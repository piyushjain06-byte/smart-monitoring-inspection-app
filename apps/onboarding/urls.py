from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import RegisterApplicantView, SchemeApplicationViewSet, SchemeCatalogueView

router = DefaultRouter()
router.register(r"applications", SchemeApplicationViewSet, basename="scheme-application")

urlpatterns = [
    path("register/", RegisterApplicantView.as_view(), name="applicant-register"),
    path("schemes-catalogue/", SchemeCatalogueView.as_view(), name="schemes-catalogue"),
] + router.urls
