from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

from . import services
from .filters import RequestFilter, RequestOrderingFilter
from .permissions import CanModifyRequest, IsAdminRoleOrReadOnly
from .serializers import (
    CategorySerializer,
    RequestDetailSerializer,
    RequestListSerializer,
    RequestWriteSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]
    pagination_class = None  # small lookup list, used for dropdowns
    filterset_fields = ("is_active",)
    search_fields = ("name",)
    ordering_fields = ("name",)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return services.visible_categories(self.request.user)

    def perform_destroy(self, instance):
        services.delete_category(instance)


class RequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanModifyRequest]
    filter_backends = [DjangoFilterBackend, SearchFilter, RequestOrderingFilter]
    filterset_class = RequestFilter
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "title", "priority")
    ordering = ("-created_at",)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return services.scoped_requests(self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return RequestListSerializer
        if self.action == "retrieve":
            return RequestDetailSerializer
        return RequestWriteSerializer

    def perform_destroy(self, instance):
        services.delete_request(instance)
