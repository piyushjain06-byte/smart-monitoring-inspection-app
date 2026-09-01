from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.registry.models import Institute, Staff


class AttendanceRecord(models.Model):
    """Represents a staff attendance mark for a single day."""

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        HALF_DAY = "HALF_DAY", "Half day"

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="attendance_records")
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(default=timezone.now)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("staff", "institute", "date")
        ordering = ["-date", "staff__full_name"]

    def __str__(self):
        return f"{self.staff.full_name} — {self.date} ({self.status})"

    @property
    def is_checked_in(self):
        return self.check_in is not None

    @property
    def is_checked_out(self):
        return self.check_out is not None