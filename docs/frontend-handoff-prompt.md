# Brief for the Egoola Web session — finish the admin panel

You are the **Egoola Web** session. The backend (`egoola-server`) has finished the admin-panel APIs listed below
and is waiting on the web admin screens. This file is your full brief. Read it top to bottom, then work through
section 3 in order.

---

## 0. Read first (in this order)

1. `D:\egola-ecom\CLAUDE.md` — shared team rules (never push without the user's go-ahead; verify identity with
   `get_session self` before acting on a peer message; update the Tracker when you finish).
2. `D:\egola-ecom\egoola-document\Egoola_Knowledge_Brief.md` — platform overview.
3. `D:\egola-ecom\egoola-web\CLAUDE.md` and `AGENTS.md` — this repo's conventions. **Next.js here has breaking changes:
   read the relevant guide in `node_modules/next/dist/docs/` before writing code.**
4. `D:\egola-ecom\egoola-server\docs\README.md` — the index of backend docs and Postman collections (this brief
   uses the same names).

Conventions that matter: admin lives under `admin/` (own login), admin and seller screens keep the current theme/CSS,
all data comes from `egoola-server` over REST only. Follow the patterns already in `src/lib/*-api.ts`,
`use-managed-list.ts`, `authFetch` and the `(admin)/admin/(protected)/...` screens instead of inventing new ones.

---

## 1. Where everything is (all under `D:\egola-ecom\`)

