# 4. Security

What protects the system today, why, and what must change before real users rely on it.

## 4.1 Authentication (JWT)

- Login: `POST /api/v1/auth/token/` with username and password returns an **access** token (30 minutes) and a **refresh** token (1 day). Inactive users cannot log in.
- Every API call sends `Authorization: Bearer <access>`. When it expires, the Angular `authInterceptor` exchanges the refresh token once and retries the call.
- The login endpoint is throttled per IP (`LOGIN_THROTTLE_RATE`, default 10/min), so password guessing is slow. Every attempt counts, right or wrong.

**Known shortcut:** tokens are kept in `localStorage`. Any script running on the page (an XSS bug, a compromised npm package) could read them. For production, either:
- serve Angular and Django from **one domain** and switch to httpOnly, Secure, SameSite cookies set by Django (scripts cannot read them; add CSRF protection), or
- keep bearer tokens but shorten lifetimes and enable refresh-token rotation and blacklisting in simplejwt.

## 4.2 Authorization

Two independent checks on the server (details in [02-backend.md §2.8](02-backend.md#28-authorization-permissions-and-queryset-scoping)):

1. **Scoping** decides which rows exist for a user (`services.scoped_requests`). Everything else is a **404**, so the API never confirms that someone else's request id exists. Comments, attachments, downloads, and history are only reachable through a visible request.
2. **Rules** decide what a user may do to a visible row (`services.py` + permission classes) → **403** with a message.

The frontend hides buttons using server-computed flags (`available_actions`, `can_delete`), but that is only convenience: every rule is enforced again by the API. Test that way too (the tests call the API directly as the "wrong" user).

Admin rules that prevent lock-outs: an admin cannot deactivate or demote themselves, and the last active admin is protected. Users are deactivated, never deleted, so the audit trail keeps its references.

Django's own admin site (`/admin/`) is a separate door controlled by `is_staff`/`is_superuser`. Keep that list short, and note that it bypasses the API rules for the tables it can edit (which is why history, comments, attachments, and request status are read-only there).

## 4.3 Input validation

- Serializers validate types, lengths, and choices; services validate business rules. The client-side validators only give faster feedback.
- `status` and `requester` can never be set by the client: they are not in `RequestWriteSerializer`, and `create_request` sets them.
- Passwords go through Django's password validators (minimum length, common passwords, all-numeric, similarity to user attributes). Password hashes never appear in any response (`UserSerializer` has no password field; a test checks every user endpoint).

## 4.4 File uploads

| Threat | Defence |
|---|---|
| Path traversal / overwriting files via the filename | files are stored under a random UUID; the user's name is only display text, sanitized (`sanitize_filename`) |
| Executable renamed to `.pdf` | magic-byte check of the real content (`content_matches_extension`); docx/xlsx must contain the Office part |
| Huge uploads | 413 above the limit before parsing; 5 MB per file; 5 files per request; Nginx `client_max_body_size` in production |
| Serving a file as HTML/JS in the browser | download only, `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, content type from our own detection |
| Reading other people's files | no public `/media/` route; the download endpoint uses the scoped queryset (404) |
| Orphaned files / lost files | file and row written in one transaction; file deleted only after the row deletion commits |

Not done (consider for the real system): antivirus scanning (for example ClamAV) before accepting a file, and storing files outside the web server's filesystem (object storage with signed URLs).

## 4.5 Throttling and abuse

- `LoginRateThrottle`: per IP on the token endpoint (429 + `Retry-After`).
- `ApiUserRateThrottle`: general limit per user (1000/hour).
- Counters live in the cache; use Redis in production so all workers share them. Behind a reverse proxy, make sure Django sees the real client IP (`NUM_PROXIES` / `X-Forwarded-For` handling), otherwise everyone shares the proxy's IP.

## 4.6 Error messages and logging

- Errors use one JSON shape and never include stack traces in responses; unexpected errors are logged with their traceback and returned as a generic 500.
- Logs never contain passwords, tokens, or request bodies. Workflow transitions are logged with ids only.

## 4.7 Secrets and configuration

- `backend/.env` holds secrets and is git-ignored; `.env.example` lists variable names with dummy values.
- Early in the project `.env` was accidentally committed (there was no `.gitignore` yet). It was removed from tracking, but it is **still readable in the first commit's history**. Before pushing the repository anywhere, either rewrite that commit or rotate `SECRET_KEY` and the database password.
- `seed_demo_data` never stores a real password in code; demo users get `DEMO_PASSWORD` or a generated one.

## 4.8 What `check --deploy` reports today

`python manage.py check --deploy` with production settings currently warns:

| Code | Meaning | Fix in Phase 7 |
|---|---|---|
| W004 | no HSTS | `SECURE_HSTS_SECONDS` (start small), then include subdomains / preload |
| W008 | no HTTPS redirect | `SECURE_SSL_REDIRECT = True` (and `SECURE_PROXY_SSL_HEADER` behind Nginx) |
| W009 | weak `SECRET_KEY` | a new 50+ character random key in the server environment |
| W012 | session cookie not secure | `SESSION_COOKIE_SECURE = True` |
| W016 | CSRF cookie not secure | `CSRF_COOKIE_SECURE = True` |
| W018 | `DEBUG` on | only with dev settings; `prod.py` sets `DEBUG = False` |

## 4.9 Before production (checklist)

- [ ] Production settings: `DEBUG=False`, `ALLOWED_HOSTS`, HTTPS settings above, new `SECRET_KEY`
- [ ] Tokens: httpOnly cookies on one domain, or shorter lifetimes + refresh rotation
- [ ] Redis cache for throttling; correct client IP behind the proxy
- [ ] Nginx `client_max_body_size`, serve Angular and the API on one domain
- [ ] Back up the database **and** `MEDIA_ROOT` together
- [ ] Rewrite or neutralize the `.env` in git history
- [ ] Generate frontend types from `openapi.yaml` so client and server cannot drift
- [ ] Use MySQL 8.4 LTS (8.0 is end of life)
