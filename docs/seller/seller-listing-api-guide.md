# Seller Listing (Product) API Guide

Seller-side CRUD for **products** — a seller's own rows in the shared `listings` table
(`catalog_type = product`). All endpoints live under `/api/v1/seller/` and need a
**seller access token** (`Authorization: Bearer <seller access token>`). No token is
`401`; an admin or buyer token is `403`.

> **Products, gigs and jobs.** This guide covers products only (`/seller/listings/`).
> A seller's service offer is a **gig** — separate endpoints, `/seller/gigs/` — and a
> service body sent here is `400`. Bidding on a buyer's job request is a different
> flow — `/seller/jobs/...` — not covered here. See
> [`../Egoola_Listing_Guide.md`](../Egoola_Listing_Guide.md) for the plain-language
> tour of all three, and [`../listing-complete-guide.md`](../listing-complete-guide.md)
> for the full field/SKU/attribute reference shared with the admin side.
>
> The admin side of this same table (moderation, bulk actions, brands) is
> [`../admin/listing-module-guide.md`](../admin/listing-module-guide.md).

Related files: `apps/catalog/seller/{urls,views,serializers,filters}.py`,
`apps/catalog/listing_files.py`, `apps/catalog/models.py`; Postman collection
`postman/seller/Egoola-SellerApp.postman_collection.json` → **Seller listings** folder.

---

## Table of contents

