# Egoola Cart & Wishlist Guide (in plain words)

This guide explains how a buyer's **cart** and **wishlist** work: what each one is, how it is created, how things go
in and come out of it, and what happens once it turns into an order. It has no technical terms and no mention of
any API — it describes the idea, not the code. For what happens after checkout (the order itself), see the
**Egoola Order Guide**.

The two are deliberately different ideas:

| | Cart | Wishlist |
|---|---|---|
| **What it means** | "I intend to buy this" | "I like this, remind me later" |
| **Holds** | A quantity or a duration, chosen on purpose | Nothing but the listing itself |
| **Leads to** | An order, once the buyer checks out | Nothing automatically — a buyer still has to add it to a cart to buy it |
| **How many a buyer has** | One per seller they're shopping with, per kind (see Part I, section 2) | One single list |

Part I covers the cart. Part II covers the wishlist.

---

# Part I — The cart

---

## Table of contents

- [1. What a cart is](#1-what-a-cart-is)
- [2. Carts never mix two kinds, or two sellers](#2-carts-never-mix-two-kinds-or-two-sellers)
- [3. How a cart comes to exist](#3-how-a-cart-comes-to-exist)
- [4. Adding something to the cart](#4-adding-something-to-the-cart)
- [5. What a line in the cart shows](#5-what-a-line-in-the-cart-shows)
- [6. Changing or removing something already in the cart](#6-changing-or-removing-something-already-in-the-cart)
- [7. What happens to a cart once an order is placed from it](#7-what-happens-to-a-cart-once-an-order-is-placed-from-it)
- [8. What the cart does not cover yet](#8-what-the-cart-does-not-cover-yet)
- [9. What a wishlist is](#9-what-a-wishlist-is)
- [10. Saving and un-saving something](#10-saving-and-un-saving-something)
- [11. What the wishlist shows, and what happens when things change](#11-what-the-wishlist-shows-and-what-happens-when-things-change)
- [12. The wishlist and the cart are not connected](#12-the-wishlist-and-the-cart-are-not-connected)

---

## 1. What a cart is

A cart is a holding area. Before a buyer commits to buying anything, they can drop things into their cart, look at
them together, change their mind about how many they want, and take things back out — all without anything being
bought yet. Nothing is final until checkout happens — see the **Egoola Order Guide** for what happens then.

A cart belongs to exactly one buyer. Nobody else can see it or touch it.

---

## 2. Carts never mix two kinds, or two sellers

Egoola sells two very different kinds of things, and a buyer's cart keeps them apart:

| Kind | What it holds | How it is priced |
|---|---|---|
| **Product cart** | Physical goods a seller sells (a shirt, a phone, a chair) | By quantity — 2 shirts, 5 phones |
| **Service cart** | A seller's gig (a service offer, like cleaning or design work) | By duration — 3 hours, 2 days, 1 week |

A buyer can have a product cart and a service cart **at the same time** — one with three things in it, and separately
a service cart with a cleaner they are about to hire. The two never sit together. The reason is simple: paying for a
product and paying to hire someone go through different payment paths behind the scenes, so keeping them apart from
the very start avoids a cart that cannot cleanly checkout as one thing.

**On top of that, a cart never holds more than one seller's things either.** If a buyer adds a shirt from one shop and
a phone from a different shop, those are two separate carts, even though both are plain products. This mirrors how
an order works: every order is always placed with exactly one seller, so a cart that mixed sellers could never
cleanly become a single order anyway. An item that an admin added directly (with no seller behind it at all) counts
as its own, single, shared "no seller" bucket, separate from every real seller's cart.

In practice this means a buyer shopping from three different sellers for products has **three separate product
carts** running at once, one per seller — not three items awkwardly sharing one cart, and not three unrelated
"baskets" with nothing in common except belonging to the same buyer.

A buyer never has to choose which cart something goes into, on either count — it is decided automatically by what
the thing itself is and who sells it. Adding a product from Seller A always lands in Seller A's product cart; adding
a gig from Seller B always lands in Seller B's own, separate service cart.

---

## 3. How a cart comes to exist

A buyer does not create a cart on purpose, and there is no empty cart waiting for them the moment they sign up.
The very first time a buyer adds something of a given kind **from a given seller**, a cart for that exact
combination is created for them automatically, right then. Adding something from a different seller — even of the
same kind — creates another, separate cart the same way.

Because a cart cannot exist until both the kind and the seller are known, there is no single "the buyer's cart" to
show before anything has been added. Looking for one that doesn't exist yet simply shows nothing, not an error and
not a placeholder cart waiting to be filled.

When a buyer just wants to see "my cart" without naming a seller — opening the cart icon from anywhere on the site,
say — they are shown whichever of their carts of that kind they were most recently doing something with: adding to
it, changing a quantity, or taking something out. Looking at one *specific* seller's cart on purpose (for example,
while on that seller's shop page or looking at one of their items) works the same way as always, named directly,
regardless of which cart was touched most recently.

---

## 4. Adding something to the cart

When a buyer adds a product or a gig to their cart, a few things are decided for them automatically:

- **Which cart it goes into** — the product cart or the service cart, based on what is being added.
- **What exact version of the listing** — a seller's listing can come in variations (a shirt in blue, size medium;
  a cleaning gig priced by the hour versus by the day). The buyer always picks the exact variation they want, not
  just the general listing.
- **How much of it** — for a product, how many. For a gig, how long (how many hours, days, weeks, or months of work).

Only things a buyer can actually see and buy can be added — an item that is not yet approved, belongs to a seller who
is not in good standing, or has nothing left to sell cannot be added to a cart, exactly the same as it would not show
up while browsing.

**Adding the same exact thing twice does not create two entries.** If a buyer adds 2 of a shirt and later adds 3 more
of that same exact shirt (same size, same colour), the cart does not end up with two separate lines — it combines
into one line of 5. The same happens for a gig: asking for 2 more hours of the same gig adds onto the hours already
in the cart, rather than listing it twice.

If there is only a limited amount of something left to sell, the cart will not let a buyer add more than is actually
available right now. This is just a check at the moment of adding — nothing is held back or reserved for the buyer
yet. Stock is checked again, for real, at the moment of checkout (see the **Egoola Order Guide**) — but even then
nothing is set aside ahead of time; it is simply re-checked against whatever is in stock right then.

---

## 5. What a line in the cart shows

Each thing sitting in the cart shows:

- what it is (its title, picture, and which listing it came from)
- the exact variation chosen (for example, "Blue, Medium")
- how many, or how long
- its price **right now** — worked out fresh every time the cart is looked at, including any sale that happens to be
  running at that moment
- the line's total (price times quantity, or rate times duration)
- whether it is still available to buy

That last point matters: time passes between adding something to a cart and actually checking out, and things can
change in the meantime — a seller might pause their shop, an item might sell out, or a seller might take a variation
off sale entirely. The cart does not silently remove a line when this happens. It keeps the line exactly as the buyer
left it, but marks it as no longer available, so the buyer can see and decide what to do about it themselves.

Nothing about price is locked in while it sits in the cart. The price shown is always today's price, worked out at
the moment someone looks at the cart — never a frozen snapshot from when the item was added. A price only truly
locks in once an order is placed.

---

## 6. Changing or removing something already in the cart

A buyer can:

- **Change how many, or how long** — update the quantity on a product line, or the duration on a gig line. This
  replaces the old value outright (going from 3 to 5 sets it to 5 — it does not add 5 more on top).
- **Remove one line entirely** — take one thing back out of the cart without touching anything else in it.
- **Empty a cart** — clear every line out of one seller's cart at once (naming the seller, or just "the one I was
  last doing something with"). The cart row itself is not thrown away; it is simply left empty, ready to be added to
  again.

A buyer can only ever change or remove their own cart's contents — never anyone else's.

---

## 7. What happens to a cart once an order is placed from it

This is the part that connects a cart to an order — see the **Egoola Order Guide** for everything about the order
itself (checkout, status, payment). A product cart and a service (gig) cart both become an order the exact same
way; the only difference is what kind of order comes out the other end.

A cart is meant to be used **once**. The moment everything in it is turned into an actual order — the buyer has
committed to buying and paying — that cart is considered closed. It is not emptied out and handed back for reuse.
Instead, it is kept exactly as it was, side by side with the order it produced, as a permanent record of what that
order was built from. A closed cart can always be looked back on later to see precisely what was in it when the
buyer checked out.

Because a closed cart is never reused, the next time that same buyer adds something of that same kind **from that
same seller**, a brand-new cart is created for them, starting empty, completely separate from the one that is now
closed and tied to a past order. (Their carts with other sellers, if they have any, are untouched the whole time —
each seller's cart closes into an order on its own, independently of the others.)

Put simply: a cart's life looks like this —

1. **Born** — created automatically the first time something is added to it.
2. **Lived in** — items are added, merged, changed, or removed, any number of times, in any order.
3. **Closed** — once an order is placed from it, it stops accepting changes and becomes a record of that order,
   forever.
4. A fresh cart of that same kind is born the next time it is needed, and the cycle repeats.

---

## 8. What the cart does not cover yet

- **Reserving stock ahead of checkout** — adding something to a cart only checks that enough is available at that
  moment; it does not hold or set aside stock for that buyer. Checkout re-checks it for real (see the **Egoola
  Order Guide**), but even that is a check at the moment of buying, not a reservation made in advance.

---

# Part II — The wishlist

---

## 9. What a wishlist is

A wishlist is a much simpler idea than a cart: it is a plain list of things a buyer likes and wants to find again
later, with no intention attached. Saving something to the wishlist does not mean the buyer is about to buy it, does
not reserve anything, and does not affect stock in any way. It is a bookmark, nothing more.

A buyer has **one single wishlist** — unlike the cart, it is not split into a product one and a service one. A
product and a gig can sit side by side in the same list, since there is no checkout or payment implication to keep
them apart for.

---

## 10. Saving and un-saving something

Saving something to the wishlist and taking it back off are both simple, reversible actions with no side effects:

- **Saving** something that is already on the list changes nothing — it does not appear twice, and nothing breaks if
  a buyer taps "save" on something they already saved.
- **Removing** something from the list is just as forgiving — removing something that was never saved, or that has
  already been removed, is not treated as a mistake. Either way, the buyer ends up with it off the list, which is
  all that matters.

Only things a buyer can actually see can be saved — exactly the same rule as the cart and ordinary browsing: an item
that is not yet approved, or belongs to a seller who is not in good standing, cannot be saved.

---

## 11. What the wishlist shows, and what happens when things change

Each saved thing shows the same card a buyer would see while browsing it normally — its title, picture, and current
price, worked out fresh each time, exactly like the cart. There is no quantity, no duration, and no line total, since
nothing has been committed to yet.

If something saved to the wishlist later becomes unavailable — the seller is no longer in good standing, or the
listing itself is taken down — it is **not deleted from the wishlist**. It simply stops showing up in the list for as
long as it stays unavailable, and comes back on its own the moment it is available again. This is different from how
the cart handles the same situation: a cart keeps an unavailable line visible but marked, because a buyer might still
want to deal with it (remove it, wait for it to come back); a wishlist item has nothing to "deal with" while it is
hidden, so it is simply set aside until it matters again.

---

## 12. The wishlist and the cart are not connected

Saving something to the wishlist never adds it to the cart, and nothing is removed from the wishlist just because it
was also added to the cart — a buyer might want both: keep an eye on something *and* be actively planning to buy it
right now. Moving something from "I like this" to "I'm buying this" is a decision the buyer makes on purpose, not
something that happens automatically between the two lists.
