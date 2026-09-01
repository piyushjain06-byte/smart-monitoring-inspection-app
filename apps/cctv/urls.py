from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CameraViewSet, stream_view

router = DefaultRouter()
router.register("cameras", CameraViewSet)

urlpatterns = [
    # Not a DRF action — StreamingHttpResponse doesn't go through DRF's
    # renderer machinery, and this needs to be a plain URL usable as an
    # <img src="...">, so it's registered separately from the router.
    path("cameras/<int:pk>/stream/", stream_view, name="camera-stream"),
] + router.urls
