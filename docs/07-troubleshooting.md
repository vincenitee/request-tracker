# 7. Troubleshooting

Real problems met while building this project, grouped by area. Each entry: **symptom → cause → fix**.

## Environment and setup

| Symptom | Cause | Fix |
|---|---|---|
| `python --version` shows 3.10/3.11 after installing 3.14 | Windows runs the first `python.exe` on `PATH` | create the venv with `py -3.14 -m venv venv`; inside an active venv `python` is the venv's |
| `ModuleNotFoundError: No module named 'pymysql'` | `config/__init__.py` still imported PyMySQL after switching drivers | keep `config/__init__.py` empty; use only `mysqlclient` |
| `ImproperlyConfigured: SECRET_KEY` | `.env` missing or not next to `manage.py` | `cp .env.example .env` in `backend/` |
| `Access denied for user 'rt_user'` | password in `.env` differs from MySQL | fix one of them; use `127.0.0.1`, not `localhost` |
| `InconsistentMigrationHistory` | `migrate` ran before `AUTH_USER_MODEL` was set | drop and recreate the database, delete generated migrations, redo |
| `.env` showed up in `git ls-files` | the repo had no `.gitignore` when the first commit was made | add `.gitignore`, `git rm --cached backend/.env`; the old copy stays in history until rewritten |
| `mysql` login says `using password: NO` in Git Bash | the prompt does not reach the TTY | `winpty mysql -u root -p` |
| `ng` blocked in PowerShell | execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Git Bash |
| npm prints "install scripts not yet covered by allowScripts" (esbuild, lmdb...) | npm 11 lists skipped build scripts of Angular's tooling | harmless: those packages ship prebuilt binaries |
| `seed_demo_data` user cannot log in | the password was changed (for example in `/admin/`) after seeding | `DEMO_PASSWORD=... python manage.py seed_demo_data` resets all demo passwords |

## Angular / PrimeNG

| Symptom | Cause | Fix |
|---|---|---|
| `npm install primeng` fails with ERESOLVE | `primeng@latest` targeted the next Angular major | install the matching major: `primeng@^21` for Angular 21 (never `--force`) |
| Theme does not apply / looks half-styled | `@primeuix/themes` 3.x paired with PrimeNG 21 (needs 2.x) | `@primeuix/themes@^2`; one copy of `@primeuix/styled` in `npm ls` |
| Dark components on a light page | Aura follows the OS dark mode by default | `options: { darkModeSelector: '.app-dark' }` in `providePrimeNG` |
| Toolbar items wrap onto two lines | our `p-toolbar { display: block }` overrode PrimeNG's flex host | do not override `display` on PrimeNG host elements |
| Timeline uses only half the card, markers zig-zag | empty "opposite" column | `[pt]="{ eventOpposite: { style: { display: 'none' } } }"` |
| `'p-table' is not a known element` style errors | `Table` is not standalone in PrimeNG 21 | import `TableModule` |
| A dialog footer `<p-button type="submit" form="x">` does nothing | `p-button` has no `form` input | call the save method with `(onClick)` |
| `TS7053: Element implicitly has an 'any' type` in a table template | `let-item` is `any`; strict templates refuse indexing a typed map with it | use a typed method: `priorityLabel(item.priority)` |
| Clicking a form's button reloads the whole page | `<form>` without `[formGroup]` → no `ngSubmit`, native submit | bind a `FormGroup`, or `(submit)="$event.preventDefault(); ..."` |
| Delete buttons still visible after a status change | list loaded once with old `can_delete` flags | reload when the status input changes (`effect()` in `RequestAttachments`) |
| `::ng-deep` used for one margin | habit from older Angular | wrap the element in a `div` with a class instead (`::ng-deep` is deprecated) |
| Build warning "bundle initial exceeded maximum budget" | PrimeNG + Aura in the initial bundle | budget raised to 750 kB; keep pages lazy |
| First page load after adding a PrimeNG import reloads by itself | Vite pre-bundles the new dependency, then reloads once | expected; reload or wait a second |
| The app shows old code although files changed and `ng build` passes | the running `ng serve` got stuck on an earlier compile error | save any file (or `touch src/app/app.config.ts`); otherwise restart `ng serve` |

## Django / DRF

| Symptom | Cause | Fix |
|---|---|---|
| Deleting a used category returned 500 | `PROTECT` raises `ProtectedError` | catch it in the service and raise a 400 with a helpful message (`delete_category`) |
| `ordering=priority` gives high, low, medium | text column sorted alphabetically | sort by an annotated rank (`RequestOrderingFilter`) |
| Counts wrong when annotating two `Count()`s | two joins multiply rows | correlated `Subquery` counts (`_count_of`) |
| List does one extra query per row | lazy related lookups (N+1) | `select_related`, subquery counts, pass parent objects via serializer context |
| Comment POST blocked by "Only the requester can change..." | `CanModifyRequest` applied to nested POST actions | nested actions use `get_permissions()` → `IsAuthenticated`, rules in services |
| `assertRaises` no longer catches an exception in an API test | the exception handler now turns unexpected errors into a JSON 500 | assert the 500 response instead (and use `assertLogs` to keep output clean) |
| A file-deletion test passes the delete but the file still exists | `on_commit` callbacks never run inside `TestCase` | `with self.captureOnCommitCallbacks(execute=True): ...` |
| Login tests randomly return 429 | throttle counters persist in the cache across tests | `cache.clear()` in `setUp`; lower rates with `override_settings` only where tested |
| You are "throttled" in the browser after testing | 10 logins/min per IP, counter lives ~60 s | wait a minute or restart `runserver` (LocMemCache is cleared) |
| `spectacular`: "unable to guess serializer" for `health` | function view without a serializer | `@extend_schema(responses=inline_serializer(...))` |
| `spectacular`: "Failed to obtain model through view's queryset", ids typed as string | `get_queryset()` needs a real user | return `Model.objects.none()` when `swagger_fake_view` is set |
| `/api/v1/docs/` returns 404 | `DEBUG` is False (by design) | only available in development |
| Unknown `/api/...` URL used to return an HTML page | Django's default 404 page | `re_path(r"^api/", api_not_found)` catch-all + `handler404` |
| An API bug shows only "A server error occurred" | unexpected exceptions are converted to JSON 500 | read the traceback in the `runserver` console (`apps.core.errors` logger) |
| `seed_demo_data --reset` undid manual testing | it rebuilds every request owned by `demo_*` users | run plain `seed_demo_data` unless you really want a clean demo set |

## Tooling used during development (not in the repo)

| Symptom | Cause | Fix |
|---|---|---|
| Headless Edge (Puppeteer) cancels every download | the download path used forward slashes on Windows | pass a Windows path (`cygpath -w`) to `Browser.setDownloadBehavior` |
| Two `runserver` processes on port 8000 | Windows lets two sockets bind the same port | stop the extra one; check with `Get-NetTCPConnection -LocalPort 8000` |
