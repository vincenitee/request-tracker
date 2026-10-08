from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.service_requests.models import Request

from .factories import make_category, make_department, make_request, make_user

S, P = Request.Status, Request.Priority
SUMMARY_URL = reverse("dashboard-summary")
LIST_URL = reverse("request-list")


class DashboardTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        it, hr = make_department("IT"), make_department("HR")
        cat = make_category()
        cls.staff = make_user("staff", department=it)
        cls.colleague = make_user("colleague", department=it)
        cls.staff_hr = make_user("staff_hr", department=hr)
        cls.reviewer = make_user("reviewer", User.Role.REVIEWER, it)
        cls.admin = make_user("admin", User.Role.ADMIN)

        make_request(cls.staff, cat, "own draft", S.DRAFT, priority=P.HIGH)
        make_request(cls.staff, cat, "own draft 2", S.DRAFT)
        make_request(cls.staff, cat, "own submitted", S.SUBMITTED)
        make_request(cls.staff, cat, "own approved", S.APPROVED, priority=P.LOW)
        make_request(cls.colleague, cat, "colleague in review", S.IN_REVIEW)
        make_request(cls.colleague, cat, "colleague draft", S.DRAFT)
        make_request(cls.staff_hr, cat, "hr submitted", S.SUBMITTED)
        make_request(cls.reviewer, cat, "reviewer own submitted", S.SUBMITTED)
        make_request(cls.admin, cat, "admin own in review", S.IN_REVIEW)

    def summary(self, user):
        self.client.force_authenticate(user)
        response = self.client.get(SUMMARY_URL)
        self.assertEqual(response.status_code, 200)
        return response.data

    def list_count(self, user, **params):
        self.client.force_authenticate(user)
        return self.client.get(LIST_URL, params).data["count"]

    def test_staff_counts_cover_only_own_requests_with_zero_statuses_present(self):
        data = self.summary(self.staff)

        self.assertEqual(data["total"], 4)
        self.assertEqual(
            data["by_status"],
            {"draft": 2, "submitted": 1, "in_review": 0, "approved": 1, "rejected": 0, "completed": 0},
        )
        self.assertEqual(data["by_priority"], {"low": 1, "medium": 2, "high": 1})
        self.assertEqual(data["needs_my_action"], 2)  # own drafts
        self.assertEqual({r["title"] for r in data["recent"]}, {"own draft", "own draft 2", "own submitted", "own approved"})

    def test_reviewer_needs_my_action_excludes_own_and_other_departments(self):
        data = self.summary(self.reviewer)

        # visible: IT non-drafts (staff submitted/approved, colleague in review, own submitted)
        self.assertEqual(data["total"], 4)
        self.assertEqual(data["by_status"]["draft"], 0)
        # waiting on the reviewer: staff submitted + colleague in review (own submitted and HR excluded)
        self.assertEqual(data["needs_my_action"], 2)

    def test_admin_sees_all_and_needs_my_action_excludes_own(self):
        data = self.summary(self.admin)

        self.assertEqual(data["total"], Request.objects.count())
        # submitted/in review: own submitted, colleague in review, hr submitted, reviewer own submitted
        # (admin's own in-review request excluded)
        self.assertEqual(data["needs_my_action"], 4)

    def test_counts_match_the_scoped_list_including_needs_my_action_filter(self):
        for user in (self.staff, self.reviewer, self.admin):
            data = self.summary(user)
            self.assertEqual(data["total"], self.list_count(user), user.username)
            for status_value, n in data["by_status"].items():
                self.assertEqual(n, self.list_count(user, status=status_value), (user.username, status_value))
            self.assertEqual(data["needs_my_action"], self.list_count(user, needs_my_action="true"), user.username)

    def test_recent_is_newest_first_and_at_most_five(self):
        data = self.summary(self.admin)

        self.assertEqual(len(data["recent"]), 5)
        created = [r["created_at"] for r in data["recent"]]
        self.assertEqual(created, sorted(created, reverse=True))
        self.assertIn("comments_count", data["recent"][0])

    def test_query_count_is_constant_as_data_grows(self):
        self.client.force_authenticate(self.admin)
        with CaptureQueriesContext(connection) as before:
            self.client.get(SUMMARY_URL)

        cat = make_category("Extra")
        for i in range(30):
            make_request(self.staff, cat, f"bulk {i}", S.SUBMITTED)
        with CaptureQueriesContext(connection) as after:
            self.client.get(SUMMARY_URL)

        self.assertEqual(len(before), len(after))
        self.assertLessEqual(len(after), 2)  # one aggregate + one "recent" query

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(SUMMARY_URL).status_code, 401)
