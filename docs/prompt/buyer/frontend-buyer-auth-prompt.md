# Brief for the Egoola Web session — buyer login and self-registration

Backend done and tested in `egoola-server`: a buyer signing themself up and logging in. Read top to bottom, then
build in **Buyer Web**. Do not push; commit locally only if asked.

Read first: `docs/buyer-api-guide.md` sections 1–2 (the technical contract below is a copy of it), `docs/frontend-api-guide.md`
sections 3–4 (token handling — shared across admin/seller/buyer, read this for the refresh flow and error shapes).
Postman: `Egoola-BuyerApp` → **Auth**. Run backend with `uv run manage.py runserver 8000`. Existing test account:
`test.buyer@egoola.com` / `Test@12345` (or register a new one against this contract).

Every other buyer feature you've built (cart, wishlist, jobs/bidding) needs the token this flow produces — build
this first if it isn't already in place.

---

## 1. What this is

Two public (no-token) endpoints: register and log in. Both return a JWT pair (`access` + `refresh`) directly in
their response — **registration logs the buyer in too**, there's no separate "now log in" step after signing up.

Buyer login is **phone+password always**, **or email+password if the buyer gave one at sign-up**. A buyer who
didn't give an email has no way to log in with email — the UI should make phone the primary field, with email as
an alternative only when relevant (there's no way to know in advance from the login screen itself whether a given
buyer has one — just accept either and let the server decide).

## 2. The contract

### Register — `POST /api/v1/auth/buyer/register/`

Public. JSON, or `multipart/form-data` when a profile picture is included.

| Field | Required | Notes |
|---|---|---|
| `name` | **yes** | not blank |
| `phone` | **yes** | the buyer's mobile number **and their login**. Digits only, 6–15 of them, optional leading `+`. Spaces/hyphens are stripped server-side (`+880 1711-000111` saves as `+8801711000111`) — don't bother stripping client-side, but do strip for display consistency if you want. Must be unused |
| `password` | **yes** | ≥8 chars, not a very common password, not all-digit |
| `email` | no | must be unused if given (case-insensitive); empty/omitted = no email, and several buyers can all have none |
| `profile_pic` | no | one image file, needs multipart |
| `description` | no | about the buyer |
| `address_line` | no | street address |
| `country`/`state`/`city`/`thana` | no | ids from the public geography lists (`public-api-guide.md` §2 — country→state→city→thana, limit/offset dropdowns). Any level can be skipped, but each given level must belong to the one above it |
| `skills`/`experiences`/`interests`/`educations` | no | free-form JSON lists |

```json
POST /api/v1/auth/buyer/register/
{ "name": "Mahin Rahman", "phone": "+8801711000111", "password": "Buy@12345" }
```

`201`, already logged in:

```json
{ "access": "eyJ...", "refresh": "eyJ...", "actor_type": "user",
  "id": 14, "name": "Mahin Rahman", "phone": "+8801711000111", "email": null,
  "profile_pic_url": null, "description": null, "address_line": null,
  "country": null, "state": null, "city": null, "thana": null,
  "skills": null, "experiences": null, "interests": null, "educations": null,
  "status": "active", "message": "Welcome to Egoola. Your account is ready." }
```

Save `access`/`refresh` exactly as you would after login (next section) — the response shape is a superset of the
login response, carrying the full profile too. A failed sign-up leaves nothing behind (no row, no uploaded file).

**Errors — `400 {"field": ["message"]}`:**

| Problem | Field | Message |
|---|---|---|
| required field missing/blank | the field | `This field is required.` |
| bad mobile number | `phone` | `Enter a valid mobile number (digits only, may start with +).` |
| phone already used | `phone` | `buyer with this phone already exists.` |
| email already used | `email` | `buyer with this email already exists.` |
| bad email | `email` | `Enter a valid email address.` |
| weak password | `password` | a list of reasons (too short / too common / all-digit) |
| state/city/thana outside its parent | `state`/`city`/`thana` | `This city does not belong to the selected state.` |
| bad image | `profile_pic` | (image-validation message) |

### Log in — `POST /api/v1/auth/buyer/login/`

Send **exactly one** of `phone`/`email`, with `password`:

```json
{ "phone": "+8801711000111", "password": "Buy@12345" }
```
```json
{ "email": "mahin@example.com", "password": "Buy@12345" }
```

