from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.service_requests.models import Request

from .factories import make_category, make_department, make_request, make_user

S = Request.Status
LIST_URL = reverse("request-list")


def detail_url(pk):
    return reverse("request-detail", args=[pk])


class RequestApiTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.it = make_department("IT")
        cls.hr = make_department("HR")
        cls.category = make_category("Equipment")

        cls.staff = make_user("staff", department=cls.it)
        cls.staff_other = make_user("staff_other", department=cls.it)
        cls.staff_hr = make_user("staff_hr", department=cls.hr)
        cls.reviewer = make_user("reviewer", User.Role.REVIEWER, cls.it)
        cls.admin = make_user("admin", User.Role.ADMIN)

        cls.own_draft = make_request(cls.staff, cls.category, "Own draft", S.DRAFT)
        cls.own_submitted = make_request(cls.staff, cls.category, "Own submitted", S.SUBMITTED)
        cls.other_draft = make_request(cls.staff_other, cls.category, "Colleague draft", S.DRAFT)
        cls.other_submitted = make_request(cls.staff_other, cls.category, "Colleague submitted", S.SUBMITTED)
        cls.hr_submitted = make_request(cls.staff_hr, cls.category, "HR submitted", S.SUBMITTED)

    def ids(self, response):
        return {item["id"] for item in response.data["results"]}


class ScopingTests(RequestApiTestBase):
    def test_staff_sees_only_own_requests(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ids(response), {self.own_draft.id, self.own_submitted.id})

    def test_reviewer_sees_same_department_non_drafts_only(self):
        self.client.force_authenticate(self.reviewer)
        response = self.client.get(LIST_URL)

        self.assertEqual(self.ids(response), {self.own_submitted.id, self.other_submitted.id})

    def test_reviewer_without_department_sees_nothing(self):
        self.client.force_authenticate(make_user("lonely_reviewer", User.Role.REVIEWER))
        response = self.client.get(LIST_URL)

        self.assertEqual(response.data["count"], 0)

    def test_admin_sees_all_requests(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(LIST_URL)

        self.assertEqual(response.data["count"], Request.objects.count())

    def test_staff_cannot_read_another_users_request(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(detail_url(self.other_submitted.id))

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_gets_401(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, 401)


class WriteRuleTests(RequestApiTestBase):
    def test_create_sets_requester_and_draft_status_server_side(self):
        self.client.force_authenticate(self.staff)
        payload = {
            "title": "New mouse",
            "description": "Wireless",
            "category": self.category.id,
            "priority": "high",
            "status": "approved",  # must be ignored
            "requester": self.admin.id,  # must be ignored
        }
        response = self.client.post(LIST_URL, payload, format="json")

        self.assertEqual(response.status_code, 201)
        created = Request.objects.get(pk=response.data["id"])
        self.assertEqual(created.requester, self.staff)
        self.assertEqual(created.status, S.DRAFT)
        self.assertEqual(response.data["category"], {"id": self.category.id, "name": "Equipment"})

    def test_requester_can_edit_and_delete_own_draft(self):
        self.client.force_authenticate(self.staff)

        response = self.client.patch(detail_url(self.own_draft.id), {"title": "Renamed"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Renamed")

        self.assertEqual(self.client.delete(detail_url(self.own_draft.id)).status_code, 204)

    def test_staff_cannot_edit_another_users_request(self):
        self.client.force_authenticate(self.staff)
        response = self.client.patch(detail_url(self.other_draft.id), {"title": "Hijack"}, format="json")

        self.assertEqual(response.status_code, 404)  # not even visible
        self.other_draft.refresh_from_db()
        self.assertEqual(self.other_draft.title, "Colleague draft")

    def test_requester_cannot_edit_or_delete_non_draft(self):
        self.client.force_authenticate(self.staff)

        patch = self.client.patch(detail_url(self.own_submitted.id), {"title": "Too late"}, format="json")
        delete = self.client.delete(detail_url(self.own_submitted.id))

        self.assertEqual(patch.status_code, 403)
        self.assertEqual(delete.status_code, 403)
        self.assertIn("detail", patch.data)

    def test_reviewer_cannot_edit_or_delete(self):
        self.client.force_authenticate(self.reviewer)

        patch = self.client.patch(detail_url(self.other_submitted.id), {"title": "Nope"}, format="json")
        delete = self.client.delete(detail_url(self.other_submitted.id))

        self.assertEqual(patch.status_code, 403)
        self.assertEqual(delete.status_code, 403)

    def test_admin_can_edit_any_request(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(detail_url(self.hr_submitted.id), {"priority": "high"}, format="json")

        self.assertEqual(response.status_code, 200)

    def test_inactive_category_is_rejected_on_create(self):
        inactive = make_category("Old stuff", is_active=False)
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            LIST_URL,
            {"title": "X", "description": "Y", "category": inactive.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.data["errors"])

    def test_blank_title_is_rejected_with_error_shape(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            LIST_URL,
            {"title": "   ", "description": "Y", "category": self.category.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {"detail", "errors"})
        self.assertIn("title", response.data["errors"])


class ListFeatureTests(RequestApiTestBase):
    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_filter_by_status(self):
        response = self.client.get(LIST_URL, {"status": "draft"})

        self.assertEqual(self.ids(response), {self.own_draft.id, self.other_draft.id})

    def test_filter_by_category(self):
        other_category = make_category("Leave")
        leave = make_request(self.staff, other_category, "Leave request")
        response = self.client.get(LIST_URL, {"category": other_category.id})

        self.assertEqual(self.ids(response), {leave.id})

    def test_search_matches_title_and_description(self):
        by_title = make_request(self.staff, self.category, "Broken projector")
        by_description = make_request(self.staff, self.category, "AV issue", description="The projector is dim")
        response = self.client.get(LIST_URL, {"search": "projector"})

        self.assertEqual(self.ids(response), {by_title.id, by_description.id})

    def test_ordering_by_priority_uses_rank_not_alphabet(self):
        Request.objects.all().delete()
        for priority in ("medium", "high", "low"):
            make_request(self.staff, self.category, f"P {priority}", priority=priority)

        response = self.client.get(LIST_URL, {"ordering": "priority"})

        self.assertEqual([r["priority"] for r in response.data["results"]], ["low", "medium", "high"])

    def test_pagination_shape(self):
        for i in range(12):
            make_request(self.staff, self.category, f"Bulk {i}")

        response = self.client.get(LIST_URL)

        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])

    def test_list_query_count_does_not_grow_with_rows(self):
        for i in range(12):
            make_request(self.staff, self.category, f"Bulk {i}")

        with self.assertNumQueries(2):  # COUNT + one SELECT with joins (no N+1)
            self.client.get(LIST_URL)
