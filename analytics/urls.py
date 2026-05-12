"""
Analytics URL Configuration
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('leaderboard/<slug:contest_slug>/', views.leaderboard, name='leaderboard'),
    path('contest/<slug:contest_slug>/', views.contest_analytics, name='contest_analytics'),
    path('export/<slug:contest_slug>/<str:format_type>/', views.export_report, name='export_report'),
]
