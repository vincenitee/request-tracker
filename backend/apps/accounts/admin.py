from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Org info", {"fields": ("role", "department")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Org info", {"fields": ("role", "department")}),)
    list_display = ("username", "email", "role", "department", "is_active")
    list_filter = ("role", "department", "is_active")


admin.site.register(Department)
