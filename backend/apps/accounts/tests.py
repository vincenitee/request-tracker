from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_new_user_defaults_to_staff_role(self):
        user = User.objects.create_user(username="alice", password="pass12345")

        self.assertEqual(user.role, User.Role.STAFF)
        self.assertIsNone(user.department)
