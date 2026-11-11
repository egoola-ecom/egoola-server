# Brief: Seller Account APIs (sign-up, login, profile) — web + mobile

Backend (`egoola-server`, Django REST) ships the seller **account** surface: public
sign-up with KYC documents, phone+password login, the seller's own profile (view,
edit, documents), resubmit after a rejection, and change password. Nothing else.
**This prompt is account only** — no products, gigs, jobs/bidding or orders. Those
get their own prompts one at a time; do not start on them here even if you notice
gaps while you're in the code.

Do not push to any remote. Commit locally only when asked. Do not change
`egoola-server` — if the contract looks wrong or something needed is missing on the
backend, stop and report it instead of working around it.

Two target apps, two different starting points — read the section for the one you're
working in:

- **`egoola-web`** (Next.js) — the seller account screens already exist. Your job is
  to **cross-check** the implementation against the contract below, fix mismatches,
  and report anything that doesn't match (§2).
- **`egoola-seller`** (Flutter, the seller mobile app) — only the folder skeleton
  exists (`lib/features/{auth,onboarding,profile}/{data,domain,presentation}` are
  empty `.gitkeep` stubs). Your job is to **build** the screens and API layer from
  scratch (§3).

---

## 0. Read first

1. This file.
2. `egoola-server/docs/seller/seller-account-api-guide.md` — the full contract. **The source of truth.**
3. `egoola-server/docs/frontend-api-guide.md` sections 1–5 (base URL, tokens, error shapes) and `egoola-server/docs/authentication.md`.
4. Plain-language guide: `egoola-server/docs/Egoola_Seller_Guide.md`.
5. Test accounts: `egoola-server/docs/test-accounts.md`. Postman (real responses):
   `egoola-server/postman/seller/Egoola-SellerApp.postman_collection.json` → **Setup**, **Public lookups**,
   **Seller sign-up**, **Seller — own profile**, **After approval** folders, + `Egoola-Local.postman_environment.json`.

Run the backend with `uv run manage.py runserver 8000`.

---

## 1. The contract (condensed — read the guide for every field and error)

| Call | What it does |
|---|---|
| `GET /api/v1/public/geography/{countries,states,cities,thanas}/` | location dropdowns, no token (§2 of the guide) |
| `POST /api/v1/auth/seller/register/` | sign-up, multipart, no token, no token back either (§3) |
| `POST /api/v1/auth/seller/login/` | `{"phone","password"}` — **phone, not email** (§4) |
| `GET /api/v1/seller/me/` | own profile, open even to a **locked** seller (§5.1) |
| `PATCH /api/v1/seller/me/` | edit profile + documents, needs `can_edit_profile` (§5.2–5.3) |
| `POST /api/v1/seller/me/resubmit/` | only when `rejected` (§5.4) |
| `POST /api/v1/seller/me/change-password/` | (§5.5) |

**The state machine that drives every screen** (guide §1): two independent fields,
`verification_status` (`unverified`/`pending`/`verified`/`rejected`) and `status`
(`active`/`inactive`/`suspended`). `can_operate = verified && active`. Three tiers,
both booleans returned on login and on `GET /seller/me/`:

| Tier | `can_operate` | `can_edit_profile` | Screen |
|---|---|---|---|
| Full | `true` | `true` | the main app (out of scope here) |
| Profile-only | `false` | `true` | under-review / rejected (+ Resubmit) / paused-but-not-yet-approved — profile screens only |
| Locked | `false` | `false` | read-only `GET /seller/me/`, every write `403` |

Every status can log in now (including `suspended`) — it is a post-login tier, not a
login gate. The server re-reads the seller on **every request**: re-fetch
`/seller/me/` on app start/resume and whenever a call returns `403`/`401`
unexpectedly, and re-route.

**Errors, the shapes you'll see:** `401` no/expired token or (at login) wrong
phone+password (`{"detail": "Invalid phone number or password."}`, same message for
a wrong password and an unknown phone). `403` = `{"detail": "..."}`, two different
messages depending on tier (guide §6/7) — show the server's text, don't invent your
own. `400` is `{"field": ["message", ...]}`. `415` = multipart sent to a JSON-only
call or vice versa.

---

## 2. `egoola-web` — cross-check tasks

Existing files (read all of them before changing anything):

- `src/lib/seller-register-api.ts`, `src/lib/seller-me-api.ts`, `src/lib/seller-request-count.ts`
- `src/app/(public)/seller/register/register-form.tsx` (sign-up)
- `src/app/(public)/login/login-form.tsx` (shared buyer/seller tabs — confirm the
  seller tab sends `phone` not `email`, and shows the phone-specific placeholder/hint)
- `src/app/(seller)/seller/profile/profile-client.tsx`, `src/app/(seller)/seller/profile/page.tsx`
- `src/app/(seller)/seller/password/password-client.tsx`, `src/app/(seller)/seller/password/page.tsx`
- `src/app/(seller)/seller/seller-context.tsx` (the session/tier state — confirm it
  re-reads `/seller/me/` on the right triggers, not just once at login)

Cross-check against the guide, fix what's wrong, report what you changed:

1. **Register**: all required fields present (name, email, phone, password,
   present_address, permanent_address, country/state/city cascader, thana optional);
   `media_for`+`media_file` sent as **pairs in matching order**, at least one `nid`
   enforced client-side before submit; optional `profile_pic`, optional `info` (all
   six business fields required together if `info` is sent at all); `201` has **no
   token** — confirm the form routes to a "thank you, log in" screen, not an
   auto-login attempt.
