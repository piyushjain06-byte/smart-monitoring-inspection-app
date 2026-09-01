from django.contrib import admin

from .models import AIAlert, RiskSnapshot


@admin.register(RiskSnapshot)
class RiskSnapshotAdmin(admin.ModelAdmin):
    list_display = ("institute", "score", "severity", "is_anomaly", "computed_at")
    list_filter = ("severity", "is_anomaly")
    search_fields = ("institute__name",)
    readonly_fields = ("computed_at",)


@admin.register(AIAlert)
class AIAlertAdmin(admin.ModelAdmin):
    list_display = ("institute", "alert_type", "severity", "status", "risk_score", "created_at")
    list_filter = ("alert_type", "severity", "status")
    search_fields = ("institute__name", "description")
    readonly_fields = ("created_at",)
