"""
Accounts Forms - Authentication, registration, profile management
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class RegistrationForm(forms.ModelForm):
    """User registration form."""
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}), validators=[validate_password])
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}),
            'role': forms.Select(attrs={'class': 'form-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        return cleaned_data


class LoginForm(forms.Form):
    """User login form."""
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))


class ProfileForm(forms.ModelForm):
    """User profile update form."""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'organization', 
            'bio', 'linkedin_url', 'github_url', 'preferred_language', 'preferred_theme'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'organization': forms.TextInput(attrs={'class': 'form-input'}),
            'bio': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-input'}),
            'github_url': forms.URLInput(attrs={'class': 'form-input'}),
            'preferred_language': forms.Select(attrs={'class': 'form-input'}, choices=[
                ('python', 'Python'), ('cpp', 'C++'), ('java', 'Java'), ('javascript', 'JavaScript'),
                ('c', 'C'), ('csharp', 'C#'), ('go', 'Go'), ('ruby', 'Ruby'), ('rust', 'Rust')
            ]),
            'preferred_theme': forms.Select(attrs={'class': 'form-input'}),
        }


class PasswordChangeForm(forms.Form):
    """User password change form."""
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}), validators=[validate_password])
    confirm_new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}))

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')

        if new_password and confirm_new_password and new_password != confirm_new_password:
            self.add_error('confirm_new_password', "New passwords do not match.")
        
        return cleaned_data


class ForgotPasswordForm(forms.Form):
    """Form to request password reset."""
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Enter your email'}))


class ResetPasswordForm(forms.Form):
    """Form to reset password using token."""
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'New Password'}), validators=[validate_password])
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm New Password'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        return cleaned_data
