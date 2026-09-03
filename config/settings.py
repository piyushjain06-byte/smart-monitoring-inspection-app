"""
Django settings for the DoSJE Smart Monitoring Platform.

LOCAL DEV MODE: pure Python + SQLite, no Docker/Postgres required.
Redis IS now required for two features (Phase 4.5 / 4.7 — see README):
  - Django Channels (real-time WebSocket push of new AI alerts)
  - Celery + celery beat (scheduled/automatic risk-engine runs)
Both are wired up below behind REDIS_URL. If you don't want to run Redis
yet, see the "Running without Redis" note in PHASE4_COMPLETION.md — the
app still works, you just lose live push + the scheduled job (same as
before this phase: poll-on-load + manual "Run AI Analysis" button).
"""

from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-secret-key-change-me")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "django.contrib.gis",  # Re-enable when we switch to Postgres+PostGIS
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "simple_history",
    "rest_framework.authtoken",
    "storages",
    "channels",  # Phase 4.5 — real-time dashboard (needs Redis, see CHANNEL_LAYERS below)
    # "rest_framework_gis",     # Re-enable with PostGIS
    # "django_celery_beat",     # optional: DB-backed periodic task admin UI. Not required —
    #                            # CELERY_BEAT_SCHEDULE below runs the scheduler without it.
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.registry",
    "apps.inspections",
    "apps.cctv",
    "apps.attendance",
    "apps.core",
    "apps.analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
# Phase 4.5 — Channels is now active, so the ASGI app is the one that
# actually serves both HTTP and WebSocket traffic when you run:
#   daphne -b 0.0.0.0 -p 8000 config.asgi:application
# `manage.py runserver` still works for plain HTTP during normal dev (it
# will just 404/refuse websocket upgrades) — use daphne (or `manage.py
# runserver` with an ASGI-aware runner) when you want to test the
# real-time alerts feed locally. See PHASE4_COMPLETION.md.
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — SQLite for local dev. Zero setup: it's just a file, no server,
# no install. Swap to the block below once Postgres+PostGIS is available.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Later (Phase: Postgres+PostGIS), replace the block above with:
# DATABASES = {
#     "default": {
#         "ENGINE": "django.contrib.gis.db.backends.postgis",
#         "NAME": env("POSTGRES_DB", default="dosje_db"),
#         "USER": env("POSTGRES_USER", default="dosje_user"),
#         "PASSWORD": env("POSTGRES_PASSWORD", default="dosje_pass"),
#         "HOST": env("POSTGRES_HOST", default="db"),
#         "PORT": env("POSTGRES_PORT", default="5432"),
#     }
# }
# This is intentionally still deferred — it's an infrastructure swap (a
# running Postgres+PostGIS+GDAL stack), not a code change; docker-later/
# already has the compose service ready for when Docker Desktop is sorted.

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# CCTV (Phase 7)
# ---------------------------------------------------------------------------
# Seconds a camera can go without a frame/ping before the dashboard marks it
# OFFLINE. See apps/cctv/models.py Camera.status.
CCTV_OFFLINE_THRESHOLD_SECONDS = env.int("CCTV_OFFLINE_THRESHOLD_SECONDS", default=30)

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # JWT is the primary auth for the React dashboard + inspector UI
        # (Part 7 of the plan). Session/Token kept alive so /admin/ and the
        # old api-token-auth/ endpoint (mobile-browser fallback) still work.
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),   # long-lived: inspectors may be in the field all day
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Optional: AWS S3 storage for production media files. Configure via .env:
# USE_S3=True, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
# ---------------------------------------------------------------------------
USE_S3 = env.bool("USE_S3", default=False)
if USE_S3:
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)

    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    # Optional: media URL override when using S3
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
    else:
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"

# ---------------------------------------------------------------------------
# Channels / Redis (Phase 4.5) — real-time push of new AI alerts to the
# dashboard. See apps/analytics/consumers.py + apps/analytics/routing.py
# and frontend/src/hooks/useAlertsSocket.js.
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

# ---------------------------------------------------------------------------
# Celery / Redis (Phase 4.7) — scheduled risk-engine runs. Without this,
# "Run AI Analysis" stays a manual button/CLI (still works fine either way —
# this just adds an automatic periodic run on top).
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Plain crontab-based periodic schedule — no django_celery_beat DB tables
# needed for this to work, just `celery -A config beat -l info` running
# alongside the worker. Runs the full risk engine (Part 22-25) every 6
# hours automatically instead of waiting for someone to click the button.
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "run-risk-engine-every-6-hours": {
        "task": "apps.analytics.tasks.run_risk_analysis_task",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "auto-assign-surprise-inspections-daily": {
        "task": "apps.inspections.tasks.auto_assign_inspections_task",
        "schedule": crontab(minute=0, hour=6),
    },
}

# ---------------------------------------------------------------------------
# CORS (open for local dev; tighten before deploying)
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG

AUTO_ASSIGN_RADIUS_KM = env.float("AUTO_ASSIGN_RADIUS_KM", default=50)
AUTO_ASSIGN_NOTICE_HOURS = env.float("AUTO_ASSIGN_NOTICE_HOURS", default=3)