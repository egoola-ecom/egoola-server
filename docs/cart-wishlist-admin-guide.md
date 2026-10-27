# Cart & Wishlist — Admin Oversight API

**Read-only.** An admin can see every buyer's cart and wishlist, list and filter them, and look at one in detail —
there is no create, update or delete here. A buyer manages their own cart and wishlist through the buyer-facing API
instead (`docs/buyer-api-guide.md` sections 3 and 4); this is purely for support and oversight.

Header: `Authorization: Bearer <admin access token>`. Both a plain `admin` and a `super_admin` may use these —
there is no super-admin-only restriction here, unlike Admin Management.

| Token | Result |
|---|---|
| none / invalid | `401` |
| seller or buyer token | `403` |
| admin (either type) | allowed |

**Pagination is cursor-based** on both endpoints, not page-based like the buyer-facing lists: `{next, previous,
results}` — no `count`. Sort with `?ordering=`, default newest first. A row added or removed between two requests
never causes a skipped or repeated row, which offset/page paging cannot promise (same convention as the Seller
Request queue — see `apps/core/pagination.py`, `DefaultCursorPagination`).

**Visibility.** Unlike every buyer-facing list in this project, **nothing is hidden here**: a cart or a favourite is
shown even if the listing it points to is no longer publicly visible (its seller went inactive, the listing itself
was rejected or deleted, and so on). An admin needs the full picture to help a buyer, not the shop-front view. For
wishlists specifically, `listing_visible` says whether that rule currently passes, and can be filtered on.

Postman: `Egoola` → **Carts & Wishlists (admin)**.

---

## 1. Carts — `/api/v1/orders/carts/`

### List — `GET /orders/carts/`

One row per cart (not per item) — item details are only on the detail view.

| Query | Meaning |
|---|---|
| `search` | the buyer's name, email or phone (contains) |
| `buyer` | exact buyer id |
| `cart_type` | `product` \| `service` |
| `is_active` | `true` (still open) \| `false` (closed — became an order) |
| `has_order` | `true` \| `false` — whether `order` is set |
| `listing` | only carts holding this listing id, in any line |
| `created_from`, `created_to` | `YYYY-MM-DD`, inclusive |
| `ordering` | `created_at` \| `updated_at` \| `id` (prefix `-` for descending; default `-created_at`) |

Filters combine, e.g. `/orders/carts/?cart_type=product&is_active=true&created_from=2026-10-01`. A bad `cart_type` or
`is_active` value is `400`.

```json
{
  "next": null, "previous": null,
  "results": [
    {
      "id": 13,
      "buyer": { "id": 1, "name": "Test Buyer", "email": "test.buyer@egoola.com", "phone": "+8801700000003",
                  "profile_pic_url": null, "wallet_balance": "0.00", "status": "active" },
      "cart_type": "product", "is_active": true, "order": null,
      "item_count": 1, "subtotal": "200.00",
      "created_at": "2026-10-27T17:08:16+06:00", "updated_at": "2026-10-27T17:08:16+06:00"
    }
  ]
}
```

`order` is the linked order's id, or `null` while the cart is still open — there is no order detail API yet.
`subtotal` is worked out live (current prices), the same as the buyer's own view of their cart.

### Retrieve — `GET /orders/carts/{id}/`

Everything from the list row, plus `items` (full line detail) and the cart's own audit columns. Unknown id → `404`.

```json
{
  "id": 13, "buyer": { "...": "as above" }, "cart_type": "product", "is_active": true, "order": null,
  "item_count": 1, "subtotal": "200.00",
  "items": [
    { "id": 19,
      "listing": { "id": 245, "title": "Cotton T-Shirt", "title_bn": null, "slug": "cotton-t-shirt",
                    "image_url": null, "catalog_type": "product" },
      "listing_sku": { "id": 273, "sku": null, "price": "100.00", "discounted_price": "100.00",
                        "price_type": null, "is_active": true },
      "qty": 2, "duration": null, "color": null, "size": null,
      "unit_price": "100.00", "line_subtotal": "200.00", "available": true,
      "created_by": 1, "creator_type": "user", "creator_name": "Test Buyer",
      "updated_by": null, "updater_type": null, "updater_name": null,
      "created_at": "...", "updated_at": "..." } ],
  "created_by": 1, "creator_type": "user", "creator_name": "Test Buyer",
  "updated_by": null, "updater_type": null, "updater_name": null,
  "created_at": "...", "updated_at": "..."
}
```

`available` on a line is the same flag the buyer sees on their own cart: `false` once the SKU has gone inactive, the
listing is no longer approved, or stock can no longer cover `qty` — the line is never removed for this, only flagged.

---

## 2. Wishlists (favourites) — `/api/v1/engagement/favourites/`

### List — `GET /engagement/favourites/`

One row per saved listing.

| Query | Meaning |
|---|---|
| `search` | the buyer's name/email/phone, or the listing's title (English or Bangla) |
| `buyer` | exact buyer id |
| `listing` | exact listing id |
| `catalog_type` | `product` \| `service` (of the saved listing) |
| `listing_visible` | `true` \| `false` — whether the listing currently passes the buyer-facing visibility rule |
| `created_from`, `created_to` | `YYYY-MM-DD`, inclusive |
| `ordering` | `created_at` \| `id` (prefix `-` for descending; default `-created_at`) |

```json
{
  "next": null, "previous": null,
  "results": [
    {
      "id": 10,
      "buyer": { "id": 1, "name": "Test Buyer", "email": "test.buyer@egoola.com", "phone": "+8801700000003",
                  "profile_pic_url": null, "wallet_balance": "0.00", "status": "active" },
      "listing": { "id": 245, "title": "Cotton T-Shirt", "title_bn": null, "slug": "cotton-t-shirt",
                    "catalog_type": "product", "status": "approved", "image_url": null,
                    "seller": { "id": 113, "name": "Rafiq Traders", "status": "active", "verification_status": "verified" } },
      "listing_visible": true,
      "created_at": "2026-10-27T17:08:16+06:00"
    }
  ]
}
```

The `listing` block here is **not** the same shape a buyer sees — it carries the listing's raw `status` and the
seller's own `status`/`verification_status`, so an admin can see at a glance *why* `listing_visible` is `false`
(pending/rejected listing, or an inactive/unverified seller) without a second lookup.

### Retrieve — `GET /engagement/favourites/{id}/`

Everything from the list row, plus the favourite's own audit columns (`created_by`, `updated_by`, ...). Unknown id →
`404`.

---

## Testing

`admin_cart_smoke.py` (23 checks): auth, cursor shape, every filter, item count/subtotal, detail items and audit
columns. `admin_favourites_smoke.py` (19 checks): auth, cursor shape, every filter including `listing_visible`
reacting to a seller's standing, and detail audit columns. Run with `scripts/smoke/run_all.sh` or individually
against the dev server (see `scripts/smoke/README.md`). Test data was removed afterwards.
