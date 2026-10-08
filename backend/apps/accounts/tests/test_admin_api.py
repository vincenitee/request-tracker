import json

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Department, User
from apps.service_requests.tests.factories import make_category, make_request

USERS_URL = reverse("user-list")
DEPARTMENTS_URL = reverse("department-list")
STRONG = "Correct-Horse-42"


def user_url(pk):
    return reverse("user-detail", args=[pk])


class AdminApiTestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.it = Department.objects.create(name="IT")
        cls.empty_dept = Department.objects.create(name="Empty")
        cls.admin = User.objects.create_user("admin", password=STRONG, role=User.Role.ADMIN)
        cls.staff = User.objects.create_user("staff", password=STRONG, department=cls.it)
        cls.reviewer = User.objects.create_user("reviewer", password=STRONG, role=User.Role.REVIEWER, department=cls.it)

    def as_admin(self):
        self.client.force_authenticate(self.admin)


class PermissionTests(AdminApiTestBase):
    def test_non_admins_get_403_on_users_and_departments(self):
        for user in (self.staff, self.reviewer):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(USERS_URL).status_code, 403)
            self.assertEqual(self.client.post(USERS_URL, {}, format="json").status_code, 403)
            self.assertEqual(self.client.patch(user_url(self.staff.id), {"is_active": False}, format="json").status_code, 403)
            self.assertEqual(self.client.get(DEPARTMENTS_URL).status_code, 403)
            self.assertEqual(self.client.post(DEPARTMENTS_URL, {"name": "X"}, format="json").status_code, 403)
            self.assertEqual(self.client.delete(reverse("department-detail", args=[self.empty_dept.id])).status_code, 403)

    def test_there_is_no_delete_endpoint_for_users(self):
        self.as_admin()
        self.assertEqual(self.client.delete(user_url(self.staff.id)).status_code, 405)


class UserCrudTests(AdminApiTestBase):
    def test_list_search_filter_and_pagination(self):
        self.as_admin()
        response = self.client.get(USERS_URL, {"role": "reviewer"})
        self.assertEqual([u["username"] for u in response.data["results"]], ["reviewer"])
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})

        response = self.client.get(USERS_URL, {"search": "sta"})
        self.assertEqual([u["username"] for u in response.data["results"]], ["staff"])

    def test_create_validates_password(self):
        self.as_admin()
        for weak in ("123", "password", "newperson"):
            response = self.client.post(
                USERS_URL, {"username": "newperson", "password": weak, "role": "staff"}, format="json"
            )
            self.assertEqual(response.status_code, 400, weak)
            self.assertIn("password", response.data["errors"])

        missing = self.client.post(USERS_URL, {"username": "newperson"}, format="json")
        self.assertIn("password", missing.data["errors"])

    def test_create_works_and_new_user_can_log_in(self):
        self.as_admin()
        response = self.client.post(
            USERS_URL,
            {"username": "newperson", "password": STRONG, "first_name": "New", "role": "staff", "department": self.it.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["department"], {"id": self.it.id, "name": "IT"})
        self.assertTrue(User.objects.get(username="newperson").check_password(STRONG))

        self.client.force_authenticate(None)
        login = self.client.post(reverse("token_obtain_pair"), {"username": "newperson", "password": STRONG}, format="json")
        self.assertEqual(login.status_code, 200)

    def test_password_never_appears_in_responses(self):
        self.as_admin()
        created = self.client.post(USERS_URL, {"username": "newperson", "password": STRONG}, format="json")
        responses = [
            created,
            self.client.get(USERS_URL),
            self.client.get(user_url(self.staff.id)),
            self.client.patch(user_url(self.staff.id), {"first_name": "Sam"}, format="json"),
        ]
        for response in responses:
            body = json.dumps(response.data, default=str)
            self.assertNotIn("password", body)
            self.assertNotIn("pbkdf2", body)
            self.assertNotIn(STRONG, body)

    def test_password_cannot_be_changed_through_patch(self):
        self.as_admin()
        response = self.client.patch(user_url(self.staff.id), {"password": STRONG + "x"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["errors"])

    def test_reset_password(self):
        self.as_admin()
        url = reverse("user-set-password", args=[self.staff.id])

        self.assertEqual(self.client.post(url, {"password": "short"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"password": "Brand-New-Secret-7"}, format="json").status_code, 204)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("Brand-New-Secret-7"))


class UserRuleTests(AdminApiTestBase):
    def test_admin_cannot_deactivate_or_demote_self(self):
        other_admin = User.objects.create_user("admin2", password=STRONG, role=User.Role.ADMIN)
        self.as_admin()

        deactivate = self.client.patch(user_url(self.admin.id), {"is_active": False}, format="json")
        demote = self.client.patch(user_url(self.admin.id), {"role": "staff"}, format="json")

        self.assertEqual(deactivate.status_code, 400)
        self.assertEqual(deactivate.data["detail"], "You cannot deactivate your own account.")
        self.assertIn("is_active", deactivate.data["errors"])
        self.assertEqual(demote.status_code, 400)
        self.assertIn("role", demote.data["errors"])
        self.assertTrue(other_admin.is_active)

    def test_admin_can_demote_another_admin_while_one_active_admin_remains(self):
        other = User.objects.create_user("admin2", password=STRONG, role=User.Role.ADMIN)
        self.as_admin()

        response = self.client.patch(user_url(other.id), {"role": "staff"}, format="json")

        self.assertEqual(response.status_code, 200)
        # Through the API the last-admin rule can never fire on its own: acting on another admin
        # means two active admins exist, and acting on yourself hits the self rule first.
        # LastAdminServiceTests covers the rule directly.

    def test_reviewer_without_department_is_rejected(self):
        self.as_admin()
        create = self.client.post(USERS_URL, {"username": "rev2", "password": STRONG, "role": "reviewer"}, format="json")
        remove_dept = self.client.patch(user_url(self.reviewer.id), {"department": None}, format="json")
        promote = self.client.patch(user_url(User.objects.create_user("nodept", password=STRONG).id), {"role": "reviewer"}, format="json")

        for response in (create, remove_dept, promote):
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["detail"], "A reviewer must belong to a department.")
            self.assertIn("department", response.data["errors"])


