from rest_framework import serializers

from apps.accounts.models import Role, User

from .models import SchemeApplication


class ApplicantRegisterSerializer(serializers.Serializer):
    """
    Public self-registration for an NGO/Institute admin (POST /api/onboarding/register/).
    Creates a bare User account with the right role — no NGO/Institute
    exists yet. Those only get created once a SchemeApplication this user
    submits is approved (see apps.onboarding.services.approve_application).
    """
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    applicant_type = serializers.ChoiceField(choices=SchemeApplication.ApplicantType.choices)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("That username is already taken.")
        return value

    def create(self, validated_data):
        applicant_type = validated_data.pop("applicant_type")
        role = Role.NGO_ADMIN if applicant_type == SchemeApplication.ApplicantType.NGO else Role.PROJECT_INCHARGE
        password = validated_data.pop("password")
        user = User(role=role, **validated_data)
        user.set_password(password)
        user.save()
        return user


class SchemeApplicationCreateSerializer(serializers.ModelSerializer):
    """What the applicant fills in when applying for a scheme."""

    class Meta:
        model = SchemeApplication
        fields = [
            "id", "applicant_type", "scheme",
            "organization_name", "registration_number", "contact_person",
            "contact_phone", "contact_email", "address", "state", "district",
            "latitude", "longitude",
            "project_name", "project_plan", "proposed_fund_amount",
            "proposed_start_date", "proposed_end_date",
            "status", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate(self, data):
        applicant_type = data.get("applicant_type")
        if applicant_type == SchemeApplication.ApplicantType.NGO and not data.get("registration_number"):
            raise serializers.ValidationError({"registration_number": "Required for NGO applications."})
        if applicant_type == SchemeApplication.ApplicantType.INSTITUTE:
            for field in ("state", "district"):
                if not data.get(field):
                    raise serializers.ValidationError({field: "Required for Institute applications."})
        return data

    def validate_registration_number(self, value):
        from apps.registry.models import NGO

        if value and NGO.objects.filter(registration_number=value).exists():
            raise serializers.ValidationError("An NGO with this registration number is already on the platform.")
        return value


class SchemeApplicationSerializer(serializers.ModelSerializer):
    """Full read serializer — used for the applicant's own list and the government review queue."""
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)
    applicant_username = serializers.CharField(source="applicant.username", read_only=True)
    applicant_display_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    applicant_type_display = serializers.CharField(source="get_applicant_type_display", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True)

    class Meta:
        model = SchemeApplication
        fields = [
            "id", "applicant", "applicant_username", "applicant_display_name",
            "applicant_type", "applicant_type_display", "scheme", "scheme_name",
            "organization_name", "registration_number", "contact_person",
            "contact_phone", "contact_email", "address", "state", "district",
            "latitude", "longitude",
            "project_name", "project_plan", "proposed_fund_amount",
            "proposed_start_date", "proposed_end_date",
            "status", "status_display", "review_notes", "approved_fund_amount",
            "reviewed_by", "reviewed_by_username", "reviewed_at",
            "created_ngo", "created_institute", "created_project",
            "created_at",
        ]
        read_only_fields = fields

    def get_applicant_display_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.username


class SchemeApplicationReviewSerializer(serializers.Serializer):
    """Body for the approve/reject actions."""
    approved_fund_amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    review_notes = serializers.CharField(required=False, allow_blank=True)
