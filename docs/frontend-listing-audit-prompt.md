# Audit brief for the Egoola Web session — verify the complete Listings / Gigs implementation (Admin and Seller panels)

You are the **Egoola Web** session. Products and gigs (listings) are implemented in the web app, in the **admin panel** and the **seller panel**. The
backend enforces many rules and constraints. Your job now is **not** to build new features: it is to **prove that every item in this checklist is
implemented correctly**, fix every gap you find, and report the result. Be strict: "looks fine" is not evidence.

Read first: `egoola-server/docs/listing-complete-guide.md` (all sections; gigs = §14, thumbnail = §15), `egoola-server/docs/Egoola_Listing_Guide.md`
(plain words), `egoola-server/docs/seller-api-guide.md` (§6, 6b, 6.8), `egoola-server/docs/attribute-sku-guide.md`,
`egoola-server/docs/frontend-api-guide.md`, `egoola-server/docs/frontend-gigs-thumbnail-prompt.md`, `egoola-server/docs/test-accounts.md`. Paths: the
repos are under `/Users/ghl/Github/egoola/` (`egoola-web`, `egoola-server`, `egoola-document`). **Never edit `egoola-server`**; report backend bugs.

---

## How to work (three phases)

**Phase 1 — Audit (no code changes).** For every checklist item below, inspect the code and the screens. Produce a table with one row per item:
`ID | Status (Done / Partial / Missing / N/A) | Evidence (file:line, or the screen and what you saw) | Note`. "Done" needs evidence. Anything you did
not check is "Missing", never "Done". Save the table in `egoola-web/docs/listing-audit.md`.

**Phase 2 — Fix.** Fix every Partial and Missing item (smallest correct change; follow the existing patterns: `src/lib/*-api.ts`, `use-managed-list.ts`,
`authFetch`, `Modal`, `geography-fields`). Commit locally per logical group (no push). Update the table with the new status and evidence.

**Phase 3 — Test.** Run the backend (see the end), then exercise the **test matrix** (section 12) in the browser with the test accounts. Run
`npm run ci`. Record each matrix case as Pass / Fail with a one-line note. Fix failures and re-run until all pass.

Final report: counts (Done / Partial / Missing before and after), the test matrix result, open questions, and any **backend bug** (with the request and the
response). Update the Phase Tracker (`egoola-document/Egoola_Phase_Tracker.md`, Admin Web row 10.1; edit the file, do not commit that repo).

---

## 1. Structure and kinds

- **K1** Admin has two separate areas: **Listings** (products only) and **Gigs** (service offers only). Seller panel has the same split for the screens
  that exist (`/seller/listings/` products; `/seller/gigs/` gigs only if built).
- **K2** Listings area: no Service option anywhere; **Product is selected by default**. Gigs area: no Product option; **Service is selected by default**.
- **K3** The Listings list defaults to `catalog_type=product` (buyer job requests, `service` + `buyer_request`, still come from `/catalog/listings/`:
  hidden by that filter or labelled "Job request"). There is **no create-job form**.
- **K4** A gig id on `/catalog/listings/...` or a product id on `/catalog/gigs/...` (and the seller equivalents) is `404`: screens show "not found", not a crash.
- **K5** `catalog_type` and `posted_by_role` are never editable after creation (no input on edit forms). The gig endpoints do not need them in the body.
- **K6** `price_type` and `hourly_rate` do not appear on any listing or gig (removed). A SKU has **no `duration`** (no input, never sent).
- **K7** Menu badges: pending products `GET /catalog/listings/?status=pending&limit=1` and pending gigs `GET /catalog/gigs/?status=pending&limit=1` (read `count`),
  refreshed after every moderation action.

## 2. Access, login and error handling (both panels)

- **A1** Admin screens call `/catalog/*` with an **admin** token; any admin (not only super-admin) may use listings and gigs.
- **A2** Seller screens call `/seller/*` with a **seller** token. Wrong-role tokens give `403` (show "not allowed"); no token / invalid / inactive account gives
  `401` (clear the session and go to login, once, no loop).
- **A3** Refresh tokens **rotate**: `POST /auth/token/refresh/` returns a new `refresh`; both tokens are stored.
- **A4** Seller states (login response `verification_status`, `status`, `can_operate`): only **verified AND active** (`can_operate: true`) may use listings, gigs
  and the listing lookups. Everyone else gets `403` there. The seller panel shows the right message and **hides / disables listing screens and create buttons**:
  `unverified` / `pending`: "application under review"; `rejected`: show the reason and the Resubmit path (profile screens); `verified` + `inactive`: "account paused";
  `suspended`: login fails (`401`). A listing screen must never be reachable by a seller who cannot operate.
- **A5** Error shapes are mapped to the right field, not a generic toast: `{"field": ["msg"]}`, nested `{"skus": {"0": {"price": "msg"}}}` (index = row),
  `{"skus": ["msg"]}` (section error), `{"detail": "msg"}`. Non-field errors are shown in a visible banner.
- **A6** Money (`price`, `discounted_price`, `effective_price`) is handled as **strings** (`"450.00"`), never as floating point.
- **A7** `409` (delete blocked: category, brand, attribute, attribute value in use) shows the server message and offers **Deactivate**.
- **A8** Every list screen has loading, empty and error states; every submit button is disabled while the request runs (no double submit).
- **A9** Media / picture URLs are resolved with `resolveMediaUrl` (on a local server they are `/media/...`).

## 3. Lists, search, filters, pagination

- **L1** Limit/offset lists: `limit` (default 20, max 100) and `offset`; response `{count, next, previous, results}`; filters reset the offset.
- **L2** **Cursor lists** (admin pending products `/catalog/listings/requests/`, pending gigs `/catalog/gigs/requests/`): follow `next` / `previous` exactly,
  **no `count`**, no page numbers, a "Load more" pattern, cursor reset when a filter or `ordering` changes; default order newest request first
  (`requested_at`), `ordering` options `requested_at`, `created_at`, `title`, `id` (`-` reverses).
- **L3** Admin product filters: `status`, `catalog_type`, `listing_type`, `category`, `brand`, `seller`, `buyer`, `created_from/to`, `requested_from/to`
  (`YYYY-MM-DD`, inclusive), `search` (title, Bangla title, brand name, model, SKU code).
- **L4** Admin gig filters: `status`, `category`, `seller`, **`price_type`** (gigs with an active package priced that way), the date filters, `search`
  (title, Bangla title, SKU code).
- **L5** Seller product filters: `status`, `listing_type`, `category`, `brand`, dates, `search`, `ordering` (`created_at`, `updated_at`, `requested_at`, `title`,
  `status`, `id`; default newest first). Seller gig filters: `status`, `category`, `price_type`, dates, `search`, `ordering`.
- **L6** List rows show the **thumbnail** (`image_url`, a placeholder when `null`), title (+ Bangla title), status badge, price ("from" price; for a gig the lowest
  rate **with its price type**, e.g. "৳450 / hour"; `fixed` = flat price), and for a seller the rejection `note`.
- **L7** Status filter values: `draft`, `pending`, `approved`, `rejected`, `changes_requested`, each with a distinct badge.

## 4. Product form (admin and seller)

- **P1** Required: `category`, `title`, `description`, and **at least one SKU** (full `skus` list, or the create shortcut `price` for one default SKU; never both).
- **P2** Category dropdown: only **active** categories of type **product**; tree from `GET /catalog/categories/tree/?type=product` (seller: `/seller/lookups/categories/?type=product`).
- **P3** `listing_type` (`general`, `used`, `village`, `retail`, `wholesale`, `brand`). **`brand` is required when `listing_type = brand`**; brand dropdown shows only
  **active** brands (seller: `/seller/lookups/brands/`). A brand listing without a brand is blocked client-side and mapped from the server `400`.
- **P4** `measurement` optional (seller: `/seller/lookups/measurements/`). `min_order_qty` integer ≥ 1. `condition_note` (used products). `attributes` free JSON specs.
  `model`, `origin`, `warranty`, `currency` (default `BDT`).
- **P5** Bangla fields next to the English ones: `title_bn`, `description_bn`, `origin_bn`, `warranty_bn`, `condition_note_bn` (five; **no** `package_includes_bn`
  on a product). All optional.
- **P6** **No service-only fields** on a product (`delivery_days`, `urgent`, `package_includes*`, `available_from`, `available_to`): they are `400`.
- **P7** Location: country → state → city → thana cascade; each dropdown loaded from the level above; any level may be empty; mismatches map to
  `{"city": ["This city does not belong to the selected state."]}`.
- **P8** Title: one live title per seller **per kind** (case and extra spaces ignored). Map `{"title": ["... (listing #123)"]}` to the title field (seller message
  starts "You already have a listing with this title"; admin message "This seller already has ..."). A product and a gig may share a title.
- **P9** **SKUs (product)**: `sku` code unique across the system; `price` ≥ 0 (required for a new SKU); `discounted_price` ≤ `price` (empty = price);
  `discount_start_date` / `discount_end_date` (end after start; a window needs a lower discounted price); `stock_qty` ≥ 0 (empty = not tracked; `0` = sold out);
  `is_active` toggle. Show read-only `effective_price` and whether the discount is active now.
- **P10** **Options (variants)**: pick active attributes and values (`GET /catalog/attributes/?is_active=true`; seller `/seller/lookups/attributes/`), generate every
  combination as rows; **one value per attribute per SKU**; **every SKU of a listing uses the same attributes**; **no two SKUs with the same combination** (hidden
  SKUs count); the value must belong to its attribute; only active attributes/values can be newly chosen; a listing with more than one SKU needs options on each.
- **P11** SKUs are **never deleted**: hide with `{"id": n, "is_active": false}` (greyed in the admin, with a note that they cannot be deleted); show again with
  `true`. On **edit** send only changed SKUs **with their `id`**; an item without `id` adds a SKU; SKUs not sent are untouched; `variants`, when sent, replaces
  that SKU's options.
- **P12** Top-level `price` / `stock_qty` / `sku` on an **update** are refused (`400`): the form sends prices and stock only through `skus` on edit.
- **P13** **Quantity prices** (`price_tiers`, products only): `min_qty` ≥ 1, `max_qty` ≥ `min_qty` (empty = "and above"), **no overlap**, only the **last** tier may be
  open-ended, each tier has `price` and an optional `discounted_price` (≤ price); the list is **replaced as a whole** when sent (`[]` clears; omit to keep).
- **P14** Create with JSON when SKUs / tiers are used (multipart cannot carry nested lists); gallery files go in a separate multipart `PATCH` (`media_file`,
  `media_delete_ids`).
- **P15** Edit form sends **only what changed** (PATCH). `listing_type` / `catalog_type` rules and brand rule re-checked on edit.

## 5. Gig form (admin and seller)

- **G1** Required: service `category` (active service category only), `title`, `description`, and **at least one package** (SKU).
- **G2** Optional: `title_bn`, `description_bn`, `delivery_days` (≥ 0), `urgent`, `package_includes` (+ `_bn`), `available_from` / `available_to`, location, `currency`,
  gallery. Admin only: optional `seller` (owner; none allowed), `status`, `note`.
- **G3** **No product fields** on a gig: no brand, model, origin, warranty, measurement, condition note, `listing_type`, `attributes`, `min_order_qty`, quantity prices,
  stock, options. They are `400` (`{"brand": "Not available here."}`).
- **G4** **Packages editor**: one row per package: **price type** (`hourly`, `daily`, `weekly`, `monthly`, `fixed`) required; **price = the rate** for that unit (≥ 0)
  required; optional discount (+ dates); optional `description` / `description_bn` (**gigs only**); optional SKU code; active toggle. Show the unit on the price
  ("per hour", "per day", "per week", "per month", "fixed price").
- **G5** **One package per price type** (also enforced by the database): the editor blocks a price type already used, **including hidden saved packages**
  (offer "Show it again"); the Add button is disabled when all five are used; the server error `{"skus": ["Every gig SKU needs its own price type ..."]}` is
  shown in the packages section.
- **G6** Packages are **never deleted**, only hidden (`is_active: false`); on edit send changed rows with `id`, new rows without `id` (needs `price` + `price_type`).
- **G7** **No `duration` and no stock / options inputs** on a package. A SKU never carries `duration` (the buyer picks it when ordering; not built).
- **G8** Gig `price` / `discounted_price` and the list `price_type` are read only: the lowest rate among active packages and what it is for.
- **G9** Title rule per kind (see P8). `catalog_type` / `posted_by_role` not sent / not editable.

## 6. Thumbnail (products and gigs, admin and seller)

- **T1** Not part of create or edit. Own endpoints: `PUT` (multipart, one field `image`) and `DELETE` on `/catalog/listings/{id}/thumbnail/`,
  `/catalog/gigs/{id}/thumbnail/`, `/seller/listings/{id}/thumbnail/`, `/seller/gigs/{id}/thumbnail/`.
- **T2** JPG / PNG / WEBP only, **≤ 10 MB**, a real image (client-side check **and** mapping of `400 {"image": [...]}`; the current thumbnail stays on a refused upload).
- **T3** Create flow: `POST` the listing (JSON) first, then `PUT` the thumbnail with the new id; a failed upload leaves the listing created, the user stays on the
  edit page and can retry (no rollback). The control is enabled after the first save.
- **T4** Replace (the server deletes the old file), Remove (confirmation; `204`, also when none), preview from `image_url` or a placeholder; list / detail state
  refreshed after each action. Never set `Content-Type` manually (`FormData`).
- **T5** Seller side: a thumbnail change on a **rejected / changes-requested** listing sends it back to **pending** (like saving it): the UI warns before upload
  and refreshes the status after. On approved / pending the status stays. Admin changes never change the status.
- **T6** Thumbnail changes appear in the admin **change log** (`thumbnail`).

## 7. Gallery media (products and gigs)

- **M1** `media_file` (repeat per file) in a multipart `PATCH` after the JSON save; `media_delete_ids` to remove (the server deletes the file).
- **M2** **Seller limits**: JPG, PNG, WEBP, GIF, MP4, PDF; **10 MB** each; at most **10 per request**; at most **20 per listing** (client-side checks + mapped
  `{"media_file": [...]}` errors). Admin has no such limits.
- **M3** Media type (image / video / document) is detected by the server; render images inline, video with a player, documents as links.

## 8. Admin moderation (products and gigs, each on its own endpoints)

- **D1** Statuses: `draft`, `pending`, `approved`, `rejected`, `changes_requested`. **`rejected` and `changes_requested` require a note** (block client-side; map
  `{"note": ["A note is required ..."]}`). A note is only read when the status really changes (re-sending the same status does nothing).
- **D2** Detail page: **approve**, **reject**, **request changes** (note dialog), set pending; shows the current `note` (the reason) and the full **status history**
  (newest first: status, note, who `creator_name` + `creator_type`, when).
- **D3** **Bulk moderate** from the lists: select rows → `POST .../bulk-moderate/` `{listing_ids, status, note}` with status only `approved`, `rejected`,
  `changes_requested` (note required for the last two); show `updated` and `skipped`; the gig endpoint only touches gigs, the listing endpoint products/jobs.
- **D4** **Pending lists** (cursor): a listing a seller fixed after a rejection returns to the **top**; the menu badge refreshes (K7).
- **D5** **Info change log** (admin only) on the detail: every content change with `changed_fields`, `previous_data`, `new_data`, who, when (SKU changes as whole
  lists incl. `price_type` / description for gigs, `price_tiers`, `media`, `thumbnail`, text and Bangla fields, category, brand, owner, location; **stock is not logged**).
- **D6** Admin create: default status **approved** (can choose `pending`, or a rejected status with a note); owner `seller` optional (none allowed); never both seller
  and buyer.
- **D7** Admin delete is a **soft delete** (`204`, then `404`), with a confirmation; admins can edit any listing/gig.
- **D8** Admin can change the owner on edit (logged); the same-title rule applies to the new owner.

## 9. Seller rules (listings and gigs)

- **S1** A seller's new listing/gig is **always `pending`**, owned by them. The form has **no** owner, buyer, `posted_by_role`, `status` or `requested_at` inputs (they are
  ignored by the server). After saving show "Waiting for review".
- **S2** A seller sees and edits **only their own** non-deleted listings; other ids are `404`.
- **S3** **No delete** (`DELETE` is `405`): no delete button for sellers. Sellers can hide SKUs/packages.
- **S4** Saving behaviour (show it to the user): **pending** stays pending; **approved stays approved whatever changes** (content, SKUs, prices, stock) and is logged for
  the admin; **rejected / changes_requested (and an admin-made draft)** goes back to **pending** on **any save**, even an empty one. There is **no Resubmit button**:
  "Save and resubmit" on a rejected listing.
- **S5** On a rejected / changes-requested listing show the admin's **reason (`note`)** prominently and the **status history** (status, note, `creator_type`
  seller/admin, date; **not** which admin). An optional **message to the reviewer** (`note`) may be sent with that save; in any other state the note is ignored (hide the field).
- **S6** The seller does **not** see the info change log. The seller's `status`, `note`, `requested_at` are read only.
- **S7** Lookups only return **active** items: `/seller/lookups/categories/` (`type`, `parent`, `search`), `/brands/`, `/measurements/`, `/attributes/` (with active values);
  limit default 500 (max 1000).
