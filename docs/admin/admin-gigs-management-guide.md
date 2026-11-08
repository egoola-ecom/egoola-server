# Admin Gig Management Guide

Admin-side management for **Gigs** — a seller's service offer (cleaning, photography, logo design, repair). A gig
is a row of the same shared `listings` table as a product, but it has its own endpoints, its own pending list and
its own price model (**packages**, priced by `price_type`, not by options and stock).

Base path: `/api/v1/catalog/gigs/`, plus the shared `listing-files/{id}/` endpoint for the thumbnail/gallery. All
endpoints are **Admin-only** (`Authorization: Bearer <admin access token>`). Another actor's token gets `403`; no
token gets `401`.

> **Products, gigs and jobs are three separate kinds**, one shared `listings` table. `/catalog/listings/` manages
> products (and, for now, job requests via `/catalog/jobs/`). A product id on `/catalog/gigs/` is `404`; a gig id on
> `/catalog/listings/` or `/catalog/jobs/` is `404`. `catalog_type` and `posted_by_role` cannot change after creation.

Related: [`listing-module-guide.md`](listing-module-guide.md) (the product/moderation reference this guide mirrors),
[`../listing-complete-guide.md`](../listing-complete-guide.md) section 14 (the full technical reference — every
error, the order/cart shape, the database migrations), [`../Egoola_Listing_Guide.md`](../Egoola_Listing_Guide.md)
section 12 (plain-language version). Code: `apps/catalog/models.py`, `admin_api/serializers.py` (`GigSerializer`,
`GigListSerializer`), `admin_api/views.py` (`GigViewSet`), `admin_api/filters.py` (`GigFilter`), `kinds.py`.
Postman: `postman/admin/Egoola-Gig.postman_collection.json` (standalone) and `Egoola-Listing` → **Gigs** folder
(same calls, run alongside Listings/Jobs). Smoke: `scripts/smoke/gig_smoke.py` (109 checks),
`scripts/smoke/listing_files_smoke.py` (130 checks, shared with products).

---

## Table of contents

