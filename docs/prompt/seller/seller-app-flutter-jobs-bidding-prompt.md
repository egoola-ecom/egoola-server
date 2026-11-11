# Brief for the Egoola Seller App session (Flutter) — Jobs & Bidding (new backend feature)

Target app: **`egoola-seller`** (Flutter, the seller mobile app). This extends the app built by the earlier
"build every seller feature" prompt (auth, profile, products, gigs, files — already shipped and working). Backend
(`egoola-server`, Django REST) is done and tested: the seller's job board and bidding. Build it following the
exact same stack, repository pattern and conventions the app already uses — **do not** introduce a second pattern.

**Out of scope** (not built on the backend yet): accepting/rejecting your own bid (that's the buyer's/admin's
call), orders, deliverables, messaging, wallet and withdrawals, push notifications for a new job matching your
filters.

Do not push to any remote. Commit locally only when asked. Do not change `egoola-server`; if the contract looks
wrong or something is missing, stop and report it.

## 0. Read first (in this order)

1. This file.
2. `egoola-server/docs/seller/seller-job-bidding-api-guide.md` — the seller contract (summarized below, read the full
   guide for anything ambiguous).
3. `egoola-server/docs/listing-complete-guide.md` section 16 — the full state machine shared by all three roles
   (buyer, seller, admin). Read 16.2 ("every case"), 16.3 (bid statuses), 16.4 (price tiers), 16.8–16.9 (the
   seller endpoints in full depth).
4. `egoola-server/docs/Egoola_Listing_Guide.md` section 13 — plain-language version, if anything is unclear
   conceptually.
5. `egoola-seller/PHASES.md` (your own checklist) and `egoola-document/Egoola_Phase_Tracker.md` (Seller App rows).
   Update `PHASES.md` as work lands.
6. Test accounts: `egoola-server/docs/test-accounts.md` (seller: phone `0100000002`, password `Test@12345` — must
   be **verified and active** to use this feature; check that account's state first, or use/approve a fresh one).
   Postman (use it to see real responses): `egoola-server/postman/seller/Egoola-SellerApp.postman_collection.json` →
   **Seller jobs & bidding** folder, with `Egoola-Local.postman_environment.json`.

## 1. What this is

A **job** is a buyer's request for work. A seller does not buy or accept it directly — they **bid** on it with
their own price, and the buyer (or an admin) picks a winner. Four things to build:

1. **Job board** — browse every job currently open for bids, with filters.
2. **Job detail** — full info, plus this seller's own bids on it.
3. **My bids** — every bid this seller has placed, any status, and a "my jobs" view narrowed to the ones actually
   won.
4. **Place / edit / cancel a bid.**

**Pagination differs from everything else you've built.** Products and gigs use limit/offset
(`count`/`next`/`previous`/`results`). **The job board and my-bids list use cursor pagination**
(`next`/`previous`/`results`, **no `count`**) — the same shape the admin Seller Request queue uses on the web
side. Build (or reuse, if you already have one) a cursor-based infinite-scroll list controller distinct from
whatever `count`-driven pager you built for products/gigs; do not try to compute a page count from a cursor
response, there isn't one.

## 2. The contract

Needs a seller token, and the seller must be **verified and active** ("can operate") — the usual `403` with a
message saying which switch is holding them back otherwise (same pattern as products/gigs). No token `401`.

| Call | What it does |
|---|---|
| `GET /seller/jobs/` | the job board: open jobs only, cursor-paged |
| `GET /seller/jobs/{id}/` | detail (any open job, or one I've bid on even after it closes) |
| `GET /seller/jobs/mine/` | jobs I've bid on, any status. `?won=true` → only jobs I actually got (my bid `accepted`/`completed`) |
| `POST /seller/jobs/{job_id}/bids/` | place a bid |
| `GET /seller/bids/` | my bids, cursor-paged, job summary embedded |
| `GET /seller/bids/{id}/` | one bid |
| `PATCH /seller/bids/{id}/` | edit while `pending`, or cancel |

No delete anywhere — a bid is never removed, only its status changes.

### Job board — `GET /seller/jobs/`

Filters: `category`, `country`/`state`/`city`/`thana`, `price_type` (an active budget tier priced that way),
`budget_min`/`budget_max` (against the cheapest active tier), `delivery_days_max`, `urgent`, `created_from`/
`created_to`, `requested_from`/`requested_to`.

```json
{ "id": 42, "title": "Need a plumber for bathroom pipe repair", "slug": "...",
  "category": {"...":"..."}, "status": "open_for_bidding", "budget": {"price":"1500.00","price_type":"fixed"},
  "delivery_days": 1, "urgent": true, "bid_count": 2, "my_bid_count": 0, "created_at": "..." }
```
`bid_count` = every bid on it (any seller). `my_bid_count` = this seller's own bids on it (any status) — show
this as a small "you've bid X times" indicator on the card.

### Job detail — `GET /seller/jobs/{id}/`

Adds `description`, `package_includes`, `available_from`/`available_to`, `location`, and **`my_bids`**: this
seller's own bids on the job (any status), each with its `price_tiers`. Show these inline rather than making the
seller cross-reference the separate My Bids list.

### My bids — `GET /seller/jobs/mine/` and `GET /seller/bids/`

`/seller/jobs/mine/` returns **jobs** (same shape as the board), for a job-centric "jobs I'm involved in" tab.
`?won=true` narrows it to only jobs where this seller's bid is currently `accepted` or `completed` — use this for
a "My Jobs" (won) tab, separate from a general "My Bids" (everything, win or lose) tab.

`/seller/bids/` returns **bids** (bid-centric), for a "did I bid on this, what did I say" view:
```json
{ "id": 7, "job": {"id":42,"title":"...","status":"in_progress"}, "status": "accepted",
  "description": "...", "proposed_start": null, "proposed_end": null,
  "price_tiers": [{"...":"..."}], "accepted_price_tier": {"...":"..."}, "created_at": "...", "updated_at": "..." }
```
Filters: `status`, `listing` (job id). `GET /seller/bids/{id}/` adds `actual_start_date`, `actual_end_date`,
`note`.

Build **both**: My Bids (full history, bid-centric, from `/seller/bids/`) and My Jobs / Won (job-centric,
`/seller/jobs/mine/?won=true`) as two distinct tabs/screens — they answer different questions and the backend
gives you both shapes on purpose.

### Place a bid — `POST /seller/jobs/{job_id}/bids/`

```json
{ "description": "I can start tomorrow", "proposed_start": "2026-11-01T09:00:00Z", "proposed_end": "2026-11-01T17:00:00Z",
  "price_tiers": [ { "price_type": "fixed", "price": "1300" } ] }
```
At least one price tier required (`price_type` optional per tier, defaults to `fixed`; `price`; optional
`duration` meaningless for `fixed`, meaningful for the others; optional `description`). Two tiers with the same
`price_type` in one request is `400`. The job must be `open_for_bidding`. This seller must have **no other live
bid** (`pending` or `accepted`) on this job already. `201` returns the full bid.

### Edit / cancel — `PATCH /seller/bids/{id}/`

Only while `pending`. `description`/`proposed_start`/`proposed_end` change in place. `price_tiers` **reconciles**
like a gig's packages: an item with `id` updates that tier, one without adds a tier, a tier not mentioned is left
alone (never auto-deleted). The **only** status move a seller can make is `{"status": "cancelled"}` — anything
else here is `400`. After cancelling, the seller can place a brand-new bid on the same job (a new row, not a
reuse of the cancelled one) once no other live bid blocks it.

### Errors

| Case | Error |
|---|---|
| Unverified/inactive seller | `403`, `detail` message says which switch is off — same pattern as products/gigs |
| No price tiers | `{"price_tiers": "A bid needs at least one price option."}` |
| Two tiers, same `price_type` | `"Two tiers use the same price type (...)"` |
| Job not `open_for_bidding` | `"This job isn't open for bidding."` |
| Already have a live bid on this job | `"You already have a live bid on this job."` |
| Editing a non-pending bid | `"This bid can no longer be edited."` |
| Any status but `cancelled` on edit | `{"status": "You can only cancel a pending bid."}` |
| Another seller's bid/job-you-never-bid-on-and-it's-closed | `404` |

## 3. Tasks

1. **Repositories**: `JobsRepository` (`board(filters, cursor)`, `detail(id)`, `mine(cursor, won)`) and
   `BidsRepository` (`myBids(filters, cursor)`, `detail(id)`, `create(jobId, body)`, `update(id, body)`,
   `cancel(id)`), same `Api...Repository` + abstract-class pattern as the existing features. Money stays
   `String`, same rule as everywhere else in this app.
2. **Job board screen**: filter sheet (category, location, price type, budget range, urgent, delivery days),
   infinite-scroll list (cursor, not page-number), card per job (title, budget, delivery/urgent badges, bid
   count, your-bid-count indicator).
3. **Job detail screen**: full fields, your own bids on it inline (status, tiers, description), a "Place a bid"
   CTA when you have no live bid on it and it's open, hidden/disabled otherwise with the reason shown (already
   bid, job closed).
4. **Bid form** (place or edit): description, optional proposed start/end date-time pickers, a repeatable
   price-tier row group (price type dropdown, price, optional duration shown only for non-fixed types, optional
   description) — reuse the gig-packages form component if you already built one, same reconcile semantics
   (existing tiers carry their id when editing).
5. **My Bids screen**: cursor list from `/seller/bids/`, filter by status, each row → bid detail (job name,
   status, tiers, cancel button if `pending`).
6. **My Jobs (Won) screen**: cursor list from `/seller/jobs/mine/?won=true`, same job-card style as the board.
   Also add a plain "My Jobs" / "All my activity" tab using `/seller/jobs/mine/` with no `won` filter, if your nav
   has room for both — otherwise a toggle/segment on one screen between "All" and "Won" is fine.
7. Entry point: a **Jobs** tab/section in the seller app nav, alongside Products and Gigs.

## 4. Verify (device/emulator, verified+active seller role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Open the job board as a pending/unverified seller | `403`, clear message, no board shown |
| 2 | Open the board as a verified+active seller | open jobs listed, cursor "load more" works |
| 3 | Filter by category / budget range / urgent | list narrows correctly |
| 4 | Open a job with no bid of mine yet | "Place a bid" available |
| 5 | Place a bid, one tier | `201`, shows pending on the job detail and in My Bids |
| 6 | Try to place a second bid on the same job | blocked client-side or `400` from the server |
| 7 | Edit the bid: change the price, add a second tier | both tiers shown, original unchanged except the price |
| 8 | Cancel the bid | status → `cancelled`, "Place a bid" available again |
| 9 | Place a fresh bid on the same job after cancelling | `201`, a **new** bid row (My Bids shows 2 historical rows for this job) |
| 10 | Have a job accepted elsewhere (admin/buyer side) for one of your bids | it shows up under My Jobs (Won); My Bids shows that bid as `accepted`/`completed` |
| 11 | Open a job that closed after you bid but you never won it | still reachable from My Bids / job detail (not `404`), shows the job's final status |
| 12 | A job you never bid on, once it's closed | `404` |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
