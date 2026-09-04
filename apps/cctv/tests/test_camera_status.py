from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.cctv.models import Camera
from apps.registry.models import Institute, Scheme

User = get_user_model()


class CameraStatusTests(TestCase):
    def setUp(self):
        scheme = Scheme.objects.create(name="Test Scheme")
        # FLATTENED ARCHITECTURE: Institute references Scheme only now
        # (no `ngo=` kwarg — Institute.ngo was removed).
        self.institute = Institute.objects.create(
            scheme=scheme, name="Test Institute",
            state="MH", district="Mumbai", latitude=19.0760, longitude=72.8777,
        )

    def test_status_offline_when_never_seen(self):
        camera = Camera.objects.create(institute=self.institute, name="Main Hall")
        self.assertEqual(camera.status, "OFFLINE")

    def test_status_online_when_recently_seen(self):
        camera = Camera.objects.create(institute=self.institute, name="Main Hall")
        camera.mark_seen()
        self.assertEqual(camera.status, "ONLINE")

    def test_status_offline_after_threshold(self):
        camera = Camera.objects.create(
            institute=self.institute, name="Main Hall",
            last_online=timezone.now() - timedelta(minutes=5),
        )
        self.assertEqual(camera.status, "OFFLINE")

    def test_status_disabled_when_inactive_even_if_recently_seen(self):
        camera = Camera.objects.create(
            institute=self.institute, name="Main Hall",
            is_active=False, last_online=timezone.now(),
        )
        self.assertEqual(camera.status, "DISABLED")


class CameraApiPermissionTests(TestCase):
    def setUp(self):
        scheme = Scheme.objects.create(name="Test Scheme")
        self.institute = Institute.objects.create(
            scheme=scheme, name="Test Institute",
            state="MH", district="Mumbai",
        )
        self.camera = Camera.objects.create(institute=self.institute, name="Main Hall")

    def test_field_officer_cannot_list_cameras(self):
        User.objects.create_user(username="officer1", password="pass", role="INSPECTION_OFFICER")
        self.client.login(username="officer1", password="pass")
        response = self.client.get("/api/cctv/cameras/")
        self.assertEqual(response.status_code, 403)

    def test_official_can_list_cameras(self):
        User.objects.create_user(username="admin1", password="pass", role="DISTRICT_AUTHORITY")
        self.client.login(username="admin1", password="pass")
        response = self.client.get("/api/cctv/cameras/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_stream_requires_token(self):
        response = self.client.get(f"/api/cctv/cameras/{self.camera.id}/stream/")
        self.assertEqual(response.status_code, 401)
