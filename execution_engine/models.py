"""
Execution Engine Models - Track Docker execution jobs
"""
from django.db import models
from django.conf import settings


class ExecutionJob(models.Model):
    """Track code execution jobs in Docker containers."""

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        TIMEOUT = 'timeout', 'Timed Out'

    submission_id = models.PositiveIntegerField(db_index=True)
    language = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)

    # Docker details
    container_id = models.CharField(max_length=100, blank=True)
    image_used = models.CharField(max_length=100, blank=True)

    # Results
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    execution_time_ms = models.FloatField(null=True, blank=True)
    memory_used_kb = models.FloatField(null=True, blank=True)

    # Timing
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'execution_job'
        ordering = ['-queued_at']

    def __str__(self):
        return f"Job #{self.id} [{self.language}] - {self.status}"
