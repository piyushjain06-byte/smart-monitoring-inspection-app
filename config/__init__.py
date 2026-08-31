# Celery is disabled for local/no-Docker dev (it needs Redis).
# Re-enable this import once we reach Phase 4.7 (random assignment scheduling):
#
# from .celery import app as celery_app
# __all__ = ("celery_app",)
