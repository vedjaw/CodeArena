"""
Submissions Admin Configuration
"""
from django.contrib import admin
from .models import Submission, CodeDraft, MCQAnswer, SubjectiveAnswer


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'question', 'language', 'verdict', 'score', 'submitted_at', 'is_final')
    list_filter = ('verdict', 'language', 'is_final')
    search_fields = ('user__email', 'question__title')
    readonly_fields = ('submitted_at', 'judged_at')
    date_hierarchy = 'submitted_at'


@admin.register(CodeDraft)
class CodeDraftAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'question', 'language', 'updated_at')


@admin.register(MCQAnswer)
class MCQAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'question', 'is_bookmarked', 'updated_at')


@admin.register(SubjectiveAnswer)
class SubjectiveAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'question', 'is_bookmarked', 'updated_at')
