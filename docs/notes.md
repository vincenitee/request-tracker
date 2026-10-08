# Build notes

What each phase added, the decisions taken (with the option chosen), and the lessons. Newest last. Commit hashes refer to this repository.

## Phase 1: Foundation (`53df8a0`)

- Settings split into `config/settings/{base,dev,prod}.py`; `.env` via django-environ; MySQL with `mysqlclient`.
- Apps `accounts` and `core` under `apps/`; custom `User` (role, department) and `Department` **before the first migrate**; abstract `TimeStampedModel`; `/api/v1/health/`.
- Added the missing `.gitignore` and `.env.example`; removed PyMySQL leftovers.
- Decision: keep the accidentally committed `.env` in history for now (it was never pushed) → must be rewritten or the secrets rotated before publishing the repo.

## Phase 2: Auth slice (`b54755c`)

- simplejwt login/refresh (30 min / 1 day), `/me/`.
- Angular 21 scaffold (standalone, zoneless, Vitest), environments, `AuthService` with a signal, functional `authInterceptor` (single shared refresh, retry once), `authGuard` with `returnUrl`, session restored by an app initializer.
- Switched the UI library to **PrimeNG 21 + Aura** (`primeng@latest` targeted Angular 22, so the v21 line and `@primeuix/themes@2` were pinned). Aura pinned to light mode.
- Decision: keep explicit `auth.service.ts` / `auth.guard.ts` names; components follow the CLI's suffix-less names.

## Phase 3: Core CRUD (`087e59d`)

- `service_requests` app: `Category`, `Request`, scoped queryset, write/list/detail serializers, `FilterSet`, priority-rank ordering, pagination, admin, idempotent dev-only `seed_demo_data`.
- One error shape `{detail, errors}` through a custom exception handler.
- Angular: lazy requests feature, list (lazy table, debounced search, filters), create/edit form with server field errors, shared status badge, ConfirmDialog delete.
- Decisions: custom exception handler now (A); initial bundle budget raised to 750 kB (A).

## Phase 4: Workflow (`9b04b99`)

- `StatusHistory`; transition table; `perform_transition` with `select_for_update`, permission → state → input checks, history in the same transaction; `available_actions`; history endpoint; multi-value status filter.
- Detail page with server-driven buttons, reject dialog with required remarks, Timeline; relative-date pipe; "Needs review" preset.
- Decisions: reviewers see and edit their own requests but never review them (A); `seed_demo_data --reset` rebuilds demo requests through the real workflow (A); pages moved under `features/requests/pages/` (A).

## Phase 5: Comments and attachments (`7ea8416`)

- `Comment` and `Attachment`; private `MEDIA_ROOT` with UUID filenames; magic-byte validation; orphan-free upload and on-commit file deletion; permission-checked streaming download; subquery counts on the list.
- Comments and attachments sections with FileUpload (custom upload, real progress), Blob download, file-size pipe, shared attachment constants.
- Lessons: a `<form>` without `[formGroup]` reloads the page; lists derived from status must reload when the status changes.

## Phase 6: Polish (`bf4f28c`)

- Dashboard summary in one aggregate query; `needs_my_action` rule shared by the dashboard and a list filter so numbers always match.
- Admin API (users, departments) with rules in `accounts/services.py`; categories active-only by default with `include_inactive` for admins.
- Login and general throttling; OpenAPI with Swagger UI only in DEBUG and `docs/openapi.yaml`; JSON 404/500 for `/api/`; key=value logging with workflow log lines.
- Angular: dashboard, admin pages, role guard, global error interceptor with per-request opt-out and `notifyError`, empty/skeleton/page-header components, not-found page, page titles, tablet drawer, skip link.
- Decisions: progress bars instead of installing chart.js (A); `?needs_my_action=true` filter (A); interceptor owns network/403/429/5xx toasts (A).
- `check --deploy` warnings recorded for Phase 7 (see [04-security.md](04-security.md#48-what-check---deploy-reports-today)).

## Handbook

- `docs/` handbook written: architecture, backend, frontend, security, testing, new-module recipe, troubleshooting, these notes.

## Phase 7: Deploy (next)

Gunicorn behind Nginx on Linux, production settings and HTTPS, Redis cache, one domain for Angular and the API, backups of the database and `MEDIA_ROOT`, CI running tests and the schema check.
