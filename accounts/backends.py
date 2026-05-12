"""
Accounts Backends - Custom authentication backend
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """Authenticate using email address instead of username."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        # Also support 'username' kwarg for compatibility
        if email is None:
            email = kwargs.get('username')
        if email is None:
            return None

        try:
            user = User.objects.get(email=email.lower().strip())
        except User.DoesNotExist:
            # Run the default password hasher to reduce timing attacks
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
