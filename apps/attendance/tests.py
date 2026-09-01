from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.registry.models import Institute, NGO, Scheme, Staff
from .models import AttendanceRecord

User = get_user_model()


class AttendanceRecordModelTests(TestCase):
    def setUp(self):
        scheme = Scheme.objects.create(name="Test Scheme")
        ngo = NGO.objects.create(name="Test NGO", registration_number="R1")
        self.institute = Institute.objects.create(
            scheme=scheme,
            ngo=ngo,
            name="Test Institute",
            state="MH",
            district="Mumbai",
            latitude=19.0760,
            longitude=72.8777,
        )
        self.staff = Staff.objects.create(
            institute=self.institute,
            full_name="Rahul Patel",
            designation="Trainer",
        )

    def test_create_attendance_record(self):
        record = AttendanceRecord.objects.create(
            staff=self.staff,
            institute=self.institute,
            date=date.today(),
            status=AttendanceRecord.Status.PRESENT,
        )
        self.assertEqual(record.status, AttendanceRecord.Status.PRESENT)
        self.assertTrue(record.is_checked_in is False)

    def test_unique_record_per_staff_day(self):
        AttendanceRecord.objects.create(
            staff=self.staff,
            institute=self.institute,
            date=date.today(),
        )
        self.assertEqual(
            AttendanceRecord.objects.filter(staff=self.staff, date=date.today()).count(),
            1,
        )
