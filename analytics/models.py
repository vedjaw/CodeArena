"""
Analytics Models - Leaderboard, reports, contest analytics
"""
from django.db import models
from django.conf import settings
from contests.models import Contest


class Leaderboard(models.Model):
    """Contest leaderboard entry."""
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='leaderboard_entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leaderboard_entries')
    rank = models.PositiveIntegerField(default=0)
    score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_time_seconds = models.PositiveIntegerField(default=0)
    problems_solved = models.PositiveIntegerField(default=0)
    penalty = models.PositiveIntegerField(default=0)
    last_submission_at = models.DateTimeField(null=True, blank=True)
    is_frozen = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_leaderboard'
        unique_together = ['contest', 'user']
        ordering = ['rank']
        indexes = [
            models.Index(fields=['contest', 'rank']),
        ]

    def __str__(self):
        return f"#{self.rank} {self.user.email} - {self.contest.title} ({self.score})"


class ContestReport(models.Model):
    """Generated contest report."""
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='reports')
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=[
        ('summary', 'Summary'), ('detailed', 'Detailed'),
        ('violations', 'Violations'), ('analytics', 'Analytics'),
    ])
    report_file = models.FileField(upload_to='reports/', blank=True, null=True)
    report_data = models.JSONField(default=dict, blank=True)
    format = models.CharField(max_length=10, choices=[
        ('pdf', 'PDF'), ('csv', 'CSV'), ('xlsx', 'Excel'),
    ], default='pdf')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_report'
        ordering = ['-created_at']

    def __str__(self):
        return f"Report: {self.contest.title} ({self.report_type})"
