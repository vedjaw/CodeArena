# CodeArena

CodeArena is a self-hosted coding assessment platform built for technical hiring teams. It provides the full pipeline from contest creation through candidate evaluation: recruiters compose contests with multiple question types, candidates solve them inside a browser-based IDE, and the platform judges code automatically, tracks integrity in real time, and surfaces ranked results.

The project is intentionally kept as a single deployable Django application. There is no microservice split, no managed SaaS dependency, and no external judging API. Everything runs on your own infrastructure.

---

## What it does

A recruiter creates a contest and adds questions to it. Questions can be coding problems judged against hidden test cases, single or multiple-answer MCQs, or open-ended subjective prompts. The recruiter controls the time window, duration per candidate, visibility (public, password-protected, or invite-only), proctoring settings, and scoring rules.

Candidates access the contest through a browser-based IDE. They write and run code, navigate between questions, and submit before the timer expires. The IDE autosaves drafts every thirty seconds so no work is lost to an accidental refresh. Once a candidate submits code, it is dispatched to a Celery worker for execution and judged against every test case. Scores update immediately and propagate to the leaderboard.

Admins have a system-level view: all users, all contests, all activity. They can deactivate accounts, export reports, and access analytics that recruiters cannot see.

---

## Technical architecture

**Backend:** Django 6.0.5, Python 3.14. The application uses eight internal apps:

- `accounts` handles a custom User model (email-first, no username), role-based access middleware, and activity logging.
- `contests` manages the Contest and ContestSession lifecycle, invitations, and announcements.
- `questions` holds the base Question model plus three specialized subtypes: CodingQuestion (with test cases, starter code, hidden driver code, and per-language execution limits), MCQQuestion (with options), and SubjectiveQuestion (with word limit and grading guidelines).
- `submissions` records every submission attempt, stores per-test-case results as JSON, tracks verdict progression (pending, running, accepted, wrong answer, time limit, runtime error, compilation error, partial), and maintains autosaved drafts separately from final submissions.
- `execution_engine` compiles and runs submitted code. It attempts Docker-based execution first for full isolation, then falls back to a subprocess runner when Docker is unavailable. Both paths respect the per-question time and memory limits defined by the recruiter.
- `proctoring` records violations (tab switches, copy attempts, fullscreen exits, keyboard shortcuts, right-clicks, developer tools), stores webcam snapshots if webcam capture is enabled, and logs granular activity events throughout the session.
- `analytics` builds leaderboards and provides per-question acceptance rates, score distributions, and contest-level statistics for export.
- `api` exposes a Django REST Framework API for contests, submissions, leaderboards, timer state, and violations, consumed by internal JavaScript and available for external integrations.

**Async execution:** Celery with Redis as the broker handles code execution off the request cycle. The worker tries Docker first, falls back to subprocess, and reports the result back through the database. The IDE polls a status endpoint until the verdict is final.

**Database:** SQLite by default. PostgreSQL is supported through environment variables with no code changes.

**Frontend:** Server-rendered Django templates with a custom CSS design system. There is no Node build step and no JavaScript framework. The design system defines a complete token set (surfaces, text scales, lines, signal accent) and ships a dark theme by default with a fully specified light theme. Users toggle between themes using a button available on every page; the preference is stored in localStorage and applied before the first paint to prevent flicker. The IDE layout is a separate CSS file optimized for the full-height cockpit view.

---

## Code execution

The execution engine supports Python, C++ (compiled with g++ at O2), Java, and JavaScript (Node). Each language has a corresponding Docker image. When Docker is available, code runs inside an isolated container with:

- no network access (`--network none`)
- a 256 MB memory limit by default (configurable)
- a CPU limit of one core
- a process limit of 64
- a temporary directory mounted as the only filesystem access

The container is destroyed after every run. If Docker is not reachable, the engine falls back to a subprocess runner that enforces the same time limit through Python's `subprocess.TimeoutExpired`.

For coding questions, recruiters can attach hidden driver code per language. The driver wraps the candidate's solution and handles input parsing and output formatting. When a driver is provided, the engine either inserts the candidate's code at a `{{USER_CODE}}` placeholder or appends it after the solution, depending on the template. This means candidates write clean functions rather than boilerplate main routines.

Scoring supports two modes. In all-or-nothing mode, the full mark is awarded only if every test case passes. In partial scoring mode, each test case carries a weight and the score is proportional to the weighted sum of cases passed divided by the total weight.

---

## Proctoring

Proctoring is optional and configured per contest. When enabled, the platform intercepts browser events: tab or window focus loss, copy and paste attempts, right-clicks, keyboard shortcuts (Ctrl/Cmd + C, V, U, S, P), and fullscreen exits. Each event is reported to the server as a violation record with a type, description, and timestamp.

Recruiters set a maximum violation count. When a candidate reaches the limit, the session is auto-submitted if the contest has that setting enabled. The candidate's violation count is visible in the manage view alongside their score and session status.

If webcam capture is enabled, periodic snapshots are taken and stored. Recruiters can review them alongside violation logs.

---

## Roles

The platform has three roles enforced at both the view and middleware level:

