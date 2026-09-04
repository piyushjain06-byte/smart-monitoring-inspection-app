from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.analytics.models import RiskSnapshot
from apps.core.geo import distance_meters
from apps.inspections.models import InspectionAssignment, InspectionTemplate
from apps.inspections.services import eligible_officers_for_institute, run_auto_assignment
from apps.registry.models import Institute, NGO, Scheme


User = get_user_model()


class AutoAssignmentTests(TestCase):
    def setUp(self):
        scheme = Scheme.objects.create(name="Scheme")
        # FLATTENED ARCHITECTURE: NGO hangs directly off Scheme now (needs
        # `scheme=`), and Institute no longer has an `ngo` field — the
        # anti-collusion check in apps.inspections.services now keys off
        # Institute.scheme instead of the removed Institute.ngo.
        self.ngo = NGO.objects.create(scheme=scheme, name="NGO", registration_number="NGO-1")
        self.other_ngo = NGO.objects.create(scheme=scheme, name="Other NGO", registration_number="NGO-2")
        self.institute = Institute.objects.create(
            scheme=scheme, name="Priority Institute", state="S", district="D",
            latitude=12.9716, longitude=77.5946,
        )
        self.other_institute = Institute.objects.create(
            scheme=scheme, name="Other Institute", state="S", district="D",
            latitude=12.9716, longitude=77.5946,
        )
        self.template = InspectionTemplate.objects.create(name="Surprise checklist")
        self.nearby = User.objects.create_user(
            username="nearby", role="INSPECTION_OFFICER", base_latitude=12.9716, base_longitude=77.5946,
        )
        self.far = User.objects.create_user(
            username="far", role="INSPECTION_OFFICER", base_latitude=13.5, base_longitude=77.5946,
        )
        self.conflicted = User.objects.create_user(
            username="conflicted", role="INSPECTION_OFFICER", base_latitude=12.9716, base_longitude=77.5946,
        )
        old_assignment = InspectionAssignment.objects.create(
            officer=self.conflicted, institute=self.other_institute, template=self.template,
            due_date="2025-01-01",
        )
        InspectionAssignment.objects.filter(pk=old_assignment.pk).update(
            assigned_at=timezone.now() - timedelta(days=30),
        )

    def test_proximity_and_anti_collusion_filter(self):
        candidates = eligible_officers_for_institute(self.institute, radius_km=50)
        self.assertEqual([officer.username for officer, _ in candidates], ["nearby"])
        self.assertLess(distance_meters(12.9716, 77.5946, 13.5, 77.5946) / 1000, 100)

    @patch("apps.inspections.services.notify_assignment_created")
    def test_batch_assigns_high_risk_institute_with_short_notice(self, notify):
        RiskSnapshot.objects.create(institute=self.institute, score=80, severity="HIGH")

        result = run_auto_assignment(radius_km=50, due_in_hours=3)

        self.assertEqual(result["assigned"], 1)
        assignment = InspectionAssignment.objects.get(institute=self.institute)
        self.assertEqual(assignment.officer, self.nearby)
        self.assertEqual(assignment.status, InspectionAssignment.Status.PENDING)
        self.assertIsNotNone(assignment.scheduled_at)
        self.assertAlmostEqual((assignment.scheduled_at - timezone.now()).total_seconds() / 3600, 3, delta=0.1)
        notify.assert_called_once_with(assignment)

    def test_pending_institute_is_not_reassigned(self):
        RiskSnapshot.objects.create(institute=self.institute, score=90, severity="HIGH")
        InspectionAssignment.objects.create(
            officer=self.nearby, institute=self.institute, template=self.template,
            due_date=timezone.localdate(),
        )

        result = run_auto_assignment()

        self.assertEqual(result["evaluated"], 0)
        self.assertEqual(result["assigned"], 0)
