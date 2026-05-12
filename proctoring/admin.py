"""
Proctoring Admin Configuration
"""
from django.contrib import admin
from .models import Violation, WebcamSnapshot, ActivityLog


@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ('user', 'contest', 'violation_type', 'created_at')
    list_filter = ('violation_type', 'created_at')
    search_fields = ('user__email', 'description')
    readonly_fields = ('created_at',)


@admin.register(WebcamSnapshot)
class WebcamSnapshotAdmin(admin.ModelAdmin):
    list_display = ('user', 'session', 'captured_at')
    readonly_fields = ('captured_at',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'session', 'event_type', 'timestamp')
    list_filter = ('event_type',)
    readonly_fields = ('timestamp',)
