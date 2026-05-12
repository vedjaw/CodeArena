"""
Contests Models - Contest management, sessions, invitations
"""
import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class Contest(models.Model):
    """Online coding contest/assessment."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ONGOING = 'ongoing', 'Ongoing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private (Invite Only)'
        PASSWORD = 'password', 'Password Protected'

    # Basic info
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True, help_text='Rules and instructions shown before starting')
    banner_image = models.ImageField(upload_to='contest_banners/', blank=True, null=True)

    # Creator
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='created_contests',
    )

    # Timing
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveIntegerField(
        help_text='Duration in minutes for each candidate',
        validators=[MinValueValidator(5), MaxValueValidator(480)],
    )

    # Status and visibility
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    access_password = models.CharField(max_length=100, blank=True)
    access_token = models.UUIDField(default=uuid.uuid4, unique=True)

    # Scoring
    total_marks = models.PositiveIntegerField(default=100)
    passing_percentage = models.PositiveIntegerField(default=40, validators=[MaxValueValidator(100)])
    negative_marking = models.BooleanField(default=False)

    # Proctoring
    enable_proctoring = models.BooleanField(default=True)
    enable_webcam = models.BooleanField(default=False)
    enable_screen_recording = models.BooleanField(default=False)
    max_violations = models.PositiveIntegerField(default=3)
    auto_submit_on_violation = models.BooleanField(default=True)
    fullscreen_required = models.BooleanField(default=True)

    # Settings
    shuffle_questions = models.BooleanField(default=False)
    shuffle_options = models.BooleanField(default=False)
    show_results_immediately = models.BooleanField(default=False)
    allow_review = models.BooleanField(default=True)
    leaderboard_visible = models.BooleanField(default=True)
    leaderboard_frozen = models.BooleanField(default=False)

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contests_contest'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['created_by', 'status']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        now = timezone.now()
        return self.status == 'published' and self.start_time <= now <= self.end_time

    @property
    def is_upcoming(self):
        return self.status == 'published' and self.start_time > timezone.now()

    @property
    def is_past(self):
        return self.end_time < timezone.now()

    @property
    def question_count(self):
        return self.questions.count()

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('contests:detail', kwargs={'slug': self.slug})


class ContestSession(models.Model):
    """Tracks a candidate's session within a contest."""

    class SessionStatus(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        AUTO_SUBMITTED = 'auto_submitted', 'Auto-Submitted'
        DISQUALIFIED = 'disqualified', 'Disqualified'

    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contest_sessions')
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.NOT_STARTED)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    time_remaining_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Scoring
    total_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_possible_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)

    # Proctoring
    violation_count = models.PositiveIntegerField(default=0)
    proctoring_data = models.JSONField(default=dict, blank=True)

    # System checks
    system_check_passed = models.BooleanField(default=False)
    camera_granted = models.BooleanField(default=False)
    microphone_granted = models.BooleanField(default=False)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contests_session'
        unique_together = ['contest', 'user']
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['contest', 'status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.contest.title}"

    @property
    def deadline(self):
        """Calculate when this session's time expires."""
        if self.started_at:
            from datetime import timedelta
            session_end = self.started_at + timedelta(minutes=self.contest.duration_minutes)
            return min(session_end, self.contest.end_time)
        return None

    @property
    def is_expired(self):
        if self.deadline:
            return timezone.now() > self.deadline
        return False


class ContestInvitation(models.Model):
    """Invitation to a private contest."""
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_accepted = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'contests_invitation'
        unique_together = ['contest', 'email']

    def __str__(self):
        return f"Invite: {self.email} -> {self.contest.title}"


class Announcement(models.Model):
    """Live announcements during a contest."""
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_urgent = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contests_announcement'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.contest.title}: {self.title}"
