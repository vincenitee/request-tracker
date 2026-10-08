# Request Tracker

A small internal request-management system built with **Angular + PrimeNG**, **Django REST Framework**, and **MySQL**. Staff submit requests, reviewers approve or reject them, and admins manage users, departments, and categories.

This is a learning and reference project. It covers the patterns a real internal system needs (roles, workflow, audit trail, file uploads, filtering, JWT auth) in a codebase small enough to finish and reuse as a blueprint.

> **Status:** Phases 1–6 are complete (requests, workflow with audit trail, comments, attachments, dashboard, admin pages, throttling, OpenAPI). Phase 7 (deployment) is next.

## Documentation

The **[handbook in docs/](docs/README.md)** explains how every piece works and why, with Laravel/Vue comparisons:

| Guide | Covers |
|---|---|
| [Architecture](docs/01-architecture.md) | folders, conventions, how one click travels from Angular to MySQL |
| [Backend](docs/02-backend.md) | settings, models, serializers, viewsets, services, permissions, workflow, uploads, errors, throttling, OpenAPI |
| [Frontend](docs/03-frontend.md) | bootstrapping, routing, guards, auth and interceptors, signals vs RxJS, forms, PrimeNG, error handling |
| [Security](docs/04-security.md) | auth, 404 vs 403, upload hardening, `check --deploy`, production checklist |
| [Testing](docs/05-testing.md) | test layout and techniques, manual browser checklist |
| [Recipe: new module](docs/06-recipe-new-module.md) | step-by-step blueprint for adding your own module |
| [Troubleshooting](docs/07-troubleshooting.md) | real problems met while building this, with fixes |
| [Build notes](docs/notes.md) | what each phase added and the decisions taken |

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Angular (standalone components, signals), PrimeNG (Aura theme), SCSS |
| Backend | Django 5.2 LTS, Django REST Framework |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Database | MySQL 8.x (`mysqlclient` driver) |
| API docs | OpenAPI via `drf-spectacular` |
| Filtering | `django-filter` |

## Features (MVP)

- Role-based access: **Staff**, **Reviewer**, **Admin**
- Request lifecycle: Draft → Submitted → In Review → Approved / Rejected → Completed
- Approve/reject with remarks and a full status history (audit trail)
- Comments and file attachments on requests
- List with search, filters, ordering, and server-side pagination
- Dashboard with counts by status and a "needs my action" call-out
- OpenAPI schema and Swagger UI (development)
- Login throttling and one consistent JSON error shape
- Admin management of users, departments, and categories

Out of scope for the MVP: email notifications, real-time updates, multi-step approval chains, PDF export.

## Roles

| Role | Permissions |
|---|---|
| Staff | Create and edit own drafts, submit, view own requests, comment, upload attachments |
| Reviewer | View their own requests and non-draft requests from their department, start review, approve/reject with remarks (never their own), comment |
| Admin | View all requests, review any request except their own, complete approved requests, manage users, departments, and categories |

## Project structure

```
request-tracker/
├── backend/                  # Django + DRF
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                  # local only, not committed
│   ├── .env.example          # template for .env
│   ├── config/
│   │   └── settings/         # base.py, dev.py, prod.py
│   └── apps/
│       ├── accounts/         # custom User, Department, /me/
│       ├── core/             # base models, health endpoint, utilities
│       └── service_requests/ # request workflow module
├── frontend/                 # Angular app
│   └── src/app/
│       ├── core/             # auth service, guards, interceptors
│       ├── shared/           # reusable components, pipes, models
│       ├── layouts/
│       └── features/         # auth, dashboard, requests, admin
├── docs/                     # handbook (start at docs/README.md), notes, openapi.yaml
├── CLAUDE.md                 # context and rules for Claude Code
└── README.md
```

## Prerequisites

| Tool | Version used |
|---|---|
| Python | 3.14 (3.13 also works) |
| Node.js | 22 LTS |
| Angular CLI | 21.x |
| MySQL | 8.0 or newer (8.4 LTS recommended) |
| Git | 2.x |

Commands use Git Bash syntax. In Command Prompt, activate the venv with `venv\Scripts\activate`.

## Getting started

### 1. Clone

```bash
git clone <repository-url> request-tracker
cd request-tracker
```

### 2. Create the MySQL database

```bash
mysql -u root -p
```

```sql
CREATE DATABASE request_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'rt_user'@'localhost' IDENTIFIED BY 'choose_a_password';
GRANT ALL PRIVILEGES ON request_tracker.* TO 'rt_user'@'localhost';
GRANT ALL PRIVILEGES ON `test_request_tracker`.* TO 'rt_user'@'localhost';
FLUSH PRIVILEGES;
```

