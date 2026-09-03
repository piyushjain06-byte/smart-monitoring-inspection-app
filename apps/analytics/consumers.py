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

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.core.permissions import is_official

ALERTS_GROUP = "ai_alerts"


class AIAlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated or not is_official(user):
            await self.close(code=4401)
            return

        await self.channel_layer.group_add(ALERTS_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(ALERTS_GROUP, self.channel_name)

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
