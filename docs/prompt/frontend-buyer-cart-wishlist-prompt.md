# Brief for the Egoola Web session — buyer cart & wishlist (new backend features)

Backend done and tested in `egoola-server`: the buyer's own cart and wishlist. Read this file top to bottom, then
build both in **Buyer Web**. Do not push; commit locally only if asked. (This replaces two earlier, separate prompts
for the same features — `frontend-cart-prompt.md` and `frontend-wishlist-prompt.md` — which went through a few
contract revisions; this file is the current, settled state of both.)

Read first: `egoola-server/docs/buyer/buyer-api-guide.md` sections 3–4 (the technical contracts below are a copy of it),
`egoola-server/docs/Egoola_Cart_Guide.md` (plain-language explanation of how each behaves — Part I is the cart, Part
II the wishlist; read whichever one is unclear conceptually below). Postman: `Egoola-BuyerApp` → **Cart**,
**Favourites**. Run the backend with `uv run manage.py runserver 8000`; accounts in `docs/test-accounts.md` (buyer:
`test.buyer@egoola.com` / `Test@12345`).

Both need a buyer token (`Authorization: Bearer <access>`, same as every other buyer-authenticated call — see
`frontend-api-guide.md`). No token: `401`. A seller or admin token: `403`. Checkout (turning a cart into an order,
Stripe/bKash) is **not built yet** — cart and wishlist only.

---

# Part I — Cart

## 1. What this is

A buyer can add a product or a gig to their cart, see it, change the quantity/duration, remove it, or clear it.

A buyer has at most **one active cart per type AND seller** — `product` or `service` (a gig), and never mixing two
sellers in the same cart. A product checkout will go through Stripe, a gig/service checkout through bKash, so type
keeps them apart; every order is always placed with exactly one seller, so seller keeps them apart too. A buyer
shopping from three sellers for products simply has three separate product carts running at once.

**`GET`/`DELETE` always act on exactly one cart, never several.** You tell them which one two ways:

- **Name the seller** (`&seller=<id>`, or `&seller=0` for the shared cart of admin-owned listings) — use this on a
  product or gig's own page, to ask "does the buyer already have a cart going with *this* seller?"
- **Name nothing** — then it's whichever active cart of that type the buyer most recently did anything with (added
  to, edited, or removed something from). Use this for a general "my cart" icon or page, where there's no specific
  seller context yet — this is what a buyer lands on.

Neither call ever creates a cart, and neither has anything to show when there's genuinely nothing there: `GET`
returns `null`, `DELETE` is a harmless no-op `204`. **The frontend never sends type or seller when adding something**
— both come from the listing itself (`catalog_type` and its own seller, from the product/gig detail you already have
— see `public-api-guide.md`). A cart is created automatically the first time something of that type and seller is
added — there is no "create a cart" call.

A cart is **never reused**: once it becomes an order (a later step), it closes and the buyer's next add of that type
and seller opens a fresh one.

## 2. The contract

Base path: `/api/v1/buyer/cart/`.

| Route | Does |
|---|---|
| `GET /buyer/cart/?type=product\|service[&seller=]` | that seller's cart, or the most recently touched one if `seller` is left out — `null` if none |
| `POST /buyer/cart/items/` | add a listing + SKU |
| `PATCH /buyer/cart/items/{id}/` | replace the quantity (product) or duration (gig) of one line |
| `DELETE /buyer/cart/items/{id}/` | remove one line |
| `DELETE /buyer/cart/?type=product\|service[&seller=]` | empty that same cart (same lookup as `GET`) — no-op if there is none |

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

This is one **line**, not the cart it landed in. If you need the updated cart right after adding, re-fetch it with
`&seller=<the listing's seller id>`.

`color`/`size` are a best-effort text label of the SKU's variant (may be `null` — don't rely on them over
`listing_sku`). `unit_price`/`line_subtotal` are worked out **live, every time** — never cache them client-side longer
than one screen render; re-fetch the cart to get current numbers (a sale can start or end between visits).

`available` is `false` when the SKU has since gone inactive, the listing is no longer approved, or stock can no
longer cover `qty`. **The line is not removed when this happens** — show it with a clear "no longer available"
state (e.g. greyed out, badge) and let the buyer remove it themselves; do not auto-delete it client-side either.

### The cart — `GET /buyer/cart/?type=product`

```json
{ "id": 1, "cart_type": "product", "seller": { "id": 211, "name": "Rafiq Ahmed", "profile_pic_url": null },
  "is_active": true, "items": [ { "...": "as above" } ],
  "subtotal": "200.00", "created_at": "...", "updated_at": "..." }
```

