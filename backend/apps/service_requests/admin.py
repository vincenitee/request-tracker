from django.contrib import admin

from .models import Category, Request


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("title", "requester", "category", "status", "priority", "created_at")
    list_filter = ("status", "priority", "category", "requester__department")
    search_fields = ("title", "description", "requester__username")
    list_select_related = ("requester", "category")
    autocomplete_fields = ("requester",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