2. **Login**: seller tab sends `{"phone","password"}`, not `email`; stores
   `access`/`refresh`; reads `verification_status`/`status`/`can_operate`/`can_edit_profile`
   from the response and routes to the right tier screen, not just "logged in".
3. **Profile read**: `GET /seller/me/` rendered fields match §5.1 exactly, including
   `verification_note` shown when present, and `media[]` URLs prefixed with the
   server origin when they're relative (`/media/...`).
4. **Profile edit**: only changed fields sent; `email`/`phone` shown read-only (not
   editable in the form at all, or a submit attempt is blocked client-side before the
   guaranteed-`400` round trip); `country/state/city/thana` re-validated as one
   branch before submit.
5. **Documents**: add/delete/replace via `media_for`+`media_file`+`media_delete_ids`;
   UI enforces "at least one NID must remain" before submit; **NID/birth_certificate
   locked once `verified`** — those controls disabled/hidden in that state, with the
   "ask an admin" message, while `certificate`/`other` stay editable.
6. **Resubmit**: visible and callable **only** when `verification_status === "rejected"`;
   shows `verification_note` as the reason; optional note field ≤ 1000 chars; after
   success, re-reads `/seller/me/` and routes back to under-review, not a stale cached
   tier.
7. **Change password**: `current_password`+`new_password`; server error text shown
   under the right field, not swallowed into a generic toast.

---

## 3. `egoola-seller` (Flutter) — build tasks

Nothing exists yet beyond the empty feature folders. Build, in this order:

1. **Foundation** (if not already done elsewhere in the project): Dio client with a
   refresh interceptor (`401` → refresh once, serialize concurrent refreshes, retry;
   refresh failure → clear storage → login), a generic `400` error mapper
   (`Map<String, List<String>>`, flatten nested keys), secure token storage.
2. **Login** (`lib/features/auth`) — `POST /auth/seller/login/ {"phone","password"}`.
   Phone field, not email. Store `access`+`refresh`. Read
   `verification_status`/`status`/`can_operate`/`can_edit_profile` into a session
   provider that the router reads for its redirect guard.
3. **Sign-up** (`lib/features/onboarding`) — multi-step wizard, one multipart request
   at the end:
   - account (`name`,`email`,`phone`,`password`), address + cascading geography
     dropdowns (`GET /public/geography/{countries,states,cities,thanas}/`, no token),
     documents (`media_for`+`media_file` pairs, at least one `nid`, JPG/PNG/WEBP/PDF
     ≤5 MB, ≤10 files), optional `profile_pic`, optional business `info` (all six
     fields together or omit it entirely).
   - `201` has no token → "thank you, we'll review your documents" screen with a
     Login button. `400` field errors map back to the step that owns the key.
4. **Profile + status screens** (`lib/features/profile`) — works in every
   non-suspended state:
   - `GET`/`PATCH /seller/me/` — view/edit, `email`/`phone` read-only, documents
     (add/delete/replace, enforce the NID-remains and locked-after-verified rules
     client-side as well as handling the server's `400`).
   - Under-review / rejected (reason + Resubmit button →
     `POST /seller/me/resubmit/`) / paused screens, driven by the tier table in §1.
   - `POST /seller/me/change-password/`.
   - Re-read `/seller/me/` on app start, on resume, and whenever any call returns an
     unexpected `403`.
5. **Router guard**: no token → login; token + profile-only or locked → status/profile
   screens only; token + full tier → a placeholder "coming soon" home (the actual
   seller features are out of scope for this prompt).

---

## 4. Verify (record the result of each, both platforms)

| # | Case | Expected |
|---|---|---|
| 1 | Sign up with 2 NID files | `201`, no token, thank-you screen |
| 2 | Sign up with no NID / a `.txt` / a 6 MB file / a duplicate phone | field errors on the right step/field, nothing created |
| 3 | Wrong password; unknown phone | same message both times, no leak |
| 4 | Log in as a fresh `unverified`+`inactive` seller | under-review screen, no listings/gigs nav |
| 5 | [Admin] approve → app resumes / re-login | full-tier placeholder shown, no re-login needed if session re-reads `/seller/me/` |
| 6 | [Admin] reject with a reason → open profile | reason shown, Resubmit works, lands back on under-review (`pending`) |
| 7 | [Admin] pause an approved seller → any call | `403`/locked screen on next re-read, not a stale "approved" view |
| 8 | [Admin] suspend → try to log in | logs in (not blocked), lands on **locked**: read-only profile, no edit controls |
| 9 | Verified seller tries to edit/delete NID | blocked in UI; a forced request shows the server's locked message |
| 10 | Delete the only NID with no replacement in the same request | blocked client-side or `400` mapped cleanly |
| 11 | Change password with wrong current password | field error, token still works after |
| 12 | Token expiry mid-session | silent refresh + retry; expired refresh → login |

Report which cases pass, what you changed, and anything in
`seller-account-api-guide.md` or this brief that looked wrong, missing or unclear
once you tried it against the real API.

---

## 5. Not built on the backend yet — do not build screens for these

Email/phone OTP verification, changing email or phone, push notifications on
approval/rejection/resubmit, per-document verification, seeing the profile change
history as a seller. (Full list: guide §8.)
