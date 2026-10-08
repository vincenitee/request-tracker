from rest_framework import serializers

from . import services
from .models import Department, User


class DepartmentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name")


class MeSerializer(serializers.ModelSerializer):
    department = DepartmentSummarySerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "department")
        read_only_fields = fields


class DepartmentSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)  # annotated in the viewset

    class Meta:
        model = Department
        fields = ("id", "name", "user_count")


class UserSerializer(serializers.ModelSerializer):
    """Read shape for the admin pages. There is deliberately no password field here."""

    department = DepartmentSummarySerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name", "full_name",
            "role", "department", "is_active", "last_login", "date_joined",
        )
        read_only_fields = fields

    def get_full_name(self, user) -> str:
        return user.get_full_name()


class UserWriteSerializer(serializers.ModelSerializer):
    """Create/PATCH input. password is write-only and accepted on create only."""

    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), allow_null=True, required=False)
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"}, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "role", "department", "is_active", "password")

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": ["A password is required."]})
        if self.instance is not None and "password" in attrs:
            raise serializers.ValidationError({"password": ["Use the reset-password action to change a password."]})
        return attrs

    def create(self, validated_data):
        return services.create_user(self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        return services.update_user(self.context["request"].user, instance, **validated_data)

    def to_representation(self, instance):
        return UserSerializer(instance, context=self.context).data


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"}, trim_whitespace=False)
