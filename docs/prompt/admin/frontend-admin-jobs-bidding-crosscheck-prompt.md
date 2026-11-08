# Brief for the Egoola Web session — admin Jobs & Bidding panel (validate implementation)

Backend done and tested in `egoola-server`: Admin "can do everything" on **Jobs** (a buyer's work request, hired
through bidding) and **Bidding**. This brief is for **cross-checking an existing/in-progress Jobs & Bidding
screen**, not a from-scratch build — go through every section below against your implementation and report back
what matches, what doesn't, and why (a deliberate UI choice is fine, same as the earlier Products/Gigs briefs).

Read first: `egoola-server/docs/admin/job-admin-guide.md` (the admin contract — read fully, this brief summarizes
it), `egoola-server/docs/listing-complete-guide.md` section 16 (the full state machine shared by all three roles —
every error case), `egoola-server/docs/Egoola_Job_Guide.md` (plain-language version, has the full status-transition
table if anything below is unclear conceptually). Postman: `Egoola-Listing` collection → **Jobs** folder, `Egoola`
collection → **Bidding** folder. Run the backend with `uv run manage.py runserver 8000`; accounts in
`docs/test-accounts.md` (admin: `test.admin@egoola.com` / `Test@12345`).

---

## 1. What this is

A **job** is a buyer's request for work — unlike a product or a gig it is **never moderated** (no
pending/approved/rejected, live the instant it's posted) and **never bought outright**: sellers place **bids**, and
the buyer (or, here, the admin) accepts one to hire them. Two screens:

1. **Jobs** (`/catalog/jobs/`) — every job, create one on a buyer's behalf, edit one, the one admin-only move:
   force-cancel a hired (`in_progress`) job with a mandatory reason.
2. **Bidding** (`/bidding/bids/`) — every bid, create one on a seller's behalf, edit one, and two actions no one
   else has: `accept` (hire on the buyer's behalf) and `reject` (undo an already-accepted hire without cancelling
   the job).

**Pagination differs between the two** — don't let one screen's pattern leak into the other: Jobs is **page-based**
(`count`/`next`/`previous`/`results`, same as `/catalog/listings/` and `/catalog/gigs/`); Bidding is **cursor**-based
(`next`/`previous`/`results`, no `count`, same as the Seller Request queue / Cart & Wishlist oversight).

A job id is `404` on `/catalog/listings/` and `/catalog/gigs/`; posting `posted_by_role: "buyer_request"` to either
is `400`.

## 2. The contract

Header: `Authorization: Bearer <admin access token>` (plain admin or super-admin, no restriction). `401` no token,
`403` wrong role.

### Jobs — `/api/v1/catalog/jobs/...`

| Call | What it does |
|---|---|
| `POST /catalog/jobs/` | create **on a buyer's behalf** — `buyer` required. Always starts `open_for_bidding`; a `status` sent is ignored |
| `GET /catalog/jobs/` | list, page-based. Filters: `status`, `category`, `buyer`, `created_from`/`created_to`, `requested_from`/`requested_to`. Search: title/title_bn/description/buyer name/phone. Ordering: `created_at`/`updated_at`/`id` |
| `GET /catalog/jobs/{id}/` | detail |
| `PATCH`/`PUT /catalog/jobs/{id}/` | edit on the buyer's behalf, and/or move `status` (same call) |

No delete — a job is cancelled, never removed.

Row/detail shape (shortened):
```json
{ "id": 42, "title": "...", "slug": "...", "category": {"id":29,"name":"...","...": "..."},
  "buyer": {"id":4,"name":"Test Buyer","phone":"...","email":"..."},
  "status": "open_for_bidding", "budget": {"price":"1500.00","price_type":"fixed"}, "bid_count": 2,
  "delivery_days": 1, "urgent": true, "description": "...",
  "location": {"country":null,"state":null,"city":null,"thana":null},
  "skus": [ {"id":101,"price_type":"fixed","price":"1500.00","...":"..."} ],
  "accepted_bid": null, "note": null, "created_at": "...", "updated_at": "..." }
```
`budget` = cheapest active budget tier. `accepted_bid` (detail only) = the bid currently hired, or `null`.
`buyer` is a brief (`id`/`name`/`phone`/`email`) — the admin view needs it, a buyer's own `/buyer/jobs/` doesn't.

**Status moves** (`{"status": "..."}` on `PATCH`):

