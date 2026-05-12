"""
Proctoring URL Configuration
"""
from django.urls import path
from . import views

app_name = 'proctoring'

urlpatterns = [
    path('violation/<slug:contest_slug>/', views.report_violation, name='report_violation'),
    path('activity/<slug:contest_slug>/', views.log_activity, name='log_activity'),
    path('snapshot/<slug:contest_slug>/', views.upload_snapshot, name='upload_snapshot'),
    path('timer/<slug:contest_slug>/', views.get_timer, name='timer'),
]
