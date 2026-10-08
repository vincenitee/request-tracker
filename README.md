# Request Tracker

A small internal request-management system built with **Angular**, **Django REST Framework**, and **MySQL**. Staff submit requests, reviewers approve or reject them, and admins manage users, departments, and categories.

This is a learning and reference project. It covers the patterns a real internal system needs (roles, workflow, audit trail, file uploads, filtering, JWT auth) in a codebase small enough to finish and reuse as a blueprint.

> **Status:** in development. Backend foundation (MySQL connection, environment config) is in place. Custom user model, API, and Angular frontend are in progress.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Angular (standalone components, signals), SCSS |
| Backend | Django 5.2 LTS, Django REST Framework |
| Auth | JWT (`djangorestframework-simplejwt`) |
| Database | MySQL 8.x (`mysqlclient` driver) |
| API docs | OpenAPI via `drf-spectacular` |
| Filtering | `django-filter` |

## Features (MVP)

- Role-based access: **Staff**, **Reviewer**, **Admin**
- Request lifecycle: Draft → Submitted → In Review → Approved / Rejected → Completed
- Approve/reject with remarks, with a full status history (audit trail)
- Comments and file attachments on requests
- List with search, filters, ordering, and pagination
- Dashboard with counts by status
- Admin management of users, departments, and categories

Out of scope for the MVP: email notifications, real-time updates, multi-step approval chains, PDF export.

## Roles

| Role | Permissions |
|---|---|
| Staff | Create and edit own drafts, submit, view own requests, comment, upload attachments |
| Reviewer | View requests in their department, approve/reject with remarks, comment |
| Admin | Everything, plus manage users, departments, and categories |

## Project structure

```
request-tracker/
├── backend/                  # Django + DRF
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                  # local only, not committed
│   ├── .env.example          # template for .env
│   ├── config/               # settings, urls, wsgi/asgi
│   └── apps/
│       ├── accounts/         # custom User, Department, roles, auth
│       ├── core/             # shared base models, health endpoint, utilities
│       └── service_requests/ # request workflow module
├── frontend/                 # Angular app
│   └── src/app/
│       ├── core/             # auth service, guards, interceptors
│       ├── shared/           # reusable components, pipes, models
│       ├── layouts/
│       └── features/         # auth, dashboard, requests, admin
├── docs/                     # notes, ERD, API contract
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

On Windows, use Git Bash or Command Prompt. The commands below use Git Bash syntax; in Command Prompt, activate the venv with `venv\Scripts\activate`.

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

Always use `utf8mb4` (not `utf8`). The second `GRANT` lets Django's test runner create its test database.

### 3. Set up the backend

```bash
cd backend
py -3.14 -m venv venv
source venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create `backend/.env` from the template:

```bash
cp .env.example .env
```

Then edit it:

```
SECRET_KEY=replace-with-a-long-random-string
DEBUG=True
DB_NAME=request_tracker
DB_USER=rt_user
DB_PASSWORD=choose_a_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Check the database connection:

```bash
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('MySQL connected')"
```

Run migrations, create an admin user, and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- API health check: <http://localhost:8000/api/v1/health/>
- Django admin: <http://localhost:8000/admin/>

### 4. Set up the frontend

In a second terminal:

```bash
cd frontend
npm install
ng serve
```

Open <http://localhost:4200>. The Angular dev server calls the API at `http://localhost:8000/api/v1` (configured in `src/environments/environment.ts`).

## Daily workflow

```
Terminal 1:  cd backend  → source venv/Scripts/activate → python manage.py runserver
Terminal 2:  cd frontend → ng serve
```

The venv must be active for any `python` or `pip` command in `backend/`. Angular commands do not need it. In VS Code, select the interpreter once (`Ctrl+Shift+P` → **Python: Select Interpreter** → `backend/venv/Scripts/python.exe`) and new terminals activate it automatically.

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key. Never commit it |
| `DEBUG` | `True` for local development only |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MySQL credentials |
| `DB_HOST`, `DB_PORT` | MySQL host and port (default `127.0.0.1:3306`) |

