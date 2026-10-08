from unittest import mock

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.service_requests import services
from apps.service_requests.models import Request, StatusHistory

from .factories import make_category, make_department, make_request, make_user

S = Request.Status


def action_url(pk, name):
    return reverse(f"request-{name.replace('_', '-')}", args=[pk])


class WorkflowTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.it = make_department("IT")
        cls.hr = make_department("HR")
        cls.category = make_category("Equipment")

        cls.staff = make_user("staff", department=cls.it)
        cls.staff_other = make_user("staff_other", department=cls.it)
        cls.reviewer = make_user("reviewer", User.Role.REVIEWER, cls.it)
        cls.reviewer_hr = make_user("reviewer_hr", User.Role.REVIEWER, cls.hr)
        cls.admin = make_user("admin", User.Role.ADMIN)

    def post(self, user, pk, action, remarks=None):
        self.client.force_authenticate(user)
        body = {} if remarks is None else {"remarks": remarks}
        return self.client.post(action_url(pk, action), body, format="json")

    def draft(self, requester=None, **extra):
        return make_request(requester or self.staff, self.category, "Laptop", S.DRAFT, **extra)

    def in_status(self, status, requester=None):
        return make_request(requester or self.staff, self.category, f"In {status}", status)


class HappyPathTests(WorkflowTestBase):
    def test_submit_review_approve_complete_writes_four_history_rows(self):
        req = self.draft()

        steps = [
            (self.staff, "submit", S.SUBMITTED),
            (self.reviewer, "start_review", S.IN_REVIEW),
            (self.reviewer, "approve", S.APPROVED),
            (self.admin, "complete", S.COMPLETED),
        ]
        for user, action, expected in steps:
            response = self.post(user, req.id, action)
            self.assertEqual(response.status_code, 200, (action, response.data))
            self.assertEqual(response.data["status"], expected)

        history = list(StatusHistory.objects.filter(request=req).order_by("changed_at", "id"))
        self.assertEqual(len(history), 4)
        self.assertEqual(
            [(h.from_status, h.to_status, h.changed_by) for h in history],
            [
                (S.DRAFT, S.SUBMITTED, self.staff),
                (S.SUBMITTED, S.IN_REVIEW, self.reviewer),
                (S.IN_REVIEW, S.APPROVED, self.reviewer),
                (S.APPROVED, S.COMPLETED, self.admin),
            ],
        )

    def test_action_returns_detail_with_new_available_actions(self):
        req = self.in_status(S.SUBMITTED)
        response = self.post(self.reviewer, req.id, "start_review")

        self.assertEqual(response.data["available_actions"], ["approve", "reject"])
        self.assertIn("description", response.data)


class RejectTests(WorkflowTestBase):
    def test_reject_requires_remarks(self):
        req = self.in_status(S.IN_REVIEW)

        for blank in (None, "", "   "):
            response = self.post(self.reviewer, req.id, "reject", blank)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(set(response.data), {"detail", "errors"})
            self.assertIn("remarks", response.data["errors"])

        response = self.post(self.reviewer, req.id, "reject", "  Budget not available  ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], S.REJECTED)
        self.assertEqual(StatusHistory.objects.get(request=req).remarks, "Budget not available")


class PermissionTests(WorkflowTestBase):
    def test_staff_cannot_approve(self):
        req = self.in_status(S.IN_REVIEW)  # staff's own request, visible to them

        self.assertEqual(self.post(self.staff, req.id, "approve").status_code, 403)

    def test_reviewer_from_another_department_cannot_act(self):
        req = self.in_status(S.SUBMITTED)

        response = self.post(self.reviewer_hr, req.id, "start_review")

        self.assertIn(response.status_code, (403, 404))
        self.assertEqual(response.status_code, 404)  # not even visible to them

    def test_reviewer_cannot_review_or_approve_own_request(self):
        submitted = self.in_status(S.SUBMITTED, requester=self.reviewer)
        in_review = self.in_status(S.IN_REVIEW, requester=self.reviewer)

        self.assertEqual(self.post(self.reviewer, submitted.id, "start_review").status_code, 403)
        response = self.post(self.reviewer, in_review.id, "approve")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "You cannot review your own request.")

    def test_admin_cannot_approve_or_reject_own_request(self):
        req = self.in_status(S.IN_REVIEW, requester=self.admin)

        self.assertEqual(self.post(self.admin, req.id, "approve").status_code, 403)
        self.assertEqual(self.post(self.admin, req.id, "reject", "no").status_code, 403)

    def test_requester_cannot_submit_someone_elses_draft(self):
        req = self.draft(requester=self.staff_other)

        self.assertEqual(self.post(self.staff, req.id, "submit").status_code, 404)  # not visible
        self.assertEqual(self.post(self.admin, req.id, "submit").status_code, 403)  # visible, not the requester
        req.refresh_from_db()
        self.assertEqual(req.status, S.DRAFT)

    def test_complete_is_admin_only(self):
        req = self.in_status(S.APPROVED)

        self.assertEqual(self.post(self.reviewer, req.id, "complete").status_code, 403)
        self.assertEqual(self.post(self.admin, req.id, "complete").status_code, 200)


