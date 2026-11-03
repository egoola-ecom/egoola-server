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
| `sku_smoke.py` | Attributes, attribute values and listing SKUs (every SKU rule, update by id, discount windows, category delete protection) | 143 |
| `cms_smoke.sh` | Banners, email templates, settings, site logo | 97 |
| `seller_onboarding_smoke.sh` | Seller self-registration with KYC documents (validation, files, duplicates, location), pending-seller login, the Seller Request queue (cursor paging, ordering, every filter, permissions) and how admin actions clear the request flag | 162 |
| `seller_self_smoke.sh` | The seller's own API (`/seller/me/`): sellers who cannot operate (pending, rejected, or approved but paused) can log in and edit only their profile, email/phone locked, documents (add, delete, replace, NID rules, locked after verification), password change, resubmit after a rejection, the profile change log (seller and admin edits, before/after, no password hash), suspended sellers, `IsActiveVerifiedSellerActor`, files removed from storage when media, a photo or an account is deleted, and the phone + password seller login | 156 |
| `seller_listing_smoke.sh` | The seller product API (every product format through one endpoint), lookups, access rules, the same-title rule (also on admin-created listings and in the database), Bangla fields, list filters, the admin pending list (cursor), approve / reject / fix by saving (no Resubmit button), approved listings staying approved, the info change log (before / after, stock not logged), file limits and files removed from storage | 221 |
| `public_geography_smoke.sh` | The public (no login) country / state / city / thana lists: shape, parent filters, search, read-only, no audit data, admin API still locked | 45 |
| `gig_smoke.py` | The admin gig API (`/catalog/gigs/`): packages (price type, duration, one per type, no stock or options), every rule, edit by SKU id, list and filters, the pending gig list, bulk moderation, the product / gig / job separation (404 and 400) | 109 |
| `seller_gig_smoke.py` | The seller gig API (`/seller/gigs/`): access, always pending, packages and their rules, the same-title rule per type, the product / gig split, approve / reject / fix | 72 |
| `listing_files_smoke.py` | The 4 listing-files APIs (`/catalog/listing-files/{id}/`, `/seller/listing-files/{id}/`, POST + PATCH) for products and gigs: add, replace, remove, gallery, limits, all-or-nothing, access, status rules, change log, JSON-only create / update, old `/thumbnail/` gone | 130 |
| `category_browse_smoke.py` | The Buyer Panel category list (`/public/catalog/categories/`): no login, roots by default, `parent_id` children at every level, name / Bangla search (with and without a parent), `type`, active only (also under an inactive parent), page-based paging, validation (`400` / `404`) | 41 |
| `public_listing_smoke.py` | The public product and gig lists and details (`/public/catalog/products/`, `/gigs/`) and the seller page (`/public/sellers/{id}/`): visibility (approved, live, seller verified and active, an active SKU), every filter, ordering, paging, validation, product / gig / job separation, no private fields | 103 |
| `buyer_register_smoke.py` | Buyer sign-up (`/auth/buyer/register/`: only name, phone, password required; optional fields, mobile format, duplicates ignoring case and spaces, location rules, profile picture, tokens work, status / wallet cannot be set) and buyer login by phone or email | 55 |
| `buyer_cart_smoke.py` | The buyer's own cart(s) (`/buyer/cart/`, `/buyer/cart/items/`, `/buyer/cart/summary/`): one active cart per (buyer, type, seller) — never spanning sellers; GET/DELETE are pure lookups (never creating), targeting a named `?seller=` or the most-recently-touched cart otherwise, `null`/no-op when there is none; `summary` listing every active cart at once (line-count `item_count`, not a qty/duration sum) plus a grand total; admin-owned (no-seller) listings sharing one cart; merging the same SKU; qty vs duration rules, stock check, cross-listing SKU, unknown listing, missing/bad `?type` or `?seller`, auth (401/403), per-buyer scoping (404 on another buyer's item), PATCH, DELETE one line | 57 |
| `buyer_favourites_smoke.py` | The buyer's own wishlist (`/buyer/favourites/`): save, idempotent re-save (200, no duplicate), list newest first, `?type` filter, validation and auth, a favourite surviving its listing going private (hidden, not deleted, reappears), per-buyer scoping, and idempotent remove (204 whether or not it was saved) | 21 |
| `admin_cart_smoke.py` | Admin, read-only oversight of carts (`/orders/carts/`): auth (admin only, 401/403), cursor paging shape, buyer/seller (incl. the `0` no-seller sentinel)/search/`cart_type`/`is_active`/`has_order`/`listing` filters, item count and subtotal on the list row, and the detail view's items and audit columns | 26 |
| `admin_favourites_smoke.py` | Admin, read-only oversight of wishlists (`/engagement/favourites/`): auth, cursor paging shape, buyer/`catalog_type`/`listing` filters, the `listing_visible` filter and that admin still sees a favourite whose listing went private (unlike the buyer's own view), and the detail view's audit columns | 19 |
| `buyer_job_smoke.py` | A buyer's own job postings (`/buyer/jobs/`): the mandatory budget SKU, the full status state machine (`open_for_bidding` on create, pause/reopen via `draft`→`pending`, cancel, and the `in_progress`-locks-everything-but-complete rule), the empty bids-on-my-job list, and per-buyer scoping (404 on another buyer's job) | 29 |
| `seller_job_smoke.py` | The seller job board and bidding (`/seller/jobs/`, `/seller/bids/`): auth (pending/unverified seller blocked), the open-jobs-only board with `bid_count`/`my_bid_count`, job detail with my own bids embedded, `/seller/jobs/mine/` and `?won=true` (jobs this seller was actually hired for), placing a bid (mandatory price tiers, only one live bid per seller per job, only on an `open_for_bidding` job), price-tier reconcile on edit (same contract as a listing's SKUs), cancel, re-bidding after cancel as a new historical row, and a closed job dropping off the board while staying visible to a seller who already bid | 42 |
| `bid_accept_smoke.py` | A buyer accepting a bid (`/buyer/jobs/{job_id}/bids/{bid_id}/accept/`) and its cascades: Order created directly (no cart), every other pending bid auto-rejected, job → `in_progress`; marking it complete carries the accepted bid and Order to `completed`; cancelling a job cancels its live bid(s) (never the already-rejected ones) and, if one was accepted, its Order too; multi-tier bids require an explicit `price_tier_id` | 25 |
| `admin_job_bid_smoke.py` | The admin job + bid panel (`/catalog/jobs/`, `/bidding/bids/`) — "admin can do everything": create a job on a buyer's behalf, create a bid on a seller's behalf, accept on the buyer's behalf (same cascade as the buyer's own accept), `reject` to undo an already-accepted hire (job reopens, the Order cancels, the bid that auto-rejected earlier stays rejected), the admin-only `in_progress -> cancelled` transition with a mandatory reason, and that a job is no longer reachable through `/catalog/listings/` or `/catalog/gigs/` | 32 |

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
