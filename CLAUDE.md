# Request Tracker: Project Context for Claude Code

This file summarizes the planning and setup conversation so far. Read it first, then continue from **"Current state"** and **"Next steps"**.

## 1. Goal

Build a **Request Tracker** MVP with **Angular + Django (DRF) + MySQL**. It is a learning/reference project: a small but complete internal system that covers the concepts needed for a real production system with the same stack. The finished version will be tagged and used as a blueprint for the real system.

The developer knows PHP (CodeIgniter 4, Laravel), Vue 3 and SQL, is refreshing Python, and is new to Django and Angular. Explain Django/Angular conventions briefly where they differ from Laravel/CodeIgniter/Vue. Prefer working vertical slices, committing after each phase.

## 2. Environment (Windows)

| Item | Value |
|---|---|
| OS | Windows 11 (x64) |
| Shell | **Git Bash (MINGW64)** in VS Code. Activate venv with `source venv/Scripts/activate`. Use `winpty` for interactive prompts (e.g. `winpty mysql -u root -p`) |
| Python | 3.14.8, created with `py -3.14 -m venv venv`. Other installs exist (3.10, 3.11, 3.13). Plain `python` outside a venv may resolve to an older one, so always use the venv |
| Django | `>=5.2.8,<5.3` (5.2.8 is the first 5.2 release supporting Python 3.14) |
| Node | 22.21.0 (LTS) |
| npm | 11.21.0 |
| Angular CLI | 21.2.26 (use standalone components, signals, `@for`/`@if` control flow) |
| Git | 2.39.2 |
| MySQL | 8.0.36 Community Server (Django 5.2 needs 8.0.11+) |
| MySQL driver | **mysqlclient 2.3.0** (installed fine on 3.14). PyMySQL was installed during troubleshooting and should be removed |
| Editor | VS Code (Python, Pylance, Angular Language Service, ESLint, Prettier). Interpreter: `backend/venv/Scripts/python.exe` |

Project root: `C:\Vincent\Learning\request-tracker`

## 3. Current state

**Done**
- Tools installed and verified (Python 3.14.8, Node, Angular CLI, Git, MySQL).
- Project folder created with `git init`, `backend/` and `docs/`.
- Backend venv created in `backend/venv`; Django 5.2.x plus packages installed:
  `django`, `djangorestframework`, `django-cors-headers`, `djangorestframework-simplejwt`, `django-environ`, `drf-spectacular`, `django-filter`, `mysqlclient`.
- `django-admin startproject config .` run inside `backend/`, so `manage.py` and `config/` sit together.
- Django welcome page confirmed working on SQLite before the switch.
- MySQL database `request_tracker` (utf8mb4, `utf8mb4_unicode_ci`) and user `rt_user` created with grants on `request_tracker.*` and `test_request_tracker.*`.
- `backend/.env` created with `SECRET_KEY`, `DEBUG`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=127.0.0.1`, `DB_PORT=3306`.
- `config/settings.py` reads `.env` via `django-environ` and uses the MySQL `DATABASES` block (below).
- Connection test passed: `MySQL connected`.

**Not done yet**
- **No `migrate` has been run against MySQL.** Keep it that way until `AUTH_USER_MODEL` is set (see Section 6). If a migrate was run by accident, drop and recreate the database.
- Cleanup pending: remove PyMySQL (`pip uninstall pymysql -y`), make `config/__init__.py` empty, then `pip freeze > requirements.txt`.
- Angular frontend not created yet (`ng new frontend --routing --style=scss` from the project root, answer **No** to SSR).
- Settings are still a single `settings.py`. The developer was asked whether to split into `base/dev/prod` and the recommendation was to split now.
- Nothing committed for the MySQL config yet.

## 4. Current database configuration

`backend/.env` (never commit; keep a `.env.example` with dummy values):

```
SECRET_KEY=replace-with-a-long-random-string
DEBUG=True
DB_NAME=request_tracker
DB_USER=rt_user
DB_PASSWORD=change_me
DB_HOST=127.0.0.1
DB_PORT=3306
```

`config/settings.py` (relevant parts):

```python
import environ

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

Separate DB variables are used instead of `DATABASE_URL` so special characters in passwords don't break parsing.

Connection test:

```bash
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('MySQL connected')"
```

If the settings are split into a package, `BASE_DIR` becomes `Path(__file__).resolve().parent.parent.parent`.

