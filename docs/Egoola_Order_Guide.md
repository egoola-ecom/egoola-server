# Egoola Order Guide

**One guide for everyone.** This guide explains, in simple words, everything about an **order** on Egoola: how a
buyer turns a cart into one, how a seller moves it along, how money and payment status are tracked, what an
admin can see and override, and what a **Payment Gateway** is. It is written for all teams: operations, support,
product, design, testing and development. You do not need any technical knowledge to read it.

For technical details (API addresses, request/response shapes), see
[`buyer/buyer-order-api-guide.md`](buyer/buyer-order-api-guide.md), [`seller/seller-order-api-guide.md`](seller/seller-order-api-guide.md),
[`admin/admin-order-api-guide.md`](admin/admin-order-api-guide.md) and [`admin/admin-payment-gateway-api-guide.md`](admin/admin-payment-gateway-api-guide.md).
For how a cart is built up before checkout, see [`Egoola_Cart_Guide.md`](Egoola_Cart_Guide.md). For a job's own
order (created directly when a bid is accepted — no cart, no checkout step), see the **Egoola Job Guide**.

---

## Status flow (read this first)

Every order carries **two** statuses that move side by side but are not the same thing: the **order status**
(where the parcel actually is) and the **payment status** (where the money stands). Keep both in mind.

### The order's own status

```
   pending ──────────────▶ accepted ──────────────▶ in_progress ──────────────▶ shipped ──────────────▶ delivered
      │                        │                         │
      │ seller, reason          │                                buyer may cancel from any of these three
      ▼ required                │◀────────────────────────────────────── (any time before "shipped")
   rejected                     ▼
                           cancelled

   Admin: can move an order to ANY of the above statuses, from ANY status, at ANY time — no restriction.
```

| From | Can move to | Who | Notes |
|---|---|---|---|
| *(created at checkout)* | pending | — | Always the starting status. |
| pending | accepted | seller | The seller is agreeing to fulfil the order. |
| pending | rejected | seller | **A reason is required** — the buyer sees it. |
| accepted | in_progress | seller | The seller is now preparing it. |
| in_progress | shipped | seller | On its way. |
| shipped | delivered | seller | The parcel has arrived. Also flips the **payment** to `paid` — see below. |
| pending / accepted / in_progress | cancelled | **buyer** | The buyer's own move — any time **before** it's shipped. An optional reason may be given. |
| *(any status)* | *(any status)* | **admin** | No restriction at all — admin can jump an order anywhere, backwards or forwards, at any time. |

A seller moves an order **one step at a time** — there is no skipping from `pending` straight to `shipped`, for
example. A buyer's cancel window closes the moment the seller marks it `shipped`. Admin has none of these limits.

### The payment's own status

