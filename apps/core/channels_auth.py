"""
Phase 4.5 — WebSocket JWT authentication.

A browser WebSocket can't attach an `Authorization: Bearer <token>` header
(same limitation as the CCTV MJPEG <img> stream — see
apps/cctv/views.py::_authenticate_from_query_token), so the frontend
connects with `?token=<jwt access token>` on the socket URL instead, and
this middleware validates it the same way.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def _get_user_from_token(raw_token):
    try:
        validated = JWTAuthentication().get_validated_token(raw_token)
        return JWTAuthentication().get_user(validated)
    except (InvalidToken, TokenError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Standalone JWT auth for the ASGI scope — deliberately NOT stacked on top
    of channels.auth.AuthMiddlewareStack (session-based), since this
    platform's WebSocket clients (the React dashboard) only ever carry a
    JWT, never a Django session cookie.
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        scope["user"] = await _get_user_from_token(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Named to match the channels.auth.AuthMiddlewareStack convention used elsewhere."""
    return JWTAuthMiddleware(inner)
