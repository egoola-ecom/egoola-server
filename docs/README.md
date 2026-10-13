# Egoola Backend — Documentation Index

**The one place to find any backend document, Postman collection or smoke test.** For each feature it shows where its
overview, its technical guide, its Postman collection, its smoke test and its database design are.

Paths: guides are in this folder (`egoola-server/docs/`). Postman collections are in `../postman/`. Smoke tests are in
`../scripts/smoke/`. Project documents that belong to the other repo are in `egoola-document/` (a sibling of `egoola-server`).

> **Keep this file up to date.** Whenever you add a guide, a Postman collection or a smoke test, add or change its row
> here in the same commit. This is the only index.

---

## 1. Start here, by role

| You are | Read first |
|---|---|
| **Operations / support / product** (not technical) | [`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md) (the whole seller process) and [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) (listings, for admins and sellers), both in simple words |
| **Frontend web or Flutter app developer** | [`frontend-api-guide.md`](frontend-api-guide.md) (login, tokens, errors, pagination, filters), then the feature rows below |
| **Backend developer** | [`../README.md`](../README.md), [`authentication.md`](authentication.md), then the feature rows below |
| **Tester** | [`../scripts/smoke/README.md`](../scripts/smoke/README.md) and the "Smoke test" column below |
| **Anyone asking "what is done?"** | `egoola-document/Egoola_Phase_Tracker.md` |

---

## 2. Set up once (Postman)

1. Start the server: `uv run manage.py runserver 8000`.
2. In Postman, import `postman/Egoola-Local.postman_environment.json` and pick it as the active environment
   (`base_url` = `http://127.0.0.1:8000`).
3. Import the collections you need (section 4). Each one has an **Auth** or **Setup** folder; run it first and the token is saved for you.
4. Logins to use: [`test-accounts.md`](test-accounts.md) (password `Test@12345`). Use the **super-admin** for Admin Management,
   a plain admin for the rest. Admins and buyers log in with email; **sellers log in with phone number**.

Notes:
- The Listing and Attribute collections leave a few demo rows behind after a run (soft-deleted listings keep their SKUs).
- The CMS collection's site-logo delete step removes the logo.
- Requests with a file row (banner image, site logo, seller documents, listing media) have no file selected, because file paths
  are not portable. Pick a real JPG / PNG / PDF in Postman before sending.

---

## 3. Features: where each one is documented

Columns: **Overview** is plain language for everyone. **Technical guide** has what to send, what comes back and every error.
**Postman** is a collection in `postman/`. **Smoke test** is a script in `scripts/smoke/`. **Database** is the table(s) in
`egoola-document/database/Egolola DB Re-Design.docx`.

### 3.1 Accounts and login

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| Login, tokens, errors, pagination, filters (all actors) | — | [`frontend-api-guide.md`](frontend-api-guide.md), [`authentication.md`](authentication.md) | `Egoola` → **Auth** | `e2e_smoke.sh` | `admins`, `sellers`, `users (buyer)` |
| Test accounts and reference ids for testing | — | [`test-accounts.md`](test-accounts.md) | — | — | — |
| Admin management (super-admin only) | — | [`admin-management-guide.md`](admin-management-guide.md) | `Egoola` → **Auth → Super-Admin Login**, **Accounts → Admins** | `admin_smoke.sh` | `admins`, `adminMedia` |
| Buyer management (admin) | — | [`buyer-management-guide.md`](buyer-management-guide.md) | `Egoola` → **Accounts → Buyers** | `buyer_smoke.sh` | `users (buyer)`, `buyerMedia` |

### 3.2 Sellers

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| **Seller process, everything** (sign-up, verification, login, what sellers and admins can do) | **[`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md)** | — | — | — | — |
| **Seller-facing APIs**: public location lists, sign-up with KYC documents, seller login (phone + password), own profile (`/seller/me`), documents, change password, resubmit after rejection | [`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md) | [`seller-api-guide.md`](seller-api-guide.md) | **`Egoola-SellerApp`** | `seller_self_smoke.sh`, `seller_onboarding_smoke.sh` (sign-up part), `public_geography_smoke.sh` | `sellers`, `sellerMedia`, `sellerInfos` |
| **Seller management by admins**: seller list and filters, Seller Request queue, review, approve / reject / pause / suspend, review history, profile change history | [`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md) | [`seller-verification-guide.md`](seller-verification-guide.md), [`frontend-api-guide.md`](frontend-api-guide.md) §8 | **`Egoola-Seller`** | `seller_onboarding_smoke.sh` (queue part), `e2e_smoke.sh` | `sellers`, `sellerVerificationLogs`, `sellerProfileChangeLogs` |

### 3.3 Reference data

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| Geography management (country, state, city, thana), admin | — | [`geography-api-guide.md`](geography-api-guide.md) | `Egoola-Geography` | none of its own; `e2e_smoke.sh` checks the location rules | `countries`, `states`, `cities`, `thanas` |
| **Public geography lists** (no login; for the sign-up form) | [`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md) §3.1 | [`seller-api-guide.md`](seller-api-guide.md) §2 | `Egoola-SellerApp` → **Public lookups** | `public_geography_smoke.sh` | same four tables |
| Categories (one tree for products and services) | — | [`category-tree-api-guide.md`](category-tree-api-guide.md) | `Egoola-Category` | `listing_smoke.sh` (regression), `sku_smoke.py` (delete protection) | `categories` |
| Measurements (units) | — | [`listing-module-guide.md`](listing-module-guide.md) (how listings use them) | `Egoola-Measurement` | `listing_smoke.sh` (regression only) | `measurements` |

### 3.4 Listings

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| **Listings, everything in plain words** (admin and seller: statuses, who can do what, the same-title rule, the pending list, change history) | **[`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md)** | — | — | — | — |
| **Listings, start here (technical)**: how a listing relates to categories, brands, attributes, SKUs, owners and locations; how to create every kind; the seller's part (section 13) | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) | [`listing-complete-guide.md`](listing-complete-guide.md) | `Egoola-Listing`, `Egoola-Attribute` | `listing_smoke.sh`, `sku_smoke.py` | `listings`, `listingPriceTiers`, `listingMedia` |
| **Seller listings**: create, list, see and edit my listings (every kind through one endpoint), the lookups for the form, Bangla fields | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) | [`seller-api-guide.md`](seller-api-guide.md) section 6 | **`Egoola-SellerApp`** → **Seller listings** | `seller_listing_smoke.sh` | `listings`, `listingStatusChangeLogs`, `listingInfoChangeLogs` |
| Listing endpoints and **moderation** (approve / reject / request changes, bulk, history), the **pending list** (cursor), the info change log | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) | [`listing-module-guide.md`](listing-module-guide.md) (section 9 = what the seller feature added) | `Egoola-Listing` | `listing_smoke.sh`, `seller_listing_smoke.sh`, `e2e_smoke.sh` | `listings`, `listingStatusChangeLogs`, `listingInfoChangeLogs` |
| Brands | — | [`listing-module-guide.md`](listing-module-guide.md) | `Egoola-Listing` | `brand_smoke.sh` | `brands` |
| Attributes, attribute values and listing SKUs (sizes, colours, own price / discount / stock) | — | [`attribute-sku-guide.md`](attribute-sku-guide.md) | `Egoola-Attribute` | `sku_smoke.py` | `attributes`, `attributeValues`, `listingSkus`, `listingSkuVariants` |

### 3.5 Content

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| CMS: banners, email templates, site settings, site logo | — | [`cms-api-guide.md`](cms-api-guide.md) | `Egoola-CMS` | `cms_smoke.sh` | `banners`, `emailTemplates`, `settings` |

### 3.6 Not built yet (no document, no API)

- Admin dashboard data (counts, charts, recent activity).
- Financial oversight: withdrawal requests, refunds, commission settings.
- Freelance gigs and bids, seller orders, wallet and withdrawals (Phase 3, next rows).
- Everything for buyers beyond account management (browsing, cart, checkout, orders, messages, reviews: Phase 4).
- Email / phone code checks (OTP), notifications to sellers, forgot password.

Status of each: `egoola-document/Egoola_Phase_Tracker.md`.

---

## 4. Postman collections: what each one covers

All are in `postman/`. Import `Egoola-Local.postman_environment.json` first.

| Collection | Side | Covers |
|---|---|---|
| `Egoola.postman_collection.json` | Admin | Auth for every actor, Admins, Sellers (basic), Buyers |
| `Egoola-Seller.postman_collection.json` | Admin | Seller management, Seller Request queue, review, approve / reject / pause / suspend, change history |
| `Egoola-SellerApp.postman_collection.json` | **Seller-facing** | Public lookups, sign-up, seller login, own profile, documents, change password, resubmit, **listings and the listing lookups**. (Requests named **[Admin step]** play the admin so you can see what a seller sees.) |
| `Egoola-Geography.postman_collection.json` | Admin | Country, state, city, thana |
| `Egoola-Category.postman_collection.json` | Admin | Category tree |
| `Egoola-Measurement.postman_collection.json` | Admin | Measurements |
| `Egoola-Listing.postman_collection.json` | Admin | Listings (Bangla fields, pending list, status and info history), brands, moderation |
| `Egoola-Attribute.postman_collection.json` | Admin | Attributes, values, listing SKUs |
| `Egoola-CMS.postman_collection.json` | Admin | Banners, email templates, settings, site logo |
| `openapi.json` | — | **Old snapshot. Do not use.** |

---

## 5. Smoke tests: what each script checks

Start the server, then run `scripts/smoke/run_all.sh` for everything, or one script by name. Current check counts:
[`../scripts/smoke/README.md`](../scripts/smoke/README.md). The scripts create their own temporary data and remove it when they finish.

| Script (`scripts/smoke/`) | Checks |
|---|---|
| `e2e_smoke.sh` | Seller approval, listing moderation, buyer management, a second admin, banner update, plus the shared rules (notes, location, passwords) |
| `admin_smoke.sh` | Admin management |
| `buyer_smoke.sh` | Buyer management |
| `listing_smoke.sh` | Listings: CRUD, moderation, price tiers, media, soft delete, bulk |
| `brand_smoke.sh` | Brands and their rules |
| `sku_smoke.py` | Attributes, values, SKUs, category delete protection |
| `cms_smoke.sh` | Banners, email templates, settings, logo |
| `seller_onboarding_smoke.sh` | Seller sign-up with documents and the admin Seller Request queue |
| `seller_self_smoke.sh` | The seller's own API, phone login, profile change log, files removed from storage |
| `public_geography_smoke.sh` | Public location lists |
| `seller_listing_smoke.sh` | The seller listing API and lookups, the same-title rule, the pending list, approve / reject / fix, the info change log, Bangla fields, file limits, files removed from storage |

Web screen tests (frontend repo): `egoola-web/docs/admin-smoke-tests.md`.

---

## 6. Other documents

| Document | Where | What it is |
|---|---|---|
| Backend set-up | [`../README.md`](../README.md) | Run the backend locally |
| Frontend work brief | [`frontend-handoff-prompt.md`](frontend-handoff-prompt.md) | Tasks and rules for the web session |
| Knowledge Brief, Phase Tracker, Rebuild Guideline, DB Re-Design, migration documents | `egoola-document/` (sibling repo; it has its own README and rules) | Platform overview, task status, architecture, the new database, data migration |
| Team rules | `CLAUDE.md` in the root and in each repo | How the five sessions work together |

---

## 7. Rules every form needs to respect

- Passwords: at least 8 characters, not a very common password, not all digits.
- A seller logs in with **phone number + password** (not email). Seller `status` is `active`, `inactive` or `suspended`:
  `inactive` sellers can log in but only edit their own profile; `suspended` sellers cannot log in. Failed logins are `401`.
- Location: state must belong to the country, city to the state, thana to the city (any level may be left out).
- A rejection or change request on a seller or listing needs a note.
- Prices, discounts and stock are on **SKUs**, not on the listing. Every listing has at least one SKU; hide a SKU with `is_active: false` (SKUs are never deleted).
- Lists are paginated with `?limit=` / `?offset=` (default 20, max 100). The exception is the Seller Request queue, which uses **cursor** pagination (follow `next` / `previous`, no `count`).

---

## 8. Which file do I update? (for people who maintain the docs)

| You changed | Update |
|---|---|
| A seller rule or flow | `Egoola_Seller_Guide.md` (plain words) **and** the matching technical guide, Postman collection and smoke test |
| A listing rule or flow | `Egoola_Listing_Guide.md` (plain words) **and** `listing-complete-guide.md`, `listing-module-guide.md` / `seller-api-guide.md`, the Postman collection and smoke test |
| An API endpoint | The feature's technical guide, its Postman collection, its smoke test |
| A table or column | `egoola-document/database/Egolola DB Re-Design.docx` (the table's section) |
| Added a guide, collection or script | This file |
