# 6. Recipe: add a new business module

This is the blueprint part of the handbook. It walks through adding a module the same way `service_requests` / `features/requests` were built, using a hypothetical **Assets** module (company equipment assigned to users, visible per department) as the example. Replace the names with your own.

The pattern on both sides:

- **Backend:** model → migration → admin → services → serializers → permissions → filters → viewset → router → tests
- **Frontend:** interface → service → pages → routes (+ guard) → menu

Each step links back to the section of the handbook that explains the idea.

---

## Backend

### Step 1: create the app

```bash
cd backend && source venv/Scripts/activate
mkdir -p apps/assets
python manage.py startapp assets apps/assets
mkdir apps/assets/tests && touch apps/assets/tests/__init__.py && rm apps/assets/tests.py
```

- In `apps/assets/apps.py` set `name = "apps.assets"`.
- Add `"apps.assets"` to `INSTALLED_APPS` in `config/settings/base.py`.

Why: [§2.2 Apps](02-backend.md#22-apps).

### Step 2: model and migration

```python
# apps/assets/models.py
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Asset(TimeStampedModel):
    class Condition(models.TextChoices):
        GOOD = "good", "Good"
        REPAIR = "repair", "Needs repair"
        RETIRED = "retired", "Retired"

    tag = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="assets"
    )

    class Meta:
        ordering = ["tag"]
        indexes = [models.Index(fields=["condition"])]

    def __str__(self):
        return f"{self.tag} {self.name}"
```

```bash
python manage.py makemigrations assets
python manage.py sqlmigrate assets 0001     # read the SQL once
python manage.py migrate
```

Checklist: every FK has `on_delete` and `related_name`; filtered columns are indexed; `CharField` lengths ≤ 255 if indexed (MySQL). Why: [§2.4](02-backend.md#24-models-and-migrations).

### Step 3: Django admin

Register the model with `list_display`, `list_filter`, `search_fields`, and `list_select_related`. Make fields read-only if they must only change through a service. Why: [§2.20](02-backend.md#220-django-admin-site).

### Step 4: services (rules first)

Decide the rules in a table before writing code, for example:

| | staff | reviewer | admin |
|---|---|---|---|
| see | assets assigned to them | assets assigned to people in their department | all |
| create / edit / retire | no | no | yes |

Then encode them in `apps/assets/services.py`:

```python
from django.db.models import Q, QuerySet

from apps.accounts.services import is_admin, is_reviewer

from .models import Asset


def scoped_assets(user) -> QuerySet[Asset]:
    qs = Asset.objects.select_related("assigned_to")
    if is_admin(user):
        return qs
    if is_reviewer(user) and user.department_id:
        return qs.filter(Q(assigned_to=user) | Q(assigned_to__department_id=user.department_id))
    return qs.filter(assigned_to=user)


def can_manage_assets(user) -> bool:
    return is_admin(user)
```

Any state change that needs history or locking follows `perform_transition`: `transaction.atomic()` + `select_for_update()` + write the audit row in the same transaction. Why: [§2.7](02-backend.md#27-the-services-layer), [§2.11](02-backend.md#211-the-request-workflow-state-machine).

### Step 5: serializers

```python
class AssetSerializer(serializers.ModelSerializer):
    assigned_to = RequesterSerializer(read_only=True)          # {id, name}; reuse or copy the pattern
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source="assigned_to", queryset=User.objects.filter(is_active=True), write_only=True,
        allow_null=True, required=False,
    )

    class Meta:
        model = Asset
        fields = ("id", "tag", "name", "condition", "assigned_to", "assigned_to_id", "created_at")
        read_only_fields = ("id", "created_at")
```

Use separate list / detail / write serializers when the shapes differ, and route `create()` / `update()` through services when rules apply. Why: [§2.5](02-backend.md#25-serializers).

### Step 6: permissions

```python
class CanManageAssets(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or services.can_manage_assets(request.user)
```

Remember the split: **scoping (404)** in `get_queryset`, **rules (403)** in permission classes or services. Why: [§2.8](02-backend.md#28-authorization-permissions-and-queryset-scoping).

### Step 7: filters

```python
class AssetFilter(django_filters.FilterSet):
    condition = django_filters.MultipleChoiceFilter(choices=Asset.Condition.choices)

    class Meta:
        model = Asset
        fields = ("condition", "assigned_to")
```

Why: [§2.9](02-backend.md#29-filtering-search-ordering-pagination).

### Step 8: viewset, router, URLs

```python
class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, CanManageAssets]
    filterset_class = AssetFilter
    search_fields = ("tag", "name")
    ordering_fields = ("tag", "name", "created_at")
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Asset.objects.none()
        return services.scoped_assets(self.request.user)
```

```python
# apps/assets/urls.py
router = SimpleRouter()
router.register("assets", AssetViewSet, basename="asset")
urlpatterns = router.urls

# config/urls.py — add BEFORE the api/ catch-all
path("api/v1/", include("apps.assets.urls")),
```

Why: [§2.6](02-backend.md#26-viewsets-routers-and-custom-actions). Add `@extend_schema` to any custom action ([§2.19](02-backend.md#219-openapi-and-swagger-ui)).

### Step 9: tests

Create `apps/assets/tests/test_assets_api.py` with at least:

- [ ] each role sees exactly the right ids (assert sets of ids)
- [ ] an invisible id returns 404 for GET, PATCH, DELETE
- [ ] a refused write returns 403 **and** the row is unchanged
- [ ] validation errors return 400 with `{detail, errors}` and the right field
- [ ] filters, search, ordering work; pagination shape is `{count, next, previous, results}`
- [ ] `assertNumQueries` on the list stays constant as rows grow

Reuse `apps/service_requests/tests/factories.py` helpers or copy the pattern. Why: [05-testing.md](05-testing.md).

### Step 10: docs and schema

```bash
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file ../docs/openapi.yaml --validate --fail-on-warn
```

Optionally add demo rows to `seed_demo_data` (idempotent with `get_or_create`).

---

## Frontend

### Step 11: feature folder, models, service

```
src/app/features/assets/
├── routes.ts
├── models/asset.model.ts
├── services/assets.service.ts
└── pages/asset-list/  pages/asset-form/
```

```ts
// models/asset.model.ts
export type AssetCondition = 'good' | 'repair' | 'retired';
export interface Asset {
  id: number;
  tag: string;
  name: string;
  condition: AssetCondition;
  assigned_to: { id: number; name: string } | null;
  created_at: string;
}
export interface AssetQuery { page: number; search?: string; condition?: AssetCondition[]; ordering?: string }
```

```ts
// services/assets.service.ts
@Injectable({ providedIn: 'root' })
export class AssetsService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/assets/`;

  list(q: AssetQuery): Observable<Paginated<Asset>> {
    let params = new HttpParams().set('page', q.page);
    if (q.search) params = params.set('search', q.search);
    if (q.ordering) params = params.set('ordering', q.ordering);
    for (const c of q.condition ?? []) params = params.append('condition', c);
    return this.http.get<Paginated<Asset>>(this.url, { params });
  }
  create(body: Partial<Asset> & { assigned_to_id?: number | null }) { return this.http.post<Asset>(this.url, body); }
  update(id: number, body: Partial<Asset> & { assigned_to_id?: number | null }) { return this.http.patch<Asset>(`${this.url}${id}/`, body); }
  delete(id: number) { return this.http.delete<void>(`${this.url}${id}/`); }
}
```

Generate components with the CLI so names match the conventions:

```bash
cd frontend
ng g c features/assets/pages/asset-list --skip-tests
ng g c features/assets/pages/asset-form --skip-tests
```

Why: [§3.7](03-frontend.md#37-services-and-models).

### Step 12: list page

Copy the structure of `features/requests/pages/request-list` (or `features/admin/pages/users`):

- signals for filters (`search`, `condition`), `items`, `total`, `loading`, `firstLoad`, `first`
- `reload$` + `switchMap` for loading, debounced `searchInput$`
- `p-table [lazy]="true" (onLazyLoad)` with `pSortableColumn`
- `#emptymessage` showing `<app-table-skeleton>` on first load, `<app-empty-state>` otherwise
- `<app-page-header>` with the "New" button; errors through `notifyError`

Why: [§3.8](03-frontend.md#38-signals-vs-rxjs), [§3.11](03-frontend.md#311-primeng).

### Step 13: form page

Copy `features/requests/pages/request-form`: typed `NonNullableFormBuilder` group, `<form [formGroup]>` with `(ngSubmit)`, `applyServerErrors()` for field errors, `saving` signal on the button, toast on success, navigate back. Why: [§3.9](03-frontend.md#39-reactive-forms-and-server-errors).

### Step 14: routes, guard, menu

```ts
// features/assets/routes.ts
export const ASSETS_ROUTES: Routes = [
  { path: '', title: 'Assets', loadComponent: () => import('./pages/asset-list/asset-list').then((m) => m.AssetList) },
  { path: 'new', title: 'New asset', loadComponent: () => import('./pages/asset-form/asset-form').then((m) => m.AssetForm) },
  { path: ':id/edit', title: 'Edit asset', loadComponent: () => import('./pages/asset-form/asset-form').then((m) => m.AssetForm) },
];

// app.routes.ts, inside the MainLayout children (before '**')
{ path: 'assets', loadChildren: () => import('./features/assets/routes').then((m) => m.ASSETS_ROUTES) },
// admin-only page instead? add: canActivate: [roleGuard], data: { roles: ['admin'] }
```

Add a menu entry to `MAIN_NAV` (or `ADMIN_NAV`) in `layouts/main-layout/main-layout.ts`. Why: [§3.3](03-frontend.md#33-routing-and-lazy-loading), [§3.4](03-frontend.md#34-guards).

### Step 15: verify

```bash
ng build          # no errors, no budget warning
ng test --watch=false
```

Then log in as each role and walk the rules table from Step 4 in the browser.

---

## Done checklist

**Backend**
- [ ] app registered, `apps.py` name dotted
- [ ] model with `on_delete`, `related_name`, indexes; migration generated and committed
- [ ] admin registered (read-only where the API must be the only writer)
- [ ] rules table written down, encoded in `services.py`
- [ ] scoped `get_queryset` (404) + permission/service checks (403)
- [ ] serializers: nested read, id write, server-set fields not writable
- [ ] filters / search / ordering / pagination
- [ ] tests for every rule, including "refused and unchanged"; query count
- [ ] `openapi.yaml` regenerated without warnings

**Frontend**
- [ ] interfaces match the serializers
- [ ] service uses `environment.apiUrl`, returns typed Observables
- [ ] pages use shared `page-header`, `empty-state`, `table-skeleton`, `status-badge`-style components
- [ ] loading, empty, and error states; `notifyError` for page errors
- [ ] lazy route with `title`, guard if needed, menu item
- [ ] feature imports nothing from other features (move shared things to `shared/`)
- [ ] `ng build` clean

**Docs**
- [ ] a line in `docs/notes.md`
- [ ] new rules described in `docs/02-backend.md`
