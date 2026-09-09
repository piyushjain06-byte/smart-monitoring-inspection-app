from rest_framework.routers import DefaultRouter

from .views import VCSessionViewSet

router = DefaultRouter()
router.register("sessions", VCSessionViewSet, basename="vc-session")

urlpatterns = router.urls
