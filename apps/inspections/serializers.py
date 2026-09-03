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
    """
    `template` is now writable (previously read-only-by-omission) so the
    frontend template builder (frontend/src/pages/admin/InspectionTemplates.jsx)
    can create/reorder checklist questions without touching /admin/.
    """
    class Meta:
        model = InspectionField
        fields = ["id", "template", "label", "field_type", "is_required", "order"]


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
    """
    Added institute_name / officer_name / template_name / answers_display so
    the new official-facing report viewer (frontend/src/pages/ReportDetail.jsx)
    can show a readable report instead of raw {field_id: answer} JSON.
    Existing `answers` field is left untouched for backward compatibility.
    """
    evidence_items = EvidenceSerializer(many=True, read_only=True)
    assignment = serializers.PrimaryKeyRelatedField(queryset=InspectionAssignment.objects.all())
    institute = serializers.IntegerField(source="assignment.institute_id", read_only=True)
    institute_name = serializers.CharField(source="assignment.institute.name", read_only=True)
    officer_name = serializers.SerializerMethodField()
    template_name = serializers.CharField(source="assignment.template.name", read_only=True)
    answers_display = serializers.SerializerMethodField()

    class Meta:
        model = InspectionReport
        fields = [
            "id", "assignment", "institute", "institute_name", "officer_name", "template_name",
            "submitted_at", "submitted_latitude", "submitted_longitude",
            "distance_from_site_meters", "is_geofence_verified", "location_verified",
            "answers", "answers_display", "overall_score",
            "notes", "evidence_items",
        ]

    def get_officer_name(self, obj):
        officer = obj.assignment.officer
        return officer.get_full_name() or officer.username

    def get_answers_display(self, obj):
        fields_by_id = {str(f.id): f for f in obj.assignment.template.fields.all()}
        display = []
        for field_id, answer in (obj.answers or {}).items():
            f = fields_by_id.get(str(field_id))
            display.append({
                "field_id": field_id,
                "label": f.label if f else f"(deleted field {field_id})",
                "field_type": f.field_type if f else None,
                "answer": answer,
            })
        return display


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
    has_report = serializers.SerializerMethodField()

    class Meta:
        model = InspectionAssignment
        fields = [
            "id", "institute", "institute_name", "institute_district", "institute_state",
            "institute_latitude", "institute_longitude",
            "officer", "officer_name", "template", "template_name",
            "assigned_at", "due_date", "status", "has_report",
            "scheduled_at",
        ]

    def get_officer_name(self, obj):
        return obj.officer.get_full_name() or obj.officer.username

    def get_has_report(self, obj):
        return hasattr(obj, "report")


class AutoAssignRequestSerializer(serializers.Serializer):
    institute = serializers.PrimaryKeyRelatedField(queryset=Institute.objects.all(), required=False)
    template = serializers.PrimaryKeyRelatedField(
        queryset=InspectionTemplate.objects.filter(is_active=True), required=False
    )
    due_in_days = serializers.IntegerField(required=False, min_value=1, default=7)
    radius_km = serializers.FloatField(required=False, min_value=1, max_value=500)
    due_in_hours = serializers.FloatField(required=False, min_value=2, max_value=24)


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
        latitude = data.get("submitted_latitude")
        longitude = data.get("submitted_longitude")
        institute = assignment.institute
        if None in (latitude, longitude, institute.latitude, institute.longitude):
            raise serializers.ValidationError("A valid GPS location is required to submit an inspection.")
        from apps.core.geo import distance_meters

        distance = distance_meters(latitude, longitude, institute.latitude, institute.longitude)
        if distance > 200:
            raise serializers.ValidationError(
                "Submission rejected: You must be physically within 200 meters of the institute facility."
            )
        for evidence_file in data.get("evidence", []):
            if not (evidence_file.content_type or "").startswith("image/"):
                raise serializers.ValidationError("Evidence files must be images captured by the device camera.")
        data["distance_from_site_meters"] = round(distance, 2)
        return data
