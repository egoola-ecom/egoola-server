# Public API Guide — the routes that need no login

Every route in this guide is **public**: no token, `GET` only, and a stale or expired token sent by mistake is ignored (never a `401`). They exist for the **buyer** side
(web, app, browsing, search) and the sign-up forms. A seller or an admin screen may use them too (for example the seller sign-up form and the listing form use the same
location and category lists), but nothing here is built for them specifically. **Every public route is documented here and only here**: when a new public route is added, add it to this file.

## 1. Conventions

- Base URL `/api/v1/`. Public routes live under `/api/v1/public/...`.
- Read-only: `POST`, `PATCH`, `DELETE` are `405` / `404`. No audit columns (who created a row) are ever returned.
- **Paging.** The Buyer Panel convention is **page-based**: `?page=1&page_size=20` (`page` from 1, `page_size` default 20, max 100). Response `{count, page, page_size, total_pages, results}`:
  load more while `page < total_pages`. No match is `count: 0`, `total_pages: 0`, `results: []`. A page past the last is `404 {"detail": "Invalid page."}`.
  **Exception today:** the four geography lists (section 2) are still limit/offset (`limit` default 500, max 1000, `offset`), because dropdowns load a whole list and the seller sign-up already uses them.
- Errors: `400 {"field": ["message"]}`, `404 {"detail": "..."}`.

| Route | What | Section |
|---|---|---|
| `GET /public/geography/countries/` | countries | 2 |
| `GET /public/geography/states/` | states / divisions of a country | 2 |
| `GET /public/geography/cities/` | cities / districts of a state | 2 |
| `GET /public/geography/thanas/` | thanas / unions of a city | 2 |
| `GET /public/catalog/categories/` | the category list: top level, children, search | 3 |
| `GET /public/catalog/products/`, `/products/{id}/` | product list (filters, ordering) and detail | 4 |
| `GET /public/catalog/gigs/`, `/gigs/{id}/` | gig list (filters, ordering) and detail | 5 |
| `GET /public/sellers/{id}/` | the seller page | 6 |

## 2. Geography: country, state (division), city (district), thana

Load the dropdowns one level at a time: when a country is picked call `states/?country=<id>`; for a state `cities/?state=<id>`; for a city `thanas/?city=<id>`.
An empty list is normal (most cities have no thanas). Send the chosen `id`s to the API that needs them.

| Dropdown | Endpoint | Filters (all optional) |
|---|---|---|
| Country | `GET /api/v1/public/geography/countries/` | `search` |
| State / division | `GET /api/v1/public/geography/states/` | `country`, `search` |
| City / district | `GET /api/v1/public/geography/cities/` | `country`, `state`, `search` |
| Thana / union | `GET /api/v1/public/geography/thanas/` | `country`, `state`, `city`, `search` |

Sorted by name. Rows have only `id`, `name`, `slug` and the parent ids (countries also `country_code`, `flag_url`).

```json
GET /api/v1/public/geography/countries/
{ "count": 3, "next": null, "previous": null,
  "results": [ { "id": 126, "name": "Bangladesh", "slug": "bangladesh", "country_code": "645", "flag_url": null } ] }

GET /api/v1/public/geography/states/?country=126
{ "count": 2, "next": null, "previous": null,
  "results": [ { "id": 13, "name": "Chittagong", "slug": "chittagong", "country": 126 },
               { "id": 12, "name": "Dhaka", "slug": "dhaka", "country": 126 } ] }

GET /api/v1/public/geography/cities/?state=13
{ "count": 2, "next": null, "previous": null,
  "results": [ { "id": 8, "name": "Feni", "slug": "feni", "country": 126, "state": 13 },
               { "id": 9, "name": "Noakhali", "slug": "noakhali", "country": 126, "state": 13 } ] }

GET /api/v1/public/geography/thanas/?city=8
{ "count": 1, "next": null, "previous": null,
  "results": [ { "id": 40, "name": "Feni Sadar", "slug": "feni-sadar", "country": 126, "state": 13, "city": 8 } ] }
```

Tests: `scripts/smoke/public_geography_smoke.sh`. Postman: `Egoola-SellerApp` → **Public lookups**. Admin-side geography (with writes and audit columns) is a different API: [`geography-api-guide.md`](geography-api-guide.md).

## 3. Categories: `GET /api/v1/public/catalog/categories/`

The single category list for browsing (Phase 4, step 1). **No login** (a stale token is ignored), `GET` only, no audit columns. The buyer web, the buyer app and the
search screens all use this one endpoint: the first call lists the top level, and each tap calls it again with the tapped category's id as `parent_id`.

