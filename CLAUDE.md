# Request Tracker: Project Context for Claude Code

Read this first in every session. It holds the goal, environment, architecture, rules, and current phase status.

## 1. Goal

Build a **Request Tracker** MVP with **Angular (PrimeNG) + Django REST Framework + MySQL**. It is a learning and reference project: a small but complete internal system covering the patterns a real production system with the same stack needs. The finished version will be tagged and used as a blueprint.

The developer knows PHP (CodeIgniter 4, Laravel) and Vue 3, and is new to Django and Angular. Briefly explain conventions that differ from Laravel/CodeIgniter/Vue. Work in small vertical slices, one phase at a time, and stop at each checkpoint.

## 2. Environment (Windows)

| Item | Value |
|---|---|
| OS / shell | Windows 11, **Git Bash (MINGW64)**. Activate venv with `source venv/Scripts/activate`. Use `winpty` for interactive prompts |
| Python | 3.14.8 in `backend/venv`. Older Pythons exist on the machine, so **always call `backend/venv/Scripts/python.exe`** |
| Django | `>=5.2.8,<5.3` |
| Node / npm | 22.21.0 / 11.21.0 |
| Angular CLI | 21.x. Modern Angular only (standalone components, signals, `inject()`, functional guards/interceptors, `@if`/`@for`) |
| UI library | **PrimeNG** with the Aura theme (`primeng`, `@primeuix/themes`, `primeicons`) |
| MySQL | 8.0.36, database `request_tracker`, user `rt_user`, driver **mysqlclient** (PyMySQL must not be installed) |
| Git | 2.39.2, single repo at the project root (monorepo) |

Project root: `C:\Vincent\Learning\request-tracker`

## 3. Phase status

| Phase | Scope | Status |
|---|---|---|
| 1. Foundation | Settings split (base/dev/prod), apps, custom User + Department, health endpoint, first migrate on MySQL | Done |
| 2. Auth slice | JWT login/refresh, `/me/`, Angular scaffold, PrimeNG, login, interceptor, guard, layout, dashboard placeholder | Done (revised to use PrimeNG) |
| 3. Core CRUD | Category + Request models, role-scoped API, list and form pages | Next |
| 4. Workflow | Submit/approve/reject, StatusHistory, detail page | Planned |
| 5. Extras | Comments, attachments, filters polish | Planned |
| 6. Polish | Dashboard summary, tests, OpenAPI, error/loading states | Planned |
| 7. Deploy | Gunicorn, Nginx, MySQL, `check --deploy`, `ng build` | Planned |

Update this table at the end of each phase.

## 4. Rules for Claude Code

- Show a short plan first and **wait for approval** before changing files.
- Do one phase at a time. Stop at the checkpoint and report each item as pass/fail.
- Use `backend/venv/Scripts/python.exe` for Python, pip, and `manage.py`.
- **Never read, print, or commit `backend/.env`.** Keep `.env.example` current with dummy values.
- `AUTH_USER_MODEL = "accounts.User"` is already set. Never change it.
- Do not drop or reset the database without asking.
- Do not use `--force` or `--legacy-peer-deps` for npm without asking.
- Do not commit unless asked. Suggest a commit message.
- Keep views thin. Business rules (status transitions, ownership rules) go in `services.py`.
- Write tests for permissions and workflow rules.
- After each step, explain in 1-2 sentences what it does, with the Laravel/CodeIgniter/Vue equivalent where one exists.
- Check the official docs for the installed version before using a PrimeNG or Angular API, since names change between major versions.

## 5. Architecture

```
request-tracker/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                  # not committed
│   ├── .env.example
│   ├── config/
│   │   ├── settings/         # base.py, dev.py, prod.py
│   │   ├── urls.py, wsgi.py, asgi.py
│   └── apps/
│       ├── accounts/         # custom User, Department, /me/
│       ├── core/             # TimeStampedModel, health endpoint, utilities
│       └── service_requests/ # request workflow (not "requests", to avoid clashing with the library)
├── frontend/
│   └── src/
│       ├── environments/     # apiUrl per environment
│       └── app/
│           ├── core/         # auth service, guards, interceptors
│           ├── shared/       # reusable components, pipes, models (Paginated<T>)
│           ├── layouts/      # main layout (Menubar/Toolbar)
│           └── features/     # auth, dashboard, requests, admin
├── docs/                     # notes.md ("how this works" entries), ERD, API notes
├── CLAUDE.md
└── README.md
```

