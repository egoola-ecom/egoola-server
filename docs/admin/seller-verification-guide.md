# Seller Management & Verification — Admin Guide

Everything an **admin** does with sellers: the seller list and filters, the **Seller Request** queue
(new sign-ups and resubmissions), reviewing documents, approving and rejecting, and reading a seller's
change history. All of it is on the Seller Management API (`/api/v1/accounts/sellers/`), **Admin-only**,
same bearer token as everything else on that resource.

- Postman: `postman/admin/Egoola-Seller.postman_collection.json` (admin collection).
- **Seller-facing APIs** (sign-up, seller login, a seller's own profile, resubmit) are in a separate guide:
  [`../seller/seller-account-api-guide.md`](../seller/seller-account-api-guide.md), with their own collection `Egoola-SellerApp.postman_collection.json`.
- Basic list/create/update shapes: [`../frontend-api-guide.md`](../frontend-api-guide.md) §8.

---

## Table of contents

- [What's new](#whats-new)
- [Default verification_status on create](#default-verification_status-on-create)
- [Approving a self-registered seller](#approving-a-self-registered-seller)
  - [Pausing an approved seller](#pausing-an-approved-seller)
  - [When does a seller leave the Seller Request queue?](#when-does-a-seller-leave-the-seller-request-queue)
  - [Rejected sellers fix and resubmit](#rejected-sellers-fix-and-resubmit)
- [Changing verification_status later](#changing-verification_status-later)
- [How `verification_note` behaves](#how-verification_note-behaves)
- [`verification_logs` — the change history](#verification_logs-the-change-history)
- [The seller list and its filters](#the-seller-list-and-its-filters)
- [The Seller Request queue (cursor pagination)](#the-seller-request-queue-cursor-pagination)
- [Reviewing a request](#reviewing-a-request)
- [Profile change log (`profile_change_logs`)](#profile-change-log-profile_change_logs)
- [Deleting a seller](#deleting-a-seller)
- [Full walkthrough](#full-walkthrough)

---

## What's new

| Field | Where | Behavior |
|---|---|---|
| `verification_status` | `sellers` | Writable. One of `unverified`, `pending`, `verified`, `rejected`. |
| `verification_note` | `sellers` | Writable. Always mirrors the note for the seller's *current* status — see "How verification_note behaves" below. |
| `verification_logs` | `sellers` (detail only) | Read-only. Full status-change history, newest first. Never send this — it's server-written. |
| `status` | `sellers` | `active`, `inactive` or `suspended`. **Every value can log in now** — `status` gates what a seller can *do*, not whether they can log in. See "Login and the three access tiers" below. **Partly derived from `verification_status`** — see "Transition and status rules" below; only free to pick when `verification_status` is `verified`. |
| `was_ever_verified` | `sellers` (detail only) | Read-only. `true` forever once `verification_status` is ever saved as `verified`. Blocks any future move to `rejected`. Not on the list row — same as `verification_logs`/`profile_change_logs`. |
| `can_operate`, `can_edit_profile` | `sellers` (detail only) | Read-only. The two booleans that report which of the three access tiers a seller is in — see "Login and the three access tiers" below. Not on the list row. |
| `is_seller_request` | `sellers` | Read-only. `true` while the seller waits in the Seller Request queue. |
| `requested_at` | `sellers` | Read-only. When the seller joined the queue: sign-up, or the latest resubmit. |
| `profile_change_logs` | `sellers` (detail only) | Read-only. Every change to the seller's profile, before and after. See "Profile change log" below. |
| `remove_profile_pic` | `sellers` | Write-only, boolean, default `false`. `true` clears `profile_pic_path`/`profile_pic_url` back to `null` and deletes the file. Update only — a `profile_pic` sent in the same request always wins over it. |

## Default verification_status on create

- **Admin creates the Seller** (`POST /api/v1/accounts/sellers/`) → `verification_status` defaults to `verified` if you don't pass one.
- **The seller registers themselves** (`POST /api/v1/auth/seller/register/`) → always `unverified`, with `status: inactive` and `is_seller_request: true`. The registration writes the first history entry, created by the seller. (How a seller signs up: [`../seller/seller-account-api-guide.md`](../seller/seller-account-api-guide.md) §3.)
- Any other creation path → defaults to `unverified`.
- You can still pass `verification_status` explicitly on create to override the default (e.g. create straight into `pending`).

## Approving a self-registered seller

A seller who signed up by themselves is `inactive` and `unverified`. They can already log in, but only to edit
their own profile. Approving takes both fields, in one request:

```
PATCH /api/v1/accounts/sellers/{id}/
{ "verification_status": "verified", "status": "active" }
```

`verification_status: "verified"` is the KYC decision (the seller is now **approved**); `status: "active"` lets them use
the full seller features. They are separate switches on purpose. After both, the seller's login returns `can_operate: true`
(`can_operate` = `verified` AND `active`).

### Pausing an approved seller

`PATCH /accounts/sellers/{id}/ {"status": "inactive"}` pauses a seller. They stay `verified` (still approved), can
still log in, but are **fully locked** — not just down to profile-only: `can_operate` and `can_edit_profile` are
both `false`. Pausing an already-verified seller is stricter than pausing one who was never verified (see "Transition
and status rules" below, `verified + inactive`) — there's no "edit profile but not features" middle ground for them.
Set `status: "active"` again to restore full access. Pausing does not put them back in the Seller Request queue
(only a real sign-up or resubmit does).

**Every status can log in now, including `suspended`.** `suspended` no longer blocks login — it's a post-login
access tier, same as pausing: `can_operate` and `can_edit_profile` both `false` (except a `rejected` seller, see
below). Use it to lock a seller out of everything while still letting them see their own account status.

### When does a seller leave the Seller Request queue?

`is_seller_request` turns `false` when an admin **really changes** `verification_status` or `status` (to
`verified`, `rejected`, `pending` "I am checking this", `suspended`...). These do **not** move the seller out:

- editing an address, name, business profile or documents
- sending the same status again (a full `PUT` of the form does this)
- sending only a `verification_note`
- a request that fails validation (for example a rejection without a note)

The flag is read-only: no client, not even an admin, can set it. It turns `true` again only when the seller
signs up or **resubmits** (below). Sellers an admin creates directly are never requests.

### Rejected sellers fix and resubmit

A rejected seller's `status` is forced to `suspended` (see "Transition and status rules"), but they're a
**deliberate carve-out**: `can_edit_profile` stays `true` for them specifically, so they can still log in, read your
rejection note, fix their profile and documents, and press **Resubmit**. Nothing else is carved out — they stay
`403` on every full-feature endpoint, same as any other non-operating seller.

Resubmitting sets `verification_status` to `pending` (which forces `status` back to `inactive`, so they land in the
profile-only tier, not locked), puts them back in the queue (`is_seller_request: true`, `requested_at` = now, so
they appear as the newest request), and adds a history entry made by the seller (`creator_type: "seller"`) with
their optional message as the note. Your rejection reason stays in `verification_logs`. You review again and
approve or reject as usual.

While the seller is not approved (unverified, pending or rejected) they can add, delete and replace **any** of their
documents, NID included, so they can fix what you asked for. A rejected seller keeps at least one NID at all times.

**After you approve a seller, their NID and birth certificate are locked for them**: the seller can no longer add, delete or
replace those two (certificates and "other" documents stay editable). If one must change, you change it yourself on the
seller's page; admins are not blocked by the lock. Pausing a seller (inactive) does not unlock them: the lock follows the
verification result, not the account switch.

A rejected seller cannot sign up again with the same phone or email; they use resubmit.

**A seller logs in with their phone number + password.** So if you change a seller's phone number (admins can; sellers cannot),
their login changes with it: the old number stops working at once, so tell the seller their new login.

## Changing verification_status later

```
PATCH /api/v1/accounts/sellers/{id}/
{ "verification_status": "verified" }
```

- **Rejecting requires a note.** If `verification_status` is `rejected`, `verification_note` is
  mandatory **in that same request** — it doesn't matter whether a note already exists on the
  seller from before.
- Any other status (`verified`, `pending`, `unverified`) — `verification_note` is optional.

**Validation error if you reject without a note:**
```json
{ "verification_note": ["A verification note is required when rejecting a seller."] }
```
`400 Bad Request`

## Transition and status rules

Two rules on top of the basic field, both enforced in `SellerSerializer.validate()`:

**1. `rejected` only moves forward to `pending`.** You cannot PATCH a `rejected` seller straight
to `unverified` or `verified` — only to `pending` (review again from there):
```json
{ "verification_status": ["A rejected seller can only be moved to pending next."] }
```
`400`. Every other pair among `unverified`/`pending`/`verified` is open in both directions.

**2. Once ever verified, never `rejected` again — from any status, forever.** The first time a
seller's `verification_status` is saved as `verified`, `was_ever_verified` flips to `true` and
never flips back, even after the seller later moves to `unverified` or `pending`. Any later
attempt to set `verification_status: "rejected"` on that seller, from any status, fails:
```json
{ "verification_status": ["A seller who has ever been verified can never be rejected."] }
```
`400`. Practical effect: the "fix and resubmit" flow (see "Rejected sellers fix and resubmit"
above) only ever applies to a seller who has never once been verified — a seller who was
verified, then paused/demoted, cannot end up back in `rejected`.

**3. `status` is forced or restricted by the resulting `verification_status`**, in the same
request — this applies even if you only send `status` and don't touch `verification_status` at
all, because it's evaluated against whatever the seller's `verification_status` will be after
the request:

| Resulting `verification_status` | What happens to `status` |
|---|---|
| `pending` | Forced to `inactive` — whatever `status` you sent (or didn't) is silently overridden. |
| `rejected` | Forced to `suspended` — same, silently overridden. |
| `unverified` | Restricted: must be `inactive` or `suspended`. Sending (or leaving it resolved as) `active` is `400`: `{"status": ["A seller with verification_status=unverified cannot be active."]}` |
| `verified` | Free — `active`, `inactive` or `suspended`, your choice (this is how "Pausing an approved seller" and "Approving a self-registered seller" above work). |

`POST /seller/me/resubmit/` (the seller's own resubmit action, not an admin PATCH) restates rule 3's `pending`
forcing manually, since that endpoint writes the model directly rather than going through `SellerSerializer`.

## Login and the three access tiers

**Every status can log in** — `status` no longer gates login at all (it used to block `suspended`; it doesn't any
more). What a logged-in seller can actually *do* is one of three tiers, both reported as booleans on the seller row
(and in the seller's own login response):

| Tier | `can_operate` | `can_edit_profile` | Can do |
|---|---|---|---|
| Full | `true` | `true` | Everything. |
| Profile-only | `false` | `true` | Only their own profile/documents, change password, and (if `rejected`) resubmit. |
| Locked | `false` | `false` | Nothing — not even their own profile. Still able to `GET` it, just not change it. |

Which `(verification_status, status)` pair lands where — see the table in "What each reachable state falls into"
in [`../seller/seller-account-api-guide.md`](../seller/seller-account-api-guide.md) §1 for the full breakdown (this is the seller's
own view of the same three tiers your `PATCH`es here drive).

## How `verification_note` behaves

`sellers.verification_note` always holds the note for the **current** status only — it never
carries over from a previous status change. Every time you change `verification_status`:

- Send `verification_note` → that's what gets stored, both on the seller row and in the new log entry.
- Don't send it → it's stored as `null`, both on the seller row and in the new log entry — **even if the seller had a note from an earlier rejection.** Nothing is inherited.

So if you want the previous note to still show up after a status change, you have to resend it
yourself — the API will not do that for you.

An update that doesn't change `verification_status` (e.g. just changing `name` or
`status`, or re-sending the status the seller already has, as a full `PUT` does) leaves
`verification_note` completely untouched, and writes nothing to the log. A `verification_note`
sent without a real status change is ignored — a note is the reason for a status change, so the
note on the seller always matches the newest log entry. Because of this, re-sending
`"verification_status": "rejected"` on an already-rejected seller needs no note (and changes nothing).

## `verification_logs` — the change history

Only appears on the **detail** response (`GET /api/v1/accounts/sellers/{id}/`), not on the list
endpoint. A new entry is written:

- Once, always, when the seller is created (captures the initial status).
- Again, every time an update actually **changes** `verification_status` (setting it to the
  value it already had does not write a new entry).

For a self-registered seller the first entry has `creator_type: "seller"` (the seller is its own creator).

Each entry:

```json
{
  "id": 6,
  "verification_status": "rejected",
  "verification_note": "Bad NID scan.",
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "created_at": "2026-09-28T02:26:19.535740+06:00"
}
```

`created_by` / `creator_type` / `creator_name` identify whoever made *that* change: an Admin, or
the seller themselves for the registration entry of a self-registered account and for a resubmission.

## The seller list and its filters

`GET /api/v1/accounts/sellers/` — normal limit/offset pagination (`count`, `next`, `previous`, `results`).

| Param | Example | Meaning |
|---|---|---|
| `search` | `search=rafiq` | Partial match on name, email or phone |
| `verification_status` | `=unverified` | `unverified`, `pending`, `verified`, `rejected`. Several: `verification_status__in=unverified,pending` |
| `status` | `=inactive` | `active`, `inactive`, `suspended`. Several: `status__in=inactive,suspended` |
| `is_seller_request` | `=true` | In the Seller Request queue or not |
| `creator_type` | `=seller` | Who created the account: `seller` (signed up) or `admin` |
| `country`, `state`, `city`, `thana` | `city=8` | Geography ids |
| `has_business_profile` | `=true` / `false` | Did the seller send a business profile? |
| `business_type` | `=retail` | Text inside the business type (any case) |
| `email_verified`, `phone_verified` | `=false` | Everyone is `false` until the OTP flow exists |
| `created_from`, `created_to` | `=2026-10-01` | Sign-up date range, inclusive, `YYYY-MM-DD` |
| `requested_from`, `requested_to` | `=2026-10-01` | The same on the date they joined the queue (sign-up or latest resubmit) |

All filters combine (AND) and work with `search`, `limit` and `offset`. A list row:

```json
{
  "id": 211,
  "name": "Rafiq Ahmed Khan",
  "email": "smoke.guide@example.com",
  "phone": "+8801700096001",
  "profile_pic_url": null,
  "verification_status": "unverified",
  "status": "inactive",
  "is_seller_request": true,
  "wallet_balance": "0.00",
  "bonus_balance": "0.00",
  "last_logged_at": "2026-10-11T22:38:52.730000+06:00",
  "created_at": "2026-10-11T22:38:52.250133+06:00",
  "requested_at": "2026-10-11T22:38:51.947603+06:00"
}
```

`wallet_balance` / `bonus_balance` are strings (money). `requested_at` is `null` for a seller an admin created.

## The Seller Request queue (cursor pagination)

**`GET /api/v1/accounts/sellers/requests/`** — Admin only (any admin). Lists the sellers who signed up (or
resubmitted) and that no admin has acted on yet (`is_seller_request = true`).

This list uses **cursor pagination**, not limit/offset. It is a queue that changes while the admin works: with
offset paging, a new request arriving between two page loads shifts every row and the admin sees one twice or
misses one. A cursor never does that.

```json
{
  "next": "http://127.0.0.1:8000/api/v1/accounts/sellers/requests/?cursor=cD0yMDI2LTEwLTExKzE1JTNBMzQlM0E0OS4zMTk4ODglMkIwMCUzQTAw&limit=1",
  "previous": null,
  "results": [ { "id": 211, "name": "Rafiq Ahmed Khan", "is_seller_request": true, "...": "same row as the list" } ]
}
```

- **No `count`** and no page numbers; only `next` and `previous`.
- `next` / `previous` are full URLs. **Use them exactly as given.** The `cursor` is opaque; never build it.
- `next` is `null` on the last page; `previous` is `null` on the first. `limit` is the page size (default 20, max 100).
- Build "Load more" / infinite scroll by following `next`. Reset the cursor whenever a filter or the sort changes.
  A broken `cursor` returns `404`.
- **Menu badge** ("Seller Request (7)"): the queue has no count. Use `GET /accounts/sellers/?is_seller_request=true&limit=1`
  and read `count`.

Sorting with `ordering`:

| Value | Order |
|---|---|
| (nothing) | Newest request first (`-requested_at`) |
| `requested_at` | Oldest request first (first come, first served) |
| `created_at` / `-created_at` | By sign-up date |
| `name` / `-name` | A to Z / Z to A |
| `id` / `-id` | By id |

Any other value is ignored. A **resubmission counts as a new request** (`requested_at` is set again), so that seller
appears at the top of the default order. The queue accepts every filter in the table above.

## Reviewing a request

**`GET /api/v1/accounts/sellers/{id}/`** — everything the reviewer needs:

| Field | What it shows |
|---|---|
| `media` | The uploaded documents: `media_for` (`nid`, `certificate`...), `media_type` (`image`, or `document` for a PDF), `media_url` to open it |
| `business_info` | The business profile, or `null` |
| `present_address`, `permanent_address`, `country`, `state`, `city`, `thana` | Where the seller is |
| `is_seller_request`, `requested_at` | In the queue? Since when? |
| `verification_status`, `verification_note`, `status` | Current decision and the note for it |
| `verification_logs` | Review history (see "verification_logs" below) |
| `profile_change_logs` | Profile change history (next section) |

`media_url` is a path on a local server (`/media/...`): put the server address in front. In production the files are
private and the link is a full short-lived signed URL: fetch the detail again if a link has expired.

## Profile change log (`profile_change_logs`)

Every time a seller's profile is saved and something **really changed**, one row is added to `profile_change_logs`
on the seller **detail** (newest first). It records edits by the seller (their own profile, password change) **and by
an admin** (`PATCH /accounts/sellers/{id}/`). There is no separate endpoint. Status and verification changes are
**not** here: they are in `verification_logs`.

One row per save. `previous_data` and `new_data` have **the same keys**: only the fields that changed, as they were
before and as they are now. `changed_fields` lists those keys. A save that changes nothing writes no row.

```json
[
  {
    "id": 46,
    "changed_fields": ["business_info"],
    "previous_data": { "business_info": { "main_product": "Shoes" } },
    "new_data":      { "business_info": { "main_product": "Bags" } },
    "created_by": 211,
    "creator_type": "seller",
    "creator_name": "Rafiq Ahmed Khan",
    "created_at": "2026-10-11T22:38:53.429949+06:00"
  },
  {
    "id": 45,
    "changed_fields": ["name", "present_address", "business_info"],
    "previous_data": {
      "name": "Rafiq Ahmed",
      "present_address": "House 12, Road 5, Feni Sadar",
      "business_info": null
    },
    "new_data": {
      "name": "Rafiq Ahmed Khan",
      "present_address": "Shop 4, Trunk Road, Feni",
      "business_info": { "business_type": "Retail", "main_product": "Shoes", "owner_name": "Rafiq Ahmed", "...": "all business fields" }
    },
    "created_by": 211,
    "creator_type": "seller",
    "creator_name": "Rafiq Ahmed",
    "created_at": "2026-10-11T22:38:53.252679+06:00"
  }
]
```

What can appear as a key, and how it looks:

| Key | Value |
|---|---|
| `name`, `email`, `phone`, `present_address`, `permanent_address` | text |
| `country`, `state`, `city`, `thana` | `{"id": 13, "name": "Chittagong"}` or `null` (the name is saved too, so the log stays readable if a place is renamed) |
| `skills`, `education`, `experience`, `interest` | the JSON value |
| `profile_pic` | the picture URL |
| `business_info` | the whole object when first added (`previous`: `null`); afterwards only the sub-fields that changed |
| `documents` | the full list of documents before and after (`id`, `media_for`, `media_type`, `media_url`) |
| `password` | always the text `"[hidden]"` on both sides. The password or its hash is never stored. |

`creator_type` is `seller` or `admin`; `creator_name` is that person's name when they started the change. Rows are
never edited or deleted. Show it in the seller detail as a timeline: who, when, and a before → after for each key in
`changed_fields`. A seller cannot change their email or phone themselves (for now); an admin can, and it is logged.

## Deleting a seller

`DELETE /accounts/sellers/{id}/` returns `204` and removes the seller, their history and their documents, if nothing
protects the row. **A seller with any order cannot be hard-deleted** — `Order.seller` is a `PROTECT` foreign key, so this
now returns `409` instead: `{"detail": "This seller has one or more orders. Deactivate or suspend the account instead
of deleting."}`. Deactivate (`status: "inactive"`) or suspend (`status: "suspended"`) instead.

A seller with **no** orders deletes cleanly, and their uploaded files (identity documents and profile photo) are
deleted from storage too. Deleting a single document with `media_delete_ids`, or replacing/clearing a photo
(`profile_pic`/`remove_profile_pic` — see "What's new" above), removes that file as well. The same cascade applies to
buyers and admins — but note neither of those resources has an order-style `PROTECT` guard, so this 409 is Seller-only
for now.

## Full walkthrough

**Note on the default:** creating a seller with **no** `verification_status` in the payload defaults it to
`verified` (admin-created) immediately — see "Default verification_status on create" above. That seller could
never be rejected afterward (rule 2 below), so this walkthrough creates seller #13 explicitly `unverified` instead,
to show reject → re-verify → the lock that follows.

**1. Admin creates a seller explicitly `unverified` + `inactive`, no note given:**
```
POST /api/v1/accounts/sellers/
{ "name": "Rafiq Traders", "email": "info@rafiqtraders.com", "phone": "+8801711000111", "password": "...",
  "verification_status": "unverified", "status": "inactive" }
```
```json
{
  "id": 13,
  "verification_status": "unverified",
  "verification_note": null,
  "was_ever_verified": false,
  "verification_logs": [
    { "id": 5, "verification_status": "unverified", "verification_note": null,
      "created_by": 10, "creator_type": "admin", "creator_name": "Test Admin",
      "created_at": "2026-09-28T08:26:18.680000+06:00" }
  ]
}
```

**2. Admin rejects with a note** (legal — this seller has never been verified):
```
PATCH /api/v1/accounts/sellers/13/
{ "verification_status": "rejected", "verification_note": "Bad NID scan." }
```
```json
{
  "verification_status": "rejected",
  "verification_note": "Bad NID scan.",
  "status": "suspended",
  "was_ever_verified": false,
  "verification_logs": [
    { "id": 6, "verification_status": "rejected", "verification_note": "Bad NID scan.", "...": "..." },
    { "id": 5, "verification_status": "unverified", "verification_note": null, "...": "..." }
  ]
}
```
`status` is forced to `suspended`; `can_edit_profile` is still `true` for this seller specifically (the rejected
carve-out), so they can log in and fix things.

**3. Admin re-verifies later *without* resending a note — note clears to null, it does not keep "Bad NID scan.":**
```
PATCH /api/v1/accounts/sellers/13/
{ "verification_status": "verified", "status": "active" }
```
```json
{
  "verification_status": "verified",
  "verification_note": null,
  "status": "active",
  "was_ever_verified": true,
  "verification_logs": [
    { "id": 7, "verification_status": "verified", "verification_note": null, "...": "..." },
    { "id": 6, "verification_status": "rejected", "verification_note": "Bad NID scan.", "...": "..." },
    { "id": 5, "verification_status": "unverified", "verification_note": null, "...": "..." }
  ]
}
```
`was_ever_verified` flips to `true` here, and never flips back.

**4. An unrelated update (no `verification_status`) — note and log are untouched:**
```
PATCH /api/v1/accounts/sellers/13/
{ "status": "suspended" }
```
`verification_note` and `verification_logs` come back exactly as they were in step 3 — no new
log entry is written. (This now also locks the seller: `verified + suspended` is the locked tier.)

**5. Trying to reject this seller now fails — the lock from step 3 is permanent:**
```
PATCH /api/v1/accounts/sellers/13/
{ "verification_status": "rejected", "verification_note": "trying anyway" }
```
```json
{ "verification_status": ["A seller who has ever been verified can never be rejected."] }
```
`400`. It doesn't matter that `verification_status` is currently `verified` and not literally "rejected" already —
`was_ever_verified` (set permanently in step 3) is what's checked, not the current value.
