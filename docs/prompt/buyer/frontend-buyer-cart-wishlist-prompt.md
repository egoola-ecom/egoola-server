# Brief for the Egoola Web session — cart and wishlist

Backend done and tested in `egoola-server`: the buyer's cart(s) and wishlist. Read top to bottom, then build in
**Buyer Web**. Do not push; commit locally only if asked.

Read first: `docs/buyer/buyer-api-guide.md` sections 3–4 (technical contract below is a copy of it — the source of truth),
`docs/Egoola_Cart_Guide.md` (plain-language explainer if anything below is unclear conceptually). Postman:
`Egoola-BuyerApp` → **Cart**, **Wishlist**. Run backend with `uv run manage.py runserver 8000`. Needs a buyer token
(`test.buyer@egoola.com` / `Test@12345`, or register one — `docs/test-accounts.md`).

---

## 1. The one thing to get right: carts are per (type, seller), not one cart

A buyer does **not** have a single cart. They have **one active cart per (`product`|`service`) type per seller**,
created automatically the first time something of that type/seller is added — never asked for directly. Consequence
for the UI:

- Adding a product from seller A and a product from seller B creates **two separate carts**, both `cart_type:
  "product"`. Adding a gig from seller A creates a **third**, separate cart (`cart_type: "service"`) — gigs and
  products from the same seller never share a cart either (different checkout gateway later: Stripe for product,
  bKash for service).
