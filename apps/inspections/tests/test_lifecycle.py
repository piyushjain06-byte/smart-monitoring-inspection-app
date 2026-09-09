from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.registry.models import Scheme, Institute
from apps.inspections.models import InspectionAssignment, InspectionTemplate


User = get_user_model()


class InspectionLifecycleTests(TestCase):
    def setUp(self):
        self.officer = User.objects.create_user(username="officer", password="pass", role="INSPECTION_OFFICER")
        self.reviewer = User.objects.create_user(username="reviewer", password="pass", role="SUPER_ADMIN")
        scheme = Scheme.objects.create(name="Test Scheme")
        institute = Institute.objects.create(scheme=scheme, name="Inst", state="S", district="D")
        template = InspectionTemplate.objects.create(name="Monthly")
        self.assignment = InspectionAssignment.objects.create(
            officer=self.officer, institute=institute, template=template, due_date="2099-01-01"
        )
        self.url = reverse("inspection-assignment-detail", args=[self.assignment.id])

    def post_action(self, action, user, data=None):
        self.client.force_login(user)
        return self.client.post(f"{self.url}{action}/", data or {})

    def test_inspector_can_accept_and_start_but_cannot_review(self):
        self.assertEqual(self.post_action("accept", self.officer).status_code, 200)
        self.assertEqual(self.post_action("start", self.officer).status_code, 200)
        self.assertEqual(self.post_action("review", self.officer).status_code, 403)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, InspectionAssignment.Status.IN_PROGRESS)

    def test_changes_require_comment_and_can_return_to_progress(self):
        self.assignment.status = InspectionAssignment.Status.SUBMITTED
        self.assignment.save()
        self.assertEqual(self.post_action("review", self.reviewer).status_code, 200)
        self.assertEqual(self.post_action("request_changes", self.reviewer).status_code, 400)
        response = self.post_action("request_changes", self.reviewer, {"comment": "Add the missing site photo."})
        self.assertEqual(response.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, InspectionAssignment.Status.CHANGES_REQUIRED)
        self.assertEqual(self.assignment.review_comment, "Add the missing site photo.")
        self.assertEqual(self.post_action("resubmit", self.officer).status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, InspectionAssignment.Status.IN_PROGRESS)

    def test_invalid_transition_is_rejected(self):
        response = self.post_action("approve", self.reviewer)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Cannot transition", response.json()["detail"])

    def test_review_approve_complete_path(self):
        self.assignment.status = InspectionAssignment.Status.SUBMITTED
        self.assignment.save()
        self.assertEqual(self.post_action("review", self.reviewer).status_code, 200)
        self.assertEqual(self.post_action("approve", self.reviewer).status_code, 200)
        self.assertEqual(self.post_action("complete", self.reviewer).status_code, 200)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, InspectionAssignment.Status.COMPLETED)
        self.assertEqual(self.assignment.reviewer_id, self.reviewer.id)
