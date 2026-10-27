# Brief for the Egoola Web session — buyer cart (new backend feature)

Backend done and tested in `egoola-server`: the buyer's own cart. Read this file top to bottom, then build the cart
screens in **Buyer Web**. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/buyer-api-guide.md` section 3 (the technical contract below is a copy of it),
`egoola-server/docs/Egoola_Cart_Guide.md` (plain-language explanation of how a cart behaves — read this one if anything
below is unclear conceptually). Postman: `Egoola-BuyerApp` → **Cart**. Run the backend with
`uv run manage.py runserver 8000`; accounts in `docs/test-accounts.md` (buyer: `test.buyer@egoola.com` /
`Test@12345`).

## 1. What this is

A buyer can add a product or a gig to their cart, see it, change the quantity/duration, remove it, or clear it.
Checkout (turning a cart into an order, Stripe/bKash) is **not built yet** — this is cart only.

Needs a buyer token (`Authorization: Bearer <access>`, same as every other buyer-authenticated call — see
`frontend-api-guide.md`). No token: `401`. A seller or admin token: `403`.

## 2. The core rule: one cart per type, picked automatically

A buyer has at most **one active cart per type** — `product` or `service` (a gig). The two never mix: a product
checkout will go through Stripe, a gig/service checkout through bKash, so they are kept apart from the start.

**The frontend never sends which cart type it means when adding something** — it is decided by the listing's own
`catalog_type`, taken from the product/gig detail you already have (see `public-api-guide.md`). Adding a product
always lands in the product cart; adding a gig always lands in the service cart. You only pick `type` when **reading**
or **clearing** a cart (`?type=product` or `?type=service`), since at that point you need to say which one you want
to look at.

A cart is created automatically the first time something of that type is added — there is no "create a cart" call,
and `GET`/`DELETE` with `?type=` auto-creates one too if none exists yet (so a brand-new buyer's cart page is just an
empty cart, `200`, never a `404`).

## 3. The contract

Base path: `/api/v1/buyer/cart/`.

| Route | Does |
|---|---|
| `GET /buyer/cart/?type=product\|service` | the active cart of that type, items, and a running subtotal |
| `POST /buyer/cart/items/` | add a listing + SKU |
| `PATCH /buyer/cart/items/{id}/` | replace the quantity (product) or duration (gig) of one line |
| `DELETE /buyer/cart/items/{id}/` | remove one line |
| `DELETE /buyer/cart/?type=product\|service` | empty the cart (it stays active, ready for more) |

### Add to cart — `POST /buyer/cart/items/`

```json
{ "listing": 103, "listing_sku": 113, "qty": 2 }
```

| Field | Product | Gig |
|---|---|---|
| `listing` | required — the listing id | same |
| `listing_sku` | required — the **exact SKU** id (the variant/package the buyer picked on the detail page, from `skus`/`packages` in the product/gig detail response), not just the listing id | same |
| `qty` | required, ≥ 1 | not accepted — `400` if sent |
| `duration` | not accepted — `400` if sent | required, ≥ 1 (hours/days/weeks/months, matching the SKU's `price_type`) |

**Adding the same SKU again merges into the existing line** — the response is still `201`, but it is the *same* cart
item id, with `qty` (or `duration`) summed, not a new line. Design the "Add to cart" button to not assume a brand-new
line every time; re-fetch or trust the returned item.

Errors: an invisible/unknown listing or a SKU from a different listing is `400`:
```json
{ "listing": ["Invalid pk \"999\" - object does not exist."] }
{ "listing_sku": ["Does not belong to this listing."] }
```
Missing/wrong field for the kind: `{"qty": ["This field is required."]}`, `{"duration": ["Not used for a product."]}`,
etc. Over stock: `{"qty": ["Not enough stock."]}`.

Success `201`:
```json
{ "id": 1,
  "listing": { "id": 103, "title": "Cotton T-Shirt", "title_bn": "...", "slug": "cotton-t-shirt",
               "image_url": "/media/...", "catalog_type": "product" },
  "listing_sku": { "id": 113, "sku": "TEE-001", "price": "100.00", "discounted_price": "100.00",
                    "price_type": null, "is_active": true },
  "qty": 2, "duration": null, "color": "Blue", "size": "M",
  "unit_price": "100.00", "line_subtotal": "200.00", "available": true, "created_at": "..." }
