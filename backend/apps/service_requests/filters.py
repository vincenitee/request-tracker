import django_filters
from django.db.models import Case, IntegerField, Value, When
from rest_framework.filters import OrderingFilter

from .models import Request

# Priority is stored as text, so "priority" would sort alphabetically (high, low, medium).
PRIORITY_RANK = Case(
    When(priority=Request.Priority.LOW, then=Value(1)),
    When(priority=Request.Priority.MEDIUM, then=Value(2)),
    When(priority=Request.Priority.HIGH, then=Value(3)),
    output_field=IntegerField(),
)


class RequestFilter(django_filters.FilterSet):
    class Meta:
        model = Request
        fields = ("status", "category", "priority")


class RequestOrderingFilter(OrderingFilter):
    """OrderingFilter that sorts priority by rank and adds -id so paging is stable on ties."""

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset

        mapped = [term.replace("priority", "priority_rank") for term in ordering]
        if any(term.lstrip("-") == "priority_rank" for term in mapped):
            queryset = queryset.annotate(priority_rank=PRIORITY_RANK)
        return queryset.order_by(*mapped, "-id")