class SubmitValidationTests(WorkflowTestBase):
    def test_submit_fails_for_inactive_category(self):
        req = self.draft()
        self.category.is_active = False
        self.category.save()

        response = self.post(self.staff, req.id, "submit")

        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.data["errors"])

    def test_submit_fails_for_empty_description(self):
        req = self.draft(description="   ")

        response = self.post(self.staff, req.id, "submit")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "This request is not ready to submit.")
        self.assertIn("description", response.data["errors"])


class InvalidTransitionTests(WorkflowTestBase):
    def test_approve_a_draft_is_400(self):
        req = self.draft()

        response = self.post(self.admin, req.id, "approve")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Cannot approve a request that is draft.")

    def test_complete_a_submitted_request_is_400(self):
        req = self.in_status(S.SUBMITTED)

        self.assertEqual(self.post(self.admin, req.id, "complete").status_code, 400)

    def test_final_states_reject_every_action(self):
        for final in (S.REJECTED, S.COMPLETED):
            req = self.in_status(final)
            for action in services.TRANSITIONS:
                user = self.staff if action == "submit" else self.admin
                response = self.post(user, req.id, action, "remarks")
                self.assertEqual(response.status_code, 400, (final, action))
            req.refresh_from_db()
            self.assertEqual(req.status, final)
            self.assertFalse(req.history.exists())


class AvailableActionsTests(WorkflowTestBase):
    def actions(self, user, req):
        self.client.force_authenticate(user)
        return self.client.get(reverse("request-detail", args=[req.id])).data["available_actions"]

    def test_available_actions_by_role_and_status(self):
        draft = self.draft()
        submitted = self.in_status(S.SUBMITTED)
        in_review = self.in_status(S.IN_REVIEW)
        approved = self.in_status(S.APPROVED)
        rejected = self.in_status(S.REJECTED)

        # staff (the requester)
        self.assertEqual(self.actions(self.staff, draft), ["submit"])
        self.assertEqual(self.actions(self.staff, submitted), [])
        self.assertEqual(self.actions(self.staff, in_review), [])
        # reviewer, same department
        self.assertEqual(self.actions(self.reviewer, submitted), ["start_review"])
        self.assertEqual(self.actions(self.reviewer, in_review), ["approve", "reject"])
        self.assertEqual(self.actions(self.reviewer, approved), [])
        # admin
        self.assertEqual(self.actions(self.admin, draft), [])  # not the requester
        self.assertEqual(self.actions(self.admin, in_review), ["approve", "reject"])
        self.assertEqual(self.actions(self.admin, approved), ["complete"])
        self.assertEqual(self.actions(self.admin, rejected), [])

    def test_reviewer_sees_no_review_actions_on_own_request(self):
        own = self.in_status(S.SUBMITTED, requester=self.reviewer)

        self.assertEqual(self.actions(self.reviewer, own), [])


class ReviewerOwnRequestTests(WorkflowTestBase):
    def test_reviewer_can_create_see_edit_and_submit_own_draft(self):
        self.client.force_authenticate(self.reviewer)
        created = self.client.post(
            reverse("request-list"),
            {"title": "Reviewer laptop", "description": "Mine", "category": self.category.id},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        pk = created.data["id"]

        self.assertIn(pk, {r["id"] for r in self.client.get(reverse("request-list")).data["results"]})
        patch = self.client.patch(reverse("request-detail", args=[pk]), {"title": "Renamed"}, format="json")
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(self.post(self.reviewer, pk, "submit").status_code, 200)


class HistoryEndpointTests(WorkflowTestBase):
    def test_history_is_newest_first_with_actor(self):
        req = self.draft()
        self.post(self.staff, req.id, "submit")
        self.post(self.reviewer, req.id, "start_review")

        self.client.force_authenticate(self.staff)
        response = self.client.get(reverse("request-history", args=[req.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([h["to_status"] for h in response.data], ["in_review", "submitted"])
        self.assertEqual(response.data[0]["changed_by"], {"id": self.reviewer.id, "name": "reviewer"})

    def test_staff_cannot_read_another_users_history(self):
        req = self.in_status(S.SUBMITTED, requester=self.staff_other)

        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(reverse("request-history", args=[req.id])).status_code, 404)

    def test_history_query_count_is_constant(self):
        req = self.draft()
        for user, action in [(self.staff, "submit"), (self.reviewer, "start_review"), (self.reviewer, "approve")]:
            self.post(user, req.id, action)

        self.client.force_authenticate(self.staff)
        with self.assertNumQueries(2):  # load request (scoped) + history with changed_by joined
            self.client.get(reverse("request-history", args=[req.id]))


class AtomicityTests(WorkflowTestBase):
    def test_failed_history_write_rolls_back_status_change(self):
        req = self.draft()

        with mock.patch.object(StatusHistory.objects, "create", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                services.perform_transition(req, self.staff, "submit")

        req.refresh_from_db()
        self.assertEqual(req.status, S.DRAFT)
        self.assertFalse(StatusHistory.objects.filter(request=req).exists())

    def test_rejected_action_changes_nothing(self):
        req = self.in_status(S.IN_REVIEW)

        self.post(self.reviewer, req.id, "reject", "")  # 400: missing remarks

        req.refresh_from_db()
        self.assertEqual(req.status, S.IN_REVIEW)
        self.assertFalse(req.history.exists())
