"""
CodeArena URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Landing page
    path('', TemplateView.as_view(template_name='base/landing.html'), name='landing'),

    # App URLs
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('contests/', include('contests.urls', namespace='contests')),
    path('questions/', include('questions.urls', namespace='questions')),
    path('submissions/', include('submissions.urls', namespace='submissions')),
    path('proctoring/', include('proctoring.urls', namespace='proctoring')),
    path('analytics/', include('analytics.urls', namespace='analytics')),

    # API URLs
    path('api/', include('api.urls', namespace='api')),

    # Dashboard redirect
    path('dashboard/', include('accounts.dashboard_urls', namespace='dashboard')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
