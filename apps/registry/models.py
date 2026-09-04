"""
FLATTENED ARCHITECTURE (post-audit fix)
----------------------------------------
Old (wrong) hierarchy:  Scheme -> NGO -> Institute -> Project
New (correct) hierarchy: Scheme -> { NGO, Institute, Project } independently

NGO, Institute, and Project each carry their own FK straight to Scheme.
Institute.ngo and Project.institute have been removed entirely — there is
no nesting between them anymore. Staff (-> Institute) and Beneficiary
(-> Project) are unaffected: those are simple "works at" / "enrolled in"
relations, not part of the Scheme/NGO/Institute/Project hierarchy that was
wrong, so they're left exactly as they were.
"""
from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords  # Part 5.7 — immutable audit log


class Scheme(models.Model):
    """A DoSJE scheme. The single top-level parent — NGO, Institute, and
    Project each reference this directly and independently."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class NGO(models.Model):
    """An NGO partner operating under a Scheme. Does NOT own Institutes —
    see the module docstring for why that link was removed."""
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="ngos")
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
    A physical location (project site) operating under a Scheme.

    FLATTENED ARCHITECTURE: Institute references Scheme directly and no
    longer references NGO. `incharge` (Project Incharge login) stays as-is.

    LOCAL DEV MODE: location is plain latitude/longitude floats (no PostGIS
    needed). Geofence checks use apps.core.geo.is_within_radius().
    """
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="institutes")
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)

    latitude = models.FloatField(null=True, blank=True, help_text="e.g. 19.0760")
    longitude = models.FloatField(null=True, blank=True, help_text="e.g. 72.8777")

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
    A specific activity/program running under a Scheme.

    FLATTENED ARCHITECTURE: Project references Scheme directly and no
    longer references Institute. A Project is no longer "at" one
    Institute — it's a Scheme-level activity (mirrors NGO and Institute).
    """
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    sanctioned_budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} ({self.scheme.name})"


class Staff(models.Model):
    """Institute-level staff (used for attendance analytics — Part 4.9).
    Unaffected by the flatten — Staff always just "works at" an Institute."""
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
    """A beneficiary registered under a Project. Unaffected by the flatten —
    Beneficiary always just "enrolls in" a Project."""
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