## 5. Target architecture

```
request-tracker/
├── backend/                  # Django + DRF
│   ├── manage.py
│   ├── requirements.txt      # (later: requirements/base.txt, dev.txt, prod.txt)
│   ├── .env                  # not committed
│   ├── .env.example          # committed
│   ├── config/
│   │   ├── settings/         # base.py, dev.py, prod.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── apps/
│       ├── accounts/         # custom User, Department, roles, auth/me
│       ├── core/             # TimeStampedModel, pagination, health, utils
│       └── service_requests/ # business module (not `requests`, to avoid clashing with the library)
│           ├── models.py, serializers.py, views.py, urls.py
│           ├── permissions.py, filters.py, services.py, admin.py
│           └── tests/
├── frontend/                 # Angular
│   └── src/
│       ├── environments/     # environment.ts (apiUrl), environment.prod.ts
│       └── app/
│           ├── app.routes.ts, app.config.ts
│           ├── core/         # auth service, guards, interceptors, api services
│           ├── shared/       # reusable components, pipes, models (Paginated<T>, ApiError)
│           ├── layouts/      # main layout, auth layout
│           └── features/     # auth/, dashboard/, requests/, admin/
├── docs/
├── docker-compose.yml        # later, at staging time
├── .gitignore
└── README.md
```

Conventions:
- One Django app and one Angular feature folder per business module, with matching names.
- Thin views; business rules (status transitions) live in `services.py`.
- Versioned API under `/api/v1/`, plural nouns, trailing slashes (Django expects them).
- Pagination shape: `{count, next, previous, results}`. One consistent error shape: `{detail, errors: {field: [..]}}`.
- Angular: a feature never imports from another feature; shared things go in `shared/`. Lazy-load features with `loadChildren`. Services own HTTP calls.
- Commit migrations; never commit `.env`, `venv/`, `node_modules/`, `.angular/`, `dist/`, `db.sqlite3`.
- Use `ruff` or `black` for Python, ESLint + Prettier for Angular.

`.gitignore`:

```
venv/
__pycache__/
*.pyc
.env
db.sqlite3
node_modules/
dist/
.angular/
.vscode/
Thumbs.db
.DS_Store
```

## 6. Critical rule: custom user before first migrate

Set `AUTH_USER_MODEL = "accounts.User"` **before** the first `migrate` on the database. Changing it later is painful.

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class User(AbstractUser):
    class Role(models.TextChoices):
        STAFF = "staff", "Staff"
        REVIEWER = "reviewer", "Reviewer"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    department = models.ForeignKey(
        Department, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="users",
    )
```

```python
# apps/core/models.py
from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
```

App configs must use the dotted name, for example `name = "apps.accounts"` and `name = "apps.core"`, and `apps/__init__.py` must exist. Register them in `INSTALLED_APPS` as `"apps.accounts"` and `"apps.core"`.

Admin for the custom user:

```python
# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Department

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Org info", {"fields": ("role", "department")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Org info", {"fields": ("role", "department")}),)
    list_display = ("username", "email", "role", "department", "is_active")
    list_filter = ("role", "department", "is_active")

admin.site.register(Department)
```

Settings additions for the MVP:

```python
AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS += [
    "rest_framework", "corsheaders", "django_filters", "drf_spectacular",
    "apps.accounts", "apps.core",
]
# CorsMiddleware must be near the top of MIDDLEWARE
CORS_ALLOWED_ORIGINS = ["http://localhost:4200"]   # dev only

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
TIME_ZONE = "Asia/Manila"
USE_TZ = True
```

Health endpoint (`/api/v1/health/` returns `{"status": "ok"}`) in `apps/core/views.py`, routed in `config/urls.py` alongside `admin/`.

Then:

```bash
python manage.py makemigrations accounts core
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Checkpoint: the health URL returns ok, and `/admin/` lets you create a Department and users with roles.

## 7. Request Tracker specification

Staff submit requests (equipment, leave, document, repair); reviewers approve or reject; admins manage users, departments and categories.

### Roles

| Role | Can do |
|---|---|
| Staff | Create requests, edit drafts, submit, view only their own, comment, upload attachments |
| Reviewer | See requests for their department, approve/reject with remarks, comment |
| Admin | Everything, plus manage users, departments, categories |

### Data model

