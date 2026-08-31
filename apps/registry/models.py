from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from simple_history.models import HistoricalRecords  # Part 5.7 — immutable audit log


class Scheme(models.Model):
    """A DoSJE scheme under which projects/institutes operate."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class NGO(models.Model):
    """An NGO partner running one or more projects/institutes under a scheme."""
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)
    contact_email = models.EmailField(blank=True)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ngos_administered",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class Institute(models.Model):
    """
    A physical location (project site) run by an NGO under a Scheme.
    This is the entity that gets CCTV cameras, random VC calls, and inspections.
    """
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="institutes")
    ngo = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name="institutes")
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)

    # Official registered location — every inspection/evidence geo-tag is validated
    # against this point (see apps/core/geo.py -> is_within_radius). SRID 4326 = WGS84 lat/lon.
    location = gis_models.PointField(srid=4326, geography=True, null=True, blank=True)

    incharge = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="institutes_incharged",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} ({self.district}, {self.state})"


class Project(models.Model):
    """
    A specific activity/program running at an Institute under a Scheme.
    Kept separate from Institute because one institute can run several projects
    (e.g. a skill-training institute running both a tailoring and a computer course).
    """
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    sanctioned_budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} @ {self.institute.name}"


class Staff(models.Model):
    """Institute-level staff (used for attendance analytics — Part 4.9)."""
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="staff_members")
    full_name = models.CharField(max_length=255)
    designation = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    linked_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="staff_profile",
    )

    def __str__(self):
        return f"{self.full_name} — {self.institute.name}"


class Beneficiary(models.Model):
    """A beneficiary registered under a Project (used for headcount/attendance checks)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="beneficiaries")
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, blank=True)
    linked_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="beneficiary_profile",
    )
    enrolled_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} — {self.project.name}"
