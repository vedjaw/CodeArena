"""
Proctoring Models - Violation tracking, webcam snapshots, activity logs
"""
from django.db import models
from django.conf import settings
from contests.models import Contest, ContestSession


class Violation(models.Model):
    """Proctoring violation record."""

    class ViolationType(models.TextChoices):
        TAB_SWITCH = 'tab_switch', 'Tab Switch'
        WINDOW_BLUR = 'window_blur', 'Window Focus Loss'
        COPY_PASTE = 'copy_paste', 'Copy/Paste Attempt'
        RIGHT_CLICK = 'right_click', 'Right Click'
        FULLSCREEN_EXIT = 'fullscreen_exit', 'Fullscreen Exit'
        SHORTCUT_KEY = 'shortcut_key', 'Keyboard Shortcut'
        MULTI_MONITOR = 'multi_monitor', 'Multiple Monitor Detected'
        BROWSER_RESIZE = 'browser_resize', 'Browser Resize'
        DEV_TOOLS = 'dev_tools', 'Developer Tools Opened'
        OTHER = 'other', 'Other'

    session = models.ForeignKey(ContestSession, on_delete=models.CASCADE, related_name='violations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='violations')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='violations')

    violation_type = models.CharField(max_length=30, choices=ViolationType.choices)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    screenshot = models.ImageField(upload_to='violations/screenshots/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'proctoring_violation'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', 'violation_type']),
            models.Index(fields=['contest', 'user']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.violation_type} at {self.created_at}"


class WebcamSnapshot(models.Model):
    """Periodic webcam snapshots during contest."""
    session = models.ForeignKey(ContestSession, on_delete=models.CASCADE, related_name='webcam_snapshots')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='snapshots/')
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'proctoring_webcam_snapshot'
        ordering = ['-captured_at']


class ActivityLog(models.Model):
    """Detailed activity tracking during contest."""

    class EventType(models.TextChoices):
        PAGE_FOCUS = 'page_focus', 'Page Got Focus'
        PAGE_BLUR = 'page_blur', 'Page Lost Focus'
        QUESTION_SWITCH = 'question_switch', 'Switched Question'
        CODE_RUN = 'code_run', 'Ran Code'
        CODE_SUBMIT = 'code_submit', 'Submitted Code'
        ANSWER_SAVE = 'answer_save', 'Saved Answer'
        COPY = 'copy', 'Copy Attempted'
        PASTE = 'paste', 'Paste Attempted'
        KEYDOWN = 'keydown', 'Key Pressed'
        MOUSE_LEAVE = 'mouse_leave', 'Mouse Left Window'

    session = models.ForeignKey(ContestSession, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'proctoring_activity_log'
        ordering = ['-timestamp']
