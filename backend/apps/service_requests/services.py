"""Business rules for requests and categories. Views and permissions call these; they hold no rules themselves."""

from django.db.models import ProtectedError, QuerySet
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User

from .models import Category, Request


def is_admin(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def is_reviewer(user) -> bool:
    return user.is_authenticated and user.role == User.Role.REVIEWER


# --- Requests -------------------------------------------------------------


def scoped_requests(user) -> QuerySet[Request]:
    """Requests this user may see: admin all, reviewer own department minus drafts, staff own."""
    qs = Request.objects.select_related("category", "requester")
    if is_admin(user):
        return qs
    if is_reviewer(user):
        if user.department_id is None:
            return qs.none()
        return qs.filter(requester__department_id=user.department_id).exclude(
            status=Request.Status.DRAFT
        )
    return qs.filter(requester=user)


def can_modify(user, request: Request) -> bool:
    """Edit/delete rule: admins always; reviewers never; otherwise the requester, while draft."""
    if is_admin(user):
        return True
    if is_reviewer(user):
        return False
    return request.requester_id == user.id and request.status == Request.Status.DRAFT


def create_request(*, requester, **data) -> Request:
    """New requests always start as drafts owned by the caller."""
    return Request.objects.create(requester=requester, status=Request.Status.DRAFT, **data)


def update_request(request: Request, **data) -> Request:
    for field, value in data.items():
        setattr(request, field, value)
    request.save()
    return request


def delete_request(request: Request) -> None:
    request.delete()


# --- Categories -----------------------------------------------------------


def visible_categories(user) -> QuerySet[Category]:
    """Admins manage every category; everyone else only picks from active ones."""
    qs = Category.objects.all()
    return qs if is_admin(user) else qs.filter(is_active=True)


def delete_category(category: Category) -> None:
    try:
        category.delete()
    except ProtectedError:
        raise ValidationError(
            {"detail": "This category is used by existing requests. Deactivate it instead."}
        )