| Query | Default | Meaning |
|---|---|---|
| *(nothing)* | | the **top-level** categories (no parent) |
| `parent_id` | none | the **direct children** of that category. `400` if not a whole number ≥ 1; `404 {"detail": "Category not found."}` if it does not exist, is inactive, or sits under an inactive category |
| `search` | none | partial, case-insensitive match on `name` **or** `name_bn`, up to 100 characters. **With `parent_id`**: among that parent's direct children. **Without**: across **every level** (so "phone" finds "Mobile Phones" wherever it is). Blank = no search |
| `type` | both | `product` or `service` (`400` for anything else). Combines with the others |
| `page` | `1` | page number (`400` below 1; a page past the last one is `404 {"detail": "Invalid page."}`) |
| `page_size` | `20` | rows per page, `1`–`100` (`400` outside that) |

**Filter combinations.** Every filter narrows the result (they are ANDed). `parent_id` and `search` together search only the direct children of that parent, not deeper levels.
`search` alone ignores the "top level only" default. An **inactive** category is never returned, **nor is any category under an inactive one**, whatever the filters. Order: `sort_order`, then `name`.

Paging is **page-based** (`page`, `page_size`) for every Buyer Panel list, not limit/offset or cursor. Response: `{count, page, page_size, total_pages, results}`.

```json
GET /api/v1/public/catalog/categories/?page_size=2
{ "count": 11, "page": 1, "page_size": 2, "total_pages": 6,
  "results": [
    { "id": 18, "parent": null, "type": "product", "name": "Electronics", "name_bn": "ইলেকট্রনিক্স", "slug": "electronics",
      "image_url": null, "sort_order": 1, "has_children": true },
    { "id": 24, "parent": null, "type": "product", "name": "Furniture", "name_bn": "", "slug": "furniture",
      "image_url": null, "sort_order": 2, "has_children": false } ] }

GET /api/v1/public/catalog/categories/?parent_id=18          (the children of Electronics)
GET /api/v1/public/catalog/categories/?search=phone          (any level)
GET /api/v1/public/catalog/categories/?parent_id=18&search=phone&type=product
```

`has_children` is `true` when there is at least one **active** sub-category: show a "more" arrow and call again with `parent_id=<id>`; when `false`, the buyer has reached a leaf
(the next step is the listings of that category). A leaf is an empty list (`200`), not an error.

**Indexes.** The browse query is "active rows of one parent, in display order", served by `categories_browse_idx` on `(parentId, status, sortOrder, name)` (migration `catalog 0014`;
the foreign key on `parentId` is indexed already). No index was added for the name search: `icontains` (`%text%`) cannot use a normal B-tree index, a trigram index would only pay off with
thousands of categories (this is a small reference table of a few hundred rows), and the planner would not use it at that size. Revisit if the table grows a lot.

Tests: `scripts/smoke/category_browse_smoke.py`. Postman: `Egoola-BuyerApp` → **Categories**.

## 4. Products: `GET /api/v1/public/catalog/products/` and `/products/{id}/`

Product listings (`catalog_type = product`) for the Buyer Panel.

