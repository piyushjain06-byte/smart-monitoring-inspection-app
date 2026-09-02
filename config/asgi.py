import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# get_asgi_application() must run BEFORE importing anything that touches
# models/apps (channels routing imports consumers, which import models),
# otherwise Django raises AppRegistryNotReady.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from apps.core.channels_auth import JWTAuthMiddlewareStack  # noqa: E402
from config.routing import websocket_urlpatterns  # noqa: E402

# Phase 4.5 — Channels is now active. HTTP requests still go through plain
# Django (django_asgi_app); WebSocket connections (the real-time AI alerts
# feed) go through JWTAuthMiddlewareStack so `?token=<jwt access token>`
# on the socket URL authenticates the user the same way the CCTV MJPEG
# stream endpoint already does (see apps/cctv/views.py).
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})