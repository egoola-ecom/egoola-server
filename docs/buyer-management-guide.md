# Buyer Management API — Guide

Admin-only management of buyer accounts (the `User` model — this is the buyer,
not Django's auth user). Base path: `/api/v1/accounts/buyers/`.
Header: `Authorization: Bearer <admin access token>`.

| Token | Result |
|---|---|
| none / invalid | `401` |
| buyer or seller token | `403` |
| admin | allowed |

Postman: **Buyers** folder in `postman/Egoola.postman_collection.json`.

## Fields

| Field | Type | Notes |
|---|---|---|
| id | int | read only |
| name | string | **required** |
| email | string | **required**, unique |
| phone | string | **required**, unique |
| password | string | **required on create**, write only, stored hashed; optional on update |
| profile_pic | image file | write only (multipart); read back as `profile_pic_path` / `profile_pic_url` |
| description | text | optional |
| skills, experiences, interests, educations | JSON, optional | |
| address_line | string | optional |
| country, state, city, thana | ids | optional |
| status | `active` \| `suspended` | default `active`; a suspended buyer cannot log in |
| email_verified_at, phone_verified_at | datetime | read only |
| wallet_balance | decimal | read only (changed by the wallet flow, never here) |
| media | list | read only on retrieve; add files with `media_for` + `media_file`, remove with `media_delete_ids` |

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
  "country": 126, "state": 12, "city": 8,
  "status": "active"
}
```
`201` (password is never returned)
```json
{
  "id": 14, "name": "Mahin Rahman", "email": "mahin@example.com",
  "phone": "+8801711000222", "profile_pic_path": null, "profile_pic_url": null,
  "description": "Interior designer", "skills": ["design"],
  "address_line": "Road 1, Gulshan", "country": 126, "state": 12, "city": 8, "thana": null,
  "email_verified_at": null, "phone_verified_at": null,
  "wallet_balance": "0.00", "status": "active", "media": []
}
```

| Case | Result |
|---|---|
| no `password` | `400` `{"password": ["This field is required when creating a new record."]}` |
| missing `name` / `email` / `phone` | `400` per field |
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

`204`. Deleting again → `404`.

## Testing

49 / 49 checks passed (create and validation, retrieve, update including
password change and login, profile picture, every list filter, 401/403, creator
stamping, delete). Test data was removed afterwards.
