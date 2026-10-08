"""Attachment checks: name, extension, size, count, and the file's real type from its leading bytes."""

import os
import re
import unicodedata
import zipfile

from django.conf import settings
from rest_framework.exceptions import ValidationError

# Content type we store and serve for each allowed extension (never the browser-supplied one).
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_filename(name: str) -> str:
    """Display name only (never used on disk): no directories, no control characters, max 255."""
    name = unicodedata.normalize("NFC", name or "")
    name = name.replace("\\", "/").rsplit("/", 1)[-1]  # drop any path, Windows or POSIX
    name = _CONTROL_CHARS.sub("", name).strip().strip(".")
    if not name:
        name = "file"
    if len(name) > 255:
        stem, ext = os.path.splitext(name)
        name = stem[: 255 - len(ext)] + ext
    return name


def extension_of(name: str) -> str:
    return os.path.splitext(name)[1].lower().lstrip(".")


def _read_head(file, length=8) -> bytes:
    file.seek(0)
    head = file.read(length)
    file.seek(0)
    return head


def _is_office_zip(file, required_entry: str) -> bool:
    """docx/xlsx are ZIP archives; require the part that makes them a Word/Excel document."""
    if _read_head(file, 4) != b"PK\x03\x04":
        return False
    try:
        file.seek(0)
        with zipfile.ZipFile(file) as archive:
            return required_entry in archive.namelist()
    except zipfile.BadZipFile:
        return False
    finally:
        file.seek(0)


def content_matches_extension(file, ext: str) -> bool:
    head = _read_head(file)
    if ext == "pdf":
        return head.startswith(b"%PDF-")
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in ("jpg", "jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == "docx":
        return _is_office_zip(file, "word/document.xml")
    if ext == "xlsx":
        return _is_office_zip(file, "xl/workbook.xml")
    return False


def validate_attachment(file, existing_count: int) -> tuple[str, str]:
    """Raise ValidationError (errors on "file") or return (safe original name, content type)."""
    original_name = sanitize_filename(getattr(file, "name", ""))
    ext = extension_of(original_name)
    allowed = settings.ATTACHMENT_ALLOWED_EXTENSIONS
    max_bytes = settings.ATTACHMENT_MAX_BYTES

    def fail(message):
        raise ValidationError({"detail": message, "file": [message]})

    if existing_count >= settings.ATTACHMENT_MAX_PER_REQUEST:
        fail(f"A request can have at most {settings.ATTACHMENT_MAX_PER_REQUEST} attachments.")
    if ext not in allowed:
        fail(f"'.{ext or '?'}' files are not allowed. Allowed: {', '.join(allowed)}.")
    if file.size == 0:
        fail("The file is empty.")
    if file.size > max_bytes:
        fail(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
    if not content_matches_extension(file, ext):
        fail(f"The file content does not match its .{ext} extension.")
    return original_name, CONTENT_TYPES[ext]
