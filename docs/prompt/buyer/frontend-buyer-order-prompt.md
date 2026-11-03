# Brief for the Egoola Web session — buyer Orders (new backend feature)

Backend done and tested in `egoola-server`: checking out a cart into an order, watching it, and cancelling it.
Read this file top to bottom, then build it in **Buyer Web**. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/buyer/buyer-order-api-guide.md` (the technical contract below is a copy of it),
`egoola-server/docs/Egoola_Order_Guide.md` (plain-language version — read the status flow at the very top
first, it's the single most important thing in this whole feature), `egoola-server/docs/buyer/buyer-address-api-guide.md`
(the Addresses brief builds that screen; this one just consumes it). Postman: `Egoola-BuyerApp` → **Orders**
(and **Addresses**, if that brief hasn't landed yet — build a minimal inline address-create form if so). Run
the backend with `uv run manage.py runserver 8000`; accounts in `docs/test-accounts.md` (buyer:
`test.buyer@egoola.com` / `Test@12345`).

Needs a buyer token (`Authorization: Bearer <access>`). No token: `401`.

---

## 1. What this is

Checkout is **one request**: pick an active cart, a saved address, and a Payment Gateway (today, always Cash on
Delivery — fetch its id from the public gateway list below, don't hardcode it), and that one call creates the
order, its line items, and its payment, together. Pagination for the order list is **page-based**
(`count`/`page`/`page_size`/`total_pages`/`results`), same as every other Buyer Panel list.

Five things to build:
1. **Gateway lookup** (one no-auth call, cache it) feeding the checkout request.
2. **Checkout** from an existing cart (reuse the Cart screen's "Checkout" button).
3. **My orders** list.
4. **Order detail** — items, address, payment, and both status histories.
5. **Cancel** an order, while it's still allowed.

## 2. The contract

| Call | What it does |
|---|---|
| `GET /public/orders/payment-gateways/` | active gateways, no auth, no pagination — see below |
| `POST /buyer/orders/` | checkout: `{"cart": <id>, "address": <id>, "payment_gateway": <id>}` |
| `GET /buyer/orders/` | my orders, page-paginated |
| `GET /buyer/orders/{id}/` | detail |
| `PATCH /buyer/orders/{id}/` | for now, only `{"status": "cancelled", "reason": "..."}` (`reason` optional) |

No separate "cancel" endpoint — it's the general `PATCH` above. (An earlier version of this API had a dedicated
`POST .../cancel/` action; it's gone now, `404`.)

### Gateway lookup

```json
GET /public/orders/payment-gateways/
```
→ `200`, no token needed:
```json
[ { "id": 11, "name": "Cash on Delivery", "slug": "cash-on-delivery", "icon_url": null } ]
```
Pick the row by `slug` (`"cash-on-delivery"` for now) and use its `id` below — **never hardcode the id**, the
DB assigns it and it is not guaranteed to be `1`.

### Checkout

```json
POST /buyer/orders/
{ "cart": 212, "address": 7, "payment_gateway": 11 }
```
→ `201` with the full order (same shape as the detail call, section below).

### Detail (shortened)

```json
{
  "id": 104, "order_type": "product",
  "seller": { "id": 723, "name": "...", "phone": "...", "profile_pic_url": null },
  "status": "pending", "payment_status": "due",
  "subtotal": "450.00", "delivery_cost": "0.00", "discount": "0.00", "total": "450.00", "payable": "450.00",
  "items": [ { "id": 104, "listing": 1777, "listing_sku": 2018, "title_snapshot": "...",
                "price_snapshot": "150.00", "qty": 3, "total": "450.00", "subtotal": "450.00" } ],
  "address": { "name": "...", "address_line1": "...", "...": "..." },
  "payment": { "id": 7, "status": "due", "amount": "450.00", "method": "Cash on Delivery",
                "status_histories": [ { "previous_status": null, "current_status": "due", "created_at": "..." } ] },
  "status_histories": [ { "previous_status": null, "current_status": "pending", "reason": null, "created_at": "..." } ],
  "cancelled_reason": null, "rejected_reason": null
}
```
Render both `status_histories` arrays as a simple timeline (newest first) — one for the order itself, one
nested inside `payment` for the payment's own moves.

### Cancel

```json
PATCH /buyer/orders/104/
{ "status": "cancelled", "reason": "Changed my mind" }
```
Only allowed while `status` is `pending`, `accepted`, or `in_progress` — grey out / hide the Cancel button once
it's `shipped` or later (or terminal). Sending anything other than `cancelled` is refused.

### Errors

| Case | Response |
|---|---|
| `cart` not the buyer's own, empty, already used, or has an unavailable line | `{"cart": [...]}` or a top-level message, `400` |
| `address` not the buyer's own | `{"address": ["Not your saved address."]}`, `400` |
| An inactive `payment_gateway` | `400` |
| Cancel after `shipped` | `{"status": ["This order can no longer be cancelled."]}`, `400` |
| Any other `PATCH` status value | `{"status": ["A buyer can currently only move an order to cancelled."]}`, `400` |
| Unknown id, or another buyer's | `404` |

## 3. Tasks

1. **API client** (`buyer-orders-api.ts`): `listPaymentGateways` (public, no-auth), `checkout`, `listOrders`,
   `getOrder`, `cancelOrder`.
2. **Checkout flow**: from the Cart screen, "Checkout" opens a short form — address picker (with a "new
   address" shortcut into the Addresses create form), payment gateway shown read-only (fetched from
   `listPaymentGateways`, not hardcoded — today it only ever shows "Cash on Delivery"), a summary of the cart
   total, and a Confirm button that calls `POST /buyer/orders/` with that gateway's `id`. On success, navigate
   to the new order's detail.
3. **My orders list**: page-based list (seller name/avatar, status badge, payable, date), status filter if
   useful, links to detail.
4. **Order detail**: items table, address card, a Payment card (status badge + its own mini timeline), the
   order's own status timeline, and a **Cancel** button (with an optional reason field in the confirmation
   dialog) shown only while cancellable.
5. Status badges: give each of `pending/accepted/rejected/in_progress/shipped/delivered/cancelled` its own
   color, consistent with however job/bid statuses are already styled elsewhere in the app.

## 4. Verify (browser, buyer role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Add a product to cart, go to checkout with no saved address | prompted to add one first |
| 2 | Checkout with a cart, an address, Cash on Delivery | `201`, order shows `pending`/`due` |
| 3 | Open the order's detail | items, address, payment and both timelines all render |
| 4 | Try to check out the same cart again | `400`, clear message (cart's already used) |
| 5 | Cancel the order with a reason | `200`, status badge updates to `cancelled`, reason shown, new timeline row |
| 6 | Try to cancel it again | `400`, handled gracefully (not a raw error dump) |
| 7 | My orders list, page through if more than one page exists | paging controls work |
| 8 | No token (if testable) | `401` handled the same as elsewhere |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
