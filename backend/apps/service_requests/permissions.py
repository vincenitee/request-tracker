from rest_framework.permissions import SAFE_METHODS, BasePermission

from . import services


class IsAdminRoleOrReadOnly(BasePermission):
    """Any authenticated user may read; only admins may write."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or services.is_admin(request.user)


class CanModifyRequest(BasePermission):
    """Reads are already limited by the scoped queryset; writes follow services.can_modify."""

    message = "Only the requester can change a request, and only while it is a draft."

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or services.can_modify(request.user, obj)
