"""
Submissions Models - Code submissions, MCQ answers, judgement results
"""
from django.db import models
from django.conf import settings
from contests.models import Contest, ContestSession
from questions.models import Question, CodingQuestion, MCQQuestion, SubjectiveQuestion


class Submission(models.Model):
    """A candidate's submission for a question."""

    class Verdict(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        ACCEPTED = 'accepted', 'Accepted'
        WRONG_ANSWER = 'wrong_answer', 'Wrong Answer'
        RUNTIME_ERROR = 'runtime_error', 'Runtime Error'
        TIME_LIMIT = 'time_limit', 'Time Limit Exceeded'
        MEMORY_LIMIT = 'memory_limit', 'Memory Limit Exceeded'
        COMPILATION_ERROR = 'compilation_error', 'Compilation Error'
        PARTIAL = 'partial', 'Partial Score'
        ERROR = 'error', 'System Error'

    # Relationships
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='submissions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='submissions')
    session = models.ForeignKey(ContestSession, on_delete=models.CASCADE, related_name='submissions', null=True)

    # Code submission fields
    language = models.CharField(max_length=20, blank=True)
    source_code = models.TextField(blank=True)

    # MCQ fields
    selected_options = models.JSONField(default=list, blank=True)

    # Subjective fields
    answer_text = models.TextField(blank=True)

    # Judgement results
    verdict = models.CharField(max_length=20, choices=Verdict.choices, default=Verdict.PENDING)
    score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Execution details
    execution_time_ms = models.FloatField(null=True, blank=True)
    memory_used_kb = models.FloatField(null=True, blank=True)
    compiler_output = models.TextField(blank=True)
    runtime_output = models.TextField(blank=True)

    # Test case results
    test_case_results = models.JSONField(default=list, blank=True)
    passed_test_cases = models.PositiveIntegerField(default=0)
    total_test_cases = models.PositiveIntegerField(default=0)

    # Tracking
    is_final = models.BooleanField(default=False, help_text='Is this the final submission for scoring')
    submission_number = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    judged_at = models.DateTimeField(null=True, blank=True)

    # Celery task tracking
    task_id = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'submissions_submission'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['user', 'contest', 'question']),
            models.Index(fields=['verdict']),
            models.Index(fields=['contest', 'user', 'is_final']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.question.title} [{self.verdict}]"


class CodeDraft(models.Model):
    """Auto-saved code drafts."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='code_drafts')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    language = models.CharField(max_length=20)
    source_code = models.TextField()
    custom_input = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'submissions_code_draft'
        unique_together = ['user', 'contest', 'question', 'language']

    def __str__(self):
        return f"Draft: {self.user.email} - {self.question.title} ({self.language})"


class MCQAnswer(models.Model):
    """Saved MCQ answers (auto-save)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mcq_answers')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_options = models.JSONField(default=list)
    is_bookmarked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'submissions_mcq_answer'
        unique_together = ['user', 'contest', 'question']


class SubjectiveAnswer(models.Model):
    """Saved subjective answers (auto-save)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subjective_answers')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    is_bookmarked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'submissions_subjective_answer'
        unique_together = ['user', 'contest', 'question']