- **S8** Seller title messages, `403` messages ("not approved yet" / "inactive") and `404`s are shown as friendly screens.
- **S9** Seller list shows the status, the rejection reason, the thumbnail and the dates; filters/search/ordering per L5.

## 10. Reference-data screens that listings depend on (regression check)

- **R1** Categories (one tree for product and service; type and parent rules; delete blocked with `409` when used), Brands (`is_active`, `409` on delete when used),
  Measurements, Attributes and values (`409` when a SKU uses them; deactivate instead; value's attribute cannot change; Bangla names optional) still work after the change.
- **R2** Admin forms only offer active items for new selections, but still **display** an already attached inactive category / brand / value without blocking edits.

## 11. Things that must NOT exist (negative checks)

- **N1** No input or request field named `price_type` / `hourly_rate` on a listing, no `duration` on a SKU, no `total_price`.
- **N2** No service option in the Listings form; no product option in the Gigs form; no create-job form; no orders / cart / hiring / bidding screens.
- **N3** No client-side invented endpoints; no direct DB access; no secrets in the repo.
- **N4** No delete button for sellers; no status / owner inputs for sellers.

---

## 12. Test matrix (Phase 3, browser, with `docs/test-accounts.md`; password `Test@12345`)

Run the backend: `cd /Users/ghl/Github/egoola/egoola-server && uv run manage.py runserver 8000` (check that `uv`, `.env` and a local database exist; if not, create a
throwaway local database and run `uv run manage.py migrate`, then seed the accounts and ids from `test-accounts.md`; never touch other databases). Needed ids:
product category 18, service category 29, measurement 13, Bangladesh 126 / Chittagong 13 / Feni 8. Create a verified+active seller from the admin panel for the seller cases.

| # | Case | Expected |
|---|---|---|
| 1 | Admin: create product with options (2 sizes × 2 colours), tiers, thumbnail | created `approved`; 4 SKUs; thumbnail in list and detail |
| 2 | Admin: product with `listing_type = brand`, no brand | blocked / `400` on `brand` |
| 3 | Admin: edit a SKU price only | only that SKU sent with `id`; change log has `skus` |
| 4 | Admin: hide a SKU, then show it | stays in the list, greyed; no delete |
| 5 | Admin: overlapping price tiers | error on `price_tiers` |
| 6 | Admin: create gig with hourly + weekly + fixed packages and an owner | created `approved`, 3 packages, no stock/options inputs |
| 7 | Admin: add a second `hourly` package (and a hidden one) | blocked in the UI; server error mapped if sent |
| 8 | Admin: gig with a product-only field via a crafted request | `400` mapped, no crash |
| 9 | Admin: gig id opened on the product URL, product id on the gig URL | "not found" |
| 10 | Admin: thumbnail upload (jpg), replace, remove; a `.txt`; an 11 MB file | 200 / replace / 204 / `400` / `400` |
| 11 | Admin: pending products and pending gigs lists | cursor "Load more", badges correct |
| 12 | Admin: reject without note / with note / request changes / approve | blocked / ok / ok / ok; history rows |
| 13 | Admin: bulk approve 3 gigs, bulk reject without note | updated list / blocked |
| 14 | Admin: soft delete a gig | `204`, gone from lists, detail `404` |
| 15 | Seller (verified+active): create product | `pending`, no owner/status inputs, "Waiting for review" |
| 16 | Seller: same title again | title error with the existing listing id |
| 17 | Seller: upload > 10 files / > 10 MB / an .exe | blocked + mapped errors |
| 18 | Admin rejects it with a reason; seller opens it | reason + history shown, no admin name |
| 19 | Seller saves the rejected listing | becomes `pending`, back at the top of the admin pending list |
| 20 | Seller changes the thumbnail of a rejected listing | warning first; becomes `pending` |
| 21 | Admin approves; seller edits it | stays `approved`; admin change log shows the edit |
| 22 | Seller: delete | no button (`405` if forced) |
| 23 | Seller with status `inactive` / `pending` / `rejected` / `suspended` | listing screens unreachable, correct message / login refused |
| 24 | Seller: another seller's listing id | "not found" |
| 25 | Expired access token | one refresh, retry, new refresh stored; refresh failure → login |
| 26 | Pagination: 25+ listings | limit/offset works; filters reset offset |
| 27 | `npm run ci` | lint + typecheck + build pass |

If a case cannot run (no backend), say so explicitly; never mark it Pass.