**What a buyer sees.** Only listings that are `approved` and not deleted, of a seller who is **verified and active** (or of no seller, an admin's own listing), and that have at least one **active SKU**.
Pending, rejected, changes-requested, draft and deleted listings, and the listings of a waiting, rejected, paused or suspended seller, never appear (list **and** detail: `404`).
A gig id here is `404`. Prices are those of the **active SKUs only**; the "from" price is the cheapest active SKU right now (the discounted price while its window is open).

**Query** (all optional; a bad value is `400 {"field": ["message"]}`; paging as in section 1):

| Param | Meaning |
|---|---|
| `category` | a category id; **includes every sub-category** below it |
| `search` | partial, case-insensitive: title, Bangla title, brand name, model (max 100 characters) |
| `listing_type` | `general`, `used`, `village`, `retail`, `wholesale`, `brand` |
| `brand` | brand id |
| `in_stock` | `true`: at least one active SKU in stock (stock not tracked counts as in stock). `false`: sold out |
| `price_min`, `price_max` | on the "from" price (cheapest active SKU, discount included); `price_min` above `price_max` is `400` |
| `seller` | seller id (a seller page's product list) |
| `country`, `state`, `city`, `thana` | location ids |
| `ordering` | `newest` (default), `oldest`, `price_asc`, `price_desc`, `title` |
| `page`, `page_size` | page-based paging |

**List row**

```json
{ "count": 1, "page": 1, "page_size": 20, "total_pages": 1,
  "results": [ {
    "id": 681, "title": "Cotton T-Shirt", "title_bn": "সুতির টি-শার্ট", "slug": "cotton-t-shirt", "listing_type": "general",
    "category": { "id": 18, "name": "Electronics", "name_bn": "", "slug": "electronics" },
    "brand": { "id": 3, "name": "Samsung" },
    "image_url": "/media/listing/thumbnails/a1b2.png",
    "price": "500.00", "discounted_price": "450.00", "currency": "BDT", "in_stock": true,
    "seller": { "id": 211, "name": "Rafiq Ahmed", "profile_pic_url": null },
    "created_at": "2026-10-12T09:41:03.596790+06:00" } ] }
```

`brand` and `seller` are `null` when there is none. `price` is the original price and `discounted_price` the price charged now (equal when there is no discount). `seller.id` links to the seller page (section 6).

**Detail** `GET /products/{id}/` adds: `description`, `description_bn`, `model`, `origin`, `origin_bn`, `warranty`, `warranty_bn`, `measurement` `{id, name, symbol}`, `min_order_qty`, `condition_note`, `condition_note_bn`,
`attributes` (specs), `location` (`country`, `state`, `city`, `thana`, each `{id, name}` or `null`), `price_tiers`, `media` (`id`, `media_type`, `media_url`) and `skus`:

```json
"skus": [ { "id": 593, "sku": "TEE-001", "price": "500.00", "discounted_price": "450.00", "is_discount_active": true,
            "in_stock": true, "available_qty": 20,
            "variants": [ { "attribute": { "id": 22, "name": "Colour", "name_bn": "রং" }, "attribute_value": { "id": 55, "name": "Black", "name_bn": "কালো" } } ] } ]
```

`available_qty` is the stock left (`null` when stock is not tracked). Never returned: status, notes, status or change logs, audit columns, seller phone or email.

## 5. Gigs: `GET /api/v1/public/catalog/gigs/` and `/gigs/{id}/`

A seller's service offers (`catalog_type = service`, a seller offer; a buyer's job request is never listed). The same visibility rules as products. A product id here is `404`.
A gig is priced by **packages**, one per `price_type` (`hourly`, `daily`, `weekly`, `monthly`, `fixed`); `price` is the rate for that unit and the buyer chooses the duration when ordering.

**Query:** `category` (with sub-categories), `search` (title, Bangla title), `seller`, `country`, `state`, `city`, `thana`, `ordering`, `page`, `page_size` exactly as for products, plus:

| Param | Meaning |
|---|---|
| `price_type` | only gigs with an **active package** of that type (`400` for another value). The row then shows **that** package, and `price_min` / `price_max` apply to that package's rate |
| `price_min`, `price_max` | without `price_type`: on the lowest active rate (rates of different units are compared as they are, so combine with `price_type` for a fair comparison) |
| `delivery_days_max` | gigs delivered within that many days (gigs with no delivery time are left out) |
| `urgent` | `true`: urgent service offered. `false`: not urgent |

**List row**: `id, title, title_bn, slug, category{…}, image_url, price, discounted_price, price_type, currency, delivery_days, urgent, seller{id, name, profile_pic_url}, created_at`.
`price` / `discounted_price` / `price_type` are the lowest-rate package (or the filtered one): show "from 50 / hour".

**Detail** `GET /gigs/{id}/` adds `description`, `description_bn`, `package_includes`, `package_includes_bn`, `available_from`, `available_to`, `location`, `media` and `packages`:

```json
"packages": [ { "id": 212, "price_type": "hourly", "price": "500.00", "discounted_price": "450.00", "is_discount_active": true,
                "description": "Hourly cleaning", "description_bn": "ঘণ্টাভিত্তিক ক্লিনিং" },
              { "id": 213, "price_type": "weekly", "price": "12000.00", "discounted_price": "12000.00", "is_discount_active": false,
                "description": null, "description_bn": null } ]
```

## 6. Seller page: `GET /api/v1/public/sellers/{id}/`

Opened when a buyer taps the seller's name on a product or a gig. Only a seller who is verified **and** active has a page; any other seller (waiting, rejected, paused, suspended) is `404`, like their listings.

```json
{ "id": 211, "name": "Rafiq Ahmed", "profile_pic_url": null, "member_since": "2026-10-11T22:38:52.250133+06:00",
  "location": { "country": "Bangladesh", "state": "Chittagong", "city": "Feni", "thana": null },
  "business": { "business_type": "Retail", "main_product": "Bags", "description": null, "established_year": "2020", "employees_range": "1-10" },
  "contact": { "public_email": null, "whatsapp": null, "facebook": null, "wechat": null, "skype": null },
  "skills": null, "education": null, "experience": null,
  "product_count": 12, "gig_count": 3 }
```

`business` and `contact` are `null` when the seller has no business profile. The counts are the seller's public products and gigs. To list them call the lists with `?seller=<id>`.
Never returned: email, phone, addresses, documents, balances, verification status or notes.

Tests: `scripts/smoke/public_listing_smoke.py`. Postman: `Egoola-BuyerApp`.

## 7. Adding a public route

Put the view in the app's `public_views.py` (`permission_classes = [AllowAny]`, `authentication_classes = []`), mount it under `public/` in `config/urls.py`, and add its section, its row in the
table in section 1 and a smoke test. Buyer Panel lists use `BuyerPagePagination` (`apps/core/pagination.py`).
