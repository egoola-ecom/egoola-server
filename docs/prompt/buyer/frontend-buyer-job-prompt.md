# Brief for the Egoola Web session — buyer Jobs (new backend feature)

Backend done and tested in `egoola-server`: a buyer posting a job and hiring a seller for it. Read this file top
to bottom, then build it in **Buyer Web**. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/buyer-api-guide.md` section 5 (the technical contract below is a copy of it),
`egoola-server/docs/listing-complete-guide.md` section 16 (the full state machine shared by all three roles — read
this for the "why", it has every case), `egoola-server/docs/Egoola_Listing_Guide.md` section 13 (plain-language
version, if anything below is unclear conceptually). Postman: `Egoola-BuyerApp` → **Jobs**. Run the backend with
`uv run manage.py runserver 8000`; accounts in `docs/test-accounts.md` (buyer: `test.buyer@egoola.com` /
`Test@12345`).

Needs a buyer token (`Authorization: Bearer <access>`, same as every other buyer call — see
`frontend-api-guide.md`). No token: `401`. A seller or admin token: `403`.

---

## 1. What this is

A **job** is different from browsing and buying a product or a gig (neither of which has checkout built yet
anyway): a buyer describes work they need done and a budget, sellers place **bids**, and the buyer picks one to
**hire**. There is no moderation step — the job is live the instant it's posted. Accepting a bid creates an
**Order directly** (no cart, no checkout flow to build here) and locks the job into `in_progress`.

Five things to build:
1. **Post a job** (and edit it while it's still open for bidding).
2. **My jobs** list + **detail**.
3. **Pause / reopen / cancel** a job.
4. **See the bids** on a job.
5. **Accept** a bid (hire that seller) and **mark complete** once the work is done.

Pagination is **page-based** here (`count`/`page`/`page_size`/`total_pages`/`results`), the same convention as
every other Buyer Panel list — not cursor-based like admin oversight screens.

## 2. The contract

| Call | What it does |
|---|---|
| `POST /buyer/jobs/` | post a job |
| `GET /buyer/jobs/` | my jobs. Filter: `status`. Search: title/description |
| `GET /buyer/jobs/{id}/` | detail |
| `PATCH`/`PUT /buyer/jobs/{id}/` | edit, or move `status` |
| `GET /buyer/jobs/{id}/bids/` | every bid on this job, any status, newest first (page-based) |
| `POST /buyer/jobs/{id}/bids/{bid_id}/accept/` | hire that bidder |

No delete — cancel instead.

### Post a job

```json
POST /buyer/jobs/
{ "category": 29, "title": "Need a plumber for bathroom pipe repair", "description": "Leaking pipe under the basin.",
  "urgent": true, "delivery_days": 1, "skus": [ { "price_type": "fixed", "price": "1500" } ] }
```

`category` (must be an **active service** category — picker should only offer service categories), `title`,
`description`, and **at least one budget option** (`skus`) are required. A budget option: `price_type` (optional,
one of `fixed`/`hourly`/`daily`/`weekly`/`monthly`, defaults to `fixed`), `price`, optional `description`/
`description_bn`. Two tiers with the same `price_type` is `400`. Optional: `title_bn`/`description_bn`,
`package_includes`(+`_bn`), `available_from`/`available_to`, `country`/`state`/`city`/`thana` (cascading, same
rule as everywhere: state belongs to country, city to state, thana to city).

`201` (shortened):
```json
{ "id": 42, "title": "...", "slug": "...", "category": {"id":29,"name":"...","...":"..."},
  "status": "open_for_bidding", "budget": {"price":"1500.00","price_type":"fixed"}, "bid_count": 0,
  "delivery_days": 1, "urgent": true, "created_at": "...", "updated_at": "...",
  "description": "...", "location": {"country":null,"state":null,"city":null,"thana":null},
  "skus": [ {"id":101,"price_type":"fixed","price":"1500.00","effective_price":"1500.00","is_active":true,"...":"..."} ],
  "accepted_bid": null, "note": null }
```
`budget` = the cheapest active budget tier's price/type, `null` if none active. `bid_count` = every bid ever
placed (any status). `accepted_bid` (detail only) = the currently hired bid, or `null`.

### Edit — budget tiers reconcile like a gig's packages

```json
PATCH /buyer/jobs/42/
{ "title": "Need a plumber — urgent", "skus": [ { "id": 101, "price": "1800" }, { "price_type": "hourly", "price": "400" } ] }
```
An item with `id` updates that tier (only fields sent change); one without adds a tier; a tier not mentioned is
left alone (never auto-deleted — there's no separate "remove one tier" call; hide one with `is_active: false` if
you need that, but it's rarely needed on a job's own budget).

### Status moves

| From | To | How |
|---|---|---|
| `open_for_bidding` | `draft` (pause), `cancelled` | `PATCH {"status": "draft"}` / `{"status": "cancelled"}` |
| `draft` | `pending` | `PATCH {"status": "pending"}` — **not** straight back to `open_for_bidding`, that's `400` |
| `pending` | `open_for_bidding` (reopen) | `PATCH {"status": "open_for_bidding"}` |
| `in_progress` | `completed` | `PATCH {"status": "completed"}` — the **only** field accepted in this request; anything else alongside it is `400` |

The buyer **cannot** cancel an `in_progress` (hired) job themselves — only an admin can, with a mandatory reason.
Don't show a cancel option once the job is hired; show "mark complete" instead.

Cancelling (any state before `in_progress`) takes every live bid on the job down as `cancelled` — this happens
server-side, no extra UI action needed, just reflect the resulting bid statuses if you show them.

### Bids on my job — `GET /buyer/jobs/{id}/bids/`

Every bid ever placed, any status, so the buyer sees the full history (lost bids included). `?status=pending`
filters.

```json
{ "count": 2, "page": 1, "page_size": 20, "total_pages": 1, "results": [
  { "id": 7, "bidder": {"id":15,"name":"Karim Electric","profile_pic_url":null}, "status": "pending",
    "accepted_price_tier": null, "created_at": "...", "description": "I can start tomorrow",
    "proposed_start": null, "proposed_end": null, "actual_start_date": null, "actual_end_date": null, "note": null,
    "price_tiers": [ {"id":12,"price_type":"fixed","price":"1300.00","duration":1,"description":null,"total_price":"1300.00"} ],
    "updated_at": "..." } ] }
