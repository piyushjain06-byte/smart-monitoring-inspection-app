"""
Phase 9 views. Same shape as apps.inspections.views' auto-assign/surprise
actions: a POST "run" endpoint the official clicks on the dashboard, plus
read-only listing for what the engine has already produced.
"""
from django.db.models import Max
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOfficial
from apps.registry.models import Institute

from .models import AIAlert, RiskSnapshot
from .serializers import AIAlertSerializer, RiskSnapshotSerializer, RunAnalysisRequestSerializer
from .services.risk_engine import compute_risk_for_institute, run_risk_engine


def _scoped_institutes(user):
    """Same district/state scoping as InstituteViewSet/DashboardSummaryView (apps.registry.views)."""
    qs = Institute.objects.filter(is_active=True)
    if user.is_superuser or user.is_staff:
        return qs
    if getattr(user, "role", None) == "DISTRICT_AUTHORITY" and user.district:
        return qs.filter(district=user.district)
    if getattr(user, "role", None) == "STATE_AUTHORITY" and user.state:
        return qs.filter(state=user.state)
    return qs


class RiskSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/analytics/risk/            -> most recent snapshot per institute
    GET /api/analytics/risk/<pk>/       -> one specific snapshot
    GET /api/analytics/risk/institute/<institute_id>/live/     -> compute fresh, no snapshot needed/saved
    GET /api/analytics/risk/institute/<institute_id>/pdf/      -> downloadable AI Risk Report (Part 33)
    GET /api/analytics/risk/institute/<institute_id>/history/  -> past snapshots, chronological (Part 33 trends)
    """
    serializer_class = RiskSnapshotSerializer
    permission_classes = [IsOfficial]

    def get_queryset(self):
        institutes = _scoped_institutes(self.request.user)
        latest_per_institute = (
            RiskSnapshot.objects.filter(institute__in=institutes)
            .values("institute")
            .annotate(latest=Max("computed_at"))
            .values_list("latest", flat=True)
        )
        return (
            RiskSnapshot.objects.filter(institute__in=institutes, computed_at__in=latest_per_institute)
            .select_related("institute")
            .order_by("-score")
        )

    @action(detail=False, methods=["get"], url_path=r"institute/(?P<institute_id>\d+)/live")
    def live(self, request, institute_id=None):
        """
        Computes a fresh breakdown for one institute without requiring a
        saved snapshot to already exist — used by the institute detail page
        so it works even before anyone has clicked "Run AI Analysis" yet.

        Also reports `last_snapshot_at` / `last_snapshot_age_days` — the
        timestamp of the most recent *saved* RiskSnapshot (if any), kept
        deliberately separate from the freshly-computed score above. Since
        there's no Celery scheduler yet (see README's "Stale trend nudge"
        item), a saved score can silently go stale; the frontend uses this
        to show "last analyzed N days ago" next to the live number.
        """
        try:
            institute = _scoped_institutes(request.user).get(id=institute_id)
        except Institute.DoesNotExist:
            return Response({"detail": "Institute not found."}, status=status.HTTP_404_NOT_FOUND)

        breakdown = compute_risk_for_institute(institute)
        breakdown["institute_name"] = institute.name

        last_snapshot = institute.risk_snapshots.order_by("-computed_at").first()
        if last_snapshot:
            breakdown["last_snapshot_at"] = last_snapshot.computed_at.isoformat()
            breakdown["last_snapshot_age_days"] = (timezone.now() - last_snapshot.computed_at).days
        else:
            breakdown["last_snapshot_at"] = None
            breakdown["last_snapshot_age_days"] = None

        return Response(breakdown)

    @action(detail=False, methods=["get"], url_path=r"institute/(?P<institute_id>\d+)/pdf")
    def pdf(self, request, institute_id=None):
        """
        GET /api/analytics/risk/institute/<id>/pdf/
        Part 33 of the plan — downloadable AI Risk Report. Computes a fresh
        breakdown (same as `live/`) and renders it through WeasyPrint,
        mirroring the pattern already used for inspection reports in
        apps/inspections/views.py.
        """
        try:
            institute = _scoped_institutes(request.user).get(id=institute_id)
        except Institute.DoesNotExist:
            return Response({"detail": "Institute not found."}, status=status.HTTP_404_NOT_FOUND)

        breakdown = compute_risk_for_institute(institute)
        html = render_to_string("analytics/risk_report.html", {
            "institute": institute,
            "breakdown": breakdown,
            "generated_at": timezone.now(),
        })

        try:
            from weasyprint import HTML

            pdf = HTML(string=html).write_pdf()
            resp = HttpResponse(pdf, content_type="application/pdf")
            resp["Content-Disposition"] = f"attachment; filename=risk-report-{institute.id}.pdf"
            return resp
        except Exception:
            return HttpResponse(html)

    @action(detail=False, methods=["get"], url_path=r"institute/(?P<institute_id>\d+)/history")
    def history(self, request, institute_id=None):
        """
        GET /api/analytics/risk/institute/<id>/history/?limit=20
        Part 33 — "historical trends". Every POST /api/analytics/run/ already
        saves a new RiskSnapshot row instead of overwriting the old one
        (see RiskSnapshot.Meta.ordering = ['-computed_at']), so this just
        surfaces that existing history in chronological order for charting.
        Returns the most recent `limit` snapshots (default 20), oldest first.
        """
        try:
            institute = _scoped_institutes(request.user).get(id=institute_id)
        except Institute.DoesNotExist:
            return Response({"detail": "Institute not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            limit = int(request.query_params.get("limit", 20))
        except ValueError:
            limit = 20
        limit = max(1, min(limit, 100))

        snapshots = list(
            RiskSnapshot.objects.filter(institute=institute).order_by("-computed_at")[:limit]
        )
        snapshots.reverse()  # chronological (oldest -> newest) for a left-to-right chart

        serializer = RiskSnapshotSerializer(snapshots, many=True)
        return Response(serializer.data)


class AIAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/analytics/alerts/?institute=&status=&severity= — Part 25/34."""
    serializer_class = AIAlertSerializer
    permission_classes = [IsOfficial]
    queryset = AIAlert.objects.select_related("institute").all()

    def get_queryset(self):
        qs = super().get_queryset().filter(institute__in=_scoped_institutes(self.request.user))
        institute_id = self.request.query_params.get("institute")
        status_param = self.request.query_params.get("status")
        severity = self.request.query_params.get("severity")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if severity:
            qs = qs.filter(severity=severity.upper())
        return qs

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        alert.status = AIAlert.Status.ACKNOWLEDGED
        alert.save(update_fields=["status"])
        return Response(AIAlertSerializer(alert).data)

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.status = AIAlert.Status.RESOLVED
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["status", "resolved_at"])
        return Response(AIAlertSerializer(alert).data)


