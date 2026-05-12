"""
Contests Forms - Contest creation, editing, access control
"""
from django import forms
from django.utils import timezone
from .models import Contest, ContestInvitation, Announcement


class ContestForm(forms.ModelForm):
    """Form for creating/editing contests."""

    class Meta:
        model = Contest
        fields = [
            'title', 'description', 'instructions', 'banner_image',
            'start_time', 'end_time', 'duration_minutes',
            'visibility', 'access_password',
            'total_marks', 'passing_percentage', 'negative_marking',
            'enable_proctoring', 'enable_webcam', 'max_violations',
            'auto_submit_on_violation', 'fullscreen_required',
            'shuffle_questions', 'shuffle_options',
            'show_results_immediately', 'allow_review',
            'leaderboard_visible', 'tags',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Contest Title'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Describe your contest...'}),
            'instructions': forms.Textarea(attrs={'class': 'form-input', 'rows': 6, 'placeholder': 'Rules, guidelines, and instructions...'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': 5, 'max': 480}),
            'visibility': forms.Select(attrs={'class': 'form-input'}),
            'access_password': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Set access password'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-input'}),
            'passing_percentage': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'max': 100}),
            'max_violations': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 20}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        duration = cleaned_data.get('duration_minutes')

        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError('End time must be after start time.')
            window_minutes = (end_time - start_time).total_seconds() / 60
            if duration and duration > window_minutes:
                raise forms.ValidationError('Duration cannot exceed the contest window.')

        visibility = cleaned_data.get('visibility')
        password = cleaned_data.get('access_password')
        if visibility == 'password' and not password:
            raise forms.ValidationError('Password is required for password-protected contests.')

        return cleaned_data


class ContestPasswordForm(forms.Form):
    """Form for entering contest access password."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Enter contest password'}),
    )


class InvitationForm(forms.Form):
    """Form for adding contest invitations."""
    emails = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input', 'rows': 4,
            'placeholder': 'Enter email addresses, one per line...',
        }),
        help_text='Enter one email address per line.',
    )
    emails_file = forms.FileField(
        required=False,
        help_text='Or upload a .txt or .csv file with emails.'
    )

    def clean(self):
        cleaned_data = super().clean()
        emails_text = cleaned_data.get('emails') or ''
        emails_file = cleaned_data.get('emails_file')
        
        email_list = []
        
        # Parse text area
        if emails_text:
            email_list.extend([e.strip().lower() for e in emails_text.split('\n') if e.strip()])
            
        # Parse file upload
        if emails_file:
            try:
                import csv
                from io import StringIO
                content = emails_file.read().decode('utf-8')
                if emails_file.name.endswith('.csv'):
                    reader = csv.reader(StringIO(content))
                    for row in reader:
                        for item in row:
                            if '@' in str(item):
                                email_list.append(str(item).strip().lower())
                else:
                    # Treat as txt or other flat file
                    email_list.extend([e.strip().lower() for e in content.split('\n') if e.strip()])
            except Exception as e:
                raise forms.ValidationError(f"Error reading file: {str(e)}")
        
        # Validate emails
        valid_emails = []
        for email in email_list:
            if '@' in email and '.' in email:
                valid_emails.append(email)
                
        if not valid_emails:
            raise forms.ValidationError('Please provide at least one valid email address.')
            
        cleaned_data['parsed_emails'] = list(set(valid_emails))  # Deduplicate
        return cleaned_data


class AnnouncementForm(forms.ModelForm):
    """Form for contest announcements."""

    class Meta:
        model = Announcement
        fields = ['title', 'message', 'is_urgent']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Announcement title'}),
            'message': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Message...'}),
        }
