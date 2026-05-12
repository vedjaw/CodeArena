"""
Execution Engine - Celery tasks for async code execution
"""
from celery import shared_task
from django.utils import timezone


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def execute_code(self, submission_id, is_run_only=False, custom_input=''):
    """
    Celery task to execute submitted code.
    Tries Docker first, falls back to subprocess.
    """
    from submissions.models import Submission

    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        return {'error': 'Submission not found'}

    submission.verdict = 'running'
    submission.save(update_fields=['verdict'])

    try:
        # Try Docker execution first
        from .docker_executor import run_in_docker
        result = run_in_docker(submission, is_run_only, custom_input)
        if result.get('success'):
            return result
    except Exception:
        pass  # Docker not available, fall back to subprocess

    # Fallback to subprocess
    from .executor import run_code_sync
    run_code_sync(submission, is_run_only, custom_input)

    return {
        'submission_id': submission_id,
        'verdict': submission.verdict,
        'score': float(submission.score),
    }


@shared_task
def update_leaderboard(contest_id):
    """Update contest leaderboard after a submission."""
    from contests.models import Contest, ContestSession
    from analytics.models import Leaderboard

    try:
        contest = Contest.objects.get(id=contest_id)
    except Contest.DoesNotExist:
        return

    sessions = ContestSession.objects.filter(
        contest=contest
    ).order_by('-total_score', 'ended_at')

    for rank, session in enumerate(sessions, 1):
        Leaderboard.objects.update_or_create(
            contest=contest,
            user=session.user,
            defaults={
                'rank': rank,
                'score': session.total_score,
                'last_submission_at': session.ended_at,
            },
        )
