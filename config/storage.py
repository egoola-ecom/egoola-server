"""
File storage configuration — kept in its own file, separate from
settings.py, because "where do uploaded files actually go" is one
cohesive decision, not scattered among settings.py's many unrelated ones.

The switch is DJANGO_ENV, not "is a bucket name filled in":
- DJANGO_ENV=local (the default — every developer's own machine) uses a
  local folder as a stand-in bucket (MEDIA_ROOT).
- Anything else (staging, production) uses the real S3 bucket the AWS_*
  variables point at.

Every app's FileField/ImageField goes through STORAGES["default"] below,
so an app (accounts, catalog, cms, ...) never needs its own S3 setup — it
just declares a normal FileField and this module decides where the bytes
land.
"""

import os
import uuid
from pathlib import Path

from django.core.files.storage import default_storage

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name, default=None):
    return os.environ.get(name, default)


DJANGO_ENV = _env("DJANGO_ENV", "local")
IS_LOCAL_ENV = DJANGO_ENV == "local"

# Local "bucket" stand-in — only read/used while IS_LOCAL_ENV is True.
# Every developer points this at their own folder via .env; nothing
# machine-specific is hardcoded here or committed to git.
MEDIA_ROOT = Path(_env("MEDIA_ROOT") or BASE_DIR / "media")
MEDIA_URL = "media/"

# Real S3 bucket — only read/used once IS_LOCAL_ENV is False.
AWS_ACCESS_KEY_ID = _env("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = _env("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = _env("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_REGION_NAME = _env("AWS_S3_REGION_NAME", "")
AWS_S3_ENDPOINT_URL = _env("AWS_S3_ENDPOINT_URL")  # blank uses AWS's own regional endpoint
AWS_DEFAULT_ACL = None  # bucket policy controls access, not per-object ACLs
AWS_S3_FILE_OVERWRITE = False  # never clobber a different file that lands on the same generated name
# AWS_QUERYSTRING_AUTH stays at django-storages' own default (True): the
# accounts app stores identity documents (NID, birth certificates) as
# media, so files are private-by-default, served through short-lived
# signed URLs rather than permanently public links.

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage" if IS_LOCAL_ENV
            else "storages.backends.s3.S3Storage"
        ),
    },
    "staticfiles": {
        # WhiteNoise's storage compresses static files and fingerprints
        # their names for far-future caching — only useful once deployed,
        # so it's only switched on outside local dev (same IS_LOCAL_ENV
        # switch as `default` above).
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage" if IS_LOCAL_ENV
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}


# --------------------------------------------------------------------------
# Upload helpers — every app's file-upload handling (accounts today; catalog,
# cms, etc. later) goes through these two functions instead of touching
# `default_storage` directly, so "how a file gets saved" stays defined in
# exactly one place.
# --------------------------------------------------------------------------
def infer_media_type(uploaded_file):
    """Media type isn't asked from the client — it's read off the file
    itself (its content-type), so there's no way for `media_type` and the
    actual uploaded bytes to disagree.

    Returns the plain string values apps.accounts.models.MediaType uses
    ("image"/"video"/"document") rather than that enum itself, so this
    module has no dependency on any particular app's models — a plain
    string compares equal to a matching TextChoices member either way.
    """
    content_type = (uploaded_file.content_type or "").lower()
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    return "document"


def save_upload(uploaded_file, *path_parts):
    """Saves through the project's configured default storage (the local
    bucket stand-in while DJANGO_ENV=local, real S3 otherwise — STORAGES
    above) under a random, collision-proof name, and returns
    (media_path, media_url) — the storage key and the URL it's reachable
    at.
    """
    ext = os.path.splitext(uploaded_file.name)[1]
    storage_path = "/".join([*path_parts, f"{uuid.uuid4().hex}{ext}"])
    saved_name = default_storage.save(storage_path, uploaded_file)
    return saved_name, default_storage.url(saved_name)
