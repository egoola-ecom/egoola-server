# Egoola Job Guide

**One guide for everyone.** This guide explains, in simple words, how a **job** works on Egoola: a buyer's request
for work that sellers compete for by **bidding** instead of buying anything outright. It covers the buyer's side,
the seller's side, the admin's side, and what happens the moment a bid is accepted.

It is written for all teams: operations, support, product, design, testing and development. You do not need any
technical knowledge to read it. For the technical reference (every API, every error, every field), see
[`listing-complete-guide.md`](listing-complete-guide.md) section 16, [`admin/job-admin-guide.md`](admin/job-admin-guide.md),
[`buyer/buyer-api-guide.md`](buyer/buyer-api-guide.md) section 5 and [`seller/seller-job-bidding-api-guide.md`](seller/seller-job-bidding-api-guide.md).

---

## Status flow (read this first)

A job has its own status, and every bid placed on it has its own status too. They move together, but they are
two separate things — keep both in mind while reading the rest of this guide.

### The job's own status

```
                 buyer pauses it
   Open for    ──────────────────▶   Draft
   Bidding     ◀──────────────────   (no new bids while paused)
   (live the        buyer reopens
   moment it's
   posted,              buyer asks to re-list it (same pause/reopen cycle, just the
   no approval          other direction — Draft and Pending are reused for this)
   needed)      ◀──────────────────   Pending
                 ──────────────────▶

   Open for Bidding / Draft / Pending  ──▶  Cancelled   (buyer, any time before a hire —
                                                          or admin, any time, reason required)

   Open for Bidding  ──▶  (a bid is accepted)  ──▶  In Progress  ──▶  Completed
                                                          │
                                                          └──▶  Cancelled   (admin only, reason required —
                                                                             a buyer cannot undo a hire themselves)
```

| From | Can move to | Who | Notes |
|---|---|---|---|
| *(created)* | Open for Bidding | buyer, or admin on their behalf | Always this status on creation — a job skips moderation entirely. |
| Open for Bidding | Draft | buyer (pause) | No new bids come in while paused. Bids already placed are untouched. |
| Draft | Pending | buyer (reopen, step 1) | Still not open to sellers yet. |
| Pending | Open for Bidding | buyer (reopen, step 2) | Open to sellers again. |
| Open for Bidding / Draft / Pending | Cancelled | buyer, or admin (reason required) | Takes every live bid down with it (see below). |
| Open for Bidding | In Progress | automatic, the moment a bid is **accepted** | Every other pending bid is rejected at the same instant. |
| In Progress | Completed | buyer, seller, or admin | Marks the hired bid, and the order it created, complete too. |
| In Progress | Cancelled | **admin only**, reason required | The only way to undo a job that's already been hired, short of the admin's bid-level `reject` (see below). |

### A bid's own status

| From | Can move to | Who | Notes |
|---|---|---|---|
| *(created)* | Pending | seller, or admin on their behalf | A bid always starts here. |
| Pending | Accepted | buyer, or admin (hiring this seller) | Creates an Order immediately — no cart step. |
| Pending | Rejected | automatic | Every other pending bid on the job when one is accepted. Not the seller's own doing. |
| Pending | Cancelled | seller (withdraws) | The seller may place a brand-new bid afterwards — a fresh row, not a reuse of the old one. |
| Accepted | Completed | automatic, when the job is marked Completed | |
| Accepted | Cancelled | automatic, if the job itself is cancelled | |
| Accepted | Rejected | **admin only** (`reject`, a note required) | Undoes the hire without cancelling the job — it reopens for other sellers. The bids that auto-rejected earlier stay rejected. |

A seller may have more than one bid on the same job **over time** (cancel one, place a new one later); what's
never allowed is **two live bids at once** (pending or accepted) from the same seller on the same job.

---

## Table of contents

