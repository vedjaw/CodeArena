"""
Questions Models - Coding, MCQ, and Subjective question types
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from contests.models import Contest


class Question(models.Model):
    """Base question model supporting multiple types."""

    class QuestionType(models.TextChoices):
        CODING = 'coding', 'Coding'
        MCQ_SINGLE = 'mcq_single', 'MCQ (Single Answer)'
        MCQ_MULTIPLE = 'mcq_multiple', 'MCQ (Multiple Answers)'
        SUBJECTIVE = 'subjective', 'Subjective'

    class Difficulty(models.TextChoices):
        EASY = 'easy', 'Easy'
        MEDIUM = 'medium', 'Medium'
        HARD = 'hard', 'Hard'

    # Relationships
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='questions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_questions')

    # Question details
    title = models.CharField(max_length=300)
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, db_index=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    order = models.PositiveIntegerField(default=0, help_text='Display order in contest')

    # Scoring
    marks = models.DecimalField(max_digits=6, decimal_places=2, default=10)
    negative_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    partial_scoring = models.BooleanField(default=False)

    # Tags
    tags = models.JSONField(default=list, blank=True)

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'questions_question'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['contest', 'question_type']),
        ]

    def __str__(self):
        return f"[{self.question_type}] {self.title}"


class CodingQuestion(models.Model):
    """Extended data for coding-type questions."""

    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('cpp', 'C++'),
        ('java', 'Java'),
        ('javascript', 'JavaScript'),
        ('c', 'C'),
        ('csharp', 'C#'),
        ('go', 'Go'),
        ('ruby', 'Ruby'),
        ('rust', 'Rust'),
    ]

    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='coding_detail')

    # Problem statement
    problem_statement = models.TextField()
    constraints = models.TextField(blank=True)
    input_format = models.TextField(blank=True)
    output_format = models.TextField(blank=True)
    sample_input = models.TextField(blank=True)
    sample_output = models.TextField(blank=True)
    explanation = models.TextField(blank=True)

    # Execution limits
    time_limit_seconds = models.FloatField(default=2.0, validators=[MinValueValidator(0.5), MaxValueValidator(30)])
    memory_limit_mb = models.PositiveIntegerField(default=256, validators=[MaxValueValidator(1024)])

    # Allowed languages
    allowed_languages = models.JSONField(
        default=list,
        help_text='List of allowed language codes: python, cpp, java, javascript',
    )

    # Starter code templates
    starter_code = models.JSONField(
        default=dict, blank=True,
        help_text='Language-keyed starter code: {"python": "...", "cpp": "..."}'
    )
    
    # Hidden driver code appended during execution
    driver_code = models.JSONField(
        default=dict, blank=True,
        help_text='Language-keyed hidden driver code'
    )

    class Meta:
        db_table = 'questions_coding'

    def __str__(self):
        return f"Coding: {self.question.title}"

    def save(self, *args, **kwargs):
        if not self.allowed_languages:
            self.allowed_languages = [lang[0] for lang in self.LANGUAGE_CHOICES]
        super().save(*args, **kwargs)


class TestCase(models.Model):
    """Test case for coding questions."""
    coding_question = models.ForeignKey(CodingQuestion, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField()
    expected_output = models.TextField()
    is_hidden = models.BooleanField(default=True, help_text='Hidden test cases are not shown to candidates')
    weight = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0,
        help_text='Weight for partial scoring'
    )
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'questions_testcase'
        ordering = ['order', 'id']

    def __str__(self):
        visibility = 'Hidden' if self.is_hidden else 'Visible'
        return f"TC {self.order} ({visibility}): {self.coding_question.question.title}"


class MCQQuestion(models.Model):
    """Extended data for MCQ questions."""
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='mcq_detail')
    question_text = models.TextField()
    explanation = models.TextField(blank=True, help_text='Explanation shown after contest')

    class Meta:
        db_table = 'questions_mcq'

    def __str__(self):
        return f"MCQ: {self.question.title}"


class MCQOption(models.Model):
    """Option for MCQ questions."""
    mcq_question = models.ForeignKey(MCQQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'questions_mcq_option'
        ordering = ['order']

    def __str__(self):
        correct = '✓' if self.is_correct else '✗'
        return f"{correct} {self.option_text[:50]}"


class SubjectiveQuestion(models.Model):
    """Extended data for subjective questions."""
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='subjective_detail')
    question_text = models.TextField()
    guidelines = models.TextField(blank=True, help_text='Grading guidelines for reviewers')
    max_word_count = models.PositiveIntegerField(default=1000)
    reference_answer = models.TextField(blank=True, help_text='Reference answer for grading')

    class Meta:
        db_table = 'questions_subjective'

    def __str__(self):
        return f"Subjective: {self.question.title}"
