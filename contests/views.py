"""
Contests Views - Contest CRUD, access control, session management
"""
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from django.core.mail import send_mail
from django.conf import settings as django_settings

from .models import Contest, ContestSession, ContestInvitation, Announcement
from .forms import ContestForm, ContestPasswordForm, InvitationForm, AnnouncementForm
from accounts.decorators import role_required, recruiter_or_admin_required, candidate_required
from questions.models import Question


# ─── Contest List ────────────────────────────────────────────────────────────────

def contest_list(request):
    """Public contest listing page."""
    now = timezone.now()
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    # Base query for all published contests
    base_contests = Contest.objects.filter(status='published').annotate(num_questions=Count('questions'))

    if request.user.is_authenticated:
        if request.user.is_admin:
            # Admins see everything published
            contests = base_contests
        elif request.user.is_recruiter:
            # Recruiters see ONLY their own contests, regardless of visibility
            contests = base_contests.filter(created_by=request.user)
        else:
            # Candidates see public/password contests, PLUS private contests they are invited to
            invited_contest_ids = ContestInvitation.objects.filter(
                email=request.user.email
            ).values_list('contest_id', flat=True)
            
            contests = base_contests.filter(
                Q(visibility__in=['public', 'password']) |
                Q(id__in=invited_contest_ids)
            )
    else:
        # Anonymous users see only public/password contests
        contests = base_contests.filter(visibility__in=['public', 'password'])

    if search:
        contests = contests.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    if status_filter == 'upcoming':
        contests = contests.filter(start_time__gt=now)
    elif status_filter == 'ongoing':
        contests = contests.filter(start_time__lte=now, end_time__gte=now)
    elif status_filter == 'past':
        contests = contests.filter(end_time__lt=now)

    context = {
        'contests': contests.order_by('-start_time'),
        'search': search,
        'status_filter': status_filter,
        'now': now,
    }
    return render(request, 'contests/list.html', context)


# ─── Contest Detail ──────────────────────────────────────────────────────────────

def contest_detail(request, slug):
    """Contest detail/landing page."""
    contest = get_object_or_404(Contest, slug=slug)
    now = timezone.now()

    # Access control for private (invite-only) contests
    if contest.visibility == 'private':
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in to access this contest.')
            return redirect('accounts:login')
        if not (request.user.is_admin or contest.created_by == request.user):
            is_invited = ContestInvitation.objects.filter(
                contest=contest, email=request.user.email
            ).exists()
            if not is_invited:
                messages.error(request, 'This is an invite-only contest. You do not have access.')
                return redirect('contests:list')

    # Check if user has a session
    session = None
    if request.user.is_authenticated:
        session = ContestSession.objects.filter(contest=contest, user=request.user).first()

    context = {
        'contest': contest,
        'session': session,
        'question_count': contest.questions.count(),
        'now': now,
        'is_creator': request.user.is_authenticated and contest.created_by == request.user,
        'announcements': contest.announcements.all()[:5],
    }
    return render(request, 'contests/detail.html', context)


# ─── Contest Create ──────────────────────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
def contest_create(request):
    """Create a new contest."""
    if request.method == 'POST':
        form = ContestForm(request.POST, request.FILES)
        if form.is_valid():
            contest = form.save(commit=False)
            contest.created_by = request.user
            # Generate unique slug
            base_slug = slugify(contest.title)
            contest.slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
            contest.save()
            messages.success(request, f'Contest "{contest.title}" created successfully!')
            return redirect('contests:manage', slug=contest.slug)
    else:
        form = ContestForm(initial={
            'duration_minutes': 120,
            'max_violations': 3,
            'total_marks': 100,
            'passing_percentage': 40,
        })

    return render(request, 'contests/create.html', {'form': form})


# ─── Contest Edit ────────────────────────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
def contest_edit(request, slug):
    """Edit an existing contest."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden('Not authorized')

    if request.method == 'POST':
        form = ContestForm(request.POST, request.FILES, instance=contest)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contest updated successfully!')
            return redirect('contests:manage', slug=contest.slug)
    else:
        form = ContestForm(instance=contest)

    return render(request, 'contests/edit.html', {'form': form, 'contest': contest})


# ─── Contest Manage ──────────────────────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
def contest_manage(request, slug):
    """Contest management dashboard for creators."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden('Not authorized')

    questions = contest.questions.all().order_by('order')
    sessions = contest.sessions.select_related('user').order_by('-started_at')
    announcements = contest.announcements.all()
    invitations = contest.invitations.all().order_by('-sent_at')

    context = {
        'contest': contest,
        'questions': questions,
        'sessions': sessions,
        'announcements': announcements,
        'invitations': invitations,
        'participant_count': sessions.count(),
        'completed_count': sessions.filter(status='completed').count(),
        'invitation_form': InvitationForm(),
        'announcement_form': AnnouncementForm(),
    }
    return render(request, 'contests/manage.html', context)