```

`color`/`size` are a best-effort text label of the SKU's variant (may be `null` — don't rely on them over
`listing_sku`). `unit_price`/`line_subtotal` are worked out **live, every time** — never cache them client-side longer
than one screen render; re-fetch the cart to get current numbers (a sale can start or end between visits).

`available` is `false` when the SKU has since gone inactive, the listing is no longer approved, or stock can no
longer cover `qty`. **The line is not removed when this happens** — show it with a clear "no longer available"
state (e.g. greyed out, badge) and let the buyer remove it themselves; do not auto-delete it client-side either.

### The cart — `GET /buyer/cart/?type=product`

```json
{ "id": 1, "cart_type": "product", "is_active": true,
  "items": [ { "...": "one row as shown above" } ],
  "subtotal": "200.00", "created_at": "...", "updated_at": "..." }
```

`type` is required — missing or anything other than `product`/`service` is `400`. An empty cart is `items: []`,
`subtotal: "0.00"`, still `200`.

### Edit / remove a line

`PATCH /buyer/cart/items/{id}/` **replaces** the value, it does not add to it (`{"qty": 1}` sets it to exactly 1,
unlike the merge-on-add behavior of `POST`). Sending `duration` on a product line, or `qty` on a gig line, is `400`.

`DELETE /buyer/cart/items/{id}/` removes one line — `204`. Both are scoped to the logged-in buyer's own items:
another buyer's item id (or a made-up id) is `404`, indistinguishable from "doesn't exist" — do not treat it
specially.

`DELETE /buyer/cart/?type=product|service` clears every line — `204`. The cart row itself is untouched and stays
active; there is nothing further to do on the frontend besides refreshing the (now empty) cart view.

## 4. Tasks

1. **Cart API client** (`cart-api.ts` or similar): `getCart(type)`, `addItem({listing, listing_sku, qty?, duration?})`,
   `updateItem(id, {qty?, duration?})`, `removeItem(id)`, `clearCart(type)`.
2. **"Add to cart" action** on product and gig cards/detail pages: send the chosen SKU id (from the variant/package
   picker already built for Products/Gigs), and `qty` or `duration` depending on `catalog_type`. Show a toast/badge
   update from the response, not a guessed local increment.
3. **Two cart views** (or one view with a product/service tab) — a cart icon or page for each type is fine; they are
   genuinely separate baskets with separate subtotals, don't merge them visually into one total.
4. Each cart line: image, title, variant label (`color`/`size`, or fall back to `listing_sku.sku`), a quantity
   stepper (product) or a duration input (gig) that calls `PATCH` on change, a remove button, line subtotal, and an
   "unavailable" indicator driven by `available: false`.
5. **Empty state**: a cart with `items: []` is normal, not an error — show "your cart is empty", not a blank/error
   screen.
6. **Clear cart** button per type, confirming before calling `DELETE /buyer/cart/?type=...`.
7. **Auth gating**: "Add to cart" when signed out should prompt login (reuse the existing buyer auth flow), not call
   the API and show a raw 401.
8. Cart total badge (e.g. a count in the header) should reflect whichever cart(s) have items — decide per design
   whether to show one combined count or two.

## 5. Verify (browser, buyer role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | New buyer, open the cart page before adding anything | empty cart, `200`, no error |
| 2 | Add a product, then add the same exact variant again | one line, quantity summed (not two lines) |
| 3 | Add a different variant of the same listing | a second, separate line |
| 4 | Add a gig (duration-based) | shows in a separate cart/tab from products |
| 5 | Change quantity via the stepper | `PATCH`, line and subtotal update, does not add on top of the old value |
| 6 | Try to set quantity above available stock | blocked or `400` shown clearly |
| 7 | Remove one line | that line gone, others and the subtotal unaffected |
| 8 | Clear the whole cart | empty state shown, cart still usable for a new add right after |
| 9 | Add something, then (via admin/Postman) pause that seller or deactivate the SKU, reload the cart | line stays, now marked unavailable |
| 10 | Sign out, try to view/add to cart | prompted to log in, no raw 401 shown |
| 11 | A sale starts on an item already in the cart, reload the cart | price updates to the sale price (nothing was cached stale) |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
