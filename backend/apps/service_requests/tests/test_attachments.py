import os
import re
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.service_requests.models import Attachment, Request
from apps.service_requests.validators import sanitize_filename

from .factories import (
    EXE_BYTES,
    JPEG_BYTES,
    PDF_BYTES,
    PNG_BYTES,
    make_category,
    make_department,
    make_request,
    make_user,
    office_bytes,
    upload,
)
from .media import TempMediaMixin

S = Request.Status
MB = 1024 * 1024


def list_url(pk):
    return reverse("request-attachments", args=[pk])


def item_url(pk, attachment_id):
    return reverse("request-delete-attachment", kwargs={"pk": pk, "attachment_id": attachment_id})


def download_url(pk, attachment_id):
    return reverse("request-download-attachment", kwargs={"pk": pk, "attachment_id": attachment_id})


class AttachmentTestBase(TempMediaMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        it = make_department("IT")
        cls.category = make_category()
        cls.staff = make_user("staff", department=it)
        cls.outsider = make_user("outsider", department=it)
        cls.reviewer = make_user("reviewer", User.Role.REVIEWER, it)
        cls.admin = make_user("admin", User.Role.ADMIN)

    def setUp(self):
        self.draft = make_request(self.staff, self.category, "Draft", S.DRAFT)
        self.submitted = make_request(self.staff, self.category, "Submitted", S.SUBMITTED)

    def send(self, user, pk, file):
        self.client.force_authenticate(user)
        return self.client.post(list_url(pk), {"file": file}, format="multipart")

    def stored_path(self, attachment_id):
        return Path(Attachment.objects.get(pk=attachment_id).file.path)


class UploadTests(AttachmentTestBase):
    def test_tests_use_a_temporary_media_root(self):
        self.assertIn("rt-test-media-", str(settings.MEDIA_ROOT))

    def test_requester_can_upload_to_draft(self):
        response = self.send(self.staff, self.draft.id, upload("Quote 2026.pdf", content_type="text/plain"))

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["original_name"], "Quote 2026.pdf")
        self.assertEqual(response.data["content_type"], "application/pdf")  # detected, not the client's
        self.assertEqual(response.data["size"], len(PDF_BYTES))
        self.assertTrue(response.data["can_delete"])
        self.assertTrue(self.stored_path(response.data["id"]).exists())

    def test_stored_filename_is_random_not_the_original(self):
        response = self.send(self.staff, self.draft.id, upload("my secret plan.pdf"))

        stored = Attachment.objects.get(pk=response.data["id"]).file.name
        self.assertNotIn("secret", stored)
        self.assertRegex(os.path.basename(stored), r"^[0-9a-f]{32}\.pdf$")
        self.assertTrue(stored.startswith("attachments/"))

    def test_original_name_is_sanitized(self):
        response = self.send(self.staff, self.draft.id, upload("re\x07po\x1frt.pdf"))

        self.assertEqual(response.data["original_name"], "report.pdf")
        self.assertEqual(sanitize_filename("..\\..\\windows\\evil.pdf"), "evil.pdf")
        self.assertEqual(sanitize_filename("../../etc/passwd.pdf"), "passwd.pdf")
        self.assertEqual(len(sanitize_filename("a" * 300 + ".pdf")), 255)

    def test_all_allowed_types_with_matching_content_are_accepted(self):
        files = [
            upload("a.png", PNG_BYTES),
            upload("b.JPG", JPEG_BYTES),
            upload("c.docx", office_bytes("word/document.xml")),
            upload("d.xlsx", office_bytes("xl/workbook.xml")),
        ]
        for f in files:
            self.assertEqual(self.send(self.staff, self.draft.id, f).status_code, 201, f.name)

    def test_upload_fails_once_submitted_but_admin_can_still_upload(self):
        self.assertEqual(self.send(self.staff, self.submitted.id, upload()).status_code, 403)
        self.assertEqual(self.send(self.admin, self.submitted.id, upload()).status_code, 201)

    def test_reviewer_cannot_upload(self):
        response = self.send(self.reviewer, self.submitted.id, upload())

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Attachment.objects.exists())


