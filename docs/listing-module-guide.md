# Listing Module — Implementation & API Guide

Admin-side Listing management for Egoola: one shared Listing system for every
listing format (general, used, village, retail, wholesale, brand) and for
services, plus the **Brand** list that listings pick from, plus moderation with
a full status-change history.

All endpoints live under `/api/v1/catalog/` and are **Admin-only**
(`Authorization: Bearer <admin access token>`). Another actor's token gets
`403`; no token gets `401`.

Related files: `apps/catalog/models.py`, `serializers.py`, `views.py`,
`urls.py`, `admin.py`; migrations `0004`–`0007`; Postman collection
`docs/Egoola-Listing.postman_collection.json`.

---

## 1. What is in this module

| Resource | Endpoints | Notes |
|---|---|---|
| Brand | create, update, list, delete | New table `brands` |
| Listing | create, retrieve, update, list, delete (soft) | One table `listings` for every format |
| Listing moderation | status change through PATCH, `bulk-moderate` | Full history in `status_change_logs` |
| Price tiers | nested inside Listing | Table `listingPriceTiers` |
| Media | nested inside Listing (multipart) | Table `listingMedia` |

Not included (left as they were): **Attribute, Color and Origin** have no table
or CRUD yet. `Listing.color`, `colors`, `origin` and `attributes` still work as
before.

---

## 2. Database

### 2.1 `brands` (new)

| Column | Type | Notes |
|---|---|---|
| id | bigint PK | |
| name | varchar(255) | |
| slug | varchar(255), **unique across the project** | generated from `name` |
| isActive | boolean, default `true` | |
| createdBy / creatorType / creatorName | audit | stamped from the Admin token |
| updatedBy / updaterType / updaterName | audit | |
| createdAt / updatedAt | timestamps | |

### 2.2 `listings` — what changed

