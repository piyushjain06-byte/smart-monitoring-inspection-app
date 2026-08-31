"""
Django settings for the DoSJE Smart Monitoring Platform.

LOCAL DEV MODE: pure Python + SQLite, no Docker/Postgres/Redis required.
Everything here is written so that switching to Postgres+PostGIS+Redis later
(see comments below) is a config change, not a rewrite.
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
    # "rest_framework_gis",     # Re-enable with PostGIS
    # "channels",               # Re-enable for Phase 4.5 (real-time dashboard)
    # "django_celery_beat",     # Re-enable for Phase 4.7 (random assignment scheduler)
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.registry",
    "apps.inspections",
    "apps.core",
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
# ASGI_APPLICATION = "config.asgi.application"   # Re-enable when Channels is back (Phase 4.5)

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
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# ---------------------------------------------------------------------------
# Channels / Celery — disabled for now (both need Redis, which we're skipping
# until Phase 4). Kept here as reference for when we re-enable them.
# ---------------------------------------------------------------------------
# REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {"hosts": [REDIS_URL]},
#     }
# }
# CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
# CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
# CELERY_ACCEPT_CONTENT = ["json"]
# CELERY_TASK_SERIALIZER = "json"
# CELERY_RESULT_SERIALIZER = "json"
# CELERY_TIMEZONE = TIME_ZONE

# ---------------------------------------------------------------------------
# CORS (open for local dev; tighten before deploying)
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG
