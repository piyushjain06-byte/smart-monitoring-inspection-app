from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.registry.models import Institute


# ---------------------------------------------------------------------------
# 1. Checklist builder — lets DoSJE HQ edit what an inspection asks about
#    without touching code (Part 4.6).
# ---------------------------------------------------------------------------

class InspectionTemplate(models.Model):
    """A named checklist, e.g. 'Monthly Skill Centre Inspection'."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class InspectionField(models.Model):
    """One question/checklist item belonging to a template."""

    class FieldType(models.TextChoices):
        TEXT = "TEXT", "Short text"
        TEXTAREA = "TEXTAREA", "Long text"
        YES_NO = "YES_NO", "Yes / No"
        RATING = "RATING", "Rating (1-5)"
        NUMBER = "NUMBER", "Number"

    template = models.ForeignKey(InspectionTemplate, on_delete=models.CASCADE, related_name="fields")
    label = models.CharField(max_length=255, help_text="The question shown to the inspector")
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.YES_NO)
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Controls display order on the form")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.label} ({self.template.name})"


# ---------------------------------------------------------------------------
# 2. Assignment — who is inspecting which institute, and why (audit trail
#    for the random-assignment engine we build in Phase 3).
# ---------------------------------------------------------------------------

class InspectionAssignment(models.Model):
    """
    One inspection duty given to one officer for one institute.
    For now these get created manually from /admin/; Phase 3 adds the
    weighted-random engine that creates these automatically.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUBMITTED = "SUBMITTED", "Submitted"
        OVERDUE = "OVERDUE", "Overdue"

    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inspection_assignments",
    )
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="inspection_assignments")
    template = models.ForeignKey(InspectionTemplate, on_delete=models.PROTECT, related_name="assignments")

    assigned_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Audit fields — populated by the Phase 3 random-assignment engine.
    # Left blank for manually-created assignments.
    random_seed = models.CharField(max_length=100, blank=True)
    weight_snapshot = models.JSONField(null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.institute.name} -> {self.officer} (due {self.due_date})"


# ---------------------------------------------------------------------------
# 3. Report + Evidence — what the officer actually submits (Part 4.6 + 4.8).
# ---------------------------------------------------------------------------

class InspectionReport(models.Model):
    """The filled-out checklist + geo-tag, submitted against one assignment."""
    assignment = models.OneToOneField(InspectionAssignment, on_delete=models.CASCADE, related_name="report")
    submitted_at = models.DateTimeField(auto_now_add=True)

    # Where the report was actually submitted from — checked against the
    # institute's registered lat/lng via apps.core.geo.is_within_radius().
    submitted_latitude = models.FloatField(null=True, blank=True)
    submitted_longitude = models.FloatField(null=True, blank=True)
    distance_from_site_meters = models.FloatField(null=True, blank=True)
    is_geofence_verified = models.BooleanField(
        default=False, help_text="True when the submitted location is within the allowed site radius",
    )
    location_verified = models.BooleanField(
        default=False, help_text="True if submitted location was within the allowed radius of the institute",
    )

    # Answers stored as {field_id: answer} — flexible since templates can change.
    answers = models.JSONField(default=dict, blank=True)

    overall_score = models.PositiveIntegerField(null=True, blank=True, help_text="0-100, computed from answers")
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"Report for {self.assignment}"


class Evidence(models.Model):
    """A photo/video/document attached to a submitted report."""

    class MediaType(models.TextChoices):
        PHOTO = "PHOTO", "Photo"
        VIDEO = "VIDEO", "Video"
        DOCUMENT = "DOCUMENT", "Document"

    report = models.ForeignKey(InspectionReport, on_delete=models.CASCADE, related_name="evidence_items")
    media_type = models.CharField(max_length=20, choices=MediaType.choices, default=MediaType.PHOTO)
    file = models.FileField(upload_to="evidence/%Y/%m/%d/")
    captured_at = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_media_type_display()} for {self.report}"
