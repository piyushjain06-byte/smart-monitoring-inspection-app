"""
Celery app config — NOT ACTIVE in local/no-Docker dev mode.

This file is kept as reference for Phase 4.7 (random inspection assignment
scheduling), which needs a Redis broker to run. To re-enable:
  1. pip install celery redis django-celery-beat
  2. Uncomment the CELERY_* settings block in config/settings.py
  3. Uncomment the import in config/__init__.py
  4. Install and run Redis locally (or via Docker once that's set up)
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("dosje_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
