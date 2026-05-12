"""
Execution Engine - Docker-based code execution
"""
import os
import subprocess
import tempfile
import json
import shutil
from django.conf import settings
from django.utils import timezone

from .executor import LANGUAGE_CONFIG


def run_in_docker(submission, is_run_only=False, custom_input=''):
    """Execute code inside a Docker container for isolation."""
    language = submission.language
    config = LANGUAGE_CONFIG.get(language)

    if not config:
        submission.verdict = 'error'
        submission.compiler_output = f'Unsupported language: {language}'
        submission.save()
        return {'success': False, 'error': 'Unsupported language'}

    # Check if Docker is available
    try:
        subprocess.run(['docker', 'info'], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise RuntimeError('Docker not available')

    # Create temp directory with source code
    tmp_dir = tempfile.mkdtemp(prefix='codearena_docker_')

    try:
        # Write source code
        if language == 'java':
            filename = 'Main.java'
        else:
            filename = f'solution{config["extension"]}'

        # Append hidden driver code if available
        full_code = submission.source_code
        if hasattr(submission.question, 'coding_detail'):
            driver = submission.question.coding_detail.driver_code.get(language, '')
            if driver:
                if '{{USER_CODE}}' in driver:
                    full_code = driver.replace('{{USER_CODE}}', submission.source_code)
                else:
                    full_code = f"{submission.source_code}\n\n{driver}"

        with open(os.path.join(tmp_dir, filename), 'w') as f:
            f.write(full_code)

        # Write input data
        if is_run_only:
            input_data = custom_input
        else:
            # For judging, we handle test cases individually
            from .executor import run_code_sync
            run_code_sync(submission, is_run_only, custom_input)
            return {'success': True}

        with open(os.path.join(tmp_dir, 'input.txt'), 'w') as f:
            f.write(input_data)

        # Build Docker command
        time_limit = 10
        if hasattr(submission.question, 'coding_detail'):
            time_limit = submission.question.coding_detail.time_limit_seconds

        memory_limit = settings.EXECUTION_MEMORY_LIMIT
        docker_image = config['docker_image']

        # Build run script
        if config['compile_cmd']:
            compile_step = config['compile_cmd'].format(
                file=f'/code/{filename}',
                output='/code/solution',
                dir='/code',
            )
            run_step = config['run_cmd'].format(
                file=f'/code/{filename}',
                output='/code/solution',
                dir='/code',
            )
            script = f'cd /code && {compile_step} && {run_step} < /code/input.txt'
        else:
            run_step = config['run_cmd'].format(file=f'/code/{filename}')
            script = f'cd /code && {run_step} < /code/input.txt'

        docker_cmd = [
            'docker', 'run', '--rm',
            '--memory', memory_limit,
            '--cpus', '1',
            '--network', 'none',  # No network access
            '--pids-limit', '64',
            '-v', f'{tmp_dir}:/code:rw',
            docker_image,
            'bash', '-c', script,
        ]

        result = subprocess.run(
            docker_cmd, capture_output=True, text=True,
            timeout=time_limit + 5,
        )

        submission.runtime_output = result.stdout[:10000]
        if result.returncode != 0:
            submission.verdict = 'runtime_error'
            submission.compiler_output = result.stderr[:5000]
        else:
            submission.verdict = 'accepted'

        submission.judged_at = timezone.now()
        submission.save()

        return {'success': True}

    except subprocess.TimeoutExpired:
        submission.verdict = 'time_limit'
        submission.judged_at = timezone.now()
        submission.save()
        return {'success': True}

    except Exception as e:
        raise RuntimeError(f'Docker execution failed: {e}')

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
