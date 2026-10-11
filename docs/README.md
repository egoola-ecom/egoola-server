# Admin panel API — where to find what

Start here if you are building the admin panel. Every screen below has one
guide (what to send, what comes back, every error) and one Postman collection
(import it and click through the calls).

## Set up once

1. Start the server: `uv run manage.py runserver 8000`.
2. In Postman, import `postman/Egoola-Local.postman_environment.json` and pick it
   as the active environment (`base_url` = `http://127.0.0.1:8000`).
3. Import the collections you need from the table below. Each one has its own
   **Auth** folder; run **Admin Login** first and the token is saved for you.
4. Logins to use: [`test-accounts.md`](test-accounts.md) (password `Test@12345`).
   Use the **super-admin** for Admin Management, a plain admin for the rest.

Read first: [`frontend-api-guide.md`](frontend-api-guide.md) (login, tokens,
errors, pagination, filters) and [`authentication.md`](authentication.md) (how
roles and the `401` / `403` split work).

## Screens that are ready

| Admin screen | Guide (`docs/`) | Postman collection (`postman/`) |
|---|---|---|
| Login, tokens, errors, pagination | `frontend-api-guide.md`, `authentication.md` | `Egoola.postman_collection.json` → **Auth** |
| Seller management + **seller verification** (approve / reject) | `seller-verification-guide.md`, `frontend-api-guide.md` §8 | `Egoola-Seller.postman_collection.json` |
| Buyer management | `buyer-management-guide.md` | `Egoola.postman_collection.json` → **Accounts → Buyers** |
| Admin management (super-admin only) | `admin-management-guide.md` | `Egoola.postman_collection.json` → **Auth → Super-Admin Login**, then **Accounts → Admins** |
| **Listings — start here**: how a listing relates to categories, brands, attributes, SKUs, owners and locations; how to create every kind of listing; moderation | `listing-complete-guide.md` | `Egoola-Listing.postman_collection.json`, `Egoola-Attribute.postman_collection.json` |
| Listings + **moderation** (approve / reject / request changes, bulk, history) and Brands — endpoint reference | `listing-module-guide.md` | `Egoola-Listing.postman_collection.json` |
| **Attributes, attribute values and listing SKUs** (sizes / colours with their own price, discount window and stock) | `attribute-sku-guide.md` (read this together with the listing guide) | `Egoola-Attribute.postman_collection.json` |
| CMS: banners, email templates, site settings, site logo | `cms-api-guide.md` | `Egoola-CMS.postman_collection.json` |
| Categories (tree) | `category-tree-api-guide.md` | `Egoola-Category.postman_collection.json` |
| Measurements (unit list: create, update, list, delete — no separate guide; same list/paginate rules as the others) | the Postman collection is the reference; how listings use it: `listing-module-guide.md` | `Egoola-Measurement.postman_collection.json` |
| Geography (country / state / city / thana) | `geography-api-guide.md` | `Egoola-Geography.postman_collection.json` |

Notes for the Postman collections:
- The Listing and Attribute collections leave a few demo rows behind after a run (soft-deleted listings keep their SKUs, so their attributes can only be deactivated). Run **CMS → Site Logo** requests only if you can afford to lose the logo: its delete step removes it.
- Requests that upload a file (banner image, site logo, seller documents,
  listing media) have no file selected, because file paths are not portable.
  Pick a file in the request body before sending.
- The Listing collection leaves soft-deleted demo listings and brands behind
  after every run; this is normal (the API cannot hard-delete them).
- `postman/openapi.json` is an old snapshot — do not use it.

## Not built yet (no API to call)

- **Admin dashboard data** (counts, charts, recent activity).
- **Financial oversight**: withdrawal requests, refunds, commission settings.

Both are open in the Phase Tracker.

## Rules every form needs to respect

- Passwords: at least 8 characters, not a very common password, not all digits.
- Location: state must belong to the country, city to the state, thana to the
  city (any level may be left out).
- A rejection or change request on a seller or listing needs a note.
- Prices, discounts and stock are on **SKUs**, not on the listing. Every listing has at least one SKU; hide a SKU with `is_active: false` (SKUs are never deleted).
- Lists are paginated with `?limit=` / `?offset=` (default 20, max 100).

## Checking the backend yourself

Curl-based smoke tests: `scripts/smoke/run_all.sh` (see `scripts/smoke/README.md`).
