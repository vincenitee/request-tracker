from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User

TOKEN_URL = reverse("token_obtain_pair")


class HealthEndpointTests(TestCase):
    def test_health_returns_ok_without_auth(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class ThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.addCleanup(cache.clear)

    @override_settings(LOGIN_THROTTLE_RATE="3/min")
    def test_token_endpoint_is_throttled_per_ip(self):
        User.objects.create_user("someone", password="Correct-Horse-42")
        statuses = [
            self.client.post(TOKEN_URL, {"username": "someone", "password": "wrong"}, format="json").status_code
            for _ in range(4)
        ]
        self.assertEqual(statuses, [401, 401, 401, 429])

        # Even the right password is refused while throttled, and the body has the usual shape.
        response = self.client.post(TOKEN_URL, {"username": "someone", "password": "Correct-Horse-42"}, format="json")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(set(response.data), {"detail", "errors"})
        self.assertIn("Too many attempts", response.data["detail"])
        self.assertIn("Retry-After", response)

    @override_settings(API_USER_THROTTLE_RATE="2/min")
    def test_general_authenticated_rate(self):
        user = User.objects.create_user("busy", password="Correct-Horse-42")
        self.client.force_authenticate(user)
        statuses = [self.client.get(reverse("me")).status_code for _ in range(3)]

        self.assertEqual(statuses, [200, 200, 429])


class ErrorShapeTests(APITestCase):
    def test_unknown_api_url_returns_json_404_even_with_debug(self):
        for debug in (True, False):
            with self.settings(DEBUG=debug):
                response = self.client.get("/api/v1/does-not-exist/")
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response["Content-Type"], "application/json")
                self.assertEqual(response.json(), {"detail": "Not found.", "errors": {}})

    def test_401_403_404_405_use_the_shape(self):
        user = User.objects.create_user("staff", password="Correct-Horse-42")
        unauthenticated = self.client.get(reverse("me"))
        self.client.force_authenticate(user)
        forbidden = self.client.get(reverse("user-list"))
        missing = self.client.get(reverse("request-detail", args=[999999]))
        not_allowed = self.client.put(reverse("me"), {}, format="json")

        for response, code in ((unauthenticated, 401), (forbidden, 403), (missing, 404), (not_allowed, 405)):
            self.assertEqual(response.status_code, code)
            self.assertEqual(set(response.data), {"detail", "errors"}, code)


class ApiDocsTests(TestCase):
    def test_docs_and_schema_are_served_only_with_debug(self):
        with self.settings(DEBUG=True):
            self.assertEqual(self.client.get(reverse("swagger-ui")).status_code, 200)
            self.assertEqual(self.client.get(reverse("schema")).status_code, 200)
        with self.settings(DEBUG=False):
            for name in ("swagger-ui", "schema"):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 404, name)
                self.assertEqual(response.json()["detail"], "Not found.")