- [1. Who can use this, and on what](#1-who-can-use-this-and-on-what)
- [2. Lookups for the form (read-only)](#2-lookups-for-the-form-read-only)
- [3. Create — `POST /seller/listings/`](#3-create-post-sellerlistings)
- [4. Same-title rule](#4-same-title-rule)
- [5. List — `GET /seller/listings/`](#5-list-get-sellerlistings)
- [6. Detail — `GET /seller/listings/{id}/`](#6-detail-get-sellerlistingsid)
- [7. Edit — `PATCH`/`PUT /seller/listings/{id}/`](#7-edit-patchput-sellerlistingsid)
- [8. Thumbnail and gallery files](#8-thumbnail-and-gallery-files)
- [9. Delete](#9-delete)
- [10. Errors (cheat sheet)](#10-errors-cheat-sheet)
- [11. Notes for the front-end team](#11-notes-for-the-front-end-team)

---

## 1. Who can use this, and on what

Only a seller who **can operate** — verified **and** active. Everyone else gets `403`
with a message that says why:

- not approved yet: `{"detail": "Your seller application is not approved yet. You can only edit your profile until an admin approves it."}`
- locked: `{"detail": "Your seller account is locked. Contact support."}`

A seller sees and changes **only their own, non-deleted products**. Another seller's
listing, an admin-owned listing, a buyer's job request, and the seller's own gigs are
all `404` on these endpoints. **A seller can never delete a listing** (`DELETE` is
`405` — only an admin deletes).

## 2. Lookups for the form (read-only)

All need the same seller token, return **only active** items, and are paged like the
geography lists (`limit` default 500, max 1000).

| Endpoint | Rows | Filters |
|---|---|---|
| `GET /seller/lookups/categories/` | `id, type, parent, name, name_bn, slug, sort_order` | `type` (`product` \| `service`), `parent`, `search` |
| `GET /seller/lookups/brands/` | `id, name, slug` | `search` |
| `GET /seller/lookups/measurements/` | `id, name, slug, symbol` | `search` |
| `GET /seller/lookups/attributes/` | `id, name, name_bn, values[{id, name, name_bn}]` | `search` |

```json
GET /api/v1/seller/lookups/categories/?type=product&limit=2
{ "count": 11, "next": ".../categories/?limit=2&offset=2&type=product", "previous": null,
  "results": [ { "id": 18, "type": "product", "parent": null, "name": "Electronics", "name_bn": "", "slug": "electronics", "sort_order": 1 },
               { "id": 25, "type": "product", "parent": 24, "name": "Furniture", "name_bn": "", "slug": "furniture", "sort_order": 1 } ] }

GET /api/v1/seller/lookups/attributes/        (one attribute with its active values)
{ "id": 22, "name": "Colour", "name_bn": "রং", "values": [ { "id": 55, "name": "Black", "name_bn": "কালো" }, { "id": 56, "name": "White", "name_bn": "সাদা" } ] }
```

Country/state/city/thana for the place fields come from the public geography lists, not
from a seller-specific endpoint. A category must match the listing's `catalog_type`
(`product`) and be active, or it's `400`. All lookups are `GET`-only: `POST` is `405`.

## 3. Create — `POST /seller/listings/`

JSON only (multipart is `415`; files are a separate call — section 8). The new listing
is **always `pending`**, owned by the logged-in seller, `posted_by_role = seller_offer`.
**Not accepted** (ignored if sent): `seller`, `buyer`, `posted_by_role`, `status`,
`requested_at`, and `note` on create.

Required: `category`, `catalog_type`, `title`, `description`, and either `skus` or a
`price` (a shortcut for one default SKU). Everything else is optional. Full field
reference: [`../listing-complete-guide.md`](../listing-complete-guide.md) section 6.1.

| Group | Fields |
|---|---|
| Basics | `category`, `catalog_type` (optional — always `product` here; `service` is `400`), `listing_type`, `title`, `description` |
| Bangla (all optional) | `title_bn`, `description_bn`, `condition_note_bn`, `warranty_bn`, `origin_bn` |
| Product | `brand` (required for `listing_type: brand`), `model`, `origin`, `warranty`, `measurement`, `min_order_qty`, `condition_note`, `attributes` (JSON specs) |
| Place | `country`, `state`, `city`, `thana` (must be on one geography branch) |
| Price and stock | `skus` (list: `sku`, `price`, `discounted_price`, discount dates, `stock_qty`, `is_active`, `variants`), **or** the create-only shortcut `price`, `discounted_price`, `discount_start_date`, `discount_end_date`, `stock_qty`, `sku` — not both together |
| Quantity prices | `price_tiers` (list of `min_qty`, `max_qty`, `price`, `discounted_price`) |

```json
POST /api/v1/seller/listings/
{ "category": 18, "catalog_type": "product", "listing_type": "general",
  "title": "Cotton T-Shirt", "title_bn": "সুতির টি-শার্ট",
  "description": "Soft cotton t-shirt.", "description_bn": "নরম সুতির টি-শার্ট।",
  "origin": "Bangladesh", "origin_bn": "বাংলাদেশ",
  "price": "500", "discounted_price": "450", "stock_qty": 20, "sku": "TEE-CAP-001" }
```

`201`:

```json
{ "id": 681, "category": 18, "catalog_type": "product", "listing_type": "general",
  "title": "Cotton T-Shirt", "title_bn": "সুতির টি-শার্ট", "slug": "cotton-t-shirt",
  "description": "Soft cotton t-shirt.", "description_bn": "নরম সুতির টি-শার্ট।",
  "origin": "Bangladesh", "origin_bn": "বাংলাদেশ", "currency": "BDT",
  "price": "500.00", "discounted_price": "450.00",
  "skus": [ { "id": 593, "sku": "TEE-CAP-001", "price": "500.00", "discounted_price": "450.00", "effective_price": "450.00",
              "is_discount_active": true, "stock_qty": 20, "is_active": true, "variants": [] } ],
  "status": "pending", "note": null, "requested_at": "2026-10-12T09:41:03.595364+06:00",
  "price_tiers": [], "media": [],
  "status_change_logs": [ { "id": 1119, "status": "pending", "note": null, "creator_type": "seller", "created_at": "2026-10-12T09:41:03.599409+06:00" } ],
  "created_at": "2026-10-12T09:41:03.596790+06:00", "updated_at": "2026-10-12T09:41:03.596790+06:00",
  "...": "plus the other fields, null when empty" }
```

The seller's response has **no** `seller`, `buyer`, `posted_by_role` or
`info_change_logs` (admin-only). `price` / `discounted_price` are read-only — the
cheapest active SKU's values. Options (sizes, colours...) are sent as `skus` with
`variants` (`attribute` + `attribute_value` ids from the attributes lookup); one SKU
per combination — full rules in
[`../attribute-sku-guide.md`](../attribute-sku-guide.md).

## 4. Same-title rule

A seller **cannot have two listings with the same title** (case and extra spaces don't
matter). If they try, they must update the existing one instead:

```json
400 { "title": ["You already have a listing with this title. Update the existing listing instead. (listing #681)"] }
```

True even when the earlier listing was **rejected** — the seller updates that listing
(section 7), they cannot get around it by creating a new one since they cannot delete.
Another seller may use the same title. A product and a gig of the same seller may also
share a title (the rule is per `catalog_type`). An admin deleting a listing frees its
title.

## 5. List — `GET /seller/listings/`

Limit/offset pagination (`count`, `next`, `previous`, `results`; default limit 20, max
100), newest first.

| Param | Example | Meaning |
|---|---|---|
| `status` | `=rejected` | `pending`, `approved`, `rejected`, `changes_requested`, `draft` |
| `listing_type` | `=used` | the six product formats |
| `category`, `brand` | `category=18` | ids, exact match |
| `created_from`, `created_to` | `=2026-10-01` | creation date, inclusive, `YYYY-MM-DD` |
| `requested_from`, `requested_to` | `=2026-10-01` | the date it joined the pending list (creation, or the last time it went back to pending) |
| `search` | `=cotton` | title, Bangla title, SKU code, brand name |
| `ordering` | `=title` | `created_at`, `updated_at`, `requested_at`, `title`, `status`, `id`; `-` reverses |
| `limit`, `offset` | `limit=20` | paging |

```json
{ "count": 1, "next": null, "previous": null,
  "results": [ { "id": 681, "title": "Cotton T-Shirt", "title_bn": "সুতির টি-শার্ট", "slug": "cotton-t-shirt",
                 "catalog_type": "product", "listing_type": "general", "category": 18, "brand": null,
                 "price": "500.00", "discounted_price": "450.00", "status": "pending", "note": null,
                 "requested_at": "2026-10-12T09:41:03.595364+06:00",
                 "created_at": "2026-10-12T09:41:03.596790+06:00", "updated_at": "2026-10-12T09:41:03.596790+06:00" } ] }
```

## 6. Detail — `GET /seller/listings/{id}/`

Same shape as the create response: SKUs with options, price tiers, media and the
**status history**. The status history shows `status`, `note`, `creator_type`
(`seller` or `admin`) and `created_at`, but **not which admin**. The seller does
**not** get the admin-only info change log.

## 7. Edit — `PATCH`/`PUT /seller/listings/{id}/`

Send only what changes (`PATCH`). Same fields as create, **except** the price
shortcut — change prices and stock through `skus` with the SKU `id`
(`{"skus": [{"id": 593, "price": "550", "stock_qty": 99}]}`); a SKU is hidden with
`"is_active": false`, never deleted. `price_tiers`, when sent, replaces the whole list.

**What the save does to the status:**

| The listing is | A seller's save (even an empty `{}`) does |
|---|---|
| `pending` | stays `pending`; `requested_at` unchanged |
| `approved` | stays `approved`, whatever content/SKU/price/stock changes are sent; the admin sees the change in the (admin-only) info change log |
| `rejected`, `changes_requested` (or an admin-made `draft`) | goes back to **`pending`**, `requested_at` = now. **There is no separate Resubmit button — saving is resubmitting** |

`status` can never be set by a seller (silently ignored). For a rejected listing,
`note` is the admin's reason, read-only to the seller until they save: a `note` sent
while saving a `rejected`/`changes_requested` listing becomes the **seller's message
to the reviewer** (omitting it clears it); in any other state `note` on the request is
ignored. The admin's own reason stays in `status_change_logs`, never overwritten.

```json
GET /api/v1/seller/listings/681/        (after an admin rejected it)
{ "id": 681, "status": "rejected", "note": "Please add a clear photo.", "requested_at": "2026-10-12T09:41:03.595364+06:00",
  "status_change_logs": [ { "id": 1120, "status": "rejected", "note": "Please add a clear photo.", "creator_type": "admin",  "created_at": "2026-10-12T09:41:03.925444+06:00" },
                          { "id": 1119, "status": "pending",  "note": null,                        "creator_type": "seller", "created_at": "2026-10-12T09:41:03.599409+06:00" } ] }

PATCH /api/v1/seller/listings/681/
{ "description": "Soft cotton t-shirt, now with size chart.", "note": "Added a size chart." }
200 { "id": 681, "status": "pending", "note": "Added a size chart.", "requested_at": "2026-10-12T09:41:04.174396+06:00",
      "status_change_logs": [ { "id": 1121, "status": "pending", "note": "Added a size chart.", "creator_type": "seller", "created_at": "..." },
                              { "id": 1120, "status": "rejected", "note": "Please add a clear photo.", "creator_type": "admin", "created_at": "..." },
                              { "id": 1119, "status": "pending", "note": null, "creator_type": "seller", "created_at": "..." } ] }
```

The row is locked (`select_for_update`) for the whole save, so an admin decision made
at the same moment cannot be silently overwritten by an older copy of the listing.

On the admin side the resubmitted listing is back at the top of the pending queue
(`requested_at` = now).

## 8. Thumbnail and gallery files

Create and edit above are **JSON only** (multipart is `415`). Files use a separate
endpoint, `/seller/listing-files/{id}/`, for a product or gig id of mine (`404` for
anyone else's; still needs a seller who can operate):

- `POST /seller/listing-files/{id}/`: add files. `thumbnail` (optional; `400` if the
  listing already has one — use `PATCH` to replace) and `media_file` (optional,
  repeated). An empty request is allowed. `201`.
- `PATCH /seller/listing-files/{id}/`: change files. `remove_thumbnail` (`true`),
  `thumbnail` (a new one always replaces the old, even without `remove_thumbnail`),
  `remove_media_ids` (`4,5` or repeated; must be this listing's own, else `400`),
  `media_file` (repeated). All parts independent — ids removed and new files added in
  the same call. `200`.

Response: `{"image_path", "image_url", "media": [{id, media_type, media_path,
media_url}], "status"}`. Thumbnail: JPG, PNG or WEBP, up to 10 MB. Gallery: JPG, PNG,
WEBP, GIF, MP4, PDF; 10 MB each; at most 10 per request and 20 per listing. If any part
of the request is refused, nothing is saved; old files are deleted from storage only
after a successful replace/remove.

This call is written to the admin's info change log and **never changes the status** —
a rejected product stays rejected after a files-only change; only saving the listing
itself (section 7) resubmits it. Full rules:
[`../listing-complete-guide.md`](../listing-complete-guide.md) section 15.

## 9. Delete

Not available to a seller. `DELETE /seller/listings/{id}/` is `405`. Only an admin can
delete (soft delete) a listing.

## 10. Errors (cheat sheet)

| What went wrong | Response |
|---|---|
| no token / admin or buyer token | `401` / `403` |
| `catalog_type: "service"`, or a service-only field (`delivery_days`, `urgent`, `package_includes`, ...), or a gig SKU field (`price_type`, `description`) | `400` (services are gigs: `/seller/gigs/`) |
| a gig id on this endpoint | `404` |
| seller cannot operate (pending, rejected, paused) | `403` with the message in section 1 |
| another seller's listing, or an admin's | `404` |
| `DELETE` | `405` |
| same title as one of mine | `400` `{"title": ["You already have a listing with this title. Update the existing listing instead. (listing #681)"]}` |
| no `skus` and no `price` | `400` `{"skus": ["A listing needs at least one SKU: send `skus`, or `price` for a single default SKU."]}` |
| `skus` and `price` shortcut together | `400` `{"skus": "Send either `skus` or the price shortcut, not both."}` |
| `price` or `stock_qty` on an edit | `400` `{"price": "Prices and stock are changed through `skus`."}` |
| category of the wrong type or inactive | `400` `{"category": [...]}` |
| `listing_type: brand` without `brand`; an inactive brand | `400` `{"brand": [...]}` |
| inactive attribute value in `variants` | `400` on `skus` |
| negative price; discount above price | `400` on the field |
| the same SKU code twice, or one another listing uses | `400` `{"skus": [...]}` |
| overlapping price tiers | `400` `{"price_tiers": [...]}` |
| city not in the state | `400` `{"city": ["This city does not belong to the selected state."]}` |
| a file of the wrong type, over 10 MB, or too many | `400` `{"media_file": [...]}` |

## 11. Notes for the front-end team

- Use `brand` (id); the Brand dropdown comes from `GET /seller/lookups/brands/`
  (already active-only — no extra filter needed).
- `price` / `discounted_price` on the list/detail are the cheapest active SKU
  ("from ..."); show a SKU's own `price` struck through only when its
  `effective_price` is lower, and hide SKUs with `is_active: false`.
- Build the option pickers (Size, Colour ...) from `skus[].variants`; see
  [`../attribute-sku-guide.md`](../attribute-sku-guide.md).
- `status_change_logs` is the only timeline a seller gets — there is no
  `info_change_logs` on this side, don't try to render one.
- **There is no "resubmit" button to build** — editing a `rejected` or
  `changes_requested` listing and saving it *is* the resubmit. Make that obvious in
  the UI (e.g. the save button reads "Save & resubmit" when the listing is in one of
  those two states).
- `listing_type = brand` → mark the Brand dropdown as required, client-side, before
  submit.
- There is no delete action to wire up on this screen.