```
User (custom)   role, department (FK), is_active
Department      name
Category        name, is_active
Request         title, description, category (FK), requester (FK User),
                status, priority, created_at, updated_at
Attachment      request (FK), file, uploaded_by, uploaded_at
Comment         request (FK), author (FK), body, created_at
StatusHistory   request (FK), from_status, to_status, changed_by, remarks, changed_at   (audit trail)
```

Status lifecycle: **Draft → Submitted → In Review → Approved / Rejected → Completed**.

Business rules to enforce in `services.py`: cannot submit an empty request; only the requester edits a draft; a reviewer cannot approve their own request; every transition writes a `StatusHistory` row; rejecting requires remarks.

### Endpoints

```
POST   /api/v1/auth/token/             login (JWT)
POST   /api/v1/auth/token/refresh/
GET    /api/v1/me/                     current user and role

GET    /api/v1/requests/               ?status=&category=&search=&ordering=&page=
POST   /api/v1/requests/
GET    /api/v1/requests/{id}/
PATCH  /api/v1/requests/{id}/
POST   /api/v1/requests/{id}/submit/
POST   /api/v1/requests/{id}/approve/
POST   /api/v1/requests/{id}/reject/
GET    /api/v1/requests/{id}/history/
GET/POST /api/v1/requests/{id}/comments/
POST   /api/v1/requests/{id}/attachments/

GET    /api/v1/dashboard/summary/
GET/POST /api/v1/categories/           admin only
GET/POST /api/v1/users/                admin only
```

Queryset scoping in `get_queryset()`: staff sees own requests; reviewer sees requests in their department; admin sees all. Use `select_related`/`prefetch_related` on list queries. Attachments need size and type limits.

### Angular pages

1. Login
2. Dashboard (counts by status, recent requests)
3. Request list (filters, search, pagination)
4. Request form (create/edit draft, attachments)
5. Request detail (info, comments, history timeline, approve/reject buttons)
6. Admin: users, departments, categories

### Concepts the MVP should cover

**Django/DRF:** custom user and roles, models and relationships, migrations, ModelSerializer and nested serializers, ViewSets and routers, custom actions, role and object-level permissions, queryset scoping, validation, filtering/search/ordering/pagination, file uploads, services layer, admin site, JWT auth, tests (`pytest-django`), N+1 avoidance, OpenAPI via `drf-spectacular`.

**Angular:** routing and lazy loading, auth and role guards, interceptors (attach token, 401 refresh, global error toast), services and DI, reactive forms with validation, Observables (`switchMap`, `async` pipe), signals, reusable components (data table, status badge, confirm dialog, file uploader), pagination and filter UI, file upload with progress, role-based UI, environment config, loading/empty/error states.

### Build phases

| Phase | Backend | Frontend |
|---|---|---|
| 1. Foundation | Settings split, custom user, roles, health endpoint | `ng new`, folder structure, environments |
| 2. Auth slice | JWT login, `/me/` | Login page, interceptor, auth guard |
| 3. Core CRUD | Category and Request models, serializer, viewset, permissions | List and form pages |
| 4. Workflow | Submit/approve/reject actions, StatusHistory | Detail page, action buttons, role guard |
| 5. Extras | Comments, attachments, filters, pagination | Comment box, uploader, filter bar |
| 6. Polish | Dashboard summary, tests, OpenAPI | Dashboard, error handling, loading states |
| 7. Deploy | Gunicorn, Nginx, MySQL, `check --deploy` | `ng build`, serve static files |

Phases 1 to 4 give a working vertical slice; 5 to 7 make it production-shaped. Out of scope for the MVP: email notifications, WebSockets, multi-step approval chains, PDF export (extension exercises later).

## 8. Reference patterns

**Django module pattern:** model → serializer → viewset (scoped queryset) → router.
**Angular module pattern:** interface → service (HTTP) → component → route (+ guard).

A half-day "Task Notes" blueprint was also sketched (one `Task` model, JWT login, list/add/toggle/delete) to prove the loop. The Request Tracker supersedes it, but its pieces are the same:
- Interceptor attaches `Authorization: Bearer <access>` from storage.
- `AuthService.login()` posts to `/api/v1/auth/token/` and stores the token; `authGuard` redirects to `/login`.
- `TaskService`-style services wrap `HttpClient` with typed interfaces.

## 9. Known shortcuts to fix before the real system

