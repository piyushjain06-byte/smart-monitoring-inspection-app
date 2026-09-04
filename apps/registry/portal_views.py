"""
NGO Admin / Project Incharge portal.

FLATTENED ARCHITECTURE NOTE
----------------------------
Previously an NGO_ADMIN's visible institutes were found by walking
Institute.ngo__admin_user == them. Since Institute no longer has an `ngo`
field at all (Scheme -> {NGO, Institute, Project} independently now), that
path doesn't exist anymore. The adapted scoping rule below is the closest
equivalent under the flat model — Scheme is now the only thing NGO,
Institute, and Project all share:

    NGO_ADMIN        -> every Institute/Project under any Scheme that an
                         NGO they administer also belongs to.
    PROJECT_INCHARGE -> unaffected: still every Institute where
                         Institute.incharge == them (that field never
                         depended on NGO/Project at all), plus Projects
                         under the same Scheme(s) as those institutes.

If you want NGO portals to be scoped more narrowly than "same Scheme"
later (e.g. an explicit NGO<->Project link table), this is the one place
to change — every view below reads through portal_scoped_institutes() /
portal_scoped_projects() rather than re-deriving scope itself.
"""
from django.db.models import Max
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsNGOOrIncharge, is_ngo_admin, is_project_incharge
from apps.inspections.models import InspectionAssignment

from .models import Beneficiary, Institute, Project, Scheme, Staff
from .serializers import (
    BeneficiarySerializer,
    InstituteSerializer,
    ProjectSerializer,
    StaffSerializer,
)


def portal_scoped_schemes(user):
    """Schemes visible to the logged-in NGO admin / project incharge."""
    if is_ngo_admin(user):
        return Scheme.objects.filter(ngos__admin_user=user).distinct()
    if is_project_incharge(user):
        return Scheme.objects.filter(institutes__incharge=user).distinct()
    return Scheme.objects.none()


def portal_scoped_institutes(user):
    """Institutes visible to the logged-in NGO admin / project incharge."""
    if is_ngo_admin(user):
        return Institute.objects.filter(scheme__in=portal_scoped_schemes(user))
    if is_project_incharge(user):
        return Institute.objects.filter(incharge=user)
    return Institute.objects.none()


def portal_scoped_projects(user):
    """Projects visible to the logged-in NGO admin / project incharge — scheme-scoped."""
    return Project.objects.filter(scheme__in=portal_scoped_schemes(user))


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
        return portal_scoped_institutes(self.request.user).select_related("scheme")


class PortalProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/registry/portal/projects/?scheme=<id optional>
    FLATTENED ARCHITECTURE: was ?institute=<id> — Project has no institute
    field anymore, so this now scopes/filters by scheme instead."""
    serializer_class = ProjectSerializer
    permission_classes = [IsNGOOrIncharge]

    def get_queryset(self):
        qs = portal_scoped_projects(self.request.user).select_related("scheme")
        scheme_id = self.request.query_params.get("scheme")
        if scheme_id:
            qs = qs.filter(scheme_id=scheme_id)
        return qs


class PortalStaffViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/registry/portal/staff/?institute=<id>
    Unaffected by the flatten — Staff still belongs to an Institute."""
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
    """GET /api/registry/portal/beneficiaries/?project=<id>
    Scoped through portal_scoped_projects() (Scheme-based) now, since
    Beneficiary -> Project -> Scheme is the only chain left connecting a
    beneficiary back to something the NGO/incharge can see."""
    serializer_class = BeneficiarySerializer
    permission_classes = [IsNGOOrIncharge]

    def get_queryset(self):
        qs = Beneficiary.objects.filter(
            project__in=portal_scoped_projects(self.request.user)
        ).select_related("project")
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class PortalDashboardSummaryView(APIView):
    """
    GET /api/registry/portal/dashboard-summary/
    Same shape as apps.registry.views.DashboardSummaryView, scoped to the
    logged-in NGO admin's / project incharge's own institutes/projects.
    """
    permission_classes = [IsNGOOrIncharge]

    def get(self, request):
        from apps.analytics.models import AIAlert, RiskSnapshot  # local import, same pattern as DashboardSummaryView

        institutes = portal_scoped_institutes(request.user)
        institute_ids = list(institutes.values_list("id", flat=True))
        projects = portal_scoped_projects(request.user)
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
