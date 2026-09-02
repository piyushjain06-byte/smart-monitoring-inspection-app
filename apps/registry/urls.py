from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .portal_views import (
    PortalBeneficiaryViewSet,
    PortalDashboardSummaryView,
    PortalInstituteViewSet,
    PortalProjectViewSet,
    PortalStaffViewSet,
)
from .views import (
    BeneficiaryViewSet,
    DashboardSummaryView,
    InstituteViewSet,
    NGOViewSet,
    ProjectViewSet,
    SchemeViewSet,
    StaffViewSet,
)

router = DefaultRouter()
router.register("schemes", SchemeViewSet)
router.register("ngos", NGOViewSet)
router.register("institutes", InstituteViewSet)
router.register("projects", ProjectViewSet)
router.register("staff", StaffViewSet)
router.register("beneficiaries", BeneficiaryViewSet)

# NGO Admin / Project Incharge portal — separate prefix so it's obvious at
# a glance which endpoints are official-only vs. portal-scoped. See
# apps/registry/portal_views.py for the scoping logic.
portal_router = DefaultRouter()
portal_router.register("institutes", PortalInstituteViewSet, basename="portal-institute")
portal_router.register("projects", PortalProjectViewSet, basename="portal-project")
portal_router.register("staff", PortalStaffViewSet, basename="portal-staff")
portal_router.register("beneficiaries", PortalBeneficiaryViewSet, basename="portal-beneficiary")

urlpatterns = [
    path("dashboard-summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("portal/dashboard-summary/", PortalDashboardSummaryView.as_view(), name="portal-dashboard-summary"),
    path("portal/", include(portal_router.urls)),
] + router.urls
