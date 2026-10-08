"""Dev-only demo data. Safe to run repeatedly: existing rows are reused, never duplicated."""

import os
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Department, User
from apps.service_requests.models import Category, Request

DEPARTMENTS = ("IT", "HR")
CATEGORIES = ("Equipment", "Leave", "Document", "Repair")

# username: (first, last, role, department)
USERS = {
    "demo_staff": ("Sam", "Staff", User.Role.STAFF, "IT"),
    "demo_staff_hr": ("Hana", "Reyes", User.Role.STAFF, "HR"),
    "demo_reviewer": ("Rex", "Reviewer", User.Role.REVIEWER, "IT"),
    "demo_admin": ("Ada", "Admin", User.Role.ADMIN, None),
}

S, P = Request.Status, Request.Priority
# (title, requester, category, status, priority, days ago)
REQUESTS = [
    ("New laptop for onboarding", "demo_staff", "Equipment", S.DRAFT, P.HIGH, 1),
    ("Second monitor", "demo_staff", "Equipment", S.SUBMITTED, P.MEDIUM, 3),
    ("Vacation leave in December", "demo_staff", "Leave", S.IN_REVIEW, P.MEDIUM, 5),
    ("Certificate of employment", "demo_staff", "Document", S.APPROVED, P.LOW, 8),
    ("Fix flickering office light", "demo_staff", "Repair", S.REJECTED, P.LOW, 12),
    ("Replacement keyboard", "demo_staff", "Equipment", S.COMPLETED, P.LOW, 20),
    ("Sick leave follow-up", "demo_staff", "Leave", S.DRAFT, P.MEDIUM, 0),
    ("Docking station", "demo_reviewer", "Equipment", S.SUBMITTED, P.MEDIUM, 2),
    ("Training leave", "demo_reviewer", "Leave", S.APPROVED, P.HIGH, 15),
    ("Payslip copy for March", "demo_staff_hr", "Document", S.SUBMITTED, P.LOW, 4),
    ("Ergonomic chair", "demo_staff_hr", "Equipment", S.IN_REVIEW, P.HIGH, 6),
    ("Aircon repair in HR room", "demo_staff_hr", "Repair", S.DRAFT, P.HIGH, 1),
    ("Maternity leave paperwork", "demo_staff_hr", "Leave", S.APPROVED, P.MEDIUM, 25),
    ("Projector for town hall", "demo_admin", "Equipment", S.COMPLETED, P.MEDIUM, 30),
    ("Update records template", "demo_admin", "Document", S.SUBMITTED, P.LOW, 7),
]


class Command(BaseCommand):
    help = "Create demo departments, categories, users and requests (development only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo_data is for development only and refuses to run when DEBUG is False.")

        env_password = os.environ.get("DEMO_PASSWORD")
        new_password = env_password or secrets.token_urlsafe(9)

        with transaction.atomic():
            departments = {name: Department.objects.get_or_create(name=name)[0] for name in DEPARTMENTS}
            categories = {name: Category.objects.get_or_create(name=name)[0] for name in CATEGORIES}
            users, created_users = self._seed_users(departments, new_password, env_password is not None)
            created_requests = self._seed_requests(users, categories)

        self.stdout.write(self.style.SUCCESS(
            f"Departments: {len(departments)}, categories: {len(categories)}, "
            f"users created: {created_users}, requests created: {created_requests}"
        ))
        self.stdout.write("Demo users: " + ", ".join(f"{u} ({USERS[u][2]})" for u in USERS))
        if env_password:
            self.stdout.write("Password: the value of DEMO_PASSWORD (applied to all demo users).")
        elif created_users:
            self.stdout.write(self.style.WARNING(f"Generated password for new demo users: {new_password}"))
        else:
            self.stdout.write("Existing demo users kept their passwords. Set DEMO_PASSWORD to reset them.")

    def _seed_users(self, departments, password, force_password):
        users, created_count = {}, 0
        for username, (first, last, role, dept) in USERS.items():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "department": departments.get(dept),
                    "email": f"{username}@example.com",
                },
            )
            if created or force_password:
                user.set_password(password)
                user.save()
            created_count += created
            users[username] = user
        return users, created_count

    def _seed_requests(self, users, categories):
        now, created_count = timezone.now(), 0
        for title, requester, category, status, priority, days_ago in REQUESTS:
            obj, created = Request.objects.get_or_create(
                title=title,
                requester=users[requester],
                defaults={
                    "description": f"Demo request: {title.lower()}.",
                    "category": categories[category],
                    "status": status,
                    "priority": priority,
                },
            )
            if created:
                # auto_now_add ignores passed values, so backdate with update() for realistic sorting.
                Request.objects.filter(pk=obj.pk).update(created_at=now - timedelta(days=days_ago, hours=len(title)))
                created_count += 1
        return created_count
