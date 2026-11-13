# Seller Order API Guide

Everything a seller does around the orders placed against their own shop — seeing them, moving them forward, and
what shows up about **payment** and the delivery **address** inside each one. For the plain-language version,
read the **Egoola Order Guide** first; this document is the technical reference.

Base URL: everything below is under `/api/v1/seller/orders/`. A seller token belonging to a seller who can
**operate** (verified **and** active) only — the usual `403` otherwise, same rule as every other seller-facing
endpoint (listings, gigs, the job board). An order that isn't placed with this seller is always `404`, never
`403`.

---

## Table of contents

- [1. List — `GET /seller/orders/`](#1-list-get-sellerorders)
- [2. Detail — `GET /seller/orders/{id}/`](#2-detail-get-sellerordersid)
- [3. Move it forward — `PATCH /seller/orders/{id}/`](#3-move-it-forward-patch-sellerordersid)
- [4. Payment (read-only here)](#4-payment-read-only-here)
- [5. Address (read-only here)](#5-address-read-only-here)
- [6. Errors](#6-errors)

---

## 1. List — `GET /seller/orders/`

Cursor-paginated (`?limit=`, default 20, max 100 — same shape as the Seller Request queue: `next`/`previous`
links, no `count`). **Product** and **gig** orders placed with this seller — `order_type` tells them apart.

| Query param | What it does |
|---|---|
| `status` | exact match: `pending`, `accepted`, `rejected`, `in_progress`, `shipped`, `delivered`, `cancelled`, `disputed`, `completed` |
| `order_type` | exact match (`product` or `service`) |
| `created_from` / `created_to` | inclusive dates, `YYYY-MM-DD` |
| `search` | matches the buyer's name, phone or email |

```json
GET /seller/orders/?status=pending
{ "next": null, "previous": null,
  "results": [
    { "id": 104, "order_type": "product",
      "buyer": { "id": 1, "name": "...", "email": "...", "phone": "...", "profile_pic_url": null, "wallet_balance": "0.00", "status": "active" },
      "status": "pending", "payment_status": "due",
      "subtotal": "450.00", "delivery_cost": "0.00", "discount": "0.00", "total": "450.00", "payable": "450.00",
      "created_at": "...", "updated_at": "..." } ] }
```

## 2. Detail — `GET /seller/orders/{id}/`

Everything the list row has, plus `items` (same shape as the buyer's own detail — see
[`../buyer/buyer-order-api-guide.md`](../buyer/buyer-order-api-guide.md) §6), `address`, `payment` (with its nested
`status_histories`), this order's own `status_histories`, and `expected_delivery_at`/`completed_at`/
`cancelled_reason`/`rejected_reason`.

## 3. Move it forward — `PATCH /seller/orders/{id}/`

```json
PATCH /seller/orders/104/
{ "status": "accepted" }
```
→ `200` with the **full detail shape** (same as a `GET`, including `payment` and both histories) — not just the
two fields sent.

One step at a time (see the Egoola Order Guide's status flow):

| Current status | Allowed next | Notes |
|---|---|---|
| `pending` | `accepted` or `rejected` | `rejected` needs `{"reason": "..."}` — buyer-visible, `400` without one. |
| `accepted` | `in_progress` | |
| `in_progress` | `shipped` | |
| `shipped` | `delivered` | Also flips the payment `due → paid` — see §4. |

Any other move (skipping a step, moving a terminal order, moving backwards) is refused:
```json
{ "status": ["Cannot move an order from pending to delivered."] }
```

## 4. Payment (read-only here)

A seller never edits a payment directly — it's shown in the order detail exactly as the buyer sees it (amount,
status, gateway, its own status history), and it moves on its own in exactly one case: the seller's own
`delivered` move (§3) flips it from `due` to `paid` automatically, writing a new row onto the payment's status
history in the same step. See the Egoola Order Guide §9 for the full field list.

## 5. Address (read-only here)

The delivery address is shown exactly as the buyer entered it at checkout — a frozen snapshot, same shape as
[`../buyer/buyer-address-api-guide.md`](../buyer/buyer-address-api-guide.md)'s fields minus the id (name, phone, country,
`country_name`, state, `state_name`, city, `city_name`, thana, `thana_name`, address lines, zip). A seller never edits it.

## 6. Errors

| Case | Status |
|---|---|
| No token | `401` |
| Seller cannot operate (pending/rejected, or paused) | `403` |
| Order id unknown, or placed with a different seller | `404` |
| An out-of-order status move | `400` |
| `rejected` without a `reason` | `400` |
