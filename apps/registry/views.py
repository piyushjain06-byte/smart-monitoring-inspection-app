import csv
import uuid

from django.contrib.auth import get_user_model
from django.db.models import Max
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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
    queryset = NGO.objects.select_related("scheme").all()
    serializer_class = NGOSerializer
    permission_classes = [IsOfficial]


class InstituteViewSet(viewsets.ModelViewSet):
    """Powers the dashboard map view (Part 4.5).
    FLATTENED ARCHITECTURE: Institute -> Scheme only (no NGO link)."""
    queryset = Institute.objects.select_related("scheme").all()
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
        """Create an auditable VC session while preserving the Jitsi alert flow."""
        institute = self.get_object()
        initiated_at = timezone.now()
        room_name = f"sih-dosje-call-{institute.id}-{int(initiated_at.timestamp())}-{uuid.uuid4().hex[:12]}"
        from apps.consultations.models import VCParticipant, VCSession
        from apps.inspections.models import InspectionAssignment
        from apps.registry.models import Project

        inspection = None
        if request.data.get("inspection"):
            inspection = InspectionAssignment.objects.filter(
                pk=request.data["inspection"], institute=institute,
            ).first()
            if inspection is None:
                return Response({"detail": "Inspection does not belong to this institute."}, status=400)
        project = None
        if request.data.get("project"):
            project = Project.objects.filter(pk=request.data["project"], scheme_id=institute.scheme_id).first()
            if project is None:
                return Response({"detail": "Project does not belong to this institute's scheme."}, status=400)
        session = VCSession.objects.create(
            institute=institute,
            project=project,
            inspection=inspection,
            room_name=room_name,
            created_by=request.user,
            purpose=request.data.get("purpose", "Surprise video consultation"),
            scheduled_at=parse_datetime(request.data["scheduled_at"]) if request.data.get("scheduled_at") else initiated_at,
        )
        participant_ids = request.data.get("participant_ids", [])
        if isinstance(participant_ids, str):
            participant_ids = [value.strip() for value in participant_ids.split(",") if value.strip()]
        participant_ids = set(participant_ids or []) | {request.user.id}
        users = get_user_model().objects.filter(id__in=participant_ids, is_active=True)
        allowed_roles = {"SUPER_ADMIN", "STATE_AUTHORITY", "DISTRICT_AUTHORITY", "PMU_TEAM", "INSPECTION_OFFICER", "NGO_ADMIN", "PROJECT_INCHARGE"}
        if users.count() != len(participant_ids) or any(user.role not in allowed_roles for user in users):
            session.delete()
            return Response({"detail": "Selected participants are not authorized for this VC."}, status=400)
        for user in users:
            if user.id == request.user.id:
                role = VCParticipant.Role.INITIATOR
            elif user.role in {"SUPER_ADMIN", "STATE_AUTHORITY", "DISTRICT_AUTHORITY"}:
                role = VCParticipant.Role.OFFICIAL
            elif user.role in {"PMU_TEAM", "INSPECTION_OFFICER"}:
                role = VCParticipant.Role.INSPECTOR
            else:
                role = VCParticipant.Role.INSTITUTE
            VCParticipant.objects.create(session=session, user=user, role=role, invited_by=request.user)
        session.start()
        payload = {
            "type": "SURPRISE_VC_ALERT",
            "session_id": session.id,
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
        return Response({
            "session_id": session.id, "room_name": room_name,
            "timestamp": payload["timestamp"], "institute_id": institute.id,
            "status": session.status,
        })

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        """
        GET /api/registry/institutes/export-csv/
        FLATTENED ARCHITECTURE: no NGO column anymore — Scheme is the only
        shared parent an Institute has.
        """
        qs = self.get_queryset()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=institutes.csv"
        writer = csv.writer(response)
        writer.writerow([
            "ID", "Name", "Scheme", "State", "District",
            "Latitude", "Longitude", "Active",
            "Latest Inspection Status", "Latest Risk Severity", "Latest Risk Score",
        ])
        for inst in qs:
            latest_assignment = inst.inspection_assignments.order_by("-assigned_at").first()
            latest_snapshot = inst.risk_snapshots.order_by("-computed_at").first()
            writer.writerow([
                inst.id, inst.name, inst.scheme.name,
                inst.state, inst.district, inst.latitude, inst.longitude, inst.is_active,
                latest_assignment.status if latest_assignment else "NO_INSPECTION",
                latest_snapshot.severity if latest_snapshot else "",
                latest_snapshot.score if latest_snapshot else "",
            ])
        return response


class ProjectViewSet(viewsets.ModelViewSet):
    """FLATTENED ARCHITECTURE: Project -> Scheme only (no Institute link).
    Supports ?scheme=<id> (previously ?institute=<id>)."""
    queryset = Project.objects.select_related("scheme").all()
    serializer_class = ProjectSerializer
    permission_classes = [IsOfficial]

    def get_queryset(self):
        qs = super().get_queryset()
        scheme_id = self.request.query_params.get("scheme")
        if scheme_id:
            qs = qs.filter(scheme_id=scheme_id)
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

    FLATTENED ARCHITECTURE: Projects no longer belong to Institutes, so
    "active projects" is now scoped by the Scheme(s) covered by the
    institutes in view, rather than by institute id.

    high_risk_institutes / open_ai_alerts come from apps.analytics
    (Phase 9's rule-based risk engine + Isolation Forest anomaly model) —
    real, computed values, not a fabricated number.
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
        scheme_ids = list(institutes.values_list("scheme_id", flat=True))
        projects = Project.objects.filter(scheme_id__in=scheme_ids)
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
            "pending_inspections": assignments.filter(status__in=[InspectionAssignment.Status.PENDING, InspectionAssignment.Status.ACCEPTED, InspectionAssignment.Status.IN_PROGRESS, InspectionAssignment.Status.CHANGES_REQUIRED]).count(),
            "overdue_inspections": assignments.filter(status=InspectionAssignment.Status.OVERDUE).count(),
            "submitted_inspections": assignments.filter(status=InspectionAssignment.Status.SUBMITTED).count(),
            "under_review_inspections": assignments.filter(status=InspectionAssignment.Status.UNDER_REVIEW).count(),
            "approved_inspections": assignments.filter(status=InspectionAssignment.Status.APPROVED).count(),
            "completed_inspections": assignments.filter(status=InspectionAssignment.Status.COMPLETED).count(),
            "high_risk_institutes": high_risk_institutes,
            "open_ai_alerts": open_ai_alerts,
        })
