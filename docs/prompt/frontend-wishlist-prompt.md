# Brief for the Egoola Web session — buyer wishlist (new backend feature)

Backend done and tested in `egoola-server`: the buyer's own wishlist (favourites). Read this file top to bottom, then
build the wishlist screens/controls in **Buyer Web**. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/buyer-api-guide.md` section 4 (the technical contract below is a copy of it),
`egoola-server/docs/Egoola_Cart_Guide.md` Part II (plain-language explanation of how the wishlist behaves — read this
one if anything below is unclear conceptually; Part I there also covers the cart, already built). Postman:
`Egoola-BuyerApp` → **Favourites**. Run the backend with `uv run manage.py runserver 8000`; accounts in
`docs/test-accounts.md` (buyer: `test.buyer@egoola.com` / `Test@12345`).

## 1. What this is

A buyer can save a product or a gig to look at later, with no quantity, no duration, and no relation to the cart —
it is a plain bookmark, not an intent to buy. Needs a buyer token (`Authorization: Bearer <access>`, same as the
cart — see `frontend-api-guide.md`). No token: `401`. A seller or admin token: `403`.

**This is a single list** — unlike the cart, there is no split between product and service. A product and a gig can
sit in the same list; `?type=` only filters what you ask for, it does not change where something is saved.

**It is a toggle, not a stateful form.** Saving something already saved, or removing something never saved, are both
successful no-ops — the frontend never needs to check "is this already saved?" before acting, just fire the request
the heart icon implies and trust the response.

## 2. The contract

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

## 3. Tasks

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

## 4. Verify (browser, buyer role; record results)

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

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