# ─── Contest Publish/Unpublish ───────────────────────────────────────────────────

@login_required
@require_POST
def contest_publish(request, slug):
    """Publish or unpublish a contest."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden('Not authorized')

    action = request.POST.get('action', 'publish')
    if action == 'publish':
        if contest.questions.count() == 0:
            messages.error(request, 'Add at least one question before publishing.')
        else:
            contest.status = 'published'
            contest.save()
            messages.success(request, 'Contest published successfully!')
    elif action == 'unpublish':
        contest.status = 'draft'
        contest.save()
        messages.info(request, 'Contest moved to draft.')

    return redirect('contests:manage', slug=contest.slug)


# ─── Contest Clone ───────────────────────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
def contest_clone(request, slug):
    """Clone an existing contest."""
    original = get_object_or_404(Contest, slug=slug)
    if original.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden('Not authorized')

    # Clone contest
    new_contest = Contest.objects.create(
        title=f"{original.title} (Copy)",
        slug=f"{slugify(original.title)}-copy-{uuid.uuid4().hex[:8]}",
        description=original.description,
        instructions=original.instructions,
        created_by=request.user,
        start_time=timezone.now() + timezone.timedelta(days=7),
        end_time=timezone.now() + timezone.timedelta(days=8),
        duration_minutes=original.duration_minutes,
        status='draft',
        visibility=original.visibility,
        total_marks=original.total_marks,
        passing_percentage=original.passing_percentage,
        negative_marking=original.negative_marking,
        enable_proctoring=original.enable_proctoring,
        enable_webcam=original.enable_webcam,
        max_violations=original.max_violations,
        auto_submit_on_violation=original.auto_submit_on_violation,
        fullscreen_required=original.fullscreen_required,
        shuffle_questions=original.shuffle_questions,
        shuffle_options=original.shuffle_options,
        show_results_immediately=original.show_results_immediately,
        allow_review=original.allow_review,
        leaderboard_visible=original.leaderboard_visible,
    )

    # Clone questions
    for q in original.questions.all():
        old_q_id = q.id
        q.pk = None
        q.contest = new_contest
        q.save()

        # Clone coding question details
        from questions.models import CodingQuestion, TestCase, MCQQuestion, MCQOption, SubjectiveQuestion
        if q.question_type == 'coding':
            try:
                old_coding = CodingQuestion.objects.get(question_id=old_q_id)
                old_coding.pk = None
                old_coding.question = q
                old_coding.save()

                for tc in TestCase.objects.filter(coding_question_id=old_coding.pk):
                    tc.pk = None
                    tc.coding_question = old_coding
                    tc.save()
            except CodingQuestion.DoesNotExist:
                pass

        elif q.question_type in ('mcq_single', 'mcq_multiple'):
            try:
                old_mcq = MCQQuestion.objects.get(question_id=old_q_id)
                old_mcq_id = old_mcq.id
                old_mcq.pk = None
                old_mcq.question = q
                old_mcq.save()

                for opt in MCQOption.objects.filter(mcq_question_id=old_mcq_id):
                    opt.pk = None
                    opt.mcq_question = old_mcq
                    opt.save()
            except MCQQuestion.DoesNotExist:
                pass

        elif q.question_type == 'subjective':
            try:
                old_sub = SubjectiveQuestion.objects.get(question_id=old_q_id)
                old_sub.pk = None
                old_sub.question = q
                old_sub.save()
            except SubjectiveQuestion.DoesNotExist:
                pass

    messages.success(request, f'Contest cloned as "{new_contest.title}"')
    return redirect('contests:manage', slug=new_contest.slug)


# ─── Contest Delete ──────────────────────────────────────────────────────────────

@login_required
@require_POST
def contest_delete(request, slug):
    """Delete a contest."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden('Not authorized')

    title = contest.title
    contest.delete()
    messages.success(request, f'Contest "{title}" deleted.')
    return redirect('dashboard:home')


# ─── Contest Access (Password Check) ────────────────────────────────────────────

@login_required
@candidate_required
def contest_access(request, slug):
    """Handle password-protected contest access."""
    contest = get_object_or_404(Contest, slug=slug, status='published')

    if contest.visibility == 'password':
        if request.method == 'POST':
            form = ContestPasswordForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['password'] == contest.access_password:
                    request.session[f'contest_access_{contest.id}'] = True
                    return redirect('contests:system_check', slug=contest.slug)
                else:
                    messages.error(request, 'Incorrect password.')
        else:
            form = ContestPasswordForm()
        return render(request, 'contests/access.html', {'form': form, 'contest': contest})

    return redirect('contests:system_check', slug=contest.slug)


