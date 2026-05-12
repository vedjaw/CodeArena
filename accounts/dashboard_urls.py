"""
Dashboard URL Configuration - Role-based dashboard routing
"""
from django.urls import path
from . import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.dashboard_home, name='home'),
    path('admin/', dashboard_views.admin_dashboard, name='admin'),
    path('recruiter/', dashboard_views.recruiter_dashboard, name='recruiter'),
    path('candidate/', dashboard_views.candidate_dashboard, name='candidate'),
    path('admin/users/', dashboard_views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/toggle/', dashboard_views.admin_toggle_user, name='admin_toggle_user'),
]
