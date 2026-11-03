# Admin Payment Gateway API Guide

Admin management of **Payment Gateways** — the ways a buyer can pay at checkout. Only Cash on Delivery exists
today (seeded by a migration); a real gateway (bKash, a card processor, ...) is added here, later, with no code
change needed on the checkout side. For the full picture of how a gateway is used, see the
**Egoola Order Guide**, section 3. For how it fits into checkout and an order's own money fields, see
[`../buyer/buyer-order-api-guide.md`](../buyer/buyer-order-api-guide.md), [`../seller/seller-order-api-guide.md`](../seller/seller-order-api-guide.md)
and [`admin-order-api-guide.md`](admin-order-api-guide.md).

Base URL: `/api/v1/orders/payment-gateways/`. Admin token only (401 with none, 403 with a seller/buyer token).

**Buyer/seller checkout forms don't use this endpoint** — they have no admin token, and this endpoint also
lists inactive gateways. They call the public, no-auth list instead:

```
GET /api/v1/public/orders/payment-gateways/
```

Returns every **active** gateway only, unpaginated, no auth required (same pattern as
`/api/v1/public/geography/...`):

```json
[
  { "id": 11, "name": "Cash on Delivery", "slug": "cash-on-delivery", "icon_url": null }
]
```

`id` here is exactly the value `CheckoutSerializer` expects for `payment_gateway` — **never hardcode the id**
(it's whatever the DB assigns, not necessarily `1`); look it up by `slug` from this list instead.

---

## Table of contents

- [1. Fields](#1-fields)
- [2. List — `GET /orders/payment-gateways/`](#2-list-get-ordersPayment-gateways)
- [3. Create — `POST /orders/payment-gateways/`](#3-create-post-orderspayment-gateways)
- [4. Update — `PATCH /orders/payment-gateways/{id}/`](#4-update-patch-orderspayment-gatewaysid)
- [5. Delete — `DELETE /orders/payment-gateways/{id}/`](#5-delete-delete-orderspayment-gatewaysid)
- [6. No retrieve, by design](#6-no-retrieve-by-design)
- [7. Errors](#7-errors)

---

## 1. Fields

| Field | Type | Notes |
|---|---|---|
| `id` | integer | |
| `name` | string | Required, unique. |
| `slug` | string | **Read-only.** Always generated from `name` on create, and regenerated whenever `name` changes. Never sent by the client. |
| `icon` | file (write-only) | Optional. Sending one on `PATCH` replaces the old file and deletes it from storage. |
| `icon_path` / `icon_url` | string | **Read-only.** Where the icon is stored and the URL it's served from — both `null` until an icon is uploaded. |
| `is_active` | boolean | Default `true`. A gateway that's `false` can no longer be picked at checkout (`CheckoutSerializer` only offers active gateways); existing orders that already used it are untouched. |
| `created_at` / `updated_at` | datetime | |

## 2. List — `GET /orders/payment-gateways/`

Standard limit/offset pagination (`?limit=&offset=`, same as every other admin list that isn't cursor-paginated).

| Query param | What it does |
|---|---|
| `is_active` | `true` / `false` — exact match. |
| `search` | Matches `name` or `slug`. |

```json
GET /orders/payment-gateways/?is_active=true
{
  "count": 1, "next": null, "previous": null,
  "results": [
    { "id": 1, "name": "Cash on Delivery", "slug": "cash-on-delivery",
      "icon_path": null, "icon_url": null, "is_active": true,
      "created_at": "...", "updated_at": "..." }
  ]
}
```

## 3. Create — `POST /orders/payment-gateways/`

Multipart if sending an icon, JSON otherwise.

```json
POST /orders/payment-gateways/
{ "name": "bKash" }
```
→ `201`, `"slug": "bkash"`, `"is_active": true`.

- `name` missing → `400`.
- `name` already used by another gateway (case-sensitive match today) → `400` (standard "already exists" field error).

## 4. Update — `PATCH /orders/payment-gateways/{id}/`

Partial update. Renaming regenerates the slug:

```json
PATCH /orders/payment-gateways/3/
{ "name": "bKash Mobile Banking" }
```
→ `"slug": "bkash-mobile-banking"`. Saving the same `name` again (no actual change) keeps the same slug — the
slug only regenerates when the name is genuinely different from what it already was.

Turning a gateway off:
```json
PATCH /orders/payment-gateways/3/
{ "is_active": false }
```

Replacing the icon: multipart `PATCH` with a new `icon` file — the old file is deleted from storage once the
new one is saved. Unknown id → `404`.

## 5. Delete — `DELETE /orders/payment-gateways/{id}/`

`204`. Also deletes the icon file from storage, if one was uploaded. Unknown id → `404`. Deleting a gateway that
existing orders/payments already reference does **not** cascade or break those rows — `Payment.payment_gateway`
is a `PROTECT` foreign key, so deleting a gateway that's in use is refused at the database level (standard `400`
from the integrity check) until nothing still points at it. In practice, **deactivate** instead of deleting one
that's ever been used.

## 6. No retrieve, by design

There's no `GET /orders/payment-gateways/{id}/` — the list row already carries every field there is (name, slug,
icon, active), so a separate detail screen would show nothing new.

## 7. Errors

| Case | Status |
|---|---|
| No token | `401` |
| Seller or buyer token | `403` |
| Missing `name` on create | `400` |
| Duplicate `name` | `400` |
| Unknown id (update/delete) | `404` |
| Deleting a gateway still referenced by a Payment | `400` |
