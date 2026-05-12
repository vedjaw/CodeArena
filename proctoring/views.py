"""
Proctoring Views - Violation tracking, activity logging
"""
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import json

from .models import Violation, ActivityLog, WebcamSnapshot
from contests.models import Contest, ContestSession
from accounts.decorators import candidate_required


@login_required
@candidate_required
@require_POST
def report_violation(request, contest_slug):
    """Report a proctoring violation from the client."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    session = get_object_or_404(
        ContestSession, contest=contest, user=request.user, status='in_progress'
    )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    violation_type = data.get('type', 'other')
    description = data.get('description', '')

    # Create violation record
    Violation.objects.create(
        session=session,
        user=request.user,
        contest=contest,
        violation_type=violation_type,
        description=description,
        metadata=data.get('metadata', {}),
    )

    # Update session violation count
    session.violation_count += 1
    auto_submit = False

    if session.violation_count >= contest.max_violations and contest.auto_submit_on_violation:
        session.status = 'auto_submitted'
        session.ended_at = timezone.now()
        auto_submit = True

    session.save()

    return JsonResponse({
        'violation_count': session.violation_count,
        'max_violations': contest.max_violations,
        'auto_submitted': auto_submit,
        'warning': f'Warning: Violation {session.violation_count}/{contest.max_violations}',
    })


@login_required
@candidate_required
@require_POST
def log_activity(request, contest_slug):
    """Log candidate activity during contest."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    session = ContestSession.objects.filter(
        contest=contest, user=request.user
    ).first()

    if not session:
        return JsonResponse({'error': 'No session'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    ActivityLog.objects.create(
        session=session,
        user=request.user,
        event_type=data.get('event_type', 'other'),
        details=data.get('details', {}),
    )

    return JsonResponse({'status': 'logged'})


@login_required
@candidate_required
@require_POST
def upload_snapshot(request, contest_slug):
    """Upload webcam snapshot."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    session = get_object_or_404(
        ContestSession, contest=contest, user=request.user
    )

    if 'image' in request.FILES:
        WebcamSnapshot.objects.create(
            session=session,
            user=request.user,
            image=request.FILES['image'],
        )
        return JsonResponse({'status': 'uploaded'})

    return JsonResponse({'error': 'No image'}, status=400)


@login_required
def get_timer(request, contest_slug):
    """Get server-side timer for contest session."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    session = ContestSession.objects.filter(
        contest=contest, user=request.user
    ).first()

    if not session or not session.deadline:
        return JsonResponse({'error': 'No active session'}, status=400)

    remaining = (session.deadline - timezone.now()).total_seconds()
    remaining = max(0, remaining)

    return JsonResponse({
        'remaining_seconds': int(remaining),
        'deadline': session.deadline.isoformat(),
        'is_expired': remaining <= 0,
    })
