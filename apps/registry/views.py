from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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


class NGOViewSet(viewsets.ModelViewSet):
    queryset = NGO.objects.all()
    serializer_class = NGOSerializer


class InstituteViewSet(viewsets.ModelViewSet):
    """Powers the dashboard map view (Part 4.5) once we build it."""
    queryset = Institute.objects.select_related("ngo", "scheme").all()
    serializer_class = InstituteSerializer

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


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related("institute").all()
    serializer_class = ProjectSerializer

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


class BeneficiaryViewSet(viewsets.ModelViewSet):
    queryset = Beneficiary.objects.select_related("project").all()
    serializer_class = BeneficiarySerializer


class DashboardSummaryView(APIView):
    """
    GET /api/registry/dashboard-summary/
    Powers the top stat cards + map on the React government dashboard
    (Part 10 of the plan). Deliberately only reports what's actually
    implemented so far (no fabricated AI risk scores — that's Phase 9,
    not built yet). Respects the same state/district scoping as
    InstituteViewSet.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        institutes = Institute.objects.all()
        if not (user.is_superuser or user.is_staff):
            if getattr(user, "role", None) == "DISTRICT_AUTHORITY" and user.district:
                institutes = institutes.filter(district=user.district)
            elif getattr(user, "role", None) == "STATE_AUTHORITY" and user.state:
                institutes = institutes.filter(state=user.state)

        institute_ids = institutes.values_list("id", flat=True)
        projects = Project.objects.filter(institute_id__in=institute_ids)
        assignments = InspectionAssignment.objects.filter(institute_id__in=institute_ids)

        return Response({
            "total_institutes": institutes.count(),
            "active_institutes": institutes.filter(is_active=True).count(),
            "total_projects": projects.count(),
            "active_projects": projects.filter(is_active=True).count(),
            "pending_inspections": assignments.filter(status=InspectionAssignment.Status.PENDING).count(),
            "overdue_inspections": assignments.filter(status=InspectionAssignment.Status.OVERDUE).count(),
            "submitted_inspections": assignments.filter(status=InspectionAssignment.Status.SUBMITTED).count(),
        })