Conventions:
- One Django app and one Angular feature folder per business module, with matching names.
- API under `/api/v1/`, plural nouns, trailing slashes. Pagination `{count, next, previous, results}`. Error shape `{detail, errors: {field: [..]}}`.
- A feature never imports from another feature. Shared things go in `shared/`. Features are lazy-loaded. HTTP calls live in services, not components.
- No hardcoded API URLs; use `environment.apiUrl`.
- Commit migrations. Never commit `.env`, `venv/`, `node_modules/`, `.angular/`, `dist/`, `db.sqlite3`.
- Backend module pattern: model → serializer → viewset (scoped queryset) → router. Frontend module pattern: interface → service → component → route (+ guard).

## 6. Frontend UI library: PrimeNG

- Use PrimeNG (Aura theme via `providePrimeNG`) for all UI: `p-table` with lazy server-side pagination for lists, `p-dialog` / `p-confirmDialog` for confirmations, `p-toast` for notifications, `p-fileupload` for attachments, `p-select`, `p-datepicker`, `p-tag` for status badges, `p-timeline` for status history, `p-card` for panels, Menubar/Toolbar for the layout.
- Install: `npm install primeng @primeuix/themes primeicons` (the older `@primeng/themes` package is outdated).
- Import each PrimeNG component individually in the standalone component that uses it.
- Wrap repeated patterns (status badge, data table, confirm dialog, file uploader) as components under `shared/` instead of repeating them.
- Do not hand-write CSS for things PrimeNG already provides.
- If components render unstyled, check the theme provider in `app.config.ts`.

## 7. Database configuration

`backend/.env` (never commit):

```
SECRET_KEY=replace-with-a-long-random-string
DEBUG=True
DB_NAME=request_tracker
DB_USER=rt_user
DB_PASSWORD=change_me
DB_HOST=127.0.0.1
DB_PORT=3306
```

`base.py` loads it with `django-environ` and defines the MySQL `DATABASES` block with `charset: utf8mb4` and `init_command: SET sql_mode='STRICT_TRANS_TABLES'`. Separate DB variables are used instead of `DATABASE_URL`. Use `127.0.0.1`, not `localhost`.

MySQL notes: migrations are not transactional (back up before production migrations); `utf8mb4_unicode_ci` is case-insensitive; keep indexed `CharField` lengths at 255 or less; InnoDB only. MySQL 8.0 is past end of life, so use 8.4 LTS for the real system.

## 8. Request Tracker specification

Staff submit requests (equipment, leave, document, repair), reviewers approve or reject, and admins manage users, departments, and categories.

### Roles

| Role | Can do |
|---|---|
| Staff | Create requests, edit own drafts, submit, view only their own, comment, upload attachments |
| Reviewer | View requests from their department (not drafts), approve/reject with remarks, comment |
| Admin | Everything, plus manage users, departments, categories |

### Data model

```
User (custom)   role (staff/reviewer/admin), department (FK, optional)   [done]
Department      name                                                      [done]
Category        name (unique), is_active
Request         title, description, category (FK PROTECT), requester (FK PROTECT),
                status, priority, created_at, updated_at
Attachment      request, file, uploaded_by, uploaded_at
Comment         request, author, body, created_at
StatusHistory   request, from_status, to_status, changed_by, remarks, changed_at
```

Status lifecycle: **draft → submitted → in_review → approved / rejected → completed**. Priority: low, medium, high.

Business rules (in `services.py`): cannot submit an empty request; only the requester edits or deletes, and only while draft; a reviewer cannot approve their own request; every transition writes a StatusHistory row; rejecting requires remarks.

### Queryset scoping

- staff: own requests only.
- reviewer: requests whose requester is in the reviewer's department, excluding drafts. A reviewer with no department sees nothing.
- admin: all requests.
- Use `select_related`/`prefetch_related` on list queries.

### Endpoints

