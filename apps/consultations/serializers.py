from rest_framework import serializers

from apps.core.permissions import is_official

from .models import VCParticipant, VCSession


class VCParticipantSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = VCParticipant
        fields = ["id", "user", "user_name", "user_role", "role", "joined_at", "left_at"]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class VCSessionSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source="institute.name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    inspection_status = serializers.CharField(source="inspection.status", read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()
    participants = VCParticipantSerializer(many=True, read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    room_name = serializers.SerializerMethodField()

    class Meta:
        model = VCSession
        fields = [
            "id", "institute", "institute_name", "project", "project_name", "inspection",
            "inspection_status", "room_name", "created_by", "created_by_name", "purpose",
            "scheduled_at", "started_at", "ended_at", "status", "created_at", "participants",
            "duration_seconds",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_room_name(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and (is_official(user) or obj.created_by_id == user.id or obj.participants.filter(user=user).exists()):
            return obj.room_name
        return None

    def get_duration_seconds(self, obj):
        if not obj.started_at:
            return None
        end = obj.ended_at or obj.started_at
        return max(0, int((end - obj.started_at).total_seconds()))


class VCSessionCreateSerializer(serializers.Serializer):
    institute = serializers.IntegerField()
    project = serializers.IntegerField(required=False, allow_null=True)
    inspection = serializers.IntegerField(required=False, allow_null=True)
    purpose = serializers.CharField(required=False, allow_blank=True, max_length=255)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    participant_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
