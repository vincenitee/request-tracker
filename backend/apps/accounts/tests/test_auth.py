from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Department, User


class AuthTests(APITestCase):
    password = "pass12345"

    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="IT")
        cls.user = User.objects.create_user(
            username="rita",
            password=cls.password,
            first_name="Rita",
            role=User.Role.REVIEWER,
            department=cls.department,
        )

    def login(self, password=None):
        return self.client.post(
            reverse("token_obtain_pair"),
            {"username": "rita", "password": password or self.password},
            format="json",
        )

    def test_login_with_valid_credentials_returns_tokens(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_wrong_password_fails(self):
        response = self.login(password="wrong-password")

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access", response.data)

    def test_me_without_token_returns_401(self):
        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, 401)

    def test_me_with_token_returns_user_and_role(self):
        access = self.login().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "rita")
        self.assertEqual(response.data["role"], "reviewer")
        self.assertEqual(response.data["department"], {"id": self.department.id, "name": "IT"})

    def test_refresh_returns_new_access_token(self):
        refresh = self.login().data["refresh"]

        response = self.client.post(reverse("token_refresh"), {"refresh": refresh}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
