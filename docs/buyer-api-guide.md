# Buyer API Guide — sign-up and login (the buyer-facing APIs)

For the buyer web, the buyer app and anything a buyer does **before** they have a token. Browsing needs no login at all: see [`public-api-guide.md`](public-api-guide.md).
What an admin does with buyers (list, edit, suspend) is in [`buyer-management-guide.md`](buyer-management-guide.md).

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

Needs a buyer token (`Authorization: Bearer <access>`). A buyer has at most **one active cart per type** — `product` or `service` — created automatically the first time something of that type is added. Adding a listing picks the matching cart by the **listing's own type**, not something the buyer states, so the two kinds can never mix: a product checks out through Stripe, a service/gig through bKash (routes 3 and 4, not built yet).

A cart is **never reused**. Once it becomes an order (a later step), it closes — the row and everything in it stay exactly as that order's record — and the buyer's next add of that type opens a fresh cart.

| Route | What |
|---|---|
| `GET /buyer/cart/?type=product\|service` | the active cart of that type, with its items and a running subtotal |
| `POST /buyer/cart/items/` | add a listing + SKU |
| `PATCH /buyer/cart/items/{id}/` | change the quantity (product) or duration (gig) of one line |
| `DELETE /buyer/cart/items/{id}/` | remove one line |
| `DELETE /buyer/cart/?type=product\|service` | empty the cart (it stays active) |

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
{ "id": 1, "cart_type": "product", "is_active": true,
  "items": [ { "...": "as above" } ], "subtotal": "200.00",
  "created_at": "...", "updated_at": "..." }
```

`?type=` is required (`400` if missing or not `product`/`service`). A buyer who has never added anything of that type still gets a valid, empty cart (it's created on this first touch).

### Edit / remove a line

`PATCH /buyer/cart/items/{id}/` replaces the quantity or duration (it does not add to it, unlike `POST`): `{"qty": 1}`. Sending the wrong field for that line's kind (`duration` on a product line, `qty` on a gig line) is `400`. `DELETE /buyer/cart/items/{id}/` removes it — `204`. Both are scoped to the logged-in buyer's own cart: another buyer's item id is `404`, same as if it didn't exist.

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

## 5. Not built yet

- **OTP / phone and email verification.** `phone_verified_at` and `email_verified_at` stay empty for everyone; there is no code sent and no check.
- **Forgot / reset password** and **change password** for a buyer.
- **Rate limiting** on the public sign-up and login endpoints: put a limit in front of them before launch.
- **The buyer's own profile API** (view and edit my profile, add documents) and checkout (Stripe/bKash): the next Buyer Panel steps.

Tests: `scripts/smoke/buyer_register_smoke.py`, `scripts/smoke/buyer_cart_smoke.py`, `scripts/smoke/buyer_favourites_smoke.py`.
Postman: `Egoola-BuyerApp` → **Buyer sign-up and login**, **Cart**, **Favourites**.
