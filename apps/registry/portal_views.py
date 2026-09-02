"""
NGO Admin / Project Incharge portal (fills the gap noted in README.md:
"Role.NGO_ADMIN and Role.PROJECT_INCHARGE exist on the User model but have
no dedicated views/pages yet").

Kept as a separate module/router from apps.registry.views.InstituteViewSet
(IsOfficial) rather than overloading that viewset's permission/scoping
logic — an NGO admin or project incharge sees a materially narrower slice
of data (their own NGO's institutes, or just the institute(s) they're
marked incharge of), and mixing that into the officials' cross-institute
viewset would make both harder to reason about.

Scoping:
- NGO_ADMIN  -> every Institute under any NGO where NGO.admin_user == them.
- PROJECT_INCHARGE -> only Institute rows where Institute.incharge == them.
Both fields already existed on the models before this file (see
apps/registry/models.py) — nothing new to migrate.
"""
from django.db.models import Max
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsNGOOrIncharge, is_ngo_admin, is_project_incharge
from apps.inspections.models import InspectionAssignment

from .models import Beneficiary, Institute, Project, Staff
from .serializers import (
    BeneficiarySerializer,
    InstituteSerializer,
    ProjectSerializer,
    StaffSerializer,
)


def portal_scoped_institutes(user):
    """Institutes visible to the logged-in NGO admin / project incharge."""
    if is_ngo_admin(user):
        return Institute.objects.filter(ngo__admin_user=user)
    if is_project_incharge(user):
        return Institute.objects.filter(incharge=user)
    return Institute.objects.none()


class PortalInstituteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/registry/portal/institutes/         -> list
    GET /api/registry/portal/institutes/<id>/     -> retrieve
    Read-only on purpose: NGO admins/incharges report data through
    inspections/attendance, they don't edit institute registration here.
    """
    serializer_class = InstituteSerializer
    permission_classes = [IsNGOOrIncharge]

    def get_queryset(self):
        return portal_scoped_institutes(self.request.user).select_related("ngo", "scheme")


class PortalProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/registry/portal/projects/?institute=<id>"""
    serializer_class = ProjectSerializer
    permission_classes = [IsNGOOrIncharge]

    def get_queryset(self):
        qs = Project.objects.filter(
            institute__in=portal_scoped_institutes(self.request.user)
        ).select_related("institute")
        institute_id = self.request.query_params.get("institute")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)
        return qs


class PortalStaffViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/registry/portal/staff/?institute=<id>"""
    serializer_class = StaffSerializer
    permission_classes = [IsNGOOrIncharge]

    def get_queryset(self):
        qs = Staff.objects.filter(
            institute__in=portal_scoped_institutes(self.request.user)
        ).select_related("institute")
        institute_id = self.request.query_params.get("institute")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)
        return qs


class PortalBeneficiaryViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/registry/portal/beneficiaries/?project=<id>"""
    serializer_class = BeneficiarySerializer
    permission_classes = [IsNGOOrIncharge]

    def get_queryset(self):
        qs = Beneficiary.objects.filter(
            project__institute__in=portal_scoped_institutes(self.request.user)
        ).select_related("project")
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class PortalDashboardSummaryView(APIView):
    """
    GET /api/registry/portal/dashboard-summary/
    Same shape as apps.registry.views.DashboardSummaryView, scoped to the
    logged-in NGO admin's / project incharge's own institutes instead of
    state/district.
    """
    permission_classes = [IsNGOOrIncharge]

    def get(self, request):
        from apps.analytics.models import AIAlert, RiskSnapshot  # local import, same pattern as DashboardSummaryView

        institutes = portal_scoped_institutes(request.user)
        institute_ids = list(institutes.values_list("id", flat=True))
        projects = Project.objects.filter(institute_id__in=institute_ids)
        assignments = InspectionAssignment.objects.filter(institute_id__in=institute_ids)

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
