# Egoola Cart Guide (in plain words)

This guide explains how a buyer's **cart** works: what it is, how it is created, how items go in and come out of it,
and what happens to it once it turns into an order. It has no technical terms and no mention of any API — it describes
the idea, not the code. Ordering and checkout themselves are not built yet; this guide only covers the cart that will
feed into them.

---

## 1. What a cart is

A cart is a holding area. Before a buyer commits to buying anything, they can drop things into their cart, look at
them together, change their mind about how many they want, and take things back out — all without anything being
bought yet. Nothing is final until checkout happens, and checkout is a separate step that has not been built.

A cart belongs to exactly one buyer. Nobody else can see it or touch it.

---

## 2. Two kinds of cart, never mixed

Egoola sells two very different kinds of things, and a buyer's cart keeps them apart:

| Kind | What it holds | How it is priced |
|---|---|---|
| **Product cart** | Physical goods a seller sells (a shirt, a phone, a chair) | By quantity — 2 shirts, 5 phones |
| **Service cart** | A seller's gig (a service offer, like cleaning or design work) | By duration — 3 hours, 2 days, 1 week |

A buyer can have **one of each at the same time** — a product cart with three things in it, and separately a service
cart with a cleaner they are about to hire. The two never sit in the same cart. The reason is simple: paying for a
product and paying to hire someone go through different payment paths behind the scenes, so keeping them apart from
the very start avoids a cart that cannot cleanly checkout as one thing.

A buyer never has to choose which cart something goes into — that is decided automatically by what the thing itself
is. Adding a product always lands in the product cart; adding a gig always lands in the service cart.

---

## 3. How a cart comes to exist

A buyer does not create a cart on purpose, and there is no empty cart waiting for them the moment they sign up.
The very first time a buyer adds something of a given kind (say, their first product), a cart of that kind is created
for them automatically, right then. If they later add their first gig, a separate service cart is created the same way.

Looking at an empty cart — one a buyer has never put anything into — behaves the same way: it simply comes back empty,
not missing. There is never a case where a buyer "doesn't have a cart" and gets stuck; one is always ready the moment
it is needed.

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
yet. That reservation only happens once an actual order is placed, which is a later step not built yet.

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
- **Empty the whole cart** — clear every line out at once. The cart itself is not thrown away when this happens; it
  is simply left empty, ready to be added to again.

A buyer can only ever change or remove their own cart's contents — never anyone else's.

---

## 7. What happens to a cart once an order is placed from it

This is the part that connects a cart to an order, even though ordering itself has not been built yet.

A cart is meant to be used **once**. The moment everything in it is turned into an actual order — the buyer has
committed to buying and paying — that cart is considered closed. It is not emptied out and handed back for reuse.
Instead, it is kept exactly as it was, side by side with the order it produced, as a permanent record of what that
order was built from. A closed cart can always be looked back on later to see precisely what was in it when the
buyer checked out.

Because a closed cart is never reused, the next time that same buyer adds something of that same kind (another
product, say), a brand-new cart is created for them, starting empty, completely separate from the one that is now
closed and tied to a past order.

Put simply: a cart's life looks like this —

1. **Born** — created automatically the first time something is added to it.
2. **Lived in** — items are added, merged, changed, or removed, any number of times, in any order.
3. **Closed** — once an order is placed from it, it stops accepting changes and becomes a record of that order,
   forever.
4. A fresh cart of that same kind is born the next time it is needed, and the cycle repeats.

---

## 8. What this guide does not cover yet

- **Checkout itself** — the step where a cart's contents actually turn into an order and a payment is taken. This is
  a future piece of work; this guide only describes the cart that will feed into it.
- **Reserving stock** — right now, adding something to a cart only checks that enough is available at that moment; it
  does not hold or set aside stock for that buyer. True reservation happens only once an order is placed.
- **Wishlist / favourites** — saving something to look at later, without the intent to buy it right now, is a
  separate idea from the cart and is covered elsewhere.
