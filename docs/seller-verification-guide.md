# Seller Verification — Frontend Guide

Seller verification is not a separate endpoint — it's a few fields on the existing Seller
Management API (`/api/v1/accounts/sellers/`), Admin-only, same bearer token as everything else
on that resource.

## What's new

| Field | Where | Behavior |
|---|---|---|
| `verification_status` | `sellers` | Now writable (was read-only). One of `unverified`, `pending`, `verified`, `rejected`. |
| `verification_note` | `sellers` | Now writable. Always mirrors the note for the seller's *current* status — see "How verification_note behaves" below. |
| `verification_logs` | `sellers` (detail only) | New, read-only. Full change history, newest first. Never send this — it's server-written. |

## Default verification_status on create

- **Admin creates the Seller** (`POST /api/v1/accounts/sellers/`) → `verification_status` defaults to `verified` if you don't pass one.
- Any other creation path (e.g. a future public seller sign-up) → defaults to `unverified`.
- You can still pass `verification_status` explicitly on create to override the default (e.g. create straight into `pending`).

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

## How `verification_note` behaves

`sellers.verification_note` always holds the note for the **current** status only — it never
carries over from a previous status change. Every time you change `verification_status`:

- Send `verification_note` → that's what gets stored, both on the seller row and in the new log entry.
- Don't send it → it's stored as `null`, both on the seller row and in the new log entry — **even if the seller had a note from an earlier rejection.** Nothing is inherited.

So if you want the previous note to still show up after a status change, you have to resend it
yourself — the API will not do that for you.

An update that doesn't touch `verification_status` at all (e.g. just changing `name` or
`status`) leaves `verification_note` completely untouched, and writes nothing to the log.

## `verification_logs` — the change history

Only appears on the **detail** response (`GET /api/v1/accounts/sellers/{id}/`), not on the list
endpoint. A new entry is written:

- Once, always, when the seller is created (captures the initial status).
- Again, every time an update actually **changes** `verification_status` (setting it to the
  value it already had does not write a new entry).

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

`created_by` / `creator_type` / `creator_name` identify whoever made *that* change (currently
always an Admin, since only Admins can reach this API today).

## Full walkthrough

**1. Admin creates a seller, no note given — verified by default, note null:**
```
POST /api/v1/accounts/sellers/
{ "name": "Rafiq Traders", "email": "info@rafiqtraders.com", "phone": "+8801711000111", "password": "..." }
```
```json
{
  "id": 13,
  "verification_status": "verified",
  "verification_note": null,
  "verification_logs": [
    { "id": 5, "verification_status": "verified", "verification_note": null,
      "created_by": 10, "creator_type": "admin", "creator_name": "Test Admin",
      "created_at": "2026-09-28T02:26:18.68Z" }
  ]
}
```

**2. Admin rejects with a note:**
```
PATCH /api/v1/accounts/sellers/13/
{ "verification_status": "rejected", "verification_note": "Bad NID scan." }
```
```json
{
  "verification_status": "rejected",
  "verification_note": "Bad NID scan.",
  "verification_logs": [
    { "id": 6, "verification_status": "rejected", "verification_note": "Bad NID scan.", "...": "..." },
    { "id": 5, "verification_status": "verified", "verification_note": null, "...": "..." }
  ]
}
```

**3. Admin re-verifies later *without* resending a note — note clears to null, it does not keep "Bad NID scan.":**
```
PATCH /api/v1/accounts/sellers/13/
{ "verification_status": "verified" }
```
```json
{
  "verification_status": "verified",
  "verification_note": null,
  "verification_logs": [
    { "id": 7, "verification_status": "verified", "verification_note": null, "...": "..." },
    { "id": 6, "verification_status": "rejected", "verification_note": "Bad NID scan.", "...": "..." },
    { "id": 5, "verification_status": "verified", "verification_note": null, "...": "..." }
  ]
}
```

**4. An unrelated update (no `verification_status`) — note and log are untouched:**
```
PATCH /api/v1/accounts/sellers/13/
{ "status": "suspended" }
```
`verification_note` and `verification_logs` come back exactly as they were in step 3 — no new
log entry is written.