class RunAnalysisView(APIView):
    """
    POST /api/analytics/run/
    Body: {"institute": <id, optional>} — omit to score every active institute.
    Part 22-25 end to end: runs the risk engine (rule-based score + Isolation
    Forest anomaly check), saves a RiskSnapshot per institute, opens AIAlerts
    for newly-triggered factors. This is the "AI ALERT" generator the plan's
    dashboard mockup (Part 10) expects — there's no Celery/scheduler yet
    (see requirements.txt), so for now an official triggers it manually,
    same as the "Surprise Inspection" button.
    """
    permission_classes = [IsOfficial]

    def post(self, request):
        serializer = RunAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        institute_id = serializer.validated_data.get("institute")

        institutes = _scoped_institutes(request.user)
        if institute_id:
            institutes = institutes.filter(id=institute_id)
            if not institutes.exists():
                return Response({"detail": "Institute not found."}, status=status.HTTP_404_NOT_FOUND)

        results = run_risk_engine(institutes=list(institutes))

        return Response({
            "evaluated": len(results),
            "high_risk_count": sum(1 for r in results if r["severity"] == "HIGH"),
            "anomalies_flagged": sum(1 for r in results if r["is_anomaly"]),
            "alerts_created": sum(r["alerts_created"] for r in results),
            "results": [
                {
                    "institute_id": r["institute_id"],
                    "score": r["score"],
                    "severity": r["severity"],
                    "is_anomaly": r["is_anomaly"],
                    "factors": r["factors"],
                }
                for r in results
            ],
        }, status=status.HTTP_200_OK)
