# Brief for the Egoola Web session — public buyer browsing (categories, products, gigs, seller page)

Backend done and tested in `egoola-server`: every public (no-login) route a buyer uses to browse — categories,
products, gigs, geography dropdowns, and the seller page. Read this file top to bottom, then build the browsing
screens in **Buyer Web**. Do not push; commit locally only if asked.

Read first: `docs/public-api-guide.md` (the technical contract below is a copy of it — the single source of truth
for every public route; if a new one gets added later, it's documented there first), `docs/Egoola_Buyer_Browsing_Guide.md`
(plain-language explanation of what a buyer sees and why, if anything below is unclear conceptually). Postman:
`Egoola-BuyerApp` → **Categories**, and the products/gigs/seller-page requests in the same collection. Run the
backend with `uv run manage.py runserver 8000`. No login needed for any of this — but if you need to see what an
*invisible* listing looks like from the admin side to set up test data, admin: `test.admin@egoola.com` / `Test@12345`.

---

## 1. What this is

Pure read-only browsing: no token required anywhere in this brief, `POST`/`PATCH`/`DELETE` are `405` everywhere,
a stale/expired token sent by mistake is simply ignored (never `401`). This is the buyer's entry point before
they ever log in — category drill-down, product/gig search and filtering, and the seller's public profile page.

**Visibility rule, the same everywhere in this brief**: a buyer only ever sees an `approved`, non-deleted listing
belonging to a seller who is **verified and active** (or no seller at all — an admin-owned listing), with **at
least one active SKU**. Anything else — pending/rejected/draft/deleted, a waiting/rejected/paused/suspended
seller's listings, or a listing with every SKU hidden — is invisible: `404` on detail, simply absent from lists.
A buyer's own job request is never listed here at all (it lives on the seller job board instead, bid on, not
browsed — out of scope for this brief).

