# Brief for the Egoola Web session — admin Product (Listing) panel

Backend done and tested in `egoola-server`: Admin CRUD + moderation for **products**. Build the
**Products** screen (list, create, edit, detail, moderate, delete, thumbnail/media) in **Admin Web**.
Do not push; commit locally only if asked. After building, cross-check every call and response
shape below against your implementation and report any mismatch.

Read first: `egoola-server/docs/admin/listing-module-guide.md` (the full contract — sections 1–8 cover
products; read it fully, the sections below are a summary scoped to products only — gigs and jobs are
separate screens, not part of this brief). Postman: `Egoola-Listing` collection → **Listings**, **Listing
files**, **Brands** folders (already covers every call in this brief — no new collection needed; the
**Gigs**/**Jobs**/**Cleanup** folders are for the other two screens, ignore them here). Run the backend
with `uv run manage.py runserver 8000`; accounts in `docs/test-accounts.md` (admin:
`test.admin@egoola.com` / `Test@12345`).

---

## 1. What this is

A **product** is one row of the shared `listings` table (`catalog_type = product`). It is NOT a gig
(a seller's service offer, `/catalog/gigs/`) or a job (a buyer's work request, `/catalog/jobs/`) — those
are separate screens with their own endpoints; a gig/job id on the product endpoints is `404`.

Everything about a product is managed through two APIs:

1. **`/catalog/listings/`** — full CRUD + moderation (create, retrieve, update, list, soft-delete,
   approve/reject/request-changes, bulk-moderate). JSON only — uploading a file here is `415`.
2. **`/catalog/listing-files/{id}/`** — thumbnail + gallery media, multipart only, a *separate* call
   from create/update. There is no "upload thumbnail on create" — create the product first (JSON),
   then call this endpoint. One endpoint, two verbs: `POST` adds (thumbnail only if none exists yet,
   plus any gallery files), `PATCH` removes/replaces the thumbnail and removes/adds gallery files.

Supporting reference data the product form needs (own existing screens/pickers, not new ones unless
missing): `/catalog/categories/` (product-type, active only), `/catalog/brands/` (active only),
`/catalog/measurements/`, `/catalog/attributes/` + `/catalog/attribute-values/` (for SKU option
pickers — see the [attribute guide](../../attribute-sku-guide.md)), `/public/geography/...` or the
admin geography endpoints for country/state/city/thana.

## 2. The contract

Header: `Authorization: Bearer <admin access token>` everywhere (plain admin or super-admin, no
restriction between them for products). `401` no token, `403` wrong role.

### Products — `/api/v1/catalog/listings/...`

| Call | What it does |
|---|---|
| `POST /catalog/listings/` | create. Default status `approved` (admin-created); `status` can be sent explicitly |
| `GET /catalog/listings/` | list, limit/offset (`count`/`next`/`previous`/`results`, default limit 20) |
| `GET /catalog/listings/requests/` | **pending queue only** (`status=pending`), cursor-paginated (`next`/`previous`, no `count`), newest request first |
| `GET /catalog/listings/{id}/` | detail |
| `PATCH`/`PUT /catalog/listings/{id}/` | edit fields, and/or move `status` (same call — see §4) |
| `DELETE /catalog/listings/{id}/` | soft delete (`204`); vanishes from list/retrieve after |
| `POST /catalog/listings/bulk-moderate/` | approve/reject/request-changes many at once |

List filters: `status`, `catalog_type`, `listing_type`, `category`, `brand`, `seller`, `buyer`,
`created_from`/`created_to`, `requested_from`/`requested_to` (dates, inclusive). Search: title,
Bangla title, brand name, model, SKU code. `requests/` takes the same filters plus `ordering`
(`requested_at`, `created_at`, `title`, `id`).

### Fields (create/update body)

| Field | Notes |
|---|---|
| `category` | id, **required**, must be a `product`-type, active category |
| `catalog_type` | `"product"` — fixed for this screen, cannot change after creation |
| `listing_type` | `general`/`used`/`village`/`retail`/`wholesale`/`brand`, optional; `brand` makes `brand` mandatory |
| `seller` | id, optional — leave unset for an admin-owned listing |
| `title`, `description` | **required**; `title_bn`, `description_bn` optional |
| `brand` | brand id, optional (mandatory if `listing_type = brand`); must be active when newly picked |
| `model`, `origin`(`_bn`), `warranty`(`_bn`), `min_order_qty`, `measurement`, `condition_note`(`_bn`), `attributes` | optional, product-only (service-only fields are `400` here) |
| `country`, `state`, `city`, `thana` | ids, optional, must be on one geography branch |
| `skus` | **required on create** (or use the `price` shortcut) — see §3 |
| `price`, `discounted_price`, `discount_start_date`, `discount_end_date`, `stock_qty`, `sku` | create-only shortcut for one default SKU with no options; `400` on update, and `400` if sent together with `skus` |
| `price_tiers` | optional, quantity pricing — see §3 |
| `status`, `note` | see §4 |
| *(read-only, in every response)* | `id`, `slug`, `brand_name`, `price`, `discounted_price` (cheapest active SKU), `skus[].effective_price`/`is_discount_active`, `media`, `status_change_logs`, `info_change_logs`, `requested_at`, `created_at`, `updated_at` |

