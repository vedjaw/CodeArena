"""
Dashboard Views - Role-based dashboards for admin, recruiter, candidate
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone

from .models import User, UserActivity
from .decorators import role_required
from contests.models import Contest, ContestSession
from submissions.models import Submission


@login_required
def dashboard_home(request):
    """Route to appropriate dashboard based on user role."""
    if request.user.is_admin:
        return redirect('dashboard:admin')
    elif request.user.is_recruiter:
        return redirect('dashboard:recruiter')
    else:
        return redirect('dashboard:candidate')


@login_required
@role_required('admin')
def admin_dashboard(request):
    """Admin dashboard with system overview."""
    now = timezone.now()
    context = {
        'total_users': User.objects.count(),
        'total_candidates': User.objects.filter(role='candidate').count(),
        'total_recruiters': User.objects.filter(role='recruiter').count(),
        'total_contests': Contest.objects.count(),
        'active_contests': Contest.objects.filter(
            start_time__lte=now, end_time__gte=now, status='published'
        ).count(),
        'total_submissions': Submission.objects.count(),
        'recent_activities': UserActivity.objects.select_related('user')[:20],
        'recent_users': User.objects.order_by('-date_joined')[:10],
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
@role_required('recruiter')
def recruiter_dashboard(request):
    """Recruiter dashboard with contest management overview."""
    now = timezone.now()
    my_contests = Contest.objects.filter(created_by=request.user)
    context = {
        'total_contests': my_contests.count(),
        'active_contests': my_contests.filter(
            start_time__lte=now, end_time__gte=now, status='published'
        ).count(),
        'draft_contests': my_contests.filter(status='draft').count(),
        'total_participants': ContestSession.objects.filter(
            contest__created_by=request.user
        ).values('user').distinct().count(),
        'recent_contests': my_contests.order_by('-created_at')[:5],
        'recent_submissions': Submission.objects.filter(
            contest__created_by=request.user
        ).select_related('user', 'contest', 'question').order_by('-submitted_at')[:10],
    }
    return render(request, 'accounts/recruiter_dashboard.html', context)


@login_required
@role_required('candidate')
def candidate_dashboard(request):
    """Candidate dashboard with contests and submissions."""
    now = timezone.now()
    my_sessions = ContestSession.objects.filter(user=request.user)
    context = {
        'upcoming_contests': Contest.objects.filter(
            status='published', start_time__gt=now
        ).order_by('start_time')[:5],
        'ongoing_contests': Contest.objects.filter(
            status='published', start_time__lte=now, end_time__gte=now
        ).order_by('start_time'),
        'completed_sessions': my_sessions.filter(
            status='completed'
        ).select_related('contest').order_by('-ended_at')[:10],
        'total_contests_taken': my_sessions.filter(status='completed').count(),
        'recent_submissions': Submission.objects.filter(
            user=request.user
        ).select_related('contest', 'question').order_by('-submitted_at')[:10],
    }
    return render(request, 'accounts/candidate_dashboard.html', context)


@login_required
@role_required('admin')
def admin_users(request):
    """Admin user management page."""
    role_filter = request.GET.get('role', '')
    search = request.GET.get('search', '')

    users = User.objects.all()
    if role_filter:
        users = users.filter(role=role_filter)
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    return render(request, 'accounts/admin_users.html', {
        'users': users.order_by('-date_joined'),
        'role_filter': role_filter,
        'search': search,
    })


@login_required
@role_required('admin')
def admin_toggle_user(request, user_id):
    """Toggle user active status."""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user != request.user:
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {user.email} has been {status}.')
    return redirect('dashboard:admin_users')
