from rest_framework import serializers

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
