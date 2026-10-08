from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import api_not_found, debug_only, health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.service_requests.urls")),
    # OpenAPI schema and Swagger UI: routed always, but 404 unless DEBUG is True (checked per request).
    path("api/v1/schema/", debug_only(SpectacularAPIView.as_view()), name="schema"),
    path("api/v1/docs/", debug_only(SpectacularSwaggerView.as_view(url_name="schema")), name="swagger-ui"),
    # Anything else under /api/ is a JSON 404, never an HTML page.
    re_path(r"^api/", api_not_found),
]

handler404 = "apps.core.views.handler404"
handler500 = "apps.core.views.handler500"
