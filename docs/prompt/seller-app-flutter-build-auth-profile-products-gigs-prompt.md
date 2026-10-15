# Brief for the Egoola Seller App session (Flutter) — build every seller feature the backend has shipped

## Features to build (the whole scope of this prompt)

Target app: **`egoola-seller`** (Flutter, the seller mobile app). Backend: `egoola-server`, already shipped. Build these, in this order:

1. **Foundation**: API client with token refresh, error mapper, secure session, theme, router with a status-based guard.
2. **Auth and sign-up**: seller login (phone + password), a sign-up wizard with cascading location dropdowns and KYC document upload, logout.
3. **Seller status and profile**: under-review, rejected (reason + resubmit) and paused screens; profile view and edit; business profile; documents (with the lock after verification); change password.
4. **Product listings**: lookups, list with filters, detail with status timeline, create, edit (SKUs, options, price tiers, Bangla fields), same-title handling.
5. **Thumbnail and gallery files** for products and gigs (add, replace, remove).
6. **Gigs**: list, detail, create and edit with price-type packages.

**Out of scope** (not built on the backend yet): OTP, push notifications, orders, hire requests, bidding, wallet and withdrawals, deleting a listing.

You are building the **Egoola Seller App** in `egoola-seller` (Flutter, Android + iOS). The project is only initialised (Phase 0: theme placeholder, Dio, secure
storage, router skeleton, empty feature folders). **Nothing else is built.** The backend (`egoola-server`, Django REST) already ships everything below; your job is to
build the screens and the API layer against it, exactly as the contract says. This file is your whole brief. Read it top to bottom before writing code.

Do not push to any remote. Commit locally only when asked. Do not change `egoola-server`; if the contract looks wrong or something is missing, stop and report it.

## 0. Read first (in this order)

1. This file.
2. `egoola-server/docs/seller-api-guide.md` — the seller API guide (sign-up, login, profile, products, gigs, files). **The source of truth.**
3. `egoola-server/docs/listing-complete-guide.md` sections 6, 13, 14, 15 (every listing field, the gig packages, files) and `egoola-server/docs/attribute-sku-guide.md` (options / SKUs).
4. `egoola-server/docs/frontend-api-guide.md` sections 1–5 (base URL, tokens, error shapes, pagination) and `egoola-server/docs/authentication.md`.
5. Plain-language guides for the product rules: `egoola-server/docs/Egoola_Seller_Guide.md` and `egoola-server/docs/Egoola_Listing_Guide.md`.
6. `egoola-seller/PHASES.md` (your own checklist) and `egoola-document/Egoola_Phase_Tracker.md` (Seller App rows). Update `PHASES.md` as work lands.
7. Test accounts: `egoola-server/docs/test-accounts.md`. Postman (use it to see real responses): `egoola-server/postman/Egoola-SellerApp.postman_collection.json` + `Egoola-Local.postman_environment.json`.

## 1. Stack and structure (already chosen — do not swap)

`flutter_riverpod`, `go_router`, `dio` + `retrofit` + `json_serializable`, `flutter_secure_storage`, `cached_network_image`. Feature-first layout that already exists:
`lib/core/{config,network,router,storage,theme}` and `lib/features/{auth,onboarding,profile,listings,...}/{data,domain,presentation}`.

- `AppConfig.apiBaseUrl` is `--dart-define=API_BASE_URL=...`, default `http://localhost:8000/api/v1`. Android emulator reaches the host at `http://10.0.2.2:8000/api/v1`;
  a physical phone needs the computer's LAN IP; Android debug builds need cleartext HTTP allowed (`usesCleartextTraffic` in the debug manifest). iOS may need an ATS exception for local HTTP.
- Every screen depends on a feature **repository** (abstract class + `Api...Repository`), never on Dio directly. Models are plain Dart + `json_serializable`. Money values are
  **strings** (`"450.00"`): keep them as `String` / `Decimal`-style, never `double`.
- Match the existing website's colours, fonts, button and card styles (`AppTheme` is a placeholder: apply a real seller palette). Layout may differ from the website. Support Bangla text
  (`title_bn`, `description_bn`, ...): use a font that renders Bangla.

## 2. API ground rules (the same everywhere)

