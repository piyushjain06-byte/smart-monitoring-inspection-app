from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.inspections.models import InspectionAssignment
from apps.registry.models import Institute, Project


class VCSession(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        LIVE = "LIVE", "Live"
        ENDED = "ENDED", "Ended"
        CANCELLED = "CANCELLED", "Cancelled"

    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="vc_sessions")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="vc_sessions")
    inspection = models.ForeignKey(InspectionAssignment, on_delete=models.SET_NULL, null=True, blank=True, related_name="vc_sessions")
    room_name = models.CharField(max_length=180, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_vc_sessions")
    purpose = models.CharField(max_length=255, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def start(self):
        if self.status not in {self.Status.SCHEDULED}:
            raise ValueError("Only scheduled sessions can be started.")
        self.status = self.Status.LIVE
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def end(self):
        if self.status != self.Status.LIVE:
            raise ValueError("Only live sessions can be ended.")
        self.status = self.Status.ENDED
        self.ended_at = timezone.now()
        self.save(update_fields=["status", "ended_at"])


class VCParticipant(models.Model):
    class Role(models.TextChoices):
        INITIATOR = "INITIATOR", "Initiator"
        OFFICIAL = "OFFICIAL", "Official"
        INSPECTOR = "INSPECTOR", "Inspector"
        INSTITUTE = "INSTITUTE", "Institute representative"
        OTHER = "OTHER", "Participant"

    session = models.ForeignKey(VCSession, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vc_participations")
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.OTHER)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="vc_invitations")
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "user"], name="unique_vc_session_participant")]

    def join(self):
        if self.session.status != VCSession.Status.LIVE:
            raise ValueError("The VC session is not live.")
        self.joined_at = self.joined_at or timezone.now()
        self.left_at = None
        self.save(update_fields=["joined_at", "left_at"])

    def leave(self):
        if self.joined_at and self.left_at is None:
            self.left_at = timezone.now()
            self.save(update_fields=["left_at"])
