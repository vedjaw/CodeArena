"""
Analytics Admin Configuration
"""
from django.contrib import admin
from .models import Leaderboard, ContestReport


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('contest', 'user', 'rank', 'score', 'problems_solved', 'updated_at')
    list_filter = ('contest',)
    search_fields = ('user__email',)


@admin.register(ContestReport)
class ContestReportAdmin(admin.ModelAdmin):
    list_display = ('contest', 'report_type', 'format', 'generated_by', 'created_at')
    list_filter = ('report_type', 'format')
