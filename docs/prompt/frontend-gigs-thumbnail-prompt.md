# Brief for the Egoola Web session — separate Listings and Gigs panels, gig packages, and the thumbnail

You are the **Egoola Web** session. The backend (`egoola-server`) changed how listings work. This is a **breaking change** for the admin screens
that already exist, and it adds a new **Gigs** area and a **thumbnail** upload. This file is your whole brief: read it top to bottom, then build
the tasks in section 4 in order. The backend is finished and tested; you only build screens.

---

## 0. Read first

1. `D:\egola-ecom\CLAUDE.md` (shared rules: never push without the user's go-ahead; verify your identity with `get_session self` before acting on a
   peer message; update the Phase Tracker when you finish a task).
2. `D:\egola-ecom\egoola-web\CLAUDE.md` and `AGENTS.md` (this repo's conventions; Next.js here has breaking changes, read the relevant guide in
   `node_modules/next/dist/docs/` before writing code).
3. `egoola-server\docs\listing-complete-guide.md` **sections 14 and 15** (the full gig and thumbnail contract) and
   `egoola-server\docs\Egoola_Listing_Guide.md` **section 12** (the same rules in plain words).
4. For the product side you already know: `listing-complete-guide.md`, `attribute-sku-guide.md` (sections 1–7), `frontend-api-guide.md`.

Rules that always apply: all data comes from `egoola-server` over REST only; follow the patterns already in `src/lib/*-api.ts`, `use-managed-list.ts`,
`authFetch`, `Modal`, `geography-fields` and the `(admin)/admin/(protected)/...` screens; the admin keeps the current theme and CSS; **never edit
`egoola-server`** (write down any backend bug or missing endpoint and tell the user).

Run the backend: `cd D:\egola-ecom\egoola-server && uv run manage.py runserver 8000`. Base URL `http://localhost:8000/api/v1`. Logins and ids:
`egoola-server\docs\test-accounts.md` (password `Test@12345`; product category 18, **service category 29**, measurement 13, Bangladesh 126 /
Chittagong 13 / Feni 8). Postman: `postman\Egoola-Listing.postman_collection.json` → **Gigs** and **Listing files**. Media URLs come back as
`/media/...`: resolve them with `resolveMediaUrl`.

---

## 1. What changed in the backend (the model you must follow)

There are now **three kinds** of listing, each with its **own API**. They are rows of one table, told apart by `catalog_type` and `posted_by_role`
(which can never be changed after creation).

| Kind | What it is | Admin API | Status |
|---|---|---|---|
| **Product** | a thing for sale (`catalog_type = product`) | `/catalog/listings/` | existing screens, change them |
| **Gig** | a seller's **service offer** (`service` + `seller_offer`) | **`/catalog/gigs/`** (new) | build a new panel |
| **Job** | a buyer's request for work (`service` + `buyer_request`) | `/catalog/listings/` (for now) | no UI to build |

- **Wrong kind = error.** A gig id on `/catalog/listings/...` is `404`, and a product id on `/catalog/gigs/...` is `404`. A seller's service offer
  sent to `/catalog/listings/` is `400`. Fields of another kind are `400` (see 3.4).
- **Removed from the listing:** `price_type` and `hourly_rate` no longer exist on a listing or gig.
- **New on every listing and gig:** `image_path` and `image_url` (read only): the **thumbnail**, changed through the listing-files API (section 3.6).
- **A gig is priced by packages.** A package is a SKU with a **`price_type`** (`hourly`, `daily`, `weekly`, `monthly` or `fixed`) and a **`price`
  that is the rate for that unit**. A SKU has **no duration**: the buyer will choose how many hours / days / weeks / months when ordering (the order
  stores it). You do **not** build ordering. One gig can have several packages, **at most one per price type**.
- A gig has **no options (attributes), no stock, no quantity prices, no brand / model / origin / warranty / measurement / condition /
  `listing_type` / `attributes` / `min_order_qty`**.

---

## 2. What to build (summary)

1. **Two separate admin areas:** **Listings** (products) and **Gigs** (service offers). In the sidebar and in any type switch, **Product is the
   default for Listings and Service is the default for Gigs**. The Listings area has **no service option**; the Gigs area has **no product option**.
