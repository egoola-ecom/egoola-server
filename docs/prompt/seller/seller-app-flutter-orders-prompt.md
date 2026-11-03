# Brief for the Egoola Seller App session (Flutter) — Orders (new backend feature)

Target app: **`egoola-seller`** (Flutter, the seller mobile app). This extends the app built by the earlier
"build every seller feature" and "Jobs & Bidding" prompts — already shipped and working. Backend
(`egoola-server`, Django REST) is done and tested: the orders placed against this seller's shop. Build it
following the exact same stack, repository pattern and conventions the app already uses — **do not** introduce
a second pattern.

**Out of scope** (not built on the backend yet): a seller editing a delivery address or the Payment Gateway
list (admin-only), coupons/discounts, delivery-cost pricing, any gateway besides Cash on Delivery, push
notifications for a new order.

Do not push to any remote. Commit locally only when asked. Do not change `egoola-server`; if the contract looks
wrong or something is missing, stop and report it.

## 0. Read first (in this order)

1. This file.
2. `egoola-server/docs/seller/seller-order-api-guide.md` — the seller contract (summarized below, read the full
   document for anything ambiguous).
3. `egoola-server/docs/Egoola_Order_Guide.md` — plain-language version. Read the **status flow at the very
   top** first; it's the single most important thing in this whole feature.
4. `egoola-seller/PHASES.md` (your own checklist) and `egoola-document/Egoola_Phase_Tracker.md` (Seller App
   rows). Update `PHASES.md` as work lands.
5. Test accounts: `egoola-server/docs/test-accounts.md` (seller: phone `0100000002`, password `Test@12345` —
   must be **verified and active**; check that account's state first, or use/approve a fresh one). Postman (use
   it to see real responses): `egoola-server/postman/seller/Egoola-SellerApp.postman_collection.json` → **Orders
   (needs an approved, active seller)** folder, with `Egoola-Local.postman_environment.json`.

## 1. What this is

An order is placed by a buyer against this seller's shop (checkout isn't a seller concern at all — see the
Order Guide). The seller's job is to **move it forward, one step at a time**: `pending` → `accepted` or
`rejected` (a reason is required and buyer-visible) → `in_progress` → `shipped` → `delivered`. Marking an order
`delivered` also flips its payment from `due` to `paid` automatically — nothing extra to do for that.

Three things to build:

1. **Orders list** — every order placed with this seller, filterable by status.
2. **Order detail** — buyer info, every item, the delivery address, the Payment (with its own status and
   history), and this order's own status history.
3. **Move it forward** — accept / reject / in_progress / shipped / delivered, from the detail screen.

**Pagination** is cursor-based here (`next`/`previous`/`results`, **no `count`**) — same shape as the job board.
Reuse the cursor-based infinite-scroll controller already built for that; don't try to compute a page count.

## 2. The contract

| Call | What it does |
|---|---|
| `GET /seller/orders/` | orders placed with me. Filters: `status`, `created_from`/`created_to` (`YYYY-MM-DD`). Search: buyer name/phone/email. |
| `GET /seller/orders/{id}/` | detail |
| `PATCH /seller/orders/{id}/` | move it forward (see the table below) |

### Moving an order forward

| Current `status` | Send | Notes |
|---|---|---|
| `pending` | `{"status": "accepted"}` | |
| `pending` | `{"status": "rejected", "reason": "..."}` | `reason` **required** — shown to the buyer. |
| `accepted` | `{"status": "in_progress"}` | |
| `in_progress` | `{"status": "shipped"}` | |
| `shipped` | `{"status": "delivered"}` | Payment flips `due → paid` automatically; no separate call needed. |

Any other move — skipping a step, acting on a terminal order (`rejected`, `cancelled`, already `delivered`) —
is refused:
```json
{ "status": ["Cannot move an order from pending to delivered."] }
```
The response to a successful `PATCH` is always the **full detail shape** (same as a `GET`), not just the two
fields sent — refresh the whole order card from it, don't merge partial state.

### Detail (shortened)

```json
{
  "id": 104, "order_type": "product",
  "buyer": { "id": 1, "name": "...", "email": "...", "phone": "...", "wallet_balance": "0.00", "status": "active" },
  "status": "pending", "payment_status": "due",
  "subtotal": "450.00", "delivery_cost": "0.00", "discount": "0.00", "total": "450.00", "payable": "450.00",
  "items": [ { "id": 104, "listing": 1777, "title_snapshot": "...", "price_snapshot": "150.00", "qty": 3,
                "total": "450.00", "subtotal": "450.00" } ],
  "address": { "name": "...", "phone": "...", "address_line1": "...", "...": "..." },
  "payment": { "id": 7, "status": "due", "amount": "450.00", "method": "Cash on Delivery",
                "status_histories": [ { "previous_status": null, "current_status": "due", "created_at": "..." } ] },
  "status_histories": [ { "previous_status": null, "current_status": "pending", "reason": null, "created_at": "..." } ],
  "cancelled_reason": null, "rejected_reason": null
}
```

### Errors

| Case | Response |
|---|---|
| An out-of-order move | `{"status": [...]}`, `400` |
| `rejected` without `reason` | `{"reason": ["A reason is required to reject an order."]}`, `400` |
| Order id unknown, or placed with a different seller | `404` |
| Seller can't operate (pending/rejected, or paused) | `403` |

## 3. Tasks

1. **Repository/API layer**: `getOrders` (cursor, filters), `getOrder`, `updateOrderStatus` — same HTTP client
   and error-mapping pattern the Jobs & Bidding feature already uses.
2. **Orders list screen**: status filter chips, infinite-scroll list (buyer name, status badge, payable,
   created date), pull-to-refresh.
3. **Order detail screen**: buyer card, items list, address card, a Payment card (status badge + a small
   timeline of its `status_histories`), the order's own status timeline, and the forward-move action — a
   button (or menu) offering only the moves valid from the current status, greyed out/hidden otherwise. Reject
   opens a dialog that requires typing a reason before it enables Submit.
4. Status badges/colors: reuse whatever palette the Jobs & Bidding feature already uses for job/bid statuses,
   extended with the order-specific ones (`shipped`, `delivered`).
5. Entry point: add **Orders** to wherever the seller app's main navigation already lists Jobs & Bidding,
   Products, Gigs.

## 4. Verify (device/emulator, seller role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | List orders, filter by `status=pending` | only pending ones show |
| 2 | Open one, check buyer/items/address/payment all render | everything present, payment status `due` |
| 3 | Accept it | status → `accepted`, screen refreshes from the full detail response |
| 4 | Try to jump it straight to `delivered` | blocked client-side or `400` handled gracefully |
| 5 | Move it `in_progress` → `shipped` → `delivered` | each step succeeds; on delivered, payment card shows `paid` and a new history row |
| 6 | On a different (fresh) order, reject with no reason | blocked client-side, or `400` surfaced under the reason field |
| 7 | Reject with a reason | status → `rejected`, reason shown on the card |
| 8 | Try to act on that rejected order again | blocked — it's terminal |
| 9 | Open an order placed with a *different* seller (if reachable, e.g. by id manipulation) | `404`, handled gracefully |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
