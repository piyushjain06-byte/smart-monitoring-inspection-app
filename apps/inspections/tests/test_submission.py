from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.registry.models import Scheme, NGO, Institute, Project
from apps.inspections.models import InspectionTemplate, InspectionField, InspectionAssignment, InspectionReport, Evidence


User = get_user_model()


class GeoAndSubmissionTests(TestCase):
    def setUp(self):
        # Create user
        self.officer = User.objects.create_user(username='officer', password='pass')

        # Registry objects
        scheme = Scheme.objects.create(name='Test Scheme')
        ngo = NGO.objects.create(name='Test NGO', registration_number='R1')
        self.institute = Institute.objects.create(
            scheme=scheme, ngo=ngo, name='Inst', state='S', district='D', latitude=12.9716, longitude=77.5946
        )

        # Template and fields
        self.template = InspectionTemplate.objects.create(name='Monthly')
        f1 = InspectionField.objects.create(template=self.template, label='Has electricity', field_type=InspectionField.FieldType.YES_NO, is_required=True)
        f2 = InspectionField.objects.create(template=self.template, label='Cleanliness', field_type=InspectionField.FieldType.RATING, is_required=True)

        # Assignment
        self.assignment = InspectionAssignment.objects.create(officer=self.officer, institute=self.institute, template=self.template, due_date='2099-01-01')

        self.client = Client()

    def test_geofence_and_submission(self):
        login = self.client.login(username='officer', password='pass')
        self.assertTrue(login)

        url = reverse('inspection-report-list')  # router registered with basename 'inspection-report'

        answers = {str(f.id): 'yes' for f in InspectionField.objects.filter(template=self.template)}

        # Create a small dummy image
        img = SimpleUploadedFile('photo.jpg', b'\x47\x49\x46\x38\x39\x61', content_type='image/gif')

        data = {
            'assignment': str(self.assignment.id),
            'answers': __import__('json').dumps(answers),
            'submitted_latitude': str(self.institute.latitude),
            'submitted_longitude': str(self.institute.longitude),
            'evidence': img,
        }

        response = self.client.post(url, data)
        self.assertIn(response.status_code, (200, 201))

        # Ensure report created
        reports = InspectionReport.objects.filter(assignment=self.assignment)
        self.assertEqual(reports.count(), 1)
        report = reports.first()
        self.assertTrue(report.location_verified)
        self.assertTrue(report.is_geofence_verified)
        self.assertEqual(report.distance_from_site_meters, 0)
        self.assertIsNotNone(report.overall_score)

        # Evidence saved
        ev = Evidence.objects.filter(report=report)
        self.assertTrue(ev.exists())
        self.assertEqual(ev.first().latitude, self.institute.latitude)

    def test_out_of_fence_submission_is_rejected(self):
        self.client.login(username="officer", password="pass")
        url = reverse("inspection-report-list")
        answers = {str(f.id): "yes" for f in InspectionField.objects.filter(template=self.template)}
        response = self.client.post(url, {
            "assignment": str(self.assignment.id),
            "answers": __import__("json").dumps(answers),
            "submitted_latitude": "13.5",
            "submitted_longitude": str(self.institute.longitude),
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn("within 200 meters", str(response.json()))
        self.assertFalse(InspectionReport.objects.exists())
