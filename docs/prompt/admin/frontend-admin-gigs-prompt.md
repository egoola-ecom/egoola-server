# Brief for the Egoola Web session — admin Gigs panel (validate implementation)

Backend done and tested in `egoola-server`: Admin CRUD + moderation for **Gigs** (a seller's service offer —
cleaning, photography, logo design, repair). This brief is for **cross-checking an existing/in-progress Gigs
screen**, not a from-scratch build — go through every section below against your implementation and report back
what matches, what doesn't, and why (a deliberate UI choice is fine, same as the earlier Products brief).

Read first: `egoola-server/docs/admin/admin-gigs-management-guide.md` (the full admin contract — read fully, this
brief summarizes it), `egoola-server/docs/listing-complete-guide.md` section 14 (the deeper technical reference,
every error case), `egoola-server/docs/Egoola_Listing_Guide.md` section 12 (plain-language version). Postman:
`Egoola-Gig` collection (standalone — run top to bottom once to see every call and response live) or the **Gigs**
folder inside `Egoola-Listing`. Run the backend with `uv run manage.py runserver 8000`; accounts in
`docs/test-accounts.md` (admin: `test.admin@egoola.com` / `Test@12345`).

---

## 1. What this is

A gig is a row of the same `listings` table as a product (`catalog_type = service`, `posted_by_role =
seller_offer`), with its own endpoints and its own price model: instead of options+stock SKUs, a gig has one SKU
("**package**") per **price type** (hourly, daily, weekly, monthly, fixed). Moderation, history, bulk actions,
pending list and the thumbnail/gallery API all work exactly like the product screen (section 2 assumes you already
have those patterns built for Products and just reuses them) — the differences are entirely in the fields and the
package pricing model (section 3).

A gig id is `404` on the product/job screens, and a product/job id is `404` here.

## 2. The contract

Header: `Authorization: Bearer <admin access token>`. `401` no token, `403` wrong role.

| Call | What it does |
|---|---|
| `POST /catalog/gigs/` | create. Default `approved`; `status` can be sent explicitly |
| `GET /catalog/gigs/` | list, limit/offset (`count`/`next`/`previous`/`results`, default limit 20) |
| `GET /catalog/gigs/requests/` | **pending queue only** (`status=pending`), cursor-paginated, newest first — separate from the product queue |
| `GET /catalog/gigs/{id}/` | detail |
| `PATCH`/`PUT /catalog/gigs/{id}/` | edit fields and/or move `status` (same call) |
| `DELETE /catalog/gigs/{id}/` | soft delete (`204`) |
| `POST /catalog/gigs/bulk-moderate/` | approve/reject/request-changes many at once — **only gig ids are touched**, a product/job id in the list is silently skipped |
| `POST`/`PATCH /catalog/listing-files/{id}/` | thumbnail + gallery — **same shared endpoint as products**, multipart |

List filters: `status`, `category`, `seller`, `price_type` (gigs with an active package of that type),
`created_from`/`created_to`, `requested_from`/`requested_to`. Search: title, Bangla title, SKU code.

### Fields

| Field | Notes |
|---|---|
| `category` | id, **required**, must be an active **service** category (a product category here is `400`) |
| `seller` | id, optional — leave unset for an admin-owned gig |
| `title`, `description` | **required**; `title_bn`, `description_bn` optional |
| `delivery_days`, `urgent`, `package_includes`(`_bn`), `available_from`, `available_to` | optional service details |
| `country`, `state`, `city`, `thana` | ids, optional, must be one geography branch |
| `skus` | **required on create** (or the `price`+`price_type` shortcut) — the packages, see §3 |
| `status`, `note` | same moderation rules as a product |
| *(read-only)* | `id`, `slug`, `price`/`discounted_price` (lowest-rate active package), `image_path`/`image_url`, `media`, `status_change_logs`, `info_change_logs`, `requested_at`, `created_at`, `updated_at` |

**Refused here** (`400`): `listing_type`, `brand`, `model`, `origin`(`_bn`), `warranty`(`_bn`), `measurement`,
`min_order_qty`, `condition_note`(`_bn`), `attributes`, `price_tiers` — all product-only. There is **no quantity
pricing** on a gig; don't show that builder on this form.

## 3. Packages (gig SKUs) — the part that's different from Products

Each package: `price_type` (**required**: hourly/daily/weekly/monthly/fixed), `price` (the rate), optional
`discounted_price` + discount date window, optional `description`(`_bn`), `is_active`. No `stock_qty`, no
`variants` — sending either is `400`.

