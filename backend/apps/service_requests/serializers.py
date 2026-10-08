from rest_framework import serializers

from apps.accounts.models import User

from . import services
from .models import Category, Request


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "is_active")


class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class RequesterSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "name")

    def get_name(self, user) -> str:
        return user.get_full_name() or user.username


class RequestListSerializer(serializers.ModelSerializer):
    category = CategorySummarySerializer(read_only=True)
    requester = RequesterSerializer(read_only=True)

    class Meta:
        model = Request
        fields = ("id", "title", "category", "requester", "status", "priority", "created_at")


class RequestDetailSerializer(RequestListSerializer):
    class Meta(RequestListSerializer.Meta):
        fields = RequestListSerializer.Meta.fields + ("description", "updated_at")


class RequestWriteSerializer(serializers.ModelSerializer):
    """Input for create/PATCH. status and requester are set by the server, never by the client."""

    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = Request
        fields = ("title", "description", "category", "priority")

    def validate_title(self, value: str) -> str:
        # DRF already trims whitespace and rejects "", this keeps the rule explicit.
        if not value.strip():
            raise serializers.ValidationError("Title cannot be blank.")
        return value

    def validate_category(self, category: Category) -> Category:
        if not category.is_active:
            raise serializers.ValidationError("This category is no longer active.")
        return category

    def create(self, validated_data):
        return services.create_request(requester=self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        return services.update_request(instance, **validated_data)

    def to_representation(self, instance):
        # Respond with the full detail shape so the client never needs a second GET.
        return RequestDetailSerializer(instance, context=self.context).data
