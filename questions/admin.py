"""
Questions Admin Configuration
"""
from django.contrib import admin
from .models import Question, CodingQuestion, TestCase, MCQQuestion, MCQOption, SubjectiveQuestion


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'contest', 'question_type', 'difficulty', 'marks', 'order')
    list_filter = ('question_type', 'difficulty')
    search_fields = ('title',)


@admin.register(CodingQuestion)
class CodingQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'time_limit_seconds', 'memory_limit_mb')
    inlines = [TestCaseInline]


@admin.register(MCQQuestion)
class MCQQuestionAdmin(admin.ModelAdmin):
    list_display = ('question',)


@admin.register(MCQOption)
class MCQOptionAdmin(admin.ModelAdmin):
    list_display = ('mcq_question', 'option_text', 'is_correct', 'order')


@admin.register(SubjectiveQuestion)
class SubjectiveQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'max_word_count')
