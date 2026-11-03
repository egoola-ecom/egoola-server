# Jobs & Bidding — Admin API

Unlike Cart/Wishlist oversight, this is **not read-only**: "admin can do everything" a buyer or a seller can —
create or edit a job on any buyer's behalf, create or edit a bid on any seller's behalf, accept a bid on the
buyer's behalf, and undo an already-accepted hire. This guide is the admin-facing reference; the full state
machine and every error case (shared with the buyer and seller sides) is
[`../listing-complete-guide.md`](../listing-complete-guide.md) section 16, which this guide assumes.

Header: `Authorization: Bearer <admin access token>`. Both a plain `admin` and a `super_admin` may use these —
no super-admin-only restriction here.

| Token | Result |
|---|---|
| none / invalid | `401` |
| seller or buyer token | `403` |
| admin (either type) | allowed |

**Pagination**: the job panel is limit/offset (`count`, `next`, `previous`, `results`; default 20, max 100), same
as `/catalog/listings/` and `/catalog/gigs/`. The bid panel is **cursor**-based (`next`, `previous`, `results`, no
`count`), same convention as the Seller Request queue and Cart/Wishlist oversight.

Postman: `Egoola-Listing` → **Jobs**, `Egoola` → **Bidding**.

---

## Table of contents

- [1. The job panel — `/api/v1/catalog/jobs/...`](#1-the-job-panel-apiv1catalogjobs)
  - [Create — `POST /catalog/jobs/`](#create-post-catalogjobs)
  - [Edit — `PATCH /catalog/jobs/{id}/`](#edit-patch-catalogjobsid)
  - [It is not the same thing as `/catalog/listings/` or `/catalog/gigs/`](#it-is-not-the-same-thing-as-cataloglistings-or-cataloggigs)
- [2. The bid panel — `/api/v1/bidding/bids/...`](#2-the-bid-panel-apiv1biddingbids)
  - [Create — `POST /bidding/bids/`](#create-post-biddingbids)
  - [Edit — `PATCH /bidding/bids/{id}/`](#edit-patch-biddingbidsid)
  - [Accept — `POST /bidding/bids/{id}/accept/`](#accept-post-biddingbidsidaccept)
  - [Reject — `POST /bidding/bids/{id}/reject/`](#reject-post-biddingbidsidreject)
  - [`accept` vs `reject` vs the job's own `in_progress → cancelled`](#accept-vs-reject-vs-the-jobs-own-in_progress-cancelled)
- [Testing](#testing)

---

## 1. The job panel — `/api/v1/catalog/jobs/...`

| Call | What it does |
|---|---|
| `POST /catalog/jobs/` | create **on a buyer's behalf** — `buyer` is required |
| `GET /catalog/jobs/` | every job |
| `GET /catalog/jobs/{id}/` | detail |
| `PATCH` / `PUT /catalog/jobs/{id}/` | edit on the buyer's behalf |

No delete — a job is cancelled, never removed (see `Listing.Status`).

Filters: `status`, `category`, `buyer`, `created_from`/`created_to`, `requested_from`/`requested_to` (same as the
admin product list, `ListingFilter`). Search: `title`, `title_bn`, `description`, `buyer__name`, `buyer__phone`.
Ordering: `created_at`, `updated_at`, `id` (default `-created_at`).

### Create — `POST /catalog/jobs/`

```json
{ "buyer": 4, "category": 29, "title": "Need a plumber for bathroom pipe repair",
  "description": "Leaking pipe under the basin.", "urgent": true, "delivery_days": 1,
  "skus": [ { "price_type": "fixed", "price": "1500" } ] }
```

`buyer` is required on create only (never reassigned on update) — `{"buyer": "Say which buyer this job is for."}`
without it. Everything else (category must be an active service category, at least one budget tier, no two tiers
with the same `price_type`) is identical to a buyer creating their own job. The job always starts
`open_for_bidding` — a `status` sent is ignored.

```json
{
  "id": 42, "title": "Need a plumber for bathroom pipe repair", "slug": "need-a-plumber-...",
  "category": { "id": 29, "name": "Home Repair", "name_bn": "...", "slug": "home-repair" },
  "buyer": { "id": 4, "name": "Test Buyer", "phone": "+8801700000003", "email": "test.buyer@egoola.com" },
  "status": "open_for_bidding", "budget": { "price": "1500.00", "price_type": "fixed" }, "bid_count": 0,
  "delivery_days": 1, "urgent": true, "created_at": "...", "updated_at": "...",
  "description": "Leaking pipe under the basin.",
  "location": { "country": null, "state": null, "city": null, "thana": null },
  "skus": [ { "id": 101, "price_type": "fixed", "price": "1500.00", "...": "..." } ],
  "accepted_bid": null, "note": null
}
```

The admin detail/list rows carry a **`buyer` brief** (`id`, `name`, `phone`, `email`) that the buyer's own
`/buyer/jobs/` response doesn't need (a buyer already knows who they are).

### Edit — `PATCH /catalog/jobs/{id}/`

Same budget-SKU reconcile, same status-move table as a buyer's own job
(`../listing-complete-guide.md` §16.2, §16.5) — **plus one admin-only move**:

| From | To | Note |
|---|---|---|
| `in_progress` | `cancelled` | **admin only.** Requires a mandatory `note`: `{"note": "A reason is required to cancel a hired job."}` without one. A buyer cannot make this move at all. |

```json
PATCH /catalog/jobs/42/
{ "status": "cancelled", "note": "Buyer and admin agreed to call it off" }
```

Cancelling an `in_progress` job this way cascades like any other job cancel: the accepted bid → `cancelled`, its
Order → `cancelled` (`cancelled_reason` = this note).

### It is not the same thing as `/catalog/listings/` or `/catalog/gigs/`

A job id is `404` on both of those, and posting `posted_by_role: "buyer_request"` to either is `400`:

```json
POST /catalog/listings/
{ "category": 29, "catalog_type": "service", "posted_by_role": "buyer_request", "buyer": 4, "...": "..." }
```
→ `400 {"posted_by_role": ["A buyer's job request has its own endpoint: /catalog/jobs/ (admin) or /buyer/jobs/ (buyer)."]}`

---

## 2. The bid panel — `/api/v1/bidding/bids/...`

| Call | What it does |
|---|---|
| `POST /bidding/bids/` | create **on a seller's behalf** — `listing` (the job) and `bidder` (the seller) required |
| `GET /bidding/bids/` | every bid, cursor-paginated |
| `GET /bidding/bids/{id}/` | detail |
| `PATCH /bidding/bids/{id}/` | edit on the seller's behalf (only while `pending`) |
| `POST /bidding/bids/{id}/accept/` | accept **on the buyer's behalf** |
| `POST /bidding/bids/{id}/reject/` | undo an **already-accepted** hire |

No delete — a bid is never hard-deleted, only its status changes. Filters: `status`, `listing`, `bidder`.
Ordering: `created_at`, `updated_at`, `id` (default `-created_at`).

### Create — `POST /bidding/bids/`

```json
{ "listing": 42, "bidder": 15, "description": "Can start tomorrow",
  "price_tiers": [ { "price_type": "fixed", "price": "1300" } ] }
```

`listing` and `bidder` are required on create only, and are never reassigned on update —
`{"listing": "Say which job this bid is for."}` / `{"bidder": "Say which seller this bid is for."}` with either
missing. Same rules as a seller placing their own bid: the job must be `open_for_bidding`, that seller must have
no other **live** bid on it, at least one price tier, no two tiers of the same `price_type`. The bid always
starts `pending`.

```json
{
  "id": 7, "job": { "id": 42, "title": "Need a plumber...", "title_bn": null, "slug": "...", "status": "open_for_bidding", "buyer": 4 },
  "bidder": { "id": 15, "name": "Karim Electric", "phone": "+8801700000015" },
  "status": "pending", "description": "Can start tomorrow", "proposed_start": null, "proposed_end": null,
  "price_tiers": [ { "id": 12, "price_type": "fixed", "price": "1300.00", "duration": 1, "description": null, "total_price": "1300.00" } ],
  "accepted_price_tier": null, "created_at": "...", "updated_at": "...",
  "actual_start_date": null, "actual_end_date": null, "note": null
}
```

The admin's `job` brief includes `buyer` (so an admin reviewing a bid can see who posted it without a second
call); the admin's `bidder` brief is `id`/`name`/`phone`.

### Edit — `PATCH /bidding/bids/{id}/`

Only while `pending` (`400` "This bid can no longer be edited." otherwise). `price_tiers` reconciles exactly like
a seller's own edit. The only `status` move here is `cancelled` — `{"status": "You can only cancel a pending
bid."}` for anything else. **Use `accept` / `reject` below for those**, not a plain `PATCH`.

### Accept — `POST /bidding/bids/{id}/accept/`

Identical effect to the buyer's own accept (`../listing-complete-guide.md` §16.6): that bid → `accepted`, every
other pending bid on the job → `rejected`, the job → `in_progress`, and an Order is created directly.

```json
POST /bidding/bids/7/accept/
{ "price_tier_id": 12 }
```
(`price_tier_id` only needed when the bid quoted more than one price option.)

```json
{ "bid": { "id": 7, "status": "accepted", "accepted_price_tier": { "id": 12, "...": "..." }, "...": "..." },
  "order": { "id": 301, "status": "in_progress", "payable": "1300.00" } }
```

Errors: job not `open_for_bidding` → `400`; bid not `pending` → `400`; multi-tier bid with no `price_tier_id` →
`400`; an id that isn't one of that bid's tiers → `400`; unknown bid id → `404`.

### Reject — `POST /bidding/bids/{id}/reject/`

**Undoes an already-accepted hire without cancelling the job.** Only works on a bid that is currently `accepted`.

```json
POST /bidding/bids/7/reject/
{ "note": "Seller backed out" }
```

What happens:
1. That bid → `rejected` (not `cancelled` — it *was* judged, the other way), `accepted_price_tier` cleared, `note`
   set to the reason given.
2. Its Order → `cancelled`, `cancelled_reason` = this note.
3. The job → `open_for_bidding` again (reopened for new bids).
4. **Every bid that auto-rejected earlier** when this one was first accepted **stays `rejected`** — they are not
   restored to `pending`. A seller who wants back in places a brand-new bid.

```json
{ "id": 7, "status": "rejected", "note": "Seller backed out", "accepted_price_tier": null, "...": "..." }
```

Errors: the bid isn't currently `accepted` → `400` ("Only an accepted bid can be rejected this way."); no `note`
→ `400` ("A reason is required.").

### `accept` vs `reject` vs the job's own `in_progress → cancelled`

| You want to... | Use |
|---|---|
| Hire a bidder | `POST /bidding/bids/{id}/accept/` |
| Undo a hire, job stays open for other sellers to bid again | `POST /bidding/bids/{id}/reject/` |
| Kill the job entirely (no more bidding, nothing to hire) | `PATCH /catalog/jobs/{id}/` with `{"status": "cancelled", "note": "..."}` |

---

## Testing

`admin_job_bid_smoke.py` (32 checks): create a job on a buyer's behalf, create a bid on a seller's behalf, the
admin oversight filters, `accept`, `reject` and its cascades (job reopens, Order cancelled, the earlier
auto-rejected rival stays rejected), and the admin-only `in_progress → cancelled` move with its mandatory reason.
Also re-confirms a job 404s on `/catalog/listings/` and `/catalog/gigs/`. Run with `scripts/smoke/run_all.sh` or
individually against the dev server (see `scripts/smoke/README.md`). Test data was removed afterwards.