| Status | Meaning |
|---|---|
| **due** | Money is owed and not yet collected. Every order starts here (only Cash on Delivery exists today). |
| **initiated** | A real gateway (not COD) has started a payment session that hasn't confirmed yet. |
| **paid** | The money has been collected in full. |
| **failed** | A real gateway's attempt did not go through. |
| **cancelled** | The payment itself was called off (distinct from the order being cancelled). |
| **partially_paid** | Part of the amount has been collected (a real gateway's `store_amount` tracks how much). |

**The one automatic link between the two:** the moment an order reaches **delivered** (by the seller's own
step-by-step move, or by an admin's override), if its payment is still `due`, the payment flips straight to
`paid` — on the Payment record itself and on the order's own `payment_status` copy of it, together, in the same
step. Nothing else moves the payment automatically today; every other payment-status value exists for a future
real gateway (bKash, say) to use.

---

## Table of contents

- [1. The people in this guide](#1-the-people-in-this-guide)
- [2. What is an order?](#2-what-is-an-order)
- [3. Payment Gateways](#3-payment-gateways)
- [4. How an order comes to exist (checkout)](#4-how-an-order-comes-to-exist-checkout)
- [5. Buyer: addresses, checkout, and my orders](#5-buyer-addresses-checkout-and-my-orders)
- [6. Seller: orders placed with me](#6-seller-orders-placed-with-me)
- [7. Admin: full oversight](#7-admin-full-oversight)
- [8. The money on an order](#8-the-money-on-an-order)
- [9. Payment, and its own history](#9-payment-and-its-own-history)
- [10. The order's own history](#10-the-orders-own-history)
- [11. Quick rules (one page)](#11-quick-rules-one-page)
- [12. Questions we often get (for support and operations)](#12-questions-we-often-get-for-support-and-operations)
- [13. Not available yet](#13-not-available-yet)
- [14. Words used in this guide](#14-words-used-in-this-guide)

---

## 1. The people in this guide

| Who | What they do with orders |
|---|---|
| **Buyer** | Saves delivery addresses, checks out a cart into an order, watches it move, and can cancel it before it ships. |
| **Seller** | Sees every order placed against their shop, moves it forward step by step (accept, reject, prepare, ship, deliver). |
| **Admin** | Manages the Payment Gateways sellers and buyers can use, and has full oversight of every order — can view everything and move any order to any status, at any time, no restriction. |

## 2. What is an order?

An order is what a cart becomes the moment a buyer checks out. It is the one record that ties together: who
bought it (the buyer), who it was bought from (the seller — an order always belongs to exactly one seller), what
was bought (its **order items**, a snapshot of each product line at the moment of purchase), where it's going
(a snapshotted delivery **address**), and how it's being paid for (its **Payment**).

An order is always exactly **one seller's** order — a buyer shopping from three different sellers in one visit
ends up with three separate carts and, after checking out each one, three separate orders. This guide covers a
**product** order (the kind built from a cart). A **job**'s order is a different animal — created the instant a
bid is accepted, with no cart involved at all — see the Egoola Job Guide.

## 3. Payment Gateways

A **Payment Gateway** is simply a way a buyer can pay — today there's exactly one, **Cash on Delivery**, created
for the whole platform ahead of time (no buyer or seller ever creates one). An admin manages the full list:

- **Name** — what it's called ("Cash on Delivery", "bKash", ...).
- **Slug** — a short, URL-safe version of the name, always generated by the system from the name; nobody ever
  types a slug in directly, and it regenerates automatically if the name is ever changed.
- **Icon** — an optional picture shown next to the gateway's name in the app.
- **Active** — whether buyers can pick it at checkout right now. Turning a gateway off doesn't touch any order
  already placed with it; it only stops it being offered for new ones.

An admin can **create**, **rename** (re-uploading the icon too, if wanted), **turn on/off**, or **delete** a
gateway (list page only — there's no separate "view one gateway" screen, the list already shows everything there
is). See [`admin/admin-payment-gateway-api-guide.md`](admin/admin-payment-gateway-api-guide.md) for the full technical
reference.

## 4. How an order comes to exist (checkout)

Checkout is **one single action**: the buyer picks (1) which of their active carts they're checking out, (2)
which of their saved addresses it should ship to, and (3) which Payment Gateway they're paying with. That one
action, behind the scenes, does all of the following together:

1. Creates the **Order** itself (status `pending`), copying the cart's seller onto it.
2. Creates one **OrderItem** per line in the cart, each one a frozen snapshot of that product's title and price
   at this exact moment — later price changes on the product never reach back and change a past order.
3. Snapshots the chosen address onto a brand-new **Address** row attached to this order — editing or deleting
   the buyer's saved address afterwards never changes what a past order actually shipped to.
4. Creates the **Payment** for the order, status `due`, remembering which gateway was used (both the live link
   to it and a frozen copy of its name and slug, for the same "later changes shouldn't rewrite history" reason).
5. Writes the **opening row** of both history tables — the order's own status history (nothing → `pending`) and
   the payment's own status history (nothing → `due`) — so every order's full story starts from a real,
   timestamped row, not an assumption.
6. Closes the **cart** it was built from. A closed cart is never reused or reopened; adding the same product to
   the same seller's cart again afterwards simply starts a brand-new cart.

A cart can only be checked out once (it's closed immediately after), and only by the buyer it belongs to. A cart
that holds only **admin-owned listings** (no seller at all) cannot be checked out yet — every order needs
exactly one seller.

## 5. Buyer: addresses, checkout, and my orders

**Addresses.** Before checking out for the first time, a buyer saves at least one delivery address: a name,
phone, the full country/state/city/thana location, and the street address itself. These are kept in a simple
list — add, see the list, edit one, or delete one. A buyer only ever sees and touches their **own** addresses.

**Checkout.** With at least one active cart and one saved address, the buyer checks out (section 4). The
response is the full order — seller, every item, the address it's shipping to, and the brand-new Payment, all in
one place.

**My orders.** A buyer's own order list shows every order they've ever placed, newest first, with normal paging
(a page number and a page size — not the "infinite scroll" style the seller and admin lists use). Opening one
shows the full detail: the seller, every item, the address, the **Payment** (with its own status and its own
status history nested right inside it), and the order's **own** status history.

**Cancelling.** For now, a buyer's only move on an existing order is to cancel it — any time before the seller
marks it `shipped`. There's no separate "cancel" button/action behind the scenes; it's the same general "change
this order" request every actor uses, just that a buyer is currently only allowed to send it one value
(`cancelled`). More moves may be opened up to buyers later without changing how this works.

## 6. Seller: orders placed with me

A seller's own order list shows every order placed against their shop — this list grows over time, so it scrolls
rather than pages, the same style used for the Seller Request queue. It can be filtered by status and by a date
range, and searched by the buyer's name, phone or email.

Opening one order shows the buyer, every item, the address, and the Payment with its history — the same rich
detail a buyer or an admin sees. From there the seller moves the order forward **one step at a time**: `pending`
→ `accepted` (or `rejected`, with a required, buyer-visible reason) → `in_progress` → `shipped` → `delivered`.
Trying to skip a step, or move a terminal order (`rejected`, `cancelled`, or already `delivered`) anywhere, is
refused with a clear message. Marking an order `delivered` also flips its payment from `due` to `paid`
automatically — the seller doesn't do anything extra for that; it just happens as part of the same move.

## 7. Admin: full oversight

An admin sees **every** order on the platform — the same scrollable, filterable, searchable list style as the
seller's, just not limited to one shop. Filters include the buyer, the seller, the status, the order type, and a
date range. Opening one shows absolutely everything: buyer, seller, every item, the address, the Payment and
both histories, plus the usual audit columns (who created it, who last touched it).

The one thing that makes the admin's view different from the seller's: **an admin can move an order to any
status, from any status, at any time** — forwards, backwards, it doesn't matter. There's no step-by-step
restriction the way there is for a seller. This is the safety valve for fixing a mistake, handling a dispute, or
any case that doesn't fit the normal flow. Moving an order to `delivered` this way flips its payment to `paid`
exactly the same as it would for the seller's own move.

Admin also runs the **Payment Gateway** list end to end (section 3) — nothing a buyer or seller does ever
touches that list.

## 8. The money on an order

Every order carries five money fields, and every one of them is stored and calculated to exactly **two decimal
places** — never rounded with a shortcut like "round down" or "round up", always the normal nearest-value
rounding:

| Field | What it is |
|---|---|
| **Total** | The sum of every item's price **before** any discount — the main, full price times the quantity, added up across every line. |
| **Subtotal** | The sum of every item's price **after** any discount currently running on it — the price actually charged, times the quantity, added up across every line. |
| **Discount** | An extra, order-level discount on top of the item-level ones above (a coupon, say) — `0` today, since coupons aren't built yet. |
| **Delivery cost** | What shipping costs — `0` today, since delivery pricing isn't built yet. |
| **Payable** | What the buyer actually owes: subtotal + delivery cost − discount. Right now, since the last two are always `0`, this is simply the subtotal. |

Each **order item** carries the same idea at the line level: its own `total` (main price × quantity) and
`subtotal` (discounted price × quantity, or the same as total if nothing's discounted). The order's total and
subtotal are exactly the sum of its items' totals and subtotals — nothing extra is added at the order level
today.

## 9. Payment, and its own history

Every order has exactly **one** Payment record (more could exist for other kinds of money movement in the
future — a seller payout, say — but an order's checkout payment is always the one row tied to that order). It
carries:

| Field | What it is |
|---|---|
| **Amount** | What's owed — the order's `payable`. |
| **Store amount** | How much a real gateway (bKash, for instance) reports as actually collected — unused for Cash on Delivery. |
| **Status** | `due`, `initiated`, `paid`, `failed`, `cancelled` or `partially_paid` — see the status flow at the top. |
| **Method / gateway / gateway slug** | Which Payment Gateway was used, both as a live link and as a frozen snapshot of its name and slug at the time. |
| **Notes** | Free-text notes against the payment, if any. |

Every time the Payment's status changes — at creation, and on the automatic `due` → `paid` flip when the order's
delivered — a row is written to its own, permanent **status history**. That history is never edited or deleted;
it's the one true record of exactly when, by whom, and from what to what the payment moved. It's always shown
nested right inside the Payment in every order's detail view, for all three actors.

## 10. The order's own history

Separately from the payment's history, the **order itself** keeps a full, permanent history of every status
move it's ever made — the opening `pending` row at checkout, and one more row for every single move after that
(accept, reject, ship, deliver, cancel, any admin override). Each row remembers the status it moved **from**, the
status it moved **to**, who made the move, and — for a reject or a cancel — the **reason given at that exact
moment**. That last part matters: the order's own `rejected_reason`/`cancelled_reason` fields only ever hold the
*latest* reason, but the history keeps every one, forever, exactly as it was given.

This history is also always shown in every order's detail view, for the buyer, the seller and the admin alike.

---

## 11. Quick rules (one page)

| Topic | Rule |
|---|---|
| One order, one seller | Always — a multi-seller cart basket simply doesn't exist; it's several carts, several orders. |
| Checkout | One action: cart + address + payment gateway → order + items + payment, all at once. |
| A cart with no seller | **Cannot** be checked out (admin-owned listings only). |
| A cart used once | Checking it out closes it; it can never be reused. |
| Order status start | Always `pending`. |
| Seller's moves | One step at a time: accepted/rejected → in_progress → shipped → delivered. |
| Reject | **Reason required**, buyer-visible. Only from `pending`. |
| Buyer's cancel | Any time **before** `shipped`. Optional reason. |
| Admin's moves | **Any** status, from **any** status, at **any** time. No restriction. |
| Delivered | Also flips payment `due` → `paid`, automatically, in the same step. |
| Payment status start | Always `due` (Cash on Delivery is the only gateway today). |
| Money rounding | Always to 2 decimal places, normal rounding — never floor/ceil. |
| Payable (today) | Equals the subtotal — delivery cost and discount are both `0` until those features are built. |
| Order item snapshot | Title and price are frozen at checkout — a later product-price change never rewrites a past order. |
| Address snapshot | A fresh copy is made at checkout — editing/deleting the saved address later never changes a past order. |
| Order history | Every status move, forever, with the reason given at that moment. Never edited or deleted. |
| Payment history | Every payment-status move, forever. Never edited or deleted. |
| Payment Gateway CRUD | Admin only. `slug` is always system-generated, never typed in. |
| Deactivated gateway | Can no longer be picked at checkout; existing orders using it are untouched. |

---

## 12. Questions we often get (for support and operations)

**A buyer asks: "Why can't I check out this cart?"**
Either it isn't theirs, it's already been checked out before (carts are one-time use), it's empty, something in
it is no longer available, or — rarer — it's a cart of admin-owned listings with no seller, which can't be
checked out yet.

**A seller asks: "Why can't I mark this order as shipped?"**
A seller moves an order **one step at a time** — it has to already be `in_progress` before it can become
`shipped`. If it's still `pending` or `accepted`, do those moves first.

**A seller asks: "The buyer wants to cancel, but I don't see a cancel button."**
Cancelling before it ships is the **buyer's own** move, not the seller's. If it's already past `shipped`, it's
too late for the buyer to self-cancel — an admin can still override the status if there's a genuine reason to.

**A buyer asks: "Can I cancel after it's shipped?"**
Not themselves — the window closes the moment the seller marks it shipped. Contact support; an admin can move
the order's status directly if the situation calls for it.

**An admin asks: "Can I really move an order backwards, like from delivered back to pending?"**
Yes — admin has no restriction at all on order-status moves, in either direction. Use this only when it's
genuinely warranted (fixing a mistake, a dispute); every move is still permanently recorded in the order's
history either way.

**Why did the payment status change to "paid" on its own?**
The moment any actor (seller or admin) marks an order `delivered`, its payment automatically flips from `due` to
`paid` — this is the one thing that happens by itself, with no extra step. If the payment had already moved to
something other than `due` by the time this happens, nothing changes.

**A buyer asks: "Where did my delivery address info for this order go after I deleted the saved address?"**
Nowhere — the order kept its own frozen copy of the address from the moment of checkout. Deleting (or editing)
the saved address in the address book never touches orders already placed with it.

**Why does an order's total and subtotal look the same right now?**
Because there's no discount or delivery cost in the system yet — both are `0`, so `payable` always equals the
`subtotal`. Once discounts and real delivery pricing exist, the two will start to differ.

**Where do I see why an order was rejected or cancelled?**
The order's own `rejected_reason`/`cancelled_reason` field shows the **latest** reason; the order's full status
history shows the reason given at **every single** reject/cancel that's ever happened to it, in order.

**Does a buyer need to create a new Payment Gateway to use Cash on Delivery?**
No — Cash on Delivery already exists, created ahead of time for the whole platform. A buyer just picks it by id
at checkout; nobody creates gateways except an admin.

---

## 13. Not available yet

Please do not promise these to buyers, sellers or admins yet.

- **Any payment gateway other than Cash on Delivery** (bKash and similar are the reason `store_amount` and the
  `initiated`/`failed`/`partially_paid` payment statuses already exist in the schema — the gateways themselves
  aren't wired up yet).
- **Coupons or any order-level discount** (`discount` exists on the order and is always `0` for now).
- **Real delivery-cost pricing** (`delivery_cost` exists and is always `0` for now).
- **Commission** (`commission_rate`/`commission_amount` exist on the order and stay `null` until the financial
  oversight feature is built).
- **Refunds.**
- **A seller checking out as a buyer from another seller's shop** (discussed, deliberately deferred — see the
  `buyer_type` flag already sitting, unused, on the cart).
- **Messages** (email, SMS or in-app) when an order's status or payment status changes.
- **Reviews or ratings** after delivery.
- **An admin manually editing the payment status directly** (today it only ever moves automatically, on
  delivery, or as a side effect of a future gateway integration).

---

## 14. Words used in this guide

| Word | Meaning |
|---|---|
| **Order** | The record of a purchase — created from a cart at checkout, or directly when a job's bid is accepted. |
| **Order item** | One line of an order — a frozen snapshot of one product's title, price and quantity at checkout. |
| **Payment** | The one money record tied to an order: how much, by which gateway, and its own status. |
| **Payment Gateway** | A way to pay (Cash on Delivery today). Admin-managed; a buyer just picks one by id. |
| **Payment status** | Separate from the order's own status — tracks the money (`due`, `paid`, and so on). |
| **Due** | The payment's starting status: owed, not yet collected. |
| **Paid** | The payment has been collected in full — happens automatically the moment the order is delivered. |
| **Store amount** | How much a real gateway reports as actually collected — for a future gateway, unused today. |
| **Address snapshot** | A frozen copy of the delivery address, made at checkout, independent of the buyer's saved address book afterwards. |
| **Checkout** | The one action that turns a cart into an order, its items, and its payment, together. |
| **Order status history** | The permanent, append-only record of every status move an order has ever made. |
| **Payment status history** | The same idea, for the payment's own status moves. |
| **Payable** | What the buyer actually owes: subtotal + delivery cost − discount. |
| **Subtotal** | The sum of every item's price **after** discount. |
| **Total** | The sum of every item's price **before** discount. |