| From | To | Note |
|---|---|---|
| `open_for_bidding` | `open_for_bidding` (edit fields), `draft`, `cancelled` | |
| `draft` | `draft`, `pending`, `cancelled` | **not** straight back to `open_for_bidding` — must pass through `pending` first |
| `pending` | `pending`, `open_for_bidding`, `cancelled` | |
| `in_progress` | `in_progress`, `completed` | every other field locked |
| `in_progress` | `cancelled` | **admin only**, mandatory `note` — `{"note": "A reason is required to cancel a hired job."}` without one. A buyer can never make this move |
| `completed`, `cancelled` | nothing | terminal |

`open_for_bidding → in_progress` never happens through `PATCH` — only automatically, when a bid is accepted.
Cancelling (from any state) cascades: every live bid → `cancelled`, and if one was accepted, its Order →
`cancelled` too — no separate UI action needed, just reflect the resulting states if you show them.

### Bidding — `/api/v1/bidding/bids/...`

| Call | What it does |
|---|---|
| `POST /bidding/bids/` | create **on a seller's behalf** — `listing` (job id), `bidder` (seller id) required |
| `GET /bidding/bids/` | list, cursor-paginated. Filters: `status`, `listing`, `bidder` |
| `GET /bidding/bids/{id}/` | detail |
| `PATCH /bidding/bids/{id}/` | edit on the seller's behalf — **only while `pending`** (`400` "This bid can no longer be edited." otherwise). The only `status` move through plain `PATCH` here is `cancelled` — use `accept`/`reject` below for the others |
| `POST /bidding/bids/{id}/accept/` | accept on the buyer's behalf |
| `POST /bidding/bids/{id}/reject/` | undo an already-accepted hire |

No delete — a bid only ever changes status.

Row/detail shape (shortened):
```json
{ "id": 7, "job": {"id":42,"title":"...","title_bn":null,"slug":"...","status":"open_for_bidding","buyer":4},
  "bidder": {"id":15,"name":"Karim Electric","phone":"..."},
  "status": "pending", "description": "...", "proposed_start": null, "proposed_end": null,
  "price_tiers": [ {"id":12,"price_type":"fixed","price":"1300.00","duration":1,"description":null,"total_price":"1300.00"} ],
  "accepted_price_tier": null, "created_at": "...", "updated_at": "...",
  "actual_start_date": null, "actual_end_date": null, "note": null }
```
`price_tiers` reconcile the same way as job SKUs (`id` present → edit, absent → add, omitted → untouched);
`total_price = price × duration` is read-only; `duration` forced to `1` when `price_type = fixed`. At least one
tier required on create. `listing`/`bidder` required on create only, never reassigned on update.

**`accept`** — body `{"price_tier_id": <id>}`, required only when the bid has more than one tier:
```json
{ "bid": {"id":7,"status":"accepted","accepted_price_tier":{"...":"..."},"...":"..."},
  "order": {"id":301,"status":"in_progress","payable":"1300.00"} }
```
Effect: that bid → `accepted`, every other pending bid on the job → `rejected`, job → `in_progress`, an Order
created directly (no cart). **There is no Order list/detail API yet** — this response is the only place to see it.

**`reject`** — body `{"note": "..."}` mandatory. Only works on a currently `accepted` bid:
```json
{ "id": 7, "status": "rejected", "note": "...", "accepted_price_tier": null, "...": "..." }
```
Effect: that bid → `rejected` (**not** `cancelled` — it was judged, just the other way), its Order → `cancelled`,
job → back to `open_for_bidding`. Bids that lost earlier when this one was first accepted **stay `rejected`** —
don't expect them to return to `pending`.

**Use which action, when:**

| You want to... | Use |
|---|---|
| Hire a bidder | `POST /bidding/bids/{id}/accept/` |
| Undo a hire, job stays open for other sellers | `POST /bidding/bids/{id}/reject/` |
| Kill the job entirely, no more bidding | `PATCH /catalog/jobs/{id}/` `{"status": "cancelled", "note": "..."}` |

### Errors (both screens)

