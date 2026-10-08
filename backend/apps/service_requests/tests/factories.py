"""Tiny helpers to build test data without a factory library."""

from apps.accounts.models import Department, User
from apps.service_requests.models import Category, Request


def make_user(username, role=User.Role.STAFF, department=None):
    return User.objects.create_user(username=username, password="pass12345", role=role, department=department)


def make_category(name="Equipment", is_active=True):
    return Category.objects.create(name=name, is_active=is_active)


def make_request(requester, category, title="Sample", status=Request.Status.DRAFT, **extra):
    return Request.objects.create(
        title=title,
        description=extra.pop("description", "Some details"),
        requester=requester,
        category=category,
        status=status,
        **extra,
    )


def make_department(name):
    return Department.objects.create(name=name)
