# Shared setup for the smoke scripts. Source it; do not run it.
#
# Gives every script:
#   SERVER_DIR  the egoola-server folder (so `uv run manage.py ...` works)
#   SCRATCH     a private temp folder, removed on exit, holding t.png (a real
#               4x4 PNG — image fields reject fake bytes)
#   cleanup_data  deletes every row/file the suites create, matched by their
#               name prefixes (Smoke*, E2E*, smoke.*, e2e.*, ...). It runs on exit,
#               so a failed run does not leave data behind.
# Needs: bash, curl, python, uv, and a dev server on $SMOKE_BASE (default
# http://127.0.0.1:8000) with the accounts from docs/test-accounts.md.

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SMOKE_BASE="${SMOKE_BASE:-http://127.0.0.1:8000}"

_scratch="$(mktemp -d)"
if command -v cygpath >/dev/null 2>&1; then _scratch="$(cygpath -m "$_scratch")"; fi
SCRATCH="$_scratch"
export SCRATCH SERVER_DIR

python - <<'PY'
import os, struct, zlib
def chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
raw = b"".join(b"\x00" + b"\x00\x00\xff" * 4 for _ in range(4))
png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
open(os.path.join(os.environ["SCRATCH"], "t.png"), "wb").write(png)
PY

cleanup_data() {
  (cd "$SERVER_DIR" && uv run manage.py shell -c "
import shutil
from pathlib import Path
from django.conf import settings
from django.db.models import Q
from apps.accounts.models import Admin, Seller, User
from apps.catalog.models import Attribute, Brand, Category, Listing, Measurement
from apps.cms.models import Banner, EmailTemplate, Setting
from apps.geography.models import Thana

def starts(field, *prefixes):
    q = Q()
    for p in prefixes:
        q |= Q(**{field + '__istartswith': p})
    return q

listings = Listing.all_objects.filter(starts('title', 'Smoke', 'Bad Listing', 'E2E', 'PROBE'))
for thumbnail in listings.exclude(image_path__isnull=True).values_list('image_path', flat=True):
    (Path(settings.MEDIA_ROOT) / thumbnail).unlink(missing_ok=True)
for listing_id in list(listings.values_list('id', flat=True)):
    shutil.rmtree(Path(settings.MEDIA_ROOT) / 'listing' / str(listing_id), ignore_errors=True)
listings.delete()
# Files of listings a suite already hard-deleted itself: any media/listing/<id>
# folder with no listing row behind it is an orphan.
listing_media = Path(settings.MEDIA_ROOT) / 'listing'
if listing_media.is_dir():
    existing = {str(i) for i in Listing.all_objects.values_list('id', flat=True)}
    for folder in listing_media.iterdir():
        if folder.is_dir() and folder.name != 'thumbnails' and folder.name not in existing:
            shutil.rmtree(folder, ignore_errors=True)
# Same for seller documents and profile pictures: once the Smoke*/e2e.* seller
# rows are gone (below), any file no Seller/SellerMedia row points at is an orphan.
Seller.objects.filter(starts('email', 'smoke.', 'e2e.', 'listing.smoke.')).delete()
from apps.accounts.models import SellerMedia
media_root = Path(settings.MEDIA_ROOT)
for folder, used in (
    ('seller', set(SellerMedia.objects.values_list('media_path', flat=True))),
    ('profile-pics/seller', set(Seller.objects.exclude(profile_pic_path=None).values_list('profile_pic_path', flat=True))),
):
    if (media_root / folder).is_dir():
        for path in (media_root / folder).rglob('*'):
            if path.is_file() and path.relative_to(media_root).as_posix() not in used:
                path.unlink()
Brand.objects.filter(starts('name', 'Smoke')).delete()
Attribute.objects.filter(starts('name', 'Smoke')).delete()
Seller.objects.filter(starts('email', 'smoke.', 'e2e.', 'listing.smoke.')).delete()
User.objects.filter(starts('email', 'smoke.', 'e2e.', 'listing.smoke.')).delete()
Admin.objects.filter(starts('email', 'smoke.', 'e2e.')).delete()
Category.objects.filter(starts('name', 'Smoke')).delete()
Measurement.objects.filter(starts('name', 'Smoke')).delete()
Thana.objects.filter(starts('name', 'Smoke')).delete()
Banner.objects.filter(starts('heading', 'Smoke', 'E2E')).delete()
EmailTemplate.objects.filter(starts('key', 'smoke', 'e2e')).delete()
Setting.objects.filter(starts('key', 'smoke', 'e2e')).delete()
" >/dev/null 2>&1)
}

_smoke_exit() { cleanup_data; rm -rf "$SCRATCH"; }
trap _smoke_exit EXIT

# The Admin Management suite logs in as a throwaway super-admin.
ensure_smoke_super() {
  (cd "$SERVER_DIR" && uv run manage.py shell -c "
from django.contrib.auth.hashers import make_password
from apps.accounts.models import Admin
Admin.objects.get_or_create(email='smoke.super@egoola.com', defaults=dict(
    name='Smoke Super', mobile='+8801700099000', password=make_password('Test@12345'), type='super_admin'))
" >/dev/null 2>&1)
}
