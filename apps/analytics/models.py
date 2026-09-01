"""
Phase 9 — AI (Part 23/24/25 of the plan).

Two models:

    RiskSnapshot  — one row per institute per time the risk engine runs.
    Stores the 0-100 score, the LOW/MEDIUM/HIGH bucket, and the factor
    breakdown that produced it (so the dashboard/report can show *why*,
    not just the number — mirrors how InspectionAssignment.weight_snapshot
    stores the assignment-engine breakdown in apps.inspections).

    AIAlert       — a single triggered issue (Part 25), e.g. "CCTV offline"
    or "Attendance anomaly detected". Created by the risk engine when a
    factor fires, so the dashboard's "AI ALERTS" panel (Part 10) has
    something real to list instead of the placeholder in Dashboard.jsx.

Deliberately NOT storing a `cctv_people_count` field or anything YOLO-shaped
— Part 29 (OpenCV + YOLO person detection) isn't built. The risk engine
uses camera *uptime* (Part 26/28, which IS built) as its CCTV signal, not a
fabricated headcount. See apps/analytics/services/risk_engine.py.
"""
from django.db import models

from apps.registry.models import Institute


class RiskSeverity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class RiskSnapshot(models.Model):
    """One risk-engine run for one institute. Part 24 + Part 33 (historical trends)."""

    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="risk_snapshots")
    score = models.PositiveSmallIntegerField(help_text="0-100, see apps.analytics.services.risk_engine")
    severity = models.CharField(max_length=10, choices=RiskSeverity.choices)

    # e.g. [{"factor": "ATTENDANCE_MISMATCH", "points": 25, "detail": "..."}]
    factors = models.JSONField(default=list, blank=True)

    # Raw feature values the engine computed this institute from, kept for
    # debugging/audit and so the anomaly detector's inputs are inspectable.
    features = models.JSONField(default=dict, blank=True)

    is_anomaly = models.BooleanField(
        default=False, help_text="Flagged by the Isolation Forest model (Part 23) as unusual vs. other institutes.",
    )
    anomaly_score = models.FloatField(
        null=True, blank=True, help_text="Raw Isolation Forest decision_function score; lower = more anomalous.",
    )

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-computed_at"]
        indexes = [models.Index(fields=["institute", "-computed_at"])]

    def __str__(self):
        return f"{self.institute.name} — {self.score}/100 ({self.severity})"


class AIAlert(models.Model):
    """A single triggered risk factor for an institute. Part 25."""

    class AlertType(models.TextChoices):
        ATTENDANCE_MISMATCH = "ATTENDANCE_MISMATCH", "Attendance mismatch"
        CCTV_OFFLINE = "CCTV_OFFLINE", "CCTV offline"
        FAILED_INSPECTION = "FAILED_INSPECTION", "Failed inspection"
        UNUSUAL_ATTENDANCE = "UNUSUAL_ATTENDANCE", "Unusual attendance pattern"
        REPEATED_ISSUES = "REPEATED_ISSUES", "Repeated issues"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"

    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="ai_alerts")
    snapshot = models.ForeignKey(
        RiskSnapshot, on_delete=models.CASCADE, related_name="alerts", null=True, blank=True,
    )
    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    description = models.CharField(max_length=255)
    risk_score = models.PositiveSmallIntegerField(help_text="Institute's overall score at the time this fired")
    severity = models.CharField(max_length=10, choices=RiskSeverity.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.severity}] {self.get_alert_type_display()} — {self.institute.name}"
