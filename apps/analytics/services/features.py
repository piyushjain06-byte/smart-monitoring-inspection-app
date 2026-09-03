"""
Phase 9 — feature collection for one institute.

Every value here is either a real number derived from data that actually
exists in the DB today, or `None` when there isn't enough data yet. `None`
is a signal, not a bug: apps/analytics/services/risk_engine.py treats a
missing feature as "can't judge this factor" rather than guessing — same
philosophy as apps/inspections/services.py falling back to a distance
penalty instead of crashing when an officer has no base_latitude/longitude.

No `cctv_people_count` field exists here on purpose — that needs YOLO
(Part 29), which isn't built. `camera_online_ratio` (from Part 26/28, which
IS built) is the CCTV signal instead.
"""
from datetime import timedelta

from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.cctv.models import Camera
from apps.inspections.models import InspectionAssignment, InspectionReport
from apps.registry.models import Beneficiary, Institute, Staff

ATTENDANCE_WINDOW_DAYS = 30
ALERT_LOOKBACK_DAYS = 90


def collect_features(institute: Institute) -> dict:
    """Returns the raw signals the risk engine + anomaly model read for one institute."""
    from apps.analytics.models import AIAlert  # local import: analytics -> registry, not the other way

    staff_count = Staff.objects.filter(institute=institute).count()
    beneficiary_count = Beneficiary.objects.filter(project__institute=institute).count()

    # --- Attendance rate (staff PRESENT / total marks in the last N days) ---
    since = timezone.now().date() - timedelta(days=ATTENDANCE_WINDOW_DAYS)
    recent_records = AttendanceRecord.objects.filter(institute=institute, date__gte=since)
    total_marks = recent_records.count()
    attendance_rate = (
        recent_records.filter(status=AttendanceRecord.Status.PRESENT).count() / total_marks
        if total_marks > 0 else None
    )

    # --- CCTV uptime proxy: share of this institute's active cameras that are ONLINE right now ---
    cameras = list(Camera.objects.filter(institute=institute, is_active=True))
    camera_online_ratio = (
        sum(1 for c in cameras if c.status == "ONLINE") / len(cameras) if cameras else None
    )
    offline_hours = [c.offline_hours() for c in cameras]

    # --- Most recent submitted inspection score ---
    latest_report = (
        InspectionReport.objects.filter(assignment__institute=institute, overall_score__isnull=False)
        .order_by("-submitted_at")
        .first()
    )
    latest_inspection_score = latest_report.overall_score if latest_report else None

    # --- How often this institute gets inspected at all (Part 22's "inspection_frequency") ---
    inspection_frequency = InspectionAssignment.objects.filter(institute=institute).count()

    # --- Repeated issues: HIGH-severity alerts already raised recently ---
    alert_since = timezone.now() - timedelta(days=ALERT_LOOKBACK_DAYS)
    recent_high_alerts = AIAlert.objects.filter(
        institute=institute, severity="HIGH", created_at__gte=alert_since,
    ).count()

    return {
        "staff_count": staff_count,
        "beneficiary_count": beneficiary_count,
        "attendance_rate": attendance_rate,
        "attendance_sample_size": total_marks,
        "camera_online_ratio": camera_online_ratio,
        "camera_count": len(cameras),
        "cctv_offline_over_48_count": sum(hours > 48 for hours in offline_hours),
        "cctv_max_offline_hours": round(max(offline_hours, default=0.0), 1),
        "latest_inspection_score": latest_inspection_score,
        "inspection_frequency": inspection_frequency,
        "recent_high_alerts": recent_high_alerts,
    }
