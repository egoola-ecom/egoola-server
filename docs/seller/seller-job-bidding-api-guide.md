# Seller Job Board & Bidding API Guide

The seller side of **jobs** — a buyer's request for work, hired through **bidding**
rather than bought outright. All endpoints live under `/api/v1/seller/` and need a
**seller access token** (`Authorization: Bearer <seller access token>`). No token is
`401`; an admin or buyer token is `403`.

> **Products, gigs and jobs.** This guide covers the job board and bidding only
> (`/seller/jobs/`, `/seller/bids/`). A seller's product is on `/seller/listings/` — see
> [`seller-listing-api-guide.md`](seller-listing-api-guide.md). A seller's own service
> offer is a gig — see [`seller-gig-api-guide.md`](seller-gig-api-guide.md). A job is a
> **buyer's** listing: a seller only browses and bids, never creates or edits one. Full
> reference (the state machine, every error, the buyer and admin sides):
> [`../listing-complete-guide.md`](../listing-complete-guide.md) section 16. Plain-language
> overview: [`../Egoola_Job_Guide.md`](../Egoola_Job_Guide.md).
>
> The admin side is [`../admin/job-admin-guide.md`](../admin/job-admin-guide.md).

Related files: `apps/bidding/seller/{urls,views,serializers}.py`,
`apps/catalog/seller/{urls,views}.py` (the job board), `apps/bidding/models.py`; Postman
collection `postman/seller/Egoola-SellerApp.postman_collection.json` → **Seller jobs &
bidding** folder. Smoke test: `scripts/smoke/seller_job_smoke.py`.

---

## Table of contents