A single object, or `null`. `type` is required — missing or anything other than `product`/`service` is `400`.
`seller: null` is the shared cart for admin-owned listings. With no `&seller=`, this is "whatever the buyer was last
doing" — the right call for a generic cart icon/page on landing. With `&seller=<id>` (or `0`), it's that specific
seller's cart, regardless of recency — the right call from a product/gig detail page, to show "you already have 2 of
these" or similar for *that* seller specifically.

### Edit / remove a line

`PATCH /buyer/cart/items/{id}/` **replaces** the value, it does not add to it (`{"qty": 1}` sets it to exactly 1,
unlike the merge-on-add behavior of `POST`). Sending `duration` on a product line, or `qty` on a gig line, is `400`.

`DELETE /buyer/cart/items/{id}/` removes one line — `204`. Both are scoped to the logged-in buyer's own items:
another buyer's item id (or a made-up id) is `404`, indistinguishable from "doesn't exist" — do not treat it
specially.

`DELETE /buyer/cart/?type=product|service[&seller=]` clears the one cart that same lookup would find (named seller,
or the most recently touched one) — `204` either way, even if there was nothing there. The cart row is untouched and
stays active; there is nothing further to do on the frontend besides refreshing the (now empty) cart view.

## 3. Tasks

1. **Cart API client** (`cart-api.ts` or similar): `getCart(type, seller?)` (returns an object or `null`),
   `addItem({listing, listing_sku, qty?, duration?})`, `updateItem(id, {qty?, duration?})`, `removeItem(id)`,
   `clearCart(type, seller?)`.
2. **"Add to cart" action** on product and gig cards/detail pages: send the chosen SKU id (from the variant/package
   picker already built for Products/Gigs), and `qty` or `duration` depending on `catalog_type`. On that same page,
   you can call `getCart(catalog_type, listing.seller ?? 0)` to show "already in your cart" state for this seller.
   Show a toast/badge update from the response, not a guessed local increment.
3. **A "my cart" icon/page** that calls `getCart(type)` with no seller — whichever cart the buyer was last touching.
   If a buyer wants to see a *different* seller's cart (one they're not currently "in"), the natural way to reach it
   is from that seller's page or one of their listings, not from the generic cart icon — don't try to build a
   combined "all my carts" view unless design explicitly asks for one later.
4. Cart line: image, title, variant label (`color`/`size`, or fall back to `listing_sku.sku`), a quantity stepper
   (product) or a duration input (gig) that calls `PATCH` on change, a remove button, line subtotal, and an
   "unavailable" indicator driven by `available: false`.
5. **Empty state**: `null` from `GET` is normal, not an error — show "your cart is empty" (or, for a seller-specific
   lookup, "nothing from this seller yet"), not a blank/error screen.
6. **Clear** action on the cart view, confirming before calling `DELETE` with the same `type`/`seller` the view is
   currently showing.
7. **Auth gating**: "Add to cart" when signed out should prompt login (reuse the existing buyer auth flow), not call
   the API and show a raw 401.
8. Cart total badge (e.g. a count in the header): since there's no single combined-list endpoint, show just the
   "latest" cart's count (what `getCart(type)` with no seller returns) — don't build a client-side aggregation
   across sellers for this.

## 4. Verify (browser, buyer role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | New buyer, open the cart page before adding anything | `null`, `200`, no error |
| 2 | Add a product, then add the same exact variant again | one line, quantity summed (not two lines) |
| 3 | Add a different variant of the same listing | a second, separate line, same cart |
| 4 | Add a product from seller A, then from seller B | `getCart(type)` with no seller now shows seller B's cart (most recent); `getCart(type, A)` still shows seller A's, untouched |
| 5 | Add to seller A's cart again | `getCart(type)` with no seller now shows seller A's cart again |
| 6 | Add two different admin-owned (no-seller) listings | both land in the same cart (`seller=0`), not two |
| 7 | Add a gig (duration-based) | separate from the product cart(s) entirely (`type=service`) |
| 8 | Change quantity via the stepper | `PATCH`, line and subtotal update, does not add on top of the old value |
| 9 | Try to set quantity above available stock | blocked or `400` shown clearly |
| 10 | Remove one line | that line gone, the cart's own subtotal updates, other carts (other sellers) unaffected |
| 11 | Clear the currently-shown cart | empty state shown, that cart still usable for a new add right after |
| 12 | Add something, then (via admin/Postman) pause that seller or deactivate the SKU, reload | line stays, now marked unavailable |
| 13 | Sign out, try to view/add to cart | prompted to log in, no raw 401 shown |
| 14 | A sale starts on an item already in the cart, reload | price updates to the sale price (nothing was cached stale) |

---

# Part II — Wishlist

## 5. What this is

A buyer can save a product or a gig to look at later, with no quantity, no duration, and no relation to the cart —
it is a plain bookmark, not an intent to buy.

