from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InspectionAssignmentViewSet,
    InspectionTemplateViewSet,
    InspectionReportViewSet,
    submit_page,
)

router = DefaultRouter()
router.register(r"templates", InspectionTemplateViewSet, basename="inspection-template")
router.register(r"assignments", InspectionAssignmentViewSet, basename="inspection-assignment")
router.register(r"reports", InspectionReportViewSet, basename="inspection-report")

urlpatterns = [
    path("", include(router.urls)),
    path("submit/", submit_page),
]
