from functools import wraps

from django.conf import settings
from django.http import Http404, JsonResponse
from django.views.defaults import page_not_found, server_error
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(responses=inline_serializer("Health", {"status": serializers.CharField()}), auth=[])
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


def api_not_found(request, *args, **kwargs):
    """Catch-all for unknown /api/ URLs: JSON 404 even when DEBUG is on (Django would render HTML)."""
    return JsonResponse({"detail": "Not found.", "errors": {}}, status=404)


def handler404(request, exception=None):
    """Used when DEBUG is False: JSON for /api/, Django's normal page elsewhere."""
    if request.path.startswith("/api/"):
        return api_not_found(request)
    return page_not_found(request, exception)


def handler500(request):
    """Errors that escape DRF's handler (e.g. in middleware): JSON for /api/."""
    if request.path.startswith("/api/"):
        return JsonResponse({"detail": "A server error occurred. Please try again later.", "errors": {}}, status=500)
    return server_error(request)


def debug_only(view):
    """Serve the view only while DEBUG is True (checked per request), otherwise 404."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not settings.DEBUG:
            raise Http404
        return view(request, *args, **kwargs)

    return wrapped
