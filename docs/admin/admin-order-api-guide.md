# Admin Order API Guide

Admin's full oversight of orders — every order on the platform, with no restriction on moving its status — plus
the **Payment Gateway** list admin runs, and the delivery **address** as it shows up inside an order. For the
plain-language version, read the **Egoola Order Guide** first; this document is the technical reference.

Base URL: everything below is under `/api/v1/orders/...`. Admin token only (401 with none, 403 with a seller or
buyer token).

---

## Table of contents

- [1. List — `GET /orders/orders/`](#1-list-get-ordersorders)
- [2. Detail — `GET /orders/orders/{id}/`](#2-detail-get-ordersordersid)
- [3. Any status, any time — `PATCH /orders/orders/{id}/`](#3-any-status-any-time-patch-ordersordersid)
- [4. Payment Gateways — `/orders/payment-gateways/...`](#4-payment-gateways-orderspayment-gateways)
- [5. Address (read-only here)](#5-address-read-only-here)
- [6. Errors](#6-errors)

---

## 1. List — `GET /orders/orders/`

Cursor-paginated (`?limit=`, default 20, max 100 — same shape as every other admin cursor list: `next`/
`previous`, no `count`). Every **product** and **gig** order on the platform — a job's own order (created when a
bid is accepted, no cart involved) isn't surfaced here yet.

| Query param | What it does |
|---|---|
| `buyer` | exact buyer id |
| `seller` | exact seller id |
| `status` | exact match |
| `order_type` | exact match (`product` or `service` — `job` never appears here, see above) |
| `created_from` / `created_to` | inclusive dates, `YYYY-MM-DD` |
| `search` | matches the buyer's name/phone, or the seller's name |

```json
GET /orders/orders/?status=pending&seller=723
{ "next": null, "previous": null,
  "results": [
    { "id": 104, "order_type": "product",
      "buyer": { "id": 1, "name": "...", "email": "...", "phone": "...", "profile_pic_url": null, "wallet_balance": "0.00", "status": "active" },
      "seller": { "id": 723, "name": "...", "phone": "...", "profile_pic_url": null },
      "status": "pending", "payment_status": "due",
      "subtotal": "450.00", "delivery_cost": "0.00", "discount": "0.00", "total": "450.00", "payable": "450.00",
      "created_at": "...", "updated_at": "..." } ] }
```

## 2. Detail — `GET /orders/orders/{id}/`

Everything the list row has, plus `items`, `address`, `payment` (with its nested `status_histories`), this
order's own `status_histories`, `expected_delivery_at`/`completed_at`/`cancelled_reason`/`rejected_reason`, and
the audit columns (`created_by`, `creator_type`, `creator_name`, `updated_by`, `updater_type`, `updater_name`).
Unknown id → `404`.

## 3. Any status, any time — `PATCH /orders/orders/{id}/`

```json
PATCH /orders/orders/104/
{ "status": "in_progress" }
```
→ `200` with the **full detail shape** (same as a `GET`).

Unlike the seller's own endpoint, there is **no transition check at all** — admin can move an order to any of
`pending`, `accepted`, `rejected`, `in_progress`, `shipped`, `delivered`, `cancelled`, `completed`, `disputed`,
from whatever it's currently at, forwards or backwards:

```json
PATCH /orders/orders/104/
{ "status": "rejected", "reason": "Fraud check failed" }
```
`reason` is accepted and recorded (into `rejected_reason` or `cancelled_reason`, matching whichever status was
sent) but never **required** — unlike the seller's own `reject` move.

Moving an order to `delivered` this way triggers the exact same payment side effect as the seller's own move: if
the payment was `due`, it flips to `paid`, and a new row lands on the payment's own status history. Every move,
by any actor, also always lands its own row on the order's **own** status history.

## 4. Payment Gateways — `/orders/payment-gateways/...`

Full CRUD — see [`admin-payment-gateway-api-guide.md`](admin-payment-gateway-api-guide.md) for the complete
reference. In short:

| Call | What it does |
|---|---|
| `GET /orders/payment-gateways/` | list (limit/offset, `?is_active=`, `?search=`) |
| `POST /orders/payment-gateways/` | create (`name`, optional `icon`) — `slug` is always generated |
| `PATCH /orders/payment-gateways/{id}/` | rename (slug regenerates), toggle `is_active`, replace the icon |
| `DELETE /orders/payment-gateways/{id}/` | remove — refused while a `Payment` still references it |

No `GET .../{id}/` — the list row already carries everything.

## 5. Address (read-only here)

The delivery address inside an order's detail is a frozen snapshot of what the buyer entered at checkout — same
shape as [`../buyer/buyer-address-api-guide.md`](../buyer/buyer-address-api-guide.md)'s fields minus the id. Admin never edits it
directly through the order endpoint.

## 6. Errors

| Case | Status |
|---|---|
| No token | `401` |
| Seller or buyer token | `403` |
| Order id unknown | `404` |
| Payment Gateway errors | see [`admin-payment-gateway-api-guide.md`](admin-payment-gateway-api-guide.md) §7 |
