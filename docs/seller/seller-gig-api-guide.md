# Seller Gig (Service) API Guide

Seller-side CRUD for **gigs** — a seller's own rows in the shared `listings` table
(`catalog_type = service`, `posted_by_role = seller_offer`). All endpoints live under
`/api/v1/seller/` and need a **seller access token**
(`Authorization: Bearer <seller access token>`). No token is `401`; an admin or buyer
token is `403`.

> **Products, gigs and jobs.** This guide covers gigs only (`/seller/gigs/`). A
> seller's product is on `/seller/listings/` — see
> [`seller-listing-api-guide.md`](seller-listing-api-guide.md). Bidding on a buyer's
> job request is a different flow — `/seller/jobs/...`, `/seller/bids/...` — see
> [`seller-job-bidding-api-guide.md`](seller-job-bidding-api-guide.md). See
> [`../Egoola_Listing_Guide.md`](../Egoola_Listing_Guide.md) section 12 for the
> plain-language tour, and [`../listing-complete-guide.md`](../listing-complete-guide.md)
> section 14 for the full field/package reference shared with the admin side.
>
> The admin side of this same table (moderation, bulk actions) is
> [`../admin/admin-gigs-management-guide.md`](../admin/admin-gigs-management-guide.md).

Related files: `apps/catalog/seller/{urls,views,serializers,filters}.py`,
`apps/catalog/listing_files.py`, `apps/catalog/models.py`; Postman collection
`postman/seller/Egoola-SellerApp.postman_collection.json` → **Seller gigs** folder.
Smoke test: `scripts/smoke/seller_gig_smoke.py`.

---

## Table of contents

