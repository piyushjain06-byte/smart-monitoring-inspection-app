from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    """
    Part 4.1 — Auth & Role-Based Access Control.
    Every user in the platform is exactly one of these roles.
    """
    SUPER_ADMIN = "SUPER_ADMIN", "DoSJE HQ Super Admin"
    STATE_AUTHORITY = "STATE_AUTHORITY", "State Authority"
    DISTRICT_AUTHORITY = "DISTRICT_AUTHORITY", "District Authority"
    PMU_TEAM = "PMU_TEAM", "PMU Team"
    INSPECTION_OFFICER = "INSPECTION_OFFICER", "Inspection Officer"
    NGO_ADMIN = "NGO_ADMIN", "NGO / Institute Admin"
    PROJECT_INCHARGE = "PROJECT_INCHARGE", "Project Incharge"
    BENEFICIARY = "BENEFICIARY", "Beneficiary"


class User(AbstractUser):
    """
    Custom user model (set as AUTH_USER_MODEL in settings).
    Extends Django's built-in user with the fields this platform needs.
    """
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.BENEFICIARY)
    phone_number = models.CharField(max_length=15, blank=True)
    preferred_language = models.CharField(max_length=10, default="en")  # Part 5.5 — multi-language

    # Scoping fields — a State/District authority is limited to their own state/district.
    # Kept as plain text for now; can be normalized into a State/District model later
    # if you need dropdown lists or geo-boundaries.
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)

    # Base location for field officers (inspectors/PMU) — used by the
    # auto-assignment engine to estimate travel distance to an institute.
    # Plain floats for the same reason as Institute.latitude/longitude
    # (see apps/registry/models.py) — swap to PostGIS PointField later.
    base_latitude = models.FloatField(null=True, blank=True, help_text="Officer's home-base latitude")
    base_longitude = models.FloatField(null=True, blank=True, help_text="Officer's home-base longitude")

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_field_role(self) -> bool:
        """True for roles that actually go on-site (used to gate inspection-related views)."""
        return self.role in {Role.INSPECTION_OFFICER, Role.PMU_TEAM}
