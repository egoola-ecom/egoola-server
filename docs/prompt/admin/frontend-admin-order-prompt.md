# Brief for the Egoola Web session — admin Orders (new backend feature)

Backend done and tested in `egoola-server`: full admin oversight of every order on the platform, with no
restriction on moving its status. Read this file top to bottom, then build it in **Admin Web**. Do not push;
commit locally only if asked.

Read first: `egoola-server/docs/admin/admin-order-api-guide.md` (the technical contract below is a copy of it),
`egoola-server/docs/Egoola_Order_Guide.md` (plain-language version — read the status flow at the very top
first), `egoola-server/docs/admin/admin-payment-gateway-api-guide.md` (if the Payment Gateways screen from that brief
hasn't landed yet, build it alongside this one — it's a short, separate screen). Postman: `Egoola` → **Orders
(admin)** and **Payment Gateways (admin)**. Run the backend with `uv run manage.py runserver 8000`; accounts in
`docs/test-accounts.md` (admin: `test.admin@egoola.com` / `Test@12345`).

Needs an admin token (`Authorization: Bearer <access>`). No token: `401`. A seller or buyer token: `403`.

---

## 1. What this is

Admin sees **every** order and can move any of them to **any status, at any time** — no transition rule the
way the seller's own screen has. This is the safety valve for fixing a mistake or a dispute. Pagination here is
cursor-based (`next`/`previous`/`results`, no `count`) — same shape as every other admin oversight screen
(Carts & Wishlists, the Bidding panel).

Three things to build:

1. **Orders list** — filterable, searchable, cursor-paged.
2. **Order detail** — buyer, seller, every item, address, Payment (with its own history), this order's own
   history, and the audit columns.
3. **Status override** — a control that can send any status, from any status, with an optional reason.

(The Payment Gateways screen is covered in its own brief —
`frontend-admin-payment-gateway-prompt.md` — build both if neither exists yet; they share a nav location.)

## 2. The contract

| Call | What it does |
|---|---|
| `GET /orders/orders/` | every product order. Filters: `buyer`, `seller`, `status`, `order_type`, `created_from`/`created_to`. Search: buyer name/phone, seller name. |
| `GET /orders/orders/{id}/` | full detail |
| `PATCH /orders/orders/{id}/` | `{"status": "...", "reason": "..."}` — any status, any time, no check |

### Status override

```json
PATCH /orders/orders/104/
{ "status": "delivered" }
```
→ `200`, full detail, `payment.status` flips to `paid` if it was `due` (same automatic rule as the seller's own
`delivered` move).

```json
PATCH /orders/orders/104/
{ "status": "rejected", "reason": "Fraud check failed" }
```
`reason` is accepted and recorded into `rejected_reason`/`cancelled_reason` (matching whichever status is sent)
but is **never required** here, unlike the seller's own reject. Still, the form should offer a reason field for
`rejected`/`cancelled` and encourage filling it in — it's permanently recorded on the order's history either
way, with or without one.

Because there's no transition rule, the status picker should offer **every** status, always — don't grey any
out, unlike the seller's own screen.

### Detail (shortened)

```json
{
  "id": 104, "order_type": "product",
  "buyer": { "id": 1, "name": "...", "...": "..." }, "seller": { "id": 723, "name": "...", "...": "..." },
  "status": "pending", "payment_status": "due",
  "subtotal": "450.00", "delivery_cost": "0.00", "discount": "0.00", "total": "450.00", "payable": "450.00",
  "items": [ "..." ], "address": { "...": "..." },
  "payment": { "id": 7, "status": "due", "amount": "450.00", "method": "Cash on Delivery",
                "status_histories": [ "..." ] },
  "status_histories": [ "..." ],
  "created_by": 1, "creator_type": "user", "creator_name": "...", "updated_by": null, "updater_type": null, "updater_name": null
}
```

### Errors

| Case | Response |
|---|---|
| Unknown id | `404` |
| No/wrong-role token | `401` / `403` |

## 3. Tasks

1. **API client** (`admin-orders-api.ts`): `listOrders` (cursor + filters), `getOrder`, `updateOrderStatus`.
2. **Orders list**: filter bar (buyer id, seller id, status, order type, date range, search), table (buyer,
   seller, status badge, payment-status badge, payable, created date), cursor "load more".
3. **Order detail**: buyer card, seller card, items table, address card, a Payment card (status badge + its
   own mini timeline), this order's own status timeline, audit columns, and a **status override** control —
   a plain dropdown/select of every status plus an optional reason text field, no greying-out logic.
4. Status badges: reuse the same palette as the seller app/web screens so the colors agree across roles.
5. Entry point: add **Orders** to the admin nav, near Carts & Wishlists / Bidding.

## 4. Verify (browser, admin role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | List with no filters | every product order shows |
| 2 | Filter by a specific `seller` | only that seller's orders |
| 3 | Open a `pending` order's detail | buyer, seller, items, address, payment (`due`) and both empty-ish histories all render |
| 4 | Override status straight to `delivered` | `200`, payment card flips to `paid`, new rows on both histories |
| 5 | Override it back to `pending` | `200` — no block, unlike the seller screen |
| 6 | Override to `rejected` with a reason | `rejected_reason` shown on the card |
| 7 | Override to `rejected` with **no** reason | still succeeds (admin doesn't require one) — confirm the UI doesn't block submission either |
| 8 | A non-admin token (if testable from the UI) | handled the same way other admin screens reject it |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