class RejectionTests(AttachmentTestBase):
    def assert_rejected(self, file, fragment, status_code=400):
        response = self.send(self.staff, self.draft.id, file)
        self.assertEqual(response.status_code, status_code, response.data)
        self.assertIn(fragment, response.data["detail"])
        return response

    def test_disallowed_extension(self):
        response = self.assert_rejected(upload("setup.exe", EXE_BYTES), "not allowed")
        self.assertIn("file", response.data["errors"])

    def test_oversize_file(self):
        self.assert_rejected(upload("big.pdf", PDF_BYTES + b"0" * (5 * MB)), "larger than 5 MB")

    def test_far_oversize_body_is_refused_before_parsing(self):
        self.assert_rejected(upload("huge.pdf", PDF_BYTES + b"0" * (6 * MB)), "larger than 5 MB", status_code=413)

    def test_empty_file(self):
        self.assert_rejected(upload("empty.pdf", b""), "empty")

    def test_sixth_file(self):
        for i in range(5):
            self.assertEqual(self.send(self.staff, self.draft.id, upload(f"f{i}.pdf")).status_code, 201)

        self.assert_rejected(upload("f5.pdf"), "at most 5")
        self.assertEqual(self.draft.attachments.count(), 5)

    def test_content_that_does_not_match_extension(self):
        self.assert_rejected(upload("invoice.pdf", EXE_BYTES), "does not match")
        self.assert_rejected(upload("photo.png", PDF_BYTES), "does not match")
        self.assert_rejected(upload("plain.docx", office_bytes("random/file.xml")), "does not match")

    def test_rejected_uploads_leave_no_files(self):
        self.send(self.staff, self.draft.id, upload("invoice.pdf", EXE_BYTES))

        media = Path(settings.MEDIA_ROOT)
        self.assertEqual([p for p in media.rglob("*") if p.is_file()], [])

    def test_failed_db_write_leaves_no_orphan_file(self):
        with mock.patch.object(Attachment, "save", side_effect=RuntimeError("db down")):
            with self.assertLogs("apps.core.errors", level="ERROR"), self.assertLogs("django.request", level="ERROR"):
                response = self.send(self.staff, self.draft.id, upload())

        self.assertEqual(response.status_code, 500)  # JSON 500 from the exception handler
        self.assertEqual(set(response.json()), {"detail", "errors"})

        media = Path(settings.MEDIA_ROOT)
        self.assertEqual([p for p in media.rglob("*") if p.is_file()], [])


class VisibilityAndDownloadTests(AttachmentTestBase):
    def setUp(self):
        super().setUp()
        response = self.send(self.staff, self.draft.id, upload("Quote Ñ 2026.pdf"))
        self.attachment_id = response.data["id"]

    def test_user_who_cannot_see_request_gets_404_everywhere(self):
        self.client.force_authenticate(self.outsider)
        pk, aid = self.draft.id, self.attachment_id

        self.assertEqual(self.client.get(list_url(pk)).status_code, 404)
        self.assertEqual(self.send(self.outsider, pk, upload()).status_code, 404)
        self.assertEqual(self.client.delete(item_url(pk, aid)).status_code, 404)
        self.assertEqual(self.client.get(download_url(pk, aid)).status_code, 404)

    def test_download_streams_file_with_safe_headers(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(download_url(self.draft.id, self.attachment_id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), PDF_BYTES)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        disposition = response["Content-Disposition"]
        self.assertTrue(disposition.startswith("attachment;"), disposition)
        self.assertIn("filename*=utf-8''Quote%20%C3%91%202026.pdf", disposition)

    def test_reviewer_can_list_and_download_but_not_delete(self):
        # Attach to the submitted request as admin (the requester can no longer upload there).
        aid = self.send(self.admin, self.submitted.id, upload("spec.pdf")).data["id"]

        self.client.force_authenticate(self.reviewer)
        listing = self.client.get(list_url(self.submitted.id))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual([(a["original_name"], a["can_delete"]) for a in listing.data], [("spec.pdf", False)])
        self.assertEqual(self.client.get(download_url(self.submitted.id, aid)).status_code, 200)
        self.assertEqual(self.client.delete(item_url(self.submitted.id, aid)).status_code, 403)

    def test_list_query_count_is_constant(self):
        for i in range(3):
            self.send(self.staff, self.draft.id, upload(f"more{i}.pdf"))

        self.client.force_authenticate(self.staff)
        with self.assertNumQueries(2):  # load request (scoped) + attachments with uploader joined
            self.client.get(list_url(self.draft.id))


class DeleteTests(AttachmentTestBase):
    def test_deleting_an_attachment_removes_the_file(self):
        aid = self.send(self.staff, self.draft.id, upload()).data["id"]
        path = self.stored_path(aid)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(item_url(self.draft.id, aid))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Attachment.objects.filter(pk=aid).exists())
        self.assertFalse(path.exists())

    def test_deleting_a_draft_removes_its_files(self):
        aid = self.send(self.staff, self.draft.id, upload()).data["id"]
        path = self.stored_path(aid)

        with self.captureOnCommitCallbacks(execute=True):
            self.client.delete(reverse("request-detail", args=[self.draft.id]))

        self.assertFalse(path.exists())

    def test_requester_cannot_delete_after_submit_but_admin_can(self):
        aid = self.send(self.admin, self.submitted.id, upload()).data["id"]

        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.delete(item_url(self.submitted.id, aid)).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(item_url(self.submitted.id, aid)).status_code, 204)

    def test_no_public_media_url(self):
        aid = self.send(self.staff, self.draft.id, upload()).data["id"]
        stored = Attachment.objects.get(pk=aid).file.name

        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(f"/media/{stored}").status_code, 404)
        self.assertFalse(re.search(r"/media/", str(self.client.get(list_url(self.draft.id)).data)))