- [1. What a gig is](#1-what-a-gig-is)
- [2. Fields](#2-fields)
- [3. Packages — gig SKUs](#3-packages-gig-skus)
- [4. Create — `POST /catalog/gigs/`](#4-create-post-cataloggigs)
- [5. Retrieve — `GET /catalog/gigs/{id}/`](#5-retrieve-get-cataloggigsid)
- [6. List — `GET /catalog/gigs/`](#6-list-get-cataloggigs)
- [7. Update — `PATCH /catalog/gigs/{id}/`](#7-update-patch-cataloggigsid)
- [8. Moderation (status changes)](#8-moderation-status-changes)
- [9. Bulk moderation — `POST /catalog/gigs/bulk-moderate/`](#9-bulk-moderation-post-cataloggigsbulk-moderate)
- [10. Pending list — `GET /catalog/gigs/requests/`](#10-pending-list-get-cataloggigsrequests)
- [11. Delete — `DELETE /catalog/gigs/{id}/`](#11-delete-delete-cataloggigsid)
- [12. Thumbnail and gallery](#12-thumbnail-and-gallery)
- [13. Product / gig / job separation](#13-product-gig-job-separation)
- [14. Same-title rule](#14-same-title-rule)
- [15. Errors (cheat sheet)](#15-errors-cheat-sheet)
- [16. Testing](#16-testing)

---

## 1. What a gig is

A gig is a **service a seller offers**. It goes through the same moderation as a product (`pending → approved /
rejected / changes_requested`), the same status-change history, the same info-change log, the same pending list
and bulk-moderation mechanics, and the same thumbnail/gallery API — but it is **priced differently**: not by
option+stock SKUs, but by one SKU ("package") per **price type** (hourly/daily/weekly/monthly/fixed). A gig has
**no stock, no options/variants, no brand/model/measurement, and no quantity prices (`price_tiers`)** — sending any
of those is `400`.

A gig is identified by `catalog_type = service` **and** `posted_by_role = seller_offer`. A buyer's work request
(`posted_by_role = buyer_request`) is a different kind — a **job** (`/catalog/jobs/`), not a gig.

## 2. Fields

| Field | Type | Notes |
|---|---|---|
| `seller` | id, optional | admin-created gigs may have no owner |
| `category` | id, **required** | must be an **active** **service** category — a product category here is `400` under `category` |
| `title`, `title_bn` | string | `title` required, `title_bn` optional |
| `description`, `description_bn` | text | `description` required |
| `delivery_days`, `urgent`, `package_includes`(`_bn`), `available_from`, `available_to` | optional | service details |
| `country`, `state`, `city`, `thana` | ids, optional | must be on one branch of the geography tree (state in country, city in state, thana in city), otherwise `400` on the lower level |
| `currency` | string, default `BDT` | |
| `skus` | list, **required on create** (or the `price`+`price_type` shortcut) | the packages — see §3 |
| `status`, `note` | admin only | same rules as a product (§8) |
| *(read only)* | `id`, `slug`, `price`, `discounted_price` (lowest active package's rate), `image_path`, `image_url`, `media`, `status_change_logs`, `info_change_logs`, `requested_at`, `created_at`, `updated_at` | |

**Refused on a gig** (`400`, "Not available for a gig." / "Only for gigs." depending on direction): `listing_type`,
`brand`, `model`, `origin`(`_bn`), `warranty`(`_bn`), `measurement`, `min_order_qty`, `condition_note`(`_bn`),
`attributes`, `price_tiers` — these are product-only. Sending `catalog_type`/`posted_by_role` is fine only when they
match (`service` / `seller_offer`); any other value is `400`, and neither can change after creation.

## 3. Packages — gig SKUs

A gig has no options or stock — its price lives entirely on its SKUs, and each SKU **is** a pricing strategy (a
"package"). A SKU itself has **no duration**: the buyer picks how many hours/days/weeks/months to buy when they
eventually order (not built yet on the buyer side).

| SKU field | Rule |
|---|---|
| `price_type` | **required**: `hourly`, `daily`, `weekly`, `monthly` or `fixed` (one price for the whole job) |
| `price` | the rate for that price type, required for a new package, not negative |
| `discounted_price` | optional, defaults to `price`; never higher than `price` |
| `discount_start_date` / `discount_end_date` | optional window; outside it the buyer pays `price` |
| `description`, `description_bn` | optional text about this package — **gig SKUs only** |
| `stock_qty` | **must be empty** — `400 {"stock_qty": "A gig has no stock."}` otherwise |
| `variants` | **must be empty** — `400 {"variants": "A gig SKU has no options."}` otherwise |
| `sku` (code) | optional, unique across every SKU on the site |
| `is_active` | `false` hides the package. **Packages are never deleted** |
| *(read only)* | `effective_price`, `is_discount_active` |

**One package per price type.** A gig cannot have two `hourly` packages — not in one request, and not against a
package already on the gig, hidden or not: `400 {"skus": ["Every gig SKU needs its own price type (two SKUs have
the same one)."]}`. To bring back a hidden price type, reactivate it (`{"id": ..., "is_active": true}`) instead of
adding a new one.

**A gig needs at least one package.** `{"skus": ["A listing needs at least one SKU: send `skus`, or `price` for a
single default SKU."]}` with neither `skus` nor the shortcut.

**The create shortcut.** For a one-package gig, send `price` and `price_type` (optionally `discounted_price`,
discount dates, `sku`) directly on the gig instead of `skus`. Not accepted together with `skus`
(`{"skus": "Send either `skus` or the price shortcut, not both."}`), and not accepted on update.

**Changing packages (`PATCH` with `skus`).** Same merge rule as a product's SKUs: an item with an `id` changes just
the fields sent; one without an `id` adds a package (needs `price` and `price_type`); a package not mentioned is
left untouched; nothing is ever deleted. `{"skus": [{"id": 212, "price": "550"}]}` changes the rate;
`{"skus": [{"id": 212, "is_active": false}]}` hides it. A package keeps its price type unless a new one is sent,
and the one-per-type rule is re-checked on every save.

## 4. Create — `POST /catalog/gigs/`

```json
POST /catalog/gigs/
{
  "category": 29, "title": "Home Deep Cleaning", "title_bn": "হোম ক্লিনিং",
  "description": "Full-home cleaning by a team of 3.", "delivery_days": 2,
  "package_includes": "Floors, kitchen, bathrooms",
  "skus": [
    { "price": "500", "discounted_price": "450", "price_type": "hourly",
      "description": "Hourly cleaning", "description_bn": "ঘণ্টাভিত্তিক ক্লিনিং" },
    { "price": "12000", "price_type": "weekly" },
    { "price": "9000", "price_type": "fixed" }
  ]
}
```

`201` (shortened; default `status: approved`, `seller: null` when not sent):

```json
{
  "id": 183, "seller": null, "category": 29, "catalog_type": "service", "posted_by_role": "seller_offer",
  "title": "Home Deep Cleaning", "slug": "home-deep-cleaning", "image_path": null, "image_url": null,
  "price": "500.00", "discounted_price": "450.00", "currency": "BDT",
  "skus": [
    { "id": 212, "price": "500.00", "discounted_price": "450.00", "effective_price": "450.00",
      "is_discount_active": true, "price_type": "hourly", "stock_qty": null, "is_active": true,
      "description": "Hourly cleaning", "description_bn": "ঘণ্টাভিত্তিক ক্লিনিং", "variants": [] },
    { "id": 213, "price": "12000.00", "price_type": "weekly", "...": "..." },
    { "id": 214, "price": "9000.00", "price_type": "fixed", "...": "..." }
  ],
  "delivery_days": 2, "package_includes": "Floors, kitchen, bathrooms",
  "status": "approved", "note": null, "requested_at": null, "media": [],
  "status_change_logs": [ { "status": "approved", "creator_type": "admin", "...": "..." } ],
  "info_change_logs": []
}
```

Owned by a seller instead: add `"seller": 5`. Explicit non-default status: `"status": "pending"`, or
`"status": "rejected"` (requires `note`). Images/files are never part of this call (JSON only, multipart is `415`)
— see §12.

## 5. Retrieve — `GET /catalog/gigs/{id}/`

Full detail: every package (active or not, with `effective_price`/`is_discount_active`), `media`, the complete
`status_change_logs` and `info_change_logs` (newest first). Soft-deleted or unknown id, or a product/job id → `404`.

## 6. List — `GET /catalog/gigs/`

| Query | Meaning |
|---|---|
| `status` | `draft`, `pending`, `approved`, `rejected`, `changes_requested` |
| `category`, `seller` | ids — **exact match only**, no sub-category rollup: selecting a parent category returns only gigs filed directly under that exact id, not its children too (unlike the buyer-facing public catalog, which does expand to descendants) |
| `price_type` | gigs with an **active** package priced that way |
| `created_from`, `created_to`, `requested_from`, `requested_to` | dates, `YYYY-MM-DD`, inclusive |
| `search` | title, Bangla title, SKU code |
| `limit`, `offset` | pagination (default limit 20) |

Row is light: `id, title, title_bn, slug, category, seller, price, discounted_price, price_type, image_url, status,
requested_at, created_at` (`price`/`discounted_price`/`price_type` are the lowest-rate active package). Products
and jobs never appear here.

## 7. Update — `PATCH /catalog/gigs/{id}/`

| Goal | Payload | Result |
|---|---|---|
| Change a package's rate | `{"skus": [{"id": 212, "price": "550.00"}]}` | `200` |
| Add a new package | `{"skus": [{"price": "9500", "price_type": "monthly"}]}` | `200`, new SKU added |
| Hide a package | `{"skus": [{"id": 212, "is_active": false}]}` | `200`, kept but inactive |
| Second package of a type already in use | `{"skus": [{"price": "40", "price_type": "hourly"}]}` on a gig with an hourly package | `400` |
| Plain `price`/`price_type` at the top level on update | `{"price": "100.00"}` | `400` — go through `skus` |
| `catalog_type`/`posted_by_role` change | any value | `400` — fixed after creation |
| Unrelated edit | `{"description": "new"}` | `200`; status, note and history unchanged |

## 8. Moderation (status changes)

Identical mechanics to a product (see [`listing-module-guide.md`](listing-module-guide.md) §5.7) — status changes
use the same `PATCH`:

| Step | Payload | Result |
|---|---|---|
| Reject without note | `{"status": "rejected"}` | `400` |
| Reject | `{"status": "rejected", "note": "..."}` | `200`, history +1 |
| Request changes | `{"status": "changes_requested", "note": "..."}` | `200`, history +1 |
| Approve | `{"status": "approved"}` | `200`, `note: null`, history +1 |
| Same status again | `{"status": "approved"}` on an already-approved gig | `200`, no new history row |

`Listing.note` always mirrors the latest `status_change_logs` row; a note sent without a real status change is
ignored. Content/package/thumbnail edits go to `info_change_logs` instead, never to the status timeline.

## 9. Bulk moderation — `POST /catalog/gigs/bulk-moderate/`

```json
{ "listing_ids": [31, 32, 33], "status": "rejected", "note": "Bulk rejected" }
```
`200` → `{ "updated": [31, 32], "skipped": [33] }`. Same rules as the product endpoint: `status` must be
`approved`/`rejected`/`changes_requested`; `note` required for the latter two; already-at-that-status rows are
`skipped` (no history row); all-or-nothing transaction. **Only gig ids are touched** — a product or job id in the
list is silently ignored (not updated, not skipped, not an error).

## 10. Pending list — `GET /catalog/gigs/requests/`

Admin's gig moderation inbox: `status = pending` only, newest request first (`-requested_at`), **cursor**
pagination (`next`/`previous`, no `count`) — separate from the product pending list. Same filters as §6, plus
`ordering` (`requested_at`, `created_at`, `title`, `id`). Row shape = the list row (§6).

## 11. Delete — `DELETE /catalog/gigs/{id}/`

`204`. Soft delete: `deleted_at` is stamped, the row and its history stay, the **thumbnail file is deleted** from
storage (gallery files stay). A second delete or a later retrieve is `404`. The gig's title becomes free again for
that seller to reuse.

## 12. Thumbnail and gallery

Shared endpoint with products, multipart only, same id: `POST`/`PATCH /catalog/listing-files/{id}/`.

| Call | Fields | Behavior |
|---|---|---|
| `POST` | `thumbnail` (optional, `400` if one already exists), `media_file` (repeated, optional) | adds the thumbnail and/or gallery files |
| `PATCH` | `remove_thumbnail`, `thumbnail` (always replaces), `remove_media_ids` (comma ids), `media_file` (repeated) | all independent, empty body is a 200 no-op |

Response: `{image_path, image_url, media, status}` — `status` never changes here; the change is written to
`info_change_logs`, never to `status_change_logs`. Old files are deleted from storage on replace/remove.

## 13. Product / gig / job separation

- `/catalog/listings/` refuses a seller's service offer outright: `400 {"catalog_type": ["A seller's service offer
  is a gig: use the gig endpoints (/catalog/gigs/). ..."]}`.
- A product id, or a job id, on `/catalog/gigs/` is `404` for `GET`/`PATCH`/`DELETE`.
- A gig id on `/catalog/listings/` or `/catalog/jobs/` is `404`.
- `listing-files/{id}/` accepts both a product id and a gig id (never a job id — jobs have no files API).

## 14. Same-title rule

A seller cannot have two **live** gigs with the same title (case and extra spaces ignored):
`400 {"title": ["This seller already has a listing with this title. Update that listing instead. (listing #123)"]}`.
The rule is **per kind** — a product and a gig with the same title from the same seller is fine. An admin deleting
a gig frees its title. Admin-owned gigs (no seller) are not part of this rule.

## 15. Errors (cheat sheet)

| Case | Error |
|---|---|
| Non-service or inactive category | `400` under `category` |
| No `skus` and no `price`+`price_type` shortcut | `{"skus": ["A listing needs at least one SKU: send `skus`, or `price` for a single default SKU."]}` |
| `skus` + shortcut together | `{"skus": "Send either `skus` or the price shortcut, not both."}` |
| Missing `price_type` on a SKU | `{"skus": {"0": {"price_type": "This field is required for a gig SKU."}}}` |
| Unknown `price_type` | `{"skus": {"0": {"price_type": ["\"yearly\" is not a valid choice."]}}}` |
| `stock_qty` sent on a SKU | `{"skus": {"0": {"stock_qty": "A gig has no stock."}}}` |
| `variants` sent on a SKU | `{"skus": {"0": {"variants": "A gig SKU has no options."}}}` |
| Two SKUs with the same `price_type` | `{"skus": ["Every gig SKU needs its own price type (two SKUs have the same one)."]}` |
| SKU `discounted_price` > `price` | `400` under `skus` |
| Plain `price`/`price_type` on update | `{"price": "Prices and stock are changed through `skus`."}` |
| Product-only field sent (`brand`, `price_tiers`, ...) | `{"<field>": "Not available for a gig."}` |
| `status: rejected`/`changes_requested` with no `note` | `{"note": ["A note is required when rejecting a listing or requesting changes."]}` |
| Geography not on one branch | `400` under the lower field |
| Bulk: invalid `status` | `{"status": "Must be one of: approved, changes_requested, rejected."}` |
| Thumbnail POST when one exists | `400` — use `PATCH` |
| Multipart on create/update | `415` |
| Product id or job id on this screen | `404` |
| No token / wrong role | `401` / `403` |

## 16. Testing

| Suite | Result |
|---|---|
| `scripts/smoke/gig_smoke.py` — admin gig API: packages, one-per-price-type, edit by SKU id, list/filters, pending list, bulk moderation, product/gig/job separation | 109 / 109 |
| `scripts/smoke/listing_files_smoke.py` — the 4 listing-files APIs (admin + seller, product + gig) | 130 / 130 |
| `scripts/smoke/seller_gig_smoke.py` — seller's own gig API (for cross-checking what the seller side sends) | 99 / 99 |

Postman: `postman/admin/Egoola-Gig.postman_collection.json` (this guide's calls, standalone) and the **Gigs**
folder of `Egoola-Listing.postman_collection.json` (same calls, run alongside Listings/Jobs in one flow).