- **Base URL** `…/api/v1/`. Everything needs `Authorization: Bearer <access>` except: the 3 login endpoints, `POST /auth/token/refresh/`, `POST /auth/seller/register/`, and `GET /public/geography/*`.
- **Tokens.** Login returns `access` (1 hour) and `refresh` (14 days). Refresh: `POST /auth/token/refresh/ {"refresh"}` → new `access` **and a new `refresh` (rotated: save both)**.
  In the Dio interceptor: on `401`, refresh **once** (serialise concurrent refreshes), retry the request; if the refresh also fails → clear storage → go to login. Do not refresh on the login call itself.
- **Errors.** `401` log out (except a wrong password at login: show the message). `403` = not allowed (a seller who cannot operate: show `detail`). `404` not found. `415` means you sent
  multipart to a JSON API (a bug). `400` is `{"field": ["message", ...]}`; some are nested (`{"skus": {"0": {"price_type": "..."}}}`) or a plain string (`{"price": "..."}`).
  Write **one** generic error mapper that turns any `400` into a `Map<String, List<String>>` (flatten nested keys to `skus[0].price_type`) and show messages under the matching field,
  plus a top banner for `detail` / unknown keys. Never show raw JSON.
- **Pagination.** limit/offset: `limit` (default 20, max 100; lookups default 500, max 1000), `offset`. Response `{count, next, previous, results}`. Use infinite scroll that follows `next`.
- **Files are multipart.** Use `FormData` and **never set `Content-Type` yourself**. For repeated keys use `form.fields.add(MapEntry(k, v))` / `form.files.add(MapEntry('media_file', file))`
  (do not rely on a Map for repeated keys). **Set each part's content type explicitly from the extension** (`image/jpeg`, `image/png`, `image/webp`, `image/gif`, `video/mp4`,
  `application/pdf`): the server rejects a file whose extension *or* content type is not allowed.
- **Media URLs** (`image_url`, `media_url`, `profile_pic_url`): in development they are paths like `/media/...` — prefix the **server origin** (base URL without `/api/v1`). If a value already starts
  with `http`, use it as is. In production they may be signed, short-lived links: never cache the URL itself, re-read it from the API.
- Dates are ISO 8601 with offset. Format for display with `intl`, in the device timezone.

## 3. The seller state machine (drives the whole navigation)

Two independent switches: `verification_status` (`unverified` | `pending` | `verified` | `rejected`) and `status` (`active` | `inactive` | `suspended`).
`can_operate = verification_status == verified && status == active`. Login returns `can_operate`; `GET /seller/me/` returns all three.

| State | Login | What the app shows |
|---|---|---|
| `unverified` / `pending` + `inactive` | yes | **Under review** screen + profile screens only |
| `rejected` + `inactive` | yes | **Rejected** screen: the reason (`verification_note`), fix profile / documents, **Resubmit** button |
| `verified` + `inactive` | yes | **Paused** screen: "An admin has to make your account active again" + profile only |
| `verified` + `active` | yes | the full app (listings, gigs) |
| `suspended` | **no** — `401 {"detail": "This account is not active."}` | back to login with that message |

The server re-reads the seller on **every request**: an approval, pause or suspension applies immediately. So: on app start and on resume, call `GET /seller/me/` and re-route. If any
seller-feature call returns `403`, re-fetch `/seller/me/` and route to the right status screen (do not just show a toast). A suspension shows up as `401`.

**Router guard** (go_router `redirect` driven by one `sellerSessionProvider`): no token → `/login`; token + cannot operate → status screens and `/profile/**` only; can operate → the main shell
(bottom navigation: **Listings**, **Gigs**, **Profile**). Show a splash while the session loads.

## 4. Screens and endpoints, feature by feature

### 4.1 Auth and sign-up (`features/auth`, `features/onboarding`)

- **Login** — `POST /auth/seller/login/ {"phone","password"}`. **Phone, not email**, exactly as registered. Response: `access, refresh, actor_type, id, name, email, phone, verification_status, status, can_operate`.
  `401 {"detail": "Invalid phone number or password."}` (also for an unknown phone). Store tokens in `SecureTokenStorage`.
