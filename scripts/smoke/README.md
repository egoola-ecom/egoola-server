# Smoke scripts

Curl-based checks that run against a **running local dev server** and the
accounts in [`docs/test-accounts.md`](../../docs/test-accounts.md). The guides in
`docs/` quote their pass counts.

| Script | Covers | Checks |
|---|---|---|
| `e2e_smoke.sh` | seller approval, listing moderation, buyer management, a second admin created by a super-admin, banner update, plus the validation, note, location and password rules | 159 |
| `admin_smoke.sh` | Admin Management (super-admin gate, self-protection, filters) | 52 |
| `buyer_smoke.sh` | Buyer Management | 49 |
| `listing_smoke.sh` | Listings (CRUD, moderation, tiers, media, soft delete, bulk) | 54 |
| `brand_smoke.sh` | Brands and the listing/brand/discount rules | 55 |
| `sku_smoke.py` | Attributes, attribute values and listing SKUs (every SKU rule, update by id, discount windows, category delete protection) | 144 |
| `cms_smoke.sh` | Banners, email templates, settings, site logo | 97 |
| `seller_onboarding_smoke.sh` | Seller self-registration with KYC documents (validation, files, duplicates, location), pending-seller login, the Seller Request queue (cursor paging, ordering, every filter, permissions) and how admin actions clear the request flag | 162 |
| `seller_self_smoke.sh` | The seller's own API (`/seller/me/`): sellers who cannot operate (pending, rejected, or approved but paused) can log in and edit only their profile, email/phone locked, documents (add, delete, replace, NID rules, locked after verification), password change, resubmit after a rejection, the profile change log (seller and admin edits, before/after, no password hash), suspended sellers, `IsActiveVerifiedSellerActor`, files removed from storage when media, a photo or an account is deleted, and the phone + password seller login | 156 |
| `seller_listing_smoke.sh` | The seller product API (every product format through one endpoint), lookups, access rules, the same-title rule (also on admin-created listings and in the database), Bangla fields, list filters, the admin pending list (cursor), approve / reject / fix by saving (no Resubmit button), approved listings staying approved, the info change log (before / after, stock not logged), file limits and files removed from storage | 221 |
| `public_geography_smoke.sh` | The public (no login) country / state / city / thana lists: shape, parent filters, search, read-only, no audit data, admin API still locked | 45 |
| `gig_smoke.py` | The admin gig API (`/catalog/gigs/`): packages (price type, duration, one per type, no stock or options), every rule, edit by SKU id, list and filters, the pending gig list, bulk moderation, the product / gig / job separation (404 and 400) | 115 |
| `seller_gig_smoke.py` | The seller gig API (`/seller/gigs/`): access, always pending, packages and their rules, the same-title rule per type, the product / gig split, approve / reject / fix | 72 |
| `listing_files_smoke.py` | The 4 listing-files APIs (`/catalog/listing-files/{id}/`, `/seller/listing-files/{id}/`, POST + PATCH) for products and gigs: add, replace, remove, gallery, limits, all-or-nothing, access, status rules, change log, JSON-only create / update, old `/thumbnail/` gone | 130 |
| `category_browse_smoke.py` | The Buyer Panel category list (`/public/catalog/categories/`): no login, roots by default, `parent_id` children at every level, name / Bangla search (with and without a parent), `type`, active only (also under an inactive parent), page-based paging, validation (`400` / `404`) | 41 |
| `public_listing_smoke.py` | The public product and gig lists and details (`/public/catalog/products/`, `/gigs/`) and the seller page (`/public/sellers/{id}/`): visibility (approved, live, seller verified and active, an active SKU), every filter, ordering, paging, validation, product / gig / job separation, no private fields | 103 |
| `buyer_register_smoke.py` | Buyer sign-up (`/auth/buyer/register/`: only name, phone, password required; optional fields, mobile format, duplicates ignoring case and spaces, location rules, profile picture, tokens work, status / wallet cannot be set) and buyer login by phone or email | 55 |
| `buyer_cart_smoke.py` | The buyer's own cart (`/buyer/cart/`, `/buyer/cart/items/`): one active cart per (buyer, type), auto-created, picked by the added listing's own type; merging the same SKU; qty vs duration rules, stock check, cross-listing SKU, unknown listing, missing/bad `?type`, auth (401/403), per-buyer scoping (404 on another buyer's item), PATCH, DELETE one line, and clearing the cart (still active, just empty) | 35 |

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
