# Buyer Order API Guide

Everything a buyer does around placing and watching an order: saved **addresses**, the **Payment Gateway** a
buyer picks from at checkout, and the **order** itself — checkout, listing, detail, and cancelling. For the
plain-language version of all of this, read the **Egoola Order Guide** first; this document is the technical
reference. For the cart an order is built from, see [`buyer-api-guide.md`](buyer-api-guide.md) section 3 and
[`../Egoola_Cart_Guide.md`](../Egoola_Cart_Guide.md).

Base URL: everything below is under `/api/v1/`. Buyer token only on every endpoint here (401 with none). An
order or address that isn't the logged-in buyer's own is always `404`, never `403`.

---

## Table of contents

- [1. Addresses — `/buyer/addresses/...`](#1-addresses-buyeraddresses)
- [2. Payment Gateways (read side)](#2-payment-gateways-read-side)
- [3. Checkout — `POST /buyer/orders/`](#3-checkout-post-buyerorders)
- [4. What checkout actually creates](#4-what-checkout-actually-creates)
- [5. List — `GET /buyer/orders/`](#5-list-get-buyerorders)
- [6. Detail — `GET /buyer/orders/{id}/`](#6-detail-get-buyerordersid)
- [7. Cancel — `PATCH /buyer/orders/{id}/`](#7-cancel-patch-buyerordersid)
- [8. The old `/cancel/` action is gone](#8-the-old-cancel-action-is-gone)
- [9. Errors](#9-errors)

---

## 1. Addresses — `/buyer/addresses/...`

Full CRUD, no pagination. See [`buyer-address-api-guide.md`](buyer-address-api-guide.md) for the complete
reference (fields, location-consistency rule, every error). In short:

| Call | What it does |
|---|---|
| `GET /buyer/addresses/` | every saved address, newest first |
| `POST /buyer/addresses/` | save a new one |
| `GET /buyer/addresses/{id}/` | one address |
| `PATCH /buyer/addresses/{id}/` | edit one (partial) |
| `DELETE /buyer/addresses/{id}/` | remove one — never touches a past order's own frozen copy |

## 2. Payment Gateways (read side)

A buyer never creates or edits a Payment Gateway (that's admin-only — see
[`../admin/admin-payment-gateway-api-guide.md`](../admin/admin-payment-gateway-api-guide.md)); a buyer only ever picks one **by
id** at checkout. To find which ids exist, call the public, no-auth list — **never hardcode a gateway id**,
it's whatever the DB assigns, not necessarily `1`:

```
GET /api/v1/public/orders/payment-gateways/
```

```json
[
  { "id": 11, "name": "Cash on Delivery", "slug": "cash-on-delivery", "icon_url": null }
]
```

Only active gateways are listed, unpaginated, no token needed. Pick the row by `slug` (e.g.
`"cash-on-delivery"`) and send its `id` as `payment_gateway` below.

| Field (as it appears inside an order's `payment`) | Meaning |
|---|---|
| `payment_gateway` | The gateway's id. |
| `gateway_slug` | A frozen snapshot of the gateway's slug at the moment of payment — survives the gateway being renamed later. |
| `method` | A frozen snapshot of the gateway's **name** at the moment of payment. |
| `status` | `due`, `initiated`, `paid`, `failed`, `cancelled`, `partially_paid` — see the Egoola Order Guide's status flow. |

## 3. Checkout — `POST /buyer/orders/`

```json
POST /buyer/orders/
{ "cart": 212, "address": 7, "payment_gateway": 1 }
```

| Field | Meaning |
|---|---|
| `cart` | id of one of the buyer's own **active** carts (see [`buyer-api-guide.md`](buyer-api-guide.md) §3 for how a cart comes to exist). Must have a seller — a cart of admin-owned listings with no seller can't be checked out yet. Must not be empty, and every line in it must still be available (stock, still approved, SKU still active). |
| `address` | id of one of the buyer's own **saved** addresses. |
| `payment_gateway` | id of an **active** Payment Gateway. |

`201` with the full order (section 6's shape) on success.

## 4. What checkout actually creates

One request, several rows, all in one database transaction:

1. The **Order** (`status: "pending"`, `payment_status: "due"`), with the cart's seller, and `total`/`subtotal`/
   `delivery_cost`/`discount`/`payable` computed from the cart's lines (see the Egoola Order Guide §8 for exactly
   how).
2. One **OrderItem** per cart line — a frozen snapshot of that line's title and price.
3. A fresh **Address** row, a snapshot of the chosen saved address, attached only to this order.
4. The **Payment** (`status: "due"`, `amount` = the order's `payable`), remembering the gateway used (live FK
   and a frozen `gateway_slug`/`method` snapshot).
5. The **opening row** of both history tables: the order's own status history (`null → pending`) and the
   payment's own status history (`null → due`).
6. The **cart** is closed (`is_active: false`, linked via `cart.order`) — it can never be checked out again.

## 5. List — `GET /buyer/orders/`

Page-based pagination (`?page=&page_size=`, same shape as every other Buyer Panel list — see
[`buyer-api-guide.md`](buyer-api-guide.md)'s pagination note). Newest first. Both **product** and **gig**
(`order_type: "service"`) orders show up here, same shape either way — a job's own order (created when a bid is
accepted, no cart involved) is reached through `/buyer/jobs/{id}/` instead, not this list.

| Query param | What it does |
|---|---|
| `status` | exact match: `pending`, `accepted`, `rejected`, `in_progress`, `shipped`, `delivered`, `cancelled`, `disputed`, `completed` |
| `order_type` | exact match (`product` or `service`) — separates product orders from gig orders |
| `created_from` / `created_to` | inclusive dates, `YYYY-MM-DD` |

```json
GET /buyer/orders/
{ "count": 3, "page": 1, "page_size": 20, "total_pages": 1,
  "results": [
    { "id": 104, "order_type": "product", "seller": { "id": 723, "name": "...", "phone": "...", "profile_pic_url": null },
      "status": "pending", "payment_status": "due",
      "subtotal": "450.00", "delivery_cost": "0.00", "discount": "0.00", "total": "450.00", "payable": "450.00",
      "created_at": "...", "updated_at": "..." }
  ] }
```

## 6. Detail — `GET /buyer/orders/{id}/`

Everything the list row has, plus:

```json
{
  ...,
  "items": [ { "id": 104, "listing": 1777, "listing_sku": 2018, "title_snapshot": "...",
                "price_snapshot": "150.00", "price_type_snapshot": null, "qty": 3, "duration": null,
                "total": "450.00", "subtotal": "450.00" } ],
  "address": { "name": "...", "phone": "...",
               "country": 126, "country_name": "Bangladesh", "state": 13, "state_name": "Chittagong",
               "city": 8, "city_name": "Feni", "thana": 24, "thana_name": "Sadar",
               "address_line1": "...", "address_line2": null, "zip": null },
  "payment": {
    "id": 7, "status": "due", "amount": "450.00", "store_amount": null, "method": "Cash on Delivery",
    "payment_gateway": 11, "gateway_slug": "cash-on-delivery", "gateway_txn_id": null, "notes": null, "meta_data": null,
    "status_histories": [ { "id": 1, "previous_status": null, "current_status": "due",
                             "created_by": 1, "creator_type": "user", "creator_name": "...", "created_at": "..." } ],
    "created_at": "...", "updated_at": "..."
  },
  "status_histories": [ { "id": 1, "previous_status": null, "current_status": "pending", "reason": null,
                           "created_by": 1, "creator_type": "user", "creator_name": "...", "created_at": "..." } ],
  "expected_delivery_at": null, "completed_at": null, "cancelled_reason": null, "rejected_reason": null
}
```

Both `status_histories` arrays are newest-first and grow by one row every time the seller or an admin moves the
order (or the payment) along — see the Egoola Order Guide §§9–10.

## 7. Cancel — `PATCH /buyer/orders/{id}/`

This is the **general** "change this order" request every actor uses — a buyer is just currently only allowed
to send one value:

```json
PATCH /buyer/orders/104/
{ "status": "cancelled", "reason": "Changed my mind" }
```
→ `200` with the full detail shape (section 6), `status: "cancelled"`, `cancelled_reason` set, and a new row on
top of `status_histories` recording the move and the reason. `reason` is optional.

Allowed only while the order is still `pending`, `accepted`, or `in_progress` — once the seller marks it
`shipped`, this is refused:
```json
{ "status": ["This order can no longer be cancelled."] }
```
Sending any status other than `cancelled` is refused too:
```json
{ "status": ["A buyer can currently only move an order to cancelled."] }
```
More moves may be opened up to a buyer later without changing the shape of this call.

## 8. The old `/cancel/` action is gone

An earlier version of this API had a dedicated `POST /buyer/orders/{id}/cancel/` action. It's been replaced by
the general `PATCH` above — that route now returns `404`.

## 9. Errors

| Case | Status |
|---|---|
| No token | `401` |
| `cart`/`address` not the buyer's own, or doesn't exist | `400` (field error on `cart`/`address`) |
| A no-seller cart | `400` |
| An empty, already-used, or stale (unavailable items) cart | `400`, a non-field message per stale line, e.g. `"<listing title>: Only 2 left in stock (you asked for 5)."` — stock is re-checked against what's in stock **right now**, not what the SKU showed when it was added to the cart |
| An inactive `payment_gateway` | `400` |
| Order id unknown, or another buyer's | `404` |
| `PATCH` to any status except `cancelled` | `400` |
| `PATCH` to `cancelled` once already `shipped`/`delivered`/terminal | `400` |