`.env` is ignored by Git. Keep `.env.example` up to date with variable names and dummy values.

## API overview

Base path: `/api/v1/`. Resources use plural nouns and trailing slashes.

```
POST   /auth/token/                 login (returns access and refresh tokens)
POST   /auth/token/refresh/
GET    /me/                         current user and role

GET    /requests/                   ?status=&category=&search=&ordering=&page=
POST   /requests/
GET    /requests/{id}/
PATCH  /requests/{id}/
POST   /requests/{id}/submit/
POST   /requests/{id}/approve/
POST   /requests/{id}/reject/
GET    /requests/{id}/history/
GET    /requests/{id}/comments/     POST to add a comment
POST   /requests/{id}/attachments/

GET    /dashboard/summary/
GET    /categories/                 admin only for writes
GET    /users/                      admin only
```

List responses are paginated as `{count, next, previous, results}`. Errors use one shape: `{detail, errors: {field: [..]}}`.

An OpenAPI schema and interactive docs are exposed through `drf-spectacular` once enabled.

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

**Important:** `AUTH_USER_MODEL = "accounts.User"` must be set before the first `migrate` on a database. If you ever migrated before this was in place, drop and recreate the database:

```bash
mysql -u root -p -e "DROP DATABASE request_tracker; CREATE DATABASE request_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

## Conventions

- One Django app and one Angular feature folder per business module, with matching names.
- Thin views; business rules (such as status transitions) live in `services.py`.
- Angular features never import from each other. Shared code goes in `shared/`.
- Features are lazy-loaded; HTTP calls live in services, not components.
- Commit migrations. Never commit `.env`, `venv/`, `node_modules/`, `.angular/`, or `dist/`.
- Python formatting with Ruff or Black; Angular with ESLint and Prettier.
- Commit after each build phase with a clear message.

## Build phases

| Phase | Backend | Frontend | Status |
|---|---|---|---|
| 1. Foundation | Settings split, custom user, roles, health endpoint | `ng new`, structure, environments | In progress |
| 2. Auth slice | JWT login, `/me/` | Login page, interceptor, guard | Planned |
| 3. Core CRUD | Category and Request models, serializer, viewset | List and form pages | Planned |
| 4. Workflow | Submit/approve/reject, StatusHistory | Detail page, action buttons | Planned |
| 5. Extras | Comments, attachments, filters | Comment box, uploader, filter bar | Planned |
| 6. Polish | Dashboard summary, tests, OpenAPI | Dashboard, error and loading states | Planned |
| 7. Deploy | Gunicorn, Nginx, MySQL, `check --deploy` | `ng build`, static hosting | Planned |

## Testing

```bash
cd backend
pytest                     # once pytest-django is configured

cd ../frontend
ng test
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `python --version` shows an older version | Create the venv with `py -3.14 -m venv venv`. Inside an active venv, `python` always matches it |
| `ModuleNotFoundError: No module named 'django'` | The venv is not active |
| `ImproperlyConfigured: SECRET_KEY` | `.env` is missing or not in `backend/` next to `manage.py` |
| `Access denied for user 'rt_user'` | The password in `.env` does not match the one set in MySQL |
| `Unknown database 'request_tracker'` | Run the `CREATE DATABASE` statement first |
| `Can't connect to MySQL server` | MySQL service is not running, or the port is not 3306 |
| `mysqlclient` fails to install | Use Python 3.13, or fall back to PyMySQL (`pip install pymysql cryptography` and add `import pymysql; pymysql.install_as_MySQLdb()` to `config/__init__.py`). Use only one driver |
| `ng` blocked in PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Command Prompt |
| CORS error in the browser | Check `CORS_ALLOWED_ORIGINS` has no trailing slash and `CorsMiddleware` is near the top of `MIDDLEWARE` |
| `mysql` says `using password: NO` in Git Bash | Retry, or run `winpty mysql -u root -p` |
| Port already in use | `python manage.py runserver 8001` or `ng serve --port 4201` |

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