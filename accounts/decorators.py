"""
Accounts Decorators - Role-based access control
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden


def role_required(*roles):
    """Decorator to restrict view access by user role."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role not in roles and not request.user.is_superuser:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard:home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def recruiter_or_admin_required(view_func):
    """Allow access only to recruiters and admins."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role not in ('admin', 'recruiter'):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def candidate_required(view_func):
    """Allow access only to candidates."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'candidate' and not request.user.is_superuser:
            messages.error(request, 'This page is only accessible to candidates.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper
