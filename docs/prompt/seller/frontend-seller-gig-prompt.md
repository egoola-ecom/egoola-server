# Brief for the Egoola Web session — Gig screens, validation pass

Target: **`egoola-web`**, the seller panel's Gigs screens (`src/app/(seller)/seller/gigs/...`,
`src/lib/seller-gig-api.ts`). Backend (`egoola-server`, Django REST) is done and tested for seller
gigs. Per the earlier "build every seller feature" work, gigs (lookups, list, detail, create,
edit, thumbnail/gallery files) should already be built. **Do not rebuild from scratch** —
cross-check the existing implementation against the contract below, fix anything that doesn't
match, and report any mismatch you find. Do not push; commit locally only if asked. Do not change
`egoola-server` — if the contract itself looks wrong or something needed is missing on the
backend, stop and report it instead of working around it in the app.

Read first: `egoola-server/docs/seller/seller-gig-api-guide.md` (the full contract — read it
fully). Plain-language tour: `egoola-server/docs/Egoola_Listing_Guide.md` section 12. Shared
package/SKU reference: `egoola-server/docs/listing-complete-guide.md` section 14,
`egoola-server/docs/attribute-sku-guide.md` section 8. Postman:
`postman/seller/Egoola-SellerApp.postman_collection.json` → **Seller gigs** folder (the **Seller
listings** and **Seller jobs & bidding** folders are separate screens, ignore them here).

Run the backend with `uv run manage.py runserver 8000`. Test accounts:
`egoola-server/docs/test-accounts.md` — seller phone `0100000002` / `Test@12345`. That seed account
is **unverified**; gig endpoints need a seller who **can operate** (verified **and** active), so
either approve it first (`Admin` token: `PATCH /api/v1/accounts/sellers/{id}/
{"verification_status": "verified", "status": "active"}` — see `docs/admin/seller-verification-guide.md`)
or use an already-approved seller from your own dev data. Admin login for that step:
`test.admin@egoola.com` / `Test@12345`.

---

## 1. What this is

