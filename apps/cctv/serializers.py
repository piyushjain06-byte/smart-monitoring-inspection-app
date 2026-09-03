from rest_framework import serializers

from .models import Camera


class CameraSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source="institute.name", read_only=True)
    status = serializers.CharField(read_only=True)
    offline_hours = serializers.SerializerMethodField()
    last_ping = serializers.DateTimeField(source="last_online", read_only=True)
    stream_path = serializers.SerializerMethodField()

    class Meta:
        model = Camera
        fields = [
            "id", "institute", "institute_name", "name",
            "camera_index", "stream_url", "is_active", "is_maintenance",
            "status", "last_online", "last_ping", "offline_hours", "stream_path",
        ]
        read_only_fields = ["last_online"]

    def get_stream_path(self, obj):
        """
        Relative API path (no host, no token) — the frontend appends its own
        base URL + JWT query param, same pattern as Evidence file URLs.
        """
        return f"/cctv/cameras/{obj.id}/stream/"

    def get_offline_hours(self, obj):
        return round(obj.offline_hours(), 1)