- **Sign-up** (multi-step form, one `multipart` request at the end) — `POST /auth/seller/register/`:
  - Step 1 account: `name`, `email`, `phone` (**this is the login**), `password` (≥ 8, not common, not all digits; show a hint).
  - Step 2 address: `present_address`, `permanent_address`, `country` → `state` → `city` → optional `thana`: **cascading dropdowns** from `GET /public/geography/{countries,states,cities,thanas}/`
    (`states/?country=`, `cities/?state=`, `thanas/?city=`; an empty list is normal for thanas; each lookup returns the whole list, sorted by name).
  - Step 3 documents: `media_for` + `media_file` **in pairs, same order**. `media_for` ∈ `nid`, `birth_certificate`, `certificate`, `other`. **At least one `nid`** (offer "NID front" and "NID back").
    JPG, PNG, WEBP or PDF, **≤ 5 MB each**, ≤ 10 files. Pick from camera or gallery or files; check type and size on the device first.
  - Optional: `profile_pic` (one image) and `info` = the business profile as a **JSON string** (if sent, six fields are required: `business_type`, `main_product`, `owner_name`, `employees_range`,
    `annual_revenue`, `established_year`; optional `description`, `public_email`, `whatsapp`, `facebook`, `wechat`, `skype`, location ids). `business_type`, `employees_range`, `annual_revenue` are free text: you choose the options.
  - `201` returns **no token**: show a "thank you, we will review your documents" screen with a Login button. `400` field errors map back to the right step (jump to the step that owns the first error key).
    A rejected seller cannot register again (email / phone taken): they log in and resubmit.
- **Logout**: clear tokens and cached state. **Change password**: see 4.2.

### 4.2 Profile, documents, resubmit, password (`features/profile`) — works in **every** non-suspended state

- `GET /seller/me/` → fields: `id, name, email, phone, profile_pic_url, present_address, permanent_address, country, state, city, thana, skills, education, experience, interest, media[], business_info{…}, verification_status, verification_note, status, is_seller_request, can_operate, created_at, requested_at`.
- `PATCH /seller/me/` — JSON for text, **multipart** when a file is included. Send only changed fields. Editable: `name`, `profile_pic`, `present_address`, `permanent_address`, `country/state/city/thana`
  (must match each other), `skills/education/experience/interest` (free JSON lists), `info` (send the **whole** business object; read back as `business_info`), documents. **`email` and `phone` cannot change** (show them read-only; a different value is `400`).
  Status fields are read-only.
- **Documents** (`media_for` + `media_file` pairs; `media_delete_ids` to delete; replace = delete + upload **in the same request**). 5 MB, 10 per request. Rules to enforce in the UI as well as handle from the server:
  - Not approved yet (`unverified`/`pending`/`rejected`): NID and birth certificate can be added / deleted / replaced, **but one NID must always remain**.
  - `verified`: **NID and birth certificate are locked** (disable add / delete, show "Ask an admin to change this"); `certificate` and `other` stay editable.
  - A refused request keeps the old file. Server messages: map `media_for` / `media_file` errors under the documents list.
- **Status screens** (4.0): under review / rejected (reason from `verification_note`, then **Resubmit**) / paused. `POST /seller/me/resubmit/ {"note"?}` (note ≤ 1000 chars, a message to the reviewer) — only for `rejected`
  (else `400 {"detail": ...}`); returns the profile with `verification_status: pending`. Flow for a rejected seller: read the reason → edit profile / documents → Resubmit. Pull-to-refresh re-reads `/seller/me/`.
- **Change password** — `POST /seller/me/change-password/ {"current_password","new_password"}` → `200 {"detail": "Password changed."}`; `400` for a wrong current password (`Incorrect password.`) or a weak / reused new one. The token keeps working.
- Business profile is also where the seller shows public contact details (phone, WhatsApp, Facebook, WeChat, Skype).

### 4.3 Lookups for the listing forms (`features/listings/data`) — only for a seller who can operate

`GET /seller/lookups/categories/` (`type=product|service`, `parent`, `search`; rows `id,type,parent,name,name_bn,slug,sort_order` — a tree: build it from `parent`),
`/brands/` (`id,name,slug`), `/measurements/` (`id,name,slug,symbol`), `/attributes/` (`id,name,name_bn,values[{id,name,name_bn}]`). Only active items come back. Cache them per session.

### 4.4 Products (`/seller/listings/`) — the Listings tab

All of 4.4 and 4.5 need `can_operate`. A seller sees **only their own** products. **No delete** (`DELETE` is `405`): do not build a delete or hide button.