```
POST   /api/v1/auth/token/           login (JWT)               [done]
POST   /api/v1/auth/token/refresh/                              [done]
GET    /api/v1/me/                   current user and role      [done]
GET    /api/v1/health/                                          [done]

GET/POST /api/v1/categories/         writes admin-only          [Phase 3]
GET/POST /api/v1/requests/           ?status=&category=&priority=&search=&ordering=&page=   [Phase 3]
GET/PATCH/DELETE /api/v1/requests/{id}/                         [Phase 3]
POST   /api/v1/requests/{id}/submit/  /approve/  /reject/       [Phase 4]
GET    /api/v1/requests/{id}/history/                           [Phase 4]
GET/POST /api/v1/requests/{id}/comments/                        [Phase 5]
POST   /api/v1/requests/{id}/attachments/                       [Phase 5]
GET    /api/v1/dashboard/summary/                               [Phase 6]
GET/POST /api/v1/users/              admin only                 [Phase 6]
```

### Angular pages

Login (done), Dashboard (placeholder done), Request list, Request form, Request detail with comments and history timeline, Admin pages for users, departments, and categories.

## 9. Phase 3 scope (next)

Backend: `apps/service_requests` app (`name = "apps.service_requests"`), Category and Request models (inherit TimeStampedModel, ordering `-created_at`, indexes on status and created_at), serializers (list, detail, write; status and requester are server-set), permissions and scoped queryset, django-filter `FilterSet`, search, ordering, pagination, admin registration, a dev-only idempotent `seed_demo_data` command (refuses to run when DEBUG is False, no hardcoded real password), and permission tests.

Frontend: lazy-loaded `features/requests` with list, new, and edit routes; interfaces and services; PrimeNG Table with lazy pagination, debounced search, status and category filters; a shared `status-badge`; a reactive form with validation (edit only for own drafts); ConfirmDialog delete; Toast for notifications; DRF field errors shown on the form.

Do NOT implement submit/approve/reject, comments, attachments, or StatusHistory in Phase 3.

## 10. Known shortcuts to fix before the real system

- JWT in `localStorage` is exposed to XSS. Prefer httpOnly cookies, or serve Angular and Django on one domain.
- Generate Angular types from the OpenAPI schema (`drf-spectacular`) instead of hand-written interfaces.
- Production: `DEBUG=False`, proper `ALLOWED_HOSTS`, `manage.py check --deploy`, Gunicorn behind Nginx on Linux, HTTPS, Docker Compose, automated DB backups, CI for tests and lint, a staging environment, and the same Python minor version as the server.
- Out of scope for the MVP: email notifications, WebSockets, multi-step approval chains, PDF export.

## 11. Troubleshooting log

| Problem | Cause and fix |
|---|---|
| `python --version` shows an older version | Windows runs the first `python.exe` on PATH. Create the venv with `py -3.14 -m venv venv`; inside a venv, `python` is the venv's version |
| `ERR_CONNECTION_REFUSED` on localhost:8000 | `runserver` is not running or crashed. Start it in your own terminal and read the output |
| `mysql` says `using password: NO` in Git Bash | Retry or use `winpty mysql -u root -p` |
| `ModuleNotFoundError: pymysql` | `config/__init__.py` imports PyMySQL. mysqlclient is the driver; keep `__init__.py` empty |
| `InconsistentMigrationHistory` | `migrate` ran before `AUTH_USER_MODEL` was set. Drop and recreate the DB, then redo migrations |
| `ModuleNotFoundError: apps.accounts` | Missing `apps/__init__.py`, or `name` in `apps.py` is not `"apps.accounts"` |
| `ImproperlyConfigured: SECRET_KEY` | `.env` missing or not in `backend/` next to `manage.py` |
| CORS error in the browser | `CORS_ALLOWED_ORIGINS` must contain `http://localhost:4200` with no trailing slash; `CorsMiddleware` near the top |
| PrimeNG components unstyled | Theme provider missing in `app.config.ts`, or wrong package (`@primeuix/themes` vs old `@primeng/themes`) |
| `createsuperuser` users have role staff | Set `role = admin` in the Django admin for admin accounts |
| Port in use | `python manage.py runserver 8001` or `ng serve --port 4201` |

## 12. Daily workflow

```
Terminal 1:  cd backend  → source venv/Scripts/activate → python manage.py runserver
Terminal 2:  cd frontend → ng serve
```

Claude Code cannot leave servers running, and interactive commands such as `createsuperuser` must be run by the developer in their own terminal.