List row is lighter: `id, title, title_bn, slug, catalog_type, listing_type, posted_by_role, category,
brand, seller, buyer, price, discounted_price, image_url, status, requested_at, created_at`.

## 3. SKUs, price tiers, and the price shortcut

A product needs at least one SKU (a sellable option combination — Size M + Colour Red — carrying
`price`, `discounted_price`, `stock_qty`). Two ways to send it:

- **Full form**: `"skus": [{ "sku": "...", "price": "...", "discounted_price": "...", "stock_qty": ..., "variants": [{"attribute": id, "attribute_value": id}, ...] }, ...]`. On update, items **merge by `id`**: an item with `id` edits that SKU, one without `id` adds a SKU, a SKU left out of the array is untouched. SKUs are never deleted — hide one with `{"id": 7, "is_active": false}`.
- **Shortcut** (create only, no options): top-level `price` (+ optional `discounted_price`, discount dates, `stock_qty`, `sku`) — becomes one default SKU. Not usable on update; use `skus` there instead.

Rules: `discounted_price` defaults to `price` when omitted, never higher than `price`; a discount only
applies between `discount_start_date`/`discount_end_date`; raising a discount above the (possibly
updated) `price` is `400`. Full SKU/attribute rules: [attribute-sku-guide.md](../../attribute-sku-guide.md).

`price_tiers` (quantity pricing, whole-listing): sending the key **replaces the entire list** (`[]`
clears it); omit the key on PATCH to leave tiers untouched. Each tier: `min_qty`, `max_qty` (`null` =
"and above"), `price`, `discounted_price` (defaults to `price`). Tiers must not overlap and only the
last may be open-ended; `max_qty` below `min_qty`, or a tier's `discounted_price` above its `price`,
is `400`.

## 4. Status / moderation flow

```
draft ──submit──► pending ──approve────────────► approved
                      │
                      ├──reject (note required)────► rejected
                      │
                      └──request changes (note required)──► changes_requested
```

Moderation is the **same `PATCH`** as any other edit — send `{"status": "...", "note": "..."}`.
`note` is required only for `rejected`/`changes_requested`; sending `status` unchanged (or omitting
it) writes no history row and leaves `note` untouched even if one is sent. Every real status change
appends one row to `status_change_logs` (newest first; `Listing.note` always mirrors the latest row's
note, `null` if that row had none). Content edits (not status) append to `info_change_logs` instead —
don't conflate the two timelines in the UI.

**Pending queue**: `GET /catalog/listings/requests/` is the admin's moderation inbox — only
`status=pending`, cursor-paged. Approve/reject/request-changes from here with the normal `PATCH`
above; there is no separate "approve" action endpoint.

**Bulk**: `POST /catalog/listings/bulk-moderate/` with `{"listing_ids": [...], "status": "approved"|"rejected"|"changes_requested", "note": "..."}`. `note` required for reject/changes_requested. Already-at-that-status rows go to `skipped` (no history row); the rest go to `updated`. All-or-nothing transaction.

## 5. Thumbnail and gallery media

Separate from create/update, multipart, same id: `POST`/`PATCH /catalog/listing-files/{id}/`.

| Call | Fields | Behavior |
|---|---|---|
| `POST` | `thumbnail` (file, optional), `media_file` (repeated, optional) | Adds thumbnail only if the listing has none yet (`400` if one exists — use `PATCH` to replace); adds gallery files |
| `PATCH` | `remove_thumbnail` (bool), `thumbnail` (file — always replaces), `remove_media_ids` (comma ids), `media_file` (repeated) | All fields independent/optional; empty body is a 200 no-op |

Response: `{image_path, image_url, media, status}` — `status` never changes from a files call; file
changes are logged to `info_change_logs`, not `status_change_logs`. Old files are deleted from
storage on replace/remove.

## 6. Errors (cheat sheet)

