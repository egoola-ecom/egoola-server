# Brief for the Egoola Seller App session (Flutter) — Product (Listing) screens, validation pass

Target app: **`egoola-seller`** (Flutter, the seller mobile app). Backend (`egoola-server`, Django
REST) is done and tested for seller product listings. Per the earlier
"build every seller feature" prompt, product listings (lookups, list, detail, create, edit,
thumbnail/gallery files) should already be built. **Do not rebuild from scratch** — cross-check the
existing implementation against the contract below, fix anything that doesn't match, and report any
mismatch you find. Do not push; commit locally only if asked. Do not change `egoola-server` — if the
contract itself looks wrong or something needed is missing on the backend, stop and report it instead
of working around it in the app.

Read first: `egoola-server/docs/seller/seller-listing-api-guide.md` (the full contract — read it fully;
it supersedes any older copy of this content in `docs/seller/seller-api-guide.md` section 6, which it
was extracted from). Plain-language tour: `egoola-server/docs/Egoola_Listing_Guide.md`. Shared
field/SKU/attribute reference: `egoola-server/docs/listing-complete-guide.md` and
`egoola-server/docs/attribute-sku-guide.md`. Postman:
`postman/seller/Egoola-SellerApp.postman_collection.json` → **Seller listings** folder (already covers
every call in this brief — no new collection needed; the **Seller gigs** and **Seller jobs & bidding**
folders are separate screens, ignore them here).

Run the backend with `uv run manage.py runserver 8000`. Test accounts:
`egoola-server/docs/test-accounts.md` — seller phone `0100000002` / `Test@12345`. That seed account is
**unverified**; product endpoints need a seller who **can operate** (verified **and** active), so either
approve it first (`Admin` token: `PATCH /api/v1/accounts/sellers/{id}/ {"verification_status": "verified"}` —
see `docs/admin/seller-verification-guide.md`) or use an already-approved seller from your own dev data.
Admin login for that step: `test.admin@egoola.com` / `Test@12345`.

---

## 1. What this is

A **product** is one row of the shared `listings` table (`catalog_type = product`), owned by the
logged-in seller. It is NOT a gig (`/seller/gigs/`, a service offer) or a job (a buyer's request,
`/seller/jobs/...`) — a gig id on the product endpoints is `404`, and a service body here is `400`.

Everything about a seller's own product is two APIs:

1. **`/seller/listings/`** — create, retrieve, update, list. JSON only — a file here is `415`. **No
   delete** (`405`) and **no moderation actions** — a seller never sets `status` directly; only an
   admin approves/rejects/requests changes, from the separate admin screen.
2. **`/seller/listing-files/{id}/`** — thumbnail + gallery media, multipart only, a separate call from
   create/update. `POST` adds (thumbnail only if none exists yet, plus gallery files), `PATCH`
   replaces/removes the thumbnail and removes/adds gallery files.

Supporting reference data the product form needs: `/seller/lookups/categories/` (`type=product`,
active only), `/seller/lookups/brands/`, `/seller/lookups/measurements/`,
`/seller/lookups/attributes/` (SKU option pickers — see the attribute guide), and the public geography
endpoints for country/state/city/thana.

## 2. The contract

Header: `Authorization: Bearer <seller access token>` everywhere. `401` no token, `403` admin/buyer
token or a seller who cannot operate yet (see §1 of the guide for the exact message).

| Call | What it does |
|---|---|
| `POST /seller/listings/` | create, always `status: pending`, owner forced server-side to the logged-in seller |
| `GET /seller/listings/` | list my own products, limit/offset (`count`/`next`/`previous`/`results`, default limit 20, max 100) |
| `GET /seller/listings/{id}/` | detail of my own product; another seller's or an admin's is `404` |
| `PATCH`/`PUT /seller/listings/{id}/` | edit fields and/or SKUs — this is also how a rejected listing gets resubmitted (§4) |
| `DELETE /seller/listings/{id}/` | always `405` — do not build a delete action on this screen |

List filters: `status`, `listing_type`, `category`, `brand`, `created_from`/`created_to`,
`requested_from`/`requested_to` (dates, inclusive), `search` (title, Bangla title, SKU code, brand
name), `ordering` (`created_at`, `updated_at`, `requested_at`, `title`, `status`, `id`).

### Fields (create/update body)

