from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.analytics.models import AIAlert, RiskSeverity, RiskSnapshot
from apps.cctv.models import Camera
from apps.registry.models import Institute, NGO, Scheme, Staff


User = get_user_model()
DEMO_PASSWORD = "demo1234"
STREAM_URL = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"


class Command(BaseCommand):
    help = "Create or update realistic, interconnected demo data for end-to-end testing."

    @transaction.atomic
    def handle(self, *args, **options):
        admin = self._user(
            username="admin@dosje.gov.in",
            email="admin@dosje.gov.in",
            first_name="Ministry",
            last_name="Administrator",
            role="SUPER_ADMIN",
            is_staff=True,
            is_superuser=True,
        )
        ngo_admin = self._user(
            username="ngo_admin@pratham.org",
            email="ngo_admin@pratham.org",
            first_name="Pratham",
            last_name="Administrator",
            role="NGO_ADMIN",
        )
        incharge = self._user(
            username="incharge@delhi_center.org",
            email="incharge@delhi_center.org",
            first_name="Delhi Center",
            last_name="Incharge",
            role="PROJECT_INCHARGE",
            district="New Delhi",
            state="Delhi",
        )
        inspector_delhi = self._user(
            username="inspector_delhi@gov.in",
            email="inspector_delhi@gov.in",
            first_name="Delhi Field",
            last_name="Inspector",
            role="INSPECTION_OFFICER",
            state="Delhi",
            district="New Delhi",
            base_latitude=28.6139,
            base_longitude=77.2090,
        )
        inspector_far = self._user(
            username="inspector_far@gov.in",
            email="inspector_far@gov.in",
            first_name="Mumbai Field",
            last_name="Inspector",
            role="INSPECTION_OFFICER",
            state="Maharashtra",
            district="Mumbai",
            base_latitude=19.0760,
            base_longitude=72.8777,
        )

        scheme, _ = Scheme.objects.update_or_create(
            name="Pratham Social Welfare Programme",
            defaults={"description": "Demo DoSJE monitoring programme for end-to-end testing."},
        )
        ngo, _ = NGO.objects.update_or_create(
            registration_number="DEMO-PRATHAM-001",
            defaults={
                "scheme": scheme,
                "name": "Pratham Social Welfare Trust",
                "contact_person": "Pratham Programme Office",
                "contact_phone": "+91 11 4000 1234",
                "contact_email": "ngo_admin@pratham.org",
                "admin_user": ngo_admin,
            },
        )

        institute_a, _ = Institute.objects.update_or_create(
            name="Delhi Community Learning Center",
            defaults={
                "scheme": scheme,
                "address": "12 Sansad Marg, New Delhi, Delhi 110001",
                "state": "Delhi",
                "district": "New Delhi",
                "latitude": 28.6200,
                "longitude": 77.2100,
                "incharge": incharge,
                "is_active": True,
            },
        )
        institute_b, _ = Institute.objects.update_or_create(
            name="Saket Skills Institute",
            defaults={
                "scheme": scheme,
                "address": "A-12 Saket, New Delhi, Delhi 110017",
                "state": "Delhi",
                "district": "South Delhi",
                "latitude": 28.5355,
                "longitude": 77.3910,
                "incharge": None,
                "is_active": True,
            },
        )
        Staff.objects.update_or_create(
            linked_user=incharge,
            defaults={
                "institute": institute_a,
                "full_name": "Delhi Center Incharge",
                "designation": "Institute Incharge",
                "phone_number": "+91 98765 43210",
            },
        )

        offline_camera, _ = Camera.objects.update_or_create(
            institute=institute_a,
            name="Delhi Center Main Hall",
            defaults={
                "camera_index": 0,
                "stream_url": "",
                "is_active": True,
                "is_maintenance": False,
                "last_online": timezone.now() - timedelta(hours=72),
            },
        )
        online_camera, _ = Camera.objects.update_or_create(
            institute=institute_b,
            name="Saket Institute Entrance",
            defaults={
                "camera_index": 0,
                "stream_url": STREAM_URL,
                "is_active": True,
                "is_maintenance": False,
                "last_online": timezone.now(),
            },
        )

        snapshot, _ = RiskSnapshot.objects.update_or_create(
            institute=institute_a,
            features__demo_seed=True,
            defaults={
                "score": 85,
                "severity": RiskSeverity.HIGH,
                "factors":[
                    {"factor": "CCTV_OFFLINE", "points": 20, "detail": "All registered CCTV cameras are offline."},
                    {"factor": "CCTV_OFFLINE_OVER_48H", "points": 35, "detail": "The main hall camera has been offline for 72 hours."},
                    {"factor": "INSPECTION_GAP", "points": 10, "detail": "No completed inspection history is available."},
                    {"factor": "ELEVATED_RISK_SIGNAL", "points": 20, "detail": "Demo seed data marks this institute for priority review."},
                ],
                "features": {
                    "demo_seed": True,
                    "camera_count": 1,
                    "camera_online_ratio": 0.0,
                    "cctv_offline_over_48_count": 1,
                    "inspection_gap_days": None,
                },
                "is_anomaly": False,
                "anomaly_score": None,
            },
        )
        alert_defaults = {
            "snapshot": snapshot,
            "risk_score": 85,
            "severity": RiskSeverity.HIGH,
            "status": AIAlert.Status.OPEN,
            "surprise_inspection_recommended": True,
        }
        AIAlert.objects.update_or_create(
            institute=institute_a,
            alert_type=AIAlert.AlertType.CCTV_OFFLINE_OVER_48H,
            defaults={
                **alert_defaults,
                "description": "Delhi Center main hall CCTV has been offline for 72 hours.",
            },
        )
        AIAlert.objects.update_or_create(
            institute=institute_a,
            alert_type=AIAlert.AlertType.HIGH_RISK,
            defaults={
                **alert_defaults,
                "description": "Overall demo risk score is 85/100; priority review recommended.",
            },
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write(f"Institutes: {institute_a.name}, {institute_b.name}")
        self.stdout.write(f"Cameras: {offline_camera.name} ({offline_camera.status}), {online_camera.name} ({online_camera.status})")
        self.stdout.write("")
        self.stdout.write("Demo login credentials")
        self.stdout.write("-" * 78)
        self.stdout.write(f"{'Username':<34} {'Password':<12} Role")
        self.stdout.write("-" * 78)
        for user in (admin, ngo_admin, incharge, inspector_delhi, inspector_far):
            self.stdout.write(f"{user.username:<34} {DEMO_PASSWORD:<12} {user.get_role_display()}")
        self.stdout.write("-" * 78)

    @staticmethod
    def _user(**fields):
        username = fields.pop("username")
        defaults = {**fields, "is_active": True}
        user, _ = User.objects.update_or_create(username=username, defaults=defaults)
        user.set_password(DEMO_PASSWORD)
        user.save(update_fields=["password"])
        return user