| Case | Error |
|---|---|
| `listing_type: "brand"`, no `brand` | `{"brand": ["A brand listing must select a brand."]}` |
| Inactive/unknown `brand` | `{"brand": ["This brand is inactive."]}` / `["Invalid pk ... - object does not exist."]` |
| No `skus` and no `price` shortcut | `{"skus": ["A listing needs at least one SKU: send `skus`, or `price` for a single default SKU."]}` |
| `skus` + `price` shortcut together | `{"skus": "Send either `skus` or the price shortcut, not both."}` |
| SKU/tier `discounted_price` > `price` | `400` under `skus`/`price_tiers` |
| Plain `price`/`stock_qty` on **update** | `400` — go through `skus` |
| `status: rejected`/`changes_requested` with no `note` | `{"note": ["A note is required when rejecting a listing or requesting changes."]}` |
| Wrong category type (service category on a product) | `400` under `category` |
| Geography not on one branch | `400` under the lower field, e.g. `{"city": ["This city does not belong to the selected state."]}` |
| Bulk: invalid `status` | `{"status": "Must be one of: approved, changes_requested, rejected."}` |
| Thumbnail POST when one exists | `400` — use `PATCH` |
| Multipart on create/update | `415` |
| Gig/job id on this screen | `404` |

## 7. Tasks

1. **API client** (`admin-products-api.ts`): `listProducts` (limit/offset), `listPendingProducts`
   (cursor, `requests/`), `getProduct`, `createProduct`, `updateProduct`, `deleteProduct`,
   `bulkModerate`, `uploadProductFiles` (POST, multipart), `updateProductFiles` (PATCH, multipart).
2. **List screen**: filter bar (status, category, brand, seller, date range, search), table (thumbnail,
   title, category, brand, price/discounted_price, status, requested_at/created_at), limit/offset
   pager, row-select + bulk approve/reject/request-changes action bar, a "Create product" button.
3. **Create/edit form**: category picker (product types only, active), brand picker (active; required
   when `listing_type = brand`), title/description + Bangla, model/origin/warranty, measurement,
   geography cascader (country→state→city→thana), SKU builder (attribute/value variant picker, price,
   discounted price + discount date range, stock) reusing whatever component the attribute/SKU guide
   implies, price-tier builder (min/max qty, price, discounted price, overlap validation client-side
   before submit), min_order_qty, condition_note. No file inputs here — files are a separate step
   after save (point 5).
4. **Detail view**: all fields, SKU table with `effective_price`/`is_discount_active` per row, price
   tiers, thumbnail + gallery, `status_change_logs` timeline, `info_change_logs` timeline (keep the
   two visually distinct), moderation controls (approve/reject/request-changes with a required-note
   dialog on the latter two — don't let it submit empty), delete (confirm, it's a soft delete but
   irreversible from the UI).
5. **Thumbnail/media panel** (on detail, after the product exists): upload thumbnail (disabled/hidden
   once one exists — offer "replace" instead, which is the PATCH path), add gallery files, remove
   gallery files (multi-select → `remove_media_ids`), replace/remove thumbnail.
6. **Pending queue view**: either a filtered list view (`status=pending`) or a dedicated inbox hitting
   `requests/` directly — cursor "load more", same row shape, quick approve/reject actions inline.
7. Entry point: add **Products** to the admin nav (alongside/under the existing Listings entry if one
   already exists — check first, don't duplicate).

## 8. Verify (browser, admin role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Create a product with the `price` shortcut, no brand | `201`, one default SKU, `status: approved` |
| 2 | Create with `listing_type: brand` and no `brand` | `400` under `brand` |
| 3 | Create with two SKUs (Storage × Colour) and overlapping price tiers | SKUs created; tier overlap rejected `400` before SKUs are touched (all-or-nothing) |
| 4 | Edit a SKU's price only (no discount) | `discounted_price` follows the new `price` |
| 5 | Try a plain `{"price": "10.00"}` PATCH | `400` — must go through `skus` |
| 6 | Reject without a note | `400` under `note` |
| 7 | Reject with a note, then re-send the same `rejected` status | first call: `200`, history +1; second call: `200`, no new history row, note unchanged by the second call's `note` |
| 8 | Bulk-approve 3 products, one already approved | `updated` has 2, `skipped` has 1 |
| 9 | Upload a thumbnail, then POST another thumbnail | first `201`; second `400` (use PATCH to replace) |
| 10 | PATCH `remove_thumbnail: true` plus two new `media_file`s in one call | thumbnail cleared, gallery grows by 2 |
| 11 | Open the pending queue (`requests/`), approve one from there | leaves the queue, appears as `approved` in the main list |
| 12 | Soft-delete a product, then retrieve it | `404` |
| 13 | Try to open a gig id or job id on this screen's detail route | `404`, handled without a crash |
| 14 | A non-admin token (if testable from the UI) | handled the same way other admin screens reject it |

Report which cases pass, what you changed, and anything in `listing-module-guide.md` or this brief
that looked wrong, missing, or unclear once you tried it against the real API.
