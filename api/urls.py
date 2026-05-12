"""
API URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'api'

router = DefaultRouter()
router.register(r'contests', views.ContestViewSet, basename='contest')
router.register(r'submissions', views.SubmissionViewSet, basename='submission')

urlpatterns = [
    path('', include(router.urls)),
    path('leaderboard/<slug:contest_slug>/', views.api_leaderboard, name='leaderboard'),
    path('timer/<slug:contest_slug>/', views.api_contest_timer, name='timer'),
    path('violations/<slug:contest_slug>/', views.api_violations, name='violations'),
]
