# Buyer Address API Guide

A buyer's own saved delivery addresses — `/api/v1/buyer/addresses/...`. Checkout (see
[`buyer-order-api-guide.md`](buyer-order-api-guide.md)) snapshots one of these onto the order it creates;
editing or deleting a saved address here **never** changes a past order's own, frozen copy of it. For the plain-
language version of all of this, see the **Egoola Order Guide**, section 5.

Base URL: `/api/v1/buyer/addresses/`. Buyer token only (401 with none). Every address is scoped to the logged-in
buyer — another buyer's address id is `404`, never `403` (so a buyer can't even learn that an id exists).

---

## Table of contents

- [1. Fields](#1-fields)
- [2. List — `GET /buyer/addresses/`](#2-list-get-buyeraddresses)
- [3. Create — `POST /buyer/addresses/`](#3-create-post-buyeraddresses)
- [4. Retrieve — `GET /buyer/addresses/{id}/`](#4-retrieve-get-buyeraddressesid)
- [5. Update — `PATCH /buyer/addresses/{id}/` (or `PUT`)](#5-update-patch-buyeraddressesid-or-put)
- [6. Delete — `DELETE /buyer/addresses/{id}/`](#6-delete-delete-buyeraddressesid)
- [7. Location consistency](#7-location-consistency)
- [8. Errors](#8-errors)

---

## 1. Fields

| Field | Type | Notes |
|---|---|---|
| `id` | integer | |
| `name` | string | Required. The recipient's name on this address, not necessarily the buyer's own. |
| `phone` | string | Required. |
| `country` / `state` / `city` / `thana` | id | All four **required** (unlike a job's location, which allows a partial chain — a delivery address needs the full chain). Must nest consistently — see section 7. Sent as plain ids on write. |
| `country_name` / `state_name` / `city_name` / `thana_name` | string | **Read-only.** The name behind each id above (e.g. `"Bangladesh"`, `"Chittagong"`, `"Feni"`), so a page can show "Feni, Chittagong, Bangladesh" without a round trip to the geography endpoints. Never sent on write. |
| `address_line1` | string | Required. |
| `address_line2` | string | Optional. |
| `zip` | string | Optional. |
| `created_at` / `updated_at` | datetime | |

## 2. List — `GET /buyer/addresses/`

No pagination at all — a buyer realistically never has more than a handful of saved addresses. Newest first.

```json
GET /buyer/addresses/
[
  { "id": 7, "name": "Home", "phone": "+8801711110001",
    "country": 126, "country_name": "Bangladesh", "state": 13, "state_name": "Chittagong",
    "city": 8, "city_name": "Feni", "thana": 24, "thana_name": "Sadar",
    "address_line1": "House 1, Road 2", "address_line2": "Flat 3A", "zip": "1200",
    "created_at": "...", "updated_at": "..." }
]
```

## 3. Create — `POST /buyer/addresses/`

```json
POST /buyer/addresses/
{ "name": "Home", "phone": "+8801711110001", "country": 126, "state": 13, "city": 8, "thana": 24,
  "address_line1": "House 1, Road 2", "address_line2": "Flat 3A", "zip": "1200" }
```
→ `201`, the full address including its new `id`.

## 4. Retrieve — `GET /buyer/addresses/{id}/`

`200` with the address, or `404` (not found, or it's another buyer's).

## 5. Update — `PATCH /buyer/addresses/{id}/` (or `PUT`)

Partial update — send only the fields that changed:

```json
PATCH /buyer/addresses/7/
{ "address_line1": "House 9, Road 9" }
```
Fields not sent are left exactly as they were. Location consistency (section 7) is still checked against the
**resulting** combination, merging the new fields over the existing ones.

## 6. Delete — `DELETE /buyer/addresses/{id}/`

`204`. This never touches any order that already snapshotted this address — see
[`buyer-order-api-guide.md`](buyer-order-api-guide.md) section 4.

## 7. Location consistency

The four location fields must nest correctly: `state` must belong to `country`, `city` to `state`, `thana` to
`city` (and transitively to the levels above it). Sending a `city` that belongs to a different `state` than the
one given, say, is refused:

```json
{ "city": ["This city does not belong to the selected state."] }
```
→ `400`.

## 8. Errors

| Case | Status |
|---|---|
| No token | `401` |
| Missing a required field | `400` |
| Location chain doesn't nest correctly | `400` |
| Unknown id, or another buyer's address | `404` |
