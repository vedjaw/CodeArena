"""
Contests URL Configuration
"""
from django.urls import path
from . import views

app_name = 'contests'

urlpatterns = [
    path('', views.contest_list, name='list'),
    path('create/', views.contest_create, name='create'),
    path('<slug:slug>/', views.contest_detail, name='detail'),
    path('<slug:slug>/edit/', views.contest_edit, name='edit'),
    path('<slug:slug>/manage/', views.contest_manage, name='manage'),
    path('<slug:slug>/publish/', views.contest_publish, name='publish'),
    path('<slug:slug>/clone/', views.contest_clone, name='clone'),
    path('<slug:slug>/delete/', views.contest_delete, name='delete'),
    path('<slug:slug>/access/', views.contest_access, name='access'),
    path('<slug:slug>/system-check/', views.system_check, name='system_check'),
    path('<slug:slug>/start/', views.contest_start, name='start'),
    path('<slug:slug>/take/', views.contest_take, name='take'),
    path('<slug:slug>/preview/', views.contest_preview, name='preview'),
    path('<slug:slug>/submit/', views.contest_submit, name='submit'),
    path('<slug:slug>/invite/', views.send_invitations, name='invite'),
    path('<slug:slug>/invite/<int:invite_id>/remove/', views.remove_invitation, name='remove_invitation'),
    path('<slug:slug>/announce/', views.create_announcement, name='announce'),
    path('<slug:slug>/reset-session/<int:session_id>/', views.reset_session, name='reset_session'),
]
