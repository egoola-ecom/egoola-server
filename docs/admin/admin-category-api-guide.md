# Admin Category API Guide

Admin management of **Categories** — the single, self-referencing tree used for both product
and service (gig/job) listings. Create, Update, List, Delete here; for the two read-only
hierarchy helpers (parent chain, full tree), see
[`category-tree-api-guide.md`](category-tree-api-guide.md).

Base URL: `/api/v1/catalog/categories/`. Admin token only (401 with none, 403 with a
seller/buyer token).

---

## Table of contents

- [1. Fields](#1-fields)
- [2. List — `GET /catalog/categories/`](#2-list-get-catalogcategories)
- [3. Create — `POST /catalog/categories/`](#3-create-post-catalogcategories)
- [4. Update — `PATCH /catalog/categories/{id}/`](#4-update-patch-catalogcategoriesid)
- [5. Delete — `DELETE /catalog/categories/{id}/`](#5-delete-delete-catalogcategoriesid)
- [6. No retrieve, by design](#6-no-retrieve-by-design)
- [7. Parent chain and tree](#7-parent-chain-and-tree)
- [8. Errors](#8-errors)

---

## 1. Fields

| Field | Type | Notes |
|---|---|---|
| `id` | integer | |
| `type` | string | `product` or `service`. Required on create; part of the duplicate-name and parent-type checks below. |
| `name` | string | Required. Unique per `type` — the same name is fine once under `product` and once under `service`, not twice within the same type. |
| `slug` | string | **Read-only.** Always generated from `name` on create, and regenerated whenever `name` genuinely changes. Never sent by the client. |
| `parent` | integer, nullable | Another category's id. Omit on `PATCH` to leave the current parent alone; send `null` to detach to top-level. Must be the same `type` as this category; a change that would create a cycle is rejected (see Errors). |
| `image` | file (write-only) | Optional. Sending one replaces the old file and deletes it from storage. |
| `image_path` / `image_url` | string | **Read-only.** `null` until an image is uploaded. |
| `sort_order` | integer | Default `0`. Drives list/tree ordering within the same parent. |
| `status` | string | `active` or `inactive`. Default `active`. |

No `created_at`/`updated_at` on this resource — not exposed by the serializer.

## 2. List — `GET /catalog/categories/`

Standard limit/offset pagination (`?limit=&offset=`). Ordered by `sort_order`, then `name`.

| Query param | What it does |
|---|---|
| `type` | `product` / `service` — exact match. |
| `status` | `active` / `inactive` — exact match. |
| `search` | Matches `name`. |

```json
GET /catalog/categories/?type=product&status=active
{
  "count": 1, "next": null, "previous": null,
  "results": [
    { "id": 1, "type": "product", "name": "Electronics", "slug": "electronics",
      "parent": null, "image_path": null, "image_url": null, "sort_order": 0, "status": "active" }
  ]
}
```

## 3. Create — `POST /catalog/categories/`

Multipart if sending an image, JSON otherwise.

```json
POST /catalog/categories/
{ "type": "product", "name": "Electronics" }
```
→ `201`, `"slug": "electronics"`, `"status": "active"`, `"parent": null`.

Nested under a parent:
```json
POST /catalog/categories/
{ "type": "product", "name": "Mobiles", "parent": 1 }
```

- `type`/`name` missing → `400`.
- `name` already used by another category of the same `type` → `400`.
- `parent` of a different `type` → `400`.

## 4. Update — `PATCH /catalog/categories/{id}/`

Partial update. Renaming regenerates the slug (same-name save keeps the existing slug).

```json
PATCH /catalog/categories/2/
{ "name": "Mobile Phones" }
```
→ `"slug": "mobile-phones"`.

Moving to a different parent:
```json
PATCH /catalog/categories/2/
{ "parent": 5 }
```

Detaching to top-level:
```json
PATCH /catalog/categories/2/
{ "parent": null }
```

Replacing the image: multipart `PATCH` with a new `image` file. Unknown id → `404`.

## 5. Delete — `DELETE /catalog/categories/{id}/`

`204`. Also deletes the image file from storage, if one was uploaded. Unknown id → `404`.

A category still referenced by a listing/gig/job, or that has a sub-category, cannot be
hard-deleted — `Listing.category` is a `PROTECT` foreign key, so this is refused with `409`,
not a crash. **Deactivate** (`status: "inactive"`) instead of deleting one that's ever been
used.

## 6. No retrieve, by design

There's no `GET /catalog/categories/{id}/` (`405`) — the list row already carries every field
there is, same as Geography and Payment Gateway. To show a category with its ancestors
(breadcrumb), use the parent-chain endpoint below.

## 7. Parent chain and tree

Two more read-only endpoints on this same resource — full detail in
[`category-tree-api-guide.md`](category-tree-api-guide.md):

- `GET /catalog/categories/parent-chain/?categoryIds=1,2` — each id's own data plus its
  ancestor chain, top-level first (for breadcrumbs).
- `GET /catalog/categories/tree/?type=product&categoryName=elec` — the full hierarchy (or a
  name-filtered slice of it) as a nested, unpaginated tree.

## 8. Errors

| Case | Status |
|---|---|
| No token | `401` |
| Seller or buyer token | `403` |
| Missing `type`/`name` on create | `400` |
| Duplicate `name` within the same `type` | `400` |
| `parent` of a different `type` | `400` |
| `parent` change that creates a circular chain | `400` |
| Unknown id (update/delete) | `404` |
| `GET` on the detail route | `405` |
| Deleting a category still in use (listing, or has a sub-category) | `409` |
