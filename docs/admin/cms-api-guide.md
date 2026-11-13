# CMS & Site Settings API — Guide

Admin-side content management: **Banners**, **Email Templates**, **Site
Settings** and the **Site Logo**. Base path: `/api/v1/cms/`.

Header on every request: `Authorization: Bearer <admin access token>` (any
admin; a super-admin is not required).

| Token | Result |
|---|---|
| none / invalid | `401` |
| seller or buyer | `403` |
| admin | allowed |

Lists are paginated: `?limit=` / `?offset=` (default 20, max 100) →
`{count, next, previous, results}`.
Postman: `postman/admin/Egoola-CMS.postman_collection.json`.

This API is admin-only. The buyer-facing read of active banners is a
separate, public endpoint — see [section 5](#5-public-banner-list-buyer-homepage-apiv1publiccmsbanners).
The logo and public settings have no public read endpoint yet.

---

## Table of contents

- [1. Banners — `/banners/`](#1-banners-banners)
  - [Fields](#fields)
  - [Create — `POST /banners/` (multipart)](#create-post-banners-multipart)
  - [Retrieve — `GET /banners/{id}/` · Unknown id → `404`](#retrieve-get-bannersid-unknown-id-404)
  - [Update — `PATCH /banners/{id}/`](#update-patch-bannersid)
  - [List — `GET /banners/`](#list-get-banners)
  - [Delete — `DELETE /banners/{id}/` → `204`, the image file is removed too.](#delete-delete-bannersid-204-the-image-file-is-removed-too)
- [2. Email Templates — `/email-templates/`](#2-email-templates-email-templates)
  - [Create — `POST /email-templates/`](#create-post-email-templates)
  - [Update — `PATCH` (or `PUT`) `/email-templates/{id}/`](#update-patch-or-put-email-templatesid)
  - [List — `GET /email-templates/` — `search` (key or subject), `is_active`.](#list-get-email-templates-search-key-or-subject-is_active)
  - [Retrieve — `GET /email-templates/{id}/` · Delete — `DELETE …` → `204`.](#retrieve-get-email-templatesid-delete-delete-204)
- [3. Site Settings — `/settings/`](#3-site-settings-settings)
  - [Create — `POST /settings/`](#create-post-settings)
  - [Retrieve — `GET /settings/{key}/` · unknown key → `404`](#retrieve-get-settingskey-unknown-key-404)
  - [Update — `PATCH /settings/{key}/`](#update-patch-settingskey)
  - [List — `GET /settings/?search=commission` (key contains)](#list-get-settingssearchcommission-key-contains)
  - [Delete — `DELETE /settings/{key}/` → `204`](#delete-delete-settingskey-204)
- [4. Site Logo — `/site-logo/`](#4-site-logo-site-logo)
- [5. Public banner list (buyer homepage) — `/api/v1/public/cms/banners/`](#5-public-banner-list-buyer-homepage-apiv1publiccmsbanners)
- [Notes](#notes)
- [Testing](#testing)

---

## 1. Banners — `/banners/`

One table for every placement (`hero`, `sidebar`, `category`).

### Fields

| Field | Notes |
|---|---|
| placement | **required**: `hero` \| `sidebar` \| `category` |
| image | **required on create**, image file (write only). Read back as `image_path` / `image_url` |
| heading, small_heading | optional text |
| link_url | optional — where the banner links to |
| category | optional category id — **sidebar banners only** |
| status | `active` (default) \| `inactive` |
| sort_order | integer, default 0 — display order inside a placement |
| starts_at, ends_at | optional ISO datetimes; `ends_at` must be after `starts_at`. Empty = no limit on that side |
| id, created_at, updated_at | read only |

**Create and update use multipart form data** (because of the image). A plain
JSON `PATCH` works when you are not sending an image.

### Create — `POST /banners/` (multipart)

```
placement=hero
heading=Eid Collection is Here
small_heading=Up to 40% off
link_url=/categories/electronics
sort_order=1
starts_at=2026-08-01T00:00:00Z
ends_at=2026-08-31T23:59:59Z
image=@eid-hero.png
```
`201`
```json
{
  "id": 1, "placement": "hero", "heading": "Eid Collection is Here",
  "small_heading": "Up to 40% off", "link_url": "/categories/electronics",
  "image_path": "banners/3f2a….png", "image_url": "/media/banners/3f2a….png",
  "category": null, "status": "active", "sort_order": 1,
  "starts_at": "2026-08-01T00:00:00Z", "ends_at": "2026-08-31T23:59:59Z",
  "created_at": "…", "updated_at": "…"
}
```
Sidebar banner for a category: `placement=sidebar`, `category=18`, `image=@…`.

| Case | Result |
|---|---|
| no `image` | `400` `{"image": ["A banner needs an image."]}` |
| file that is not an image | `400` on `image` |
| `placement` missing or not one of the three | `400` |
| `category` on a hero/category banner | `400` `{"category": ["A category can only be set on a sidebar banner …"]}` |
| unknown category id | `400` |
| `ends_at` ≤ `starts_at` | `400` `{"ends_at": ["Must be after starts_at."]}` |

### Retrieve — `GET /banners/{id}/` · Unknown id → `404`

### Update — `PATCH /banners/{id}/`

| Goal | Payload | Result |
|---|---|---|
| Edit text | JSON `{"heading": "New"}` | `200` |
| Hide it | JSON `{"status": "inactive"}` | `200` |
| Replace the image | multipart `image=@new.png` | `200`; new `image_path`, **old file is deleted** |
| Sidebar → hero | `{"placement": "hero", "category": null}` | `200` (without `category: null` → `400`) |
| Bad schedule | `{"ends_at": "<before existing starts_at>"}` | `400` |

### List — `GET /banners/`

| Query | Meaning |
|---|---|
| `placement` | `hero` \| `sidebar` \| `category` |
| `status` | `active` \| `inactive` |
| `category` | category id |
| `active_now` | `true` = active **and** inside its schedule window right now · `false` = everything else |
| `search` | heading or small heading |

Ordered by placement, then `sort_order`.

### Delete — `DELETE /banners/{id}/` → `204`, the image file is removed too.

---

## 2. Email Templates — `/email-templates/`

| Field | Notes |
|---|---|
| key | **required**, unique, lowercase letters/digits/underscores, starts with a letter. The stable id application code looks the template up by — **cannot be changed after creation** |
| subject | **required** |
| content | **required**; may contain `{{variables}}` such as `{{buyerName}}` |
| is_active | default `true`; controls whether the application actually sends it |
| id, created_at, updated_at | read only |

### Create — `POST /email-templates/`
```json
{
  "key": "order_approved",
  "subject": "Your Egoola order has been approved",
  "content": "Hi {{buyerName}}, your order #{{orderId}} has been approved.",
  "is_active": true
}
```
`201`, full record.

| Case | Result |
|---|---|
| key already used | `400` `{"key": ["A template with this key already exists."]}` |
| key like `Bad-Key` or `1abc` | `400` `{"key": ["Use lowercase letters, digits and underscores only, starting with a letter."]}` |
| missing `subject` / `content` | `400` |

### Update — `PATCH` (or `PUT`) `/email-templates/{id}/`

| Payload | Result |
|---|---|
| `{"subject": "New", "content": "Hi {{name}}"}` | `200` |
| `{"is_active": false}` | `200` — the app stops sending it |
| `{"key": "other"}` | `400` `{"key": ["The key cannot be changed after creation."]}` |
| `PUT` with the same `key` | `200` |

### List — `GET /email-templates/` — `search` (key or subject), `is_active`.
### Retrieve — `GET /email-templates/{id}/` · Delete — `DELETE …` → `204`.

---

## 3. Site Settings — `/settings/`

A generic key → JSON value store. Settings are addressed by **key**, not id.

| Field | Notes |
|---|---|
| key | lowercase letters/digits/underscores, starts with a letter, unique, **cannot be changed** |
| value | **required**, any JSON: number, string, boolean, list or object |
| created_at, updated_at | read only |

### Create — `POST /settings/`
```json
{ "key": "commission_rate_default", "value": 10 }
```
```json
{ "key": "contact", "value": { "email": "help@egoola.com", "phones": ["+8801700000000"] } }
```
`201` → `{"key": …, "value": …, "created_at": …, "updated_at": …}`.

| Case | Result |
|---|---|
| key already used | `400` |
| bad key format | `400` |
| no `value` | `400` |
| `site_logo_path` / `site_logo_url` | `400` — managed by the Site Logo endpoint |

### Retrieve — `GET /settings/{key}/` · unknown key → `404`
### Update — `PATCH /settings/{key}/`
`{"value": 12}` → `200`. The value may change to a different JSON type
(`{"value": {"a": 1}}`). `{"key": "other"}` → `400`.
### List — `GET /settings/?search=commission` (key contains)
### Delete — `DELETE /settings/{key}/` → `204`

The two logo keys are visible in the list/retrieve but cannot be created,
edited or deleted here (`400`).

---

## 4. Site Logo — `/site-logo/`

The logo is kept in two settings rows, `site_logo_path` and `site_logo_url`,
written only by this endpoint.

| Request | Result |
|---|---|
| `GET /site-logo/` | `200` `{"path": "site/….png", "url": "/media/site/….png"}` — both `null` when no logo is set |
| `POST /site-logo/` (multipart `image=@logo.png`) | `200` with the new `{path, url}`; the previous logo file is deleted. `PUT` does the same |
| `POST` without a file, or a non-image | `400` `{"image": [...]}` |
| `DELETE /site-logo/` | `204`; clears both settings and removes the file. Safe when no logo exists |

---

## 5. Public banner list (buyer homepage) — `/api/v1/public/cms/banners/`

**Not under `/api/v1/cms/`** — a separate, no-auth read for the storefront. No token
needed; a stale or expired one in the browser is simply ignored (never a `401`).
Returns only banners that are **live right now**: `status=active` and the current
time falls inside `starts_at`/`ends_at` (either side blank = open-ended on that
side) — the same "live" definition as the admin list's `active_now=true` filter.

```
GET /api/v1/public/cms/banners/
GET /api/v1/public/cms/banners/?placement=hero
```
`200`, a plain list (no pagination):
```json
[
  { "id": 1, "placement": "hero", "heading": "Eid Collection is Here",
    "small_heading": "Up to 40% off", "link_url": "/categories/electronics",
    "image_url": "/media/banners/3f2a….png", "category": null, "sort_order": 1 }
]
```
Ordered by placement, then `sort_order` (the model's default ordering). Only
`placement` can be filtered — `status` and the schedule are already baked into
"live," not something a client chooses. No `image_path`, `status`, `starts_at`
or `ends_at` in the response — those are internal to how the admin manages the
banner, not something the buyer screen needs.

---

## Notes

- Creator and last-editor (`created_by`, `creator_type`, `creator_name`,
  `updated_*`) are stamped from the admin's token on every row.
- Deleting or replacing a banner image or the logo removes the old file from
  storage (best effort).
- No database change was needed — the `banners`, `emailTemplates` and
  `settings` tables already existed (DB Re-Design, section 3.12).

## Testing

105 / 105 smoke checks passed (`scripts/smoke/cms_smoke.sh`; access control for every endpoint, every
validation and filter, file replace/delete behaviour on disk, creator
stamping, and the public banner list's no-auth access and "live" filtering),
plus Newman: 49 assertions, 0 failed. All test data and uploaded files were
removed afterwards.
