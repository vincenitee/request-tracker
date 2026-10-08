from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.filters import SearchFilter
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import services
from .filters import RequestFilter, RequestOrderingFilter
from .permissions import CanModifyRequest, IsAdminRoleOrReadOnly
from .serializers import (
    AttachmentSerializer,
    AttachmentUploadSerializer,
    CategorySerializer,
    CommentSerializer,
    RequestDetailSerializer,
    RequestListSerializer,
    RequestWriteSerializer,
    StatusHistorySerializer,
    TransitionSerializer,
)


class PayloadTooLarge(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = "The upload is too large."


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

    WORKFLOW_ACTIONS = tuple(services.TRANSITIONS)
    # Nested actions authorise themselves through services (CanModifyRequest is for edit/delete only).
    SELF_AUTHORISED_ACTIONS = WORKFLOW_ACTIONS + (
        "history",
        "comments",
        "delete_comment",
        "attachments",
        "delete_attachment",
        "download_attachment",
    )

    def get_queryset(self):
        return services.scoped_requests(self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return RequestListSerializer
        if self.action == "retrieve":
            return RequestDetailSerializer
        if self.action == "history":
            return StatusHistorySerializer
        if self.action == "comments":
            return CommentSerializer
        if self.action == "attachments":
            return AttachmentUploadSerializer if self.request.method == "POST" else AttachmentSerializer
        if self.action in self.WORKFLOW_ACTIONS:
            return TransitionSerializer
        return RequestWriteSerializer

    def get_permissions(self):
        if self.action in self.SELF_AUTHORISED_ACTIONS:
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        services.delete_request(instance)

    # --- workflow -----------------------------------------------------------

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

    # --- comments -----------------------------------------------------------

    @action(detail=True, methods=["get", "post"], pagination_class=None)
    def comments(self, request, pk=None):
        obj = self.get_object()
        context = self.get_serializer_context()
        if request.method == "POST":
            body = CommentSerializer(data=request.data, context=context)
            body.is_valid(raise_exception=True)
            comment = services.add_comment(obj, request.user, body.validated_data["body"])
            return Response(CommentSerializer(comment, context=context).data, status=status.HTTP_201_CREATED)
        return Response(CommentSerializer(services.comments_for(obj), many=True, context=context).data)

    @action(detail=True, methods=["delete"], url_path=r"comments/(?P<comment_id>\d+)")
    def delete_comment(self, request, pk=None, comment_id=None):
        comment = get_object_or_404(self.get_object().comments, pk=comment_id)
        services.delete_comment(request.user, comment)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- attachments --------------------------------------------------------

    @action(detail=True, methods=["get", "post"], pagination_class=None, parser_classes=[MultiPartParser])
    def attachments(self, request, pk=None):
        obj = self.get_object()
        context = {**self.get_serializer_context(), "parent_request": obj}
        if request.method == "POST":
            # Refuse clearly oversized bodies before Django reads them (64 KB allowance for multipart framing).
            if int(request.META.get("CONTENT_LENGTH") or 0) > settings.ATTACHMENT_MAX_BYTES + 64 * 1024:
                raise PayloadTooLarge(f"The file is larger than {settings.ATTACHMENT_MAX_BYTES // (1024 * 1024)} MB.")
            body = AttachmentUploadSerializer(data=request.data)
            body.is_valid(raise_exception=True)
            attachment = services.add_attachment(obj, request.user, body.validated_data["file"])
            return Response(AttachmentSerializer(attachment, context=context).data, status=status.HTTP_201_CREATED)
        return Response(AttachmentSerializer(services.attachments_for(obj), many=True, context=context).data)

    @action(detail=True, methods=["delete"], url_path=r"attachments/(?P<attachment_id>\d+)")
    def delete_attachment(self, request, pk=None, attachment_id=None):
        attachment = get_object_or_404(self.get_object().attachments, pk=attachment_id)
        services.delete_attachment(request.user, attachment)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path=r"attachments/(?P<attachment_id>\d+)/download")
    def download_attachment(self, request, pk=None, attachment_id=None):
        attachment = get_object_or_404(self.get_object().attachments, pk=attachment_id)
        try:
            handle = attachment.file.open("rb")
        except FileNotFoundError:
            raise NotFound("The file is missing from storage.")
        response = FileResponse(
            handle,
            as_attachment=True,  # Content-Disposition: attachment; filename*=UTF-8''<original name>
            filename=attachment.original_name,
            content_type=attachment.content_type,
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
