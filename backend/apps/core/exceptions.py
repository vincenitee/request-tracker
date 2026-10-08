from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Give every API error one shape: {"detail": str, "errors": {field: [messages]}}."""
    response = exception_handler(exc, context)
    if response is None:
        return None  # unhandled exception -> Django's 500

    data = response.data
    if isinstance(exc, ValidationError):
        errors = data if isinstance(data, dict) else {"non_field_errors": data}
        non_field = errors.pop("detail", None) or errors.get("non_field_errors")
        if isinstance(non_field, list):
            non_field = non_field[0] if non_field else None
        response.data = {"detail": str(non_field) if non_field else "Invalid input.", "errors": errors}
    elif isinstance(data, dict):
        data.setdefault("errors", {})
    return response
