"""
Submissions Views - Code submission, MCQ answers, auto-save drafts
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .models import Submission, CodeDraft, MCQAnswer, SubjectiveAnswer
from contests.models import Contest, ContestSession
from questions.models import Question, CodingQuestion, MCQQuestion
from accounts.decorators import candidate_required


@login_required
@candidate_required
@require_POST
def submit_code(request, contest_slug, question_id):
    """Submit code for a coding question."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    question = get_object_or_404(Question, id=question_id, contest=contest, question_type='coding')
    session = get_object_or_404(ContestSession, contest=contest, user=request.user, status='in_progress')

    if session.is_expired:
        return JsonResponse({'error': 'Time expired'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    language = data.get('language', 'python')
    source_code = data.get('source_code', '')
    is_run = data.get('is_run', False)  # Run vs Submit

    if not source_code.strip():
        return JsonResponse({'error': 'Empty code'}, status=400)

    # Count submissions
    sub_count = Submission.objects.filter(
        user=request.user, contest=contest, question=question
    ).count()

    submission = Submission.objects.create(
        user=request.user,
        contest=contest,
        question=question,
        session=session,
        language=language,
        source_code=source_code,
        verdict='queued',
        max_score=question.marks,
        submission_number=sub_count + 1,
        is_final=not is_run,
    )

    # If it's a final submission, mark previous finals as non-final
    if not is_run:
        Submission.objects.filter(
            user=request.user, contest=contest, question=question, is_final=True
        ).exclude(id=submission.id).update(is_final=False)

    # Trigger execution via Celery (or fallback to sync)
    custom_input = data.get('custom_input', '')
    if is_run and not custom_input.strip() and hasattr(question, 'coding_detail'):
        custom_input = question.coding_detail.sample_input

    try:
        from execution_engine.tasks import execute_code
        task = execute_code.delay(submission.id, is_run, custom_input)
        submission.task_id = task.id
        submission.save(update_fields=['task_id'])
    except Exception:
        # Fallback: run synchronously without Docker
        from execution_engine.executor import run_code_sync
        run_code_sync(submission, is_run, custom_input)

    return JsonResponse({
        'submission_id': submission.id,
        'status': submission.verdict,
        'message': 'Code submitted for execution',
    })


@login_required
@candidate_required
@require_POST
def save_draft(request, contest_slug, question_id):
    """Auto-save code draft."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    question = get_object_or_404(Question, id=question_id, contest=contest)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if question.question_type == 'coding':
        CodeDraft.objects.update_or_create(
            user=request.user,
            contest=contest,
            question=question,
            language=data.get('language', 'python'),
            defaults={'source_code': data.get('source_code', ''), 'custom_input': data.get('custom_input', '')},
        )
    elif question.question_type in ('mcq_single', 'mcq_multiple'):
        MCQAnswer.objects.update_or_create(
            user=request.user, contest=contest, question=question,
            defaults={
                'selected_options': data.get('selected_options', []),
                'is_bookmarked': data.get('is_bookmarked', False),
            },
        )
    elif question.question_type == 'subjective':
        SubjectiveAnswer.objects.update_or_create(
            user=request.user, contest=contest, question=question,
            defaults={
                'answer_text': data.get('answer_text', ''),
                'is_bookmarked': data.get('is_bookmarked', False),
            },
        )

    return JsonResponse({'status': 'saved'})


@login_required
@candidate_required
@require_POST
def submit_mcq(request, contest_slug, question_id):
    """Submit MCQ answer."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    question = get_object_or_404(Question, id=question_id, contest=contest)
    session = get_object_or_404(ContestSession, contest=contest, user=request.user, status='in_progress')

    if session.is_expired:
        return JsonResponse({'error': 'Time expired'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    selected = data.get('selected_options', [])

    # Calculate score
    mcq = question.mcq_detail
    correct_options = set(mcq.options.filter(is_correct=True).values_list('id', flat=True))
    selected_set = set(int(s) for s in selected)

    score = 0
    if selected_set == correct_options:
        score = float(question.marks)
    elif question.negative_marks and selected_set and selected_set != correct_options:
        score = -float(question.negative_marks)

    # Create or update submission
    submission, _ = Submission.objects.update_or_create(
        user=request.user, contest=contest, question=question, is_final=True,
        defaults={
            'session': session,
            'selected_options': list(selected),
            'verdict': 'accepted',
            'score': score,
            'max_score': question.marks,
        },
    )

    # Save answer
    MCQAnswer.objects.update_or_create(
        user=request.user, contest=contest, question=question,
        defaults={'selected_options': list(selected)},
    )

    return JsonResponse({'status': 'submitted', 'score': float(score)})


@login_required
@candidate_required
@require_POST
def submit_subjective(request, contest_slug, question_id):
    """Submit subjective answer."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    question = get_object_or_404(Question, id=question_id, contest=contest)
    session = get_object_or_404(ContestSession, contest=contest, user=request.user, status='in_progress')

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    answer_text = data.get('answer_text', '')

    submission, _ = Submission.objects.update_or_create(
        user=request.user, contest=contest, question=question, is_final=True,
        defaults={
            'session': session,
            'answer_text': answer_text,
            'verdict': 'pending',
            'max_score': question.marks,
        },
    )

    SubjectiveAnswer.objects.update_or_create(
        user=request.user, contest=contest, question=question,
        defaults={'answer_text': answer_text},
    )

    return JsonResponse({'status': 'submitted'})


@login_required
@require_POST
def test_code(request, contest_slug, question_id):
    """Run/submit code as the contest creator for testing purposes."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    question = get_object_or_404(Question, id=question_id, contest=contest, question_type='coding')

    if contest.created_by != request.user and not request.user.is_admin:
        return JsonResponse({'error': 'Not authorized'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    language = data.get('language', 'python')
    source_code = data.get('source_code', '')
    is_run = data.get('is_run', False)

    if not source_code.strip():
        return JsonResponse({'error': 'Empty code'}, status=400)

    submission = Submission.objects.create(
        user=request.user,
        contest=contest,
        question=question,
        session=None,
        language=language,
        source_code=source_code,
        verdict='queued',
        max_score=question.marks,
        submission_number=0,
        is_final=not is_run,
    )

    custom_input = data.get('custom_input', '')

    try:
        from execution_engine.tasks import execute_code
        task = execute_code.delay(submission.id, is_run, custom_input)
        submission.task_id = task.id
        submission.save(update_fields=['task_id'])
    except Exception:
        from execution_engine.executor import run_code_sync
        run_code_sync(submission, is_run, custom_input)

    return JsonResponse({
        'submission_id': submission.id,
        'status': submission.verdict,
        'message': 'Test execution started',
    })


@login_required
def submission_status(request, submission_id):
    """Check submission status (polling endpoint)."""
    submission = get_object_or_404(Submission, id=submission_id, user=request.user)
    return JsonResponse({
        'id': submission.id,
        'verdict': submission.verdict,
        'verdict_display': submission.get_verdict_display(),
        'score': float(submission.score),
        'execution_time_ms': submission.execution_time_ms,
        'memory_used_kb': submission.memory_used_kb,
        'passed_test_cases': submission.passed_test_cases,
        'total_test_cases': submission.total_test_cases,
        'compiler_output': submission.compiler_output,
        'runtime_output': submission.runtime_output,
        'test_case_results': submission.test_case_results,
    })
