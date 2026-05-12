"""
Analytics Views - Leaderboard, reports, contest analytics
"""
import csv
import io
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone

from .models import Leaderboard, ContestReport
from contests.models import Contest, ContestSession
from submissions.models import Submission
from proctoring.models import Violation
from accounts.decorators import recruiter_or_admin_required


@login_required
def leaderboard(request, contest_slug):
    """Contest leaderboard view."""
    contest = get_object_or_404(Contest, slug=contest_slug)

    # Access control: If user is not a recruiter/admin, ensure leaderboard is set to visible
    is_staff_role = getattr(request.user, 'role', '') in ['admin', 'recruiter']
    if not is_staff_role and not contest.leaderboard_visible:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Leaderboard is currently hidden for this contest.")

    # Build leaderboard from sessions
    entries = ContestSession.objects.filter(
        contest=contest,
        status__in=['completed', 'auto_submitted', 'in_progress'],
    ).select_related('user').order_by('-total_score', 'ended_at')

    # Assign ranks
    ranked = []
    for i, entry in enumerate(entries, 1):
        ranked.append({
            'rank': i,
            'user': entry.user,
            'score': entry.total_score,
            'violations': entry.violation_count,
            'status': entry.get_status_display(),
            'time': entry.ended_at or timezone.now(),
        })

    context = {
        'contest': contest,
        'entries': ranked,
        'is_frozen': contest.leaderboard_frozen,
    }
    return render(request, 'analytics/leaderboard.html', context)


@login_required
@recruiter_or_admin_required
def contest_analytics(request, contest_slug):
    """Contest analytics dashboard for recruiters."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    sessions = ContestSession.objects.filter(contest=contest)
    submissions = Submission.objects.filter(contest=contest)

    context = {
        'contest': contest,
        'total_participants': sessions.count(),
        'completed': sessions.filter(status='completed').count(),
        'in_progress': sessions.filter(status='in_progress').count(),
        'auto_submitted': sessions.filter(status='auto_submitted').count(),
        'avg_score': sessions.filter(status='completed').aggregate(avg=Avg('total_score'))['avg'] or 0,
        'total_submissions': submissions.count(),
        'total_violations': Violation.objects.filter(contest=contest).count(),
        'question_stats': _get_question_stats(contest),
        'score_distribution': _get_score_distribution(sessions),
    }
    return render(request, 'analytics/contest_analytics.html', context)


@login_required
@recruiter_or_admin_required
def export_report(request, contest_slug, format_type):
    """Export contest report as CSV/PDF/Excel."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    sessions = ContestSession.objects.filter(contest=contest).select_related('user')

    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{contest.slug}_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Rank', 'Name', 'Email', 'Score', 'Violations', 'Status', 'Started', 'Ended'])

        for i, s in enumerate(sessions.order_by('-total_score'), 1):
            writer.writerow([
                i, s.user.get_full_name(), s.user.email,
                s.total_score, s.violation_count, s.get_status_display(),
                s.started_at.strftime('%Y-%m-%d %H:%M') if s.started_at else '',
                s.ended_at.strftime('%Y-%m-%d %H:%M') if s.ended_at else '',
            ])
        return response

    elif format_type == 'xlsx':
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = 'Contest Report'
            ws.append(['Rank', 'Name', 'Email', 'Score', 'Violations', 'Status'])

            for i, s in enumerate(sessions.order_by('-total_score'), 1):
                ws.append([
                    i, s.user.get_full_name(), s.user.email,
                    float(s.total_score), s.violation_count, s.get_status_display(),
                ])

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{contest.slug}_report.xlsx"'
            wb.save(response)
            return response
        except ImportError:
            return HttpResponse('openpyxl not installed', status=500)

    return HttpResponse('Unsupported format', status=400)


def _get_question_stats(contest):
    """Get per-question submission statistics."""
    stats = []
    for q in contest.questions.all():
        subs = Submission.objects.filter(contest=contest, question=q, is_final=True)
        accepted = subs.filter(verdict='accepted').count()
        total = subs.count()
        stats.append({
            'question': q,
            'total_submissions': total,
            'accepted': accepted,
            'acceptance_rate': (accepted / total * 100) if total > 0 else 0,
        })
    return stats


def _get_score_distribution(sessions):
    """Get score distribution for charts."""
    ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    distribution = []
    for low, high in ranges:
        count = sessions.filter(
            total_score__gte=low, total_score__lt=high
        ).count()
        distribution.append({'range': f'{low}-{high}', 'count': count})
    return distribution
