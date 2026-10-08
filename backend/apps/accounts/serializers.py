from rest_framework import serializers

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
