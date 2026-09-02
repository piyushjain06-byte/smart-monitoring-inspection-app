"""
Root websocket routing table (Phase 4.5). Mirrors config/urls.py's pattern
of including each app's own urls.py — each app that wants a websocket
channel gets its own routing.py, aggregated here.
"""
from apps.analytics.routing import websocket_urlpatterns as analytics_ws_urlpatterns

websocket_urlpatterns = [
    *analytics_ws_urlpatterns,
]