- JWT in `localStorage` is exposed to XSS. Prefer httpOnly cookies in production, or serve Angular and Django on one domain.
- Add a 401 interceptor with refresh-token handling.
- Move API URLs to `environment.ts` (no hardcoded hosts).
- Generate Angular types from the OpenAPI schema (`drf-spectacular` + `ng-openapi-gen` or `openapi-typescript`).
- MySQL notes: migrations are not transactional (back up before production migrations); `utf8mb4_unicode_ci` is case-insensitive; keep indexed `CharField` lengths at 255 or less; use InnoDB. MySQL 8.0 is past end of life (April 2026), so use 8.4 LTS for the real system.
- Production: `DEBUG=False`, proper `ALLOWED_HOSTS`, `manage.py check --deploy`, Gunicorn behind Nginx on Linux, Docker Compose, automated DB backups, CI running tests and lint, a staging environment. The server must run the same Python minor version as local.

## 10. Next steps (do in order)

1. **Cleanup:** make `config/__init__.py` empty, `pip uninstall pymysql -y`, `pip freeze > requirements.txt`, check `git status` (no `.env` or `venv/`), commit.
2. **Split settings** into `config/settings/{base,dev,prod}.py`. Fix `BASE_DIR`, update `DJANGO_SETTINGS_MODULE` in `manage.py`, `wsgi.py` and `asgi.py` to `config.settings.dev`. Keep the MySQL `DATABASES` block and `.env` variables.
3. **Create apps:** `apps/__init__.py`, then `python manage.py startapp accounts apps/accounts` and `core` (create the target folders first). Fix each `apps.py` `name`.
4. **Custom user + Department + TimeStampedModel**, set `AUTH_USER_MODEL`, then `makemigrations` and the first `migrate` on MySQL. Create a superuser. Add the health endpoint.
5. **Verify checkpoint**, then commit: `Phase 1: settings split, custom user, health endpoint`.
6. **Phase 2:** JWT login, `/api/v1/me/`, then scaffold Angular (`ng new frontend --routing --style=scss`, No SSR) with environments, login page, auth interceptor and guard. Confirm CORS between `:4200` and `:8000`.
7. Continue with Phases 3 to 7 above, committing after each phase and keeping short "how I did X" notes in `docs/notes.md`.

## 11. Troubleshooting log

| Problem | Cause and fix |
|---|---|
| `python --version` showed 3.10 or 3.11 after installing 3.14 | Windows runs the first `python.exe` on PATH. Use `py -3.14 -m venv venv`. Inside an active venv, `python` is always the venv's version |
| `ng` blocked in PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Command Prompt |
| `mysql` login: `Access denied (using password: NO)` | Git Bash did not register the password prompt. Retry, or use `winpty mysql -u root -p` |
| `ModuleNotFoundError: No module named 'pymysql'` | `config/__init__.py` imported PyMySQL that was not installed. mysqlclient works, so leave `__init__.py` empty and use only one driver |
| `InconsistentMigrationHistory` | `migrate` ran before `AUTH_USER_MODEL` was set. Drop and recreate the DB, delete migration files, redo |
| `ModuleNotFoundError: apps.accounts` | Missing `apps/__init__.py`, or `name` in `apps.py` is not `"apps.accounts"` |
| `No module named 'config.settings'` | Missing `config/settings/__init__.py` |
| `ImproperlyConfigured: SECRET_KEY` | `.env` missing or not in `backend/` next to `manage.py` |
| CORS error in browser | Check `CORS_ALLOWED_ORIGINS` has no trailing slash and `CorsMiddleware` is near the top |
| `Access denied for user 'rt_user'` | Password in `.env` does not match MySQL. Use `127.0.0.1`, not `localhost` |
| Port in use | `python manage.py runserver 8001` or `ng serve --port 4201` |

## 12. Working agreements for Claude Code

- Keep explanations short and map new concepts to Laravel/CodeIgniter/Vue where it helps.
- Build in the phases above; stop at each checkpoint so the developer can verify before moving on.
- Do not run `migrate` until `AUTH_USER_MODEL` and the custom user model exist.
- Never write real secrets into committed files; use `.env` and `.env.example`.
- Use Git Bash-compatible commands (`source venv/Scripts/activate`, forward slashes) unless told otherwise.
- Use modern Angular (standalone components, signals, `@if`/`@for`), and check the generated file names (`login.ts` vs `login.component.ts`), which vary by CLI version.