- **List** `GET /seller/listings/` — filters: `status` (`pending|approved|rejected|changes_requested|draft`), `listing_type`, `category`, `brand`, `created_from/to`, `requested_from/to` (`YYYY-MM-DD`), `search` (title, Bangla title, SKU, brand),
  `ordering` (`created_at|updated_at|requested_at|title|status|id`, `-` reverses; default newest first). Row: `id,title,title_bn,slug,catalog_type,listing_type,category,brand,image_url,price,discounted_price,status,note,requested_at,created_at,updated_at`.
  Show the thumbnail, title (+ Bangla), "from" price, a **status badge**, and the rejection `note`. Status filter chips. Pull-to-refresh, infinite scroll, empty state.
- **Detail** `GET /seller/listings/{id}/` — full listing: SKUs with options, `price_tiers`, `media`, `image_url`, `status`, `note`, and `status_change_logs` (`status, note, creator_type` = `seller`|`admin`, `created_at`; **not which admin**).
  Show the status timeline. The seller never gets the admin's info change log.
- **Create** `POST /seller/listings/` — **JSON only** (multipart is `415`). Always created `pending`. Required: `category` (an active **product** category), `title`, `description`, and **either `skus` or a `price`** (a shortcut for one default SKU).
  Fields: `listing_type` (`general|used|village|retail|wholesale|brand`; `brand` needs a `brand`), `title_bn`, `description_bn`, `brand`, `model`, `origin`/`origin_bn`, `warranty`/`warranty_bn`, `measurement`, `min_order_qty`,
  `condition_note`/`condition_note_bn`, `attributes` (free JSON specs), `country/state/city/thana`, `price_tiers` (`min_qty,max_qty,price,discounted_price`, no overlaps), and prices:
  - **Simple**: `price`, `discounted_price`, `discount_start_date`, `discount_end_date`, `stock_qty`, `sku` (create only).
  - **With options** (size / colour): `skus: [{sku, price, discounted_price, discount_start_date, discount_end_date, stock_qty, is_active, variants:[{attribute, attribute_value}]}]` — one SKU per combination, ids from the attributes lookup.
  Never send `seller`, `buyer`, `posted_by_role`, `status`, `requested_at` (ignored). `catalog_type` is always `product` (`service` is `400`: services are gigs).
  Build a form with sections (Basics, Bangla, Product details, Location, Price and stock, Quantity prices, Options). A discounted price must be below the price; a discount window needs both dates.
- **Edit** `PATCH /seller/listings/{id}/` — send only what changed. **Prices and stock change only through `skus`**: `{"skus":[{"id":593,"price":"550","stock_qty":99}]}` merges by id; an item without `id` adds a SKU; SKUs are **never deleted**, hide with
  `{"id":..,"is_active":false}`. A top-level `price` / `stock_qty` on edit is `400`. `price_tiers`, when sent, **replaces the whole list**. `status` can never be set by the seller.
- **What a save does to the status** (tell the seller before saving): `pending` stays pending; `approved` **stays approved** (the admin sees the change in a log); **`rejected` / `changes_requested` / `draft` go back to `pending`** with `requested_at` = now.
  **There is no Resubmit button for listings: saving is resubmitting**, even an empty save. On a rejected listing show the admin's reason (`note`) above the form and an optional "Message to the reviewer" field sent as `note` (it is ignored in any other state).
  After saving, re-read the response (`status`, `status_change_logs`).
- **Same-title rule**: a seller cannot have two live products with the same title (case / spaces ignored). `400 {"title": ["You already have a listing with this title. Update the existing listing instead. (listing #681)"]}` — parse the `#id` and offer an **Open that listing** action.

### 4.5 Gigs (`/seller/gigs/`) — the Gigs tab (a service the seller offers)

A gig is **not** a product: the same moderation and "saving is resubmitting", but **priced by packages** and with no options, no stock, no brand, no quantity prices, and no delete. Own list, own form.

- **List** `GET /seller/gigs/` — filters `status`, `category`, `price_type`, `created_*`, `requested_*`, `search`, `ordering`. Row: `id,title,title_bn,slug,category,price,discounted_price,price_type,image_url,status,note,requested_at,created_at,updated_at`.
  `price` is the **lowest** package rate and `price_type` says what it is for (per hour / day / week / month / fixed): show "from ৳500 / hour".
