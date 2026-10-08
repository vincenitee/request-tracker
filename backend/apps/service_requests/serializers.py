from rest_framework import serializers

from apps.accounts.models import User

from . import services
from .models import Attachment, Category, Comment, Request, StatusHistory


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
    comments_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()

    class Meta:
        model = Request
        fields = (
            "id", "title", "category", "requester", "status", "priority", "created_at",
            "comments_count", "attachments_count",
        )

    # Annotated by services.scoped_requests (no N+1). Instances that did not come from that
    # queryset (just created, or returned by a workflow action) fall back to one COUNT each.
    def get_comments_count(self, obj) -> int:
        count = getattr(obj, "comments_count", None)
        return obj.comments.count() if count is None else count

    def get_attachments_count(self, obj) -> int:
        count = getattr(obj, "attachments_count", None)
        return obj.attachments.count() if count is None else count


class RequestDetailSerializer(RequestListSerializer):
    available_actions = serializers.SerializerMethodField()

    class Meta(RequestListSerializer.Meta):
        fields = RequestListSerializer.Meta.fields + ("description", "updated_at", "available_actions")

    def get_available_actions(self, obj) -> list[str]:
        return services.get_available_actions(obj, self.context["request"].user)


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by = RequesterSerializer(read_only=True)

    class Meta:
        model = StatusHistory
        fields = ("id", "from_status", "to_status", "changed_by", "remarks", "changed_at")


class CommentSerializer(serializers.ModelSerializer):
    author = RequesterSerializer(read_only=True)
    body = serializers.CharField(max_length=2000, trim_whitespace=True, allow_blank=False)
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("id", "author", "body", "created_at", "can_delete")
        read_only_fields = ("id", "author", "created_at")

    def get_can_delete(self, obj) -> bool:
        return services.can_delete_comment(self.context["request"].user, obj)


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = RequesterSerializer(read_only=True)
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ("id", "original_name", "content_type", "size", "uploaded_by", "uploaded_at", "can_delete")
        read_only_fields = fields

    def get_can_delete(self, obj) -> bool:
        # The parent request comes from the view's context, so listing N files costs no extra queries.
        parent = self.context.get("parent_request") or obj.request
        return services.can_manage_attachments(self.context["request"].user, parent)


class AttachmentUploadSerializer(serializers.Serializer):
    # Empty files pass here so validators.validate_attachment can return one consistent message.
    file = serializers.FileField(allow_empty_file=True, use_url=False)


class TransitionSerializer(serializers.Serializer):
    """Body for the workflow actions. Whether remarks are required is decided by the service."""

    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


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


class DashboardSummarySerializer(serializers.Serializer):
    """Shape of GET /dashboard/summary/ (built by services.dashboard_summary)."""

    total = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())
    by_priority = serializers.DictField(child=serializers.IntegerField())
    needs_my_action = serializers.IntegerField()
    recent = RequestListSerializer(many=True)
