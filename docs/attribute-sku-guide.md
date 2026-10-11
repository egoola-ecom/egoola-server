# Attributes, Attribute Values and Listing SKUs — Guide

How to sell one product in many sizes, colours or other options, where each
combination has its own price, discount and stock.

Admin-only. Header on every request: `Authorization: Bearer <admin access token>`.
A seller or buyer token gets `403`, no token gets `401`.
Lists are paginated: `?limit=` / `?offset=` (default 20, max 100).
Postman: `postman/Egoola-Attribute.postman_collection.json` (the SKU requests
are in its **Listing SKUs** folder). Listings in general: [listing-module-guide.md](listing-module-guide.md).

---

## 1. The idea in plain words

| Word | Meaning | Example |
|---|---|---|
| **Attribute** | A kind of option | Size, Colour, Storage |
| **Attribute value** | One choice of an attribute | Size → S, M, L, XL |
| **SKU** | One thing you can actually buy. It has its own price, discount and stock | Size M + Colour Red, 10 in stock, 1,800 BDT |
| **Variant** | One option of a SKU (a row that says "Size = M") | Size → M |

So a panjabi in 4 sizes and 3 colours is **one listing with 12 SKUs**, and each
SKU has two variants (one Size, one Colour).

- A listing with no options (a simple product, a service, a job request) has **exactly one
  SKU with no variants**.
- Price, discount and stock are on the **SKU**, not on the listing.
- A SKU is **never deleted**. To hide one, set `is_active` to `false`. The frontend should
  skip inactive SKUs.

Tables: `attributes`, `attributeValues`, `listingSkus`, `listingSkuVariants`. Bangla columns are
`nameBn` and `descriptionBn` (the same spelling as categories).

---

## 2. Attributes — `/api/v1/catalog/attributes/`

### Fields

| Field | Notes |
|---|---|
| name | **required**, unique (upper/lower case ignored) |
| name_bn | optional Bangla name |
| description, description_bn | optional |
| is_active | default `true` |
| values | read only — the attribute's values (see section 3) |
| id, created_by, creator_type, creator_name, created_at, updated_at | read only (the admin token fills the creator) |

### Endpoints

| Call | Result |
|---|---|
| `POST /attributes/` | `201` |
| `GET /attributes/{id}/` | `200` with its `values` · unknown id `404` |
| `PATCH` / `PUT /attributes/{id}/` | `200` |
| `GET /attributes/` | list. Filters: `?name=` (part of the name), `?is_active=true|false`, `?search=` (English or Bangla name) |
| `DELETE /attributes/{id}/` | `204` when unused. Used by a SKU → `409` `{"detail": "This attribute is used by one or more listing SKUs. Deactivate it instead of deleting."}`. Deleting an unused attribute also deletes its values |

### Create

```json
{ "name": "Size", "name_bn": "সাইজ", "description": "Garment size", "description_bn": "পোশাকের সাইজ" }
```
`201`
```json
{
  "id": 1, "name": "Size", "name_bn": "সাইজ", "description": "Garment size",
  "description_bn": "পোশাকের সাইজ", "is_active": true, "values": [],
  "created_by": 10, "creator_name": "Test Admin", "creator_type": "admin",
  "created_at": "2026-10-11T15:12:56+06:00", "updated_at": "2026-10-11T15:12:56+06:00"
}
```

| Case | Result |
|---|---|
| name already used (any letter case) | `400` `{"name": ["An attribute with this name already exists."]}` |
| missing or blank name | `400` `{"name": [...]}` |

---

## 3. Attribute values — `/api/v1/catalog/attribute-values/`

### Fields

| Field | Notes |
|---|---|
| attribute | **required**, id of the attribute. Cannot be changed later |
| name | **required**, unique inside its attribute (letter case ignored) |
| name_bn, description, description_bn | optional |
| is_active | default `true` |
| attribute_name | read only |

### Endpoints

| Call | Result |
|---|---|
| `POST /attribute-values/` | `201` |
| `GET /attribute-values/{id}/` | `200` |
| `PATCH` / `PUT /attribute-values/{id}/` | `200` |
| `GET /attribute-values/` | list. Filters: `?attribute=` (id), `?name=`, `?is_active=`, `?search=` (English or Bangla) |
| `DELETE /attribute-values/{id}/` | `204` when unused. Used by a SKU → `409` `{"detail": "This value is used by one or more listing SKUs. Deactivate it instead of deleting."}` |

```json
{ "attribute": 1, "name": "XL", "name_bn": "এক্সএল" }
```

| Case | Result |
|---|---|
| same name already in that attribute | `400` `{"name": ["This attribute already has a value with this name."]}` |
| same name under a different attribute | allowed (`M` can be a size and a colour code) |
| the attribute is inactive | `400` `{"attribute": ["This attribute is inactive."]}` |
| unknown attribute | `400` |
| changing the attribute of an existing value | `400` `{"attribute": ["The attribute cannot be changed after creation."]}` (re-sending the same one is fine) |

**Deactivating** an attribute or a value (`is_active: false`) does not touch SKUs that already use it.
It only stops it from being picked for a new variant (see rule 7 below). Use it instead of deleting.

---

## 4. Listing SKUs

SKUs are sent inside the listing: `skus` on `POST` / `PATCH /api/v1/catalog/listings/`.

### SKU fields

| Field | Notes |
|---|---|
| id | on update only: the SKU to change (see 4.2) |
| sku | optional code, unique across all SKUs (e.g. `SAM-A15-128-BLK`). Empty is fine |
| price | original price, **required for a new SKU**, cannot be negative |
| discounted_price | price while the discount runs. Not sent or `null` → equals `price`. Cannot be higher than `price` |
| discount_start_date, discount_end_date | optional. The discount only applies between them (empty = no limit on that side) |
| stock_qty | optional, cannot be negative. Empty = stock is not tracked (e.g. services) |
| is_active | default `true` |
| variants | list of `{ "attribute": <id>, "attribute_value": <id> }`, one per attribute. Empty for a listing with no options |
| *(read only)* | `reserved_qty` (starts at 0, kept by the order flow later), `effective_price`, `is_discount_active`, and on each variant `attribute_name` / `attribute_value_name` |

`effective_price` is the price a buyer pays **right now**: the discounted price while the
discount window is open, otherwise the normal price. `is_discount_active` says which one it is.

On the listing itself, `price` and `discounted_price` are read-only and mean "from": the original
and the current price of the cheapest **active** SKU (`null` when no SKU is active).

### 4.1 Create a listing with SKUs

```json
{
  "category": 22, "catalog_type": "product", "listing_type": "general",
  "title": "Men's Cotton Panjabi", "description": "Soft cotton.",
  "skus": [
    { "sku": "PNJ-M-WHT", "price": "1800.00", "discounted_price": "1500.00", "stock_qty": 12,
      "variants": [ { "attribute": 1, "attribute_value": 2 }, { "attribute": 2, "attribute_value": 6 } ] },
    { "sku": "PNJ-L-WHT", "price": "1900.00", "stock_qty": 8,
      "variants": [ { "attribute": 1, "attribute_value": 3 }, { "attribute": 2, "attribute_value": 6 } ] }
  ]
}
```
(Attribute 1 = Size, 2 = Colour; value 2 = M, 3 = L, 6 = White in this example.)

`201`, shortened:
```json
{
  "id": 283, "title": "Men's Cotton Panjabi", "price": "1800.00", "discounted_price": "1500.00",
  "skus": [
    { "id": 41, "sku": "PNJ-M-WHT", "price": "1800.00", "discounted_price": "1500.00",
      "discount_start_date": null, "discount_end_date": null,
      "effective_price": "1500.00", "is_discount_active": true,
      "stock_qty": 12, "reserved_qty": 0, "is_active": true,
      "variants": [
        { "attribute": 1, "attribute_name": "Size",   "attribute_value": 2, "attribute_value_name": "M" },
        { "attribute": 2, "attribute_name": "Colour", "attribute_value": 6, "attribute_value_name": "White" } ] },
    { "id": 42, "sku": "PNJ-L-WHT", "price": "1900.00", "discounted_price": "1900.00", "effective_price": "1900.00",
      "is_discount_active": false, "stock_qty": 8, "...": "..." }
  ]
}
```

