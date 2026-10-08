from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.service_requests.models import Comment, Request

from .factories import make_category, make_department, make_request, make_user

S = Request.Status


def comments_url(pk):
    return reverse("request-comments", args=[pk])


def comment_url(pk, comment_id):
    return reverse("request-delete-comment", kwargs={"pk": pk, "comment_id": comment_id})


class CommentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        it = make_department("IT")
        category = make_category()
        cls.staff = make_user("staff", department=it)
        cls.outsider = make_user("outsider", department=it)
        cls.reviewer = make_user("reviewer", User.Role.REVIEWER, it)
        cls.admin = make_user("admin", User.Role.ADMIN)
        cls.submitted = make_request(cls.staff, category, "Submitted", S.SUBMITTED)
        cls.draft = make_request(cls.staff, category, "Draft", S.DRAFT)

    def post(self, user, pk, body):
        self.client.force_authenticate(user)
        return self.client.post(comments_url(pk), {"body": body}, format="json")

    def test_comment_on_submitted_request_works_for_requester_and_reviewer(self):
        first = self.post(self.staff, self.submitted.id, "  Any update?  ")
        second = self.post(self.reviewer, self.submitted.id, "Looking at it today.")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["body"], "Any update?")  # stripped
        self.assertEqual(first.data["author"]["id"], self.staff.id)
        self.assertEqual(second.status_code, 201)

        self.client.force_authenticate(self.staff)
        listing = self.client.get(comments_url(self.submitted.id)).data
        self.assertEqual([c["body"] for c in listing], ["Any update?", "Looking at it today."])  # oldest first
        self.assertEqual([c["can_delete"] for c in listing], [True, False])

    def test_comment_on_draft_is_rejected(self):
        response = self.post(self.staff, self.draft.id, "Too early")

        self.assertEqual(response.status_code, 400)
        self.assertIn("submitted", response.data["detail"])
        self.assertFalse(Comment.objects.exists())

    def test_empty_and_too_long_bodies_are_rejected(self):
        for body in ("", "    ", "x" * 2001):
            response = self.post(self.staff, self.submitted.id, body)
            self.assertEqual(response.status_code, 400, repr(body[:10]))
            self.assertIn("body", response.data["errors"])

    def test_user_who_cannot_see_request_gets_404_everywhere(self):
        comment = Comment.objects.create(request=self.submitted, author=self.staff, body="hi")
        self.client.force_authenticate(self.outsider)

        self.assertEqual(self.client.get(comments_url(self.submitted.id)).status_code, 404)
        self.assertEqual(self.post(self.outsider, self.submitted.id, "hello").status_code, 404)
        self.assertEqual(self.client.delete(comment_url(self.submitted.id, comment.id)).status_code, 404)

    def test_only_author_or_admin_can_delete(self):
        mine = Comment.objects.create(request=self.submitted, author=self.staff, body="mine")
        theirs = Comment.objects.create(request=self.submitted, author=self.reviewer, body="theirs")

        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.delete(comment_url(self.submitted.id, theirs.id)).status_code, 403)
        self.assertEqual(self.client.delete(comment_url(self.submitted.id, mine.id)).status_code, 204)

        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(comment_url(self.submitted.id, theirs.id)).status_code, 204)
        self.assertFalse(Comment.objects.exists())

    def test_comment_id_from_another_request_is_404(self):
        other = make_request(self.staff, self.submitted.category, "Other", S.SUBMITTED)
        comment = Comment.objects.create(request=other, author=self.staff, body="elsewhere")

        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.delete(comment_url(self.submitted.id, comment.id)).status_code, 404)

    def test_counts_in_list_and_detail_without_extra_queries(self):
        for i in range(3):
            Comment.objects.create(request=self.submitted, author=self.staff, body=f"c{i}")
        for i in range(12):
            make_request(self.staff, self.submitted.category, f"Bulk {i}", S.SUBMITTED)

        self.client.force_authenticate(self.staff)
        with self.assertNumQueries(2):  # COUNT + one SELECT with joins and count subqueries
            listing = self.client.get(reverse("request-list"), {"search": "Submitted"})
        row = next(r for r in listing.data["results"] if r["id"] == self.submitted.id)
        self.assertEqual((row["comments_count"], row["attachments_count"]), (3, 0))

        detail = self.client.get(reverse("request-detail", args=[self.submitted.id])).data
        self.assertEqual(detail["comments_count"], 3)
