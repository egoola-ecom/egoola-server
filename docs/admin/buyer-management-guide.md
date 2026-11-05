# Buyer Management API — Guide

Admin-only management of buyer accounts (the `User` model — this is the buyer,
not Django's auth user). Base path: `/api/v1/accounts/buyers/`.
Header: `Authorization: Bearer <admin access token>`.

| Token | Result |
|---|---|
| none / invalid | `401` |
| valid token, but the account was suspended or deleted after it was issued | `401` `{"detail": "This account is not active."}` |
| buyer or seller token | `403` |
| admin | allowed |

Postman: `postman/admin/Egoola-Buyer.postman_collection.json` (also present as the
**Buyers** folder in `postman/admin/Egoola.postman_collection.json`).

---

## Table of contents

- [Fields](#fields)
- [1. Create — `POST /buyers/`](#1-create-post-buyers)
- [2. Update — `PATCH /buyers/{id}/` (or `PUT`)](#2-update-patch-buyersid-or-put)
- [3. Retrieve — `GET /buyers/{id}/`](#3-retrieve-get-buyersid)
- [4. List — `GET /buyers/`](#4-list-get-buyers)
- [5. Delete — `DELETE /buyers/{id}/`](#5-delete-delete-buyersid)
- [Testing](#testing)

---

## Fields

| Field | Type | Notes |
|---|---|---|
| id | int | read only |
| name | string | **required** |
| email | string | optional, unique when given (upper / lower case count as the same). Empty = no email |
| phone | string | **required**, unique |
| password | string | **required on create**, write only, stored hashed; optional on update. Must be at least 8 characters, not a very common password and not all digits |
| profile_pic | image file | write only (multipart); read back as `profile_pic_path` / `profile_pic_url` |
| remove_profile_pic | bool | write only; clears it back to empty (update only; a `profile_pic` in the same request wins over this) |
| description | text | optional |
| skills, experiences, interests, educations | JSON, optional | |
| address_line | string | optional |
| country, state, city, thana | ids | optional. Must match: the state belongs to the country, the city to the state, the thana to the city |
| status | `active` \| `suspended` | default `active`; a suspended buyer cannot log in |
| email_verified_at, phone_verified_at | datetime | read only |
| wallet_balance | decimal | read only (changed by the wallet flow, never here) |
| media | list | read only on retrieve; add files with `media_for` + `media_file` (paired by position; `media_for` is one of `nid`, `birth_certificate`, `profile_document`, `other`), remove with `media_delete_ids` |

The creator/updater (`created_by`, `creator_type`, `creator_name`, `updated_*`)
are stamped from the admin token automatically (not part of the response).

## 1. Create — `POST /buyers/`

Minimal
```json
{
  "name": "Mahin Rahman",
  "email": "mahin@example.com",
  "phone": "+8801711000222",
  "password": "Buy@12345"
}
```
Full
```json
{
  "name": "Mahin Rahman",
  "email": "mahin@example.com",
  "phone": "+8801711000222",
  "password": "Buy@12345",
  "description": "Interior designer",
  "skills": ["design"],
  "address_line": "Road 1, Gulshan",
  "country": 126, "state": 13, "city": 8,
  "status": "active"
}
```
`201` (password is never returned)
```json
{
  "id": 14, "name": "Mahin Rahman", "email": "mahin@example.com",
  "phone": "+8801711000222", "profile_pic_path": null, "profile_pic_url": null,
  "description": "Interior designer", "skills": ["design"],
  "experiences": null, "interests": null, "educations": null,
  "address_line": "Road 1, Gulshan", "country": 126, "state": 13, "city": 8, "thana": null,
  "email_verified_at": null, "phone_verified_at": null,
  "wallet_balance": "0.00", "status": "active", "media": []
}
```

| Case | Result |
|---|---|
| no `password` | `400` `{"password": ["This field is required when creating a new record."]}` |
| weak `password` (too short, too common, all digits) | `400` `{"password": ["This password is too short. It must contain at least 8 characters."]}` |
| a city / state / thana that does not belong to the level above | `400` `{"city": ["This city does not belong to the selected state."]}` |
| missing `name` / `phone` / `password` | `400` per field |
| email or phone already used | `400` on that field |
| `status` not `active`/`suspended` | `400` |

## 2. Update — `PATCH /buyers/{id}/` (or `PUT`)

| Goal | Payload | Result |
|---|---|---|
| Rename | `{"name": "New Name"}` | `200` |
| Suspend | `{"status": "suspended"}` | `200` — buyer can no longer log in |
| Re-activate | `{"status": "active"}` | `200` |
| Change password | `{"password": "New@12345"}` | `200` — old password stops working |
| Profile picture | multipart `profile_pic=@photo.png` (must be a real image) | `200`, `profile_pic_url` set |
| Remove profile picture | `{"remove_profile_pic": true}` | `200`, `profile_pic_path`/`profile_pic_url` back to `null` |
| Add media | multipart `media_for=...`, `media_file=@file` (same count, same order) | `200` |
| Remove media | `{"media_delete_ids": [3]}` | `200` |
| Email of another buyer | `{"email": "other@example.com"}` | `400` |
| `wallet_balance` | any value | ignored (read only) |

`PUT` does not need `password`. Unknown id → `404`.

## 3. Retrieve — `GET /buyers/{id}/`

Full record as in the create response, including `media`. Unknown id → `404`.

## 4. List — `GET /buyers/`

Paginated (`limit`, `offset`; default limit 20): `{count, next, previous, results}`.
Rows are light: `id, name, email, phone, profile_pic_url, wallet_balance, status`.

| Query | Meaning |
|---|---|
| `search` | name, email or phone (contains) |
| `status` | `active` \| `suspended` |
| `country`, `state`, `city`, `thana` | location ids |
| `email_verified` | `true` / `false` |
| `phone_verified` | `true` / `false` |
| `created_from`, `created_to` | signup date, `YYYY-MM-DD`, inclusive |

Filters combine, e.g. `/buyers/?status=suspended&city=8&created_from=2026-10-01`.

## 5. Delete — `DELETE /buyers/{id}/`

`204`. Deleting again → `404`. A buyer with any order (`Order.buyer` is
`PROTECT`) → `409` `{"detail": "This buyer has one or more orders. Suspend the
account instead of deleting."}` — suspend instead.

## Testing

49 / 49 checks passed (create and validation, retrieve, update including
password change and login, profile picture, every list filter, 401/403, creator
stamping, delete). Run with `scripts/smoke/buyer_smoke.sh` against the dev server (see
`scripts/smoke/README.md`). Test data was removed afterwards.

Delete's `409` on a buyer with an order was verified separately, live: a buyer
with a PROTECTed order answers `409` with the message above; deleting the
order first then the buyer answers `204` as normal.
