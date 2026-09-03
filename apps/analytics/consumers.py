"""
Phase 4.5 — real-time push for the "AI ALERTS" panel (Part 10/25/34).

Kept intentionally simple, same spirit as apps/cctv (no over-engineering
for a local/demo platform): every connected official joins ONE broadcast
group ("ai_alerts") and receives every newly-created AIAlert, rather than
implementing per-state/district group scoping. The REST endpoint
(GET /api/analytics/alerts/) still does the real state/district scoping —
this socket only tells the frontend "something changed, go refetch" plus
ships the alert payload so the panel can show it immediately without
waiting on the next poll.
"""
import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q

from apps.core.permissions import is_official

ALERTS_GROUP = "ai_alerts"


class AIAlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        query = parse_qs(self.scope.get("query_string", b"").decode())
        self.institute_id = query.get("institute", [None])[0]
        if self.institute_id and not await self._can_join_institute(self.institute_id, user.id):
            await self.close(code=4403)
            return
        if is_official(user):
            await self.channel_layer.group_add(ALERTS_GROUP, self.channel_name)
        institute_ids = [self.institute_id] if self.institute_id else await self._authorized_institute_ids(user.id)
        self.institute_groups = [f"institute_{institute_id}" for institute_id in institute_ids]
        for institute_group in self.institute_groups:
            await self.channel_layer.group_add(institute_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if is_official(self.scope.get("user")):
            await self.channel_layer.group_discard(ALERTS_GROUP, self.channel_name)
        for institute_group in getattr(self, "institute_groups", []):
            await self.channel_layer.group_discard(institute_group, self.channel_name)

    @database_sync_to_async
    def _can_join_institute(self, institute_id, user_id):
        from apps.registry.models import Institute, Staff

        institute = Institute.objects.filter(id=institute_id).first()
        if institute is None:
            return False
        user = self.scope["user"]
        return (
            is_official(user)
            or institute.incharge_id == user_id
            or institute.ngo.admin_user_id == user_id
            or Staff.objects.filter(institute_id=institute_id, linked_user_id=user_id).exists()
        )

    @database_sync_to_async
    def _authorized_institute_ids(self, user_id):
        from apps.registry.models import Institute, Staff

        return list(Institute.objects.filter(
            Q(incharge_id=user_id)
            | Q(ngo__admin_user_id=user_id)
            | Q(id__in=Staff.objects.filter(linked_user_id=user_id).values("institute_id")),
            is_active=True,
        ).values_list("id", flat=True))

    # Called by risk_engine.py via group_send({"type": "alert.created", ...})
    async def alert_created(self, event):
        await self.send(text_data=json.dumps({
            "type": "alert.created",
            "alert": event["alert"],
        }))

    # Sent once per full engine run (POST /api/analytics/run/ or the
    # scheduled Celery task) so the dashboard can refresh stat cards/map
    # even on runs that triggered zero new alerts.
    async def analysis_completed(self, event):
        await self.send(text_data=json.dumps({
            "type": "analysis.completed",
            "summary": event["summary"],
        }))

    async def assignment_created(self, event):
        await self.send(text_data=json.dumps({
            "type": "assignment.created",
            "assignment_id": event["assignment_id"],
            "officer_id": event["officer_id"],
            "institute_id": event["institute_id"],
            "scheduled_at": event["scheduled_at"],
        }))

    async def surprise_vc_alert(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
