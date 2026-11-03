# Brief for the Egoola Web session — admin Job & Bidding panel (new backend feature)

Backend done and tested in `egoola-server`: the admin panel for Jobs and Bidding. "Admin can do everything" here —
create or edit a job on any buyer's behalf, create or edit a bid on any seller's behalf, accept a bid on the
buyer's behalf, and undo an already-accepted hire. Read this file top to bottom, then build the two screens
(**Jobs**, **Bidding**) in **Admin Web**. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/admin/job-admin-guide.md` (the admin contract — read this one fully, the sections below
are a summary of it), `egoola-server/docs/listing-complete-guide.md` section 16 (the full state machine shared by
all three roles — read this for the "why", it has every case), `egoola-server/docs/Egoola_Listing_Guide.md`
section 13 (plain-language version, if anything below is unclear conceptually). Postman: `Egoola-Listing` →
**Jobs**, `Egoola` → **Bidding**. Run the backend with `uv run manage.py runserver 8000`; accounts in
`docs/test-accounts.md` (admin: `test.admin@egoola.com` / `Test@12345`).

---

## 1. What this is

A **job** is a buyer's request for work. Unlike a product or a gig, it is never moderated (no
pending/approved/rejected) — it's live the moment it's posted — and it's never bought outright: sellers place
**bids**, and someone (the buyer, or here, the admin) accepts one to hire them.

Two screens, both full CRUD (not read-only like Cart/Wishlist admin oversight):

1. **Jobs** (`/catalog/jobs/`) — every job, with the ability to create one on a buyer's behalf, edit one, and the
   one admin-only move: force-cancel a hired (`in_progress`) job with a mandatory reason.
2. **Bidding** (`/bidding/bids/`) — every bid, with the ability to create one on a seller's behalf, edit one, and
   two actions no one else has: `accept` (hire on the buyer's behalf) and `reject` (undo an already-accepted hire
   without cancelling the job).

**Pagination differs between the two.** The job panel is limit/offset, same as `/catalog/listings/` and
`/catalog/gigs/` (`count`/`next`/`previous`/`results`, reuse the existing page-based list pattern). The bid panel
is **cursor**-based (`next`/`previous`/`results`, no `count`) — same pattern as the Seller Request queue / Cart &
Wishlist oversight screens. Don't force one pagination pattern onto the other.

## 2. The contract

Header: `Authorization: Bearer <admin access token>` everywhere (plain admin or super-admin, no restriction).
`401` no token, `403` wrong role.

### Jobs — `/api/v1/catalog/jobs/...`

| Call | What it does |
|---|---|
| `POST /catalog/jobs/` | create **on a buyer's behalf** — `buyer` required |
| `GET /catalog/jobs/` | list. Filters: `status`, `category`, `buyer`, `created_from`/`created_to`, `requested_from`/`requested_to`. Search: title/description/buyer name/phone |
| `GET /catalog/jobs/{id}/` | detail |
| `PATCH`/`PUT /catalog/jobs/{id}/` | edit on the buyer's behalf, or move `status` |

No delete.

Write body: `category`, `title`, `description`, optional `title_bn`/`description_bn`, `delivery_days`, `urgent`,
`package_includes`(+`_bn`), `available_from`/`available_to`, `country`/`state`/`city`/`thana`, `status`, `note`,
and `skus` (the budget — array of `{id?, price_type?, price, description?, description_bn?}`, reconciled like a
gig's packages: an item with `id` updates, one without adds, one not mentioned is left alone, never auto-deleted).
`buyer` required on create only, never reassigned on update.

List/detail row (shortened):
```json
{ "id": 42, "title": "...", "slug": "...", "category": {"id":29,"name":"...","...": "..."},
  "buyer": {"id":4,"name":"Test Buyer","phone":"...","email":"..."},
  "status": "open_for_bidding", "budget": {"price":"1500.00","price_type":"fixed"}, "bid_count": 2,
  "delivery_days": 1, "urgent": true, "created_at": "...", "updated_at": "...",
  "description": "...", "location": {"country":null,"state":null,"city":null,"thana":null},
  "skus": [ {"id":101,"price_type":"fixed","price":"1500.00","...":"..."} ],
  "accepted_bid": null, "note": null }
