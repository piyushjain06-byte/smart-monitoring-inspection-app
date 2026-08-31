import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Plain Django ASGI app for now — no Channels/WebSockets yet (that's Phase 4.5,
# and needs Redis running). This file will grow a websocket router at that point.
application = get_asgi_application()
