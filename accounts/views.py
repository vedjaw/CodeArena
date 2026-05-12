"""
Accounts Views - Authentication, registration, profile management
"""
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from django.db.models import Count, Q

from .models import User, UserActivity
from .forms import (
    RegistrationForm, LoginForm, ProfileForm,
    PasswordChangeForm, ForgotPasswordForm, ResetPasswordForm,
)
from .decorators import role_required


def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_activity(request, user, activity_type, description='', metadata=None):
    """Create an activity log entry."""
    UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        description=description,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        metadata=metadata or {},
    )


# ─── Registration ───────────────────────────────────────────────────────────────

@csrf_protect
def register_view(request):
    """User registration with role selection."""
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.email_verification_token = uuid.uuid4()
            user.email_verification_sent_at = timezone.now()
            user.save()

            # Send verification email
            verification_url = request.build_absolute_uri(
                reverse('accounts:verify_email', kwargs={'token': user.email_verification_token})
            )
            try:
                send_mail(
                    subject='CodeArena - Verify Your Email',
                    message=f'Click the link to verify your email: {verification_url}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=f'''
                        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                            <h2 style="color: #6C63FF;">Welcome to CodeArena!</h2>
                            <p>Hi {user.first_name},</p>
                            <p>Please verify your email address by clicking the button below:</p>
                            <a href="{verification_url}"
                               style="display: inline-block; background: #6C63FF; color: white;
                                      padding: 12px 30px; text-decoration: none; border-radius: 6px;
                                      margin: 20px 0;">
                                Verify Email
                            </a>
                            <p style="color: #666; font-size: 12px;">
                                If you didn't create this account, please ignore this email.
                            </p>
                        </div>
                    ''',
                )
            except Exception:
                pass  # Email sending is best-effort in dev

            messages.success(
                request,
                'Registration successful! Please check your email to verify your account.'
            )
            # Auto-login for development
            if settings.DEBUG:
                user.is_email_verified = True
                user.save()
                login(request, user)
                log_activity(request, user, 'login', 'Auto-login after registration (dev mode)')
                return redirect('dashboard:home')

            return redirect('accounts:login')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


# ─── Login ───────────────────────────────────────────────────────────────────────

@csrf_protect
def login_view(request):
    """User login with email and password."""
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, email=email, password=password)
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'Your account has been deactivated.')
                elif not user.is_email_verified and not settings.DEBUG:
                    messages.warning(request, 'Please verify your email address first.')
                else:
                    login(request, user)
                    user.login_count += 1
                    user.last_activity = timezone.now()
                    user.save(update_fields=['login_count', 'last_activity'])
                    log_activity(request, user, 'login', 'Successful login')

                    next_url = request.GET.get('next', '')
                    if next_url:
                        return redirect(next_url)
                    return redirect('dashboard:home')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


# ─── Logout ──────────────────────────────────────────────────────────────────────

@login_required
def logout_view(request):
    """Log out the user."""
    log_activity(request, request.user, 'logout', 'User logged out')
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('landing')


# ─── Email Verification ─────────────────────────────────────────────────────────

def verify_email_view(request, token):
    """Verify user email with token."""
    try:
        user = User.objects.get(email_verification_token=token)
        if user.is_email_verified:
            messages.info(request, 'Your email is already verified.')
        else:
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
            messages.success(request, 'Email verified successfully! You can now log in.')
    except User.DoesNotExist:
        messages.error(request, 'Invalid verification link.')

    return redirect('accounts:login')


# ─── Forgot Password ────────────────────────────────────────────────────────────

@csrf_protect
def forgot_password_view(request):
    """Send password reset email."""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                user.password_reset_token = uuid.uuid4()
                user.password_reset_sent_at = timezone.now()
                user.save(update_fields=['password_reset_token', 'password_reset_sent_at'])

                reset_url = request.build_absolute_uri(
                    reverse('accounts:reset_password', kwargs={'token': user.password_reset_token})
                )
                send_mail(
                    subject='CodeArena - Password Reset',
                    message=f'Click the link to reset your password: {reset_url}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                )
            except (User.DoesNotExist, Exception):
                pass  # Don't reveal if email exists

            messages.success(
                request,
                'If an account with that email exists, a password reset link has been sent.'
            )
            return redirect('accounts:login')
    else:
        form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form})


# ─── Reset Password ─────────────────────────────────────────────────────────────

@csrf_protect
def reset_password_view(request, token):
    """Reset password using token."""
    try:
        user = User.objects.get(password_reset_token=token)
        # Check if token is expired (24 hours)
        if user.password_reset_sent_at:
            time_diff = timezone.now() - user.password_reset_sent_at
            if time_diff.total_seconds() > 86400:
                messages.error(request, 'Password reset link has expired.')
                return redirect('accounts:forgot_password')
    except User.DoesNotExist:
        messages.error(request, 'Invalid reset link.')
        return redirect('accounts:forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.password_reset_token = None
            user.password_reset_sent_at = None
            user.save()
            messages.success(request, 'Password reset successful! You can now log in.')
            return redirect('accounts:login')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form, 'token': token})


# ─── Profile ────────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    """View and edit user profile."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            log_activity(request, request.user, 'profile_update', 'Profile updated')
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    activities = request.user.activities.all()[:20]

    return render(request, 'accounts/profile.html', {
        'form': form,
        'activities': activities,
    })


# ─── Change Password ────────────────────────────────────────────────────────────

@login_required
@csrf_protect
def change_password_view(request):
    """Change user password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            if not request.user.check_password(form.cleaned_data['current_password']):
                messages.error(request, 'Current password is incorrect.')
            else:
                request.user.set_password(form.cleaned_data['new_password'])
                request.user.save()
                update_session_auth_hash(request, request.user)
                log_activity(request, request.user, 'password_change', 'Password changed')
                messages.success(request, 'Password changed successfully!')
                return redirect('accounts:profile')
    else:
        form = PasswordChangeForm()

    return render(request, 'accounts/change_password.html', {'form': form})