| Field | Notes |
|---|---|
| `category` | id, **required**, must be a `product`-type, active category |
| `catalog_type` | fixed `"product"` on this screen; sending `"service"` is `400` |
| `listing_type` | `general`/`used`/`village`/`retail`/`wholesale`/`brand`, optional; `brand` makes `brand` mandatory |
| `title`, `description` | **required**; `title_bn`, `description_bn` optional |
| `brand` | id, optional (mandatory if `listing_type = brand`); must be active |
| `model`, `origin`(`_bn`), `warranty`(`_bn`), `min_order_qty`, `measurement`, `condition_note`(`_bn`), `attributes` | optional, product-only |
| `country`, `state`, `city`, `thana` | ids, optional, must be on one geography branch |
| `skus` | **required on create** (or use the `price` shortcut) — §3 |
| `price`, `discounted_price`, `discount_start_date`, `discount_end_date`, `stock_qty`, `sku` | **create-only** shortcut for one default SKU with no options; `400` on update, and `400` if sent together with `skus` |
| `price_tiers` | optional, quantity pricing — §3 |
| `note` | ignored on create; meaningful only when saving a `rejected`/`changes_requested` listing (§4) |
| *(read-only, every response)* | `id`, `slug`, `price`, `discounted_price` (cheapest active SKU), `skus[].effective_price`/`is_discount_active`, `media`, `status`, `status_change_logs`, `requested_at`, `created_at`, `updated_at` |
| *(never present on the seller's response)* | `seller`, `buyer`, `posted_by_role`, `info_change_logs` — admin-only; don't expect these fields |

List row is lighter: `id, title, title_bn, slug, catalog_type, listing_type, category, brand, price,
discounted_price, status, note, requested_at, created_at, updated_at`.

## 3. SKUs, price tiers, and the price shortcut

Same rules as the admin side — a product needs at least one SKU. Two ways to send it:

- **Full form**: `"skus": [{ "sku": "...", "price": "...", "discounted_price": "...", "stock_qty": ..., "variants": [{"attribute": id, "attribute_value": id}, ...] }, ...]`. On update, items **merge by `id`**: an item with `id` edits that SKU, one without `id` adds a SKU, a SKU left out of the array is untouched. SKUs are never deleted — hide one with `{"id": 7, "is_active": false}`.
- **Shortcut** (create only, no options): top-level `price` (+ optional `discounted_price`, discount dates, `stock_qty`, `sku`) — becomes one default SKU. Not usable on update; use `skus` there.

`discounted_price` defaults to `price` when omitted, never higher than `price`; a discount only applies
between `discount_start_date`/`discount_end_date`; raising a discount above the (possibly updated)
`price` is `400`. Full SKU/attribute rules: `../attribute-sku-guide.md`.

`price_tiers`: sending the key **replaces the entire list** (`[]` clears it); omit the key on PATCH to
leave tiers untouched. Each tier: `min_qty`, `max_qty` (`null` = "and above"), `price`,
`discounted_price` (defaults to `price`). Tiers must not overlap and only the last may be open-ended.

## 4. Status: a seller never sets it, saving can move it

```
pending ──(admin approves)────────────► approved
   ▲            │
   │            ├──(admin rejects, note required)────► rejected
   │            └──(admin requests changes, note required)──► changes_requested
   │                                                               │
   └───────────────── a seller SAVES the listing ───────────────┘
```

A seller's `PATCH`/`PUT` never includes `status` — it's ignored if sent. What a save does instead:

| The listing is | A seller's save (even an empty `{}`) does |
|---|---|
| `pending` | stays `pending`; `requested_at` unchanged |
| `approved` | stays `approved`, whatever else changed; admin sees it in their own change log (not visible to the seller) |
| `rejected` / `changes_requested` | goes back to **`pending`**, `requested_at` = now — **this is the resubmit, there is no separate resubmit endpoint/button to call** |

For a `rejected`/`changes_requested` listing, a `note` sent with the save is the **seller's reply to
the reviewer** (omitting it clears it); in any other state a `note` on the request body is ignored.
The admin's own rejection reason lives in `status_change_logs` and is never overwritten by the
seller's note.

## 5. Thumbnail and gallery media

Separate from create/update, multipart, same id: `POST`/`PATCH /seller/listing-files/{id}/`.

| Call | Fields | Behavior |
|---|---|---|
| `POST` | `thumbnail` (file, optional), `media_file` (repeated, optional) | Adds thumbnail only if the listing has none yet (`400` if one exists — use `PATCH` to replace); adds gallery files |
| `PATCH` | `remove_thumbnail` (bool), `thumbnail` (file — always replaces), `remove_media_ids` (comma ids), `media_file` (repeated) | All fields independent/optional; empty body is a `200` no-op |

Response: `{image_path, image_url, media, status}` — `status` never changes from a files call. Old
files are deleted from storage on replace/remove. Thumbnail: JPG/PNG/WEBP, ≤10 MB. Gallery:
JPG/PNG/WEBP/GIF/MP4/PDF, ≤10 MB each, max 10 per request / 20 per listing.

## 6. Errors (cheat sheet)

| Case | Error |
|---|---|
| `listing_type: "brand"`, no `brand` | `400` `{"brand": [...]}` |
| Inactive/unknown `brand` | `400` `{"brand": [...]}` |
| No `skus` and no `price` shortcut | `400` `{"skus": ["A listing needs at least one SKU: send `skus`, or `price` for a single default SKU."]}` |
| `skus` + `price` shortcut together | `400` `{"skus": "Send either `skus` or the price shortcut, not both."}` |
| SKU/tier `discounted_price` > `price` | `400` under `skus`/`price_tiers` |
| Plain `price`/`stock_qty` on **update** | `400` `{"price": "Prices and stock are changed through `skus`."}` |
| Same title as one of mine | `400` `{"title": ["You already have a listing with this title. Update the existing listing instead. (listing #N)"]}` |
| Geography not on one branch | `400` under the lower field, e.g. `{"city": ["This city does not belong to the selected state."]}` |
| Service body, or a service-only field | `400` |
| A gig id on this screen | `404` |
| Another seller's / admin's listing | `404` |
| Seller cannot operate (pending/rejected/paused) | `403` with the message from the guide §1 |
| `DELETE` | `405` |
| Multipart on create/update | `415` |
| Thumbnail POST when one exists | `400` — use `PATCH` |

## 7. Cross-check tasks

1. **API client**: confirm `listProducts` (limit/offset + all filters above), `getProduct`,
   `createProduct`, `updateProduct`, `uploadProductFiles` (POST, multipart),
   `updateProductFiles` (PATCH, multipart) all exist and match these shapes — and that there is **no**
   delete call wired to this screen.
2. **List screen**: filter bar (status, category, brand, date range, search), table/cards (thumbnail,
   title, category, brand, price/discounted_price, status, requested_at/created_at), limit/offset
   pager, a "Create product" entry point.
3. **Create/edit form**: category picker (product types only, active), brand picker (active, required
   when `listing_type = brand`), title/description + Bangla, model/origin/warranty, measurement,
   geography cascader, SKU builder (variant picker, price, discounted price + discount dates, stock),
   price-tier builder (overlap validated client-side before submit), min_order_qty, condition_note. No
   file inputs on this form — files are the separate step in §5.
4. **Detail view**: all fields, SKU table with `effective_price`/`is_discount_active` per row, price
   tiers, thumbnail + gallery, `status_change_logs` timeline (with the admin's note clearly shown when
   `rejected`/`changes_requested`), a note field for the seller's reply that only appears/matters in
   those two states. **No moderation controls** on this screen (that's the admin app).
5. **Resubmit UX**: confirm the save button communicates "Save & resubmit" (or similar) when the
   listing is `rejected`/`changes_requested`, since there is no separate resubmit action to call —
   saving unchanged content still resubmits it.
6. **Thumbnail/media panel** (on detail, after the product exists): upload thumbnail (disabled/hidden
   once one exists — "replace" instead, the PATCH path), add gallery files, remove gallery files
   (multi-select → `remove_media_ids`), replace/remove thumbnail.
7. Confirm the app never sends `status`, `seller`, `buyer`, or `posted_by_role` from this screen, and
   never renders an `info_change_logs` section (it doesn't exist for a seller).

## 8. Verify (device/simulator, seller role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Create a product with the `price` shortcut, no brand | `201`, one default SKU, `status: pending` |
| 2 | Create with `listing_type: brand` and no `brand` | `400` under `brand` |
| 3 | Create a second listing with the exact same title (any case/spacing) | `400` under `title`, pointing at the existing listing's id |
| 4 | Create with two SKUs (Size × Colour) and overlapping price tiers | tier overlap rejected `400` before anything is saved |
| 5 | Edit a SKU's price only (no discount) | `discounted_price` follows the new `price` |
| 6 | Try a plain `{"price": "10.00"}` PATCH | `400` — must go through `skus` |
| 7 | Send `{"status": "approved"}` in a PATCH body | ignored — status unchanged, no history row |
| 8 | [Admin] reject the listing with a note, then [seller] retrieve it | listing shows `status: rejected`, the admin's note, and it in `status_change_logs` |
| 9 | Edit the rejected listing and save (any content change), with a reply `note` | `200`, `status: pending`, `requested_at` refreshed, new history row with the seller's note |
| 10 | Edit an **approved** listing's description only | `200`, `status` stays `approved` |
| 11 | Upload a thumbnail, then POST another thumbnail | first `201`; second `400` (use PATCH to replace) |
| 12 | PATCH `remove_thumbnail: true` plus two new `media_file`s in one call | thumbnail cleared, gallery grows by 2 |
| 13 | Try `DELETE` on one of my own listings | `405`, and confirm the app has no UI path that attempts this |
| 14 | Open another seller's or an admin's product id directly (if reachable, e.g. via a crafted id) | `404`, handled without a crash |
| 15 | Open a gig id on this screen's detail route | `404`, handled without a crash |

Report which cases pass, what you changed to make them pass, and anything in
`seller-listing-api-guide.md` or this brief that looked wrong, missing, or unclear once you tried it
against the real API.
