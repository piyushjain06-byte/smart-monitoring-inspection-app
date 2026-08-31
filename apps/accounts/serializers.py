from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email",
            "role", "role_display", "phone_number", "preferred_language",
            "state", "district",
        ]
        read_only_fields = ["id"]


class CurrentUserSerializer(UserSerializer):
    """Slightly richer payload for the '/api/accounts/me/' endpoint."""

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["is_staff", "is_superuser"]
