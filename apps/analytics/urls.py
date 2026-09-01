from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AIAlertViewSet, RiskSnapshotViewSet, RunAnalysisView

router = DefaultRouter()
router.register(r"risk", RiskSnapshotViewSet, basename="risk-snapshots")
router.register(r"alerts", AIAlertViewSet, basename="ai-alerts")

urlpatterns = [
    path("run/", RunAnalysisView.as_view(), name="analytics-run"),
] + router.urls
