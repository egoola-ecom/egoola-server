# Brief for the Egoola Web session — admin oversight of carts & wishlists (new backend feature)

Backend done and tested in `egoola-server`: two **read-only** admin APIs for support/oversight — every buyer's cart,
and every buyer's wishlist. Read this file top to bottom, then build the two screens in **Admin Web**. Do not push;
commit locally only if asked.

Read first: `egoola-server/docs/cart-wishlist-admin-guide.md` (the technical contract below is a copy of it),
`egoola-server/docs/buyer-api-guide.md` sections 3–4 (what the buyer-facing cart/wishlist look like — useful context,
not something you're building here), `egoola-server/docs/Egoola_Cart_Guide.md` (plain-language explanation of how a
cart/wishlist behaves, if anything is unclear conceptually). Postman: `Egoola` → **Carts & Wishlists (admin)**. Run
the backend with `uv run manage.py runserver 8000`; accounts in `docs/test-accounts.md` (admin: `test.admin@egoola.com`
or `test.super@egoola.com`, both work here — this is not super-admin-only).

## 1. What this is

**There is nothing to create, edit or delete.** Both screens are list + detail, for an admin to look something up
when helping a buyer (e.g. "what's in this buyer's cart?", "why isn't this buyer's saved item showing for them?").
Don't build forms, action buttons, or any write path — the backend has none.

**Pagination is cursor-based here, not page-based** — the opposite of most of this project's buyer-facing lists, and
the same shape as the Seller Request queue you already built in the seller panel. Reuse that same cursor-list pattern
(a `next`/`previous` cursor, "load more" rather than numbered pages) rather than inventing a new one — do not use
`use-managed-list.ts` or whatever page-based list hook the rest of Admin Web uses, since the response here has no
`count` and no page number.

## 2. The contract

Both need `Authorization: Bearer <admin access token>` (plain admin or super-admin, both work — no restriction like
Admin Management). `{next, previous, results}` on list, no `count`.

### Carts — `GET /api/v1/orders/carts/`

| Query | Meaning |
|---|---|
| `search` | buyer's name, email or phone |
| `buyer` | exact buyer id |
| `cart_type` | `product` \| `service` |
| `is_active` | `true` (open) \| `false` (closed — became an order) |
| `has_order` | `true` \| `false` |
| `listing` | only carts holding this listing id |
| `created_from`, `created_to` | `YYYY-MM-DD` |
| `ordering` | `created_at` \| `updated_at` \| `id` (prefix `-` for descending) |

List row: `id, buyer{id,name,email,phone,profile_pic_url,wallet_balance,status}, cart_type, is_active, order (id or
null), item_count, subtotal, created_at, updated_at`.

`GET /api/v1/orders/carts/{id}/` adds `items[]` (each: `listing{id,title,title_bn,slug,image_url,catalog_type}`,
`listing_sku{id,sku,price,discounted_price,price_type,is_active}`, `qty`, `duration`, `color`, `size`, `unit_price`,
`line_subtotal`, `available`, plus that line's own `created_by`/`creator_type`/`creator_name`/`updated_*`) and the
cart's own audit columns.

`available: false` on a line means the SKU went inactive, the listing is no longer approved, or stock can no longer
cover `qty` — show it as a warning badge on that line, don't hide the line.

### Wishlists — `GET /api/v1/engagement/favourites/`

| Query | Meaning |
|---|---|
| `search` | buyer's name/email/phone, or the listing's title |
| `buyer` | exact buyer id |
| `listing` | exact listing id |
| `catalog_type` | `product` \| `service` |
| `listing_visible` | `true` \| `false` |
| `created_from`, `created_to` | `YYYY-MM-DD` |
| `ordering` | `created_at` \| `id` |

List row: `id, buyer{...same as above...}, listing{id,title,title_bn,slug,catalog_type,status,image_url,
seller{id,name,status,verification_status}}, listing_visible, created_at`.

`GET /api/v1/engagement/favourites/{id}/` adds the favourite's own audit columns.

**Important: nothing is hidden on either screen.** Unlike the buyer's own view of their wishlist, a favourite whose
listing has gone private is still returned here — `listing_visible` tells you which, and `listing.status` /
`listing.seller.status` / `listing.seller.verification_status` tell you *why* (pending/rejected listing, inactive or
unverified seller). Show these plainly rather than filtering the row out — that's the whole point of this being an
admin view instead of the buyer-facing one.

## 3. Tasks

1. **Two API clients**: `admin-carts-api.ts` (`listCarts(filters, cursor?)`, `getCart(id)`) and
   `admin-favourites-api.ts` (`listFavourites(filters, cursor?)`, `getFavourite(id)`), both cursor-based like the
   Seller Request queue client.
2. **Carts screen**: filter bar (search, `cart_type`, `is_active`, `has_order`, date range — `listing`/`buyer` can be
   query-param-only, driven by navigating from elsewhere, e.g. a buyer's detail page), a list/table showing buyer,
   type, open/closed, item count, subtotal, created date, with "load more" cursor paging.
3. **Cart detail** (page or drawer): buyer block, cart metadata (`cart_type`, `is_active`, linked `order` id if any),
   then every line — listing thumbnail/title, variant (`color`/`size` or the SKU code), qty or duration, unit price,
   line subtotal, an "unavailable" badge when `available` is `false`. Show the subtotal total at the bottom.
4. **Wishlist screen**: same filter-bar pattern (search, `catalog_type`, `listing_visible`, date range), a
   list/table showing buyer, the saved listing (title + type), whether it's currently visible, saved date.
5. **Wishlist detail** (page or drawer): the saved listing's full block (title, status, seller name + status +
   verification_status), the buyer who saved it, when, and the favourite's own audit trail.
6. Both screens: empty state ("no carts match" / "no favourites match") distinct from a loading state; a cleared
   filter should reset cursor paging back to the start, not try to keep an old cursor with new filters.
7. Entry points: link to a cart/wishlist from wherever a buyer's own admin detail page already lives, if one exists,
   in addition to a standalone list under the admin nav — your call on the nav location, following whatever pattern
   Buyer Management already uses for its own sub-screens.

## 4. Verify (browser, admin role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Open the carts list with no filters | shows carts across buyers, cursor "load more" works |
| 2 | Filter by `cart_type=service` | only service/gig carts shown |
| 3 | Filter by a buyer id (or search their email) | only that buyer's carts |
| 4 | Open a cart's detail | every line shown with correct qty/duration, prices, subtotal matches the list row |
| 5 | A cart whose listing has since been deactivated | that line shows an "unavailable" badge, is not hidden |
| 6 | Open the wishlist list with no filters | shows favourites across buyers |
| 7 | Filter `listing_visible=false` | only favourites whose listing is currently hidden from buyers |
| 8 | Open a hidden favourite's detail | shows the listing's real status and the seller's status/verification, explaining why it's hidden |
| 9 | Search by listing title on the wishlist screen | matches |
| 10 | Load more / cursor paging on both screens | no duplicate or skipped rows across pages |
| 11 | A non-admin token (if testable from the UI) | handled the same way other admin screens reject it |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
