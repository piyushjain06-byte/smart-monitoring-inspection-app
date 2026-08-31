from rest_framework.routers import DefaultRouter

from django.urls import path

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

urlpatterns = [
    path("dashboard-summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
] + router.urls
