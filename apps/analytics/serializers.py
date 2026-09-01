from rest_framework import serializers

from .models import AIAlert, RiskSnapshot


class RiskSnapshotSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source="institute.name", read_only=True)

    class Meta:
        model = RiskSnapshot
        fields = [
            "id", "institute", "institute_name", "score", "severity",
            "factors", "features", "is_anomaly", "anomaly_score", "computed_at",
        ]


class AIAlertSerializer(serializers.ModelSerializer):
    institute_name = serializers.CharField(source="institute.name", read_only=True)
    alert_type_display = serializers.CharField(source="get_alert_type_display", read_only=True)

    class Meta:
        model = AIAlert
        fields = [
            "id", "institute", "institute_name", "alert_type", "alert_type_display",
            "description", "risk_score", "severity", "status", "created_at", "resolved_at",
        ]
        read_only_fields = ["created_at", "resolved_at"]


class RunAnalysisRequestSerializer(serializers.Serializer):
    institute = serializers.IntegerField(required=False, help_text="Limit the run to one institute's id.")
