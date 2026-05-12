"""
Contests Admin Configuration
"""
from django.contrib import admin
from .models import Contest, ContestSession, ContestInvitation, Announcement


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'status', 'visibility', 'start_time', 'end_time', 'duration_minutes')
    list_filter = ('status', 'visibility', 'enable_proctoring')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'access_token')
    date_hierarchy = 'start_time'


@admin.register(ContestSession)
class ContestSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'status', 'total_score', 'violation_count', 'started_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'contest__title')


@admin.register(ContestInvitation)
class ContestInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'contest', 'is_accepted', 'sent_at')
    list_filter = ('is_accepted',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'contest', 'is_urgent', 'created_at')
    list_filter = ('is_urgent',)
