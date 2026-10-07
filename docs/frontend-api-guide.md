# Frontend API Guide — Accounts & Auth

This is what's built so far, written for whoever is wiring up the frontend.
Everything in this file was tested against the running server before being
written down — the example responses are real, not made up.

Also in this repo:
- **[Egoola.postman_collection.json](Egoola.postman_collection.json)** +
  **[Egoola-Local.postman_environment.json](Egoola-Local.postman_environment.json)**
  — import both into Postman and you can call every endpoint below without
  typing anything by hand. Logging in auto-saves the token for you.
- **[openapi.json](openapi.json)** — the exact, always-up-to-date machine
  schema (field names, types, required/optional). If this guide and that
  file ever disagree, trust `openapi.json` — it's generated straight from
  the code, this file is hand-written and can go stale.
- **[authentication.md](authentication.md)** — a deeper explanation of *how*
  the login/token/permission system works internally, if you're curious.
  This guide only covers *how to call it*.
- **[geography-api-guide.md](geography-api-guide.md)** — Country/State/City/
  Thana reference-data management (Admin-only), documented separately since
  it's a different kind of resource from accounts.

---

## 1. Base URL

```
http://127.0.0.1:8000/api/v1/
```

Every path below is relative to that. Swap the host for whatever
environment you're pointed at (staging/production URLs aren't decided yet).

---

## 2. The one rule that matters: everything needs a token, unless it's login

Every endpoint requires a valid token **except** the three login endpoints.
There is no "public browsing" of accounts data — an Admin, Seller, or Buyer
must be logged in for literally everything else in this guide.

---

## 3. Logging in

There are three separate login endpoints — one per actor type. They all
work the same way and return the same shape.

| Actor  | Endpoint |
|---|---|
| Admin  | `POST /api/v1/auth/admin/login/` |
| Seller | `POST /api/v1/auth/seller/login/` |
| Buyer  | `POST /api/v1/auth/buyer/login/` |

**Request body** (same for all three):
```json
{
  "email": "test.admin@egoola.com",
  "password": "Test@12345"
}
```

