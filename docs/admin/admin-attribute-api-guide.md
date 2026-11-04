# Admin Attribute & Attribute Value API Guide

Admin management of **Attributes** (Size, Colour, ...) and **Attribute Values** (Size → S, M, L,
XL) — the options a product `Listing`'s SKUs are built from. For the full SKU picture (how a
listing combines these into priced, stocked SKUs), see
[`../attribute-sku-guide.md`](../attribute-sku-guide.md); this guide only covers the two
reference-data resources themselves.

Base URL: `/api/v1/catalog/`. Admin token only (401 with none, 403 with a seller/buyer token).
Unlike Category/Brand/Measurement, **both resources here have a Retrieve route** (`GET .../{id}/`).

---

## Table of contents

- [1. Attribute fields](#1-attribute-fields)
- [2. Attribute endpoints](#2-attribute-endpoints)
- [3. Attribute Value fields](#3-attribute-value-fields)
- [4. Attribute Value endpoints](#4-attribute-value-endpoints)
- [5. How values relate to their attribute](#5-how-values-relate-to-their-attribute)
- [6. Seller lookup](#6-seller-lookup)
- [7. Errors](#7-errors)

---

## 1. Attribute fields

| Field | Type | Notes |
|---|---|---|
| `id` | integer | |
| `name` | string | Required. Unique, case-insensitive. |
| `name_bn` | string | Optional. |
| `description` / `description_bn` | string | Optional. |
| `is_active` | boolean | Default `true`. An inactive attribute can't be picked for a new value. |
| `values` | array | **Read-only.** The attribute's own values, nested (id/name/name_bn/is_active each) — see section 5. Not writable here. |
| `created_by` / `creator_name` / `creator_type` | — | Read-only, stamped from the admin token. |
| `created_at` / `updated_at` | datetime | Read-only. |

No `image` on this resource.

## 2. Attribute endpoints

| Call | Result |
|---|---|
| `GET /catalog/attributes/?name=&is_active=&search=` | Paginated list. `search` matches English or Bangla name. |
| `POST /catalog/attributes/` | `201` |
| `GET /catalog/attributes/{id}/` | `200`, with nested `values` |
| `PATCH` / `PUT /catalog/attributes/{id}/` | `200` — only the attribute's own fields; `values` is ignored even if sent |
| `DELETE /catalog/attributes/{id}/` | `204` when unused. **Also deletes its values** (nothing else references a value's attribute once the attribute itself is gone). Used by a listing SKU → `409`, deactivate instead |

```json
POST /catalog/attributes/
{ "name": "Size", "name_bn": "সাইজ" }
```
→ `201`, `"is_active": true`, `"values": []`.

| Case | Status |
|---|---|
| `name` already used (any case) | `400` |
| Missing/blank `name` | `400` |

## 3. Attribute Value fields

| Field | Type | Notes |
|---|---|---|
| `id` | integer | |
| `attribute` | integer | Required on create. **Immutable after creation** — a SKU variant already points at the value, so moving it to a different attribute would change what that variant means. |
| `attribute_name` | string | Read-only, denormalized from `attribute`. |
| `name` | string | Required. Unique within the same `attribute` (case-insensitive) — the same name is fine under two different attributes (`M` as both a size and a colour code). |
| `name_bn` / `description` / `description_bn` | string | Optional. |
| `is_active` | boolean | Default `true`. An inactive value can't be picked for a new SKU variant. |
| `created_by` / `creator_name` / `creator_type` | — | Read-only. |
| `created_at` / `updated_at` | datetime | Read-only. |

## 4. Attribute Value endpoints

| Call | Result |
|---|---|
| `GET /catalog/attribute-values/?attribute=&name=&is_active=&search=` | Paginated list. `attribute` filters to one attribute's values. |
| `POST /catalog/attribute-values/` | `201` |
| `GET /catalog/attribute-values/{id}/` | `200` |
| `PATCH` / `PUT /catalog/attribute-values/{id}/` | `200` |
| `DELETE /catalog/attribute-values/{id}/` | `204` when unused. Used by a listing SKU → `409`, deactivate instead |

```json
POST /catalog/attribute-values/
{ "attribute": 1, "name": "XL", "name_bn": "এক্সএল" }
```

| Case | Status |
|---|---|
| Same `name` already under that `attribute` | `400` |
| Same `name` under a *different* `attribute` | Allowed |
| `attribute` is inactive | `400` |
| Unknown `attribute` | `400` |
| Changing `attribute` on an existing value | `400` (re-sending the same id is a no-op, fine) |

## 5. How values relate to their attribute

**Reading** an attribute and its values is one call — `GET /catalog/attributes/{id}/` already
returns `values` nested (prefetched, not a second query the client has to make).

**Writing** a value is always through `/catalog/attribute-values/`, never nested in an
Attribute `PATCH` — there is no array-diffing endpoint. To add a value, `POST` one row there
with the parent `attribute` id; to remove one, `DELETE` it there. `PATCH /catalog/attributes/{id}/`
only ever touches the attribute's own fields (`name`, `name_bn`, `description`, `is_active`).

## 6. Seller lookup

A seller building a listing's options uses a separate, read-only endpoint — active attributes
only, each with only its active values nested:

```
GET /api/v1/seller/lookups/attributes/?search=
```

```json
[
  { "id": 1, "name": "Size", "name_bn": "সাইজ", "values": [
    { "id": 1, "name": "S", "name_bn": null },
    { "id": 2, "name": "M", "name_bn": null }
  ] }
]
```

## 7. Errors

| Case | Status |
|---|---|
| No token | `401` |
| Seller or buyer token | `403` |
| Missing/duplicate `name` (Attribute, or within the same `attribute` for a Value) | `400` |
| `AttributeValue.attribute` unknown, inactive, or changed after creation | `400` |
| Unknown id (retrieve/update/delete, either resource) | `404` |
| Deleting an Attribute or AttributeValue still used by a listing SKU | `409` |
