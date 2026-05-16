"""
Questions Views - Question CRUD, test case management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
import json

from .models import Question, CodingQuestion, TestCase, MCQQuestion, MCQOption, SubjectiveQuestion
from .forms import QuestionForm, CodingQuestionForm, TestCaseForm, MCQQuestionForm, MCQOptionFormSet, SubjectiveQuestionForm
from contests.models import Contest
from accounts.decorators import recruiter_or_admin_required


def _type_form_detail_bound_fields(question, type_form):
    """Fields for the type-specific section (excludes coding language blocks shown in META)."""
    if not type_form:
        return None
    if question.question_type == 'coding':
        skip = {'allowed_languages'}
        for code, _ in CodingQuestion.LANGUAGE_CHOICES:
            skip.add(f'{code}_starter_code')
            skip.add(f'{code}_driver_code')
        return [type_form[name] for name in type_form.fields if name not in skip]
    return [type_form[name] for name in type_form.fields]


@login_required
@recruiter_or_admin_required
def question_create(request, contest_slug):
    """Create a new question for a contest."""
    contest = get_object_or_404(Contest, slug=contest_slug)
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    question_type = request.GET.get('type', 'coding')

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.contest = contest
            question.created_by = request.user
            question.order = contest.questions.count() + 1
            question.save()

            # Handle type-specific data
            if question.question_type == 'coding':
                coding_form = CodingQuestionForm(request.POST)
                if coding_form.is_valid():
                    coding = coding_form.save(commit=False)
                    coding.question = question
                    
                    if not coding.allowed_languages:
                        coding.allowed_languages = [lang[0] for lang in CodingQuestion.LANGUAGE_CHOICES]
                    coding.save()
                    messages.success(request, f'Coding question "{question.title}" created!')
                    return redirect('questions:edit', pk=question.pk)
                else:
                    question.delete()
                    messages.error(request, 'Please fix the errors below.')

            elif question.question_type in ('mcq_single', 'mcq_multiple'):
                mcq_form = MCQQuestionForm(request.POST)
                if mcq_form.is_valid():
                    mcq = mcq_form.save(commit=False)
                    mcq.question = question
                    mcq.save()
                    # Parse options from POST data
                    _save_mcq_options(request, mcq)
                    messages.success(request, f'MCQ question "{question.title}" created!')
                    return redirect('contests:manage', slug=contest_slug)
                else:
                    question.delete()

            elif question.question_type == 'subjective':
                sub_form = SubjectiveQuestionForm(request.POST)
                if sub_form.is_valid():
                    sub = sub_form.save(commit=False)
                    sub.question = question
                    sub.save()
                    messages.success(request, f'Subjective question "{question.title}" created!')
                    return redirect('contests:manage', slug=contest_slug)
                else:
                    question.delete()

            return redirect('contests:manage', slug=contest_slug)
    else:
        form = QuestionForm(initial={'question_type': question_type})

    has_previous_coding = False
    previous_languages = []
    
    last_coding = contest.questions.filter(question_type='coding').order_by('-order').first()
    if last_coding and hasattr(last_coding, 'coding_detail'):
        has_previous_coding = True
        previous_languages = last_coding.coding_detail.allowed_languages

    context = {
        'form': form,
        'contest': contest,
        'question_type': question_type,
        'coding_form': CodingQuestionForm(),
        'mcq_form': MCQQuestionForm(),
        'subjective_form': SubjectiveQuestionForm(),
        'has_previous_coding': has_previous_coding,
        'previous_languages_json': json.dumps(previous_languages),
    }
    return render(request, 'questions/create.html', context)


@login_required
@recruiter_or_admin_required
def question_edit(request, pk):
    """Edit an existing question."""
    question = get_object_or_404(Question, pk=pk)
    contest = question.contest
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    type_form = None
    test_cases = []

    if question.question_type == 'coding':
        coding, _ = CodingQuestion.objects.get_or_create(question=question)
        test_cases = coding.test_cases.all().order_by('order')
        if request.method == 'POST':
            form = QuestionForm(request.POST, instance=question)
            type_form = CodingQuestionForm(request.POST, instance=coding)
            if form.is_valid() and type_form.is_valid():
                form.save()
                type_form.save()
                messages.success(request, 'Question updated!')
                return redirect('questions:edit', pk=question.pk)
        else:
            form = QuestionForm(instance=question)
            type_form = CodingQuestionForm(instance=coding)

    elif question.question_type in ('mcq_single', 'mcq_multiple'):
        mcq, _ = MCQQuestion.objects.get_or_create(question=question)
        if request.method == 'POST':
            form = QuestionForm(request.POST, instance=question)
            type_form = MCQQuestionForm(request.POST, instance=mcq)
            if form.is_valid() and type_form.is_valid():
                form.save()
                type_form.save()
                _save_mcq_options(request, mcq)
                messages.success(request, 'Question updated!')
                return redirect('questions:edit', pk=question.pk)
        else:
            form = QuestionForm(instance=question)
            type_form = MCQQuestionForm(instance=mcq)

    elif question.question_type == 'subjective':
        sub, _ = SubjectiveQuestion.objects.get_or_create(question=question)
        if request.method == 'POST':
            form = QuestionForm(request.POST, instance=question)
            type_form = SubjectiveQuestionForm(request.POST, instance=sub)
            if form.is_valid() and type_form.is_valid():
                form.save()
                type_form.save()
                messages.success(request, 'Question updated!')
                return redirect('contests:manage', slug=contest.slug)
        else:
            form = QuestionForm(instance=question)
            type_form = SubjectiveQuestionForm(instance=sub)
    else:
        form = QuestionForm(instance=question)

    context = {
        'form': form,
        'type_form': type_form,
        'coding_form': type_form if question.question_type == 'coding' else None,
        'type_form_detail_fields': _type_form_detail_bound_fields(question, type_form),
        'question': question,
        'contest': contest,
        'test_cases': test_cases,
        'test_case_form': TestCaseForm(),
    }
    return render(request, 'questions/edit.html', context)


@login_required
@require_POST
def question_delete(request, pk):
    """Delete a question."""
    question = get_object_or_404(Question, pk=pk)
    contest = question.contest
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    question.delete()
    messages.success(request, 'Question deleted.')
    return redirect('contests:manage', slug=contest.slug)


# ─── Test Case Management ───────────────────────────────────────────────────────

@login_required
@require_POST
def testcase_add(request, question_pk):
    """Add a test case to a coding question."""
    question = get_object_or_404(Question, pk=question_pk, question_type='coding')
    if question.contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    coding = get_object_or_404(CodingQuestion, question=question)
    form = TestCaseForm(request.POST)
    if form.is_valid():
        tc = form.save(commit=False)
        tc.coding_question = coding
        tc.order = coding.test_cases.count() + 1
        tc.save()
        messages.success(request, 'Test case added.')
    else:
        messages.error(request, 'Invalid test case data.')

    return redirect('questions:edit', pk=question_pk)


@login_required
@require_POST
def testcase_delete(request, pk):
    """Delete a test case."""
    tc = get_object_or_404(TestCase, pk=pk)
    question_pk = tc.coding_question.question.pk
    contest = tc.coding_question.question.contest
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    tc.delete()
    messages.success(request, 'Test case deleted.')
    return redirect('questions:edit', pk=question_pk)


@login_required
@recruiter_or_admin_required
def testcase_edit(request, pk):
    """Edit an existing test case (input, output, visibility, weight, description)."""
    tc = get_object_or_404(TestCase, pk=pk)
    question = tc.coding_question.question
    contest = question.contest
    if contest.created_by != request.user and not request.user.is_admin:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = TestCaseForm(request.POST, instance=tc)
        if form.is_valid():
            form.save()
            messages.success(request, 'Test case updated.')
            return redirect('questions:edit', pk=question.pk)
        messages.error(request, 'Please fix the errors below.')
    else:
        form = TestCaseForm(instance=tc)

    return render(
        request,
        'questions/testcase_edit.html',
        {
            'form': form,
            'testcase': tc,
            'question': question,
            'contest': contest,
        },
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────────

def _save_mcq_options(request, mcq):
    """Parse and save MCQ options from POST data."""
    # Delete existing options
    mcq.options.all().delete()

    # Parse options from numbered POST fields
    i = 0
    while True:
        option_text = request.POST.get(f'option_text_{i}')
        if option_text is None:
            break
        if option_text.strip():
            is_correct = request.POST.get(f'option_correct_{i}') == 'on'
            MCQOption.objects.create(
                mcq_question=mcq,
                option_text=option_text.strip(),
                is_correct=is_correct,
                order=i,
            )
        i += 1
