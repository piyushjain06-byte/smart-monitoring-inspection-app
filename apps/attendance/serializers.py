from rest_framework import serializers

from apps.registry.models import Institute, Staff
from .models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    institute_name = serializers.CharField(source="institute.name", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id", "staff", "staff_name", "institute", "institute_name",
            "date", "check_in", "check_out", "status", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AttendanceMarkSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField()
    institute_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_staff_id(self, value):
        if not Staff.objects.filter(id=value).exists():
            raise serializers.ValidationError("Staff member does not exist.")
        return value

    def validate_institute_id(self, value):
        if not Institute.objects.filter(id=value).exists():
            raise serializers.ValidationError("Institute does not exist.")
        return value