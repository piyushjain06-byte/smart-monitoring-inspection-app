import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import is_field_officer, is_official, is_ngo_portal_user
from apps.inspections.models import InspectionAssignment
from apps.registry.models import Institute, Project
from apps.registry.portal_views import portal_scoped_institutes

from .models import VCParticipant, VCSession
from .serializers import VCSessionCreateSerializer, VCSessionSerializer

User = get_user_model()


def can_access_institute(user, institute):
    if is_official(user) or is_field_officer(user):
        return True
    return is_ngo_portal_user(user) and portal_scoped_institutes(user).filter(pk=institute.pk).exists()


def participant_role(user):
    if is_official(user):
        return VCParticipant.Role.OFFICIAL
    if is_field_officer(user):
        return VCParticipant.Role.INSPECTOR
    return VCParticipant.Role.INSTITUTE


class VCSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VCSessionSerializer
    permission_classes = [IsAuthenticated]
    queryset = VCSession.objects.select_related(
        "institute", "project", "inspection", "created_by"
    ).prefetch_related("participants__user")

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        institute_id = self.request.query_params.get("institute")
        if institute_id:
            qs = qs.filter(institute_id=institute_id)
        if is_official(user):
            return qs
        if is_field_officer(user):
            return qs.filter(participants__user=user).distinct() | qs.filter(created_by=user).distinct()
        return qs.filter(institute__in=portal_scoped_institutes(user)).distinct()

    def _create_participants(self, session, participant_ids, creator):
        ids = set(participant_ids or []) | {creator.id}
        users = User.objects.filter(id__in=ids, is_active=True)
        if users.count() != len(ids):
            raise ValueError("One or more selected participants are not available.")
        for user in users:
            if not (is_official(user) or is_field_officer(user) or getattr(user, "role", None) in {"NGO_ADMIN", "PROJECT_INCHARGE"}):
                raise ValueError("Selected participants are not authorized for VC sessions.")
            VCParticipant.objects.create(
                session=session,
                user=user,
                role=VCParticipant.Role.INITIATOR if user.id == creator.id else participant_role(user),
                invited_by=creator,
            )

    def create(self, request):
        serializer = VCSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        institute = get_object_or_404(Institute, pk=data["institute"])
        if not can_access_institute(request.user, institute) or not (is_official(request.user) or is_field_officer(request.user)):
            return Response({"detail": "You are not authorized to create a VC for this institute."}, status=status.HTTP_403_FORBIDDEN)
        inspection = None
        if data.get("inspection") is not None:
            inspection = get_object_or_404(InspectionAssignment, pk=data["inspection"], institute=institute)
            if is_field_officer(request.user) and inspection.officer_id != request.user.id:
                return Response({"detail": "Only the assigned inspector can link this inspection."}, status=status.HTTP_403_FORBIDDEN)
        project = None
        if data.get("project") is not None:
            project = get_object_or_404(Project, pk=data["project"], scheme_id=institute.scheme_id)
        room_name = f"sih-dosje-call-{institute.id}-{int(timezone.now().timestamp())}-{uuid.uuid4().hex[:12]}"
        with transaction.atomic():
            session = VCSession.objects.create(
                institute=institute, project=project, inspection=inspection,
                room_name=room_name, created_by=request.user,
                purpose=data.get("purpose", ""), scheduled_at=data.get("scheduled_at"),
            )
            try:
                self._create_participants(session, data.get("participant_ids", []), request.user)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc))
        return Response(VCSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    def _may_control(self, request, session):
        return is_official(request.user) or session.created_by_id == request.user.id

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        session = self.get_object()
        if not self._may_control(request, session):
            return Response({"detail": "Only the initiator or an official can start this VC."}, status=status.HTTP_403_FORBIDDEN)
        try:
            session.start()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(VCSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        session = self.get_object()
        if not self._may_control(request, session):
            return Response({"detail": "Only the initiator or an official can end this VC."}, status=status.HTTP_403_FORBIDDEN)
        try:
            session.end()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        for participant in session.participants.filter(joined_at__isnull=False, left_at__isnull=True):
            participant.leave()
        return Response(VCSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        session = self.get_object()
        participant = get_object_or_404(session.participants, user=request.user)
        try:
            participant.join()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"session": VCSessionSerializer(session).data, "room_name": session.room_name})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        session = self.get_object()
        participant = get_object_or_404(session.participants, user=request.user)
        participant.leave()
        return Response(VCSessionSerializer(session).data)
