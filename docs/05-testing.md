# 5. Testing

## 5.1 Running the tests

```bash
cd backend
source venv/Scripts/activate
python manage.py test                    # all 113 tests
python manage.py test apps.service_requests.tests.test_workflow   # one module
python manage.py test apps.accounts.tests.test_admin_api.UserRuleTests.test_reviewer_without_department_is_rejected

cd ../frontend
ng test --watch=false                    # Vitest unit test
ng build                                 # type-checks every template and enforces the bundle budget
```

Django creates a throwaway MySQL database `test_request_tracker` (the `rt_user` grant from the README allows it), runs every test inside a transaction that is rolled back, then drops the database.

> **Laravel:** `php artisan test` with `RefreshDatabase`.

## 5.2 Where the tests live and what they cover

| File | Covers |
|---|---|
| `apps/core/tests.py` | health, login and general throttling, error shape for 401/403/404/405/429 and unknown URLs, docs only with DEBUG |
| `apps/accounts/tests/test_auth.py` | login ok/wrong password, `/me/` with and without a token, refresh |
| `apps/accounts/tests/test_models.py` | new users default to staff |
| `apps/accounts/tests/test_admin_api.py` | 403 for non-admins, user CRUD, password validation, no password in responses, self and last-admin rules, reviewer needs a department, department/category delete blocked |
| `apps/service_requests/tests/test_requests_api.py` | scoping per role, 404 for invisible ids, server-set fields, edit/delete rules, filters, search, priority ordering, pagination shape, query count |
| `.../test_categories_api.py` | active/inactive visibility, admin-only writes, delete blocked when used |
| `.../test_workflow.py` | happy path with 4 history rows, reject needs remarks, every permission rule, submit validation, invalid and final-state transitions, `available_actions` per role, scoped history, rollback |
| `.../test_comments.py` | draft blocked, blank/too long, 404 everywhere for outsiders, delete rules, counts without extra queries |
| `.../test_attachments.py` | allowed types, random stored names, sanitizing, role/status rules, every rejection (extension, size, empty, 6th file, wrong magic bytes, 413), no orphan files, download headers, file removal on delete and cascade, no public `/media/` |
| `.../test_dashboard.py` | counts per role, zero statuses present, needs-my-action rules, every count equals the filtered list, constant query count |

## 5.3 Techniques worth reusing

**API tests as the user.** `APITestCase` + `self.client.force_authenticate(user)` skips the token dance; `test_auth.py` covers the real token flow separately.

```python
self.client.force_authenticate(self.staff)
response = self.client.patch(reverse("request-detail", args=[pk]), {"title": "x"}, format="json")
self.assertEqual(response.status_code, 403)
```

**Shared fixtures once per class.** `setUpTestData` (class method) creates users and rows once; each test still runs in its own rollback.

**Tiny factories instead of a library.** `apps/service_requests/tests/factories.py` has `make_user`, `make_category`, `make_request`, `make_department`, and file helpers (`upload()`, `PDF_BYTES`, `PNG_BYTES`, `EXE_BYTES`, `office_bytes()`).

**Reverse URLs by name**, never hard-code paths: `reverse("request-start-review", args=[pk])`, `reverse("request-download-attachment", kwargs={"pk": 1, "attachment_id": 2})`.

**Prove there is no N+1.**

```python
with self.assertNumQueries(2):            # exact count
    self.client.get(LIST_URL)

with CaptureQueriesContext(connection) as before: ...   # compare small vs large data sets
```

**Files never touch the real `media/`.** `TempMediaMixin` (`tests/media.py`) points `MEDIA_ROOT` at a temporary folder for the class and deletes it afterwards. A test asserts the path contains `rt-test-media-`.

**`on_commit` callbacks.** `TestCase` never really commits, so callbacks registered with `transaction.on_commit` (file deletion, workflow logging) do not run unless you ask:

```python
with self.captureOnCommitCallbacks(execute=True):
    self.client.delete(item_url(pk, attachment_id))
self.assertFalse(path.exists())
```

**Force a failure to test atomicity.**

```python
with mock.patch.object(StatusHistory.objects, "create", side_effect=RuntimeError("disk full")):
    with self.assertRaises(RuntimeError):
        services.perform_transition(req, self.staff, "submit")
req.refresh_from_db()
self.assertEqual(req.status, S.DRAFT)      # status change rolled back too
```

Through the API the same failure becomes a JSON 500; `test_failed_db_write_leaves_no_orphan_file` checks that and wraps the call in `assertLogs` so the expected traceback does not clutter the output.

**Throttling.** Rates are read per request, so `@override_settings(LOGIN_THROTTLE_RATE="3/min")` works; call `cache.clear()` in `setUp` because counters live in the cache. `test_auth.py` also clears the cache, since its tests log in repeatedly.

**Settings that are read per request** can be flipped inside a test: `with self.settings(DEBUG=False): ...` (used to prove Swagger UI is hidden in production).

**Test the service directly** when the API cannot reach a branch (the last-admin rule: `LastAdminServiceTests`).

## 5.4 What a good test for a new rule looks like

1. Arrange the smallest data set that shows the rule (two users, one request).
2. Act through the API as the user who should be **refused**, assert the status code **and** that nothing changed in the database.
3. Act as the user who should be **allowed**, assert success and the side effects (history row, file on disk).
4. If the rule affects a count or a list, assert the visible ids, not just the count.

## 5.5 Frontend checks

- `ng build` is the main safety net: strict templates catch typos in bindings, wrong input names, and type errors in templates.
- `ng test` runs one Vitest spec (`app.spec.ts`) that boots the root component with its providers. Unit tests for services and components are a good next exercise (Angular's `HttpTestingController` mocks HTTP).
- Browser flows were verified during development with a headless Edge script kept outside the repository. To repeat them by hand, use the checklist below.

## 5.6 Manual browser checklist

Demo users: `demo_staff` (IT), `demo_staff_hr` (HR), `demo_reviewer` (IT), `demo_admin` (password from `seed_demo_data` / `DEMO_PASSWORD`).

**Staff**
- [ ] Dashboard shows only own counts; a status card opens the list filtered by that status
- [ ] Create a draft, edit it, attach a PDF and a PNG (progress bar visible), download one, delete one
- [ ] A renamed `.exe`, a file over 5 MB, and a sixth file each show a clear error
- [ ] Submit the draft: upload controls and edit buttons disappear, the comment box appears, history has one entry
- [ ] `/admin/users` redirects to the dashboard with "You do not have access"

**Reviewer**
- [ ] Dashboard "Needs my action" equals the list opened by the call-out
- [ ] "Needs review" preset shows only Submitted / In review
- [ ] Start review → Reject without remarks is blocked → Reject with remarks shows them in the timeline
- [ ] Own submitted request shows no review buttons
- [ ] Attachments can be downloaded but not deleted; own comments can be deleted, others' cannot

**Admin**
- [ ] Complete an approved request (history now has 4 entries)
- [ ] Users: create, edit, reset password, deactivate; the new user can log in before and cannot after deactivation
- [ ] Deactivating or demoting yourself shows the server message
- [ ] Deleting a department with users, or a category with requests, shows why it is blocked
- [ ] Swagger UI at `/api/v1/docs/`: Authorize with an access token, Try it out on `/me/` returns 200

**General**
- [ ] Reload any page: you stay logged in
- [ ] 11 wrong logins within a minute: "Too many attempts" toast, the form stays usable
- [ ] Stop `runserver`: one "Cannot reach the server" toast
- [ ] Narrow the window below 960 px: the menu moves into the drawer
- [ ] Unknown URL shows the not-found page