| Change | Detail |
|---|---|
| `brand` (text) → `brandId` | FK to `brands`, nullable, `PROTECT` (a used brand can't be deleted). Old free-text values were not carried over. |
| `oldPrice` → `discountedPrice` | `price` is always the original price. `discountedPrice` is the price charged: never null, never higher than `price`. When no discount is given it equals `price`. |
| `sellerId`, `buyerId` | Both optional. Admin-created listings can have neither. Never both. |
| `status` | `draft`, `pending`, `approved`, `rejected`, `changes_requested` |
| `note` | Note of the **latest** status change only (null if that change had no note) |
| `deletedAt` | Soft delete marker |

### 2.3 `listingPriceTiers` — what changed

Added `discountedPrice` (never null; equals the tier's `price` when no discount is given, never higher).

### 2.4 `listingStatusChangeLogs`

One row for every status change (including the creation of the listing):
`listingId`, `status`, `note`, `createdBy`, `creatorType`, `creatorName`,
`createdAt`. Rows are never edited or removed.

Migrations: `0004` (moderation fields, soft delete), `0005` (rename to
`note` / `ListingStatusChangeLog`), `0006` (brands, `brandId`,
`discountedPrice`), `0007` (`discountedPrice` never null: existing rows backfilled with `price`).

---

## 3. Business rules

1. **Owner is optional.** `seller` and `buyer` can both be omitted (Admin-created).
   A listing never has both. `posted_by_role = seller_offer` cannot have a
   buyer; `buyer_request` cannot have a seller.
2. **Default status.** Created by an Admin → `approved`. Created by anyone else
   (future seller self-service) → `pending`. Sending `status` explicitly wins.
3. **Brand.**
   - `brand` is the **id** of a Brand. No free text.
   - `listing_type = brand` → `brand` is mandatory.
   - Any other `listing_type` → `brand` is optional.
   - A newly picked brand must be active. A brand that was deactivated *after*
     it was attached does not block later edits.
4. **Price.** `price` = original price. `discounted_price` is the price charged.
   - Not sent (or sent as `null`) → it is set to `price` (no discount).
   - Sent → it must not be higher than `price` (higher → `400`; equal is fine).
   - Same rules on each price tier (tier `price` → tier `discounted_price`).
   - When you update only `price` on a listing that has no discount
     (`discounted_price == price`), `discounted_price` follows the new price.
     A listing with a real discount keeps it; if the new `price` would fall
     below that discount → `400`.
   - Example: `price = 150.00`, `discounted_price = 120.00`. Without
     `discounted_price`: `price = 150.00`, `discounted_price = 150.00`.
5. **Notes and history.**
   - `note` is **required** when `status` is `rejected` or `changes_requested`,
     optional otherwise.
   - Every status change writes one history row.
   - `Listing.note` always equals the note of the **latest** change. If the
     latest change had no note, it is `null`. Older notes stay in
     `status_change_logs`.
   - An update that does not send `status` (or sends the same status) does not
     touch `note` and writes no history row.
6. **Delete.** Listings are soft deleted (`204`, then they vanish from list and
   retrieve). Brands are hard deleted, but only when no listing (including a
   soft-deleted one) uses them → otherwise `409`.
7. **Slugs** are generated by the server (`title` for listings, `name` for
   brands). They are never sent by the client.

---

## 4. Brand API

Base path: `/api/v1/catalog/brands/`

### 4.1 Create — `POST /brands/`

Request
```json
{ "name": "Samsung" }
```
Optional: `"is_active": false`.

Response `201`
```json
{
  "id": 1,
  "name": "Samsung",
  "slug": "samsung",
  "is_active": true,
  "created_by": 10,
  "creator_name": "Test Admin",
  "creator_type": "admin"
}
```

| Case | Result |
|---|---|
| `{}` | `400` `{"name": ["This field is required."]}` |
| Name whose slug exists (`"samsung"`, `"SAMSUNG"`) | `400` `{"name": ["A brand with this name already exists."]}` |
| `{"name": "Apple", "is_active": false}` | `201`, `is_active: false` |

### 4.2 Update — `PATCH /brands/{id}/`

```json
{ "name": "Samsung Electronics" }
```
`200` — the slug becomes `samsung-electronics`.

```json
{ "is_active": false }
```
`200` — deactivates (use this instead of deleting a brand that is in use).

| Case | Result |
|---|---|
| Rename onto another brand's name | `400` (same message as create) |
| Unknown id | `404` |

`PUT` also works but needs `name`.

### 4.3 List — `GET /brands/`

| Query | Meaning |
|---|---|
| `name=sam` | Case-insensitive "contains" on name |
| `is_active=true\|false` | Filter by active flag |
| `search=sam` | Alternative name search |
| `limit`, `offset` | Pagination (default limit 20) |

Response `200`
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    { "id": 1, "name": "Samsung", "slug": "samsung", "is_active": true,
      "created_by": 10, "creator_name": "Test Admin", "creator_type": "admin" }
  ]
}
```
A name with no match returns `"results": []`.

### 4.4 Delete — `DELETE /brands/{id}/`

| Case | Result |
|---|---|
| Brand not used by any listing | `204` |
| Used by a listing (even a soft-deleted one) | `409` `{"detail": "This brand is used by one or more listings. Deactivate it instead of deleting."}` |

---

## 5. Listing API

Base path: `/api/v1/catalog/listings/`

### 5.1 Fields

| Field | Type | Notes |
|---|---|---|
| seller | id, optional | seller owner |
| buyer | id, optional | buyer owner (job requests) |
| category | id, **required** | must exist |
| catalog_type | `product` \| `service`, **required** | |
| listing_type | `general` `used` `village` `retail` `wholesale` `brand`, optional | `brand` makes `brand` mandatory |
| posted_by_role | `seller_offer` \| `buyer_request`, optional | |
| title | string, **required** | slug generated from it |
| description | text, **required** | |
| brand | brand id, optional | read back with `brand_name` |
| model, color, origin, warranty | text, optional | |
| price | decimal, **required** | original price |
| discounted_price | decimal, optional | defaults to `price`; never higher than `price` |
| currency | string, default `BDT` | |
| price_type, hourly_rate, delivery_days, urgent, package_includes, available_from, available_to | optional | service side |
| min_order_qty, stock_qty, measurement, colors, sizes, reserved_qty, condition_note, attributes | optional | product side |
| country, state, city, thana | ids, optional | |
| status | see rule 2 | |
| note | text | latest status-change note |
| price_tiers | list | see 5.2 |
| media_file | files (multipart, write only) | |
| media_delete_ids | list of ids (write only) | |
| *(read only)* | `id`, `slug`, `brand_name`, `media`, `status_change_logs`, `created_at`, `updated_at` | |

### 5.2 Price tiers

```json
"price_tiers": [
  { "min_qty": 1,  "max_qty": 9,    "price": "150.00", "discounted_price": "120.00" },
  { "min_qty": 10, "max_qty": 49,   "price": "140.00", "discounted_price": "110.00" },
  { "min_qty": 50, "max_qty": null, "price": "130.00" }
]
```
- When `price_tiers` is sent, the whole list is **replaced**. `[]` removes all tiers.
- When the key is left out of a PATCH, tiers are untouched.
- A tier without `discounted_price` gets its own `price`. A tier `discounted_price` higher than its `price` → `400`.

### 5.3 Create — `POST /listings/`

**A. Brand listing, Admin-created, with discount and tiers**
```json
{
  "category": 18,
  "catalog_type": "product",
  "listing_type": "brand",
  "brand": 1,
  "title": "Samsung Galaxy A15 128GB",
  "description": "Brand new, sealed box.",
  "model": "Galaxy A15",
  "price": "150.00",
  "discounted_price": "120.00",
  "currency": "BDT",
  "stock_qty": 40,
  "measurement": 13,
  "country": 126, "state": 12, "city": 8,
  "price_tiers": [
    { "min_qty": 1, "max_qty": 9, "price": "150.00", "discounted_price": "120.00" },
    { "min_qty": 10, "max_qty": null, "price": "140.00" }
  ]
}
```
(The second tier has no `discounted_price`, so it comes back as `"140.00"`.)

Response `201` (shortened)
```json
{
  "id": 30,
  "seller": null,
  "buyer": null,
  "category": 18,
  "catalog_type": "product",
  "listing_type": "brand",
  "brand": 1,
  "brand_name": "Samsung",
  "title": "Samsung Galaxy A15 128GB",
  "slug": "samsung-galaxy-a15-128gb",
  "price": "150.00",
  "discounted_price": "120.00",
  "status": "approved",
  "note": null,
  "price_tiers": [
    { "id": 1, "min_qty": 1, "max_qty": 9, "price": "150.00", "discounted_price": "120.00" },
    { "id": 2, "min_qty": 10, "max_qty": null, "price": "140.00", "discounted_price": "140.00" }
  ],
  "media": [],
  "status_change_logs": [
    { "id": 51, "status": "approved", "note": null, "created_by": 10,
      "creator_type": "admin", "creator_name": "Test Admin",
      "created_at": "2026-10-04T10:00:00+06:00" }
  ]
}
```

**B. Smallest valid payload (no brand, no owner)**
```json
{
  "category": 18,
  "catalog_type": "product",
  "title": "Plain Listing",
  "description": "Smallest valid payload.",
  "price": "10.00"
}
```
`201`, `brand: null`, `seller: null`, `buyer: null`, `status: "approved"`.

**C. Service offer (Admin-owned)**
```json
{
  "category": 29,
  "catalog_type": "service",
  "posted_by_role": "seller_offer",
  "title": "Home Cleaning",
  "description": "Deep cleaning, 2 days.",
  "price": "4000.00",
  "discounted_price": "3500.00",
  "price_type": "fixed",
  "delivery_days": 2
}
```

**D. Seller-owned product**
```json
{ "seller": 5, "category": 18, "catalog_type": "product", "posted_by_role": "seller_offer",
  "title": "Charger", "description": "Fast charger", "price": "20.00" }
