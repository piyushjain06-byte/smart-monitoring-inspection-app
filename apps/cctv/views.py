"""
Phase 7 — CCTV views.

Two very different kinds of endpoint live here:

1. `CameraViewSet` — an ordinary DRF ModelViewSet (CRUD + a "ping" action),
   JWT-authenticated the normal way via the Authorization header, same as
   every other app.

2. `stream_view` — a raw Django view (not DRF) that opens the server's
   webcam with OpenCV and pushes an MJPEG multipart stream. This can't go
   through DRF's normal renderer machinery, and a browser <img> tag can't
   attach an Authorization header, so it authenticates via a `?token=`
   query param instead — a standard pattern for media/streaming endpoints
   that must be usable directly as an <img>/<video> src.
"""
import logging

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from apps.core.permissions import IsOfficial, is_official

from .models import Camera
from .serializers import CameraSerializer

logger = logging.getLogger(__name__)

# How many frames to serve between last_online refreshes, so a long-running
# stream doesn't write to the DB on every single frame (~30x/sec).
HEARTBEAT_EVERY_N_FRAMES = 60

# JPEG quality for the MJPEG stream. Kept modest — this is a demo feed over
# a local dev server, not a broadcast pipeline.
JPEG_QUALITY = 70


class CameraViewSet(viewsets.ModelViewSet):
    queryset = Camera.objects.select_related("institute").all()
    serializer_class = CameraSerializer
    permission_classes = [IsOfficial]

    def get_queryset(self):
        """Supports ?institute=<id> so the institute detail page can list just its cameras."""
        qs = super().get_queryset()
        institute_id = self.request.query_params.get("institute")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)
        return qs

    @action(detail=True, methods=["post"], url_path="ping")
    def ping(self, request, pk=None):
        """
        POST /api/cctv/cameras/<id>/ping/
        Manual "Refresh status" button on the dashboard — tries to open the
        camera and read a single frame without starting a full stream.
        """
        camera = self.get_object()
        ok = _check_camera_available(camera)
        if ok:
            camera.mark_seen()
        return Response({"status": camera.status})


def _open_capture(camera: Camera):
    """
    Returns an opened cv2.VideoCapture, or None if OpenCV/the device isn't
    available. Isolated in its own function so a missing webcam (very
    common — most demo/CI machines don't have one) degrades to "OFFLINE"
    instead of crashing the whole app.
    """
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python-headless not installed — CCTV streaming disabled.")
        return None

    source = camera.stream_url or camera.camera_index
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        cap.release()
        return None
    return cap


def _check_camera_available(camera: Camera) -> bool:
    cap = _open_capture(camera)
    if cap is None:
        return False
    try:
        ok, _frame = cap.read()
        return bool(ok)
    finally:
        cap.release()


def _authenticate_from_query_token(request):
    """Validates ?token=<JWT access token> and returns the user, or None."""
    raw_token = request.GET.get("token")
    if not raw_token:
        return None
    try:
        validated = JWTAuthentication().get_validated_token(raw_token)
        return JWTAuthentication().get_user(validated)
    except (InvalidToken, TokenError):
        return None


def _mjpeg_frames(camera: Camera, cap):
    """
    Generator yielding one multipart/x-mixed-replace chunk per frame.
    Takes an already-opened cv2.VideoCapture (see stream_view) rather than
    opening its own — most webcams can't be opened by two callers at once,
    so we open exactly one capture per request and reuse it here.
    """
    import cv2

    frame_count = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if not ok:
                break

            frame_count += 1
            if frame_count % HEARTBEAT_EVERY_N_FRAMES == 1:
                camera.mark_seen()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
    finally:
        cap.release()


def stream_view(request, pk):
    """
    GET /api/cctv/cameras/<id>/stream/?token=<jwt access token>
    Renders directly as an <img src="..."> — the browser treats the
    multipart response as a continuously-updating JPEG.
    """
    user = _authenticate_from_query_token(request)
    if user is None or not is_official(user):
        return HttpResponse(status=401)

    camera = get_object_or_404(Camera, pk=pk, is_active=True)

    cap = _open_capture(camera)
    if cap is None:
        return HttpResponse("Camera unavailable — no webcam detected on the server.", status=503)

    return StreamingHttpResponse(
        _mjpeg_frames(camera, cap),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )
