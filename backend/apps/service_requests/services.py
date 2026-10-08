"""Business rules for requests and categories. Views and permissions call these; they hold no rules themselves."""

import logging
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, ProtectedError, Q, QuerySet, Subquery
from django.db.models.functions import Coalesce
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.services import is_admin, is_reviewer

from .models import Attachment, Category, Comment, Request, StatusHistory
from .validators import validate_attachment

Status = Request.Status
workflow_log = logging.getLogger("apps.service_requests.workflow")

# is_admin / is_reviewer live in apps.accounts.services (imported above) and are re-exported here.


# --- Requests -------------------------------------------------------------


def _count_of(model) -> Coalesce:
    """Correlated COUNT subquery. Two Count() joins would multiply rows; subqueries do not."""
    counts = (
        model.objects.filter(request=OuterRef("pk"))
        .order_by()
        .values("request")
        .annotate(n=Count("pk"))
        .values("n")
    )
    return Coalesce(Subquery(counts, output_field=IntegerField()), 0)


def _visible_q(user) -> Q:
    """admin: all. staff: their own. reviewer: their own (any status) plus non-draft
    requests from their department (none from others if they have no department)."""
    if is_admin(user):
        return Q()
    own = Q(requester=user)
    if is_reviewer(user) and user.department_id is not None:
        return own | (Q(requester__department_id=user.department_id) & ~Q(status=Status.DRAFT))
    return own


def visible_requests(user) -> QuerySet[Request]:
    """Plain scoped queryset (no joins or annotations), for aggregates."""
    return Request.objects.filter(_visible_q(user))


def scoped_requests(user) -> QuerySet[Request]:
    """Requests this user may see, with comments_count and attachments_count annotated."""
    return (
        visible_requests(user)
        .select_related("category", "requester")
        .annotate(comments_count=_count_of(Comment), attachments_count=_count_of(Attachment))
    )


REVIEWABLE = (Status.SUBMITTED, Status.IN_REVIEW)


def needs_my_action_q(user) -> Q:
    """What waits on this user. Used by the dashboard count and the ?needs_my_action=true list filter.

    staff: own drafts. reviewer: submitted/in-review requests from their department that they did
    not create. admin: all submitted/in-review requests they did not create.
    """
    if is_admin(user):
        return Q(status__in=REVIEWABLE) & ~Q(requester=user)
    if is_reviewer(user):
        if user.department_id is None:
            return Q(pk__in=[])
        return Q(status__in=REVIEWABLE, requester__department_id=user.department_id) & ~Q(requester=user)
    return Q(requester=user, status=Status.DRAFT)


def dashboard_summary(user) -> dict:
    """Counts in ONE aggregate query (conditional COUNTs) plus one query for the recent list."""
    aggregates = {"total": Count("pk"), "needs_my_action": Count("pk", filter=needs_my_action_q(user))}
    aggregates |= {f"status__{value}": Count("pk", filter=Q(status=value)) for value in Status.values}
    aggregates |= {f"priority__{value}": Count("pk", filter=Q(priority=value)) for value in Request.Priority.values}
    counts = visible_requests(user).order_by().aggregate(**aggregates)

    return {
        "total": counts["total"],
        "by_status": {value: counts[f"status__{value}"] for value in Status.values},
        "by_priority": {value: counts[f"priority__{value}"] for value in Request.Priority.values},
        "needs_my_action": counts["needs_my_action"],
        "recent": list(scoped_requests(user).order_by("-created_at", "-id")[:5]),
    }


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
        # Logged only once committed, so a rolled-back transition is never reported as done.
        transaction.on_commit(
            lambda: workflow_log.info(
                "transition request_id=%s action=%s from=%s to=%s user_id=%s",
                locked.pk, action, from_status, transition.target, user.pk,
            )
        )
    return locked


def history_for(request: Request) -> QuerySet[StatusHistory]:
    """Newest first, with the actor joined in (no N+1)."""
    return request.history.select_related("changed_by").order_by("-changed_at", "-id")


# --- Comments -------------------------------------------------------------


def can_comment(user, request: Request) -> bool:
    """Anyone who can see the request (already enforced by the scoped queryset), except on drafts."""
    return request.status != Status.DRAFT


def can_delete_comment(user, comment: Comment) -> bool:
    return comment.author_id == user.id or is_admin(user)


def comments_for(request: Request) -> QuerySet[Comment]:
    return request.comments.select_related("author")


def add_comment(request: Request, user, body: str) -> Comment:
    if not can_comment(user, request):
        raise ValidationError({"detail": "Comments open once the request is submitted."})
    return Comment.objects.create(request=request, author=user, body=body)


def delete_comment(user, comment: Comment) -> None:
    if not can_delete_comment(user, comment):
        raise PermissionDenied("Only the author or an admin can delete this comment.")
    comment.delete()


# --- Attachments ----------------------------------------------------------


def can_manage_attachments(user, request: Request) -> bool:
    """Upload/delete: an admin at any status, otherwise the requester while the request is a draft."""
    if is_admin(user):
        return True
    return request.requester_id == user.id and request.status == Status.DRAFT


def attachments_for(request: Request) -> QuerySet[Attachment]:
    return request.attachments.select_related("uploaded_by")


def add_attachment(request: Request, user, file) -> Attachment:
    """Validate and store one file; the file write and the row INSERT succeed or fail together."""
    if not can_manage_attachments(user, request):
        raise PermissionDenied("Only the requester can add files while the request is a draft.")

    attachment = None
    try:
        with transaction.atomic():
            # Lock the request row so two parallel uploads cannot both pass the per-request limit.
            Request.objects.select_for_update().only("pk").get(pk=request.pk)
            original_name, content_type = validate_attachment(file, request.attachments.count())
            attachment = Attachment(
                request=request,
                original_name=original_name,
                content_type=content_type,
                size=file.size,
                uploaded_by=user,
            )
            attachment.file.save(original_name, file, save=False)  # written to disk under a UUID name
            attachment.save()
    except Exception:
        # INSERT or COMMIT failed after the file was written: remove it so no orphan is left.
        if attachment is not None and attachment.file:
            attachment.file.delete(save=False)
        raise
    return attachment


def delete_attachment(user, attachment: Attachment) -> None:
    if not can_manage_attachments(user, attachment.request):
        raise PermissionDenied("Only the requester can remove files while the request is a draft.")
    attachment.delete()  # the post_delete signal removes the file after commit


# --- Categories -----------------------------------------------------------


def visible_categories(user, include_inactive: bool = False) -> QuerySet[Category]:
    """Active categories for everyone; admins may also ask for inactive ones."""
    qs = Category.objects.all()
    return qs if include_inactive and is_admin(user) else qs.filter(is_active=True)


def delete_category(category: Category) -> None:
    try:
        category.delete()
    except ProtectedError:
        raise ValidationError(
            {"detail": "This category is used by existing requests. Deactivate it instead."}
        )