```

**E. Buyer job request**
```json
{ "buyer": 3, "category": 29, "catalog_type": "service", "posted_by_role": "buyer_request",
  "title": "Need cleaning", "description": "3-bedroom flat", "price": "4000.00" }
```

**F. Explicit status**
```json
{ "category": 18, "catalog_type": "product", "status": "pending",
  "title": "Pending one", "description": "x", "price": "25.00" }
```
`201`, `status: "pending"`. With `"status": "rejected"` a `note` is required.

**G. Multipart (images / files)** — send `media_file` once per file. Nested
values (`price_tiers`) are easiest to add in a later JSON PATCH.

#### Create — error cases

| Payload | Response |
|---|---|
| `listing_type: "brand"`, no `brand` | `400` `{"brand": ["A brand listing must select a brand."]}` |
| `brand` is an inactive brand | `400` `{"brand": ["This brand is inactive."]}` |
| `brand: 99999999` | `400` `{"brand": ["Invalid pk \"99999999\" - object does not exist."]}` |
| `price: "100.00"`, `discounted_price: "120.00"` | `400` `{"discounted_price": ["Cannot be higher than price (price is the original price)."]}` |
| tier with `discounted_price` higher than its `price` | `400` (error under `price_tiers`) |
| `seller` and `buyer` both set | `400` `{"buyer": ["A listing cannot have both a seller and a buyer."]}` |
| `seller_offer` with a `buyer` | `400` `{"buyer": ["A seller_offer listing cannot have a buyer."]}` |
| `buyer_request` with a `seller` | `400` `{"seller": ["A buyer_request listing cannot have a seller."]}` |
| `status: "rejected"` / `"changes_requested"` without `note` | `400` `{"note": ["A note is required when rejecting a listing or requesting changes."]}` |
| missing `category` / `title` / `description` / `price` / `catalog_type` | `400` per-field "This field is required." |

### 5.4 Retrieve — `GET /listings/{id}/`

Full detail including `brand`, `brand_name`, `price`, `discounted_price`,
`price_tiers`, `media` and the complete `status_change_logs` (newest first).
Soft-deleted or unknown id → `404`.

### 5.5 List — `GET /listings/`

| Query | Meaning |
|---|---|
| `status` | `draft`, `pending`, `approved`, `rejected`, `changes_requested` |
| `catalog_type`, `listing_type` | |
| `category`, `brand`, `seller`, `buyer` | ids |
| `search` | title, brand name, model |
| `limit`, `offset` | Pagination (default limit 20) |

Rows are light: `id, title, slug, catalog_type, listing_type, category, brand,
seller, buyer, price, discounted_price, status, created_at`.

### 5.6 Update — `PATCH /listings/{id}/`

| Goal | Payload | Result |
|---|---|---|
| Change price info | `{"price": "160.00", "discounted_price": "130.00"}` | `200` |
| Remove the discount | `{"discounted_price": null}` | `200`, `discounted_price` = `price` |
| Update only `price` on a no-discount listing | `{"price": "90.00"}` | `200`, `discounted_price` also `90.00` |
| Discount above price | `{"discounted_price": "500.00"}` | `400` |
| Replace tiers | `{"price_tiers": [{"min_qty": 1, "price": "150.00", "discounted_price": "99.00"}]}` | `200`, only that tier remains |
| Change brand | `{"brand": 2}` | `200` |
| Clear brand (non-brand listing) | `{"listing_type": "general", "brand": null}` | `200` |
| Brand listing without a brand | `{"listing_type": "brand"}` on a listing with no brand | `400` |
| Add media | multipart `media_file=@a.jpg` (repeat) | `200`, `media_type` read from the file |
| Remove media | `{"media_delete_ids": [4, 5]}` | `200` |
| Unrelated edit | `{"description": "new"}` | `200`; status, note and history unchanged |

### 5.7 Moderation (status changes)

Status changes use the same `PATCH`.

| Step | Payload | Result |
|---|---|---|
| Reject without note | `{"status": "rejected"}` | `400` |
| Reject | `{"status": "rejected", "note": "Photos are low quality"}` | `200`, `note` set, history +1 |
| Ask for changes | `{"status": "changes_requested", "note": "Add more photos"}` | `200`, history +1 |
| Approve without note | `{"status": "approved"}` | `200`, **`note: null`**, history +1 |
| Approve with note | `{"status": "approved", "note": "Looks good"}` | `200`, `note: "Looks good"` |
| Same status again | `{"status": "approved"}` on an approved listing | `200`, no history row |

History after reject → changes_requested → approve (newest first):
```json
"status_change_logs": [
  { "status": "approved",          "note": null,                  "creator_type": "admin", "creator_name": "Test Admin" },
  { "status": "changes_requested", "note": "Add more photos",     "creator_type": "admin", "creator_name": "Test Admin" },
  { "status": "rejected",          "note": "Photos are low quality", "creator_type": "admin", "creator_name": "Test Admin" },
  { "status": "approved",          "note": null,                  "creator_type": "admin", "creator_name": "Test Admin" }
]
```
(the last row is the creation event; each row also has `id`, `created_by`, `created_at`).

### 5.8 Bulk moderation — `POST /listings/bulk-moderate/`

```json
{ "listing_ids": [31, 32, 33], "status": "rejected", "note": "Bulk rejected" }
```
Response `200`
```json
{ "updated": [31, 32], "skipped": [33] }
```
- `status` must be `approved`, `rejected` or `changes_requested`.
- `note` is required for `rejected` and `changes_requested`.
- Listings already at that status go to `skipped` (no history row). The others
  are updated, `note` replaced (or cleared when omitted), one history row each.

| Case | Result |
|---|---|
| `status` missing/invalid | `400` `{"status": "Must be one of: approved, changes_requested, rejected."}` |
| reject/changes without `note` | `400` `{"note": "A note is required when rejecting or requesting changes."}` |
| `listing_ids` empty | `400` `{"listing_ids": "Provide one or more listing ids."}` |
| Unknown / deleted ids | ignored (not in either list) |

### 5.9 Delete — `DELETE /listings/{id}/`

`204`. The row stays in the database with `deletedAt` set. A second delete or a
later retrieve returns `404`.

---

## 6. Admin actions used by every request

The Admin token stamps `created_by`, `creator_type` (`admin`) and
`creator_name` on the new row and on its history entry (`updated_*` on updates).

## 7. Testing summary

| Suite | Result |
|---|---|
| Listing smoke (CRUD, moderation, tiers, media, soft delete, bulk, owner rules) | 54 / 54 |
| Brand + listing changes smoke (brand CRUD, brand rules, discount rules incl. default to price) | 55 / 55 |
| Postman collection run with Newman | 82 assertions, 0 failed (the media-upload request needs real files, so it is skipped headless) |

All test data was removed afterwards.

## 8. Notes for the front-end team

- Use `brand` (id) and show `brand_name`. Load the Brand dropdown from
  `GET /brands/?is_active=true`.
- Show `price` struck through only when `discounted_price` is lower than it; `discounted_price` is always present.
- Show `note` as the current reason, and `status_change_logs` as the timeline.
- `listing_type = brand` → mark the Brand dropdown as required.
- Attribute / Color / Origin dropdowns are not available yet.