**Success response — `200`:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "actor_type": "admin",
  "id": 10,
  "name": "Test Admin",
  "email": "test.admin@egoola.com"
}
```

**Wrong email/password — `401`:**
```json
{ "detail": "Invalid email or password." }
```

**What to do with the response:** save `access` and `refresh` somewhere
(localStorage, a cookie, wherever your app keeps this). Don't bother
decoding or reading anything out of the token yourselves — `actor_type`,
`id`, `name`, `email` are already handed to you as plain fields right next
to it.

### Sending the token on every other request

```
Authorization: Bearer <access token>
```

Every endpoint after this point needs that header. No header = `401`.

### The access token expires in 1 hour

When it does, you'll start getting `401` on requests that used to work.
Instead of logging in again, exchange the `refresh` token (valid 14 days)
for a new `access` token:

**`POST /api/v1/auth/token/refresh/`**
```json
{ "refresh": "<the refresh token you saved at login>" }
```

**Response — `200`:**
```json
{ "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

Practical suggestion: wrap your HTTP client so that on any `401`, it tries
this refresh call once and retries the original request — that way nobody
has to think about token expiry in individual screens.

If the refresh token itself has expired (past 14 days) or is invalid, this
call also returns `401` — at that point there's no way back except a real
login again.

---

## 4. Errors — the three shapes you'll see

| Status | Meaning | Example |
|---|---|---|
| `401` | No token, or an invalid/expired one | `{"detail": "Authentication credentials were not provided."}` |
| `403` | Valid token, but this actor isn't allowed here | `{"detail": "Only an authenticated Admin can access this endpoint."}` |
| `400` | The request body itself is wrong | see below |

**`401` means:** log the user out / send them to the login screen.
**`403` means:** they're logged in fine, but as the wrong role for this
screen — this is a real bug in the frontend (calling an Admin-only endpoint
as a Seller, say), not something to prompt the user about.

**`400` validation errors** are a JSON object keyed by field name, each
value a list of messages for that field. Real example — `POST` to create
an Admin with an empty body:
```json
{
  "name": ["This field is required."],
  "email": ["This field is required."],
  "mobile": ["This field is required."],
  "type": ["This field is required."]
}
```

And a uniqueness conflict (email already used by another Admin):
```json
{ "email": ["admin with this email already exists."] }
```

This shape (`{field: [messages]}`) is consistent across every Create/Update
endpoint in this guide — build one generic "show these under their fields"
error handler and reuse it everywhere, rather than one per form.

---

## 5. Pagination — every list endpoint works the same way

Pagination is **limit/offset**, not page numbers.

```
GET /api/v1/accounts/admins/?limit=20&offset=40
```

- `limit` — how many rows to return. Defaults to 20 if you don't pass it.
  Capped at 100 even if you ask for more.
- `offset` — how many rows to skip.

**Every list response** (Admins, Sellers, Buyers) is wrapped the same way —
real example, `?limit=2` against the two test admins:
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    { "id": 2, "name": "Egoola Admin", "...": "..." },
    { "id": 10, "name": "Test Admin", "...": "..." }
  ]
}
```

- `count` — total rows matching the filter, across all pages.
- `next` / `previous` — full, ready-to-use URLs for the next/previous page,
  or `null` when there isn't one. Easiest approach: just follow these
  directly instead of hand-computing the next offset yourself.
- `results` — the actual array of rows for this page. This is the array
  your table/list component renders.

---

## 6. Searching and filtering

Every list endpoint accepts a `search` query param (matches partial text
across a few fields) plus filters specific to that resource.

| Resource | `search` matches | Extra filters |
|---|---|---|
| Admins | name, email, mobile | `?type=` (`super_admin` \| `admin`), `?status=` (`active` \| `inactive`) |
| Sellers | name, email, phone | `?verification_status=` (`unverified` \| `pending` \| `verified` \| `rejected`), `?status=` (`active` \| `suspended`) |
| Buyers | name, email, phone | `?status=` (`active` \| `suspended`) |

Example: `GET /api/v1/accounts/sellers/?search=arafat&verification_status=pending`

Filters combine — they're AND'd together, and combine fine with
`search`/`limit`/`offset` on the same request.

---

## 7. Admin Management

Base path: `/api/v1/accounts/admins/` — **Admin-only** (any Seller or Buyer
token gets `403` here).

### List — `GET /api/v1/accounts/admins/`

Rows come back in a **trimmed-down shape** — just enough for a table, no
media or address fields:
```json
{
  "id": 10,
  "name": "Test Admin",
  "email": "test.admin@egoola.com",
  "mobile": "0100000001",
  "profile_pic_url": null,
  "type": "admin",
  "status": "active",
  "last_logged_at": "2026-09-25T18:28:27.541161+06:00"
}
```

### Retrieve — `GET /api/v1/accounts/admins/{id}/`

The **full** record — same fields as List, plus address/geography and the
media list:
```json
{
  "id": 10,
  "name": "Test Admin",
  "email": "test.admin@egoola.com",
  "mobile": "0100000001",
  "profile_pic_path": null,
  "profile_pic_url": null,
  "type": "admin",
  "status": "active",
  "skills": null,
  "experiences": null,
  "interests": null,
  "educations": null,
  "present_address": null,
  "permanent_address": null,
  "country": null,
  "state": null,
  "city": null,
  "thana": null,
  "last_logged_at": "2026-09-25T18:28:40.854446+06:00",
  "media": []
}
```

`country`/`state`/`city`/`thana` are just the numeric id of the row in the
`geography` app (or `null`) — not a nested object. If you need to show a
name instead of an id, look it up against the geography endpoints.

`skills`/`experiences`/`interests`/`educations` are free-form JSON — send
whatever array/object shape your form collects, it's stored as-is.

### Create — `POST /api/v1/accounts/admins/`

```json
{
  "name": "New Admin",
  "email": "new.admin@egoola.com",
  "mobile": "01700000010",
  "password": "Test@12345",
  "type": "admin",
  "status": "active"
}
```

- `name`, `email`, `mobile`, `type`, `password` are **required** on create.
- `type` must be `super_admin` or `admin`.
- **Admin Management is super-admin only:** every `/accounts/admins/` call with a plain `admin` token returns `403` (`"Only a super-admin can access Admin Management."`). You also can't change your own `type`/`status` or delete yourself (`400`). See `docs/admin-management-guide.md`.
- `status` defaults to `active` if you leave it out.
- Response is `201` with the same full shape as Retrieve.

### Update — `PUT` (full) or `PATCH` (partial) `/api/v1/accounts/admins/{id}/`

Use `PATCH` for normal edits — send only the field(s) that changed:
```json
{ "status": "inactive" }
```

Use `PUT` only when you're intentionally replacing the whole record. On
`PUT`, `password` can still be left out — it's only required when
**creating** a new Admin, not on every update. If you do send `password` on
an update, it gets re-hashed and replaces the old one.

`last_logged_at`, `profile_pic_path`, `profile_pic_url` are **read-only** —
sending them does nothing (`profile_pic_path`/`url` are set by the file
upload endpoint, see §10 below).

### Delete — `DELETE /api/v1/accounts/admins/{id}/`

Returns `204` with no body.

---

## 8. Seller Management

Base path: `/api/v1/accounts/sellers/` — **Admin-only**, same as above.

### List — trimmed shape:
```json
{
  "id": 7,
  "name": "Test Seller",
  "email": "test.seller@egoola.com",
  "phone": "0100000002",
  "profile_pic_url": null,
  "verification_status": "unverified",
  "status": "active",
  "wallet_balance": "0.00",
  "bonus_balance": "0.00",
  "last_logged_at": "2026-09-25T18:28:28.814709+06:00"
}
```

### Retrieve — full shape, real example:
```json
{
  "id": 7,
  "name": "Test Seller",
  "email": "test.seller@egoola.com",
  "phone": "0100000002",
  "profile_pic_path": null,
  "profile_pic_url": null,
  "email_verified_at": null,
  "phone_verified_at": null,
  "verification_status": "unverified",
  "verification_note": null,
  "skills": null,
  "education": null,
  "experience": null,
  "interest": null,
  "present_address": null,
  "permanent_address": null,
  "country": null,
  "state": null,
  "city": null,
  "thana": null,
  "wallet_balance": "0.00",
  "bonus_balance": "0.00",
  "status": "active",
  "last_logged_at": "2026-09-25T18:28:28.814709+06:00",
  "media": [],
  "business_info": null
}
```

`wallet_balance`/`bonus_balance` come back as **strings** (e.g. `"0.00"`),
not numbers — that's normal for money fields, parse them as decimals on
your side rather than trusting JSON number precision.

`business_info` is `null` until a business profile has been saved (see
Create/Update below) — it's the Seller's public company profile (business
type, main product, owner name, etc.).

`email_verified_at`, `phone_verified_at`, `verification_status`,
`verification_note`, `wallet_balance`, `bonus_balance` are all **read-only**
— there's no verification/wallet-adjustment flow built yet (see §11), so
none of these can be set through this endpoint.

### Create — `POST /api/v1/accounts/sellers/`

```json
{
  "name": "New Seller",
  "email": "new.seller@egoola.com",
  "phone": "01700000020",
  "password": "Test@12345",
  "info": {
    "business_type": "Retail",
    "main_product": "Electronics",
    "owner_name": "New Seller",
    "employees_range": "1-10",
    "annual_revenue": "< $50,000",
    "established_year": "2024"
  }
}
```

- `name`, `email`, `phone`, `password` required.
- `info` is **optional on create, but if you send it**, these five fields
  inside it are required: `business_type`, `main_product`, `owner_name`,
  `employees_range`, `annual_revenue`, `established_year`. (`description`,
  `public_email`, `whatsapp`, `facebook`, `wechat`, `skype` inside `info`
  are optional.)
- Send `info` again on a later `PATCH` to update the business profile —
  it's saved as one row, so a partial `info` object still needs those five
  required sub-fields filled in (it's a full replace of the profile, not a
  per-field patch of it).
- What comes back in the response is `business_info`, not `info` — `info`
  is what you send, `business_info` is the validated, saved version you
  read back.

### Update / Delete

Same pattern as Admin — `PATCH` for partial edits, `PUT` for full replace,
`DELETE` returns `204`.

---

## 9. Buyer Management

Base path: `/api/v1/accounts/buyers/` — **Admin-only**.

One thing worth knowing: the underlying table/model is called `User` in
the backend code (not to be confused with a login account for Django
itself) — but the API path is `/buyers/`, so nothing about the URL changes.

### List — trimmed shape:
```json
{
  "id": 4,
  "name": "Test Buyer",
  "email": "test.buyer@egoola.com",
  "phone": "0100000003",
  "profile_pic_url": null,
  "wallet_balance": "0.00",
  "status": "active"
}
```

### Create — `POST /api/v1/accounts/buyers/`
```json
{
  "name": "New Buyer",
  "email": "new.buyer@egoola.com",
  "phone": "01700000030",
  "password": "Test@12345"
}
```

`name`, `email`, `phone`, `password` required. Everything else (address,
skills, etc.) is optional and can be filled in with a later `PATCH`.

`email_verified_at`, `phone_verified_at`, `wallet_balance` are read-only —
same reasoning as Seller above.

### Update / Delete

Same `PATCH`/`PUT`/`DELETE` pattern as the other two.

---

## 10. Uploading files (profile picture + documents)

Two kinds of file upload exist on all three resources (Admin/Seller/Buyer),
both handled through the *same* Create/Update endpoint — there's no
separate upload URL.

**Important:** because these involve real files, you must send the request
as `multipart/form-data`, not JSON, when you include either of these.

### Profile picture

Send a single field called `profile_pic` (the actual file, not a URL) in a
multipart form. The server uploads it and fills in `profile_pic_path` /
`profile_pic_url` on the record itself — you never set those two directly.

### Other documents (NID, certificates, gallery images, etc.)

Three fields, sent together, matched up **by position**:

- `media_for` — a list of labels, one per file (e.g. `nid`,
  `birth_certificate`; Seller also allows `certificate`, `gallery_image`,
  `gallery_video`; everything allows `other`).
- `media_file` — a list of files, same length and same order as
  `media_for`. The 1st `media_for` pairs with the 1st `media_file`, and so on.
- `media_delete_ids` — optional list of existing media row `id`s (from the
  `media` array in a Retrieve response) to delete in the same request.

There's no in-place "edit" of one uploaded file — to replace one, put its
id in `media_delete_ids` and upload the new one at the same time.

Example multipart form fields for updating a Seller's documents:
```
media_for:      nid
media_for:      certificate
media_file:     <file 1>
media_file:     <file 2>
media_delete_ids: 14
```

This adds an NID and a certificate, and removes the existing media row
with id `14`, all in one `PATCH` request.

---

## 11. What's deliberately not here yet

Don't build screens against these — they don't exist on the backend yet:

- **Seller/Buyer self-service login screens that go anywhere past login.**
  Seller and Buyer login work (§3) and return a valid token, but there are
  no Seller-facing or Buyer-facing endpoints yet (no "my profile", no
  product listings, no orders). Only Admin has real management screens
  right now.
- **Signup / registration.** Every Admin/Seller/Buyer record so far is
  created by an Admin through §7–9. There's no public "create your own
  account" endpoint yet.
- **OTP / email-verification / password-reset flows.** The fields exist in
  the database but nothing exposes them over the API yet — that's why
  `email_verified_at` etc. show as read-only above.
- **Seller wallet/bonus adjustments and verification approval.** Read-only
  for the same reason — the workflow that changes them hasn't been built.

If frontend work needs any of these sooner, flag it — the plan is to build
them "gradually" per actor, not all at once.
