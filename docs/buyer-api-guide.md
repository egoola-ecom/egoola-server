# Buyer API Guide — sign-up and login (the buyer-facing APIs)

For the buyer web, the buyer app and anything a buyer does **before** they have a token. Browsing needs no login at all: see [`public-api-guide.md`](public-api-guide.md).
What an admin does with buyers (list, edit, suspend) is in [`buyer-management-guide.md`](buyer-management-guide.md).

---

## Table of contents

- [1. Sign up — `POST /api/v1/auth/buyer/register/`](#1-sign-up-post-apiv1authbuyerregister)
- [2. Log in — `POST /api/v1/auth/buyer/login/`](#2-log-in-post-apiv1authbuyerlogin)
- [3. Cart — `/api/v1/buyer/cart/...`](#3-cart-apiv1buyercart)
  - [Add to cart — `POST /buyer/cart/items/`](#add-to-cart-post-buyercartitems)
  - [The cart — `GET /buyer/cart/?type=product`](#the-cart-get-buyercarttypeproduct)
  - [Edit / remove a line](#edit-remove-a-line)
  - [Clearing — `DELETE /buyer/cart/?type=product[&seller=]`](#clearing-delete-buyercarttypeproductseller)
- [4. Wishlist (favourites) — `/api/v1/buyer/favourites/...`](#4-wishlist-favourites-apiv1buyerfavourites)
  - [Save — `POST /buyer/favourites/`](#save-post-buyerfavourites)
  - [List — `GET /buyer/favourites/?type=product`](#list-get-buyerfavouritestypeproduct)
  - [Remove — `DELETE /buyer/favourites/{listing_id}/`](#remove-delete-buyerfavouriteslisting_id)
- [5. Jobs — post work and hire — `/api/v1/buyer/jobs/...`](#5-jobs-post-work-and-hire-apiv1buyerjobs)
  - [Status moves](#status-moves)
  - [Accepting a bid](#accepting-a-bid)
- [6. Not built yet](#6-not-built-yet)

---

## 1. Sign up — `POST /api/v1/auth/buyer/register/`

Public: no token needed (a token sent by mistake is ignored). Send **JSON**, or **`multipart/form-data`** when a profile picture is included.

**Only three things are required: `name`, `phone` (the mobile number) and `password`. Everything else is optional.**

| Field | Required | Notes |
|---|---|---|
| `name` | **yes** | Not blank |
| `phone` | **yes** | The buyer's mobile number, **and their login**. Digits only, 6 to 15 of them, may start with `+` (for example `+8801711000111` or `01711000111`). Spaces and hyphens are removed (`+880 1711-000111` is saved as `+8801711000111`). Must be new |
| `password` | **yes** | At least 8 characters, not a very common password, not all digits |
| `email` | no | Must be new if given (upper and lower case count as the same email). Empty or left out = no email. Two buyers may both have none |
| `profile_pic` | no | One image file (needs multipart) |
| `description` | no | About the buyer |
| `address_line` | no | Street address |
| `country`, `state`, `city`, `thana` | no | Ids from the public lists ([`public-api-guide.md`](public-api-guide.md) section 2). Each level must belong to the one above (state in country, city in state, thana in city). Any level can be left out |
| `skills`, `experiences`, `interests`, `educations` | no | Free-form lists (JSON) |

Not accepted (ignored if sent): `status`, `wallet_balance`, `email_verified_at`, `phone_verified_at`. A new buyer is always `active`, with an empty wallet.

```json
POST /api/v1/auth/buyer/register/
{ "name": "Mahin Rahman", "phone": "+8801711000111", "password": "Buy@12345" }
```

**Success `201`.** The account is active at once, so the response **already logs the buyer in** (no second call needed):

```json
{ "access": "eyJhbGciOiJIUzI1NiIs...", "refresh": "eyJhbGciOiJIUzI1NiIs...", "actor_type": "user",
  "id": 14, "name": "Mahin Rahman", "phone": "+8801711000111", "email": null,
  "profile_pic_url": null, "description": null, "address_line": null,
  "country": null, "state": null, "city": null, "thana": null,
  "skills": null, "experiences": null, "interests": null, "educations": null,
  "status": "active", "message": "Welcome to Egoola. Your account is ready." }
```

Save `access` (1 hour) and `refresh` (14 days) as after a login: see `frontend-api-guide.md` sections 3 and 4. The password is never returned.

**With a picture and more details (multipart):**

```
POST /api/v1/auth/buyer/register/        (multipart/form-data)
name: Mahin Rahman
phone: +8801711000111
password: Buy@12345
email: mahin@example.com
country: 126
state: 13
profile_pic: <me.png>
```

**Errors `400`** (`{"field": ["message"]}`, the same shape everywhere):

| Problem | Key | Message |
|---|---|---|
| a required field is missing or blank | the field | `This field is required.` |
| not a valid mobile number | `phone` | `Enter a valid mobile number (digits only, may start with +).` |
| phone already used (spaces ignored) | `phone` | `buyer with this phone already exists.` |
| email already used (case ignored) | `email` | `buyer with this email already exists.` |
| not an email | `email` | `Enter a valid email address.` |
| weak password | `password` | `This password is too short...` (a list) |
| state not in the country, city not in the state, thana not in the city | `state` / `city` / `thana` | `This city does not belong to the selected state.` |
| not a real image | `profile_pic` | |

A failed sign-up saves nothing: no buyer row and no uploaded file are left behind.

## 2. Log in — `POST /api/v1/auth/buyer/login/`

Send **exactly one** of `phone` or `email`, with `password`:

```json
{ "phone": "+8801711000111", "password": "Buy@12345" }
{ "email": "mahin@example.com", "password": "Buy@12345" }
```

- The phone is matched after spaces and hyphens are removed, so the buyer can type it the way they like. It must be the number given at sign-up.
- `email` only works for a buyer who gave an email. A buyer without one logs in with the phone.
- Both, or neither, is `400 {"phone": ["Send either phone or email (one of them)."]}`.
- Wrong password, or an unknown phone or email: `401 {"detail": "Invalid phone number, email or password."}` (one message for both, so nobody can find out which numbers are registered).
- A suspended buyer: `401 {"detail": "This account is not active."}`.

`200`:

```json
{ "access": "...", "refresh": "...", "actor_type": "user", "id": 14, "name": "Mahin Rahman",
  "email": null, "phone": "+8801711000111" }
```

`email` is `null` for a buyer who has none. Tokens, refresh and error shapes: `frontend-api-guide.md` sections 3 and 4.

## 3. Cart — `/api/v1/buyer/cart/...`

Needs a buyer token (`Authorization: Bearer <access>`). A buyer has at most **one active cart per (type, seller)** —
`product` or `service`, **and** never spanning two sellers — created automatically the first time something of that
type and seller is added. Adding a listing picks the matching cart by the **listing's own type and seller**, not
something the buyer states, so none of it can ever mismatch: a product checks out through Stripe, a service/gig
through bKash (routes 3 and 4, not built yet), and every order will always be exactly one seller.

A buyer can have several active carts of the same type at once (one per seller). **`GET`/`DELETE` act on exactly
one of them**, never several at a time: pass `&seller=<id>` to name it (`0` for the shared no-seller cart), or leave
it out to mean *whichever active cart of that type was touched most recently* — the one the buyer's "my cart" icon
or page should show by default on landing. Neither call ever creates a cart; with nothing there, `GET` returns
`null` and `DELETE` is a no-op `204`.

A cart is **never reused**. Once it becomes an order (a later step), it closes — the row and everything in it stay
exactly as that order's record — and the buyer's next add of that type and seller opens a fresh cart.

| Route | What |
|---|---|
| `GET /buyer/cart/summary/` | one row per active cart (every type, every seller) — for a header badge or "all carts" view |
| `GET /buyer/cart/?type=product\|service[&seller=]` | that seller's cart, or the most recently touched one if `seller` is left out — `null` if none |
| `POST /buyer/cart/items/` | add a listing + SKU |
| `PATCH /buyer/cart/items/{id}/` | change the quantity (product) or duration (gig) of one line |
| `DELETE /buyer/cart/items/{id}/` | remove one line |
| `DELETE /buyer/cart/?type=product\|service[&seller=]` | empty that same cart (same lookup as `GET`) — no-op if there is none |

### Cart summary — `GET /buyer/cart/summary/`

The one call that sees *every* active cart at once — everything else in this section acts on exactly one. For a
header cart-icon badge (the true total, across every seller and type) and for a real "all carts" page, linking each
row to `GET /buyer/cart/?type=<cart_type>&seller=<id>`.

```json
{ "item_count": 2,
  "carts": [
    { "id": 192, "cart_type": "product", "seller": {"id": 550, "name": "Karim Electric", "profile_pic_url": null},
      "item_count": 1, "subtotal": "4300.00", "updated_at": "..." },
    { "id": 191, "cart_type": "product", "seller": {"id": 553, "name": "Sylhet Books", "profile_pic_url": null},
      "item_count": 1, "subtotal": "300.00", "updated_at": "..." } ] }
```

Newest-touched first. `item_count` (per cart, and the top-level grand total) is the **number of lines**, not a sum
of `qty`/`duration` — a product's quantity and a gig's duration aren't the same unit, so they can't be added
together meaningfully; counting lines is the one thing that's comparable across a product cart and a service cart
both. `seller: null` is the shared no-seller cart (admin-owned listings). Never creates a cart — an empty result
is `{"item_count": 0, "carts": []}`, not an error.

### Add to cart — `POST /buyer/cart/items/`

```json
{ "listing": 103, "listing_sku": 113, "qty": 2 }
```

| Field | Product | Gig |
|---|---|---|
| `listing`, `listing_sku` | required — the exact SKU, not just the listing | same |
| `qty` | required, at least 1 | not accepted |
| `duration` | not accepted | required, at least 1 (hours/days/weeks/months, matching the SKU's `price_type`) |

The listing must be one a buyer can already see (same rule as browsing — approved, seller verified and active); anything else is `400 {"listing": ["Invalid pk \"...\" - object does not exist."]}`, same as an unknown id. A `listing_sku` that belongs to a different listing is `400 {"listing_sku": ["Does not belong to this listing."]}`. For a product, stock is checked (`stock_qty - reserved_qty` against `qty`) — no stock is reserved yet, this only blocks adding more than is available right now.

**Adding the same SKU again merges into the existing line** instead of creating a second one — `qty` (or `duration`) adds up. `201`:

```json
{ "id": 1, "listing": { "id": 103, "title": "Cotton T-Shirt", "title_bn": "...", "slug": "cotton-t-shirt",
  "image_url": null, "catalog_type": "product" },
  "listing_sku": { "id": 113, "sku": "TEE-001", "price": "100.00", "discounted_price": "100.00",
  "price_type": null, "is_active": true },
  "qty": 2, "duration": null, "color": null, "size": null,
  "unit_price": "100.00", "line_subtotal": "200.00", "available": true, "created_at": "..." }
```

`unit_price` / `line_subtotal` are worked out live (the discounted price while a discount runs) — never stored, since nothing is final until checkout. `available` turns `false` if the SKU has since gone inactive, the listing is no longer approved, or stock can no longer cover `qty`; the line is kept either way, only flagged.

### The cart — `GET /buyer/cart/?type=product`

```json
{ "id": 1, "cart_type": "product", "seller": { "id": 211, "name": "Rafiq Ahmed", "profile_pic_url": null },
  "is_active": true, "items": [ { "...": "as above" } ], "subtotal": "200.00",
  "created_at": "...", "updated_at": "..." }
```

`?type=` is required (`400` if missing or not `product`/`service`). `seller: null` is the shared cart for admin-owned
listings. With no `&seller=`, this is the active cart of that type the buyer most recently did anything with (added
to, edited, or removed a line from) — use this for a general "my cart" view. Add `&seller=<id>` (or `0`) to look up
one specific seller's cart instead — the call you'd make from a product or gig's own page, to show whether *that*
seller's cart already has something in it. A buyer with no cart of that type (or none with that seller) gets back
`null`, `200` — not a `404`, and nothing is created by asking.

### Edit / remove a line

`PATCH /buyer/cart/items/{id}/` replaces the quantity or duration (it does not add to it, unlike `POST`): `{"qty": 1}`. Sending the wrong field for that line's kind (`duration` on a product line, `qty` on a gig line) is `400`. `DELETE /buyer/cart/items/{id}/` removes it — `204`. Both are scoped to the logged-in buyer's own cart: another buyer's item id is `404`, same as if it didn't exist.

### Clearing — `DELETE /buyer/cart/?type=product[&seller=]`

Same lookup as `GET` — with `seller`, that seller's cart; without it, the most recently touched one. Empties every
line in it; the cart row stays active — `204`, even if there was nothing to clear.

## 4. Wishlist (favourites) — `/api/v1/buyer/favourites/...`

Needs a buyer token. Saving a listing to look at later — no quantity, no duration, no checkout implication, just a
bookmark. Unlike the cart, **it is a plain, idempotent toggle**: saving something already saved changes nothing, and
removing something that was never saved (or already removed) is not an error.

| Route | What |
|---|---|
| `GET /buyer/favourites/?type=product\|service` (`type` optional) | the buyer's saved listings, newest first, with a running count |
| `POST /buyer/favourites/` | save a listing |
| `DELETE /buyer/favourites/{listing_id}/` | un-save, keyed by the **listing's own id** (not the favourite row's) |

### Save — `POST /buyer/favourites/`

```json
{ "listing": 103 }
```

Same visibility rule as the cart and browsing — an invisible/unknown listing is `400 {"listing": [...]}`. Saving an
already-saved listing returns the **existing** row, `200` (not `201`, and not a second row).

`201`/`200`:

```json
{ "id": 1, "catalog_type": "product",
  "listing": { "id": 103, "title": "Cotton T-Shirt", "...": "same row shape as GET /public/catalog/products/" },
  "created_at": "..." }
```

`listing` is the exact same row shape a buyer already sees while browsing (`public-api-guide.md` sections 4–5) — a
product gets the product shape, a gig the gig shape; `catalog_type` on the favourite itself tells you which one
without inspecting the shape. Nothing about price is frozen here either — it is worked out live, the same as
everywhere else.

### List — `GET /buyer/favourites/?type=product`

Page-based paging, same convention as every other Buyer Panel list (`public-api-guide.md` section 1):
`{count, page, page_size, total_pages, results}`. `type` is optional — leave it out for both kinds together.

**A favourite survives its listing going private** (the seller turned inactive, the listing was rejected, and so on)
— it is not deleted, it simply drops out of this list, and comes back on its own the moment the listing is public
again. Same behavior as the cart's `available` flag and public browsing's visibility rule, just applied by hiding the
row entirely rather than flagging it (there is nothing to "buy later" from a hidden favourite, unlike a cart line).

### Remove — `DELETE /buyer/favourites/{listing_id}/`

Always `204`, whether or not it was actually saved — a toggle button on the frontend never needs to check first.
Scoped to the logged-in buyer's own favourites (nothing to leak either way, since the response carries no detail).

## 5. Jobs — post work and hire — `/api/v1/buyer/jobs/...`

Needs a buyer token. A job is a request for work that sellers **bid** on, instead of something bought outright.
It skips moderation entirely — it's `open_for_bidding` the instant it's created. Full reference (the complete
state machine, the seller and admin sides, every error case):
[`listing-complete-guide.md`](listing-complete-guide.md) section 16.

| Route | What |
|---|---|
| `POST /buyer/jobs/` | post a job — category, title, description and at least one budget option (`skus`) |
| `GET /buyer/jobs/` | my jobs (page-based paging) |
| `GET /buyer/jobs/{id}/` | detail, including `accepted_bid` once one is accepted |
| `PATCH /buyer/jobs/{id}/` | edit, or move `status` (pause/reopen/cancel) |
| `GET /buyer/jobs/{id}/bids/` | every bid placed on it, any status |
| `POST /buyer/jobs/{id}/bids/{bid_id}/accept/` | hire that bidder |

```json
POST /buyer/jobs/
{ "category": 29, "title": "Need a plumber", "description": "Leaking pipe under the basin.",
  "skus": [ { "price_type": "fixed", "price": "1500" } ] }
```

`category`, `title`, `description` and at least one budget option (`skus`) are required — no budget is
`{"skus": ["A job needs at least one budget option."]}`. The category must be an active **service** category.

### Status moves

| From | To | How |
|---|---|---|
| `open_for_bidding` | `draft` (pause), `cancelled` | `PATCH {"status": "draft"}` / `{"status": "cancelled"}` |
| `draft` | `pending` | `PATCH {"status": "pending"}` (not straight back to `open_for_bidding` — `400`) |
| `pending` | `open_for_bidding` (reopen) | `PATCH {"status": "open_for_bidding"}` |
| `in_progress` | `completed` | `PATCH {"status": "completed"}` — the **only** field accepted here; anything else is `400` |

Cancelling takes every live bid down with it (pending **or** accepted) as `cancelled`; a buyer **cannot** cancel
an `in_progress` job themselves — only an admin can (with a mandatory reason).

### Accepting a bid

```json
POST /buyer/jobs/42/bids/7/accept/
{ "price_tier_id": 12 }
```
`price_tier_id` only needed when that bid quoted more than one price option. This creates an **Order directly**
(no cart, `status: "in_progress"`), auto-rejects the job's other pending bids, and moves the job to `in_progress`:

```json
{ "bid": { "id": 7, "status": "accepted", "accepted_price_tier": { "id": 12, "...": "..." }, "...": "..." },
  "order": { "id": 301, "status": "in_progress", "payable": "1300.00" } }
```

Marking the job `completed` afterwards carries the accepted bid and its Order to `completed` too.

## 6. Not built yet

- **OTP / phone and email verification.** `phone_verified_at` and `email_verified_at` stay empty for everyone; there is no code sent and no check.
- **Forgot / reset password** and **change password** for a buyer.
- **Rate limiting** on the public sign-up and login endpoints: put a limit in front of them before launch.
- **The buyer's own profile API** (view and edit my profile, add documents) and checkout for products/gigs (Stripe/bKash) — a job's Order is already created on bid acceptance (§5), just not paid for yet.

Tests: `scripts/smoke/buyer_register_smoke.py`, `scripts/smoke/buyer_cart_smoke.py`, `scripts/smoke/buyer_favourites_smoke.py`,
`scripts/smoke/buyer_job_smoke.py`, `scripts/smoke/bid_accept_smoke.py`.
Postman: `Egoola-BuyerApp` → **Buyer sign-up and login**, **Cart**, **Favourites**, **Jobs**.
