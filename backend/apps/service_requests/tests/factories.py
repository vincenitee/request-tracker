"""Tiny helpers to build test data without a factory library."""

import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile

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


# --- files ------------------------------------------------------------------

PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
EXE_BYTES = b"MZ\x90\x00" + b"\x00" * 60


def office_bytes(required_entry):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(required_entry, "<doc/>")
    return buffer.getvalue()


def upload(name="report.pdf", content=PDF_BYTES, content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)