class LastAdminServiceTests(AdminApiTestBase):
    """The last-admin rule, tested directly: the API alone can never reach it (self rule fires first)."""

    def test_last_active_admin_cannot_be_deactivated_or_demoted(self):
        from rest_framework.exceptions import ValidationError

        from apps.accounts import services

        someone = User.objects.create_user("someone", password=STRONG)  # actor other than the target
        for change in ({"is_active": False}, {"role": User.Role.STAFF}):
            with self.assertRaises(ValidationError) as ctx:
                services.update_user(someone, self.admin, **change)
            self.assertEqual(str(ctx.exception.detail["detail"]), "The last active admin cannot be deactivated or demoted.")

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, User.Role.ADMIN)


class DepartmentTests(AdminApiTestBase):
    def test_crud_and_user_count(self):
        self.as_admin()
        created = self.client.post(DEPARTMENTS_URL, {"name": "Finance"}, format="json")
        self.assertEqual(created.status_code, 201)

        listing = {d["name"]: d["user_count"] for d in self.client.get(DEPARTMENTS_URL).data}
        self.assertEqual(listing, {"Empty": 0, "Finance": 0, "IT": 2})

        renamed = self.client.patch(reverse("department-detail", args=[created.data["id"]]), {"name": "Fin"}, format="json")
        self.assertEqual(renamed.data["name"], "Fin")
        self.assertEqual(self.client.delete(reverse("department-detail", args=[self.empty_dept.id])).status_code, 204)

    def test_department_with_users_cannot_be_deleted(self):
        self.as_admin()
        response = self.client.delete(reverse("department-detail", args=[self.it.id]))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "2 users are assigned to this department. Move them to another department first.")
        self.assertTrue(Department.objects.filter(pk=self.it.pk).exists())

    def test_category_used_by_requests_cannot_be_deleted(self):
        category = make_category("Equipment")
        make_request(self.staff, category, "Uses it")
        self.as_admin()

        response = self.client.delete(reverse("category-detail", args=[category.id]))

        self.assertEqual(response.status_code, 400)
        self.assertIn("Deactivate it instead", response.data["detail"])
