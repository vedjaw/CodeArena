"""
Questions URL Configuration
"""
from django.urls import path
from . import views

app_name = 'questions'

urlpatterns = [
    path('create/<slug:contest_slug>/', views.question_create, name='create'),
    path('<int:pk>/edit/', views.question_edit, name='edit'),
    path('<int:pk>/delete/', views.question_delete, name='delete'),
    path('testcase/add/<int:question_pk>/', views.testcase_add, name='testcase_add'),
    path('testcase/<int:pk>/edit/', views.testcase_edit, name='testcase_edit'),
    path('testcase/<int:pk>/delete/', views.testcase_delete, name='testcase_delete'),
]
