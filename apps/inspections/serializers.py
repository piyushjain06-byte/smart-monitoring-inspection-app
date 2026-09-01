from rest_framework import serializers

from apps.registry.models import Institute

from .models import (
    Evidence,
    InspectionAssignment,
    InspectionField,
    InspectionReport,
    InspectionTemplate,
)


class InspectionFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionField
        fields = ["id", "label", "field_type", "is_required", "order"]


class InspectionTemplateSerializer(serializers.ModelSerializer):
    fields = InspectionFieldSerializer(many=True, read_only=True)

    class Meta:
        model = InspectionTemplate
        fields = ["id", "name", "description", "is_active", "fields"]


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ["id", "media_type", "file", "captured_at", "latitude", "longitude"]


class InspectionReportSerializer(serializers.ModelSerializer):
    evidence_items = EvidenceSerializer(many=True, read_only=True)
    assignment = serializers.PrimaryKeyRelatedField(queryset=InspectionAssignment.objects.all())

    class Meta:
        model = InspectionReport
        fields = [
            "id", "assignment", "submitted_at", "submitted_latitude", "submitted_longitude",
            "location_verified", "answers", "overall_score", "notes", "evidence_items",
        ]


class InspectionAssignmentSerializer(serializers.ModelSerializer):
    """Read-only summary used on the government dashboard's institute detail
    view, and on the inspector's "My Assignments" list."""
    officer_name = serializers.SerializerMethodField()
    template_name = serializers.CharField(source="template.name", read_only=True)
    institute_name = serializers.CharField(source="institute.name", read_only=True)
    institute_district = serializers.CharField(source="institute.district", read_only=True)
    institute_state = serializers.CharField(source="institute.state", read_only=True)
    institute_latitude = serializers.FloatField(source="institute.latitude", read_only=True)
    institute_longitude = serializers.FloatField(source="institute.longitude", read_only=True)

    class Meta:
        model = InspectionAssignment
        fields = [
            "id", "institute", "institute_name", "institute_district", "institute_state",
            "institute_latitude", "institute_longitude",
            "officer", "officer_name", "template", "template_name",
            "assigned_at", "due_date", "status",
        ]

    def get_officer_name(self, obj):
        return obj.officer.get_full_name() or obj.officer.username


class AutoAssignRequestSerializer(serializers.Serializer):
    institute = serializers.PrimaryKeyRelatedField(queryset=Institute.objects.all())
    template = serializers.PrimaryKeyRelatedField(
        queryset=InspectionTemplate.objects.filter(is_active=True), required=False
    )
    due_in_days = serializers.IntegerField(required=False, min_value=1, default=7)


class InspectionReportCreateSerializer(serializers.Serializer):
    assignment = serializers.PrimaryKeyRelatedField(queryset=InspectionAssignment.objects.all())
    answers = serializers.JSONField()
    submitted_latitude = serializers.FloatField(required=False, allow_null=True)
    submitted_longitude = serializers.FloatField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    evidence = serializers.ListField(child=serializers.FileField(), required=False)

    def validate(self, data):
        assignment = data["assignment"]
        if getattr(assignment, "status", None) == "SUBMITTED":
            raise serializers.ValidationError("Assignment already submitted")
        return data