- [1. Who can use this, and on what](#1-who-can-use-this-and-on-what)
- [2. The job board — `GET /seller/jobs/`](#2-the-job-board-get-sellerjobs)
- [3. Job detail — `GET /seller/jobs/{id}/`](#3-job-detail-get-sellerjobsid)
- [4. Jobs I've bid on — `GET /seller/jobs/mine/`](#4-jobs-ive-bid-on-get-sellerjobsmine)
- [5. My bids — `GET /seller/bids/`, `GET /seller/bids/{id}/`](#5-my-bids-get-sellerbids-get-sellerbidsid)
- [6. Placing a bid — `POST /seller/jobs/{job_id}/bids/`](#6-placing-a-bid-post-sellerjobsjob_idbids)
- [7. Editing and cancelling a bid — `PATCH /seller/bids/{id}/`](#7-editing-and-cancelling-a-bid-patch-sellerbidsid)
- [8. What happens when a bid is accepted](#8-what-happens-when-a-bid-is-accepted)
- [9. Errors (cheat sheet)](#9-errors-cheat-sheet)
- [10. Not built yet](#10-not-built-yet)

---

## 1. Who can use this, and on what

Needs a seller who **can operate** (verified **and** active) — the usual `403`
otherwise:

- not approved yet: `{"detail": "Your seller application is not approved yet. You can only edit your profile until an admin approves it."}`
- locked: `{"detail": "Your seller account is locked. Contact support."}`

A job is never created or edited by a seller — only the buyer (or an admin) does that.
A seller only browses open jobs, bids, and manages their own bids. Another seller's bid
is `404`.

## 2. The job board — `GET /seller/jobs/`

Open jobs only (`status = open_for_bidding`), cursor-paginated (`next` / `previous`, no
`count`).

| Param | Meaning |
|---|---|
| `category` | id, exact match |
| `country`, `state`, `city`, `thana` | location filters |
| `price_type` | an active budget tier priced that way |
| `budget_min`, `budget_max` | against the cheapest active budget tier's price |
| `delivery_days_max` | |
| `urgent` | |
| `created_from`, `created_to` | creation date, inclusive |
| `requested_from`, `requested_to` | the date it joined the pending list |

```json
{ "id": 42, "title": "Need a plumber for bathroom pipe repair", "slug": "...",
  "category": { "...": "..." }, "status": "open_for_bidding", "budget": { "price": "1500.00", "price_type": "fixed" },
  "delivery_days": 1, "urgent": true, "bid_count": 2, "my_bid_count": 0, "created_at": "..." }
```

`budget` is the cheapest active budget tier's price and type. `bid_count` is every bid
on the job (any seller, any status); `my_bid_count` is this seller's own (any status).

## 3. Job detail — `GET /seller/jobs/{id}/`

Any `open_for_bidding` job, **or** a job this seller has placed a bid on regardless of
its current status (so a seller who already bid keeps seeing it after it closes) —
anything else is `404`. Same fields as the board row, plus `description`,
`package_includes`, `available_from` / `available_to`, `location`, and **`my_bids`**:
this seller's own bids on the job (any status), with their `price_tiers`.

## 4. Jobs I've bid on — `GET /seller/jobs/mine/`

Every job this seller has ever placed a bid on, any job status, same shape and filters
as the board, cursor-paged. Add **`?won=true`** to narrow it to only the jobs where
**this seller's own bid** is currently `accepted` or `completed` — the jobs this seller
actually got, not just bid on.

## 5. My bids — `GET /seller/bids/`, `GET /seller/bids/{id}/`

`GET /seller/bids/`: cursor-paginated, newest first, each row carrying a brief `job`
(`id`, `title`, `title_bn`, `slug`, `status`). Filters: `status`, `listing` (job id).
Search: `listing__title`.

```json
{ "id": 7, "job": { "id": 42, "title": "...", "status": "in_progress" }, "status": "accepted",
  "description": "...", "proposed_start": null, "proposed_end": null,
  "price_tiers": [ { "...": "..." } ], "accepted_price_tier": { "...": "..." }, "created_at": "...", "updated_at": "..." }
```

`GET /seller/bids/{id}/` adds `actual_start_date`, `actual_end_date`, `note`. Another
seller's bid is `404`.

## 6. Placing a bid — `POST /seller/jobs/{job_id}/bids/`

```json
POST /api/v1/seller/jobs/42/bids/
{ "description": "I can start tomorrow", "proposed_start": "2026-11-01T09:00:00Z", "proposed_end": "2026-11-01T17:00:00Z",
  "price_tiers": [ { "price_type": "fixed", "price": "1300" } ] }
```

A bid needs **at least one price tier** (`{"price_tiers": ["A bid needs at least one price option."]}`
with none). Two tiers with the same `price_type` in one request is `400`. The job must
be `open_for_bidding` (`400` "This job isn't open for bidding." otherwise). This seller
must have **no other live bid** (`pending` or `accepted`) on this job already (`400`
"You already have a live bid on this job."). `status` sent is ignored — always starts
`pending`. `201` returns the full bid.

Price tiers (`BidPriceTier`): `price_type` (`fixed`, `hourly`, `daily`, `weekly`,
`monthly`; optional, defaults to `fixed`), `price`, `duration` (forced to `1` when
`fixed`), `description`. `total_price` is read-only (`price × duration`).

## 7. Editing and cancelling a bid — `PATCH /seller/bids/{id}/`

Only while the bid is `pending` (`400` "This bid can no longer be edited." otherwise).
`description`, `proposed_start`, `proposed_end` change in place. `price_tiers`
**reconciles**, exactly like a gig's packages: an item with an `id` updates that tier
(only the fields sent change), an item without one adds a new tier, a tier not
mentioned is left alone (never auto-deleted).

```json
PATCH /api/v1/seller/bids/7/
{ "price_tiers": [ { "id": 12, "price": "1400" }, { "price_type": "hourly", "price": "200" } ] }
```

**Cancel**: `PATCH /seller/bids/{id}/` with `{"status": "cancelled"}` — the **only**
status move a seller can make directly. Any other value is `400` ("You can only cancel
a pending bid.") — acceptance and rejection are the buyer's/admin's call. After
cancelling, the seller may place a brand-new bid on the same job (a new historical row,
not a reuse of the old one) once no other live bid of theirs is blocking it.

## 8. What happens when a bid is accepted

Acceptance is the buyer's (or admin's) call, not the seller's. When the buyer accepts
one of this seller's bids:

1. That bid → `accepted`, `accepted_price_tier` set, `actual_start_date` stamped.
2. Every other **pending** bid this seller had on the same job → `rejected`.
3. The job → `in_progress`.
4. An **Order** is created directly for this seller — no cart involved; see the admin
   `orders` seller guide for what happens next.

If the buyer or an admin later **rejects an already-accepted bid** (undoing the hire,
not cancelling the job), that bid → `rejected` and its Order is cancelled; the job
reopens to `open_for_bidding` and this seller may place a fresh bid. If the **job
itself** is cancelled, every live bid of this seller's on it → `cancelled` (a bid that
had already lost earlier stays `rejected`). Full state machine:
[`../listing-complete-guide.md`](../listing-complete-guide.md) section 16.2.

## 9. Errors (cheat sheet)

| What went wrong | Response |
|---|---|
| no token / admin or buyer token | `401` / `403` |
| seller cannot operate (pending, rejected, paused) | `403` with the message in section 1 |
| no price tiers on a bid | `400` `{"price_tiers": ["A bid needs at least one price option."]}` |
| two tiers with the same `price_type` | `400` "Two tiers use the same price type (...)" |
| job not `open_for_bidding` | `400` "This job isn't open for bidding." |
| already have a live bid on this job | `400` "You already have a live bid on this job." |
| editing a non-pending bid | `400` "This bid can no longer be edited." |
| any `status` but `cancelled` sent by a seller | `400` `{"status": "You can only cancel a pending bid."}` |
| another seller's bid, or a job not open and not bid on by me | `404` |

## 10. Not built yet

- **Payment collection** (bKash) against a job's Order — a separate, later effort.
- **Commission** on a job Order (`commission_rate` / `commission_amount` stay `null`).
- Deliverables, messaging between buyer and seller, reviews/ratings on a completed job.
- A dedicated endpoint to list/read the Orders a job produced for this seller (the Order
  row exists and updates correctly — see the orders seller guide).