Always use `utf8mb4` (not `utf8`). The second `GRANT` lets Django's test runner create its test database. In Git Bash, use `winpty mysql -u root -p` if the password prompt does not register.

### 3. Set up the backend

```bash
cd backend
py -3.14 -m venv venv
source venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

```
SECRET_KEY=replace-with-a-long-random-string
DEBUG=True
DB_NAME=request_tracker
DB_USER=rt_user
DB_PASSWORD=choose_a_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Check the database connection, migrate, create an admin, and run the server:

```bash
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('MySQL connected')"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`createsuperuser` leaves the new user's role at `staff`. In the Django admin, set **role = admin** on admin accounts.

- Health check: <http://localhost:8000/api/v1/health/>
- Django admin: <http://localhost:8000/admin/>

### 4. Set up the frontend

In a second terminal:

```bash
cd frontend
npm install
ng serve
```

Open <http://localhost:4200>. `ng serve` uses `src/environments/environment.development.ts`, which points at `http://localhost:8000/api/v1`; the production build (`environment.ts`) uses the same-domain path `/api/v1`.

### 5. Demo data

```bash
python manage.py seed_demo_data                            # idempotent; prints a generated password for new demo users
DEMO_PASSWORD=choose-one python manage.py seed_demo_data   # set or reset all demo passwords
python manage.py seed_demo_data --reset                    # rebuild the demo users' requests from scratch
```

Development only (refuses to run when `DEBUG` is `False`). It creates departments IT and HR, four categories, the users `demo_staff`, `demo_staff_hr`, `demo_reviewer`, `demo_admin`, 15 requests moved through the real workflow (with history), and a few comments. `--reset` only touches requests owned by the demo users.

API docs (Swagger UI): <http://localhost:8000/api/v1/docs/>. Click **Authorize** and paste an access token from `POST /api/v1/auth/token/`.

## Daily workflow

```
Terminal 1:  cd backend  → source venv/Scripts/activate → python manage.py runserver
Terminal 2:  cd frontend → ng serve
```

The venv must be active for any `python` or `pip` command in `backend/`. Angular commands do not need it. In VS Code, select the interpreter once (`Ctrl+Shift+P` → **Python: Select Interpreter** → `backend/venv/Scripts/python.exe`).

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key. Never commit it |
| `DEBUG` | `True` for local development only |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MySQL credentials |
| `DB_HOST`, `DB_PORT` | MySQL host and port (default `127.0.0.1:3306`) |
| `DEMO_PASSWORD` | optional; password for `seed_demo_data` users |
| `LOG_LEVEL` | optional; level for the `apps.*` loggers (default `INFO`) |
| `LOGIN_THROTTLE_RATE`, `API_USER_THROTTLE_RATE` | optional; defaults `10/min` per IP on login and `1000/hour` per user |
| `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` | production settings only (comma-separated) |

`.env` is ignored by Git. Keep `.env.example` current with variable names and dummy values.

## API overview

Base path: `/api/v1/`. Resources use plural nouns and trailing slashes. The full contract is [docs/openapi.yaml](docs/openapi.yaml).

```
POST   /auth/token/                  login (access + refresh tokens), throttled per IP
POST   /auth/token/refresh/
GET    /me/                          current user, role, department
GET    /health/

GET    /categories/                  active only (?include_inactive=true for admins); writes admin-only
GET    /requests/                    ?status=&category=&priority=&needs_my_action=&search=&ordering=&page=
POST   /requests/
GET    /requests/{id}/               includes available_actions for the current user
PATCH  /requests/{id}/               own drafts (admins: any)
DELETE /requests/{id}/               own drafts (admins: any)
POST   /requests/{id}/submit/        also start-review/, approve/, reject/ (remarks required), complete/
GET    /requests/{id}/history/
GET    /requests/{id}/comments/      POST to add; DELETE .../comments/{comment_id}/
GET    /requests/{id}/attachments/   POST multipart "file"; DELETE .../attachments/{id}/; GET .../attachments/{id}/download/
GET    /dashboard/summary/
GET    /users/                       admin only; POST, PATCH, POST /users/{id}/set-password/ (no DELETE)
GET    /departments/                 admin only; POST, PATCH, DELETE
GET    /schema/  /docs/              OpenAPI schema and Swagger UI, DEBUG only
```

List responses are paginated as `{count, next, previous, results}`. Errors use one shape: `{detail, errors: {field: [..]}}`.

