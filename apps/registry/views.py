from rest_framework import viewsets

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


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.select_related("institute").all()
    serializer_class = StaffSerializer


class BeneficiaryViewSet(viewsets.ModelViewSet):
    queryset = Beneficiary.objects.select_related("project").all()
    serializer_class = BeneficiarySerializer