2. A full **Gigs** panel: list, create, edit, details, delete, pending list, moderation (single and bulk), history, change log.
3. A **Packages** editor in the gig form (price type + rate + discount + description, one row per package).
4. A **Thumbnail** control (preview, upload, replace, remove) on the product and gig forms and detail pages.
5. Fix the existing Listings screens for the removed fields and the new response shape.

Out of scope: orders, carts, hiring, job requests, bidding, the buyer storefront. Do not invent endpoints.

---

## 3. The API contract

All admin calls need `Authorization: Bearer <admin access token>` (any admin). Seller / buyer tokens get `403`, no token `401` (send the user to
login on `401`). Errors: `{"field": ["message"]}`, nested `{"skus": {"0": {"price_type": "..."}}}`, or `{"detail": "..."}`.

### 3.1 Endpoints

| Gigs | Products (and jobs) |
|---|---|
| `GET /catalog/gigs/` list | `GET /catalog/listings/` list |
| `POST /catalog/gigs/` create (`201`, approved by default) | `POST /catalog/listings/` |
| `GET /catalog/gigs/{id}/` details | `GET /catalog/listings/{id}/` |
| `PATCH` / `PUT /catalog/gigs/{id}/` edit and moderate | `PATCH` / `PUT /catalog/listings/{id}/` |
| `DELETE /catalog/gigs/{id}/` soft delete (`204`) | `DELETE /catalog/listings/{id}/` |
| `GET /catalog/gigs/requests/` pending list (cursor) | `GET /catalog/listings/requests/` |
| `POST /catalog/gigs/bulk-moderate/` | `POST /catalog/listings/bulk-moderate/` |
| `POST` / `PATCH /catalog/listing-files/{id}/` (thumbnail and gallery; one API for both kinds) | (same) |

Menu badges: `GET /catalog/gigs/?status=pending&limit=1` and `GET /catalog/listings/?status=pending&limit=1`, read `count` (each panel has its own).

### 3.2 List filters

- **Gigs:** `status` (`draft`, `pending`, `approved`, `rejected`, `changes_requested`), `category`, `seller`, `price_type` (gigs that have an **active**
  package priced that way), `created_from` / `created_to`, `requested_from` / `requested_to` (`YYYY-MM-DD`, inclusive), `search` (title, Bangla title,
  SKU code), `limit` / `offset` (default 20, max 100).
- **Products:** as today (`status`, `catalog_type`, `listing_type`, `category`, `brand`, `seller`, `buyer`, dates, `search`). **Default the Listings
  list to `catalog_type=product`**: until the Job step exists, buyer job requests (`service` + `buyer_request`) still come out of this endpoint, so
  either hide them with that filter or label them "Job request". Never offer a create-job form.
- Pending lists use **cursor pagination** (follow `next` / `previous` exactly; there is no `count`; reset the cursor when a filter changes).

### 3.3 Gig fields

| Field | Notes |
|---|---|
| `category` | **required**, an **active service** category (`GET /catalog/categories/tree/?type=service`) |
| `title`, `description` | **required**. `title_bn`, `description_bn` optional |
| `delivery_days`, `urgent`, `package_includes`, `package_includes_bn`, `available_from`, `available_to` | optional |
| `country`, `state`, `city`, `thana` | optional; one branch of the geography tree (each dropdown filtered by the level above) |
| `currency` | default `BDT` |
| `seller` | optional (admin only): the owner. A gig with no seller is allowed |
| `status`, `note` | admin only; default `approved`. `rejected` / `changes_requested` **require a note** |
| `skus` | the packages (below). **At least one on create** |
| `image_path`, `image_url`, `media` | thumbnail and gallery, **read only here** (changed through the listing-files API, 3.6) |

`catalog_type` and `posted_by_role` are **not needed** (the endpoint sets them). Read only: `id`, `slug`, `price`, `discounted_price` (the **lowest
rate** among active packages, `null` if none), `requested_at`, `status_change_logs`, `info_change_logs`, `created_at`, `updated_at`.

### 3.4 Packages (gig SKUs)

