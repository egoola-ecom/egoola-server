# Smoke scripts

Curl-based checks that run against a **running local dev server** and the
accounts in [`docs/test-accounts.md`](../../docs/test-accounts.md). The guides in
`docs/` quote their pass counts.

| Script | Covers | Checks |
|---|---|---|
| `e2e_smoke.sh` | seller approval, listing moderation, buyer management, a second admin created by a super-admin, banner update, plus the validation, note, location and password rules | 158 |
| `admin_smoke.sh` | Admin Management (super-admin gate, self-protection, filters) | 52 |
| `buyer_smoke.sh` | Buyer Management | 49 |
| `listing_smoke.sh` | Listings (CRUD, moderation, tiers, media, soft delete, bulk) | 54 |
| `brand_smoke.sh` | Brands and the listing/brand/discount rules | 55 |
| `sku_smoke.py` | Attributes, attribute values and listing SKUs (every SKU rule, update by id, discount windows, category delete protection) | 143 |
| `cms_smoke.sh` | Banners, email templates, settings, site logo | 97 |

```bash
uv run manage.py runserver 8000        # in one terminal
scripts/smoke/run_all.sh               # in another
scripts/smoke/e2e_smoke.sh             # or a single suite
SMOKE_BASE=http://127.0.0.1:9000 scripts/smoke/run_all.sh
```

Needs `bash`, `curl`, `python` and `uv`. Every suite creates its own data with
a recognisable prefix (`Smoke…`, `E2E…`, `smoke.…@…`, `e2e.…@…`) and removes it
again when it exits, including uploaded files — even if the run fails.
`admin_smoke.sh` creates and removes a throwaway super-admin
(`smoke.super@egoola.com`).

Reference ids used by the suites (see `docs/test-accounts.md`): product
category 18, service category 29, measurement 13, country 126, state 13
(Chittagong), city 8 (Feni). If the database is rebuilt, update them.