- There is no "the cart" screen showing everything at once by default. `GET /buyer/cart/?type=product` (no
  `&seller=`) returns **one** cart: whichever active product cart the buyer most recently touched (added/edited/
  removed a line on). That is the right call for a generic cart-icon badge/page. To show **one seller's** cart
  specifically (e.g. from that seller's product page, "view my cart with this seller"), pass `&seller=<id>`.
- `seller: null` in a response, or `&seller=0` in a request, both mean the shared cart for admin-owned listings (no
  seller) — not "no filter", an actual distinct cart bucket.
- To show a buyer **everything** across all their sellers/types at once, use `GET /buyer/cart/summary/` (added
  after this brief was first written) — one row per active cart (`cart_type`, `seller`, `item_count`, `subtotal`,
  `updated_at`), plus a grand `item_count`. Use it for the header badge's true total and for a real "all carts"
  page; link each row to `GET /buyer/cart/?type=<cart_type>&seller=<id>` for that cart's full detail.
- A cart **closes permanently** once it becomes an order (checkout — see `frontend-buyer-order-prompt.md` and
  `frontend-buyer-gig-order-prompt.md`) — closed carts never resurface; the next add of that type/seller opens a
  brand new one. Don't cache a cart id across sessions expecting it to still be open.

Wishlist has none of this: it is one flat list per buyer, optionally filtered by `type`, no seller split.

## 2. The contract

All of this needs `Authorization: Bearer <access>` (buyer token). No `type` query param anywhere here ever means
"both" on the cart endpoints — it's always required and exactly one of `product`/`service`. On wishlist, `type` is
optional and *does* mean "both" when left out.

### Cart routes

| Route | What |
|---|---|
| `GET /buyer/cart/summary/` | every active cart at once — `item_count`/`subtotal`/`updated_at` per cart, plus a grand `item_count` |
| `GET /buyer/cart/?type=product\|service[&seller=]` | one cart — named seller's, or most-recently-touched — `null` if none |
| `POST /buyer/cart/items/` | add a listing + SKU (creates the cart if needed) |
| `PATCH /buyer/cart/items/{id}/` | **replace** (not add to) qty/duration of one line |
| `DELETE /buyer/cart/items/{id}/` | remove one line |
| `DELETE /buyer/cart/?type=product\|service[&seller=]` | empty that cart (same lookup as GET), no-op if none |

**Summary** — `GET /buyer/cart/summary/`:

```json
{ "item_count": 2,
  "carts": [
    { "id": 192, "cart_type": "product", "seller": {"id": 550, "name": "Karim Electric", "profile_pic_url": null},
      "item_count": 1, "subtotal": "4300.00", "updated_at": "..." } ] }
```

Newest-touched first, every type/seller together. `item_count` is **line count**, not a sum of `qty`/`duration` —
those aren't the same unit across a product and a service cart, so they're never added together. Use this for the
header badge's true total and for an "all carts" list; link each row to the single-cart `GET` above with its
`cart_type`/`seller.id`. Never creates anything — `{"item_count": 0, "carts": []}` when the buyer has nothing.

**Add** — `POST /buyer/cart/items/`:

```json
{ "listing": 103, "listing_sku": 113, "qty": 2 }
```

Product: `qty` required (≥1), `duration` rejected (`400`). Gig: `duration` required (≥1, in whatever unit the SKU's
`price_type` uses — hours/days/weeks/months), `qty` rejected (`400`). `listing`/`listing_sku` required always. The
listing must pass the same visibility rule as browsing (approved, seller verified+active, SKU active) — invisible or
unknown is `400 {"listing": ["Invalid pk \"103\" - object does not exist."]}`. A `listing_sku` from a different
listing is `400 {"listing_sku": ["Does not belong to this listing."]}`. Product stock is checked
(`stock_qty >= qty`) but **not reserved** — a race with another buyer is still possible right up to
checkout, where it is checked again.

**Adding the same SKU again merges into the existing line** — `qty`/`duration` add together, no duplicate row.
`201`:

```json
{ "id": 1, "listing": { "id": 103, "title": "Cotton T-Shirt", "title_bn": "...", "slug": "cotton-t-shirt",
  "image_url": null, "catalog_type": "product" },
  "listing_sku": { "id": 113, "sku": "TEE-001", "price": "100.00", "discounted_price": "100.00",
  "price_type": null, "is_active": true },
  "qty": 2, "duration": null, "color": null, "size": null,
  "unit_price": "100.00", "line_subtotal": "200.00", "available": true, "created_at": "..." }
```

`unit_price`/`line_subtotal` are computed live (today's discounted price), never frozen until checkout — don't
cache them client-side longer than the page load. `available: false` means the line is stale (SKU deactivated,
listing no longer approved, or stock can no longer cover `qty`) — **the line stays in the cart either way**, only
flagged; show it struck-through or with a warning, don't hide it, don't auto-remove it.

**The cart** — `GET /buyer/cart/?type=product`:

```json
{ "id": 1, "cart_type": "product", "seller": { "id": 211, "name": "Rafiq Ahmed", "profile_pic_url": null } | null,
  "is_active": true, "items": [ { "...": "item shape above" } ], "subtotal": "200.00",
  "created_at": "...", "updated_at": "..." }
```

`subtotal` = sum of every line's live `line_subtotal` (skips lines with no resolvable price). No delivery cost, no
discount, no grand total here — those only exist on an `Order`, after checkout (see the order prompts above).
Missing/invalid `type` is `400`. No cart found is `null`, `200` — not `404` — don't show an error state for it, show
the empty-cart state.

**Edit/remove a line** — `PATCH /buyer/cart/items/{id}/` with `{"qty": 1}` or `{"duration": 3}` (whichever matches
the line's own kind — sending the wrong one is `400`). This **replaces** the value, it does not add (unlike POST).
`DELETE /buyer/cart/items/{id}/` removes it, `204`. Both scoped to the logged-in buyer — another buyer's item id is
`404`.

**Clear** — `DELETE /buyer/cart/?type=product[&seller=]`, same lookup as GET, empties every line, cart row stays
active (so a later GET still finds it, just empty), `204` even if already empty/missing.

### Wishlist routes

| Route | What |
|---|---|
| `GET /buyer/favourites/?type=product\|service` (optional) | saved listings, newest first, page-based |
| `POST /buyer/favourites/` | save a listing |
| `DELETE /buyer/favourites/{listing_id}/` | un-save, keyed by **listing id**, not favourite id |

Plain idempotent toggle, unlike cart: saving an already-saved listing is a no-op `200` (not `201`, not a duplicate);
un-saving something never saved is still `204`. Never shows `400` for "already saved" — treat it as success.

**Save** — `POST /buyer/favourites/` with `{"listing": 103}`. Same visibility rule as cart/browsing — invisible is
`400 {"listing": [...]}`. `201`/`200`:

```json
{ "id": 1, "catalog_type": "product",
  "listing": { "...": "same row shape as GET /public/catalog/products/ or /gigs/, matching catalog_type" },
  "created_at": "..." }
```

`listing` is the **exact same shape** the public browsing list already renders (`docs/public-api-guide.md` §products/
§gigs) — reuse your existing product/gig card component here, don't build a second one. `catalog_type` tells you
which shape without inspecting fields.

**List** — `GET /buyer/favourites/?type=product` — page-based (`{count, page, page_size, total_pages, results}`,
same convention as every other Buyer Panel list). `type` omitted = both kinds mixed together, newest first.

**A favourite survives its listing going private** (seller deactivated, listing rejected, etc.) — not deleted, just
drops out of this list, and reappears on its own once visible again. So: don't assume "it's not in the list"
means "it was removed"; don't offer to "restore" a missing favourite, there's nothing to restore.

**Remove** — `DELETE /buyer/favourites/{listing_id}/` — always `204`. Fire-and-forget from a heart-icon toggle, no
need to check state first.

### Errors (everywhere in this brief)

`400 {"field": ["message"]}` on bad input (wrong qty/duration field for the line kind, missing `type`, unknown/
invisible listing, SKU mismatch, insufficient stock). `404 {"detail": "..."}` only on a cart-item id/favourite
listing id that isn't the logged-in buyer's — never on an empty/missing cart (that's `null`, `200`).

## 3. Tasks

1. **API clients**: `cart-api.ts` (needs `type` + optional `seller` on every call — make both explicit params, not
   optional afterthoughts, since forgetting `type` is a guaranteed `400`), `favourites-api.ts` (page-based, `type`
   truly optional).
2. **Cart state**: per (type, seller) — do not model this as one global cart object. A reasonable shape: a map keyed
   by `` `${cart_type}:${sellerId ?? 0}` ``, lazily fetched. Drive the header badge from `GET /buyer/cart/summary/`'s
   grand `item_count` (poll/refetch after any add/edit/remove/clear) rather than summing the per-cart `GET` calls
   yourself.
3. **Add to cart button** (product/gig detail page): on click, SKU/variant must already be resolved (size/colour
   picker → `listing_sku` id) before calling `POST`; show stock/duration validation client-side first where cheap,
   but always handle the `400` from the server as the real source of truth (stock can change between page load and
   click).
4. **Per-seller cart view**: reachable from a seller's page or a product/gig card ("view cart with this seller") —
   `GET ...&seller=<id>`, and `&seller=0` for admin-owned-listing carts if your catalog has any.
4.1. **"All carts" page / header dropdown**: `GET /buyer/cart/summary/`, one row per cart, each linking to its own
   `GET ...?type=&seller=` detail page.
5. **Cart page**: line list with qty/duration stepper (`PATCH`, replace not add — don't accumulate client-side
   deltas, always send the new absolute value), remove button (`DELETE`), `available: false` lines shown visibly
   disabled/flagged but not hidden, running `subtotal` from the response (don't compute it client-side), "clear
   cart" button.
6. **Wishlist/heart icon**: on every product/gig card and detail page — toggle, optimistic UI fine since both
   directions are idempotent/always-succeed from the frontend's perspective (`400` only for an invisible listing,
   which shouldn't be reachable if the card is already rendering it).
7. **Wishlist page**: reuse the existing product/gig card components (`listing` field is the identical shape),
   `type` filter tabs (all/product/service), page-based "load more" or numbered pages matching the rest of the Buyer
   Panel.
8. Empty states: no cart yet (`null` response) vs. cart with zero lines (after clearing) are different UI states —
   distinguish them. Same for wishlist: never-saved-anything vs. filtered-to-zero-for-this-type.

## 4. Verify (browser, buyer token; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Add a product from seller A, then a product from seller B | two separate carts; `GET ...&seller=A` and `...&seller=B` each show only that seller's line |
| 2 | Add a gig from seller A (same seller as #1's product) | separate cart from the product one — `cart_type` differs, lines never mix |
| 3 | Add same SKU twice (`qty=2` then `qty=3`) | one line, `qty=5`, not two lines |
| 4 | `GET /buyer/cart/?type=product` with no `&seller=` after touching two sellers' carts | returns whichever was touched most recently, not both/merged |
| 5 | `PATCH` a line with `{"qty": 1}` after it was `qty=5` | becomes exactly `1`, not `6` (replace, not add) |
| 6 | `PATCH` a gig line with `{"qty": 1}` (wrong field) | `400` |
| 7 | Deactivate a SKU already in cart (admin/seller side), then `GET` the cart | line still present, `available: false` |
| 8 | `DELETE /buyer/cart/?type=product&seller=A` | that cart's lines gone, cart row still exists (`GET` after returns it with empty `items`, not `null`) |
| 9 | Missing `?type=` on any cart route | `400`, handled gracefully, not a crash |
| 10 | Save a listing twice | second call `200` with same `id`, not a duplicate row |
| 11 | Un-save a listing never saved | `204`, no error shown |
| 12 | Favourite a listing, then have its seller go inactive (admin side) | drops out of `GET /buyer/favourites/`; reappears once seller active again |
| 13 | Wishlist list with `?type=service` vs no `type` | filtered vs both kinds mixed, newest first either way |
| 14 | Add-to-cart on a listing that fails the visibility rule (if reachable) | `400 {"listing": [...]}`, not a 500 |
| 15 | `GET /buyer/cart/summary/` after adding to two different sellers' product carts | two rows, correct per-cart `item_count`/`subtotal`, grand `item_count` = 2 |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