- **One package per price type.** A second `hourly` package — in the same request, or against one already on the
  gig (hidden or not) — is `400 {"skus": ["Every gig SKU needs its own price type (two SKUs have the same one)."]}`.
  The form should block adding a second package of a price type already present/hidden, and instead point the admin
  at reactivating the hidden one.
- **At least one package required.** Same shortcut as a product's SKU: on create only, send `price` + `price_type`
  (+ optional discount/sku) directly on the gig instead of `skus`, for a one-package gig.
- **Packages are never deleted**, only hidden (`is_active: false`). Reactivate instead of re-adding.
- Update merges by `id` on `skus`: an item with `id` edits that package, one without adds a package, one left out
  is untouched.
- Discount math is the same as a product SKU: `discounted_price` never above `price`, only applies inside its date
  window, lowering `price` below a running discount is `400`.

## 4. Thumbnail and gallery

Identical to the product screen — same shared endpoint, same two-call shape (`POST` adds, `PATCH`
removes/replaces/adds), same 400 if you `POST` a thumbnail onto a gig that already has one. If your Products screen
already has this panel built as a reusable component, point it at the gig's id — there is nothing gig-specific
here.

## 5. Moderation, bulk, pending queue, history

All identical mechanics to Products: `PATCH {"status": ..., "note": ...}` for a single decision (note required for
`rejected`/`changes_requested`); `POST /catalog/gigs/bulk-moderate/` for many at once; `GET
/catalog/gigs/requests/` is its **own** cursor-paged queue, separate from the product one — don't merge them into
one inbox unless you also distinguish which kind each row is. `status_change_logs` vs `info_change_logs` are the
same two separate timelines as products (package/thumbnail edits go to the info log, never the status log).

## 6. Tasks (cross-check against your implementation)

1. **API client** — does it have the gig equivalents of every product call (§2)? Same function-naming convention
   you already settled on for products is fine (see the earlier Products brief's point 5 — naming mismatches
   there weren't flagged as bugs).
2. **List screen** — filter bar has `status`, `category` (service categories only), `seller`, `price_type`, date
   range, search; table shows thumbnail, title, category, price/discounted_price **and what it's for** (e.g. "450
   hourly" — don't show a bare number), status, requested_at/created_at; bulk approve/reject/request-changes action
   bar; "Create gig" button.
3. **Create/edit form** — service-category picker (active only); title/description + Bangla; delivery/urgent/
   package-includes(+Bangla)/availability dates; geography cascader; **package builder**: one row per price type,
   price + discount + discount dates + description(+Bangla), add/hide controls, client-side guard against a second
   row of a price type already present (active or hidden). No stock field, no variant/option picker, no quantity-
   tier builder on this form.
4. **Detail view** — all fields, package table with `effective_price`/`is_discount_active` per row (and which
   price type is hidden vs active), thumbnail + gallery, both history timelines kept visually distinct, moderation
   controls with required-note dialog on reject/request-changes, delete (confirm).
5. **Pending queue** — its own view/tab, not merged with the product queue.
6. **Entry point** — **Gigs** in the admin nav, separate from **Products**.

## 7. Verify (browser, admin role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Create a gig with the `price`+`price_type` shortcut, no `skus` | `201`, one package, `status: approved` |
| 2 | Create a gig with hourly + weekly + fixed packages | `201`, 3 packages |
| 3 | Try to add a second `hourly` package on that gig | blocked client-side, or `400` from the server if not |
| 4 | Hide the hourly package, then try to add a *new* hourly package instead of reactivating | `400` — same price-type conflict even hidden |
| 5 | Reactivate the hidden package instead | `200`, rate editable again |
| 6 | Try `stock_qty` or an option/variant on a package | `400`, surfaced clearly |
| 7 | Try a product-only field (e.g. `brand`) on the gig form | not even offered; if forced via API, `400` |
| 8 | Reject a gig without a note | `400` under `note` |
| 9 | Bulk-approve 3 gigs, one already approved | `updated` has 2, `skipped` has 1 |
| 10 | Upload a thumbnail, then `POST` a second one | first `201`; second is `400` on the `POST` path (one already exists) — replacing it is a `PATCH`, which always succeeds and swaps the file, `remove_thumbnail` ticked or not |
| 11 | Open the gig pending queue, approve one from there | leaves the queue, shows `approved` in the main list; product pending queue is unaffected |
| 12 | Soft-delete a gig, then retrieve it | `404` |
| 13 | Open a product id or job id on the gig detail route | `404`, handled without a crash |
| 14 | Bulk-moderate with a mixed list of gig ids and a product id | only the gig ids move; the product id is silently ignored |

Report which cases pass, what you changed, and anything in `admin-gigs-management-guide.md` or this brief that
looked wrong, missing, or unclear once you tried it against the real API.