```
`budget` = cheapest active budget tier. `accepted_bid` (detail only) = the bid currently hired, or `null`.

**Status moves** (send `{"status": "..."}` on `PATCH`):

| From | To | Note |
|---|---|---|
| `open_for_bidding` | `open_for_bidding` (edit fields), `draft`, `cancelled` | |
| `draft` | `draft`, `pending`, `cancelled` | not straight back to `open_for_bidding` |
| `pending` | `pending`, `open_for_bidding`, `cancelled` | |
| `in_progress` | `in_progress`, `completed` | every other field locked |
| `in_progress` | `cancelled` | **admin only**, mandatory `note` — `{"note": "A reason is required to cancel a hired job."}` without one |
| `completed`, `cancelled` | nothing | terminal |

Cancelling (from any state) cascades: every live bid on the job → `cancelled`, and if one was accepted, its Order
→ `cancelled` too. No UI action needed for that cascade — it just happens server-side; reflect the resulting
states if you show them.

### Bidding — `/api/v1/bidding/bids/...`

| Call | What it does |
|---|---|
| `POST /bidding/bids/` | create **on a seller's behalf** — `listing` (job id) and `bidder` (seller id) required |
| `GET /bidding/bids/` | list, cursor-paginated. Filters: `status`, `listing`, `bidder` |
| `GET /bidding/bids/{id}/` | detail |
| `PATCH /bidding/bids/{id}/` | edit on the seller's behalf — **only while `pending`** |
| `POST /bidding/bids/{id}/accept/` | accept on the buyer's behalf |
| `POST /bidding/bids/{id}/reject/` | undo an already-accepted hire |

No delete.

Write body (create/edit): `description`, `proposed_start`, `proposed_end`, `status` (edit only moves to
`cancelled`), `price_tiers` (array of `{id?, price_type?, price, duration?, description?}`, same reconcile rule as
job SKUs — `total_price = price × duration` is read-only, server-computed; `duration` forced to `1` when
`price_type = fixed`). At least one price tier required on create. `listing`/`bidder` required on create only.

List/detail row (shortened):
```json
{ "id": 7, "job": {"id":42,"title":"...","title_bn":null,"slug":"...","status":"open_for_bidding","buyer":4},
  "bidder": {"id":15,"name":"Karim Electric","phone":"..."},
  "status": "pending", "description": "...", "proposed_start": null, "proposed_end": null,
  "price_tiers": [ {"id":12,"price_type":"fixed","price":"1300.00","duration":1,"description":null,"total_price":"1300.00"} ],
  "accepted_price_tier": null, "created_at": "...", "updated_at": "...",
  "actual_start_date": null, "actual_end_date": null, "note": null }
```

**`accept`** — body `{"price_tier_id": <id>}`, required only when the bid has more than one price tier:
```json
{ "bid": {"id":7,"status":"accepted","accepted_price_tier":{"...":"..."},"...":"..."},
  "order": {"id":301,"status":"in_progress","payable":"1300.00"} }
