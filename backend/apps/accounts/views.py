from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.throttling import LoginRateThrottle

from . import services
from .models import Department, User
from .permissions import IsAdminRole
from .serializers import (
    DepartmentSerializer,
    MeSerializer,
    SetPasswordSerializer,
    UserSerializer,
    UserWriteSerializer,
)


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login, limited per client IP (settings.LOGIN_THROTTLE_RATE) against password guessing."""

    throttle_classes = [LoginRateThrottle]


class MeView(RetrieveAPIView):
    """The logged-in user. Uses the default IsAuthenticated permission."""

    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None  # short list, used for dropdowns and the admin page
    search_fields = ("name",)
    ordering_fields = ("name",)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Department.objects.annotate(user_count=Count("users")).order_by("name")

    def perform_destroy(self, instance):
        services.delete_department(instance)


class UserViewSet(viewsets.ModelViewSet):
    """Admin user management. No DELETE: deactivate with is_active=false instead."""

    permission_classes = [IsAdminRole]
    filterset_fields = ("role", "department", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering_fields = ("username", "date_joined", "last_login")
    ordering = ("username",)
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return User.objects.select_related("department")

    def get_serializer_class(self):
        if self.action in ("create", "partial_update", "update"):
            return UserWriteSerializer
        if self.action == "set_password":
            return SetPasswordSerializer
        return UserSerializer

    @extend_schema(request=SetPasswordSerializer, responses={204: None})
    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        body = SetPasswordSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        services.set_password(self.get_object(), body.validated_data["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
