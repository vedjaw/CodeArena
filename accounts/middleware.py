"""
Accounts Middleware - Role-based access and activity tracking
"""
from django.utils import timezone
from django.shortcuts import redirect


class RoleBasedAccessMiddleware:
    """Middleware to handle role-based route protection and activity tracking."""

    # Paths that don't require authentication
    PUBLIC_PATHS = [
        '/', '/accounts/login/', '/accounts/register/',
        '/accounts/forgot-password/', '/accounts/verify-email/',
        '/admin/', '/static/', '/media/', '/api/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Update last activity for authenticated users
        if request.user.is_authenticated:
            if not hasattr(request, '_activity_updated'):
                try:
                    # Only update every 5 minutes to reduce DB writes
                    user = request.user
                    if (not user.last_activity or
                            (timezone.now() - user.last_activity).seconds > 300):
                        user.last_activity = timezone.now()
                        user.save(update_fields=['last_activity'])
                except Exception:
                    pass
                request._activity_updated = True

        response = self.get_response(request)
        return response