```
Effect: that bid → `accepted`, every other pending bid on the same job → `rejected`, the job → `in_progress`, an
Order is created. Show the returned Order summary to the admin (id, payable) — there's no Order list/detail API
yet, so this response is the only place to see it right now.

**`reject`** — body `{"note": "..."}` (mandatory). Only works on a bid that's currently `accepted`:
```json
{ "id": 7, "status": "rejected", "note": "...", "accepted_price_tier": null, "...": "..." }
```
Effect: that bid → `rejected` (not `cancelled`), its Order → `cancelled`, the job → back to `open_for_bidding`.
Bids that lost earlier when this one was accepted **stay `rejected`** — don't expect them to come back to
`pending`.

### Errors (both screens)

| Case | Error |
|---|---|
| No `buyer` on job create | `{"buyer": "Say which buyer this job is for."}` |
| No `listing`/`bidder` on bid create | `{"listing": "Say which job this bid is for."}` / `{"bidder": "Say which seller this bid is for."}` |
| No budget/price tiers | `{"skus": "..."}` / `{"price_tiers": "A bid needs at least one price option."}` |
| Two tiers, same `price_type` | `"Two budget options use the same price type (...)"` / `"Two tiers use the same price type (...)"` |
| Job not `open_for_bidding` on bid create/accept | `"This job isn't open for bidding."` |
| Seller already has a live bid on this job | `"This seller already has a live bid on this job."` |
| Editing a non-pending bid | `"This bid can no longer be edited."` |
| Invalid job status move | `{"status": "Cannot move a job from '<from>' to '<to>'."}` |
| Admin cancels `in_progress` with no `note` | `{"note": "A reason is required to cancel a hired job."}` |
| Accepting a non-pending bid | `"Only a pending bid can be accepted."` |
| Multi-tier bid, no `price_tier_id` on accept | `{"price_tier_id": "This bid has more than one price option — say which one you're accepting."}` |
| Rejecting a non-accepted bid | `"Only an accepted bid can be rejected this way."` |
| No `note` on reject | `{"note": "A reason is required."}` |

## 3. Tasks

1. **Two API clients**: `admin-jobs-api.ts` (`listJobs`, `getJob`, `createJob`, `updateJob` — limit/offset) and
   `admin-bids-api.ts` (`listBids`, `getBid`, `createBid`, `updateBid`, `acceptBid`, `rejectBid` — cursor).
2. **Jobs list**: filter bar (status, category, buyer, date range, search), table (title, buyer, status, budget,
   bid count, created date), page-based paging. A "Create job" button opens a form with a **buyer picker** (reuse
   whatever buyer-lookup pattern Buyer Management already has) plus the same fields as a product/gig create form
   (category picker scoped to service categories, title/description + Bangla, delivery/urgent, budget tiers
   builder — same component as a gig's packages builder, minus stock/options).
3. **Job detail**: fields, budget tiers, `accepted_bid` summary if hired, status-change controls matching the
   table in section 2 (buttons/menu for the moves valid from the current status only — grey out invalid ones
   rather than letting the request fail), the `in_progress → cancelled` move behind a confirmation dialog that
   requires typing a reason (don't let it submit empty).
4. **Bidding list**: filter bar (status, job id, seller id — `listing`/`bidder` can be query-param-only, driven by
   navigating from a job's or seller's detail page), cursor "load more" list (job title, bidder, status, tiers
   summary, created date). A "Create bid" button: job picker (only open jobs make sense, but don't hard-block —
   let the server validate), seller picker, price-tier builder (reuse the same component as job budget tiers).
5. **Bid detail**: full fields, price tiers, an **Accept** button (if `pending`) that opens a tier picker dialog
   only when there's more than one tier, and a **Reject** button (if `accepted`) that requires a reason in a
   dialog, same pattern as the job cancel reason.
6. Cross-links: from a job's detail, list/link its bids (`?listing=<id>` on the Bidding list); from a bid's
   detail, link back to its job.
7. Entry points: add **Jobs** and **Bidding** to the admin nav, alongside the existing Listings/Gigs entries.

## 4. Verify (browser, admin role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Create a job without a buyer | `400`, field error shown under the buyer picker |
| 2 | Create a job for a buyer, one budget tier | `201`, shows `open_for_bidding` |
| 3 | Edit the job's title and add a second budget tier | saved, both tiers present, first one unchanged |
| 4 | Pause (`draft`), try to reopen straight to `open_for_bidding` | `400` — must go through `pending` first |
| 5 | Create a bid on that job for a seller, one tier | `201`, `pending` |
| 6 | Create a second bid for a different seller | `201` |
| 7 | Accept the first bid (single tier, no picker needed) | job → `in_progress`, the other bid → `rejected`, Order summary shown |
| 8 | Try to edit the job now | locked — only a status-based action available, not a free edit |
| 9 | Reject the accepted bid with a reason | bid → `rejected`, job → back to `open_for_bidding`, the second bid stays `rejected` (not reset to pending) |
| 10 | Accept a bid again, then force-cancel the job (`in_progress → cancelled`) without a reason | blocked client-side or `400` from the server |
| 11 | Same cancel, with a reason | `200`, the accepted bid shows `cancelled`, job shows `cancelled` |
| 12 | Create a bid with two price tiers, accept without picking one | prompted to pick; accepting picks the right tier |
| 13 | Filter the Bidding list by `listing=<job id>` | only that job's bids |
| 14 | A non-admin token (if testable from the UI) | handled the same way other admin screens reject it |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
