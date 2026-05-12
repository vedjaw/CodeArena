"""
API Views - REST API endpoints using Django REST Framework
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .serializers import (
    ContestSerializer, QuestionSerializer, SubmissionSerializer,
    LeaderboardSerializer, ViolationSerializer, UserSerializer,
)
from contests.models import Contest, ContestSession
from questions.models import Question
from submissions.models import Submission
from analytics.models import Leaderboard
from proctoring.models import Violation
from accounts.models import User


class IsRecruiterOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin', 'recruiter')


class ContestViewSet(viewsets.ModelViewSet):
    """API endpoints for contests."""
    serializer_class = ContestSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        return [IsRecruiterOrAdmin()]

    def get_queryset(self):
        qs = Contest.objects.all()
        if not self.request.user.is_authenticated or self.request.user.role == 'candidate':
            qs = qs.filter(status='published', visibility__in=['public', 'password'])
        elif self.request.user.role == 'recruiter':
            qs = qs.filter(created_by=self.request.user)
        return qs.order_by('-start_time')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for submissions (read-only)."""
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role in ('admin', 'recruiter'):
            return Submission.objects.all()
        return Submission.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_leaderboard(request, contest_slug):
    """Get contest leaderboard."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    entries = ContestSession.objects.filter(
        contest=contest
    ).select_related('user').order_by('-total_score', 'ended_at')

    data = []
    for rank, entry in enumerate(entries, 1):
        data.append({
            'rank': rank,
            'user': entry.user.get_full_name(),
            'score': float(entry.total_score),
            'violations': entry.violation_count,
            'status': entry.get_status_display(),
        })

    return Response({'contest': contest.title, 'leaderboard': data})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_contest_timer(request, contest_slug):
    """Get server-side contest timer."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    session = ContestSession.objects.filter(
        contest=contest, user=request.user
    ).first()

    if not session or not session.deadline:
        return Response({'error': 'No active session'}, status=400)

    remaining = max(0, (session.deadline - timezone.now()).total_seconds())
    return Response({
        'remaining_seconds': int(remaining),
        'deadline': session.deadline.isoformat(),
        'is_expired': remaining <= 0,
    })


@api_view(['GET'])
@permission_classes([IsRecruiterOrAdmin])
def api_violations(request, contest_slug):
    """Get violations for a contest."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    violations = Violation.objects.filter(contest=contest).select_related('user')
    serializer = ViolationSerializer(violations, many=True)
    return Response(serializer.data)
