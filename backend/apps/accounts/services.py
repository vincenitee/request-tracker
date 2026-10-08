"""Business rules for users and departments. Admin views call these; they hold no rules themselves."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import Department, User

ADMIN, REVIEWER = User.Role.ADMIN, User.Role.REVIEWER


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.role == ADMIN)


def is_reviewer(user) -> bool:
    return bool(user and user.is_authenticated and user.role == REVIEWER)


def _fail(field: str, message: str):
    raise ValidationError({"detail": message, field: [message]})


def check_password_strength(password: str, user: User | None = None) -> None:
    """Django's AUTH_PASSWORD_VALIDATORS, reported as a 400 on the "password" field."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"detail": exc.messages[0], "password": exc.messages})


def _check_user_rules(actor: User, target: User | None, *, role, department, is_active) -> None:
    """Rules for the final state of a user after a create/update. target is None on create."""
    if role == REVIEWER and department is None:
        _fail("department", "A reviewer must belong to a department.")

    if target is None:
        return
    if target.pk == actor.pk:
        if not is_active:
            _fail("is_active", "You cannot deactivate your own account.")
        if role != target.role:
            _fail("role", "You cannot change your own role.")

    was_active_admin = target.role == ADMIN and target.is_active
    stays_active_admin = role == ADMIN and is_active
    if was_active_admin and not stays_active_admin:
        # Lock the active admins so two admins cannot demote each other at the same time.
        others = User.objects.select_for_update().filter(role=ADMIN, is_active=True).exclude(pk=target.pk)
        if not list(others.values_list("pk", flat=True)):
            field = "is_active" if not is_active else "role"
            _fail(field, "The last active admin cannot be deactivated or demoted.")


@transaction.atomic
def create_user(actor: User, *, password: str, **data) -> User:
    _check_user_rules(
        actor, None, role=data.get("role", User.Role.STAFF), department=data.get("department"),
        is_active=data.get("is_active", True),
    )
    user = User(**data)
    check_password_strength(password, user)
    user.set_password(password)
    user.save()
    return user


@transaction.atomic
def update_user(actor: User, user: User, **data) -> User:
    _check_user_rules(
        actor,
        user,
        role=data.get("role", user.role),
        department=data.get("department", user.department),
        is_active=data.get("is_active", user.is_active),
    )
    for field, value in data.items():
        setattr(user, field, value)
    user.save()
    return user


def set_password(user: User, password: str) -> None:
    check_password_strength(password, user)
    user.set_password(password)
    user.save(update_fields=["password"])


def delete_department(department: Department) -> None:
    count = department.users.count()
    if count:
        noun = "user is" if count == 1 else "users are"
        raise ValidationError(
            {"detail": f"{count} {noun} assigned to this department. Move them to another department first."}
        )
    department.delete()