**Pagination is page-based everywhere in this brief** (`{count, page, page_size, total_pages, results}`,
`?page=&page_size=`) — **except the 4 geography dropdowns**, which are limit/offset (`?limit=&offset=`, shared
with the seller sign-up form's own location pickers). Don't build one generic pager for all of this; the
geography lists are a deliberate, documented exception.

## 2. The contract

### Geography dropdowns — load one level at a time

| Dropdown | Endpoint | Filters |
|---|---|---|
| Country | `GET /public/geography/countries/` | `search` |
| State/division | `GET /public/geography/states/` | `country`, `search` |
| City/district | `GET /public/geography/cities/` | `country`, `state`, `search` |
| Thana/union | `GET /public/geography/thanas/` | `country`, `state`, `city`, `search` |

Cascading: picking a country loads its states, picking a state loads its cities, picking a city loads its thanas
(often empty — that's normal, not an error). Rows: `id`, `name`, `slug`, parent ids (`country` also has
`country_code`, `flag_url`). `{count, next, previous, results}` shape (limit/offset, not page-based).

### Categories — `GET /public/catalog/categories/`

One endpoint for the whole tree: no params = top level; `parent_id=<id>` = that category's direct children.
`has_children: true` on a row means show a "more" arrow and call again with that id as `parent_id`; `false` means
it's a leaf — the next tap goes to the listings of that category, not deeper into categories. A leaf's children
call is an empty list (`200`), not an error.

| Query | Meaning |
|---|---|
| `parent_id` | direct children of that category. `400` if not a positive integer; `404` if it doesn't exist, is inactive, or sits under an inactive one |
| `search` | name or Bangla name, partial, case-insensitive. **With** `parent_id`: only among that parent's direct children. **Without**: across every level at once |
| `type` | `product` or `service` |
| `page`, `page_size` | page-based |

Filters AND together. An inactive category, or anything under an inactive one, never appears, regardless of filters.

```json
GET /public/catalog/categories/?page_size=2
{ "count": 11, "page": 1, "page_size": 2, "total_pages": 6,
  "results": [
    { "id": 18, "parent": null, "type": "product", "name": "Electronics", "name_bn": "...", "slug": "electronics",
      "image_url": null, "sort_order": 1, "has_children": true } ] }
```

### Products — `GET /public/catalog/products/` and `/products/{id}/`

| Param | Meaning |
|---|---|
| `category` | includes every sub-category below it |
| `search` | title, Bangla title, brand name, model |
| `listing_type` | `general`, `used`, `village`, `retail`, `wholesale`, `brand` |
| `brand` | brand id |
| `in_stock` | `true`/`false` (stock not tracked counts as in stock) |
| `price_min`, `price_max` | against the cheapest active SKU's current (discounted) price; `price_min` > `price_max` is `400` |
| `seller` | a seller's product list (used on the seller page) |
| `country`, `state`, `city`, `thana` | location |
| `ordering` | `newest` (default), `oldest`, `price_asc`, `price_desc`, `title` |

List row: `id, title, title_bn, slug, listing_type, category{id,name,name_bn,slug}, brand{id,name}|null, image_url,
price, discounted_price, currency, in_stock, seller{id,name,profile_pic_url}, created_at`. `price` is the
original, `discounted_price` what's charged now (equal when no discount is running).

Detail adds: `description`(+`_bn`), `model`, `origin`(+`_bn`), `warranty`(+`_bn`), `measurement{id,name,symbol}`,
`min_order_qty`, `condition_note`(+`_bn`), `attributes` (free-form spec object), `location{country,state,city,thana}`
(each `{id,name}`|`null`), `price_tiers` (wholesale quantity pricing), `media[]`, and `skus[]` (each with
`variants[]` for the option combination, `available_qty`, `is_discount_active`). A gig id here is `404`. Never
returned: status, notes, change logs, audit columns, seller contact details.

### Gigs — `GET /public/catalog/gigs/` and `/gigs/{id}/`

Same query params as products (`category`, `search`, `seller`, location, `ordering`, paging), plus:

| Param | Meaning |
|---|---|
| `price_type` | only gigs with an active package of that type; the row then shows *that* package's rate |
| `price_min`, `price_max` | without `price_type`: against the lowest active rate, whatever its unit — combine with `price_type` for a fair comparison across gigs |
| `delivery_days_max` | gigs delivered within that many days (ones with no delivery time set are excluded) |
| `urgent` | `true`/`false` |

List row: `id, title, title_bn, slug, category{...}, image_url, price, discounted_price, price_type, currency,
delivery_days, urgent, seller{id,name,profile_pic_url}, created_at` — `price`/`discounted_price`/`price_type`
describe the **lowest-rate** package (or the one matching `price_type` if filtered): show it as "from ৳50/hour".

Detail adds `description`(+`_bn`), `package_includes`(+`_bn`), `available_from`/`available_to`, `location`,
`media[]`, and `packages[]` (each `{id, price_type, price, discounted_price, is_discount_active, description,
description_bn}` — no options, no stock, no quantity prices on a gig). A product id here is `404`.

### Seller page — `GET /public/sellers/{id}/`

Opened from a product/gig's `seller.id`. Only a verified **and** active seller has a page — anything else is
`404`, same as their listings.

```json
{ "id": 211, "name": "Rafiq Ahmed", "profile_pic_url": null, "member_since": "...",
  "location": { "country": "Bangladesh", "state": "Chittagong", "city": "Feni", "thana": null },
  "business": { "business_type": "Retail", "main_product": "Bags", "description": null, "established_year": "2020", "employees_range": "1-10" } | null,
  "contact": { "public_email": null, "whatsapp": null, "facebook": null, "wechat": null, "skype": null } | null,
  "skills": null, "education": null, "experience": null,
  "product_count": 12, "gig_count": 3 }
```

`business`/`contact` are `null` when the seller never filled in a business profile. List their products/gigs with
`?seller=<id>` on the product/gig list endpoints. Never returned: email, phone, address, documents, verification
status, balance.

### Errors (everywhere in this brief)

`400 {"field": ["message"]}` on a bad filter value (unknown `ordering`/`listing_type`/`price_type`/`type`, a
non-numeric id, `price_min > price_max`). `404 {"detail": "..."}` on an unknown/invisible id, or a page number
past the last one (`{"detail": "Invalid page."}`).

## 3. Tasks

1. **API clients**: `categories-api.ts` (page-based), `products-api.ts` + `gigs-api.ts` (page-based, each with
   their own filter param set above), `geography-api.ts` (limit/offset, cascading), `sellers-api.ts` (single
   detail fetch). Keep the geography client's pagination handling separate from the others' — don't force one
   shared pager abstraction onto a shape it doesn't have.
2. **Category browse**: a drill-down UI (breadcrumb or nested drawer) — top level on load, tap a category with
   `has_children: true` to go deeper via `parent_id`, tap one with `has_children: false` to go to its listings.
   A search box that searches the current level when inside a category, or every level when at the top.
3. **Product list / search**: filter sidebar (category, brand, listing type, in-stock, price range, location),
   sort dropdown (`ordering`), page-based "load more" or numbered pages matching the rest of the Buyer Panel's
   list convention, product cards (thumbnail, title, price/discounted price, seller name linking to the seller
   page, in-stock badge).
4. **Product detail**: full fields, SKU/variant picker (if `variants` present — build the combination selector
   the same way the seller/admin listing-edit screens already present SKU options, just read-only here), gallery
   from `media`, wholesale price tiers table if present, location, seller block linking to the seller page.
5. **Gig list / search**: same filter-bar pattern plus `price_type`, `delivery_days_max`, `urgent`; cards show
   "from ৳X / {price_type}" and the urgent/delivery-days badges.
6. **Gig detail**: description, package_includes, availability window, every package listed (not just the
   cheapest) so a buyer can compare price types, location, seller block.
7. **Seller page**: profile block (name, photo, member since, location), business info block (only if non-null),
   contact block (only if non-null, each field optional — show only what's present), two tabs/sections linking to
   that seller's product list and gig list (`?seller=<id>`).
8. Empty states distinct from loading states on every list (no results vs. still fetching); a page past the last
   one should redirect to the last valid page rather than show the raw `404`.

## 4. Verify (browser, no login needed; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Load categories with no params | top-level only, `has_children` correct on each |
| 2 | Drill into a category with children, then a leaf | children shown, then an empty "more" step (leaf reached) |
| 3 | Search a term at the top level vs. inside a category | top level searches every depth; inside a category, only its direct children |
| 4 | Product list, no filters | only approved/visible listings shown (verify none of a rejected/pending/deleted one, or an inactive seller's, leak through) |
| 5 | Filter by category (parent with sub-categories) | includes products from every sub-category, not just the exact category id |
| 6 | `price_min` > `price_max` | `400`, handled gracefully |
| 7 | `in_stock=false` | only sold-out listings |
| 8 | Product detail with variants (size/colour) | combination picker works, `available_qty` shown per combination |
| 9 | A gig id on the product detail route (or vice versa) | `404`, handled as "not found", not a crash |
| 10 | Gig list filtered by `price_type=hourly` | only gigs with an active hourly package; rate shown is the hourly one, not some other package's |
| 11 | Open a seller page from a product/gig card | correct profile, business/contact blocks hidden when null, product/gig counts match the linked lists |
| 12 | A waiting/rejected/paused/suspended seller's id (if reachable) | `404` on the seller page |
| 13 | Page past the last page | redirected or shown a clean "no more results", not a raw error screen |
| 14 | Geography cascade (country → state → city → thana) | each level loads correctly scoped to the parent picked, an empty thana list is handled as normal |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
