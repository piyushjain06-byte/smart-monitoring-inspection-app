from rest_framework import serializers

from .models import Beneficiary, Institute, NGO, Project, Scheme, Staff


class SchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheme
        fields = ["id", "name", "description", "created_at"]


class NGOSerializer(serializers.ModelSerializer):
    """FLATTENED ARCHITECTURE: NGO -> Scheme only. `admin_user` stays
    writable so the NGO portal login can be wired up from the Manage UI."""
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)

    class Meta:
        model = NGO
        fields = [
            "id", "scheme", "scheme_name", "name", "registration_number",
            "contact_person", "contact_phone", "contact_email", "admin_user",
        ]


class InstituteSerializer(serializers.ModelSerializer):
    """
    Plain lat/lng fields for now. Once we're on PostGIS, this can switch to
    GeoFeatureModelSerializer for ready-made GeoJSON.

    FLATTENED ARCHITECTURE: Institute -> Scheme only. The old `ngo`/
    `ngo_name` fields are gone — Institute no longer belongs to an NGO.
    """
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)
    latest_inspection_status = serializers.SerializerMethodField()
    latest_risk_severity = serializers.SerializerMethodField()
    latest_risk_score = serializers.SerializerMethodField()

    class Meta:
        model = Institute
        fields = [
            "id", "name", "scheme", "scheme_name",
            "address", "state", "district", "latitude", "longitude",
            "incharge", "is_active", "latest_inspection_status",
            "latest_risk_severity", "latest_risk_score",
        ]

    def get_latest_inspection_status(self, obj):
        """
        Fallback map-marker colouring for institutes with no AI risk score
        yet — "does this institute have a pending/overdue/submitted
        inspection", not a risk assessment.
        """
        latest = obj.inspection_assignments.order_by("-assigned_at").first()
        return latest.status if latest else "NO_INSPECTION"

    def _latest_snapshot(self, obj):
        if not hasattr(obj, "_latest_risk_snapshot_cache"):
            obj._latest_risk_snapshot_cache = obj.risk_snapshots.order_by("-computed_at").first()
        return obj._latest_risk_snapshot_cache

    def get_latest_risk_severity(self, obj):
        snapshot = self._latest_snapshot(obj)
        return snapshot.severity if snapshot else None

    def get_latest_risk_score(self, obj):
        snapshot = self._latest_snapshot(obj)
        return snapshot.score if snapshot else None


class ProjectSerializer(serializers.ModelSerializer):
    """FLATTENED ARCHITECTURE: Project -> Scheme only. The old `institute`/
    `institute_name` fields are gone — a Project is a Scheme-level activity,
    not tied to one physical Institute anymore."""
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "scheme", "scheme_name", "name",
            "start_date", "end_date", "sanctioned_budget", "is_active",
        ]


class StaffSerializer(serializers.ModelSerializer):
    """Unaffected by the flatten — Staff still belongs to an Institute."""
    institute_name = serializers.CharField(source="institute.name", read_only=True)

    class Meta:
        model = Staff
        fields = ["id", "institute", "institute_name", "full_name", "designation", "phone_number", "linked_user"]


class BeneficiarySerializer(serializers.ModelSerializer):
    """Unaffected by the flatten — Beneficiary still belongs to a Project."""
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = Beneficiary
        fields = ["id", "project", "project_name", "full_name", "phone_number", "linked_user", "enrolled_on"]
