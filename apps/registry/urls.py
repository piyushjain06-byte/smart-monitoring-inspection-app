from rest_framework.routers import DefaultRouter

from .views import (
    BeneficiaryViewSet,
    InstituteViewSet,
    NGOViewSet,
    ProjectViewSet,
    SchemeViewSet,
    StaffViewSet,
)

router = DefaultRouter()
router.register("schemes", SchemeViewSet)
router.register("ngos", NGOViewSet)
router.register("institutes", InstituteViewSet)
router.register("projects", ProjectViewSet)
router.register("staff", StaffViewSet)
router.register("beneficiaries", BeneficiaryViewSet)

urlpatterns = router.urls