# ─── System Check ───────────────────────────────────────────────────────────────

@login_required
@candidate_required
def system_check(request, slug):
    """Pre-contest system compatibility checks."""
    contest = get_object_or_404(Contest, slug=slug, status='published')

    # Verify access for password-protected contests
    if contest.visibility == 'password':
        if not request.session.get(f'contest_access_{contest.id}'):
            return redirect('contests:access', slug=contest.slug)
            
    # Verify access for private (invite-only) contests
    if contest.visibility == 'private':
        is_invited = ContestInvitation.objects.filter(
            contest=contest, email=request.user.email
        ).exists()
        if not is_invited:
            messages.error(request, 'This is an invite-only contest. You do not have access.')
            return redirect('contests:detail', slug=contest.slug)

    context = {
        'contest': contest,
        'require_camera': contest.enable_webcam,
        'require_fullscreen': contest.fullscreen_required,
    }
    return render(request, 'contests/system_check.html', context)


# ─── Start Contest ───────────────────────────────────────────────────────────────

@login_required
@candidate_required
@require_POST
def contest_start(request, slug):
    """Start contest session for candidate."""
    contest = get_object_or_404(Contest, slug=slug, status='published')
    now = timezone.now()

    # Validate contest timing
    if now < contest.start_time:
        messages.error(request, 'Contest has not started yet.')
        return redirect('contests:detail', slug=slug)
    if now > contest.end_time:
        messages.error(request, 'Contest has ended.')
        return redirect('contests:detail', slug=slug)

    # Get or create session
    session, created = ContestSession.objects.get_or_create(
        contest=contest,
        user=request.user,
        defaults={
            'status': 'in_progress',
            'started_at': now,
            'time_remaining_seconds': contest.duration_minutes * 60,
            'max_possible_score': contest.total_marks,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
    )

    if not created and session.status in ('completed', 'auto_submitted', 'disqualified'):
        messages.error(request, 'You have already completed this contest.')
        return redirect('contests:detail', slug=slug)

    if not created and session.status == 'not_started':
        session.status = 'in_progress'
        session.started_at = now
        session.time_remaining_seconds = contest.duration_minutes * 60
        session.save()

    return redirect('contests:take', slug=slug)


# ─── Take Contest (IDE Page) ────────────────────────────────────────────────────

@login_required
@candidate_required
def contest_take(request, slug):
    """The main contest-taking page with IDE."""
    contest = get_object_or_404(Contest, slug=slug)
    session = get_object_or_404(ContestSession, contest=contest, user=request.user)

    if session.status in ('completed', 'auto_submitted', 'disqualified'):
        messages.info(request, 'This contest session has ended.')
        return redirect('contests:detail', slug=slug)

    if session.is_expired:
        session.status = 'auto_submitted'
        session.ended_at = timezone.now()
        session.save()
        messages.info(request, 'Time expired. Contest auto-submitted.')
        return redirect('contests:detail', slug=slug)

    questions = list(contest.questions.all().order_by('order'))
    question_id = request.GET.get('q')
    current_question = None

    if question_id:
        current_question = next((q for q in questions if str(q.id) == question_id), None)
    if not current_question and questions:
        current_question = questions[0]

    # Get saved drafts (for sidebar answered/unanswered indicator + MCQ/subjective restore)
    from submissions.models import CodeDraft, MCQAnswer, SubjectiveAnswer
    drafts = {}
    for q in questions:
        if q.question_type == 'coding':
            draft = CodeDraft.objects.filter(
                user=request.user, contest=contest, question=q
            ).first()
            drafts[q.id] = draft
        elif q.question_type in ('mcq_single', 'mcq_multiple'):
            answer = MCQAnswer.objects.filter(
                user=request.user, contest=contest, question=q
            ).first()
            drafts[q.id] = answer
        elif q.question_type == 'subjective':
            answer = SubjectiveAnswer.objects.filter(
                user=request.user, contest=contest, question=q
            ).first()
            drafts[q.id] = answer

    # Build per-language draft map for the current coding question.
    # Shape: { "python": "def foo()...", "cpp": "#include...", ... }
    # Sent to the template as a JSON blob so the JS code-cache is pre-populated
    # for ALL languages without needing extra API calls on language switch.
    drafts_by_lang = {}
    if current_question and current_question.question_type == 'coding':
        all_lang_drafts = CodeDraft.objects.filter(
            user=request.user, contest=contest, question=current_question
        )
        for d in all_lang_drafts:
            drafts_by_lang[d.language] = d.source_code

    # Get visible (sample) test cases for the current coding question
    sample_test_cases = []
    if current_question and current_question.question_type == 'coding':
        try:
            coding = current_question.coding_detail
            sample_test_cases = list(
                coding.test_cases.filter(is_hidden=False).order_by('order')
            )
        except Exception:
            pass

    context = {
        'contest': contest,
        'session': session,
        'questions': questions,
        'current_question': current_question,
        'drafts': drafts,
        'drafts_by_lang': drafts_by_lang,
        'deadline_timestamp': session.deadline.isoformat() if session.deadline else None,
        'sample_test_cases': sample_test_cases,
    }
    return render(request, 'contests/take.html', context)


# ─── Preview Contest (Creator Only) ──────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
def contest_preview(request, slug):
    """Read-only preview of the IDE exactly as candidates will see it."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden('Not authorized')

    questions = list(contest.questions.all().order_by('order'))
    question_id = request.GET.get('q')
    current_question = None

    if question_id:
        current_question = next((q for q in questions if str(q.id) == question_id), None)
    if not current_question and questions:
        current_question = questions[0]

    sample_test_cases = []
    if current_question and current_question.question_type == 'coding':
        try:
            coding = current_question.coding_detail
            sample_test_cases = list(
                coding.test_cases.filter(is_hidden=False).order_by('order')
            )
        except Exception:
            pass

    context = {
        'contest': contest,
        'session': None,
        'questions': questions,
        'current_question': current_question,
        'drafts': {},
        'deadline_timestamp': None,
        'sample_test_cases': sample_test_cases,
        'preview_mode': True,
    }
    return render(request, 'contests/take.html', context)


# ─── Submit Contest ──────────────────────────────────────────────────────────────

@login_required
@candidate_required
@require_POST
def contest_submit(request, slug):
    """Final contest submission."""
    contest = get_object_or_404(Contest, slug=slug)
    session = get_object_or_404(ContestSession, contest=contest, user=request.user)

    if session.status in ('completed', 'auto_submitted'):
        messages.info(request, 'Contest already submitted.')
        return redirect('contests:detail', slug=slug)

    session.status = 'completed'
    session.ended_at = timezone.now()
    session.save()

    # Calculate final scores
    from submissions.models import Submission
    final_submissions = Submission.objects.filter(
        user=request.user, contest=contest, is_final=True
    )
    total_score = sum(s.score for s in final_submissions)
    session.total_score = total_score
    session.save()

    messages.success(request, 'Contest submitted successfully!')
    return redirect('contests:detail', slug=slug)


# ─── Send Invitations ───────────────────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
@require_POST
def send_invitations(request, slug):
    """Send contest invitations to email addresses."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    form = InvitationForm(request.POST, request.FILES)
    if form.is_valid():
        emails = form.cleaned_data['parsed_emails']
        added = 0
        for email in emails:
            invitation, created = ContestInvitation.objects.get_or_create(
                contest=contest, email=email,
            )
            if created:
                added += 1

        messages.success(request, f'{added} email(s) added to the whitelist.')

    return redirect('contests:manage', slug=slug)


# ─── Create Announcement ────────────────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
@require_POST
def create_announcement(request, slug):
    """Create a contest announcement."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    form = AnnouncementForm(request.POST)
    if form.is_valid():
        announcement = form.save(commit=False)
        announcement.contest = contest
        announcement.created_by = request.user
        announcement.save()
        messages.success(request, 'Announcement posted.')

    return redirect('contests:manage', slug=slug)


# ─── Reset Session ───────────────────────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
@require_POST
def reset_session(request, slug, session_id):
    """Reset a candidate's progress allowing them to retake."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden('Not authorized')

    session = get_object_or_404(ContestSession, id=session_id, contest=contest)
    candidate_name = session.user.get_full_name() or session.user.email
    session.delete()
    
    messages.success(request, f'Progress for {candidate_name} has been reset. They can now retake the contest.')
    return redirect('contests:manage', slug=slug)


# ─── Remove Invitation ─────────────────────────────────────────────────────────

@login_required
@recruiter_or_admin_required
@require_POST
def remove_invitation(request, slug, invite_id):
    """Remove a contest invitation."""
    contest = get_object_or_404(Contest, slug=slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    invitation = get_object_or_404(ContestInvitation, id=invite_id, contest=contest)
    email = invitation.email
    invitation.delete()
    messages.success(request, f'Removed invitation for {email}.')
    return redirect('contests:manage', slug=slug)
