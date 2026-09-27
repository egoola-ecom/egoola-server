# Category Tree APIs — Frontend Guide

Two read-only, Admin-only endpoints on top of the existing Category CRUD. Both live under
`/api/v1/catalog/categories/` alongside List/Create/Update/Delete, and both need the same
Admin bearer token as the rest of that resource.

## 1. Get Category Parent Chain

Resolves one or more categories' full ancestor chain in a single call — useful anywhere you
show a category with breadcrumbs (e.g. "Electronics > Mobiles > Smartphones").

```
GET /api/v1/catalog/categories/parent-chain/?categoryIds=1,2
```

**Query params**

| Param | Required | Notes |
|---|---|---|
| `categoryIds` | Yes | One or more category ids, comma-separated (e.g. `1,2,3`). Unknown or non-numeric ids are silently skipped — they just don't appear in the response. |

**Response** — an array, one entry per requested category (in the order you passed them),
each with its own details plus a `parents` array. `parents` is ordered **top-level ancestor
first, immediate parent last** — index `0` is always the root of the tree, and the last index
is always the direct parent of the category itself. A top-level category (no parent at all)
gets `"parents": []`.

```json
[
  {
    "id": 2,
    "type": "product",
    "name": "Mobiles",
    "slug": "mobiles",
    "image_path": null,
    "image_url": null,
    "sort_order": 1,
    "status": "active",
    "parents": [
      {
        "id": 1,
        "type": "product",
        "name": "Electronics",
        "slug": "electronics",
        "image_path": null,
        "image_url": null,
        "sort_order": 1,
        "status": "active"
      }
    ]
  },
  {
    "id": 1,
    "type": "product",
    "name": "Electronics",
    "slug": "electronics",
    "image_path": null,
    "image_url": null,
    "sort_order": 1,
    "status": "active",
    "parents": []
  }
]
```

**Error** — `categoryIds` missing or empty:

```json
{ "categoryIds": "Provide one or more comma-separated category ids." }
```
`400 Bad Request`

## 2. Get Category Tree

Returns the whole category hierarchy as a nested tree — built for rendering the tree view
while creating a category or picking/changing its parent. **Not paginated** — every matching
category comes back in one response.

```
GET /api/v1/catalog/categories/tree/?type=product&categoryName=
```

**Query params** (both optional)

| Param | Notes |
|---|---|
| `type` | Exact match — `product` or `service`. Since a category's `parent` must always be the same `type` as itself, filtering the roots by type automatically filters every descendant too. Leave it out to get both trees back. |
| `categoryName` | Case-insensitive substring match on `name`. See filtering behavior below. |

**Filtering behavior for `categoryName`**

This isn't a flat search — it prunes the *tree*, so the result is always still valid tree
structure you can render directly:

- Any category whose name contains the search text is a "match".
- Every match's **ancestor path** is kept, so you can still see where in the tree it sits.
- Every match's **full descendant subtree** is kept, so the matched branch stays fully
  browsable/selectable.
- Anything not connected to a match that way — sibling categories, unrelated branches — is
  dropped.

**Response shape** — an array of root categories, each with a `children` array of the same
shape, recursively:

```json
[
  {
    "id": 1,
    "type": "product",
    "name": "Electronics",
    "slug": "electronics",
    "image_path": null,
    "image_url": null,
    "sort_order": 1,
    "status": "active",
    "children": [
      {
        "id": 2,
        "type": "product",
        "name": "Mobiles",
        "slug": "mobiles",
        "image_path": null,
        "image_url": null,
        "sort_order": 1,
        "status": "active",
        "children": []
      },
      {
        "id": 3,
        "type": "product",
        "name": "Laptops & Computers",
        "slug": "laptops-computers",
        "image_path": null,
        "image_url": null,
        "sort_order": 2,
        "status": "active",
        "children": []
      }
    ]
  },
  {
    "id": 4,
    "type": "product",
    "name": "Fashion",
    "slug": "fashion",
    "image_path": null,
    "image_url": null,
    "sort_order": 2,
    "status": "active",
    "children": [
      { "id": 5, "type": "product", "name": "Men's Clothing", "slug": "mens-clothing", "image_path": null, "image_url": null, "sort_order": 1, "status": "active", "children": [] },
      { "id": 6, "type": "product", "name": "Women's Clothing", "slug": "womens-clothing", "image_path": null, "image_url": null, "sort_order": 2, "status": "active", "children": [] }
    ]
  }
]
```

**Example — `?type=product&categoryName=cloth`**, against the same data: only the "Fashion"
branch survives (kept as ancestor context for the two matching "Clothing" categories);
"Electronics" and everything else is pruned out entirely.

```json
[
  {
    "id": 4,
    "type": "product",
    "name": "Fashion",
    "slug": "fashion",
    "image_path": null,
    "image_url": null,
    "sort_order": 2,
    "status": "active",
    "children": [
      { "id": 5, "type": "product", "name": "Men's Clothing", "slug": "mens-clothing", "image_path": null, "image_url": null, "sort_order": 1, "status": "active", "children": [] },
      { "id": 6, "type": "product", "name": "Women's Clothing", "slug": "womens-clothing", "image_path": null, "image_url": null, "sort_order": 2, "status": "active", "children": [] }
    ]
  }
]
```
