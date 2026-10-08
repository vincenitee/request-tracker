from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import services
from .filters import RequestFilter, RequestOrderingFilter
from .permissions import CanModifyRequest, IsAdminRoleOrReadOnly
from .serializers import (
    CategorySerializer,
    RequestDetailSerializer,
    RequestListSerializer,
    RequestWriteSerializer,
    StatusHistorySerializer,
    TransitionSerializer,
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

    # Workflow actions are POSTs but are authorised by services.perform_transition, not CanModifyRequest.
    WORKFLOW_ACTIONS = tuple(services.TRANSITIONS)

    def get_queryset(self):
        return services.scoped_requests(self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return RequestListSerializer
        if self.action == "retrieve":
            return RequestDetailSerializer
        if self.action == "history":
            return StatusHistorySerializer
        if self.action in self.WORKFLOW_ACTIONS:
            return TransitionSerializer
        return RequestWriteSerializer

    def get_permissions(self):
        if self.action in self.WORKFLOW_ACTIONS:
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        services.delete_request(instance)

    def _transition(self, action_name):
        obj = self.get_object()  # scoped: requests the user cannot see are 404
        body = TransitionSerializer(data=self.request.data)
        body.is_valid(raise_exception=True)
        updated = services.perform_transition(obj, self.request.user, action_name, body.validated_data["remarks"])
        return Response(RequestDetailSerializer(updated, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return self._transition("submit")

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        return self._transition("start_review")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._transition("approve")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition("reject")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._transition("complete")

    @action(detail=True, methods=["get"], pagination_class=None)
    def history(self, request, pk=None):
        rows = services.history_for(self.get_object())
        return Response(StatusHistorySerializer(rows, many=True).data)
