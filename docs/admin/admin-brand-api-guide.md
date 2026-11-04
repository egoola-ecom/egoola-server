# Admin Brand API Guide

Admin-managed Brand reference data under the Listing module — a `Listing` picks a brand from
here instead of typing a free-text brand name. Create, Update, List, Delete. Image upload
works the same way as Category.

Base URL: `/api/v1/catalog/brands/`. Admin token only (401 with none, 403 with a seller/buyer
token).

---

## Table of contents

- [1. Fields](#1-fields)
- [2. List — `GET /catalog/brands/`](#2-list-get-catalogbrands)
- [3. Create — `POST /catalog/brands/`](#3-create-post-catalogbrands)
- [4. Update — `PATCH /catalog/brands/{id}/`](#4-update-patch-catalogbrandsid)
- [5. Delete — `DELETE /catalog/brands/{id}/`](#5-delete-delete-catalogbrandsid)
- [6. No retrieve, by design](#6-no-retrieve-by-design)
- [7. Seller lookup](#7-seller-lookup)
- [8. Errors](#8-errors)

---

## 1. Fields

| Field | Type | Notes |
|---|---|---|
| `id` | integer | |
| `name` | string | Required. Unique across the whole project — **not** scoped per `type` the way Category's name check is (Brand has no `type`). |
| `slug` | string | **Read-only.** Always generated from `name` on create, and regenerated whenever `name` genuinely changes. |
| `image` | file (write-only) | Optional. Sending one on create or update replaces the old file. Subject to the global upload size cap (images `> 2 MB` → `400`, see `config/storage.py`). |
| `image_path` / `image_url` | string | **Read-only.** `null` until an image is uploaded. |
| `is_active` | boolean | Default `true`. A listing may not pick an inactive brand. **Explicitly declared `default=True` on the serializer** — not left to auto-build — so a multipart create that omits it still saves `true` (DRF treats a missing boolean in form data as an HTML unchecked-checkbox, i.e. `false`, unless the field's own default is set). |
| `created_by` / `creator_name` / `creator_type` | — | **Read-only.** Stamped from the Admin token. |

No `created_at`/`updated_at` on this resource — not exposed by the serializer.

## 2. List — `GET /catalog/brands/`

Standard limit/offset pagination (`?limit=&offset=`). Ordered by `name`.

| Query param | What it does |
|---|---|
| `name` | Case-insensitive substring match on `name`. |
| `is_active` | `true` / `false` — exact match. |
| `search` | Same field, alternate param (DRF `SearchFilter`). |

```json
GET /catalog/brands/?is_active=true
{
  "count": 1, "next": null, "previous": null,
  "results": [
    { "id": 1, "name": "Samsung", "slug": "samsung",
      "image_path": null, "image_url": null, "is_active": true,
      "created_by": 1, "creator_name": "Admin One", "creator_type": "admin" }
  ]
}
```

## 3. Create — `POST /catalog/brands/`

JSON if no image, multipart if sending one.

```json
POST /catalog/brands/
{ "name": "Samsung" }
```
→ `201`, `"slug": "samsung"`, `"is_active": true`, `"image_path": null`.

With a logo:
```
POST /catalog/brands/   (multipart/form-data)
name=Samsung
image=<file>
```

- `name` missing → `400`.
- `name` already used (project-wide) → `400`.
- Image over 2 MB → `400` (`"<filename>: image files must be 2 MB or smaller."`).

## 4. Update — `PATCH /catalog/brands/{id}/`

Partial update. Renaming regenerates the slug.

```json
PATCH /catalog/brands/3/
{ "name": "Samsung Electronics" }
```

Deactivating:
```json
PATCH /catalog/brands/3/
{ "is_active": false }
```

Replacing the image: multipart `PATCH` with a new `image` file. Unknown id → `404`.

## 5. Delete — `DELETE /catalog/brands/{id}/`

`204`. Also deletes the image file from storage, if one was uploaded. Unknown id → `404`.

A brand still referenced by any listing — including a soft-deleted one — cannot be hard-deleted:
`Listing.brand` is a `PROTECT` foreign key, so this is refused with `409`, not a crash.
**Deactivate** (`is_active: false`) instead of deleting one that's ever been used.

## 6. No retrieve, by design

There's no `GET /catalog/brands/{id}/` (`405`) — the list row already carries every field there
is, same as Category/Measurement/Payment Gateway.

## 7. Seller lookup

A seller picking a brand for their own listing uses a separate, read-only endpoint — active
brands only, no image:

```
GET /api/v1/seller/lookups/brands/?search=
```

```json
[ { "id": 1, "name": "Samsung", "slug": "samsung" } ]
```

## 8. Errors

| Case | Status |
|---|---|
| No token | `401` |
| Seller or buyer token | `403` |
| Missing `name` on create | `400` |
| Duplicate `name` (project-wide) | `400` |
| Image over 2 MB | `400` |
| Unknown id (update/delete) | `404` |
| `GET` on the detail route | `405` |
| Deleting a brand still used by a listing | `409` |
