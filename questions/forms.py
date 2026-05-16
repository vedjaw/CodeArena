"""
Questions Forms - Forms for creating/editing questions
"""
from django import forms
from .models import Question, CodingQuestion, TestCase, MCQQuestion, MCQOption, SubjectiveQuestion


class QuestionForm(forms.ModelForm):
    """Base question form."""

    class Meta:
        model = Question
        fields = ['title', 'question_type', 'difficulty', 'marks', 'negative_marks']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Question Title'}),
            'question_type': forms.Select(attrs={'class': 'form-input', 'id': 'question-type-select'}),
            'difficulty': forms.Select(attrs={'class': 'form-input'}),
            'marks': forms.NumberInput(attrs={'class': 'form-input', 'min': 1}),
            'negative_marks': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'step': '0.5'}),
        }


class CodingQuestionForm(forms.ModelForm):
    """Form for coding question details."""
    allowed_languages = forms.MultipleChoiceField(
        choices=CodingQuestion.LANGUAGE_CHOICES,
        widget=forms.SelectMultiple(attrs={'class': 'form-input', 'id': 'allowed-languages-select'}),
        required=False,
        initial=[lang[0] for lang in CodingQuestion.LANGUAGE_CHOICES]
    )

    class Meta:
        model = CodingQuestion
        fields = [
            'problem_statement',
            'time_limit_seconds', 'memory_limit_mb', 'allowed_languages'
        ]
        widgets = {
            'problem_statement': forms.Textarea(attrs={
                'class': 'form-input code-textarea',
                'rows': 16,
                'placeholder': 'Write the full problem here. HTML is supported.\n\nInclude: problem description, input/output format, constraints, examples, explanation, etc.',
            }),
            'time_limit_seconds': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.5', 'min': '0.5', 'max': '30'}),
            'memory_limit_mb': forms.NumberInput(attrs={'class': 'form-input', 'min': '16', 'max': '1024'}),
        }
        labels = {
            'problem_statement': 'Problem description',
        }
        help_texts = {
            'problem_statement': 'Write everything here: problem statement, input/output format, constraints, examples, and explanation. Supports HTML.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for lang_code, lang_name in CodingQuestion.LANGUAGE_CHOICES:
            self.fields[f'{lang_code}_starter_code'] = forms.CharField(
                widget=forms.Textarea(attrs={'class': 'form-input code-textarea', 'rows': 6}),
                required=False, label=f"{lang_name} Starter Code"
            )
            self.fields[f'{lang_code}_driver_code'] = forms.CharField(
                widget=forms.Textarea(attrs={'class': 'form-input code-textarea', 'rows': 6}),
                required=False, label=f"{lang_name} Driver Code"
            )
            if self.instance and self.instance.pk:
                self.initial[f'{lang_code}_starter_code'] = self.instance.starter_code.get(lang_code, '')
                self.initial[f'{lang_code}_driver_code'] = self.instance.driver_code.get(lang_code, '')

    def save(self, commit=True):
        instance = super().save(commit=False)
        for lang_code, _ in CodingQuestion.LANGUAGE_CHOICES:
            instance.starter_code[lang_code] = self.cleaned_data.get(f'{lang_code}_starter_code', '')
            instance.driver_code[lang_code] = self.cleaned_data.get(f'{lang_code}_driver_code', '')
        if commit:
            instance.save()
        return instance


class TestCaseForm(forms.ModelForm):
    """Form for adding test cases."""

    class Meta:
        model = TestCase
        fields = ['input_data', 'expected_output', 'is_hidden', 'weight', 'description']
        widgets = {
            'input_data': forms.Textarea(attrs={'class': 'form-input code-textarea', 'rows': 4, 'placeholder': 'Input data...'}),
            'expected_output': forms.Textarea(attrs={'class': 'form-input code-textarea', 'rows': 4, 'placeholder': 'Expected output...'}),
            'weight': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.5'}),
            'description': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Brief description'}),
        }


class MCQQuestionForm(forms.ModelForm):
    """Form for MCQ question details."""

    class Meta:
        model = MCQQuestion
        fields = ['question_text', 'explanation']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            'explanation': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Explanation shown after contest'}),
        }


MCQOptionFormSet = None  # Options are handled dynamically via JS


class SubjectiveQuestionForm(forms.ModelForm):
    """Form for subjective question details."""

    class Meta:
        model = SubjectiveQuestion
        fields = ['question_text', 'guidelines', 'max_word_count', 'reference_answer']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            'guidelines': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'max_word_count': forms.NumberInput(attrs={'class': 'form-input'}),
            'reference_answer': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
        }
