from rest_framework import serializers

from .models import Beneficiary, Institute, NGO, Project, Scheme, Staff


class SchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheme
        fields = ["id", "name", "description", "created_at"]


class NGOSerializer(serializers.ModelSerializer):
    class Meta:
        model = NGO
        fields = [
            "id", "name", "registration_number",
            "contact_person", "contact_phone", "contact_email",
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

    class Meta:
        model = Institute
        fields = [
            "id", "name", "ngo", "ngo_name", "scheme", "scheme_name",
            "address", "state", "district", "latitude", "longitude",
            "incharge", "is_active", "latest_inspection_status",
        ]

    def get_latest_inspection_status(self, obj):
        """
        Used to colour the map marker on the dashboard (Part 9). No AI risk
        score exists yet (Phase 9 not built) — this is honestly just
        "does this institute have a pending/overdue/submitted inspection",
        not a risk assessment.
        """
        latest = obj.inspection_assignments.order_by("-assigned_at").first()
        return latest.status if latest else "NO_INSPECTION"


class ProjectSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source="institute.name", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "institute", "institute_name", "name",
            "start_date", "end_date", "sanctioned_budget", "is_active",
        ]


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = ["id", "institute", "full_name", "designation", "phone_number", "linked_user"]


class BeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Beneficiary
        fields = ["id", "project", "full_name", "phone_number", "linked_user", "enrolled_on"]