**This is a single list** — unlike the cart, there is no split between product and service, and no split by seller
either. A product and a gig, from any sellers, can all sit in the same list; `?type=` only filters what you ask for,
it does not change where something is saved.

**It is a toggle, not a stateful form.** Saving something already saved, or removing something never saved, are both
successful no-ops — the frontend never needs to check "is this already saved?" before acting, just fire the request
the heart icon implies and trust the response.

## 6. The contract

Base path: `/api/v1/buyer/favourites/`.

| Route | Does |
|---|---|
| `GET /buyer/favourites/?type=product\|service` (`type` optional) | the buyer's saved listings, newest first, page-based paging |
| `POST /buyer/favourites/` | save a listing |
| `DELETE /buyer/favourites/{listing_id}/` | un-save — **keyed by the listing's own id**, not a favourite row id |

### Save — `POST /buyer/favourites/`

```json
{ "listing": 103 }
```

Same visibility rule as the cart and public browsing — an invisible/unknown listing is `400`:
```json
{ "listing": ["Invalid pk \"999\" - object does not exist."] }
```

**Saving an already-saved listing returns the existing row, `200` (not `201`, and not a second row).** Treat both
`200` and `201` as success in your client code — don't branch UI behavior on which one came back.

```json
{ "id": 1, "catalog_type": "product",
  "listing": { "id": 103, "title": "Cotton T-Shirt", "...": "the exact same row shape as GET /public/catalog/products/" },
  "created_at": "..." }
```

`listing` is the identical row shape you already render on the browse/search screens (`public-api-guide.md` sections
4–5) — reuse your existing product/gig card component, don't build a new one. `catalog_type` on the favourite itself
(`"product"` or `"service"`) tells you which shape `listing` is in, so you don't need to sniff its fields.

### List — `GET /buyer/favourites/?type=product`

Page-based paging, same convention as everywhere else in the Buyer Panel: `{count, page, page_size, total_pages,
results}`. Omit `type` to get both kinds together; a bad value is `400`.

**A saved listing can silently disappear from this list and come back later** — if its seller goes inactive or the
listing is taken down, it drops out (not deleted) until it's public again. Don't treat a shrinking list as an error,
and don't assume "once loaded, always there" — a pull-to-refresh or revisit can legitimately show fewer items than
before.

### Remove — `DELETE /buyer/favourites/{listing_id}/`

Always `204`, whether or not it was actually saved. Fire-and-forget from a heart icon's "un-save" tap; no need to
confirm existence first.

## 7. Tasks

1. **Favourites API client**: `listFavourites({type}?)`, `saveFavourite(listingId)`, `removeFavourite(listingId)`.
2. **Heart/bookmark toggle** on every product and gig card and detail page (browse, search, seller page — wherever a
   listing is already rendered): filled when saved, outline when not. On tap, call save or remove based on current
   state, then reflect the server's response (don't just flip the icon optimistically and assume success — a `404`
   on removing a listing whose owning seller account vanished, for instance, should still resolve to "not saved").
3. **A wishlist page**: one combined list by default; add a product/service filter control using `?type=` if the
   design calls for tabs, but it is optional — unlike the cart, these are not fundamentally separate baskets.
4. Each row: the listing card (reuse the product/gig card component), with a remove/un-save action (the same heart
   toggle, or an explicit "Remove" button — either is fine).
5. **Empty state**: `results: []` is normal — "nothing saved yet", not an error.
6. **Auth gating**: tapping the heart while signed out should prompt login, not call the API and show a raw 401.
7. No connection to the cart screens is needed — do not add "move to cart" unless explicitly asked for; saving and
   buying are deliberately separate actions on the backend (see the guide, Part II section 12).

## 8. Verify (browser, buyer role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Save a product from a listing card | heart fills, no page reload needed |
| 2 | Tap save again on the same listing | still saved, no duplicate, no visible flicker/error |
| 3 | Save a gig | appears in the wishlist alongside the product (or in its own filtered tab if built) |
| 4 | Open the wishlist page fresh | shows both saved items, newest first |
| 5 | Un-save one item | disappears from the list immediately |
| 6 | Un-save it again (double-tap, or a stale UI state) | no error shown, ends up not-saved either way |
| 7 | (Via admin/Postman) deactivate the seller of a saved listing, reload the wishlist | that item is gone from the list, not shown as broken |
| 8 | Reactivate that seller, reload | the item is back, still marked saved |
| 9 | Sign out, tap a heart icon | prompted to log in, no raw 401 shown |
| 10 | Empty wishlist (new buyer) | clear "nothing saved yet" state, not a blank/error screen |

---

Report which cases pass (both parts), what you changed, and anything in the backend docs that looked wrong or unclear.
