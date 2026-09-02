"""
Phase 9, Part 24/25 — Risk Engine + AI Alerts.

Implements the plan's rule-based risk score as literally as possible:

    Attendance mismatch   +25
    CCTV offline          +20
    Failed inspection     +30
    Unusual attendance    +15   (from the Isolation Forest model, see anomaly.py)
    Repeated issues       +10
    ---
    100 max

    0-30 LOW | 31-60 MEDIUM | 61-100 HIGH

A factor only fires when there's real data to judge it on — an institute
with no cameras yet doesn't get "CCTV offline" points, and one with no
attendance records yet doesn't get "attendance mismatch" points. This
mirrors DashboardSummaryView's existing rule in apps/registry/views.py:
report what's actually known, never a fabricated number.

Phase 4.5 addition: every newly-created AIAlert is also broadcast over the
"ai_alerts" Channels group (see apps/analytics/consumers.py), so any
connected dashboard sees it immediately instead of waiting for its next
poll. The broadcast is best-effort — if Redis/Channels isn't running, the
snapshot/alert are still saved to the DB exactly as before this phase.
"""
from django.utils import timezone

from apps.registry.models import Institute

from .anomaly import detect_anomalies
from .features import collect_features

ATTENDANCE_MISMATCH_THRESHOLD = 0.70  # below 70% present -> flagged
FAILED_INSPECTION_THRESHOLD = 50      # overall_score below this -> flagged
REPEATED_ISSUES_THRESHOLD = 2         # this many recent HIGH alerts -> flagged

POINTS = {
    "ATTENDANCE_MISMATCH": 25,
    "CCTV_OFFLINE": 20,
    "FAILED_INSPECTION": 30,
    "UNUSUAL_ATTENDANCE": 15,
    "REPEATED_ISSUES": 10,
}


def _severity_for(score: int) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    return "HIGH"


def _factors_for(features: dict, is_anomaly: bool) -> list:
    factors = []

    if features["attendance_rate"] is not None and features["attendance_rate"] < ATTENDANCE_MISMATCH_THRESHOLD:
        pct = round(features["attendance_rate"] * 100)
        factors.append({
            "factor": "ATTENDANCE_MISMATCH",
            "points": POINTS["ATTENDANCE_MISMATCH"],
            "detail": f"Staff attendance {pct}% over the last {features['attendance_sample_size']} marked days.",
        })

    if features["camera_online_ratio"] is not None and features["camera_online_ratio"] == 0.0:
        factors.append({
            "factor": "CCTV_OFFLINE",
            "points": POINTS["CCTV_OFFLINE"],
            "detail": f"All {features['camera_count']} registered camera(s) are offline.",
        })

    if features["latest_inspection_score"] is not None and features["latest_inspection_score"] < FAILED_INSPECTION_THRESHOLD:
        factors.append({
            "factor": "FAILED_INSPECTION",
            "points": POINTS["FAILED_INSPECTION"],
            "detail": f"Most recent inspection scored {features['latest_inspection_score']}/100.",
        })

    if is_anomaly:
        factors.append({
            "factor": "UNUSUAL_ATTENDANCE",
            "points": POINTS["UNUSUAL_ATTENDANCE"],
            "detail": "Flagged by the anomaly model as statistically unusual compared to other institutes.",
        })

    if features["recent_high_alerts"] >= REPEATED_ISSUES_THRESHOLD:
        factors.append({
            "factor": "REPEATED_ISSUES",
            "points": POINTS["REPEATED_ISSUES"],
            "detail": f"{features['recent_high_alerts']} high-risk alerts already raised in the last 90 days.",
        })

    return factors


def compute_risk_for_institute(institute: Institute, anomaly_result: dict | None = None) -> dict:
    """
    Computes (but does not save) the risk breakdown for one institute.
    `anomaly_result` is {"is_anomaly": bool, "anomaly_score": float|None} —
    pass it in when scoring many institutes in one batch (see run_risk_engine)
    so the anomaly model only runs once instead of once per institute.
    """
    features = collect_features(institute)
    anomaly_result = anomaly_result or detect_anomalies({institute.id: features})[institute.id]

    factors = _factors_for(features, anomaly_result["is_anomaly"])
    score = min(100, sum(f["points"] for f in factors))

    return {
        "institute_id": institute.id,
        "score": score,
        "severity": _severity_for(score),
        "factors": factors,
        "features": features,
        "is_anomaly": anomaly_result["is_anomaly"],
        "anomaly_score": anomaly_result["anomaly_score"],
    }


def _broadcast_alert_created(alert):
    """
    Best-effort push over the Phase 4.5 WebSocket group. Never raises —
    a missing/unreachable Redis must not break saving the alert itself,
    same "degrade, don't crash" philosophy as the rest of this codebase
    (e.g. apps/analytics/services/anomaly.py's insufficient-data fallback).
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        from apps.analytics.consumers import ALERTS_GROUP
        from apps.analytics.serializers import AIAlertSerializer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            ALERTS_GROUP,
            {"type": "alert.created", "alert": AIAlertSerializer(alert).data},
        )
    except Exception:
        pass


def run_risk_engine(institutes=None, create_alerts: bool = True) -> list:
    """
    Part 22-25 end to end: scores every institute, saves a RiskSnapshot each,
    and opens an AIAlert for every newly-triggered factor (Part 25).
    Alerts aren't re-created if an OPEN alert of the same type already
    exists for that institute — re-running this shouldn't spam duplicates.

    Returns a list of dicts (one per institute) for the caller to serialize.
    """
    from apps.analytics.models import AIAlert, RiskSnapshot

    institutes = list(institutes) if institutes is not None else list(Institute.objects.filter(is_active=True))

    features_by_institute = {inst.id: collect_features(inst) for inst in institutes}
    anomaly_by_institute = detect_anomalies(features_by_institute)

    results = []
    for institute in institutes:
        breakdown = compute_risk_for_institute(institute, anomaly_result=anomaly_by_institute[institute.id])

        snapshot = RiskSnapshot.objects.create(
            institute=institute,
            score=breakdown["score"],
            severity=breakdown["severity"],
            factors=breakdown["factors"],
            features=breakdown["features"],
            is_anomaly=breakdown["is_anomaly"],
            anomaly_score=breakdown["anomaly_score"],
        )

        alerts_created = 0
        if create_alerts:
            for factor in breakdown["factors"]:
                already_open = AIAlert.objects.filter(
                    institute=institute, alert_type=factor["factor"], status=AIAlert.Status.OPEN,
                ).exists()
                if already_open:
                    continue
                alert = AIAlert.objects.create(
                    institute=institute,
                    snapshot=snapshot,
                    alert_type=factor["factor"],
                    description=factor["detail"],
                    risk_score=breakdown["score"],
                    severity=breakdown["severity"],
                )
                alerts_created += 1
                _broadcast_alert_created(alert)

        results.append({**breakdown, "snapshot_id": snapshot.id, "alerts_created": alerts_created})

    return results