| Case | Error |
|---|---|
| No `buyer` on job create | `{"buyer": "Say which buyer this job is for."}` |
| No `listing`/`bidder` on bid create | `{"listing": "Say which job this bid is for."}` / `{"bidder": "Say which seller this bid is for."}` |
| No budget/price tiers | `{"skus": [...]}` / `{"price_tiers": "A bid needs at least one price option."}` |
| Two tiers, same `price_type` | `"Two budget options use the same price type (...)"` / `"Two tiers use the same price type (...)"` |
| Job not `open_for_bidding` on bid create/accept | `"This job isn't open for bidding."` |
| Seller already has a live bid on this job | `"This seller already has a live bid on this job."` |
| Editing a non-pending bid | `"This bid can no longer be edited."` |
| Invalid job status move | `{"status": "Cannot move a job from '<from>' to '<to>'."}` |
| `draft → open_for_bidding` directly | `400` — must go through `pending` |
| Admin cancels `in_progress` with no `note` | `{"note": "A reason is required to cancel a hired job."}` |
| Accepting a non-pending bid | `"Only a pending bid can be accepted."` |
| Multi-tier bid, no `price_tier_id` on accept | `{"price_tier_id": "This bid has more than one price option — say which one you're accepting."}` |
| A `price_tier_id` that isn't one of that bid's tiers | `400` |
| Rejecting a non-accepted bid | `"Only an accepted bid can be rejected this way."` |
| No `note` on reject | `{"note": "A reason is required."}` |
| Unknown job/bid id | `404` |
| Job/gig id on the wrong screen | `404` |

## 3. Cross-check tasks

1. **API clients** — does `admin-jobs-api` have `listJobs`/`getJob`/`createJob`/`updateJob` (page-based), and
   `admin-bids-api` have `listBids`/`getBid`/`createBid`/`updateBid`/`acceptBid`/`rejectBid` (cursor)? Function
   names don't need to match these exactly — just confirm every call exists.
2. **Jobs list** — filter bar (status, category, buyer, date range, search), table (title, buyer, status, budget,
   bid count, created/requested date), page-based paging, "Create job" with a buyer picker + the same fields as a
   product/gig create form (service-category picker, title/description + Bangla, delivery/urgent, budget-tiers
   builder reusing the gig packages component minus stock/options).
3. **Job detail** — fields, budget tiers, `accepted_bid` summary if hired, status-change controls that only offer
   the moves valid from the current status (grey out the rest rather than letting the request fail), the
   `in_progress → cancelled` move behind a confirmation dialog that **requires typing a reason** (don't let it
   submit empty).
4. **Bidding list** — filter bar (status, job id, seller id — can be query-param-only, driven by navigating from a
   job's/seller's detail page), cursor "load more" (job title, bidder, status, tiers summary, created date),
   "Create bid" (job picker, seller picker, price-tier builder — same component as job budget tiers).
5. **Bid detail** — full fields, price tiers, **Accept** (if `pending`) opening a tier picker only when >1 tier,
   **Reject** (if `accepted`) requiring a reason in a dialog, same pattern as the job cancel dialog.
6. **Cross-links** — job detail lists/links its bids (`?listing=<id>` on the Bidding list); bid detail links back
   to its job.
7. **Entry points** — **Jobs** and **Bidding** in the admin nav, alongside Products/Gigs.
8. **Order visibility** — since there's no Order list/detail API yet, confirm the UI surfaces the Order summary
   from the `accept` response at the moment of hiring (id, payable) rather than expecting to fetch it later.

## 4. Verify (browser, admin role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Create a job without a buyer | `400`, field error under the buyer picker |
| 2 | Create a job for a buyer, one budget tier | `201`, shows `open_for_bidding` |
| 3 | Edit the job's title, add a second budget tier | saved, both tiers present, first unchanged |
| 4 | Pause (`draft`), try to reopen straight to `open_for_bidding` | `400` — must go through `pending` first |
| 5 | Create a bid on that job for a seller, one tier | `201`, `pending` |
| 6 | Create a second bid for a different seller | `201` |
| 7 | Accept the first bid (single tier, no picker needed) | job → `in_progress`, the other bid → `rejected`, Order summary shown |
| 8 | Try to edit the job now | locked — only a status-based action available, not a free edit |
| 9 | Reject the accepted bid with a reason | bid → `rejected`, job → back to `open_for_bidding`, the second bid stays `rejected` (not reset to pending) |
| 10 | Accept a bid again, force-cancel the job (`in_progress → cancelled`) with no reason | blocked client-side or `400` from the server |
| 11 | Same cancel, with a reason | `200`, the accepted bid shows `cancelled`, job shows `cancelled` |
| 12 | Create a bid with two price tiers, accept without picking one | prompted to pick; accepting then picks the right tier |
| 13 | Filter the Bidding list by `listing=<job id>` | only that job's bids |
| 14 | Try editing a bid that's already `accepted`/`rejected`/`cancelled` | blocked client-side, or `400` "This bid can no longer be edited." |
| 15 | A non-admin token (if testable from the UI) | handled the same way other admin screens reject it |

Report which cases pass, what you changed, and anything in `job-admin-guide.md` or this brief that looked wrong,
missing, or unclear once you tried it against the real API.
