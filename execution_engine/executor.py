"""
Execution Engine - Code executor for running code in Docker containers
Falls back to subprocess-based execution when Docker is unavailable.
"""
import os
import subprocess
import tempfile
import time
import shutil
from pathlib import Path
from django.conf import settings
from django.utils import timezone


# Language configurations
LANGUAGE_CONFIG = {
    'python': {
        'extension': '.py',
        'compile_cmd': None,
        'run_cmd': 'python3 {file}',
        'docker_image': 'codearena-python',
    },
    'cpp': {
        'extension': '.cpp',
        'compile_cmd': 'g++ -std=c++17 -O2 -o {output} {file}',
        'run_cmd': '{output}',
        'docker_image': 'codearena-cpp',
    },
    'java': {
        'extension': '.java',
        'compile_cmd': 'javac {file}',
        'run_cmd': 'java -cp {dir} Main',
        'docker_image': 'codearena-java',
    },
    'javascript': {
        'extension': '.js',
        'compile_cmd': None,
        'run_cmd': 'node {file}',
        'docker_image': 'codearena-node',
    },
}


def run_code_sync(submission, is_run_only=False, custom_input=''):
    """
    Execute code synchronously using subprocess (fallback when Docker/Celery unavailable).
    """
    from submissions.models import Submission
    from questions.models import TestCase

    language = submission.language
    source_code = submission.source_code
    config = LANGUAGE_CONFIG.get(language)

    if not config:
        submission.verdict = 'error'
        submission.compiler_output = f'Unsupported language: {language}'
        submission.save()
        return

    submission.verdict = 'running'
    submission.save()

    # Create temporary directory for execution
    tmp_dir = tempfile.mkdtemp(prefix='codearena_')

    try:
        # Write source code to file
        if language == 'java':
            filename = 'Main' + config['extension']
        else:
            filename = 'solution' + config['extension']

        # Append hidden driver code if available
        full_code = source_code
        if hasattr(submission.question, 'coding_detail'):
            driver = submission.question.coding_detail.driver_code.get(language, '')
            if driver:
                if '{{USER_CODE}}' in driver:
                    full_code = driver.replace('{{USER_CODE}}', source_code)
                else:
                    full_code = f"{source_code}\n\n{driver}"

        filepath = os.path.join(tmp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(full_code)

        # Compile if needed
        if config['compile_cmd']:
            compile_cmd = config['compile_cmd'].format(
                file=filepath,
                output=os.path.join(tmp_dir, 'solution'),
                dir=tmp_dir,
            )
            try:
                result = subprocess.run(
                    compile_cmd, shell=True, capture_output=True,
                    text=True, timeout=30, cwd=tmp_dir,
                )
                if result.returncode != 0:
                    submission.verdict = 'compilation_error'
                    submission.compiler_output = result.stderr[:5000]
                    submission.judged_at = timezone.now()
                    submission.save()
                    return
            except subprocess.TimeoutExpired:
                submission.verdict = 'compilation_error'
                submission.compiler_output = 'Compilation timed out'
                submission.judged_at = timezone.now()
                submission.save()
                return

        # Run against test cases or custom input
        if is_run_only:
            # Run with custom input only
            result = _execute_single(config, filepath, tmp_dir, custom_input, submission)
            submission.runtime_output = result.get('stdout', '')
            if result.get('error'):
                submission.verdict = 'runtime_error'
                submission.compiler_output = result.get('stderr', '')
            else:
                submission.verdict = 'accepted'
            submission.execution_time_ms = result.get('time_ms', 0)
            submission.judged_at = timezone.now()
            submission.save()
            return

        # Run against all test cases
        coding_detail = submission.question.coding_detail
        test_cases = coding_detail.test_cases.all().order_by('order')
        time_limit = coding_detail.time_limit_seconds

        total_passed = 0
        total_cases = test_cases.count()
        test_results = []
        max_time = 0
        max_memory = 0
        total_weight = sum(float(tc.weight) for tc in test_cases)

        for tc in test_cases:
            result = _execute_single(
                config, filepath, tmp_dir, tc.input_data, submission, time_limit
            )

            actual_output = result.get('stdout', '').strip()
            expected_output = tc.expected_output.strip()
            passed = actual_output == expected_output

            if passed:
                total_passed += 1

            tc_result = {
                'test_case_id': tc.id,
                'passed': passed,
                'is_hidden': tc.is_hidden,
                'time_ms': result.get('time_ms', 0),
                'error': result.get('error', False),
                'description': tc.description,
            }

            if not tc.is_hidden:
                tc_result['actual_output'] = actual_output[:1000]
                tc_result['expected_output'] = expected_output[:1000]

            if result.get('timeout'):
                tc_result['verdict'] = 'time_limit'
            elif result.get('error'):
                tc_result['verdict'] = 'runtime_error'
            elif passed:
                tc_result['verdict'] = 'accepted'
            else:
                tc_result['verdict'] = 'wrong_answer'

            test_results.append(tc_result)
            max_time = max(max_time, result.get('time_ms', 0))

        # Calculate score
        if submission.question.partial_scoring and total_weight > 0:
            weighted_score = 0
            for i, tc in enumerate(test_cases):
                if test_results[i]['passed']:
                    weighted_score += float(tc.weight)
            score = (weighted_score / total_weight) * float(submission.question.marks)
        else:
            if total_passed == total_cases:
                score = float(submission.question.marks)
            else:
                score = 0

        # Determine overall verdict
        if total_passed == total_cases:
            verdict = 'accepted'
        elif any(r.get('verdict') == 'time_limit' for r in test_results):
            verdict = 'time_limit'
        elif any(r.get('verdict') == 'runtime_error' for r in test_results):
            verdict = 'runtime_error'
        elif total_passed > 0 and submission.question.partial_scoring:
            verdict = 'partial'
        else:
            verdict = 'wrong_answer'

        submission.verdict = verdict
        submission.score = score
        submission.passed_test_cases = total_passed
        submission.total_test_cases = total_cases
        submission.test_case_results = test_results
        submission.execution_time_ms = max_time
        submission.judged_at = timezone.now()
        submission.save()

    except Exception as e:
        submission.verdict = 'error'
        submission.compiler_output = str(e)[:5000]
        submission.judged_at = timezone.now()
        submission.save()
    finally:
        # Cleanup
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _execute_single(config, filepath, tmp_dir, input_data, submission, time_limit=10):
    """Execute code once with given input."""
    language = submission.language
    run_cmd = config['run_cmd'].format(
        file=filepath,
        output=os.path.join(tmp_dir, 'solution'),
        dir=tmp_dir,
    )

    start_time = time.time()
    try:
        result = subprocess.run(
            run_cmd, shell=True, capture_output=True, text=True,
            timeout=time_limit, cwd=tmp_dir,
            input=input_data,
        )
        elapsed = (time.time() - start_time) * 1000  # ms

        return {
            'stdout': result.stdout[:10000],
            'stderr': result.stderr[:5000],
            'time_ms': round(elapsed, 2),
            'error': result.returncode != 0,
            'timeout': False,
        }
    except subprocess.TimeoutExpired:
        elapsed = (time.time() - start_time) * 1000
        return {
            'stdout': '',
            'stderr': 'Time Limit Exceeded',
            'time_ms': round(elapsed, 2),
            'error': True,
            'timeout': True,
        }
    except Exception as e:
        return {
            'stdout': '',
            'stderr': str(e),
            'time_ms': 0,
            'error': True,
            'timeout': False,
        }