## Data model

```
User            role, department, is_active        (custom user model)
Department      name
Category        name, is_active
Request         title, description, category, requester, status, priority, timestamps
Attachment      request, file, uploaded_by, uploaded_at
Comment         request, author, body, created_at
StatusHistory   request, from_status, to_status, changed_by, remarks, changed_at
```

**Important:** `AUTH_USER_MODEL = "accounts.User"` must be set before the first `migrate` on a database. If you ever migrated before it was in place, drop and recreate the database:

```bash
mysql -u root -p -e "DROP DATABASE request_tracker; CREATE DATABASE request_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

## Conventions

- One Django app and one Angular feature folder per business module, with matching names.
- Thin views; business rules (such as status transitions) live in `services.py`.
- Angular features never import from each other. Shared code goes in `shared/`.
- Features are lazy-loaded; HTTP calls live in services, not components.
- PrimeNG components are imported individually; repeated patterns are wrapped in `shared/` components.
- Commit migrations. Never commit `.env`, `venv/`, `node_modules/`, `.angular/`, or `dist/`.
- Commit after each build phase with a clear message.

## Build phases

| Phase | Backend | Frontend | Status |
|---|---|---|---|
| 1. Foundation | Settings split, custom user, roles, health endpoint | | Done |
| 2. Auth slice | JWT login, `/me/` | Scaffold, PrimeNG, login, interceptor, guard, layout | Done |
| 3. Core CRUD | Category and Request models, scoped API, filters | List and form pages | Done |
| 4. Workflow | Submit/approve/reject/complete, StatusHistory | Detail page, action buttons, timeline | Done |
| 5. Extras | Comments, attachments | Comment box, uploader with progress | Done |
| 6. Polish | Dashboard summary, admin API, throttling, OpenAPI, logging | Dashboard, admin pages, error and loading states | Done |
| 7. Deploy | Gunicorn, Nginx, MySQL, `check --deploy` | `ng build`, static hosting | Next |

## Testing

```bash
cd backend
python manage.py test                                  # 113 tests on a throwaway MySQL test database
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file ../docs/openapi.yaml --validate --fail-on-warn

cd ../frontend
ng test --watch=false
ng build                                               # strict template type-checking + bundle budget
```

See [docs/05-testing.md](docs/05-testing.md) for how the tests are organized and a manual browser checklist.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python --version` shows an older version | Create the venv with `py -3.14 -m venv venv`. Inside an active venv, `python` matches it |
| `ModuleNotFoundError: No module named 'django'` | The venv is not active |
| `ERR_CONNECTION_REFUSED` on port 8000 | `runserver` is not running or crashed; start it and read the output |
| `ImproperlyConfigured: SECRET_KEY` | `.env` is missing or not in `backend/` next to `manage.py` |
| `Access denied for user 'rt_user'` | The password in `.env` does not match the one set in MySQL |
| `Unknown database 'request_tracker'` | Run the `CREATE DATABASE` statement first |
| `Can't connect to MySQL server` | MySQL service is not running, or the port is not 3306 |
| `mysqlclient` fails to install | Use Python 3.13, or fall back to PyMySQL (`pip install pymysql cryptography` and add `import pymysql; pymysql.install_as_MySQLdb()` to `config/__init__.py`). Use only one driver |
| `ng` blocked in PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Command Prompt |
| CORS error in the browser | `CORS_ALLOWED_ORIGINS` needs `http://localhost:4200` with no trailing slash; `CorsMiddleware` near the top of `MIDDLEWARE` |
| PrimeNG components look unstyled | Check `providePrimeNG` with the Aura preset in `app.config.ts` and that `@primeuix/themes` is installed |
| Port already in use | `python manage.py runserver 8001` or `ng serve --port 4201` |
| Anything else | see [docs/07-troubleshooting.md](docs/07-troubleshooting.md) |

## Production notes

This project runs on development servers locally. Before deploying for real users:

- Set `DEBUG=False` and a proper `ALLOWED_HOSTS`, and run `python manage.py check --deploy`.
- Serve Django with Gunicorn behind Nginx, with HTTPS, on a Linux server. Build Angular with `ng build` and serve it from the same domain to avoid CORS.
- Prefer httpOnly cookie-based tokens over `localStorage` for JWT.
- Back up the database automatically and test migrations on staging first (MySQL migrations are not transactional).
- Use the same Python minor version on the server as in development.
- Consider MySQL 8.4 LTS; 8.0 is past end of life.

## License

Add a license here if the project will be shared.