- [1. The people in this guide](#1-the-people-in-this-guide)
- [2. What is a job?](#2-what-is-a-job)
- [3. Buyer: posting and managing a job](#3-buyer-posting-and-managing-a-job)
- [4. Seller: the job board and bidding](#4-seller-the-job-board-and-bidding)
- [5. Accepting a bid — what happens the instant it's hired](#5-accepting-a-bid--what-happens-the-instant-its-hired)
- [6. Admin: overseeing jobs and bids](#6-admin-overseeing-jobs-and-bids)
- [7. Quick rules (one page)](#7-quick-rules-one-page)
- [8. Questions we often get (for support and operations)](#8-questions-we-often-get-for-support-and-operations)
- [9. Not available yet](#9-not-available-yet)
- [10. Words used in this guide](#10-words-used-in-this-guide)

---

## 1. The people in this guide

| Who | What they do with jobs |
|---|---|
| **Buyer** | Posts a job describing work they need done and a budget, reviews the bids sellers place, and hires one. |
| **Seller** | Browses the open job board and places bids with their own price. Needs to be **Verified and Active** to bid. |
| **Admin** | Can do everything a buyer or a seller can, on their behalf, plus two things neither of them can do: undo an already-accepted hire, and cancel a job that's already in progress. |

## 2. What is a job?

A job is the mirror image of a gig. A **gig** is a seller offering a fixed service at a fixed rate; a **job** is a
**buyer** describing work they need and a budget, and letting **sellers compete for it by bidding**. The buyer (or
an admin on their behalf) picks one bid to hire. The two sides are then connected through an **order** right away
— there is no cart step, unlike buying a product or hiring a gig outright.

A job carries:

| Part | What it is |
|---|---|
| **Title and description** | The name and the details. Both can also be written in Bangla. |
| **Category** | Must be a **service** category, and it must be active. |
| **Budget** | What the buyer is willing to pay — the same price-type idea as a gig's packages (hourly, daily, weekly, monthly, or one fixed price), but this is the buyer's own number, not a seller's. At least one budget option is required. |
| **Place** | Country, state, city, thana (optional). |

Unlike a product or a gig, a job **skips moderation entirely** — there is no Pending → Approved → Rejected cycle.
It is live and open for bids the moment it's posted, by the buyer or by an admin on the buyer's behalf. A job also
never shows up in the product list or the gig list — it lives in its own place (**Jobs**) for every actor.

## 3. Buyer: posting and managing a job

1. The buyer opens **Jobs** and chooses **Post a job**.
2. They pick a **service category**, write the title and description, and set a **budget** (at least one price
   option — one amount per price type; two budget options with the same price type are refused).
3. They save. The job is live immediately, open for sellers to bid on — see the status flow above.
4. They can **edit** the job (most fields, any time it isn't yet hired), **pause** it, **reopen** it, or
   **cancel** it. Cancelling takes every live bid on it down too — see section 5.
5. They see every bid placed on their job, in any status, and **accept** the one they want to hire. If a bid
   quoted more than one price option, they say which one they're accepting.
6. Once a bid is accepted the job moves to **In Progress** and almost nothing about it can change any more — the
   one thing the buyer (or the seller, or an admin) can still do is mark it **Complete** once the work is done.

An admin can do every one of these steps **on a buyer's behalf** too (section 6).

## 4. Seller: the job board and bidding

**Who can bid?** Only a seller who is **Verified and Active**. Others see a clear message that says why.

1. The seller opens **Jobs** and browses the **board** — every job currently **Open for Bidding**, with filters
   (category, location, price type, budget range, delivery time, urgent, dates).
2. They open one and place a **bid**: their own price (one or more price options, the same price-type idea as a
   gig's packages), a short cover message, and optionally when they could start and finish.
3. A bid needs **at least one price option**, the job must be **Open for Bidding** (otherwise refused), and the
   seller must have **no other live bid** on it already — the board and the job detail both make this visible
   (`bid_count` for everyone, `my_bid_count` for this seller specifically).
4. While a bid is still **Pending**, the seller can **edit** it — the price options reconcile the same way a
   gig's packages do: an option sent with an `id` updates that one, a new one without an `id` is added, and one
   not mentioned at all is simply left alone — or **cancel** it, the only status move a seller can make directly.
5. After cancelling, the seller may place a **brand-new bid** on the same job — a fresh historical row, not a
   reuse of the old, cancelled one.
6. **My bids** lists every job they've bid on, any status. Adding `?won=true` narrows that list down to only the
   jobs where their own bid is currently **Accepted** or **Completed** — the jobs they actually got.
7. Deciding, accepting or rejecting a bid is never the seller's own call — that's the buyer's (or an admin's), as
   covered next.

## 5. Accepting a bid — what happens the instant it's hired

The moment the buyer (or an admin, on their behalf) accepts a bid, several things happen together, in one step:

- That bid moves to **Accepted**. If it quoted more than one price option, the one being accepted must be named.
- **Every other pending bid** on that same job is moved to **Rejected** automatically — not because anything was
  wrong with them, they simply lost to the winning bid.
- The **job itself** moves to **In Progress**. From this point almost nothing about the job can be edited any
  more — the only move left for a buyer, a seller or an admin is marking it **Completed**, and the only move left
  for an admin alone is cancelling it (with a reason).
- An **order is created immediately** to record the hire, built from the accepted bid's price — there is no cart
  step for a job, unlike buying a product. The buyer can see this order; its payable amount is the bid's total
  price.
- When the work is finished, marking the job **Completed** carries the hired bid and its order to **Completed**
  with it, in the same step.
- If the job is **cancelled** instead — by the buyer, before any hire, or by an admin, at any point, with a
  reason — every bid on it that's still **live** (pending or accepted) is moved to **Cancelled** too, and if one
  of them already had an order behind it, that order is cancelled as well. A bid that had already lost earlier
  (rejected) is left exactly as it was — nothing about it is restored or changed.
- An admin has one extra move nobody else has: **reject** an already-accepted bid without cancelling the whole
  job. The hired bid moves to **Rejected** (not cancelled — this one genuinely was judged, the other way), its
  order is cancelled, and the job reopens for bidding (back to **Open for Bidding**) so other sellers can still
  win it. Every bid that auto-rejected earlier when this one was first accepted **stays rejected** — only the one
  admin action undoes, nothing else moves.

## 6. Admin: overseeing jobs and bids

An admin can do absolutely everything a buyer or a seller can do, **on their behalf**:

- Create or edit a job for any buyer, including moving its status (pause, reopen, cancel, complete).
- Create or edit a bid for any seller, including cancelling it.
- Accept a bid on the buyer's behalf — the exact same cascade as section 5.

And two things **only** an admin can do:

- **Undo an already-accepted hire** (`reject`, a note required) without cancelling the whole job — see the last
  point of section 5.
- **Cancel a job that's already In Progress** (a reason is required) — a buyer cannot do this themselves once a
  job has been hired; this is the admin's safety valve for a hire gone wrong.

A job is never reachable through the product list (`/catalog/listings/`) or the gig list (`/catalog/gigs/`) —
only through its own place, **Jobs**, for every actor. Full technical reference:
[`admin/job-admin-guide.md`](admin/job-admin-guide.md).

---

## 7. Quick rules (one page)

| Topic | Rule |
|---|---|
| Who can post a job | Any buyer, or an admin on their behalf. |
| Moderation | **None.** A job is live the instant it's posted. |
| Category | Must be a **service** category, and active. |
| Budget | At least one price option; one per price type. |
| Who can bid | A seller who is **Verified and Active**, or an admin on their behalf. |
| Live bid limit | **One** per seller per job at a time (pending or accepted). Cancel first to bid again. |
| Bid price options | At least one; price options reconcile like a gig's packages on edit. |
| Editing a bid | Only while **Pending**. |
| Who decides | The **buyer**, or an admin on the buyer's behalf. Never the seller. |
| Accepting a bid | Auto-rejects every other pending bid; job → **In Progress**; an order is created with no cart. |
| Completing a job | Carries the hired bid and its order to **Completed** too. |
| Cancelling before a hire | The buyer (or an admin), any time. Takes every live bid down with it. |
| Cancelling after a hire | **Admin only**, reason required. |
| Undoing a hire without cancelling the job | **Admin only** (`reject` a bid), reason required. The job reopens. |
| Pausing / reopening | Buyer only; two-step (Open for Bidding ↔ Draft ↔ Pending). |
| Seller's own cancel move | Cancel a **pending** bid. Nothing else. |
| Visibility | A job never appears under products or gigs; it has its own place everywhere. |

---

## 8. Questions we often get (for support and operations)

**A buyer asks: "Why doesn't my job need approval like a listing?"**
That's by design — a job is a request for work, not something for sale that needs checking. It goes live the
moment it's posted.

**A seller says: "I cannot bid on this job."**
Either the job isn't **Open for Bidding** any more (it may already be hired, paused, or cancelled), or this
seller already has a **live** bid on it (pending or accepted) — they'd need to cancel it first. They also need to
be **Verified and Active**.

**A seller says: "I placed a bid but can't change the price now."**
A bid can only be edited while it's still **Pending**. Once it's accepted, rejected or cancelled, it's final —
cancel and place a fresh one if the job is still open.

**A buyer asks: "Can I take back a hire?"**
Not by themselves — once a bid is accepted the job is **In Progress** and almost nothing can change. Ask an
admin: they can either cancel the job outright (if work hasn't really started) or use the admin-only `reject` to
undo just the hire and reopen the job for other sellers, without cancelling it.

**A seller asks: "Why did my bid get rejected? I didn't do anything wrong."**
Most of the time this is the automatic kind: another seller's bid was accepted instead, so every other pending
bid — including theirs — moves to rejected. Nothing about their bid itself was judged.

**An admin asks: "What's the difference between rejecting a bid and cancelling a job?"**
Cancelling the **job** takes every live bid down with it (marked cancelled) and is something a buyer can also do
before any hire. Rejecting an **accepted bid** (admin only) undoes just that one hire — the job itself survives
and reopens for other sellers.

**A buyer asks: "Where's my order for this job?"**
The moment a bid is accepted, an order is created automatically — there's no separate checkout step for a job.
Open the job's detail to see the accepted bid; the order it created is attached to that hire.

**Does a buyer need a cart for a job?**
No. A job never goes through a cart — accepting a bid creates the order directly.

---

## 9. Not available yet

Please do not promise these to buyers or sellers yet.

- **Messages** (email, SMS or in-app) when a bid is accepted, rejected or a job's status changes.
- **Payment collection** against a job's order (the order exists; collecting money against it is not built —
  see the **Egoola Order Guide**).
- **Deliverables or messaging** between the buyer and the hired seller once work is underway.
- **Reviews or ratings** after a job is completed.
- **A seller withdrawing an already-accepted bid themselves** — only the buyer (or an admin, via accept/reject)
  moves a hire; a seller can only cancel a **pending** bid.
- **Reopening a cancelled job.** Cancelling is final; the buyer would post a new one.

---

## 10. Words used in this guide

| Word | Meaning |
|---|---|
| **Job** | Work a buyer asks for. Sellers bid on it; the buyer (or an admin) hires one. |
| **Bid** | A seller's offer on a job: their own price and message. |
| **Price option** | One way a bid (or a gig's package) is priced: a price type and an amount. A bid needs at least one. |
| **Price type** | What a price is for: hourly, daily, weekly, monthly or fixed. |
| **Live bid** | A bid that's still pending or already accepted — the thing that counts against the "one bid per seller per job" rule. |
| **The board** | The list of every job currently **Open for Bidding** that a seller can browse and bid on. |
| **My bids / my jobs** | A seller's own view of jobs they've bid on; `?won=true` narrows it to the ones they were hired for. |
| **Accept** | The buyer's (or admin's) decision to hire a particular bid. |
| **Reject (a bid, admin-only)** | Undoing an already-accepted hire without cancelling the job itself — the job reopens. |
| **Cancel (a job)** | Taking the whole job down, before or after a hire (after a hire, admin only) — every live bid falls with it. |
| **Order** | The record of the hire, created the instant a bid is accepted — no cart involved. See the Egoola Order Guide. |
| **Open for Bidding** | The job's "live, waiting for bids" status. |
| **Pause / reopen** | A buyer's own two-step way to temporarily take a job off the board and bring it back, without cancelling it. |
