"""
Phase 4.7 — Celery tasks. Currently one task: the same risk-engine run that
the "Run AI Analysis" button (POST /api/analytics/run/) and
`manage.py run_risk_analysis` already trigger manually, now also runnable
on a schedule (see CELERY_BEAT_SCHEDULE in config/settings.py — every 6
hours by default).

This directly addresses the README's own "Deliberately not built" note:
    "Celery-scheduled recurring runs (still a manual button / management
    command) ... Once Celery/Redis (Phase 4.7) is wired up, a periodic beat
    schedule calling run_risk_engine() daily/weekly would make the trend
    genuinely useful without manual intervention."
"""
from celery import shared_task

from apps.registry.models import Institute


@shared_task
def audit_cctv_status():
    """Re-score active institutes using each camera's latest heartbeat."""
    from apps.analytics.services.risk_engine import run_risk_engine

    institutes = list(Institute.objects.filter(is_active=True))
    results = run_risk_engine(institutes=institutes, create_alerts=True)
    return {
        "evaluated": len(results),
        "high_risk_count": sum(1 for result in results if result["severity"] == "HIGH"),
    }


@shared_task
def run_risk_analysis_task(institute_id: int | None = None, create_alerts: bool = True):
    """
    Celery equivalent of `manage.py run_risk_analysis`. Scores every active
    institute (or just one, if `institute_id` is given), saves a
    RiskSnapshot per institute, opens AIAlerts for newly-triggered factors,
    and pushes both over the Phase 4.5 WebSocket group so any connected
    dashboard updates without a manual refresh.
    """
    from apps.analytics.services.risk_engine import run_risk_engine

    institutes = Institute.objects.filter(is_active=True)
    if institute_id:
        institutes = institutes.filter(id=institute_id)
    institutes = list(institutes)
    if not institutes:
        return {"evaluated": 0, "high_risk_count": 0, "alerts_created": 0}

    results = run_risk_engine(institutes=institutes, create_alerts=create_alerts)

    summary = {
        "evaluated": len(results),
        "high_risk_count": sum(1 for r in results if r["severity"] == "HIGH"),
        "alerts_created": sum(r["alerts_created"] for r in results),
    }

    _broadcast_analysis_completed(summary)
    return summary


def _broadcast_analysis_completed(summary: dict):
    """Best-effort websocket push — never lets a missing/unreachable Redis break the task."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        from apps.analytics.consumers import ALERTS_GROUP

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            ALERTS_GROUP, {"type": "analysis.completed", "summary": summary},
        )
    except Exception:
        # Channels/Redis not available — the scheduled run still completed
        # and saved its data; the dashboard just won't get a live nudge
        # and will pick it up on its next poll instead.
        pass