```

### Accept a bid — `POST /buyer/jobs/{id}/bids/{bid_id}/accept/`

Body: `{"price_tier_id": 12}` — **required only when the bid quoted more than one price tier**; with a single
tier, omit it (auto-picked).

```json
{ "bid": {"id":7,"status":"accepted","accepted_price_tier":{"id":12,"...":"..."},"...":"..."},
  "order": {"id":301,"status":"in_progress","payable":"1300.00"} }
```

Effect: that bid → `accepted`, every other pending bid on the job → `rejected`, the job → `in_progress`, an Order
is created directly (no cart step to build — just show a confirmation with the order id/payable from this
response). There is no Order list/detail API yet, so this response is the only place this Order's details are
visible right now.

### Errors

| Case | Error |
|---|---|
| No budget on create | `{"skus": "A job needs at least one budget option."}` |
| Two tiers, same `price_type` | `"Two budget options use the same price type (...)"` |
| Category is a product category | `{"category": "A job needs a service category."}` |
| Editing a `completed`/`cancelled` job | `"This job can no longer be edited (it's completed or cancelled)."` |
| Invalid status move | `{"status": "Cannot move a job from '<from>' to '<to>'."}` |
| Any field but `status` while `in_progress` | `"This job has been hired — only an admin can edit it now (you may still mark it complete)."` |
| Job not `open_for_bidding` on accept | `"This job isn't open for bidding."` (checked before the bid id is even looked up) |
| Bid not `pending` on accept | `"Only a pending bid can be accepted."` |
| Multi-tier bid, no `price_tier_id` | `{"price_tier_id": "This bid has more than one price option — say which one you're accepting."}` |
| `price_tier_id` not on this bid | `{"price_tier_id": "Doesn't belong to this bid."}` |

## 3. Tasks

1. **API client**: `buyer-jobs-api.ts` — `listJobs`, `getJob`, `createJob`, `updateJob`, `listBids(jobId)`,
   `acceptBid(jobId, bidId, tierId?)`, page-based like the rest of the Buyer Panel.
2. **Post a job form**: service-category picker, title/description (+ Bangla fields, collapsible/optional),
   urgent toggle, delivery days, budget-tiers builder (one row per price type — reuse the gig-packages-style
   component if the web app already has one from the seller side; otherwise build a small repeatable
   price-type/price/description row group), location (optional cascading dropdowns).
3. **My jobs list**: filter by status, search, page-based "load more" or numbered pages (match the existing
   Buyer Panel list convention), card/row showing title, status badge, budget, bid count, created date.
4. **Job detail**: full fields, budget tiers, status badge, and a status-dependent action area:
   - `open_for_bidding`: Edit, Pause, Cancel.
   - `draft`: Edit, Reopen (via `pending` then `open_for_bidding` — do this as one user action with two requests,
     or whatever matches how you already model multi-step status flows elsewhere), Cancel.
   - `in_progress`: Mark Complete only (no edit, no cancel).
   - `completed`/`cancelled`: read-only.
5. **Bids tab/section on job detail**: list every bid (any status) with bidder name, status badge, price tiers,
   description, proposed dates. For each `pending` bid: an **Accept** button — if it has more than one price
   tier, open a tier picker first; otherwise accept immediately. Show a confirmation with the returned order info
   after accepting.
6. **Edit form**: same shape as create, pre-filled, budget-tiers builder in "reconcile" mode (existing tiers show
   their id and can be changed in place; a new row has no id).
7. Entry points: a "Jobs" or "Post a job" entry in the Buyer Panel nav, alongside Cart/Favourites.

## 4. Verify (browser, buyer role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Post a job with no budget | `400`, error shown under the budget section |
| 2 | Post a job with one budget tier | `201`, shows `open_for_bidding` immediately (no "pending review" state) |
| 3 | Edit the job, add a second budget tier | saved, both tiers shown, the first unchanged |
| 4 | Pause it (`draft`), try to edit a field | field edits still work in `draft` (only `in_progress` locks fields) |
| 5 | Reopen (`draft` → `pending` → `open_for_bidding`) | ends up `open_for_bidding` |
| 6 | Seller places a bid (use Postman/another session), buyer views the bids tab | bid shows, Accept button present |
| 7 | Accept a single-tier bid | job → `in_progress`, order confirmation shown, Accept/Edit/Cancel controls gone, only "Mark complete" left |
| 8 | A second bid that was pending at acceptance time | now shows `rejected` on the bids tab |
| 9 | Mark the job complete | job → `completed`, read-only |
| 10 | A job with two sellers' bids, cancel it before accepting any | every bid now shows `cancelled` (not `rejected`) |
| 11 | A bid with two price tiers — accept | prompted to choose a tier first; the chosen one shows as `accepted_price_tier` |
| 12 | Another buyer's job id (if reachable via URL) | `404`, handled gracefully |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