- Phone is matched with spaces/hyphens stripped — the buyer can type it however.
- `email` only works for a buyer who has one; a buyer without one must use phone.
- Both fields sent, or neither: `400 {"phone": ["Send either phone or email (one of them)."]}`.
- Wrong password, or an unrecognized phone/email: `401 {"detail": "Invalid phone number, email or password."}` —
  **one message for both cases**, on purpose (don't split this into "wrong password" vs "no such account" in the
  UI either — the backend won't tell you which, so showing one generic message is correct, not a shortcut).
- Suspended account: `401 {"detail": "This account is not active."}`.

`200`:

```json
{ "access": "...", "refresh": "...", "actor_type": "user", "id": 14, "name": "Mahin Rahman",
  "email": null, "phone": "+8801711000111" }
```

`email` is `null` when the buyer has none — not an error, just means they log in by phone.

### Token handling (shared with every other actor — `frontend-api-guide.md` §3–4)

- Save `access` and `refresh`.
- Every other call: `Authorization: Bearer <access>`. No header → `401`.
- `access` expires in **1 hour**. Refresh: `POST /api/v1/auth/token/refresh/` with `{"refresh": "<token>"}` →
  `{"access": "...", "refresh": "..."}` — refresh tokens **rotate**, save the new one each time.
- `refresh` is valid **14 days**; once it's expired/invalid, refresh also `401`s and the buyer must log in again.
- Recommended: wrap your HTTP client so any `401` tries one refresh-and-retry before giving up and redirecting to
  login — this is exactly what the heart/add-to-cart "logged-out → redirect to login with a return URL" flow you
  already settled on for other buyer screens should fall back to as well.

## 3. Tasks

1. **API client**: `buyer-auth-api.ts` — `register(payload)`, `login({phone|email, password})`,
   `refreshToken(refresh)`. Keep `register`'s payload typed so `email`/location/profile fields are genuinely
   optional, not empty-string placeholders (an empty string for `email` is a different thing from omitting it —
   omit, don't send `""`).
2. **Register screen**: name/phone/password required fields up front; email, photo, address, location
   (cascading country→state→city→thana dropdowns, reuse whatever component the public-browsing geography
   dropdowns use), and skills/experience/interest/education as a collapsed "more details" section. Multipart
   submit only when a photo is attached; plain JSON otherwise.
3. **Login screen**: a single input that accepts phone or email (detect which was typed, or give an explicit
   toggle — either is fine) + password. On success, store tokens and route to whatever page triggered the login
   (the return-URL pattern you're already using for logged-out cart/wishlist actions) or the buyer home if none.
4. **Auth guard** for every buyer-only route (cart, wishlist, jobs, profile, etc.) — redirect to login with a
   return URL when there's no valid token, per your own plan from the cart/wishlist brief.
5. **Token refresh interceptor**: on `401`, try the refresh call once; on a second `401` (refresh itself failed),
   clear stored tokens and redirect to login.
6. Error display: map the `{"field": [...]}` shape to per-field messages on both forms; map the login `401`'s
   single `detail` message to one generic banner, not a field-specific one (there's no field to attach it to —
   the backend never says which of phone/email/password was wrong).

## 4. Verify (browser, no login needed to start; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Register with only name/phone/password | `201`, logged in immediately, no second login step |
| 2 | Register again with the same phone | `400` on `phone`, field-level message shown |
| 3 | Register with a weak password | `400` on `password`, all reasons shown |
| 4 | Register with a `city` that doesn't belong to the chosen `state` | `400` on the mismatched field |
| 5 | Register with a profile picture | multipart submit succeeds, `profile_pic_url` populated |
| 6 | Log in with phone+password (account with no email) | `200` |
| 7 | Log in with email+password (account that has one) | `200` |
| 8 | Log in with both phone and email in the same request | `400` |
| 9 | Log in with wrong password | `401`, one generic message, not "wrong password" specifically |
| 10 | Log in as a suspended buyer (if one exists in test data) | `401 "This account is not active."` |
| 11 | Let the access token sit past 1 hour (or fake it), make a call | automatic refresh-and-retry, no visible interruption |
| 12 | Clear/expire the refresh token, then let access expire | redirected to login, not stuck in a refresh loop |
| 13 | Hit a buyer-only route while logged out | redirected to login with a return URL; after login, lands back on that route |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
