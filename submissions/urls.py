"""
Submissions URL Configuration
"""
from django.urls import path
from . import views

app_name = 'submissions'

urlpatterns = [
    path('code/<slug:contest_slug>/<int:question_id>/', views.submit_code, name='submit_code'),
    path('draft/<slug:contest_slug>/<int:question_id>/', views.save_draft, name='save_draft'),
    path('mcq/<slug:contest_slug>/<int:question_id>/', views.submit_mcq, name='submit_mcq'),
    path('subjective/<slug:contest_slug>/<int:question_id>/', views.submit_subjective, name='submit_subjective'),
    path('status/<int:submission_id>/', views.submission_status, name='status'),
]
