from django.contrib import admin

from .models import Category, Request, StatusHistory


class ReadOnlyAdminMixin:
    """History is written by the workflow service only, never by hand."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


class StatusHistoryInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = StatusHistory
    fields = ("changed_at", "from_status", "to_status", "changed_by", "remarks")
    readonly_fields = fields
    extra = 0


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("title", "requester", "category", "status", "priority", "created_at")
    list_filter = ("status", "priority", "category", "requester__department")
    search_fields = ("title", "description", "requester__username")
    list_select_related = ("requester", "category")
    autocomplete_fields = ("requester",)
    # status changes must go through the workflow (services.perform_transition) so history is written
    readonly_fields = ("status", "created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines = [StatusHistoryInline]


@admin.register(StatusHistory)
class StatusHistoryAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("request", "from_status", "to_status", "changed_by", "changed_at")
    list_filter = ("to_status",)
    search_fields = ("request__title", "changed_by__username", "remarks")
    list_select_related = ("request", "changed_by")
