from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.permissions import IsSuperAdmin, is_super_admin
from apps.registry.models import Scheme
from apps.registry.serializers import SchemeSerializer

from .models import SchemeApplication
from .serializers import (
    ApplicantRegisterSerializer,
    SchemeApplicationCreateSerializer,
    SchemeApplicationReviewSerializer,
    SchemeApplicationSerializer,
)
from .services import approve_application, reject_application


class RegisterApplicantView(APIView):
    """
    POST /api/onboarding/register/
    Public self-registration for an NGO/Institute admin — creates a bare
    login account. No NGO/Institute exists yet; that only happens once a
    scheme application this account submits is approved.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ApplicantRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
        }, status=status.HTTP_201_CREATED)


class SchemeCatalogueView(APIView):
    """
    GET /api/onboarding/schemes-catalogue/
    Any authenticated user can browse the scheme catalogue to apply against
    — unlike apps.registry.views.SchemeViewSet, which is officials-only CRUD.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        schemes = Scheme.objects.all().order_by("name")
        return Response(SchemeSerializer(schemes, many=True).data)


class SchemeApplicationViewSet(viewsets.ModelViewSet):
    """
    Applicants see and create only their own applications. The Super Admin
    (is_superuser or role=SUPER_ADMIN — "government" per the plan's own
    diagram) sees every application and is the only one who can approve or
    reject one.
    """
    queryset = SchemeApplication.objects.select_related("scheme", "applicant", "reviewed_by").all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return SchemeApplicationCreateSerializer
        return SchemeApplicationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if is_super_admin(self.request.user):
            return qs
        return qs.filter(applicant=self.request.user)

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

    def get_permissions(self):
        if self.action in ("approve", "reject"):
            return [IsSuperAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        application = self.get_object()
        if application.status != SchemeApplication.Status.PENDING:
            return Response(
                {"detail": "This application has already been reviewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SchemeApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        approve_application(
            application,
            reviewer=request.user,
            approved_fund_amount=serializer.validated_data.get("approved_fund_amount"),
            review_notes=serializer.validated_data.get("review_notes", ""),
        )
        return Response(SchemeApplicationSerializer(application).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        application = self.get_object()
        if application.status != SchemeApplication.Status.PENDING:
            return Response(
                {"detail": "This application has already been reviewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SchemeApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reject_application(
            application,
            reviewer=request.user,
            review_notes=serializer.validated_data.get("review_notes", ""),
        )
        return Response(SchemeApplicationSerializer(application).data)