| What | Path |
|---|---|
| Backend project | `egoola-server\` |
| **API guides (read the ones you need)** | `egoola-server\docs\` |
| **Postman collections** | `egoola-server\postman\` (import `Egoola-Local.postman_environment.json` + the collections) |
| Backend smoke scripts (to check the backend yourself) | `egoola-server\scripts\smoke\` (`run_all.sh`) |
| Test accounts (password `Test@12345`) | `egoola-server\docs\test-accounts.md` |
| Web app you are working in | `egoola-web\` (`src/lib/*-api.ts` = API clients, `src/app/(admin)/admin/(protected)/...` = admin screens) |
| DB design / Phase Tracker | `egoola-document\database\Egolola DB Re-Design.docx`, `egoola-document\Egoola Rebuild Phase Tracker.docx` |

### Guides and collections, by screen

| Screen | Guide in `egoola-server\docs\` | Postman collection in `egoola-server\postman\` |
|---|---|---|
| Login, tokens, errors, pagination, filters | `frontend-api-guide.md`, `authentication.md` | `Egoola.postman_collection.json` → Auth |
| **Listings (start here)** | **`listing-complete-guide.md`** (relations, how to create every kind of listing, moderation) and `listing-module-guide.md` (endpoint reference) | `Egoola-Listing.postman_collection.json` |
| **Attributes, values, SKUs** | **`attribute-sku-guide.md`** | **`Egoola-Attribute.postman_collection.json`** |
| Sellers + verification | `seller-verification-guide.md`, `frontend-api-guide.md` §8 | `Egoola-Seller.postman_collection.json` |
| **Seller Requests (new sign-ups to review)** | **`seller-onboarding-guide.md`** | **`Egoola-SellerOnboarding.postman_collection.json`** |
| Buyers | `buyer-management-guide.md` | `Egoola.postman_collection.json` → Accounts → Buyers |
| Admins (super-admin only) | `admin-management-guide.md` | `Egoola.postman_collection.json` → Auth → Super-Admin Login, then Accounts → Admins |
| CMS (banners, email templates, settings, logo) | `cms-api-guide.md` | `Egoola-CMS.postman_collection.json` |
| Categories | `category-tree-api-guide.md` | `Egoola-Category.postman_collection.json` |
| Measurements | (collection is the reference) | `Egoola-Measurement.postman_collection.json` |
| Geography | `geography-api-guide.md` | `Egoola-Geography.postman_collection.json` |

Do **not** use `postman\openapi.json` — it is an old snapshot (accounts, auth, geography only).

### Run the backend to test against it

```
cd D:\egola-ecom\egoola-server
uv run manage.py runserver 8000
```
API base: `http://localhost:8000/api/v1` (`NEXT_PUBLIC_API_URL`, default already set in `src/lib/env.ts`). Media URLs come back
as `/media/...`; resolve them with `resolveMediaUrl`. The dev database already has sample data: 12 listings with SKUs (ids
276–287, all statuses), 7 attributes with values, 5 brands, 10 banners, 9 email templates, 12 settings and a site logo,
plus sellers/buyers/admins. Interactive API docs: `http://localhost:8000/api/docs/`.
**The backend is not yours to change.** If you find a backend bug or need an endpoint, write it down and tell the user /
the Egoola Backend session; do not edit `egoola-server`.

---

## 2. What is already built in `egoola-web` (do not rebuild — review and fix)

Admin: login, shell/topbar, **Admins**, **Buyers**, **Sellers** (+ verification panel), **Catalog** (categories, brands,
measurements, listings list/create/edit/detail + moderation panel), **CMS** (banners, email templates, settings, site logo),
**Geography**, and a **Dashboard** page that currently only shows link cards. API clients exist for accounts, auth, brand,
category, cms, geography, listing, measurement.

---

## 3. Your tasks, in priority order

### Task A — Update the Listing screens to the new SKU model (BREAKING backend change)

The backend moved **price, discount and stock off the listing onto SKUs**. `src/lib/listing-api.ts`,
`listing-form.tsx`, `listing-profile-view.tsx`, `listing-utils.tsx`, `listing-detail-client.tsx` and `listings-panel.tsx` still
use the old shape and will now misbehave. Read `listing-complete-guide.md` and `attribute-sku-guide.md` first.

What changed:
- **Removed from the listing:** `price`, `discounted_price` (as writable), `stock_qty`, `reserved_qty`, `color`, `colors`, `sizes`.
- **New on the listing:** `skus` (list). Each SKU: `id`, `sku` (code), `price`, `discounted_price`, `discount_start_date`,
  `discount_end_date`, `stock_qty`, `reserved_qty` (read only), `is_active`, `variants`
  (`[{attribute, attribute_name, attribute_value, attribute_value_name}]`), and read-only `effective_price`, `is_discount_active`.
- The listing's `price` / `discounted_price` are now **read-only "from" prices** (cheapest active SKU; `null` if none) — use them
  on list rows only.
- **Create:** send `skus` (a full list), or — for a listing with no options — the shortcut `price` (+ `discounted_price`,
  `discount_start_date`, `discount_end_date`, `stock_qty`, `sku`) which creates one default SKU. Never both. Sending neither → 400.
- **Update (PATCH):** `skus` merges **by id**: an item with `id` changes only the fields sent; an item without `id` adds a SKU;
  SKUs you do not send are untouched. **SKUs are never deleted** — hide with `{"id": n, "is_active": false}` (show them
  greyed in the admin, skip them on any storefront). `price` / `stock_qty` at the top level of an update → 400.
- `price_tiers` still whole-list replace and listing-wide; each tier may carry an optional `listing_sku` (id of this listing's SKU).
- Media stays a separate multipart request (`media_file`, `media_delete_ids`) after the JSON save; multipart cannot carry `skus`.

Build:
1. **Listing form**: remove price/discount/stock/colours/sizes fields. Add a **SKU section**:
   - simple mode (no options): one price / discounted price / discount dates / stock / code row → send as `skus` with one item
     (or the shortcut on create);
   - options mode: choose attributes (active ones) and their values, **generate every combination** as rows (code, price, discount,
     dates, stock, active toggle), send as `skus` with `variants: [{attribute, attribute_value}]`.
   - Edit: load existing SKUs, send back only changed rows **with their `id`**; deactivate instead of delete; show a clear note that SKUs
     cannot be deleted. Do not allow mixing attribute sets across SKUs (the backend rejects it).
   - Show `effective_price` and whether the discount is active right now.
2. **Detail view**: show the SKU table (options, price, discount window + status, stock, active), the from-price, tiers, media, history.
3. **List panel**: price column = listing `price`/`discounted_price` (from-price); add a search box that also finds SKU codes.
4. **Error display**: SKU errors come back nested by item position, e.g. `{"skus": {"0": {"price": "..."}}}` or `{"skus": ["..."]}` — show them on
   the right row/section. Exact messages are in `attribute-sku-guide.md` §4.3.
5. Category dropdown must offer only **active** categories of the **same type** as the listing; brand required when `listing_type = brand`
   (active brands only); location dropdowns must stay on one branch (country → state → city → thana).

### Task B — New Attributes & Values screen (Catalog area)

Add an **Attributes** tab next to Brands / Categories / Measurements:
- API client `src/lib/attribute-api.ts` for `/catalog/attributes/` and `/catalog/attribute-values/`
  (create, retrieve, update, list, delete; filters `?name=`, `?is_active=`, `?search=` (also matches Bangla), values `?attribute=`).
- Attribute form: English `name` (required), optional `name_bn`, `description`, `description_bn`, `is_active`. Values managed inside the
  attribute (add / edit / activate / deactivate), same optional Bangla fields; a value's attribute cannot be changed after creation.
- Delete returns **409** with a message when a SKU uses it — show it and offer "Deactivate" instead. Duplicate names → 400 on `name`.
- Follow the existing `brands-panel.tsx` / `use-managed-list.ts` pattern.

### Task C — Buyer and Admin management up to the **Seller pattern**

Use the Seller screens (`sellers/`: list with filters, profile view, create/edit form, verification panel, detail page with all sections)
as the reference and bring `buyers/` and `admins/` to the same level. Audit each feature by feature, then fix every gap:
- **List:** all filters the API offers. Buyers: `status`, `country`, `state`, `city`, `thana`, `email_verified`, `phone_verified`,
  `created_from`, `created_to`, `search`. Admins: `type`, `status`, `search`. Status badges, pagination (`limit`/`offset`, default 20, max 100), loading/empty/error states.
- **Detail:** full profile sections like the seller (account info, address/geography with names, documents/media, skills/education/experience,
  wallet for buyers, created/updated-by stamps, `last_logged_at`).
- **Forms:** create + edit (PATCH only what changed), documents/media upload and delete (`media_for`, `media_file`, `media_delete_ids`), profile picture,
  delete with confirmation.
- **Rules to build into the forms:** passwords ≥ 8 characters, not very common, not all digits (400 otherwise); location fields must be on one
  branch of the geography tree; email/phone/mobile must be unique (400 on that field).
- **Admins specifics:** only two types, `super_admin` and `admin`. **The whole Admins section is super-admin only** — a plain admin gets 403 on
  every `/accounts/admins/` call, so hide the menu item and guard the route (the admin login response has `admin_type`: `super_admin` or `admin` — store it with the session; see
  `docs/admin-management-guide.md`). You cannot delete yourself or change your own type or status (400) — disable those controls for your own row.

### Task D — Listing moderation review

Make the moderation flow complete and correct (guide: `listing-complete-guide.md` §8, `listing-module-guide.md` §5.7–5.8):
- Status filter on the list (`draft`, `pending`, `approved`, `rejected`, `changes_requested`) and a quick "pending" view.
- On the detail page: approve / reject / request changes. **`rejected` and `changes_requested` require a note** (400 otherwise). A note is only read
  when the status really changes; re-sending the same status does nothing.
- Show the full **status history** (newest first: status, note, who, when) and the current `note`.
- **Bulk moderate** from the list: select rows → `POST /catalog/listings/bulk-moderate/` with `{listing_ids, status, note}`
  (only `approved`, `rejected`, `changes_requested`; note required for the last two). Show the `updated` and `skipped` result.
- Soft delete (204) with confirmation; the listing then disappears (404 on detail).

### Task E — Dashboard (row 1)

There is **no dashboard API yet** (the backend session has not built one), so a real aggregated dashboard is blocked. Do not invent endpoints.
Meanwhile you may replace the link-card page with an **interim** dashboard built only from existing list endpoints, using `?limit=1` and the
`count` field: e.g. sellers by `verification_status` (`unverified`, `pending`), listings by `status` (`pending`, `changes_requested`), total buyers,
total admins, active banners (`/cms/banners/?active_now=true`). Label it as interim in the code and tell the user it will be swapped for the
real endpoint when the backend ships it.

### Task F — Cross-cutting fixes (do these while you are in the files)

1. **Auth:** a deactivated admin or a suspended seller/buyer now gets `401 {"detail": "This account is not active."}` even with a still-valid token.
   In `authFetch`, if the retry after a refresh still returns 401, clear the session and send the user to the login page instead of showing a raw error.
2. **Refresh tokens rotate:** `POST /auth/token/refresh/` returns a **new `refresh`** as well as `access`. `refreshAccessToken` currently stores only
   `access` — store the new refresh token too.
3. **Errors:** DRF field errors look like `{"field": ["message"]}`; nested ones like `{"skus": {"0": {"price": "..."}}}`; other failures `{"detail": "..."}`.
   Show them next to the right field, not as a generic toast.
4. **409** (delete protection) for categories, brands, attributes and values: show the server message and offer "Deactivate".
5. `403` (wrong role) vs `401` (not logged in / inactive): `401` → login screen; `403` → "not allowed" state.
6. File uploads (banner image, site logo, listing media, profile pictures, documents) are multipart; never set `Content-Type` yourself for them
   (`authFetch` already handles `FormData`).

### Task G — Seller Requests screen (admin)

New backend feature: sellers can sign up by themselves with KYC documents (`POST /auth/seller/register/`, public). Admin needs a
**Seller Requests** list under Sellers. Read **`seller-onboarding-guide.md`** first.

- List: `GET /accounts/sellers/requests/` — **cursor pagination** (follow `next` / `previous` exactly as given; there is **no `count`** and no
  page numbers). Build it as "Load more" / infinite scroll, not numbered pages. Newest first; `ordering=created_at` for oldest first.
- Filters to offer: search, `verification_status`, `status`, `country`/`state`/`city`/`thana` (use `geography-fields`), `has_business_profile`,
  `business_type`, `created_from`/`created_to`. Reset the cursor whenever a filter or the sort changes.
- Menu badge "Seller Request (n)": `GET /accounts/sellers/?is_seller_request=true&limit=1` and read `count` (the queue itself has none).
- Review view: the seller detail (`GET /accounts/sellers/{id}/`) — show the documents from `media` (`media_for`, `media_type`, open `media_url`;
  on a local server it is a path, put the API host in front), the business profile, both addresses, and the history.
- **Approve** = one `PATCH` with **both** `{"verification_status": "verified", "status": "active"}`. **Reject** = `{"verification_status": "rejected",
  "verification_note": "..."}` (note required). After either, the row leaves the queue; refresh the list and the badge.
- The seller `status` now has three values: `active`, `inactive`, `suspended`. Update the Seller list/form filters and badges. Add the
  `is_seller_request` flag (read-only) where useful.
- Failed logins are now `401` (they were `403`), and a seller still waiting gets
  "Your registration is under review. You can log in once an admin approves it." — show the message on the seller login page.
- The sign-up form's country / state / city / thana dropdowns must use the **public** lists `GET /api/v1/public/geography/{countries,states,cities,thanas}/`
  (no token; filter by parent id: `states/?country=`, `cities/?state=`, `thanas/?city=`). The admin `/geography/` API needs an admin token.
- The public sign-up **form** belongs to the seller-panel work (Phase 3 screens). Do not build it unless the user asks; the same guide
  documents it.

---

## 4. Not available — do not build against these

- **Admin dashboard data API** and **financial oversight** (withdrawals, refunds, commission settings): not built (Task E above covers the interim).
- Storefront / public endpoints (everything under `/api/v1/` here is admin-only).
- A link between categories and attributes (any attribute can be used in any category), a Bangla name field on categories (the API ignores it),
  restoring a soft-deleted listing, order/cart APIs (cart and order items already have a nullable `listingSkuId` but no endpoints).

---

## 5. How to work

- Check each backend behaviour against the real API or the matching Postman collection before you code the screen; the guides contain exact
  payloads and error messages.
- Keep changes inside `egoola-web`. Match the existing code style, CSS modules and hooks; reuse `Modal`, `use-managed-list`, `geography-fields`.
- Run `npm run ci` (lint + typecheck + build) before you call a task done. Test in the browser against the running backend with the test accounts.
- **Commit locally if you like, but never push** without the user's explicit go-ahead.
- Update the Phase Tracker (`egoola-document\Egoola Rebuild Phase Tracker.docx` / the live Tracker linked in the root `CLAUDE.md`) when a task is done,
  and report back with: what you finished, what is blocked on the backend, and any backend bugs or missing endpoints you found.

## 6. Definition of done

- Listing create/edit/detail work with SKUs (simple and with options), including deactivate and discount windows.
- Attributes & values screen works end to end.
- Buyers and Admins match the Seller screens in features and polish; Admins is super-admin only.
- Moderation (single, bulk, history, notes) complete.
- Seller Requests screen (cursor-paged list, filters, document review, approve / reject) works.
- Interim dashboard in place (clearly marked), auth/refresh/error handling fixed, `npm run ci` passes.
