"""Business rules for requests and categories. Views and permissions call these; they hold no rules themselves."""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import ProtectedError, Q, QuerySet
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User

from .models import Category, Request, StatusHistory

Status = Request.Status


def is_admin(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def is_reviewer(user) -> bool:
    return user.is_authenticated and user.role == User.Role.REVIEWER


# --- Requests -------------------------------------------------------------


def scoped_requests(user) -> QuerySet[Request]:
    """Requests this user may see.

    admin: all. staff: their own. reviewer: their own (any status) plus non-draft
    requests from their department (none from others if they have no department).
    """
    qs = Request.objects.select_related("category", "requester")
    if is_admin(user):
        return qs
    own = Q(requester=user)
    if is_reviewer(user) and user.department_id is not None:
        department = Q(requester__department_id=user.department_id) & ~Q(status=Status.DRAFT)
        return qs.filter(own | department)
    return qs.filter(own)


def can_modify(user, request: Request) -> bool:
    """Edit/delete rule: admins always; otherwise only the requester, and only while draft."""
    if is_admin(user):
        return True
    return request.requester_id == user.id and request.status == Status.DRAFT


def create_request(*, requester, **data) -> Request:
    """New requests always start as drafts owned by the caller."""
    return Request.objects.create(requester=requester, status=Status.DRAFT, **data)


def update_request(request: Request, **data) -> Request:
    for field, value in data.items():
        setattr(request, field, value)
    request.save()
    return request


def delete_request(request: Request) -> None:
    request.delete()


# --- Workflow -------------------------------------------------------------

REQUESTER, REVIEWERS, ADMINS = "requester", "reviewers", "admins"


@dataclass(frozen=True)
class Transition:
    source: str
    target: str
    actor: str  # REQUESTER, REVIEWERS (reviewer or admin) or ADMINS
    label: str  # used in error messages: "Cannot <label> a request that is ..."


# The only allowed transitions. rejected and completed are final (nothing leaves them).
TRANSITIONS: dict[str, Transition] = {
    "submit": Transition(Status.DRAFT, Status.SUBMITTED, REQUESTER, "submit"),
    "start_review": Transition(Status.SUBMITTED, Status.IN_REVIEW, REVIEWERS, "start reviewing"),
    "approve": Transition(Status.IN_REVIEW, Status.APPROVED, REVIEWERS, "approve"),
    "reject": Transition(Status.IN_REVIEW, Status.REJECTED, REVIEWERS, "reject"),
    "complete": Transition(Status.APPROVED, Status.COMPLETED, ADMINS, "complete"),
}


def _permission_error(request: Request, user, transition: Transition) -> str | None:
    """Why this user may not perform the transition on this request, or None if they may."""
    if transition.actor == REQUESTER:
        if request.requester_id != user.id:
            return "Only the requester can submit this request."
        return None

    if transition.actor == ADMINS:
        return None if is_admin(user) else "Only an admin can do this."

    # REVIEWERS: reviewer or admin, never on their own request, reviewers only in their department.
    if not (is_reviewer(user) or is_admin(user)):
        return "Only reviewers and admins can review requests."
    if request.requester_id == user.id:
        return "You cannot review your own request."
    if is_reviewer(user) and (
        user.department_id is None or request.requester.department_id != user.department_id
    ):
        return "You can only review requests from your own department."
    return None


def get_available_actions(request: Request, user) -> list[str]:
    """Action names this user may perform on the request right now, in TRANSITIONS order."""
    return [
        name
        for name, transition in TRANSITIONS.items()
        if request.status == transition.source and _permission_error(request, user, transition) is None
    ]


def _submit_errors(request: Request) -> dict[str, list[str]]:
    errors = {}
    if not request.title.strip():
        errors["title"] = ["A title is required before submitting."]
    if not request.description.strip():
        errors["description"] = ["A description is required before submitting."]
    if request.category_id is None or not request.category.is_active:
        errors["category"] = ["Choose an active category before submitting."]
    return errors


def perform_transition(request: Request, user, action: str, remarks: str = "") -> Request:
    """Validate and apply one workflow action, writing a StatusHistory row in the same transaction.

    Raises PermissionDenied (403) when the user may not act, ValidationError (400) when the
    request is in the wrong state or the input is invalid.
    """
    transition = TRANSITIONS.get(action)
    if transition is None:
        raise ValidationError({"detail": f"Unknown action '{action}'."})
    remarks = (remarks or "").strip()

    with transaction.atomic():
        # Lock the row and re-read it, so two simultaneous actions cannot both pass the checks.
        locked = Request.objects.select_for_update().get(pk=request.pk)

        if error := _permission_error(locked, user, transition):
            raise PermissionDenied(error)

        if locked.status != transition.source:
            raise ValidationError(
                {"detail": f"Cannot {transition.label} a request that is {locked.get_status_display().lower()}."}
            )

        if action == "submit" and (errors := _submit_errors(locked)):
            raise ValidationError({"detail": "This request is not ready to submit.", **errors})

        if action == "reject" and not remarks:
            raise ValidationError(
                {"detail": "Remarks are required to reject a request.", "remarks": ["This field is required."]}
            )

        from_status = locked.status
        locked.status = transition.target
        locked.save(update_fields=["status", "updated_at"])
        StatusHistory.objects.create(
            request=locked,
            from_status=from_status,
            to_status=transition.target,
            changed_by=user,
            remarks=remarks,
        )
    return locked


def history_for(request: Request) -> QuerySet[StatusHistory]:
    """Newest first, with the actor joined in (no N+1)."""
    return request.history.select_related("changed_by").order_by("-changed_at", "-id")


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
