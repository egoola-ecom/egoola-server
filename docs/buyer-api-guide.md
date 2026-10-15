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

## 3. Not built yet

- **OTP / phone and email verification.** `phone_verified_at` and `email_verified_at` stay empty for everyone; there is no code sent and no check.
- **Forgot / reset password** and **change password** for a buyer.
- **Rate limiting** on the public sign-up and login endpoints: put a limit in front of them before launch.
- **The buyer's own profile API** (view and edit my profile, add documents): the next Buyer Panel steps.

Tests: `scripts/smoke/buyer_register_smoke.py`. Postman: `Egoola-BuyerApp` → **Buyer sign-up and login**.