- **Detail** `GET /seller/gigs/{id}/` — packages, media, status history. A product id is `404`.
- **Create** `POST /seller/gigs/` — JSON. Required: `category` (an active **service** category, from `lookups/categories/?type=service`), `title`, `description`, and packages. Optional: `title_bn`, `description_bn`, `delivery_days`, `urgent`, `package_includes`/`_bn`,
  `available_from`, `available_to`, `country/state/city/thana`. `catalog_type` not needed. Always `pending`.
- **Packages** (the price model): `skus: [{price_type, price, discounted_price?, discount_start_date?, discount_end_date?, description?, description_bn?, sku?, is_active?}]`.
  - `price_type` is **required**: `hourly | daily | weekly | monthly | fixed`; `price` is the **rate for that unit** (the buyer will choose the duration when ordering — **there is no duration on a package**, do not build one).
  - **At most one package per price type** (also a hidden one holds its type): offer only the unused types in the "add package" picker; reactivate a hidden one instead of adding.
  - `stock_qty` and `variants` must not be sent (`400`). One-package shortcut on create: `price` + `price_type` on the gig itself (never together with `skus`; not accepted on update).
  - Edit packages with `PATCH {"skus":[{"id":212,"price":"550"}]}` (merge by id; an item without `id` adds a package and needs `price` and `price_type`; nothing is deleted; hide with `is_active:false`).
- Errors are keyed by position: `{"skus": {"0": {"price_type": "..."}}}` — your mapper must put it under package #1. Same-title rule per type (a product with the same title is fine).
- Status behaviour, the reviewer note and the "saving resubmits" warning are **identical to products** (4.4).

### 4.6 Thumbnail and gallery files (`/seller/listing-files/{id}/`) — for a product id **or** a gig id

Listing and gig create / edit are JSON only. Pictures and videos use two multipart calls. A files change **never changes the status** (a rejected listing stays rejected; only saving the listing resubmits it) — do not warn about status here.

- `POST /seller/listing-files/{id}/` — add. `thumbnail` (optional, one JPG/PNG/WEBP ≤ 10 MB, a real image; `400` if one already exists → use PATCH) and `media_file` (optional, repeat per file). An empty request is allowed (`201`).
- `PATCH /seller/listing-files/{id}/` — change; the parts are **independent**: `remove_thumbnail=true` removes it; a new `thumbnail` **always replaces** the old (no need for `remove_thumbnail`); `remove_media_ids` (`4,5` or repeated; ids must belong to the listing, else `400`) deletes gallery files;
  `media_file` adds gallery files. Removal and addition can be in one call (`200`). Nothing sent = `200`, no change.
- Response: `{image_path, image_url, media:[{id, media_type (image|video|document), media_path, media_url}], status}` — refresh the preview and gallery from it.
- Gallery limits for a seller: JPG, PNG, WEBP, GIF, MP4, PDF; **≤ 10 MB each, ≤ 10 per request, ≤ 20 per listing** (count the files already there; ones removed in the same call do not count). Errors: `{"thumbnail":[…]}`, `{"media_file":[…]}`, `{"remove_media_ids":[…]}`. **All or nothing**: on `400` nothing was saved.
- **Create flow**: `POST` the listing (JSON) → then `POST` the files with the new id. If the upload fails the listing already exists: stay on its edit screen, show the error, let the user retry. Never roll back.
- UI: a reusable **Files control** (thumbnail preview with Choose / Replace / Remove-with-confirm; gallery grid with per-file remove and Add; image inline, video with a player, PDF as a link) used on the product and gig edit screens. Show upload progress and allow cancel.

## 5. Build order (milestones — finish and test each before the next)

1. **Foundation**: `AppConfig`, Dio with the refresh interceptor, `SecureTokenStorage`, the generic error mapper, env switch, theme palette, `go_router` with the session guard and splash, shared widgets (loading, empty, error, status badge, money text, network image with the media-URL helper).
2. **Auth**: login, geography repository, sign-up wizard, "thank you" screen, logout. Test against the server.
3. **Seller status + profile**: `sellerSessionProvider`, the under-review / rejected / paused screens, profile view / edit, business profile, documents (with the locks), resubmit, change password.
4. **Lookups + Products**: lookups cache, list with filters, detail with timeline, create, edit, status warnings.
5. **Files control** and wire it into products.
6. **Gigs**: list, detail, create / edit with the packages editor, files control.
7. **Polish**: loading / empty / error states everywhere, Bangla rendering, pull-to-refresh, offline message on network errors, no `print`, `flutter analyze` clean, widget tests for the error mapper, the router guard, the state→screen mapping and the multipart builders.