### The shortcut for a listing with no options

On **create only**, if you send a plain `price` and no `skus`, one default SKU is made for you:

```json
{ "category": 18, "catalog_type": "product", "title": "Charger", "description": "Fast charger",
  "price": "100.00", "discounted_price": "80.00", "stock_qty": 7, "sku": "CHG-20W" }
```
The shortcut accepts `price`, `discounted_price`, `discount_start_date`, `discount_end_date`,
`stock_qty` and `sku`. It cannot be sent together with `skus`, and it is rejected on update.

### 4.2 Update SKUs — merge by id, never delete

`skus` on `PATCH` works like this:

| Item in `skus` | What happens |
|---|---|
| has an `id` | that SKU changes — **only the fields you send** |
| has no `id` | a new SKU is added (needs `price`) |
| a SKU you do not mention | left exactly as it is |

Nothing is ever deleted through `skus`. To take a SKU off sale, send `"is_active": false`.
Editing the listing without a `skus` key (for example only the title) leaves every SKU alone.

| Goal | Payload | Result |
|---|---|---|
| Add a SKU | `{"skus": [{"sku": "PNJ-S-GRN", "price": "1700.00", "variants": [...]}]}` | `200`, one more SKU |
| Change a price | `{"skus": [{"id": 41, "price": "2000.00"}]}` | `200`. A SKU with no discount follows the new price; a discounted SKU keeps its discount |
| Change stock only | `{"skus": [{"id": 41, "stock_qty": 20}]}` | `200`, price untouched |
| Set a discount window | `{"skus": [{"id": 41, "discounted_price": "1500.00", "discount_start_date": "2026-11-01T00:00:00Z", "discount_end_date": "2026-11-30T23:59:59Z"}]}` | `200` |
| Remove the discount | `{"skus": [{"id": 41, "discounted_price": null, "discount_start_date": null, "discount_end_date": null}]}` | `200`, `discounted_price` = `price` |
| Replace the options of a SKU | `{"skus": [{"id": 41, "variants": [...]}]}` | `200`. When `variants` is sent it **replaces** that SKU's options; when left out they stay |
| Hide a SKU | `{"skus": [{"id": 41, "is_active": false}]}` | `200`, still returned with `is_active: false` |
| Show it again | `{"skus": [{"id": 41, "is_active": true}]}` | `200` |

### 4.3 The rules (and the `400` you get when you break one)

Errors on a SKU come back under `skus`, keyed by the item's position in your list (`"0"` is the first):
`{"skus": {"0": {"price": "This field is required for a new SKU."}}}`.

1. **Each attribute once per SKU.** `{"variants": "A SKU can have only one value per attribute."}`
2. **The value must belong to the attribute.** `{"variants": "'Red' is not a value of the attribute 'Size'."}`
3. **Same set of attributes on every SKU of a listing.** You cannot mix a Size-only SKU with a Size + Colour SKU:
   `{"skus": ["All SKUs of a listing must use the same attributes (e.g. all Size + Colour)."]}`
4. **No two SKUs with the same combination** (inactive ones count too, so reactivate the old one instead of adding it again):
   `{"skus": ["Every SKU of a listing needs its own combination of options (two SKUs have the same one)."]}`
5. **A listing with more than one SKU needs options on each.** (A SKU with no options is only allowed as the one and only SKU.)
6. **Code unique.** `{"sku": "A SKU with this code already exists."}` — a soft-deleted listing keeps its codes.
7. **Only active attributes and values can be newly chosen.** `{"variants": "'Size: XL' is inactive."}` A SKU that already uses a
   value which was deactivated later can still be edited.
