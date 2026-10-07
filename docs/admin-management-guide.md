# Admin Management API — Guide

Create, update, list and view other admins. Base path: `/api/v1/accounts/admins/`.

## Roles

There are two admin roles: **`super_admin`** and **`admin`**.

**Only a super-admin can use Admin Management.** A plain `admin` can still use
the rest of the admin panel (sellers, buyers, listings, categories …), just not
this API.

| Token | Result on every `/admins/` endpoint |
|---|---|
| none / invalid | `401` |
| seller or buyer | `403` |
| `admin` | `403` `{"detail": "Only a super-admin can access Admin Management."}` |
| `super_admin` | allowed |

The role is read from the database on each request, so promoting or demoting an
admin takes effect immediately (even with a token that was issued earlier).

Postman: **Auth > Super-Admin Login**, then the **Admins** folder in
`postman/Egoola.postman_collection.json`.

## Safety rules

- You cannot change your **own** `type` or `status` (`400`), and you cannot
  delete **yourself** (`400`). Editing your own name, phone etc. is fine, and a
  `PUT` that resends your current type/status is fine.
- Because of that, there is always at least one active super-admin left: a
  super-admin can only be demoted or deactivated by *another* super-admin.
- Inactive admins cannot log in.

## Fields

| Field | Notes |
|---|---|
| name | **required** |
| email | **required**, unique |
| mobile | **required**, unique |
| password | **required on create**, write only, stored hashed; optional on update |
| type | **required**: `super_admin` \| `admin` |
| status | `active` (default) \| `inactive` |
| profile_pic | image file, write only (multipart) → `profile_pic_url` |
| skills, experiences, interests, educations | JSON, optional |
| present_address, permanent_address | text, optional |
| country, state, city, thana | ids, optional |
| last_logged_at | read only |
| media | read only; add with `media_for` + `media_file`, remove with `media_delete_ids` |

`created_by`, `creator_type`, `creator_name` (and `updated_*`) are stamped from
the super-admin's token.

## Create — `POST /admins/`

```json
{
  "name": "Rafi Ahmed",
  "email": "rafi@egoola.com",
  "mobile": "+8801711000333",
  "password": "Adm@12345",
  "type": "admin"
}
```
`201`, full record (no password). With details:
```json
{
  "name": "Nadia Karim", "email": "nadia@egoola.com", "mobile": "+8801711000444",
  "password": "Adm@12345", "type": "super_admin", "status": "active",
  "present_address": "Dhaka", "country": 126, "state": 12, "city": 8, "skills": ["operations"]
}
```

| Case | Result |
|---|---|
| `type` missing | `400` `{"type": ["This field is required."]}` |
| `type` = `moderator`, `support` or anything else | `400` `"… is not a valid choice."` |
| no `password` | `400` `{"password": ["This field is required when creating a new record."]}` |
| duplicate `email` or `mobile` | `400` on that field |
| plain `admin` token | `403` |

## Update — `PATCH /admins/{id}/` (or `PUT`)

| Goal | Payload | Result |
|---|---|---|
| Rename | `{"name": "New Name"}` | `200` |
| Promote | `{"type": "super_admin"}` | `200`; the admin can use this API immediately |
| Demote | `{"type": "admin"}` | `200`; they lose access immediately |
| Deactivate / reactivate | `{"status": "inactive"}` / `{"status": "active"}` | `200`; inactive admins can't log in |
| Reset password | `{"password": "New@12345"}` | `200`; old password stops working |
| Bad type | `{"type": "moderator"}` | `400` |
| Your own type | `{"type": "admin"}` on your own id | `400` `{"type": ["You cannot change your own admin type."]}` |
| Your own status | `{"status": "inactive"}` on your own id | `400` `{"status": ["You cannot change your own status."]}` |

## Retrieve — `GET /admins/{id}/`

Full record including `media`. Unknown id → `404`.

## List — `GET /admins/`

Paginated (`limit`, `offset`, default 20): `{count, next, previous, results}`.
Rows: `id, name, email, mobile, profile_pic_url, type, status, last_logged_at`.

| Query | Meaning |
|---|---|
| `search` | name, email or mobile |
| `type` | `super_admin` \| `admin` |
| `status` | `active` \| `inactive` |

## Delete — `DELETE /admins/{id}/`

`204`. Your own id → `400` `{"detail": "You cannot delete your own account."}`.
Unknown id → `404`.

## Testing

52 / 52 checks passed: access control for every role, create and validation,
promote / demote with immediate effect, deactivate and re-login, password
change, self-protection, filters, creator stamping, delete. Also re-run through
Newman for the Postman Auth + Admins folders. Test data was removed.

## Dev accounts

| Email | Type | Password |
|---|---|---|
| `test.super@egoola.com` | super_admin | `Test@12345` |
| `test.admin@egoola.com` | admin | `Test@12345` |

(Local development database only.)
