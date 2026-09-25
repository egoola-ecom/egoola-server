"""
Django settings for the Egoola rebuild backend.

Every setting that differs between a developer's machine, CI, and production
is read from the environment (see .env.example) — nothing environment-specific
is hardcoded here.
"""

from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Render sets this automatically on every web service (e.g.
# "egoola-server.onrender.com") — trusting it here means DJANGO_ALLOWED_HOSTS
# doesn't need to be hand-maintained with the assigned Render domain.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Django's own CSRF check (used by the session-based /admin/ site, not by
# the JWT API) compares the request's Origin against this list — required
# for any https:// origin once DEBUG is off. Same Render domain as above.
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Render terminates TLS at its edge and forwards plain HTTP to the app —
# without this, Django can't tell the request was actually HTTPS, which
# breaks the CSRF/secure-cookie checks above.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    "django_filters",
    # Egoola apps (Section 4.1 of the Planning document — one app per
    # Database Redesign module) plus `core`, which holds the shared
    # audit-trail base model every one of the modules below builds on.
    "apps.core",
    "apps.geography",
    "apps.accounts",
    "apps.authentication",
    "apps.catalog",
    "apps.bidding",
    "apps.orders",
    "apps.inquiries",
    "apps.messaging",
    "apps.engagement",
    "apps.notifications",
    "apps.cms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves collected static files directly from the app process — no
    # separate static-file host needed, which matters on Render's free web
    # service (only one process, no CDN/static-site pairing by default).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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
ASGI_APPLICATION = "config.asgi.application"

# --------------------------------------------------------------------------
# Database — PostgreSQL only (see Planning document Section 4.3: JSONB/GIN
# support is a deliberate reason for choosing Postgres over MySQL/MariaDB).
# Every table is created through Django's ORM migrations, never hand-written
# SQL (Phase 0 Backend, task 3).
# --------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "egoola"),
        "USER": env("DB_USER", "postgres"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
    }
}

# --------------------------------------------------------------------------
# bcrypt for every password this project hashes (Admin/Seller/User rows via
# apps.accounts, and Django's own auth_user). BCryptSHA256 (not plain BCrypt)
# because bcrypt itself silently truncates passwords over 72 bytes — the
# SHA256 pre-hash avoids that. The older hashers stay listed after it purely
# so any password hashed before this change (PBKDF2, Django's old default)
# still verifies; every *new* hash uses bcrypt, since make_password() always
# uses whichever hasher is listed first.
# --------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Asia/Dhaka")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# DRF + drf-spectacular (Phase 0 Backend, task 5 — API docs at /api/docs/)
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.authentication.backends.ActorJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 20,  # DRF's LimitOffsetPagination reads this as its default `limit`
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Egoola API",
    "DESCRIPTION": "Backend API for the Egoola marketplace rebuild.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --------------------------------------------------------------------------
# JWT (Phase 0 Backend, task 7). Three separate login flows (Admin, Seller,
# Buyer/User) are built on top of this in Phase 1 — see Planning document
# Section 4.2. Each token embeds an `actor_type` claim so a request can be
# checked against the right one of the three actor tables.
# --------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

# --------------------------------------------------------------------------
# CORS (Phase 0 Backend, task 6) — egoola-web talks to egoola-server from a
# different origin. Flutter apps aren't affected by CORS at all (Planning
# document Section 5), so this only needs to cover the web app's dev/prod URLs.
# --------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)

# Temporary escape hatch for early deployment, before the frontend's real
# domain is known — skips CORS_ALLOWED_ORIGINS entirely and accepts a
# browser request from any origin. Meant to be turned back off
# (CORS_ALLOW_ALL_ORIGINS unset/false) once that domain is known, in favor
# of listing it explicitly in CORS_ALLOWED_ORIGINS above.
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", False)

# --------------------------------------------------------------------------
# File storage — see config/storage.py for the actual configuration and why
# it's kept separate. Imported here (rather than at the top of the file)
# because it reads AWS_*/MEDIA_ROOT from the environment at import time, and
# load_dotenv() above must run first.
# --------------------------------------------------------------------------
from config.storage import (  # noqa: E402
    AWS_ACCESS_KEY_ID,
    AWS_DEFAULT_ACL,
    AWS_S3_ENDPOINT_URL,
    AWS_S3_FILE_OVERWRITE,
    AWS_S3_REGION_NAME,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
    DJANGO_ENV,
    IS_LOCAL_ENV,
    MEDIA_ROOT,
    MEDIA_URL,
    STORAGES,
)