## 6. Test accounts and the approval step

`docs/test-accounts.md`: seller phone `0100000002`, password `Test@12345` (it is `unverified` + `active`, so it cannot operate yet). To test listings and gigs the seller must be **verified + active**: an admin approves with
`PATCH /accounts/sellers/{id}/ {"verification_status":"verified","status":"active"}` (Postman collection `Egoola-SellerApp` → the **[Admin step]** requests do this; admin login `test.admin@egoola.com` / `Test@12345`). Use the same admin calls to reject
(`{"verification_status":"rejected","verification_note":"..."}`), pause (`{"status":"inactive"}`) and suspend a test seller, and to approve / reject a listing (`PATCH /catalog/listings/{id}/` or `/catalog/gigs/{id}/` with `{"status":"rejected","note":"..."}`) so you can see every state.

## 7. Verify on a device or emulator (record the result of each)

| # | Case | Expected |
|---|---|---|
| 1 | Sign up with 2 NID files, then log in | `201` thank-you; login lands on the under-review screen |
| 2 | Sign up with no NID / a `.txt` / a 6 MB file / a duplicate phone | field errors under the right step, nothing created |
| 3 | Wrong password; unknown phone | same message, no leak |
| 4 | Admin approves → app resumes | goes to the full app without re-login |
| 5 | Admin rejects with a reason → open the app | rejected screen shows the reason; fix + Resubmit → under review |
| 6 | Admin pauses an approved seller | paused screen; a listing call `403` re-routes |
| 7 | Admin suspends | `401` → login with the message |
| 8 | Verified seller edits NID | locked in the UI; a crafted attempt shows the server message |
| 9 | Delete the only NID (unverified) | blocked / `400` mapped |
| 10 | Create a simple product; one with sizes × colours (4 SKUs) and price tiers | `201`, `pending`, shown in the list |
| 11 | Same title twice | error with an "Open that listing" action |
| 12 | Edit price via `skus`; hide a SKU | merged by id; hidden SKU shown greyed |
| 13 | Admin rejects → seller reads the reason → saves (with a note) | back to `pending`, history has the new entries |
| 14 | Approved listing edited | stays `approved` |
| 15 | Add thumbnail + 2 gallery files; replace the thumbnail; remove one gallery file and add another in one save | previews / gallery update from the response; old files gone |
| 16 | A `.txt`, a fake `.png`, a file > 10 MB, 11 files at once, a 21st file | blocked on device and mapped when the server refuses; nothing saved |
| 17 | Upload files to a **rejected** listing | stays `rejected` |
| 18 | Create a gig with hourly + weekly + fixed packages; add a second `hourly` | second one blocked / error under package; hide and reactivate |
| 19 | Gig with `stock_qty` / `variants` (crafted) | `400` mapped, no crash |
| 20 | Another seller's id, a product id on a gig URL | `404` screen |
| 21 | Token expiry (set a 1-minute test token or delete the access token) | silent refresh, request retried; expired refresh → login |
| 22 | Airplane mode | clear offline message, no crash |

## 8. Not built on the backend yet — do NOT build screens for these

OTP / email / phone verification (no endpoint), changing email or phone, push notifications (FCM), deleting or hiding a listing, seller drafts, bulk upload, **orders, hire requests on a gig, bidding / the job board, wallet, commission and withdrawals**
(these come in the next phase, with the buyer side). The `bidding`, `orders`, `wallet`, `notifications` feature folders stay empty. If `PHASES.md` mentions them, mark them Postponed.

## 9. Rules for you

- Work in small steps; after each milestone run `flutter analyze` and `flutter test` and fix everything.
- Follow the contract literally. If a response differs from this brief or the docs, trust the running server, then **report the difference** instead of working around it silently.
- Never store tokens anywhere but `SecureTokenStorage`. Never log tokens, passwords or document images.
- No hard-coded strings that the server provides (error messages, status reasons): show the server's text.
- Do not push. Commit locally only when asked.

Report at the end of each milestone: what is built, which cases from section 7 pass, what differed from the docs, and what is blocked.