Send them in `skus`. On **create** send the full list; on **update** `skus` **merges by `id`**: an item with an `id` changes only the fields sent, an
item without an `id` adds a package, packages you do not send are untouched. **Packages are never deleted**: hide one with `{"id": n, "is_active":
false}`.

| SKU field | Gig rule |
|---|---|
| `price_type` | **required**: `hourly` \| `daily` \| `weekly` \| `monthly` \| `fixed` (`fixed` = one price for the whole job) |
| `price` | **required** for a new package: the **rate** for that price type (≥ 0) |
| `discounted_price`, `discount_start_date`, `discount_end_date` | optional; discounted price never above price; a date window needs a lower discounted price; end after start |
| `description`, `description_bn` | optional text about the package (**gigs only**) |
| `sku` | optional unique code |
| `is_active` | `false` hides the package |
| read only | `id`, `effective_price`, `is_discount_active`, `reserved_qty` |
| **must stay empty** | `stock_qty` (a gig has no stock) and `variants` (no options). A SKU has **no `duration`**: do not show or send one |

Rules the server enforces (show them on the right row): **one package per price type** (a *hidden* package still holds its price type, so offer "show
it again" instead of adding a second one); at least one package on create; discount rules; unique SKU code. Example create body:

```json
POST /api/v1/catalog/gigs/
{ "category": 29, "title": "Home Deep Cleaning", "title_bn": "হোম ক্লিনিং", "description": "Full-home cleaning by a team of 3.",
  "delivery_days": 2, "package_includes": "Floors, kitchen, bathrooms", "seller": 7,
  "skus": [
    { "price": "500", "discounted_price": "450", "price_type": "hourly", "description": "Hourly cleaning" },
    { "price": "12000", "price_type": "weekly" },
    { "price": "9000", "price_type": "fixed" } ] }
```

Update example (change a rate, add a package, hide one): `PATCH` with
`{"skus": [{"id": 212, "price": "550"}, {"price": "30000", "price_type": "monthly"}, {"id": 213, "is_active": false}]}`.
At the top level of an update **`price` / `stock_qty` are refused** (`400`): prices change only through `skus`. Create and update are **JSON only** (multipart is `415`); pictures and videos go through the listing-files API (3.6) after the save.

**Product SKUs** keep their model (options, stock, `price`, discount) and must **not** send `price_type` or `description` / `description_bn`
(`400` `"Only for gigs."`).

### 3.5 Errors you must map to the right place

| Response | Meaning / where to show it |
|---|---|
| `{"skus": {"0": {"price_type": "This field is required for a gig SKU."}}}` | that package row, price type |
| `{"skus": {"0": {"stock_qty": "A gig has no stock."}}}` / `{"variants": "A gig SKU has no options."}` | should not happen if the form has no such inputs |
| `{"skus": ["Every gig SKU needs its own price type (two SKUs have the same one)."]}` | packages section (general error) |
| `{"skus": {"0": {"discounted_price": "Cannot be higher than price (price is the original price)."}}}` | that row |
| `{"skus": ["A listing needs at least one SKU: ..."]}` | packages section |
| `{"brand": "Not available here."}` (and `model`, `listing_type`, `price_tiers`, ...) | a product-only field was sent to a gig: remove the input |
| `{"catalog_type": ["A seller's service offer is a gig: use the gig endpoints ..."]}` | you posted a service to `/catalog/listings/` |
| `{"title": ["This seller already has a listing with this title. Update that listing instead. (listing #123)"]}` | title field; the rule is one live title per seller **per kind** (a product and a gig may share a title) |
| `{"category": ["This is a product category; ..."]}` / `["This category is inactive."]` | category field |
| `{"note": ["A note is required when rejecting a listing or requesting changes."]}` | moderation dialog |
| `{"city": ["This city does not belong to the selected state."]}` | location fields |
| `404` on a gig / product detail | wrong kind or deleted: show "not found" |
| `401` / `403` | login / "not allowed" |

### 3.6 Files: thumbnail and gallery (4 APIs)

Listing and gig create / update are **JSON only**. The thumbnail (the one cover picture, `image_path` / `image_url`) and the gallery (`media`) use
`multipart/form-data` APIs, the same for a product id or a gig id (a job id is `404`). Never set `Content-Type` yourself (`authFetch` handles `FormData`).

| | Add (first time) | Change |
|---|---|---|
| Admin | `POST /catalog/listing-files/{id}/` | `PATCH /catalog/listing-files/{id}/` |
| Seller | `POST /seller/listing-files/{id}/` | `PATCH /seller/listing-files/{id}/` |

- **POST**: `thumbnail` (optional, one JPG / PNG / WEBP, up to 10 MB, a real image; `400` if the listing already has one: use PATCH) and `media_file`
  (optional, repeat per file; JPG, PNG, WEBP, GIF, MP4, PDF). Nothing is required; an empty POST is allowed. `201`.
- **PATCH**: `remove_thumbnail` (`true`), `thumbnail`, `remove_media_ids` (`4,5` or repeated; ids must be the listing's, else `400`), `media_file`. **The parts are
  independent**: a new `thumbnail` always replaces the old one (no need to send `remove_thumbnail`); `remove_thumbnail=true` alone removes it; the ids are removed and
  the new files added in the same call. `200`. Nothing sent is `200` and changes nothing.
- Response (both): `{"image_path", "image_url", "media": [{id, media_type, media_path, media_url}], "status"}`: update the preview and the gallery from it.
- Errors: `400 {"thumbnail": [...]}`, `400 {"media_file": [...]}`, `400 {"remove_media_ids": [...]}`. All or nothing: on `400` nothing was saved.
- Seller gallery limits: 10 MB per file, 10 files per request, 20 per listing (admin: none).
- **Order of calls on a create form:** `POST` the listing (JSON) first, then `POST` the files with the new id. If the upload fails the listing already
  exists: stay on the edit page, show the error and let the user retry. Do not roll back.
- Deleting a listing or gig removes its thumbnail file on the server; nothing to do in the UI.
- File changes are in the change log (`changed_fields`: `thumbnail`, `media`) and **never change the status** (admin or seller).

### 3.7 Moderation (same on both panels)

`PATCH` `{"status": "approved" | "rejected" | "changes_requested" | "pending" | "draft", "note": "..."}`. `rejected` and `changes_requested`
**need a note**; the note is only read when the status really changes (re-sending the same status does nothing). Show `note` (the current reason) and
`status_change_logs` (newest first: status, note, who, when). Bulk: `POST .../bulk-moderate/` `{"listing_ids": [...], "status": "approved" |
"rejected" | "changes_requested", "note": "..."}` → `{"updated": [...], "skipped": [...]}` (the gig endpoint only touches gigs). Soft delete: `204`, then
the row is gone (`404`). `info_change_logs` (admin only) shows every content change with `previous_data` / `new_data`: for a gig it includes `skus`
entries (price, discount, `price_type`, description, `is_active`) and `thumbnail`.

### 3.8 List rows

Gig row: `id, title, title_bn, slug, category, seller, price, discounted_price, price_type, image_url, status, requested_at, created_at`
(`price` / `price_type` = the lowest rate and what it is for: show e.g. "৳450 / hour"; `fixed` shows as a flat price).
Product row: `id, title, title_bn, slug, catalog_type, listing_type, posted_by_role, category, brand, seller, buyer, price, discounted_price,
image_url, status, requested_at, created_at`. Show `image_url` as the row thumbnail (a placeholder when `null`).

---

## 4. Tasks, in order

### Task 1 — Split the navigation and fix the Listings screens
- Two sidebar entries and route groups: **Listings** and **Gigs**. Listings = products only (no Service option anywhere; Product is the default).
  Gigs = service offers only (Service is the default; no Product option).
- Update `src/lib/listing-api.ts` and the listing form / detail / list: remove `price_type` and `hourly_rate`; never send `price_type` /
  `description` on a product SKU; default the list filter to `catalog_type=product`; show `image_url` in the rows; handle `404` for a gig id.
- Menu badges for both panels (3.1).

### Task 2 — Gigs panel
- API client `src/lib/gig-api.ts` (list, create, retrieve, update, delete, requests, bulk-moderate) and a shared `listing-files-api.ts` (add, change) following the existing
  `*-api.ts` and `use-managed-list.ts` patterns.
- **List:** thumbnail, title (+ Bangla), category, owner, "from" rate with its price type, status badge, dates; filters from 3.2; search; pagination;
  loading / empty / error states; a **Pending** view using the cursor list with "Load more"; bulk select → bulk moderate.
- **Create / edit form:** the fields in 3.3 (service categories only, active only; owner picker optional; location cascade), Bangla fields beside the
  English ones, and the **Packages editor** (Task 3). On edit send **only what changed**, packages with their `id`.
- **Details page:** thumbnail, all fields, packages table (price type, rate, effective rate, discount window and "active now", description / Bangla,
  active), gallery, owner, status + note, **status history** and **change log**. Moderation panel (approve / reject / request changes with a required
  note), soft delete with a confirmation.

### Task 3 — Packages editor (inside the gig form)
- One row per package: **price type** (select of the five values), **price (rate)**, optional discount (+ start / end), description + Bangla
  description, optional SKU code, active toggle. Add row / hide row (never delete a saved package; say so in the UI).
- Do not allow a price type that is already used by another row (including hidden saved ones: offer "Show it again"). Disable the **Add package**
  button when all five price types are used. Label the price with its unit ("per hour", "per day", "per week", "per month", "fixed price").
- No stock, no options, no duration inputs. Show `effective_price` and whether the discount is active right now (read only).
- Validate before sending: at least one package on create, price ≥ 0, discounted price ≤ price, end date after start. Still map server errors from 3.5
  onto the right row.

### Task 4 — Files control (thumbnail and gallery)
- A reusable component for product and gig forms and detail pages: thumbnail preview (`image_url`, or a placeholder) with **Choose**, **Replace**, **Remove**
  (confirm); a gallery grid (images inline, video with a player, documents as links) with **Add files** and a per-file **Remove**.
- Client checks: thumbnail `image/jpeg,image/png,image/webp`, 10 MB; gallery types as in 3.6.
- On a create form enable it only after the first save (then `POST`); on edit send one `PATCH` with what changed (`thumbnail`, `remove_thumbnail`, `remove_media_ids`,
  `media_file`) and update the preview and gallery from the response. Show server errors from the three error keys.

### Task 5 — Cross-cutting
- `401` → clear the session and go to login; `403` → "not allowed" state; `404` → "not found".
- Never set `Content-Type` for `FormData`. Resolve `image_url` / media URLs with `resolveMediaUrl`.
- Treat money (`price`, `discounted_price`, `effective_price`) as strings (`"450.00"`); never rely on JSON number precision.

---

## 5. The seller panel (only when the user asks)

The seller side has the same split: **`/seller/listings/`** (products) and **`/seller/gigs/`** (gigs), each with create, list, details, edit and
`POST` / `PATCH /seller/listing-files/{id}/` (thumbnail and gallery). A seller's new listing or gig is always `pending`; there is no delete and no resubmit button (saving is
resubmitting; changing files does **not** change the status). Lookups: `/seller/lookups/categories/?type=service`.
Full rules: `seller-api-guide.md` sections 6, 6b and 6.8.

---

## 6. Definition of done

- Listings (products only) and Gigs (service offers only) are two separate areas; Product / Service defaults are as described; no screen sends
  `price_type` / `hourly_rate` on a listing or `duration` anywhere.
- A gig can be created, edited (packages by `id`, hide / show), listed with filters, moderated (single, bulk, pending list), viewed with history and
  change log, and deleted.
- The packages editor enforces one package per price type, has no stock / options / duration, and maps every server error to the right row.
- The thumbnail and the gallery can be added, replaced and removed for products and gigs, with previews in lists and details.
- `npm run ci` (lint + typecheck + build) passes; tested in the browser against the running backend with the test accounts.
- Commit locally if you like, **never push** without the user's go-ahead. Update the Phase Tracker (`egoola-document\Egoola_Phase_Tracker.md`, Admin Web
  row 10.1) and report: what is done, what is blocked, any backend bug you found.
