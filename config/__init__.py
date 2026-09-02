# Phase 4.7 — Celery is now wired up (needs a Redis broker, see .env.example
# REDIS_URL / CELERY_BROKER_URL). Importing celery_app here is what makes
# `@shared_task` decorated functions across the project findable by the
# worker via `app.autodiscover_tasks()` in config/celery.py.
from .celery import app as celery_app

__all__ = ("celery_app",)