**Admin** has full access to everything. Admins can manage all users, view all contests regardless of creator, access system-wide analytics, and toggle user activation status.

**Recruiter** can create, edit, clone, and delete their own contests. They manage questions, send invitations, post announcements, reset candidate sessions, view analytics for their contests, and export results as CSV or Excel.

**Candidate** can browse available contests, enter active ones, write and submit answers, view their own submission history, and see leaderboards when the recruiter has made them visible.

Email is the authentication identifier. There is no username. Password reset is handled through tokenized links sent by email.

---

## Contest types and visibility

A contest can be public (any registered user can enter), password-protected (candidates supply a password at entry), or private (invite-only, enforced through an email whitelist). Private contests are invisible to users who are not on the list.

Contests go through a state machine: draft, published, ongoing, completed, cancelled. A contest cannot be published unless it has at least one question. The leaderboard can be frozen independently of the contest state, which lets recruiters stop rank updates while the contest is still live.

---

## REST API

A REST API is available under `/api/`. Authentication uses Django session cookies. Key endpoints:

- `GET /api/contests/` and `GET /api/contests/<slug>/` return contest data. Public contests are visible without authentication.
- `GET /api/submissions/` returns the authenticated user's submissions, or all submissions for admins and recruiters.
- `GET /api/leaderboard/<contest_slug>/` returns ranked entries for a contest.
- `GET /api/timer/<contest_slug>/` returns the server-authoritative remaining time and deadline for the authenticated user's session.
- `GET /api/violations/<contest_slug>/` returns violation records for a contest (recruiter and admin only).

Rate limiting is applied: 30 requests per minute for anonymous users, 120 per minute for authenticated users.

---

## Project structure

```
codearena/          Django project configuration, Celery app, URL root
accounts/           Custom user model, authentication views, dashboards
contests/           Contest and session models, contest views
questions/          Question types, test cases, forms
submissions/        Submission recording, code drafts, MCQ and subjective answers
execution_engine/   Docker and subprocess code runners, Celery tasks
proctoring/         Violation tracking, webcam snapshots, activity logs
analytics/          Leaderboard, contest analytics, report export
api/                DRF serializers and viewsets
templates/          Django HTML templates, custom SVG icon sprite
static/css/         main.css (design system), ide.css (IDE cockpit layout)
```

---

## Local setup

**Requirements:** Python 3.10 or later, Redis (for Celery), and optionally Docker (for sandboxed code execution).

```bash
git clone <repository-url>
cd hackerank

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser

python manage.py runserver
```

In a second terminal, start Celery:

```bash
source venv/bin/activate
celery -A codearena worker -l info
```

Redis must be running on `localhost:6379`. If Redis is not available, code execution still works through the synchronous subprocess fallback, but submissions will block the request thread.

To seed a sample contest with real algorithm problems:

```bash
python seed_real_contest.py
```

---

## Configuration

All configurable values are read from environment variables. Sensitive settings have no hardcoded production defaults.

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | insecure dev key | Django secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hosts |
| `DB_ENGINE` | SQLite | Database engine |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | empty | Database connection |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery results |
| `EXECUTION_TIMEOUT` | `10` | Code execution timeout in seconds |
| `EXECUTION_MEMORY_LIMIT` | `256m` | Docker memory limit |
| `DOCKER_IMAGE_PREFIX` | `codearena` | Docker image name prefix |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | empty | SMTP configuration |
| `CORS_ORIGINS` | localhost origins | Allowed CORS origins |

In production, set `DJANGO_DEBUG=False`. The settings file automatically enables HSTS, SSL redirect, secure cookies, and X-Frame-Options deny when debug mode is off.

---

## Design system

The frontend uses a hand-written CSS design system with no external component library and no build tool. All styling is in two files: `static/css/main.css` for the application and `static/css/ide.css` for the IDE layout.

Tokens are defined as CSS custom properties on `:root`. The dark theme is the default. The light theme overrides those properties under `[data-theme="light"]` on the `html` element. A blocking inline script in the document head reads the saved preference from localStorage before the browser paints, so there is no flash of the wrong theme.

Iconography uses a custom SVG sprite. All icons are defined as symbols in `templates/base/icons.html` and referenced with `<use href="#icon-name">`. There are no icon font dependencies and no third-party icon libraries.

The IDE layout is a full-height CSS grid with four independently scrollable panels: a question rail on the left, a problem statement in the center-left, a code editor in the center-right, and a tabbed output console at the bottom. The top bar carries the contest title, a server-synced countdown timer, and the final submission button.

---

## Limitations and known considerations

The subprocess fallback for code execution runs directly on the host machine. In production, always have Docker available and use it as the primary execution path. Without Docker, a candidate could submit code that reads environment variables, accesses the filesystem, or makes network calls.

The platform does not implement a job queue with retry logic for failed executions beyond Celery's built-in two-retry mechanism. If the Celery worker is down when a submission arrives, the task will sit in the Redis queue until the worker restarts.

Webcam snapshot storage is local to the server filesystem. In a production deployment with multiple application servers, use shared storage or an object store for the media root.

The REST API does not yet have JWT authentication. It uses session cookies, which means it works for browser clients but requires additional work for non-browser integrations.
