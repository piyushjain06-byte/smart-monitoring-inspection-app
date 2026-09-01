"""
Phase 7 — CCTV (Part 26 / Part 28 of the plan).

Kept deliberately simple per the plan's own instruction ("This is where you
should not waste your time"):

    Laptop Webcam -> OpenCV -> Live stream -> Django/streaming layer -> React

`camera_index` drives the local-webcam demo path (OpenCV opens the server
machine's own webcam by device index — 0 is almost always the built-in/only
webcam). `stream_url` is there unused for now, reserved for Phase "Real CCTV
later" (IP camera -> RTSP -> MediaMTX -> WebRTC/HLS -> React) so the model
doesn't need to change shape when that phase happens — only which field a
camera actually uses.

Status (ONLINE/OFFLINE) is deliberately NOT a stored field — Part 28 says
"If camera hasn't responded for a certain period: CCTV OFFLINE", so it's a
computed property off `last_online`, refreshed either by an active stream
connection or a manual "ping" from the dashboard. No Celery/background
heartbeat needed for this phase.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.registry.models import Institute

# How long a camera can go without reporting in before the dashboard shows
# it as OFFLINE. A plain module constant (not a DB field) so it's obvious
# where to tune it, mirroring apps/inspections/services.py's WORKLOAD_* constants.
OFFLINE_THRESHOLD_SECONDS = getattr(settings, "CCTV_OFFLINE_THRESHOLD_SECONDS", 30)


class Camera(models.Model):
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name="cameras")
    name = models.CharField(max_length=255, help_text="e.g. 'Main Hall', 'Entrance'")

    camera_index = models.PositiveSmallIntegerField(
        default=0,
        help_text=(
            "OpenCV device index for the local-webcam demo (0 = the server's "
            "default/only webcam). Ignored once stream_url is set."
        ),
    )
    stream_url = models.CharField(
        max_length=500,
        blank=True,
        help_text=(
            "RTSP/HLS URL for a real IP camera, once MediaMTX is set up. "
            "Leave blank to use camera_index (local webcam demo)."
        ),
    )

    is_active = models.BooleanField(default=True)
    last_online = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["institute_id", "name"]

    def __str__(self):
        return f"{self.name} ({self.institute.name})"

    @property
    def status(self) -> str:
        if not self.is_active:
            return "DISABLED"
        if self.last_online is None:
            return "OFFLINE"
        age_seconds = (timezone.now() - self.last_online).total_seconds()
        return "ONLINE" if age_seconds <= OFFLINE_THRESHOLD_SECONDS else "OFFLINE"

    def mark_seen(self):
        """Called whenever we successfully read a frame (stream or ping)."""
        self.last_online = timezone.now()
        self.save(update_fields=["last_online"])
