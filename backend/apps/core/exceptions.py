import logging

from rest_framework import status
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger("apps.core.errors")


def api_exception_handler(exc, context):
    """Give every API error one shape: {"detail": str, "errors": {field: [messages]}}.

    Covers DRF errors (400/401/403/404/405/429...) and unexpected exceptions (500).
    """
    response = exception_handler(exc, context)
    if response is None:
        # Not an API exception: log it with the traceback and answer with a JSON 500, never HTML.
        view = context.get("view")
        logger.exception("unhandled_error view=%s", view.__class__.__name__ if view else "?")
        set_rollback()
        return Response(
            {"detail": "A server error occurred. Please try again later.", "errors": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = response.data
    if isinstance(exc, ValidationError):
        errors = data if isinstance(data, dict) else {"non_field_errors": data}
        non_field = errors.pop("detail", None) or errors.get("non_field_errors")
        if isinstance(non_field, list):
            non_field = non_field[0] if non_field else None
        response.data = {"detail": str(non_field) if non_field else "Invalid input.", "errors": errors}
    elif isinstance(exc, Throttled):
        wait = f"{int(exc.wait) + 1} seconds" if exc.wait else "a moment"
        response.data = {"detail": f"Too many attempts. Please wait {wait} and try again.", "errors": {}}
    elif isinstance(data, dict):
        data.setdefault("errors", {})
    return response
