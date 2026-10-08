"""Dev-only demo data. Safe to run repeatedly: existing rows are reused, never duplicated.

Sample requests move through the real workflow (services.perform_transition), so every
non-draft request has matching StatusHistory rows.
"""

import os
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Department, User
from apps.service_requests import services
from apps.service_requests.models import Category, Request, StatusHistory

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

# Actions needed to bring a new draft to each status.
PATH_TO = {
    S.DRAFT: [],
    S.SUBMITTED: ["submit"],
    S.IN_REVIEW: ["submit", "start_review"],
    S.APPROVED: ["submit", "start_review", "approve"],
    S.REJECTED: ["submit", "start_review", "reject"],
    S.COMPLETED: ["submit", "start_review", "approve", "complete"],
}
REJECT_REMARKS = "Facilities will handle this in the next scheduled maintenance."

# (title, requester, category, target status, priority, days ago)
# Admin-owned requests stop at submitted: nobody else may review them (admins cannot review their own).
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
    ("Projector for town hall", "demo_admin", "Equipment", S.SUBMITTED, P.MEDIUM, 9),
    ("Update records template", "demo_admin", "Document", S.DRAFT, P.LOW, 7),
]


class Command(BaseCommand):
    help = "Create demo departments, categories, users and requests (development only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete requests owned by the demo users (and their history) before seeding. "
            "Other users' data is never touched.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo_data is for development only and refuses to run when DEBUG is False.")

        env_password = os.environ.get("DEMO_PASSWORD")
        new_password = env_password or secrets.token_urlsafe(9)

        with transaction.atomic():
            if options["reset"]:
                deleted, _ = Request.objects.filter(requester__username__in=USERS).delete()
                self.stdout.write(f"Reset: deleted {deleted} demo rows (requests and their history).")
            departments = {name: Department.objects.get_or_create(name=name)[0] for name in DEPARTMENTS}
            categories = {name: Category.objects.get_or_create(name=name)[0] for name in CATEGORIES}
            users, created_users = self._seed_users(departments, new_password, env_password is not None)
            created_requests, transitions = self._seed_requests(users, categories)

        self.stdout.write(self.style.SUCCESS(
            f"Departments: {len(departments)}, categories: {len(categories)}, users created: {created_users}, "
            f"requests created: {created_requests}, workflow transitions: {transitions}"
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
        now, created_count, transitions = timezone.now(), 0, 0
        for title, requester, category, target, priority, days_ago in REQUESTS:
            obj, created = Request.objects.get_or_create(
                title=title,
                requester=users[requester],
                defaults={
                    "description": f"Demo request: {title.lower()}.",
                    "category": categories[category],
                    "priority": priority,
                },  # status defaults to draft; the workflow moves it forward below
            )
            if not created:
                continue
            created_count += 1
            created_at = now - timedelta(days=days_ago, hours=len(title))

            for step, action in enumerate(PATH_TO[target], start=1):
                actor = self._actor_for(action, obj, users)
                remarks = REJECT_REMARKS if action == "reject" else ""
                obj = services.perform_transition(obj, actor, action, remarks)
                transitions += 1
                # Spread the timeline after the (backdated) creation time so it reads naturally.
                StatusHistory.objects.filter(request=obj, to_status=obj.status).update(
                    changed_at=min(created_at + timedelta(hours=6 * step), now)
                )

            # auto_now_add ignores passed values, so backdate with update() for realistic sorting.
            Request.objects.filter(pk=obj.pk).update(created_at=created_at)
        return created_count, transitions

    @staticmethod
    def _actor_for(action, request, users):
        """Pick a user the workflow rules allow: the requester submits, the department reviewer
        reviews (unless it is their own request), otherwise the admin."""
        if action == "submit":
            return request.requester
        reviewer = users["demo_reviewer"]
        if (
            action != "complete"
            and request.requester_id != reviewer.id
            and request.requester.department_id == reviewer.department_id
        ):
            return reviewer
        return users["demo_admin"]
