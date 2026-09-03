import csv
import uuid

from django.db.models import Max
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOfficial, IsOfficialOrFieldOfficer
from apps.inspections.models import InspectionAssignment

from .models import Beneficiary, Institute, NGO, Project, Scheme, Staff
from .serializers import (
    BeneficiarySerializer,
    InstituteSerializer,
    NGOSerializer,
    ProjectSerializer,
    SchemeSerializer,
    StaffSerializer,
)


class SchemeViewSet(viewsets.ModelViewSet):
    queryset = Scheme.objects.all()
    serializer_class = SchemeSerializer
    permission_classes = [IsOfficial]


class NGOViewSet(viewsets.ModelViewSet):
    queryset = NGO.objects.all()
    serializer_class = NGOSerializer
    permission_classes = [IsOfficial]


class InstituteViewSet(viewsets.ModelViewSet):
    """Powers the dashboard map view (Part 4.5) once we build it."""
    queryset = Institute.objects.select_related("ngo", "scheme").all()
    serializer_class = InstituteSerializer
    permission_classes = [IsOfficial]

    def get_permissions(self):
        if self.action == "initiate_vc":
            return [IsOfficialOrFieldOfficer()]
        return super().get_permissions()

    def get_queryset(self):
        """
        Role-based scoping (Part 4.1 / Part 10 — a district authority should
        never see another district's data). Simple version for now.
        """
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated or user.is_superuser:
            return qs
        if user.role == "DISTRICT_AUTHORITY" and user.district:
            return qs.filter(district=user.district)
        if user.role == "STATE_AUTHORITY" and user.state:
            return qs.filter(state=user.state)
        return qs

    @action(detail=True, methods=["post"], url_path="initiate-vc")
    def initiate_vc(self, request, pk=None):
        """Create a private, auditable Jitsi room and notify institute users."""
        institute = self.get_object()
        initiated_at = timezone.now()
        room_name = f"sih-dosje-call-{institute.id}-{int(initiated_at.timestamp())}-{uuid.uuid4().hex[:12]}"
        payload = {
            "type": "SURPRISE_VC_ALERT",
            "room_name": room_name,
            "initiated_by": {
                "id": request.user.id,
                "name": request.user.get_full_name() or request.user.username,
            },
            "timestamp": initiated_at.isoformat(),
            "institute_id": institute.id,
            "institute_name": institute.name,
        }
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    f"institute_{institute.id}",
                    {"type": "surprise.vc.alert", "payload": payload},
                )
        except Exception:
            # Room creation remains usable when Redis is unavailable.
            pass
        return Response({"room_name": room_name, "timestamp": payload["timestamp"], "institute_id": institute.id})

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        """
        GET /api/registry/institutes/export-csv/
        Plain CSV export for offline government reporting (see README's
        "Good next tasks" list) — same scoping as the normal list endpoint,
        no new dependencies, just csv.writer + HttpResponse.
        """
        qs = self.get_queryset()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=institutes.csv"
        writer = csv.writer(response)
        writer.writerow([
            "ID", "Name", "NGO", "Scheme", "State", "District",
            "Latitude", "Longitude", "Active",
            "Latest Inspection Status", "Latest Risk Severity", "Latest Risk Score",
        ])
        for inst in qs:
            latest_assignment = inst.inspection_assignments.order_by("-assigned_at").first()
            latest_snapshot = inst.risk_snapshots.order_by("-computed_at").first()
            writer.writerow([
                inst.id, inst.name, inst.ngo.name, inst.scheme.name,
                inst.state, inst.district, inst.latitude, inst.longitude, inst.is_active,
                latest_assignment.status if latest_assignment else "NO_INSPECTION",
                latest_snapshot.severity if latest_snapshot else "",
                latest_snapshot.score if latest_snapshot else "",
            ])
        return response


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related("institute").all()
    serializer_class = ProjectSerializer
    permission_classes = [IsOfficial]

    def get_queryset(self):
        """Supports ?institute=<id> so the dashboard can show one institute's projects."""
        qs = super().get_queryset()
        institute_id = self.request.query_params.get("institute")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)
        return qs


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.select_related("institute").all()
    serializer_class = StaffSerializer
    permission_classes = [IsOfficial]


class BeneficiaryViewSet(viewsets.ModelViewSet):
    queryset = Beneficiary.objects.select_related("project").all()
    serializer_class = BeneficiarySerializer
    permission_classes = [IsOfficial]


class DashboardSummaryView(APIView):
    """
    GET /api/registry/dashboard-summary/
    Powers the top stat cards + map on the React government dashboard
    (Part 10 of the plan). Respects the same state/district scoping as
    InstituteViewSet.

    high_risk_institutes / open_ai_alerts come from apps.analytics
    (Phase 9's rule-based risk engine + Isolation Forest anomaly model) —
    real, computed values from whatever RiskSnapshot/AIAlert rows exist,
    not a fabricated number. They read 0 until someone runs the risk
    engine (POST /api/analytics/run/) at least once.
    """
    permission_classes = [IsOfficial]

    def get(self, request):
        from apps.analytics.models import AIAlert, RiskSnapshot  # local import: registry doesn't need analytics at import time

        user = request.user
        institutes = Institute.objects.all()
        if not (user.is_superuser or user.is_staff):
            if getattr(user, "role", None) == "DISTRICT_AUTHORITY" and user.district:
                institutes = institutes.filter(district=user.district)
            elif getattr(user, "role", None) == "STATE_AUTHORITY" and user.state:
                institutes = institutes.filter(state=user.state)

        institute_ids = list(institutes.values_list("id", flat=True))
        projects = Project.objects.filter(institute_id__in=institute_ids)
        assignments = InspectionAssignment.objects.filter(institute_id__in=institute_ids)

        # Latest RiskSnapshot per institute, counted HIGH — mirrors
        # RiskSnapshotViewSet.get_queryset() in apps.analytics.views.
        latest_per_institute = (
            RiskSnapshot.objects.filter(institute_id__in=institute_ids)
            .values("institute").annotate(latest=Max("computed_at")).values_list("latest", flat=True)
        )
        high_risk_institutes = RiskSnapshot.objects.filter(
            institute_id__in=institute_ids, computed_at__in=latest_per_institute, severity="HIGH",
        ).count()
        open_ai_alerts = AIAlert.objects.filter(
            institute_id__in=institute_ids, status=AIAlert.Status.OPEN,
        ).count()

        return Response({
            "total_institutes": institutes.count(),
            "active_institutes": institutes.filter(is_active=True).count(),
            "total_projects": projects.count(),
            "active_projects": projects.filter(is_active=True).count(),
            "pending_inspections": assignments.filter(status=InspectionAssignment.Status.PENDING).count(),
            "overdue_inspections": assignments.filter(status=InspectionAssignment.Status.OVERDUE).count(),
            "submitted_inspections": assignments.filter(status=InspectionAssignment.Status.SUBMITTED).count(),
            "high_risk_institutes": high_risk_institutes,
            "open_ai_alerts": open_ai_alerts,
        })
