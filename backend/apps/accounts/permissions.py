from rest_framework.permissions import BasePermission

from . import services


class IsAdminRole(BasePermission):
    """Only users with role=admin (our app role, not Django's is_staff/is_superuser)."""

    message = "Only admins can do this."

    def has_permission(self, request, view):
        return services.is_admin(request.user)
