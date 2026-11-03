# Egoola Backend — Documentation Index

**The one place to find any backend document, Postman collection or smoke test.** For each feature it shows where its
overview, its technical guide, its Postman collection, its smoke test and its database design are.

Paths: guides are in this folder (`egoola-server/docs/`). Postman collections are in `../postman/`. Smoke tests are in
`../scripts/smoke/`. Project documents that belong to the other repo are in `egoola-document/` (a sibling of `egoola-server`).

A technical guide written for one actor lives in that actor's own subfolder — `admin/`, `buyer/` or `seller/` — same
split as `prompt/admin/`, `prompt/buyer/`, `prompt/seller/`. A plain-language overview book (`Egoola_*_Guide.md`) or a
guide that's genuinely cross-cutting (`authentication.md`, `public-api-guide.md`, `frontend-api-guide.md`,
`attribute-sku-guide.md`, `listing-complete-guide.md`, `test-accounts.md`) stays directly in `docs/`.

> **Keep this file up to date.** Whenever you add a guide, a Postman collection or a smoke test, add or change its row
> here in the same commit. This is the only index.

---

## Table of contents

- [1. Start here, by role](#1-start-here-by-role)
- [2. Set up once (Postman)](#2-set-up-once-postman)
- [3. Features: where each one is documented](#3-features-where-each-one-is-documented)
  - [3.1 Accounts and login](#31-accounts-and-login)
  - [3.2 Sellers](#32-sellers)
  - [3.3 Reference data](#33-reference-data)
  - [3.4 Jobs & Bidding](#34-jobs-bidding)
  - [3.5 Orders, Payments & Addresses](#35-orders-payments--addresses)
  - [3.6 Listings](#36-listings)
  - [3.7 Content](#37-content)
  - [3.8 Not built yet (no document, no API)](#38-not-built-yet-no-document-no-api)
- [4. Postman collections: what each one covers](#4-postman-collections-what-each-one-covers)
- [5. Smoke tests: what each script checks](#5-smoke-tests-what-each-script-checks)
- [6. Other documents](#6-other-documents)
- [7. Rules every form needs to respect](#7-rules-every-form-needs-to-respect)
- [8. Which file do I update? (for people who maintain the docs)](#8-which-file-do-i-update-for-people-who-maintain-the-docs)

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
| Admin management (super-admin only) | — | [`admin/admin-management-guide.md`](admin/admin-management-guide.md) | `Egoola` → **Auth → Super-Admin Login**, **Accounts → Admins** | `admin_smoke.sh` | `admins`, `adminMedia` |
| Buyer management (admin) | — | [`admin/buyer-management-guide.md`](admin/buyer-management-guide.md) | `Egoola` → **Accounts → Buyers** | `buyer_smoke.sh` | `users (buyer)`, `buyerMedia` |

### 3.2 Sellers

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| **Seller process, everything** (sign-up, verification, login, what sellers and admins can do) | **[`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md)** | — | — | — | — |
| **Seller-facing APIs**: public location lists, sign-up with KYC documents, seller login (phone + password), own profile (`/seller/me`), documents, change password, resubmit after rejection | [`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md) | [`seller/seller-api-guide.md`](seller/seller-api-guide.md) | **`Egoola-SellerApp`** | `seller_self_smoke.sh`, `seller_onboarding_smoke.sh` (sign-up part), `public_geography_smoke.sh` | `sellers`, `sellerMedia`, `sellerInfos` |
| **Seller management by admins**: seller list and filters, Seller Request queue, review, approve / reject / pause / suspend, review history, profile change history | [`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md) | [`admin/seller-verification-guide.md`](admin/seller-verification-guide.md), [`frontend-api-guide.md`](frontend-api-guide.md) §8 | **`Egoola-Seller`** | `seller_onboarding_smoke.sh` (queue part), `e2e_smoke.sh` | `sellers`, `sellerVerificationLogs`, `sellerProfileChangeLogs` |

### 3.3 Reference data

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| Geography management (country, state, city, thana), admin | — | [`admin/geography-api-guide.md`](admin/geography-api-guide.md) | `Egoola-Geography` | none of its own; `e2e_smoke.sh` checks the location rules | `countries`, `states`, `cities`, `thanas` |
| **Public geography lists** (no login; for the sign-up form) | [`Egoola_Seller_Guide.md`](Egoola_Seller_Guide.md) §3.1 | [`seller/seller-api-guide.md`](seller/seller-api-guide.md) §2 | `Egoola-SellerApp` → **Public lookups** | `public_geography_smoke.sh` | same four tables |
| Categories (one tree for products and services) | — | [`admin/category-tree-api-guide.md`](admin/category-tree-api-guide.md) | `Egoola-Category` | `listing_smoke.sh` (regression), `sku_smoke.py` (delete protection) | `categories` |
| **Buyer browsing in plain words** (what a buyer sees: categories, products, gigs, the seller page, and which rules and filters apply) | [`Egoola_Buyer_Browsing_Guide.md`](Egoola_Buyer_Browsing_Guide.md) | [`public-api-guide.md`](public-api-guide.md) | `Egoola-BuyerApp` | `public_listing_smoke.py` | — |
| **Public routes** (no login: country / state / city / thana lists, the Buyer Panel category browse list, **products and gigs** (list, detail, filters), the **seller page**; page-based paging) | — | [`public-api-guide.md`](public-api-guide.md) | `Egoola-BuyerApp`, `Egoola-BuyerApp` | `public_listing_smoke.py`, `category_browse_smoke.py`, `public_geography_smoke.sh` | `categories`, `countries`, `states`, `cities`, `thanas` |
| **Buyer sign-up and login** (only name, mobile and password required; login by phone or email) | — | [`buyer/buyer-api-guide.md`](buyer/buyer-api-guide.md) | `Egoola-BuyerApp` → **Buyer sign-up and login** | `buyer_register_smoke.py` | `users` |
| **Buyer cart(s)** (one active cart per type AND seller — product/service, never mixing sellers, picked automatically by the listing; GET/DELETE always target one cart — a named seller, or whichever was touched most recently; add/merge, qty vs duration, PATCH) | [`Egoola_Cart_Guide.md`](Egoola_Cart_Guide.md) | [`buyer/buyer-api-guide.md`](buyer/buyer-api-guide.md) §3 | `Egoola-BuyerApp` → **Cart** | `buyer_cart_smoke.py` | `carts`, `cartItems` |
| **Buyer wishlist (favourites)** (idempotent save/un-save, products and gigs together, survives the listing going private without being deleted) | [`Egoola_Cart_Guide.md`](Egoola_Cart_Guide.md) | [`buyer/buyer-api-guide.md`](buyer/buyer-api-guide.md) §4 | `Egoola-BuyerApp` → **Favourites** | `buyer_favourites_smoke.py` | `favourites` |
| **Admin oversight of carts** (read-only, cursor-paged list + detail, every cart regardless of listing visibility) | — | [`admin/cart-wishlist-admin-guide.md`](admin/cart-wishlist-admin-guide.md) §1 | `Egoola` → **Carts & Wishlists (admin) → Carts** | `admin_cart_smoke.py` | `carts`, `cartItems` |
| **Admin oversight of wishlists** (read-only, cursor-paged list + detail, `listing_visible` filter) | — | [`admin/cart-wishlist-admin-guide.md`](admin/cart-wishlist-admin-guide.md) §2 | `Egoola` → **Carts & Wishlists (admin) → Favourites** | `admin_favourites_smoke.py` | `favourites` |
| Measurements (units) | — | [`admin/listing-module-guide.md`](admin/listing-module-guide.md) (how listings use them) | `Egoola-Measurement` | `listing_smoke.sh` (regression only) | `measurements` |

### 3.4 Jobs & Bidding

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| **A buyer's job request**: post, edit, pause/reopen/cancel, mandatory budget, browse bids, accept a bid (creates an Order directly, no cart) | **[`Egoola_Job_Guide.md`](Egoola_Job_Guide.md)** | [`buyer/buyer-api-guide.md`](buyer/buyer-api-guide.md) §5, [`listing-complete-guide.md`](listing-complete-guide.md) §16 | `Egoola-BuyerApp` → **Jobs** | `buyer_job_smoke.py`, `bid_accept_smoke.py` | `listings`, `bids`, `bidPriceTiers`, `orders`, `orderItems` |
| **Seller job board and bidding**: browse open jobs, jobs I've bid on (and `?won=true`), place/edit/cancel a bid (price-tier reconcile like a gig's packages) | **[`Egoola_Job_Guide.md`](Egoola_Job_Guide.md)** | [`seller/seller-api-guide.md`](seller/seller-api-guide.md) §6c, [`listing-complete-guide.md`](listing-complete-guide.md) §16 | `Egoola-SellerApp` → **Seller jobs & bidding** | `seller_job_smoke.py` | `bids`, `bidPriceTiers` |
| **Admin job + bid panel**: create/edit a job on any buyer's behalf, create/edit a bid on any seller's behalf, accept on the buyer's behalf, undo an already-accepted hire, the admin-only `in_progress → cancelled` move | **[`Egoola_Job_Guide.md`](Egoola_Job_Guide.md)** | [`admin/job-admin-guide.md`](admin/job-admin-guide.md) | `Egoola-Listing` → **Jobs**, `Egoola` → **Bidding** | `admin_job_bid_smoke.py` | `listings`, `bids`, `bidPriceTiers`, `orders` |

### 3.5 Orders, Payments & Addresses

The full story — status flow for both the order and its payment, the money math, every actor's view — is one
book: **[`Egoola_Order_Guide.md`](Egoola_Order_Guide.md)**. Read that first; the rows below are the technical
reference per actor.

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| **Buyer addresses**: a saved delivery address book, full CRUD, no pagination | [`Egoola_Order_Guide.md`](Egoola_Order_Guide.md) §5 | [`buyer/buyer-address-api-guide.md`](buyer/buyer-address-api-guide.md) | `Egoola-BuyerApp` → **Addresses** | `buyer_address_smoke.py` | `addresses` |
| **Buyer checkout and orders**: cart + address + payment gateway → order in one call; list (page-paginated), detail (items, address, payment, both histories); cancel via a generic status `PATCH` (the old dedicated `/cancel/` action is gone) | [`Egoola_Order_Guide.md`](Egoola_Order_Guide.md) §§4–5 | [`buyer/buyer-order-api-guide.md`](buyer/buyer-order-api-guide.md) | `Egoola-BuyerApp` → **Orders** | `buyer_order_smoke.py` | `orders`, `orderItems`, `addresses`, `payments`, `orderStatusChangeHistories`, `paymentStatusChangeHistories` |
| **Seller orders**: list (cursor-paginated, filterable), detail, move forward one step at a time (accept/reject/in_progress/shipped/delivered) — delivered flips the payment `due → paid` automatically | [`Egoola_Order_Guide.md`](Egoola_Order_Guide.md) §6 | [`seller/seller-order-api-guide.md`](seller/seller-order-api-guide.md) | `Egoola-SellerApp` → **Orders** | `seller_order_smoke.py` | `orders`, `orderItems`, `payments` |
| **Admin order oversight**: list/detail for every order, status override to **any** status at **any** time, no transition check | [`Egoola_Order_Guide.md`](Egoola_Order_Guide.md) §7 | [`admin/admin-order-api-guide.md`](admin/admin-order-api-guide.md) | `Egoola` → **Orders (admin)** | `admin_order_smoke.py` | `orders`, `orderItems`, `payments` |
| **Payment Gateways (admin)**: the ways a buyer can pay — list, create, rename (slug regenerates), toggle active, icon upload, delete; only Cash on Delivery is seeded today | [`Egoola_Order_Guide.md`](Egoola_Order_Guide.md) §3 | [`admin/admin-payment-gateway-api-guide.md`](admin/admin-payment-gateway-api-guide.md) | `Egoola` → **Payment Gateways (admin)** | `admin_payment_gateway_smoke.py` | `paymentGateways` |

### 3.6 Listings

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| **Listings, everything in plain words** (products and **gigs**: statuses, who can do what, the same-title rule, the pending list, change history, the thumbnail; gigs = section 12) | **[`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md)** | — | — | — | — |
| **Listings, start here (technical)**: how a product relates to categories, brands, attributes, SKUs, owners and locations; how to create every kind; the seller's part (section 13); **gigs** (section 14); the **thumbnail** (section 15) | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) | [`listing-complete-guide.md`](listing-complete-guide.md) | `Egoola-Listing`, `Egoola-Attribute` | `listing_smoke.sh`, `sku_smoke.py` | `listings`, `listingPriceTiers`, `listingMedia` |
| **Seller listings (products)**: create, list, see and edit my products (every product format through one endpoint), the lookups for the form, Bangla fields | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) | [`seller/seller-api-guide.md`](seller/seller-api-guide.md) section 6 | **`Egoola-SellerApp`** → **Seller listings** | `seller_listing_smoke.sh` | `listings`, `listingStatusChangeLogs`, `listingInfoChangeLogs` |
| **Gigs, admin**: create, update, list, details, delete, the pending gig list, bulk moderation; packages (one SKU per price type) | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) §12 | [`listing-complete-guide.md`](listing-complete-guide.md) section 14 | `Egoola-Listing` → **Gigs** | `gig_smoke.py` | `listings`, `listingSkus` |
| **Seller gigs**: create, list, see and edit my gigs | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) §12 | [`listing-complete-guide.md`](listing-complete-guide.md) section 14.5, [`seller/seller-api-guide.md`](seller/seller-api-guide.md) section 6b | **`Egoola-SellerApp`** → **Seller gigs** | `seller_gig_smoke.py` | `listings`, `listingSkus` |
| **Thumbnail and gallery files** of a product or a gig (4 multipart APIs: add / change, admin and seller; create and update stay JSON only) | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) §4.1, [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) §12 | [`listing-complete-guide.md`](listing-complete-guide.md) section 15 | `Egoola-Listing` → **Listing files**, `Egoola-SellerApp` → **Seller listing files** | `listing_files_smoke.py` | `listings` (`imagePath`, `imageUrl`) |
| Listing endpoints and **moderation** (approve / reject / request changes, bulk, history), the **pending list** (cursor), the info change log | [`Egoola_Listing_Guide.md`](Egoola_Listing_Guide.md) | [`admin/listing-module-guide.md`](admin/listing-module-guide.md) (section 9 = what the seller feature added, 9.5 = thumbnail and gigs) | `Egoola-Listing` | `listing_smoke.sh`, `seller_listing_smoke.sh`, `e2e_smoke.sh` | `listings`, `listingStatusChangeLogs`, `listingInfoChangeLogs` |
| Brands | — | [`admin/listing-module-guide.md`](admin/listing-module-guide.md) | `Egoola-Listing` | `brand_smoke.sh` | `brands` |
| Attributes, attribute values and listing SKUs (sizes, colours, own price / discount / stock; section 8 = gig SKUs) | — | [`attribute-sku-guide.md`](attribute-sku-guide.md) | `Egoola-Attribute` | `sku_smoke.py` | `attributes`, `attributeValues`, `listingSkus`, `listingSkuVariants` |

### 3.7 Content

| Feature | Overview | Technical guide | Postman | Smoke test | Database |
|---|---|---|---|---|---|
| CMS: banners, email templates, site settings, site logo | — | [`admin/cms-api-guide.md`](admin/cms-api-guide.md) | `Egoola-CMS` | `cms_smoke.sh` | `banners`, `emailTemplates`, `settings` |

### 3.8 Not built yet (no document, no API)

- Admin dashboard data (counts, charts, recent activity).
- Financial oversight: withdrawal requests, refunds, commission settings (a job's Order carries `commission_rate`
  / `commission_amount` as `null` until this exists).
- Hire requests on a gig (accept, decline, deliver — a direct gig hire, not the job/bidding flow below), seller
  orders, wallet and withdrawals (Phase 3, next rows). Gigs themselves (create, manage, price, thumbnail) are built.
- Any Payment Gateway besides Cash on Delivery (bKash, cards, ...) — the `Payment`/`PaymentGateway` schema already
  anticipates one (`store_amount`, `initiated`/`failed`/`partially_paid`), nothing is wired up yet.
- Coupons / order-level discounts, real delivery-cost pricing (both fields exist on `Order`, always `0` for now).
- A seller buying from another seller's shop (`Cart.buyer_type` sits unused, ready for it).
- Deliverables, messaging between buyer and seller, reviews/ratings.
- Email / phone code checks (OTP), notifications to sellers, forgot password.

Checkout for a product (cart → Order, Payment, both status histories) **is now built** — see §3.5. A job's
Order is still created directly on bid acceptance instead (§3.4), no cart involved either way.

Status of each: `egoola-document/Egoola_Phase_Tracker.md`.

---

## 4. Postman collections: what each one covers

All are in `postman/`, split into `admin/`, `buyer/`, `seller/` subfolders by which actor the collection is for —
same split as `docs/` and `docs/prompt/`. `Egoola-Local.postman_environment.json` and `openapi.json` stay directly
in `postman/` (shared across every collection). Import `Egoola-Local.postman_environment.json` first.

| Collection | Side | Covers |
|---|---|---|
| `admin/Egoola.postman_collection.json` | Admin | Auth for every actor, Admins, Sellers (basic), Buyers, read-only oversight of **carts and wishlists**, **Bidding** (create/edit a bid on a seller's behalf, accept, `reject` to undo a hire), **Payment Gateways** (full CRUD), **Orders** (every order, status override to any status at any time) |
| `admin/Egoola-Seller.postman_collection.json` | Admin | Seller management, Seller Request queue, review, approve / reject / pause / suspend, change history |
| `seller/Egoola-SellerApp.postman_collection.json` | **Seller-facing** | Public lookups, sign-up, seller login, own profile, documents, change password, resubmit, **product listings and the listing lookups**, **gigs**, thumbnails, **Seller jobs & bidding** (board, my bids, place/edit/cancel), **Orders** (list, detail, accept/reject/in_progress/shipped/delivered). (Requests named **[Admin step]** / **[Buyer step]** / **[Setup]** play another actor so you can see what a seller sees.) |
| `buyer/Egoola-BuyerApp.postman_collection.json` | **Buyer-facing** | Buyer sign-up and login, the public country / division / district / thana lists, category browse, products, gigs and the seller page (mostly no login), **Jobs** (post, edit, bids, accept — hire a seller), **Addresses** (full CRUD), **Orders** (checkout, list, detail, cancel). (Requests named **[Seller step]** / **[Admin step]** play another actor.) |
| `admin/Egoola-Geography.postman_collection.json` | Admin | Country, state, city, thana |
| `admin/Egoola-Category.postman_collection.json` | Admin | Category tree |
| `admin/Egoola-Measurement.postman_collection.json` | Admin | Measurements |
| `admin/Egoola-Listing.postman_collection.json` | Admin | Listings (products: Bangla fields, pending list, status and info history), brands, moderation, **Gigs** (create, update, list, details, delete, pending list, bulk moderation), **Jobs** (create on a buyer's behalf, the admin-only `in_progress → cancelled`), **Listing files** |
| `admin/Egoola-Attribute.postman_collection.json` | Admin | Attributes, values, listing SKUs |
| `admin/Egoola-CMS.postman_collection.json` | Admin | Banners, email templates, settings, site logo |
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
| `listing_smoke.sh` | Listings (products, job requests): CRUD, moderation, price tiers, media, soft delete, bulk |
| `gig_smoke.py` | Admin gigs: packages (price type), the rules, edit, list and filters, the pending gig list, bulk moderation, the product / gig / job separation |
| `seller_gig_smoke.py` | The seller gig API: always pending, the product / gig split, packages, the same-title rule per type, approve / reject / fix |
| `listing_files_smoke.py` | The 4 listing-files APIs (admin and seller, product and gig): add, replace, remove, gallery, limits, all-or-nothing, status rules, JSON-only create / update |
| `brand_smoke.sh` | Brands and their rules |
| `sku_smoke.py` | Attributes, values, SKUs, category delete protection |
| `cms_smoke.sh` | Banners, email templates, settings, logo |
| `seller_onboarding_smoke.sh` | Seller sign-up with documents and the admin Seller Request queue |
| `seller_self_smoke.sh` | The seller's own API, phone login, profile change log, files removed from storage |
| `public_geography_smoke.sh` | Public location lists |
| `seller_listing_smoke.sh` | The seller product API and lookups, the same-title rule, the pending list, approve / reject / fix, the info change log, Bangla fields, file limits, files removed from storage |
| `buyer_job_smoke.py` | A buyer's own job postings: mandatory budget, the full status state machine, the bids-on-my-job list, per-buyer scoping |
| `seller_job_smoke.py` | The seller job board and bidding: browse, bid, price-tier reconcile, cancel and re-bid, a closed job leaving the board |
| `bid_accept_smoke.py` | Accepting a bid and its cascades: Order created, rivals auto-rejected, job → `in_progress`, completing and cancelling carry the bid and Order with them |
| `admin_job_bid_smoke.py` | The admin job + bid panel: create on behalf of a buyer/seller, accept, undo a hire (`reject`), the admin-only `in_progress → cancelled` move |
| `admin_payment_gateway_smoke.py` | Payment Gateway admin CRUD: auto-slug (and its regeneration on rename), duplicate-name and missing-field validation, active filter, search, delete, the seeded Cash on Delivery row |
| `buyer_address_smoke.py` | A buyer's own saved addresses: full CRUD, no pagination, location-consistency validation, per-buyer scoping |
| `buyer_order_smoke.py` | Checkout (cart + address + gateway → order + items + payment + opening history rows), every checkout validation error, list/detail shape, the generic cancel `PATCH` (and that the old dedicated action is gone) |
| `seller_order_smoke.py` | The seller's own order lifecycle: accept/reject (reason required)/in_progress/shipped/delivered one step at a time, illegal-jump rejection, the payment auto-flip to `paid` on delivered, per-seller scoping |
| `admin_order_smoke.py` | Admin oversight: every filter, full detail, and the any-status-any-time override (including moving an order backwards) with no transition check |

Web screen tests (frontend repo): `egoola-web/docs/admin-smoke-tests.md`.

---

## 6. Other documents

| Document | Where | What it is |
|---|---|---|
| Backend set-up | [`../README.md`](../README.md) | Run the backend locally |
| Frontend work brief | [`frontend-handoff-prompt.md`](prompt/frontend-handoff-prompt.md) | Tasks and rules for the web session |
| Frontend brief: Listings / Gigs panels, packages, thumbnail | [`frontend-gigs-thumbnail-prompt.md`](prompt/frontend-gigs-thumbnail-prompt.md) | The complete prompt to hand to the web session for the gig change (Task H) |
| Frontend brief: listing files (thumbnail and gallery, 4 APIs; breaking change) | [`frontend-listing-files-prompt.md`](prompt/frontend-listing-files-prompt.md) | The complete prompt to hand to the web session for the files change |
| Seller App brief: every shipped seller feature for the Flutter app (sign-up, login, status gate, profile, products, gigs, files) | [`seller-app-flutter-build-auth-profile-products-gigs-prompt.md`](prompt/seller-app-flutter-build-auth-profile-products-gigs-prompt.md) | The complete prompt to hand to the seller app session |
| Frontend brief: admin Job & Bidding panel | [`prompt/admin/frontend-admin-job-bidding-prompt.md`](prompt/admin/frontend-admin-job-bidding-prompt.md) | The complete prompt for the Admin Web screens (job + bid CRUD on behalf, accept, reject, the admin-only cancel) |
| Frontend brief: buyer Jobs (post, manage, hire) | [`prompt/buyer/frontend-buyer-job-prompt.md`](prompt/buyer/frontend-buyer-job-prompt.md) | The complete prompt for the Buyer Web screens (post a job, bids, accept) |
| Frontend brief: public buyer browsing (categories, products, gigs, seller page) | [`prompt/buyer/frontend-buyer-browsing-prompt.md`](prompt/buyer/frontend-buyer-browsing-prompt.md) | The complete prompt for the Buyer Web browsing/search screens |
| Frontend brief: buyer cart and wishlist (per-seller carts) | [`prompt/buyer/frontend-buyer-cart-wishlist-prompt.md`](prompt/buyer/frontend-buyer-cart-wishlist-prompt.md) | The complete prompt for the Buyer Web cart/wishlist screens |
| Frontend brief: buyer login and self-registration | [`prompt/buyer/frontend-buyer-auth-prompt.md`](prompt/buyer/frontend-buyer-auth-prompt.md) | The complete prompt for the Buyer Web register/login screens and token handling |
| Seller App brief: Jobs & Bidding (board, my bids, place/edit/cancel) | [`prompt/seller/seller-app-flutter-jobs-bidding-prompt.md`](prompt/seller/seller-app-flutter-jobs-bidding-prompt.md) | The complete prompt to extend the seller app session with Jobs & Bidding |
| Frontend brief: admin Payment Gateways | [`prompt/admin/frontend-admin-payment-gateway-prompt.md`](prompt/admin/frontend-admin-payment-gateway-prompt.md) | The complete prompt for the Admin Web Payment Gateway CRUD screen |
| Frontend brief: admin Orders (any-status override) | [`prompt/admin/frontend-admin-order-prompt.md`](prompt/admin/frontend-admin-order-prompt.md) | The complete prompt for the Admin Web order oversight screens |
| Frontend brief: buyer Addresses | [`prompt/buyer/frontend-buyer-address-prompt.md`](prompt/buyer/frontend-buyer-address-prompt.md) | The complete prompt for the Buyer Web address-book screens |
| Frontend brief: buyer Orders (checkout through cancel) | [`prompt/buyer/frontend-buyer-order-prompt.md`](prompt/buyer/frontend-buyer-order-prompt.md) | The complete prompt for the Buyer Web checkout and order screens |
| Seller App brief: Orders (accept through delivered) | [`prompt/seller/seller-app-flutter-orders-prompt.md`](prompt/seller/seller-app-flutter-orders-prompt.md) | The complete prompt to extend the seller app session with Orders |
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
- **Product, gig and job are separate kinds with separate endpoints** (`/catalog/listings/` + `/seller/listings/`, `/catalog/gigs/` + `/seller/gigs/`, `/catalog/jobs/` + `/buyer/jobs/` + `/seller/jobs/`). A row of the other kind is `404`; `catalog_type` and `posted_by_role` cannot change after creation.
- **A job is hired through bidding, not bought outright**: sellers place bids (`/seller/jobs/{id}/bids/`), the buyer or an admin accepts one (`/buyer/jobs/{id}/bids/{id}/accept/` or `/bidding/bids/{id}/accept/`), which creates an `Order` directly (no cart) and auto-rejects the other pending bids. Full state machine: [`listing-complete-guide.md`](listing-complete-guide.md) section 16.
- **A gig is priced by packages**: one SKU per `price_type` (`hourly`, `daily`, `weekly`, `monthly`, `fixed`) (the rate); the buyer chooses the duration when ordering (it is kept on the order item, with `total`, `subtotal` and the order's `payable`). No options, stock, brand or quantity prices on a gig. The thumbnail is a separate `PUT` / `DELETE .../thumbnail/`.
- Lists are paginated with `?limit=` / `?offset=` (default 20, max 100). The exception is the Seller Request queue, which uses **cursor** pagination (follow `next` / `previous`, no `count`).
- **An order's status and its payment's status are two separate things.** A seller moves an order one step at a time (`pending → accepted/rejected → in_progress → shipped → delivered`); a buyer may cancel any time before `shipped`; admin can move either to any status at any time. Delivered is the one thing that moves the payment too — `due → paid`, automatically. Full flow: [`Egoola_Order_Guide.md`](Egoola_Order_Guide.md).
- **Every money field is Decimal, rounded to exactly 2 places** (half-up, never floor/ceil) — on `Order`, `OrderItem` and `Payment` alike.

---

## 8. Which file do I update? (for people who maintain the docs)

| You changed | Update |
|---|---|
| A seller rule or flow | `Egoola_Seller_Guide.md` (plain words) **and** the matching technical guide, Postman collection and smoke test |
| A listing rule or flow | `Egoola_Listing_Guide.md` (plain words) **and** `listing-complete-guide.md`, `admin/listing-module-guide.md` / `seller/seller-api-guide.md`, the Postman collection and smoke test |
| A gig or thumbnail rule or flow | `Egoola_Listing_Guide.md` §12 (plain words) **and** `listing-complete-guide.md` sections 14–15, `seller/seller-api-guide.md` section 6b, `attribute-sku-guide.md` section 8, the Postman collections and `gig_smoke.py` / `seller_gig_smoke.py` |
| A job or bidding rule or flow | [`listing-complete-guide.md`](listing-complete-guide.md) section 16 **and** `buyer/buyer-api-guide.md` §5 / `seller/seller-api-guide.md` §6c / [`admin/job-admin-guide.md`](admin/job-admin-guide.md), the Postman collections and `buyer_job_smoke.py` / `seller_job_smoke.py` / `bid_accept_smoke.py` / `admin_job_bid_smoke.py` |
| An API endpoint | The feature's technical guide, its Postman collection, its smoke test |
| A table or column | `egoola-document/database/Egolola DB Re-Design.docx` (the table's section) |
| Added a guide, collection or script | This file |