8. **Prices.** New SKU without `price` → `{"price": "This field is required for a new SKU."}`; negative price or stock → `400`;
   `{"discounted_price": "Cannot be higher than price (price is the original price)."}`.
9. **Discount dates.** `{"discount_end_date": "Must be after discount_start_date."}` and
   `{"discounted_price": "A discount period needs a discounted_price lower than price."}` (dates with no discount).
10. **The `id` must be a SKU of this listing.** `{"id": "This SKU does not belong to this listing."}`; the same SKU twice → `{"id": "The same SKU appears twice."}`
11. **At least one SKU on create.** No `skus` and no `price` (or `"skus": []`) →
    `{"skus": ["A listing needs at least one SKU: send `skus`, or `price` for a single default SKU."]}`.
12. **`skus` and the price shortcut together** → `{"skus": "Send either `skus` or the price shortcut, not both."}`.
13. **Plain `price` / `stock_qty` / `sku` on update** → `400` `{"price": "Prices and stock are changed through `skus`."}`.

Either everything in the request is saved or nothing is.

### 4.4 Price tiers and SKUs

Quantity price tiers (`price_tiers`) still apply to the **whole listing**. A tier may carry an optional
`listing_sku` (the id of one of this listing's SKUs); leave it out for a normal listing-wide tier. A SKU id
from another listing, or any `listing_sku` while creating, gives `400`
(`"A tier's listing_sku must be a SKU of this listing."`). See section 5.2 of the listing guide.

### 4.5 Search

`GET /listings/?search=` also matches the SKU code.

---

## 5. Notes for the frontend

**Admin form**
1. Load the attribute list (`GET /attributes/?is_active=true`); each item already has its `values`.
2. Let the admin pick attributes for the product (say Size and Colour) and the values for each.
3. Build the combinations (every size × every colour) as rows with price, discount, stock and code, then send them as `skus`.
4. When editing, send back only the SKUs that changed, each with its `id`. To retire one, send `is_active: false`.

**Storefront**
- Skip SKUs with `is_active: false`.
- Build the pickers from `skus[].variants` (the distinct `attribute_name` and `attribute_value_name`). When the buyer has chosen a
  value for every attribute, find the SKU whose variants match, and show its `effective_price` (struck-through `price` when
  `is_discount_active`) and `stock_qty` (`0` = out of stock; `null` = not tracked).
- A listing with no variants has one SKU: use its prices directly.
- Listing pages: use the listing's own `price` / `discounted_price` as the "from" price.

**Cart and orders (later)** point at the SKU: `cartItems.listingSkuId` and `orderItems.listingSkuId` exist now (nullable); the
colour and size text columns stay as a snapshot of what was bought.

---

## 6. What changed in the database

- New tables: `attributes`, `attributeValues`, `listingSkus`, `listingSkuVariants`.
- `listings`: `price`, `discountedPrice`, `stockQty`, `reservedQty`, `color`, `colors`, `sizes` removed (and the two GIN indexes on `colors` / `sizes`).
- `listingPriceTiers`: new nullable `listingSkuId`.
- `cartItems`, `orderItems`: new nullable `listingSkuId`.
- Migration `catalog 0008` first gives every existing listing one default SKU from its old price, discount and stock, then drops the old
  columns. (The dev database's sample listings were then removed and re-created with real options.)

## 7. Testing

- `scripts/smoke/sku_smoke.py`: 143 / 143 checks (attribute and value CRUD, every SKU rule above, update by id, deactivation,
  discount windows, tiers with `listing_sku`, 409 protection, category delete protection, soft-deleted listings). See `scripts/smoke/README.md`.
- Postman `Egoola-Attribute.postman_collection.json`: 98 assertions, 0 failed (it can be run again and again; it leaves a few
  deactivated attributes behind because soft-deleted listings keep their SKUs).
- All other smoke suites and Postman collections were re-run after the change and pass.
