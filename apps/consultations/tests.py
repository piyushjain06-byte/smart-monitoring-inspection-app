from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.registry.models import Institute, Scheme

from .models import VCParticipant, VCSession


User = get_user_model()


class VCSessionTests(TestCase):
    def setUp(self):
        scheme = Scheme.objects.create(name="VC Scheme")
        self.institute = Institute.objects.create(name="VC Institute", scheme=scheme, state="S", district="D")
        self.official = User.objects.create_user(username="official", password="pass", role="SUPER_ADMIN")
        self.inspector = User.objects.create_user(username="inspector", password="pass", role="INSPECTION_OFFICER")
        self.outsider = User.objects.create_user(username="outsider", password="pass", role="BENEFICIARY")
        self.url = "/api/consultations/sessions/"

    def create_session(self):
        self.client.force_login(self.official)
        response = self.client.post(self.url, {
            "institute": self.institute.id,
            "purpose": "Inspection review",
            "participant_ids": [self.inspector.id],
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_creation_and_participant_authorization(self):
        data = self.create_session()
        session = VCSession.objects.get(pk=data["id"])
        self.assertEqual(session.institute, self.institute)
        self.assertEqual(session.participants.count(), 2)
        self.assertEqual(session.status, VCSession.Status.SCHEDULED)
        self.client.force_login(self.outsider)
        response = self.client.post(f"{self.url}{session.id}/join/")
        self.assertEqual(response.status_code, 404)

    def test_start_join_leave_and_end_are_audited(self):
        data = self.create_session()
        session = VCSession.objects.get(pk=data["id"])
        self.client.force_login(self.official)
        self.assertEqual(self.client.post(f"{self.url}{session.id}/start/").status_code, 200)
        self.client.force_login(self.inspector)
        join = self.client.post(f"{self.url}{session.id}/join/")
        self.assertEqual(join.status_code, 200)
        participant = VCParticipant.objects.get(session=session, user=self.inspector)
        self.assertIsNotNone(participant.joined_at)
        self.assertEqual(self.client.post(f"{self.url}{session.id}/leave/").status_code, 200)
        participant.refresh_from_db()
        self.assertIsNotNone(participant.left_at)
        self.client.force_login(self.official)
        self.assertEqual(self.client.post(f"{self.url}{session.id}/end/").status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, VCSession.Status.ENDED)
        self.assertIsNotNone(session.started_at)
        self.assertIsNotNone(session.ended_at)
        self.assertTrue(session.history.exists())
        self.assertTrue(participant.history.exists())

    def test_only_authorized_user_can_create_and_history_is_scoped(self):
        self.client.force_login(self.outsider)
        response = self.client.post(self.url, {"institute": self.institute.id}, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        data = self.create_session()
        self.client.force_login(self.outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.assertEqual(self.client.get(f"{self.url}{data['id']}/").status_code, 404)

    def test_legacy_initiate_vc_creates_live_session_and_keeps_jitsi_contract(self):
        self.client.force_login(self.official)
        response = self.client.post(f"/api/registry/institutes/{self.institute.id}/initiate-vc/", {
            "purpose": "Surprise inspection consultation",
            "participant_ids": [self.inspector.id],
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("room_name", payload)
        session = VCSession.objects.get(pk=payload["session_id"])
        self.assertEqual(session.status, VCSession.Status.LIVE)
        self.assertEqual(session.participants.count(), 2)
        self.assertEqual(session.participants.get(user=self.inspector).role, VCParticipant.Role.INSPECTOR)
