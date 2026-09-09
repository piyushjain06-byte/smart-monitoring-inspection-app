from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.attendance.models import AttendanceRecord
from apps.cctv.models import Camera
from apps.inspections.models import InspectionAssignment, InspectionReport, InspectionTemplate
from apps.inspections.services import run_auto_assignment
from apps.registry.models import Institute, Scheme, Staff

from .models import AIAlert, RiskSnapshot
from .services.features import collect_features
from .services.risk_engine import run_risk_engine


User = get_user_model()


class ConnectedRiskEngineTests(TestCase):
    def setUp(self):
        scheme = Scheme.objects.create(name="Risk Scheme")
        self.institute = Institute.objects.create(
            scheme=scheme, name="Risk Institute", state="S", district="D",
            latitude=12.9716, longitude=77.5946,
        )
        self.staff = Staff.objects.create(institute=self.institute, full_name="Staff Member")
        self.template = InspectionTemplate.objects.create(name="Risk Checklist")
        self.officer = User.objects.create_user(
            username="officer", role="INSPECTION_OFFICER",
            base_latitude=12.9716, base_longitude=77.5946,
        )

    def test_features_use_attendance_cctv_and_inspection_history(self):
        today = timezone.localdate()
        AttendanceRecord.objects.create(
            staff=self.staff, institute=self.institute, date=today,
            status=AttendanceRecord.Status.ABSENT,
        )
        camera = Camera.objects.create(institute=self.institute, name="Entrance")
        InspectionAssignment.objects.create(
            officer=self.officer, institute=self.institute, template=self.template,
            due_date=today, status=InspectionAssignment.Status.SUBMITTED,
        )
        features = collect_features(self.institute)
        self.assertEqual(features["attendance_rate"], 0)
        self.assertEqual(features["camera_online_ratio"], 0)
        self.assertEqual(features["inspection_frequency"], 1)
        self.assertIsNone(features["latest_inspection_score"])
        self.assertIsNone(features["latest_inspection_at"])
        self.assertEqual(camera.status, "OFFLINE")

    def test_high_risk_creates_explainable_alert_and_recommends_surprise(self):
        Camera.objects.create(institute=self.institute, name="Entrance")
        AttendanceRecord.objects.create(
            staff=self.staff, institute=self.institute, date=timezone.localdate(),
            status=AttendanceRecord.Status.ABSENT,
        )
        assignment = InspectionAssignment.objects.create(
            officer=self.officer, institute=self.institute, template=self.template,
            due_date=timezone.localdate(), status=InspectionAssignment.Status.COMPLETED,
        )
        InspectionReport.objects.create(assignment=assignment, overall_score=0)
        with patch("apps.analytics.services.risk_engine._broadcast_alert_created"):
            result = run_risk_engine([self.institute])[0]
        self.assertEqual(result["severity"], "HIGH")
        alert = AIAlert.objects.get(institute=self.institute, alert_type=AIAlert.AlertType.HIGH_RISK)
        self.assertTrue(alert.surprise_inspection_recommended)
        self.assertIn("attendance", alert.description)
        self.assertIn("CCTV", alert.description)

    def test_high_risk_alert_and_surprise_assignment_are_not_duplicated(self):
        first = AIAlert.objects.create(
            institute=self.institute, alert_type=AIAlert.AlertType.HIGH_RISK,
            description="Existing unresolved risk", risk_score=90, severity="HIGH",
            status=AIAlert.Status.ACKNOWLEDGED,
        )
        AttendanceRecord.objects.create(
            staff=self.staff, institute=self.institute, date=timezone.localdate(),
            status=AttendanceRecord.Status.ABSENT,
        )
        acknowledged_factor = AIAlert.objects.create(
            institute=self.institute, alert_type=AIAlert.AlertType.ATTENDANCE_MISMATCH,
            description="Existing unresolved attendance issue", risk_score=25, severity="MEDIUM",
            status=AIAlert.Status.ACKNOWLEDGED,
        )
        with patch("apps.analytics.services.risk_engine._broadcast_alert_created"):
            run_risk_engine([self.institute])
        self.assertEqual(AIAlert.objects.filter(institute=self.institute, alert_type=AIAlert.AlertType.HIGH_RISK).count(), 1)
        self.assertEqual(AIAlert.objects.filter(institute=self.institute, alert_type=acknowledged_factor.alert_type).count(), 1)
        # A current HIGH snapshot makes the existing batch selector eligible.
        RiskSnapshot.objects.create(institute=self.institute, score=90, severity="HIGH")

        with patch("apps.inspections.services.notify_assignment_created"):
            first_result = run_auto_assignment(radius_km=50)
            second_result = run_auto_assignment(radius_km=50)
        self.assertEqual(first_result["assigned"], 1)
        self.assertEqual(second_result["assigned"], 0)
        self.assertEqual(InspectionAssignment.objects.filter(institute=self.institute).count(), 1)
        self.assertEqual(first.status, AIAlert.Status.ACKNOWLEDGED)

    def test_missing_data_does_not_fabricate_attendance_or_cctv_factors(self):
        result = run_risk_engine([self.institute], create_alerts=False)[0]
        factor_names = {factor["factor"] for factor in result["factors"]}
        self.assertNotIn("ATTENDANCE_MISMATCH", factor_names)
        self.assertNotIn("CCTV_OFFLINE", factor_names)
        self.assertIn("INSPECTION_GAP", factor_names)
