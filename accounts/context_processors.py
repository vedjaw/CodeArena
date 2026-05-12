"""
Context processor to make user role available in all templates.
"""


def user_role(request):
    """Add user role info to template context."""
    if request.user.is_authenticated:
        return {
            'user_role': request.user.role,
            'is_admin': request.user.is_admin,
            'is_recruiter': request.user.is_recruiter,
            'is_candidate': request.user.is_candidate,
        }
    return {
        'user_role': None,
        'is_admin': False,
        'is_recruiter': False,
        'is_candidate': False,
    }