- [1. Who can use this, and on what](#1-who-can-use-this-and-on-what)
- [2. What a gig is, and how it's priced](#2-what-a-gig-is-and-how-its-priced)
- [3. Lookups for the form (read-only)](#3-lookups-for-the-form-read-only)
- [4. Create — `POST /seller/gigs/`](#4-create-post-sellergigs)
- [5. Same-title rule](#5-same-title-rule)
- [6. List — `GET /seller/gigs/`](#6-list-get-sellergigs)
- [7. Detail — `GET /seller/gigs/{id}/`](#7-detail-get-sellergigsid)
- [8. Edit — `PATCH`/`PUT /seller/gigs/{id}/`](#8-edit-patchput-sellergigsid)
- [9. Thumbnail and gallery files](#9-thumbnail-and-gallery-files)
- [10. Delete](#10-delete)
- [11. Errors (cheat sheet)](#11-errors-cheat-sheet)
- [12. Not built yet](#12-not-built-yet)

---

## 1. Who can use this, and on what

Only a seller who **can operate** — verified **and** active. Everyone else gets `403`
with a message that says why:

- not approved yet: `{"detail": "Your seller application is not approved yet. You can only edit your profile until an admin approves it."}`
- locked: `{"detail": "Your seller account is locked. Contact support."}`

A seller sees and changes **only their own, non-deleted gigs**. Another seller's gig,
an admin-owned gig, a buyer's job request, and the seller's own products are all `404`
on these endpoints. **A seller can never delete a gig** (`DELETE` is `405` — only an
admin deletes).

## 2. What a gig is, and how it's priced

A gig is a service the seller offers (cleaning, photography, repair). It has the same
moderation as a product (`pending → approved / rejected / changes_requested`, a status
history) but a different price model: **packages**. Every package is a SKU with a
`price_type` (`hourly`, `daily`, `weekly`, `monthly` or `fixed`) and a `price` (the rate
for that unit). A package has **no duration, no options, no stock and no quantity
prices** — the buyer chooses how many hours/days/weeks/months when ordering and pays
the rate times that number. At most **one package per price type**; a hidden package
(`is_active: false`) still holds its price type — reactivate it instead of adding a new
one. Full field/package reference:
[`../listing-complete-guide.md`](../listing-complete-guide.md) section 14.

## 3. Lookups for the form (read-only)

Same lookups as products, filtered to services: `GET /seller/lookups/categories/?type=service`.
There is no brand, measurement or attribute lookup for a gig. Country/state/city/thana
for the place fields come from the public geography lists.

## 4. Create — `POST /seller/gigs/`

JSON only (multipart is `415`; files are a separate call — section 9). The new gig is
**always `pending`**, owned by the logged-in seller, `posted_by_role = seller_offer`.
**Not accepted** (ignored if sent): `seller`, `buyer`, `posted_by_role`, `status`,
`requested_at`, and `note` on create. `catalog_type` is not needed — it's always
`service` here.

Required: `category` (active, a **service** category), `title`, `description`, and
either `skus` (the packages, at least one) or `price` + `price_type` (a shortcut for one
default package). Optional: `delivery_days`, `urgent`, `package_includes` (+`_bn`),
`available_from`, `available_to`, Bangla fields, place fields.

```json
POST /api/v1/seller/gigs/
{ "category": 29, "title": "Logo Design", "description": "A logo in 3 days.", "delivery_days": 3,
  "skus": [ { "price": "1500", "price_type": "fixed", "description": "One logo, two revisions" },
            { "price": "400", "price_type": "hourly" } ] }
```

`201`: the gig with `"status": "pending"`, the two packages (a fixed 1500 and an hourly
400), and a status history with the seller's creation entry. `price` /
`discounted_price` on the gig are the **lowest rate** among the active packages,
read-only. The seller's response has no `seller`, `buyer`, `posted_by_role` or
`info_change_logs` (admin-only).

For a single package, send `price` and `price_type` (and optionally
`discounted_price`, discount dates, `sku`) on the gig itself instead of `skus` — never
both; the shortcut is not accepted on update.

## 5. Same-title rule

A seller **cannot have two live gigs with the same title** (case and extra spaces
ignored). If they try, they must update the existing one instead:

```json
400 { "title": ["You already have a listing with this title. Update the existing listing instead. (listing #681)"] }
```

A product with the same title is fine (the rule is per `catalog_type`), and so is
another seller's gig. An admin deleting a gig frees its title.

## 6. List — `GET /seller/gigs/`

Limit/offset pagination (`count`, `next`, `previous`, `results`; default 20, max 100).

| Param | Example | Meaning |
|---|---|---|
| `status` | `=rejected` | `pending`, `approved`, `rejected`, `changes_requested`, `draft` |
| `category` | `=29` | id, exact match |
| `price_type` | `=hourly` | gigs with an **active** package priced that way |
| `created_from`, `created_to` | `=2026-10-01` | creation date, inclusive, `YYYY-MM-DD` |
| `requested_from`, `requested_to` | `=2026-10-01` | the date it joined the pending list |
| `search` | `=logo` | title, Bangla title, SKU code |
| `ordering` | `=title` | `created_at`, `updated_at`, `requested_at`, `title`, `status`, `id`; `-` reverses |
| `limit`, `offset` | `limit=20` | paging |

List row: `id, title, title_bn, slug, category, price, discounted_price, price_type,
image_url, status, note, requested_at, created_at, updated_at`.

## 7. Detail — `GET /seller/gigs/{id}/`

Same shape as the create response: packages, media and the **status history**
(`status`, `note`, `creator_type`, `created_at`, not which admin). A product id here is
`404`. The seller does **not** get the admin-only info change log.

## 8. Edit — `PATCH`/`PUT /seller/gigs/{id}/`

Send only what changes (`PATCH`). Same fields as create, except the price shortcut —
change packages through `skus` with the package `id` (`{"skus": [{"id": 212, "price": "550"}]}`);
a package is hidden with `"is_active": false`, never deleted. Same merge rule as a
product's SKUs: an item with an `id` changes only the fields sent, an item without one
adds a package, a package not mentioned is left alone.

**What the save does to the status** (same rule as products — saving is resubmitting,
there is no separate Resubmit button):

| The gig is | A seller's save (even an empty `{}`) does |
|---|---|
| `pending` | stays `pending` |
| `approved` | stays `approved`, whatever changes (text, packages, prices). The admin sees it in the info change log |
| `rejected`, `changes_requested` | goes back to `pending`, `requested_at` = now (top of the admin's pending gig list) |

`status` can never be set by a seller. The `note` sent when saving a rejected /
changes-requested gig is the seller's message to the reviewer (omitting it clears it);
in any other state it is ignored.

## 9. Thumbnail and gallery files

Same endpoint and rules as a product's (see
[`seller-listing-api-guide.md`](seller-listing-api-guide.md) section 8):
`POST`/`PATCH /seller/listing-files/{id}/` for a gig id of mine. Never changes the
status — only saving the gig itself (section 8) resubmits it. Full rules:
[`../listing-complete-guide.md`](../listing-complete-guide.md) section 15.

## 10. Delete

Not available to a seller. `DELETE /seller/gigs/{id}/` is `405`. Only an admin can
delete (soft delete) a gig.

## 11. Errors (cheat sheet)

| What went wrong | Response |
|---|---|
| no token / admin or buyer token | `401` / `403` |
| a product-only field (`listing_type`, `brand`, `model`, `attributes`, `price_tiers`, ...) | `400` (not available on a gig) |
| a product id on this endpoint | `404` |
| seller cannot operate (pending, rejected, paused) | `403` with the message in section 1 |
| another seller's gig, or an admin's | `404` |
| `DELETE` | `405` |
| same title as one of mine | `400` `{"title": ["You already have a listing with this title. Update the existing listing instead. (listing #681)"]}` |
| no `price_type` on a package | `400` `{"skus": {"0": {"price_type": "This field is required for a gig SKU."}}}` |
| `stock_qty` or `variants` sent on a package | `400` (a gig has no stock, no options) |
| two packages with the same `price_type` | `400` `{"skus": ["Every gig SKU needs its own price type (two SKUs have the same one)."]}` |
| no `skus` and no `price` on create | `400` `{"skus": ["A listing needs at least one SKU: send `skus`, or `price` for a single default SKU."]}` |
| `skus` together with the shortcut | `400` `{"skus": "Send either `skus` or the price shortcut, not both."}` |
| `price` or `stock_qty` on an edit | `400` `{"price": "Prices and stock are changed through `skus`."}` |
| the same SKU code twice, or one another listing uses | `400` `{"skus": {"0": {"sku": "A SKU with this code already exists."}}}` |
| negative price; discount above price | `400` on the field |
| city not in the state | `400` `{"city": ["This city does not belong to the selected state."]}` |
| a file of the wrong type, over 10 MB, or too many | `400` `{"media_file": [...]}` |

## 12. Not built yet

- Buying or hiring a gig (cart, orders, payments) and the buyer's gig browsing: Phase 4.
- The seller's hire requests **on a gig** (accept, decline, deliver — a direct hire,
  separate from job bidding, which is built: see
  [`seller-job-bidding-api-guide.md`](seller-job-bidding-api-guide.md)).
- A link from categories to gig packages, per-package delivery time, restoring a
  deleted gig, a gig draft.