A **gig** is a service a seller offers (cleaning, photography, logo design, repair) — a row of the
shared `listings` table (`catalog_type = service`, `posted_by_role = seller_offer`), but priced
differently from a product: not by options+stock SKUs, but by **packages** — one SKU per
**price type** (`hourly`, `daily`, `weekly`, `monthly`, `fixed`). A gig is NOT a product
(`/seller/listings/`, options+stock) or a job (a buyer's request, `/seller/jobs/...`) — a product
id on the gig endpoints is `404`, and a product-only field here is `400`.

Everything about a seller's own gig is two APIs:

1. **`/seller/gigs/`** — create, retrieve, update, list. JSON only — a file here is `415`. **No
   delete** (`405`) and **no moderation actions** — a seller never sets `status` directly; only an
   admin approves/rejects/requests changes, from the separate admin screen.
2. **`/seller/listing-files/{id}/`** — thumbnail + gallery media, multipart only, a separate call
   from create/update — **same shared endpoint as products**, just pointed at a gig's id.

Supporting reference data the gig form needs: `/seller/lookups/categories/` (`type=service`,
active only) and the public geography endpoints for country/state/city/thana. There is **no**
brand, measurement or attribute lookup for a gig — don't show those pickers on this form.

## 2. The contract

Header: `Authorization: Bearer <seller access token>` everywhere. `401` no token, `403` admin/buyer
token or a seller who cannot operate yet (see §1 of the guide for the exact message).

| Call | What it does |
|---|---|
| `POST /seller/gigs/` | create, always `status: pending`, owner forced server-side to the logged-in seller |
| `GET /seller/gigs/` | list my own gigs, limit/offset (`count`/`next`/`previous`/`results`, default limit 20, max 100) |
| `GET /seller/gigs/{id}/` | detail of my own gig; another seller's or an admin's is `404` |
| `PATCH`/`PUT /seller/gigs/{id}/` | edit fields and/or packages — this is also how a rejected gig gets resubmitted (§4) |
| `DELETE /seller/gigs/{id}/` | always `405` — do not build a delete action on this screen |

List filters: `status`, `category`, `price_type` (an **active** package priced that way),
`created_from`/`created_to`, `requested_from`/`requested_to` (dates, inclusive), `search` (title,
Bangla title, SKU code), `ordering` (`created_at`, `updated_at`, `requested_at`, `title`, `status`,
`id`).

### Fields (create/update body)

| Field | Notes |
|---|---|
| `category` | id, **required**, must be a `service`-type, active category |
| `title`, `description` | **required**; `title_bn`, `description_bn` optional |
| `delivery_days`, `urgent`, `package_includes`(`_bn`), `available_from`, `available_to` | optional service details |
| `country`, `state`, `city`, `thana` | ids, optional, must be on one geography branch |
| `skus` | **required on create** (or use the `price`+`price_type` shortcut) — §3 |
| `price`, `price_type`, `discounted_price`, `discount_start_date`, `discount_end_date`, `sku` | **create-only** shortcut for one default package with a single price type; `400` on update, and `400` if sent together with `skus` |
| `note` | ignored on create; meaningful only when saving a `rejected`/`changes_requested` gig (§4) |
| *(read-only, every response)* | `id`, `slug`, `price`, `discounted_price` (lowest-rate active package), `skus[].effective_price`/`is_discount_active`, `media`, `status`, `status_change_logs`, `requested_at`, `created_at`, `updated_at` |
| *(never present on the seller's response)* | `seller`, `buyer`, `posted_by_role`, `info_change_logs` — admin-only; don't expect these fields |

**Refused on a gig** (`400`): `listing_type`, `brand`, `model`, `origin`(`_bn`), `warranty`(`_bn`),
`measurement`, `min_order_qty`, `condition_note`(`_bn`), `attributes`, `price_tiers` — all
product-only. No file inputs on this form either — files are the separate step in §5.

List row is lighter: `id, title, title_bn, slug, category, price, discounted_price, price_type,
image_url, status, note, requested_at, created_at, updated_at`.

## 3. Packages (gig SKUs) — the part that's different from Products

Same ways to send it as the attribute/SKU guide describes for products, adapted:

- **Full form**: `"skus": [{ "price_type": "...", "price": "...", "discounted_price": "...",
  "description": "...", "description_bn": "..." }, ...]`. On update, items **merge by `id`**: an
  item with `id` edits that package, one without `id` adds a package, a package left out of the
  array is untouched. Packages are never deleted — hide one with `{"id": 212, "is_active": false}`.
- **Shortcut** (create only, one package): top-level `price` + `price_type` (+ optional
  `discounted_price`, discount dates, `sku`) — becomes one default package. Not usable on update;
  use `skus` there.

**One package per price type.** A second `hourly` package — in the same request, or against one
already on the gig (hidden or not) — is `400 {"skus": ["Every gig SKU needs its own price type (two
SKUs have the same one)."]}`. The form should block adding a second package of a price type
already present/hidden, and instead point the seller at reactivating the hidden one.

**No stock, no options.** `stock_qty` and `variants` must not be sent on a gig package — `400`
otherwise (`"A gig has no stock."` / `"A gig SKU has no options."`). There is **no duration field**
on a package — the buyer chooses the duration when ordering (not built on the buyer side yet);
don't build a duration input on this form.

`discounted_price` defaults to `price` when omitted, never higher than `price`; a discount only
applies between `discount_start_date`/`discount_end_date`; raising a discount above the (possibly
updated) `price` is `400`.

## 4. Status: a seller never sets it, saving can move it

```
pending ──(admin approves)────────────► approved
   ▲            │
   │            ├──(admin rejects, note required)────► rejected
   │            └──(admin requests changes, note required)──► changes_requested
   │                                                               │
   └───────────────── a seller SAVES the gig ───────────────────┘
```

A seller's `PATCH`/`PUT` never includes `status` — it's ignored if sent. What a save does instead:

| The gig is | A seller's save (even an empty `{}`) does |
|---|---|
| `pending` | stays `pending`; `requested_at` unchanged |
| `approved` | stays `approved`, whatever else changed; admin sees it in their own change log (not visible to the seller) |
| `rejected`/`changes_requested` | goes back to **`pending`**, `requested_at` = now — **this is the resubmit, there is no separate resubmit endpoint/button to call** |

For a `rejected`/`changes_requested` gig, a `note` sent with the save is the **seller's reply to
the reviewer** (omitting it clears it); in any other state a `note` on the request body is ignored.
The admin's own rejection reason lives in `status_change_logs` and is never overwritten by the
seller's note.

## 5. Thumbnail and gallery media

Separate from create/update, multipart, same id, **same shared endpoint as products**:
`POST`/`PATCH /seller/listing-files/{id}/`.

| Call | Fields | Behavior |
|---|---|---|
| `POST` | `thumbnail` (file, optional), `media_file` (repeated, optional) | Adds thumbnail only if the gig has none yet (`400` if one exists — use `PATCH` to replace); adds gallery files |
| `PATCH` | `remove_thumbnail` (bool), `thumbnail` (file — always replaces), `remove_media_ids` (comma ids), `media_file` (repeated) | All fields independent/optional; empty body is a `200` no-op |

Response: `{image_path, image_url, media, status}` — `status` never changes from a files call. Old
files are deleted from storage on replace/remove. Thumbnail: JPG/PNG/WEBP, ≤10 MB. Gallery:
JPG/PNG/WEBP/GIF/MP4/PDF, ≤10 MB each, max 10 per request / 20 per gig.

## 6. Errors (cheat sheet)

| Case | Error |
|---|---|
| Non-service or inactive `category` | `400` under `category` |
| No `skus` and no `price`+`price_type` shortcut | `400` `{"skus": ["A listing needs at least one SKU: send `skus`, or `price` for a single default SKU."]}` |
| `skus` + shortcut together | `400` `{"skus": "Send either `skus` or the price shortcut, not both."}` |
| Missing `price_type` on a package | `400` `{"skus": {"0": {"price_type": "This field is required for a gig SKU."}}}` |
| `stock_qty` / `variants` sent on a package | `400` (a gig has no stock, no options) |
| Two packages with the same `price_type` | `400` `{"skus": ["Every gig SKU needs its own price type (two SKUs have the same one)."]}` |
| SKU `discounted_price` > `price` | `400` under `skus` |
| Plain `price`/`price_type` on **update** | `400` `{"price": "Prices and stock are changed through `skus`."}` |
| Product-only field sent (`brand`, `price_tiers`, `attributes`, ...) | `400` |
| Same title as one of mine | `400` `{"title": ["You already have a listing with this title. Update the existing listing instead. (listing #N)"]}` |
| Geography not on one branch | `400` under the lower field |
| A product id on this screen | `404` |
| Another seller's / admin's gig | `404` |
| Seller cannot operate (pending/rejected/paused) | `403` with the message from the guide §1 |
| `DELETE` | `405` |
| Multipart on create/update | `415` |
| Thumbnail `POST` when one exists | `400` — use `PATCH` |

## 7. Cross-check tasks

1. **API client**: confirm `listGigs` (limit/offset + all filters above), `getGig`, `createGig`,
   `updateGig`, `uploadGigFiles` (POST, multipart), `updateGigFiles` (PATCH, multipart) all exist
   and match these shapes — and that there is **no** delete call wired to this screen.
2. **List screen**: filter bar (status, category, price_type, date range, search), table/cards
   (thumbnail, title, category, price shown **with its unit** — "from ৳500 / hour", not a bare
   number — status, requested_at/created_at), limit/offset pager, a "Create gig" entry point.
3. **Create/edit form**: service-category picker (active only, `type=service`), title/description +
   Bangla, delivery days/urgent/package-includes(+Bangla)/availability dates, geography cascader,
   **package builder**: one row per price type, price + discounted price + discount dates +
   description(+Bangla), add/hide controls, client-side guard against a second row of a price type
   already present (active or hidden). No stock field, no variant/option picker, no quantity-tier
   builder, no brand/model/measurement fields on this form. No file inputs — files are the
   separate step in §5.
4. **Detail view**: all fields, package table with `effective_price`/`is_discount_active` per row
   (and which price type is hidden vs active), thumbnail + gallery, `status_change_logs` timeline
   (with the admin's note clearly shown when `rejected`/`changes_requested`), a note field for the
   seller's reply that only appears/matters in those two states. **No moderation controls** on this
   screen (that's the admin app).
5. **Resubmit UX**: confirm the save button communicates "Save & resubmit" (or similar) when the
   gig is `rejected`/`changes_requested`, since there is no separate resubmit action to call —
   saving unchanged content still resubmits it.
6. **Thumbnail/media panel** (on detail, after the gig exists): upload thumbnail (disabled/hidden
   once one exists — "replace" instead, the PATCH path), add gallery files, remove gallery files
   (multi-select → `remove_media_ids`), replace/remove thumbnail. If the Products screen already
   has this panel built as a reusable component, confirm the Gigs screen points it at the gig's id
   rather than duplicating it.
7. Confirm the app never sends `status`, `seller`, `buyer`, or `posted_by_role` from this screen,
   and never renders an `info_change_logs` section (it doesn't exist for a seller).
8. Confirm **Gigs** is its own entry point in the seller nav, separate from **Products**, and that
   the same-title check error names the conflicting gig/listing id correctly either way (a product
   and a gig may share a title — only two gigs, or two products, of the same seller may not).

## 8. Verify (device/simulator, seller role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Create a gig with the `price`+`price_type` shortcut | `201`, one default package, `status: pending` |
| 2 | Create a gig with hourly + weekly + fixed packages | `201`, 3 packages |
| 3 | Create a second gig with the exact same title (any case/spacing) | `400` under `title`, pointing at the existing gig's id |
| 4 | Try to add a second `hourly` package on that gig | blocked client-side, or `400` from the server if not |
| 5 | Hide the hourly package, then try to add a *new* hourly package instead of reactivating | `400` — same price-type conflict even hidden |
| 6 | Reactivate the hidden package instead | `200`, rate editable again |
| 7 | Try `stock_qty` or an option/variant on a package | `400`, surfaced clearly |
| 8 | Try a product-only field (e.g. `brand`) on the gig form | not even offered; if forced via API, `400` |
| 9 | Edit a package's price only (no discount) | `discounted_price` follows the new `price` |
| 10 | Try a plain `{"price": "10.00"}` PATCH | `400` — must go through `skus` |
| 11 | Send `{"status": "approved"}` in a PATCH body | ignored — status unchanged, no history row |
| 12 | [Admin] reject the gig with a note, then [seller] retrieve it | gig shows `status: rejected`, the admin's note, and it in `status_change_logs` |
| 13 | Edit the rejected gig and save (any content change), with a reply `note` | `200`, `status: pending`, `requested_at` refreshed, new history row with the seller's note |
| 14 | Edit an **approved** gig's description only | `200`, `status` stays `approved` |
| 15 | Upload a thumbnail, then POST another thumbnail | first `201`; second `400` (use PATCH to replace) |
| 16 | PATCH `remove_thumbnail: true` plus two new `media_file`s in one call | thumbnail cleared, gallery grows by 2 |
| 17 | Try `DELETE` on one of my own gigs | `405`, and confirm the app has no UI path that attempts this |
| 18 | Open another seller's or an admin's gig id directly (if reachable) | `404`, handled without a crash |
| 19 | Open a product id on this screen's detail route | `404`, handled without a crash |
| 20 | Create a product and a gig with the same title (same seller) | both succeed — the same-title rule is per kind |

Report which cases pass, what you changed to make them pass, and anything in
`seller-gig-api-guide.md` or this brief that looked wrong, missing, or unclear once you tried it
against the real API.
