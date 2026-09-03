from rest_framework import serializers

from .models import Beneficiary, Institute, NGO, Project, Scheme, Staff


class SchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheme
        fields = ["id", "name", "description", "created_at"]


class NGOSerializer(serializers.ModelSerializer):
    # admin_user is now writable (was previously omitted from this
    # serializer entirely) — the NGO management page needs this to link an
    # NGO to the User account that should see it in the NGO portal, without
    # requiring a trip to /admin/.
    class Meta:
        model = NGO
        fields = [
            "id", "name", "registration_number",
            "contact_person", "contact_phone", "contact_email", "admin_user",
        ]


class InstituteSerializer(serializers.ModelSerializer):
    """
    Plain lat/lng fields for now. Once we're on PostGIS, this can switch to
    GeoFeatureModelSerializer for ready-made GeoJSON — the frontend map code
    will barely need to change since it'll just read different field names.
    """
    ngo_name = serializers.CharField(source="ngo.name", read_only=True)
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)
    latest_inspection_status = serializers.SerializerMethodField()
    latest_risk_severity = serializers.SerializerMethodField()
    latest_risk_score = serializers.SerializerMethodField()

    class Meta:
        model = Institute
        fields = [
            "id", "name", "ngo", "ngo_name", "scheme", "scheme_name",
            "address", "state", "district", "latitude", "longitude",
            "incharge", "is_active", "latest_inspection_status",
            "latest_risk_severity", "latest_risk_score",
        ]

    def get_latest_inspection_status(self, obj):
        """
        Fallback map-marker colouring for institutes with no AI risk score
        yet (i.e. the Phase 9 engine hasn't run for them) — "does this
        institute have a pending/overdue/submitted inspection", not a risk
        assessment.
        """
        latest = obj.inspection_assignments.order_by("-assigned_at").first()
        return latest.status if latest else "NO_INSPECTION"

    def _latest_snapshot(self, obj):
        # Cached per-instance so the two SerializerMethodFields below don't
        # each hit the DB separately for the same institute.
        if not hasattr(obj, "_latest_risk_snapshot_cache"):
            obj._latest_risk_snapshot_cache = obj.risk_snapshots.order_by("-computed_at").first()
        return obj._latest_risk_snapshot_cache

    def get_latest_risk_severity(self, obj):
        """Phase 9 — LOW/MEDIUM/HIGH from the most recent risk-engine run, or None if it hasn't run yet."""
        snapshot = self._latest_snapshot(obj)
        return snapshot.severity if snapshot else None

    def get_latest_risk_score(self, obj):
        snapshot = self._latest_snapshot(obj)
        return snapshot.score if snapshot else None


class ProjectSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source="institute.name", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "institute", "institute_name", "name",
            "start_date", "end_date", "sanctioned_budget", "is_active",
        ]


class StaffSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source="institute.name", read_only=True)

    class Meta:
        model = Staff
        fields = ["id", "institute", "institute_name", "full_name", "designation", "phone_number", "linked_user"]


class BeneficiarySerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = Beneficiary
        fields = ["id", "project", "project_name", "full_name", "phone_number", "linked_user", "enrolled_on"]
