from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .factories import make_category, make_request, make_user

LIST_URL = reverse("category-list")


class CategoryApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = make_user("staff")
        cls.admin = make_user("admin", User.Role.ADMIN)
        cls.active = make_category("Equipment")
        cls.inactive = make_category("Retired", is_active=False)

    def test_non_admin_sees_only_active_categories_unpaginated(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["name"] for c in response.data], ["Equipment"])

    def test_admin_sees_inactive_categories_only_on_request(self):
        self.client.force_authenticate(self.admin)

        default = self.client.get(LIST_URL)
        everything = self.client.get(LIST_URL, {"include_inactive": "true"})

        self.assertEqual({c["name"] for c in default.data}, {"Equipment"})
        self.assertEqual({c["name"] for c in everything.data}, {"Equipment", "Retired"})

    def test_include_inactive_is_ignored_for_non_admins(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(LIST_URL, {"include_inactive": "true"})

        self.assertEqual({c["name"] for c in response.data}, {"Equipment"})

    def test_admin_can_reactivate_an_inactive_category(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            reverse("category-detail", args=[self.inactive.id]), {"is_active": True}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_active"])

    def test_non_admin_cannot_create_category(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(LIST_URL, {"name": "Travel"}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_category(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(LIST_URL, {"name": "Travel"}, format="json")

        self.assertEqual(response.status_code, 201)

    def test_deleting_a_used_category_returns_400_not_500(self):
        make_request(self.staff, self.active, "Uses it")
        self.client.force_authenticate(self.admin)
        response = self.client.delete(reverse("category-detail", args=[self.active.id]))

        self.assertEqual(response.status_code, 400)
        self.assertIn("Deactivate", response.data["detail"])
