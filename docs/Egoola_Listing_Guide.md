# Egoola Listing Guide

**One guide for everyone.** This guide explains, in simple words, how listings work on Egoola: what a listing is,
how a seller creates one, how an admin checks it, what happens when it is rejected, and what each person can and
cannot do.

> **Products, gigs and jobs are separate kinds.** Sections 1–11 describe **products** and the rules every listing shares (statuses, checking,
> history, the thumbnail); those rules apply to gigs too. **Section 12 covers gigs** (work a seller offers): their own place, screens and price
> rules. A **job** (work a buyer asks for) is managed by admins for now.

It is written for all teams: operations, support, product, design, testing and development. You do not need any
technical knowledge to read it.

This guide does **not** explain technical details such as API addresses or the database. Each team has its own
document for that (see the documentation index, `docs/README.md`). For the seller's own side of things (sign-up,
verification, login), read the **Egoola Seller Guide**.

---

## 1. The people in this guide

| Who | What they do with listings |
|---|---|
| **Seller** | Creates and manages their own products. Can create, change, see and search them. Cannot delete them. |
| **Admin** | Checks the products sellers create (approve or reject). Can also create, change and delete any product, for a seller or for nobody. |
| **Buyer** | Will browse and buy from approved listings (the buyer side is not built yet). |
| **Operations / support team** | Helps sellers and admins. Uses the admin panel. |

---

## 2. What is a listing?

A **listing** is one thing for sale. Egoola uses **one** kind of form for every product format.
The old app had separate, repeated screens for each format. Now every format uses the same form.

**Product, gig and job**

- A **product** is a thing you can touch and ship. It lives under **Listings** (Product is chosen by default).
- A **gig** is work a seller offers (cleaning, photography, repair). It lives under **Gigs** (Service is chosen by default), with its own
  screens and price rules (packages with a price type). See section 12.
- A **job** is work a buyer asks for. Admins manage it for now.

Each place only accepts its own kind: a gig never shows in the product list, and a service cannot be created from the product form.

**The six product formats** (called the *listing type*): General, Used, Village, Retail, Wholesale, and Brand.
A Brand listing must have a brand chosen.

**A listing holds:**

| Part | What it is |
|---|---|
| **Title and description** | The name and the details. Both can also be written in **Bangla**. |
| **Category** | Where it belongs, for example Electronics. Must be a **product** category and must be active. |
| **Brand, model, origin, warranty** | Extra facts for products. Origin and warranty can also be written in Bangla. |
| **Condition note** (used products) | A note about the condition. Can also be written in Bangla. |
| **Options (sizes, colours...)** | A product can come in options. Each combination (for example Size M + Colour Black) has its **own price, discount period and stock**. A simple product has just one. |
| **Quantity prices** (wholesale) | A cheaper price when someone buys more, for example 1 to 9 pieces at 100 and 10 or more at 90. |
| **Thumbnail** | One cover picture for lists. Added on its own (section 4.1). |
| **Photos and files** | The gallery: pictures or other files that show the listing. |
| **Place** | Country, state, city, thana (optional). |

A product does **not** have the gig parts (price type, package descriptions, delivery days, "urgent", availability dates). These
are refused with a clear message.

**Bangla versions.** Five texts of a product can be written in Bangla as well: title, description, condition note, warranty and origin.
They are all optional. (A gig also has "package includes" in Bangla.)

---

## 3. The status of a listing

Every listing has a **status**. It says where the listing is in the checking process.

| Status | What it means |
|---|---|
| **Pending** | Waiting for an admin to check it. |
| **Approved** | An admin said yes. Buyers will be able to see it. |
| **Rejected** | An admin said no. A reason is always given. |
| **Changes requested** | An admin asks the seller to change something. A reason is always given. |
| **Draft** | "Not sent yet". Sellers do not use it: a seller's new listing goes straight to Pending. |

Who sets the status:

- **A seller never sets the status.** A new listing a seller creates is always **Pending**.
- **An admin sets the status.** A listing an admin creates is **Approved** straight away (the admin can choose another
  status if they want).

---

## 4. Seller: creating a listing

**Who can create?** Only a seller who is **Verified and Active** (see the Seller Guide). A seller who is still being
checked, was rejected, or is paused can only edit their profile. They see a clear message that says why.

**Steps**

1. The seller opens **Listings** and chooses "Create listing". (Services are created under **Gigs**, see section 12.)
2. They choose the **listing type** (for products), the **category**, and a **brand** if needed.
3. They write the **title** and **description** (and the Bangla versions if they want).
4. They fill the details: model, origin, warranty, condition.
5. They set the **price and stock**. If the product has options (sizes, colours), they add each combination with
   its own price, discount and stock.
6. They add **quantity prices** (wholesale) and **photos** if they want.
7. They save. The listing is created as **Pending** and is owned by the seller.
8. They add the **thumbnail** (section 4.1) and more photos if they want. These are separate steps after saving.

The seller picks categories, brands, measurements and options from lists that show only **active** items.

**What the seller cannot do when creating:** choose the owner, choose the status, create a service (that is a gig) or create a buyer's
request. The listing is always theirs and always Pending.

### 4.1 The thumbnail and the photos

A **thumbnail** is the one cover picture of a product (or a gig), shown in lists. It is different from the **gallery** (more pictures, videos, PDFs).

- Saving a product or gig (create or change) sends **text only**. Pictures and videos go through their own step, after the product is saved: **add files** (first time) and **change files** (replace or remove).
- **Add files:** a thumbnail and/or any number of gallery files. Both are optional; sending nothing is fine.
- **Change files:** remove the thumbnail, send a new thumbnail (it **replaces** the old one, even if "remove" is not ticked), remove some gallery files, add new ones. Each part works on its own.
- Thumbnail: **JPG, PNG or WEBP**, up to **10 MB**. Gallery: JPG, PNG, WEBP, GIF, MP4 or PDF; a seller is limited to 10 MB per file, 10 per step and 20 per product.
- If one file is refused, nothing in that step is saved.
- Replacing or removing a file **deletes the old file** from storage. Deleting the product (admin) removes the thumbnail too.
- It is optional. Nothing requires one before approval.
- **It is written in the change history** (admins only), but it **never changes the status**, for a seller or an admin. A rejected product stays rejected after a file change; only saving the product itself sends it back to Pending.
- An admin can add, replace or remove the thumbnail of any product or gig; that never changes the status.

---

## 5. The same title rule

**A seller cannot have two products with the same title.** Capital or small letters and extra spaces do not matter:
"Blue Tee", "blue tee" and "Blue  Tee" are the same title. The rule is **per kind**: the same seller may have a product and a gig
with the same title.

- If a seller tries to create a listing with a title they already have, they see:
  "You already have a listing with this title. Update the existing listing instead." The message also names the
  existing listing.
- This is also true when the earlier listing was **rejected**. The seller must **update that listing** (see section 7),
  not create a new one.
- Another seller may use the same title. The rule is "one title per seller (per kind)", not "one title for the whole site".
- An admin cannot create a duplicate for a seller either.
- Sellers cannot delete listings, so they cannot get around the rule by deleting and creating again. If an **admin**
  deletes a listing, its title becomes free again.
- Listings with no seller (for example, ones an admin made for nobody) are not part of this rule.

---

## 6. Admin: checking the listings

### 6.1 The pending list

The admin has a separate list called the **pending list**. It shows only the products that are **waiting for a
decision**. (Gigs have their own pending list.)

- The **newest request is at the top.** The admin can also sort with the oldest request first.
- A listing that comes back after a rejection goes to the **top** again, as a new request.
- The admin can search and filter by seller, listing type, category, brand, the date the listing was
  created and the date it was requested.
- The list loads in small groups ("Load more") and does not show a total. A separate number on the menu shows how
  many are waiting.

### 6.2 Deciding

For each listing the admin can:

| Decision | What happens |
|---|---|
| **Approve** | The listing becomes Approved. It leaves the pending list. |
| **Reject** | The listing becomes Rejected. **A reason is required.** It leaves the pending list. |
| **Request changes** | The listing becomes "Changes requested". **A reason is required.** It leaves the pending list. |

An admin can also change the status of **many listings at once** (approve, reject or request changes for all the
selected ones). A reason is needed for reject and request changes.

**About the reason (note):** it belongs to the **current** status only. When the status changes again, the old
reason is not carried over. It stays in the history, so nothing is lost. Write the reason so the seller knows
what to fix, for example "Please add clear photos".

### 6.3 What the admin sees on a listing

- All the details, the owner, the options with prices, the quantity prices and the photos.
- The **status history**: every change of status, who did it, when, and the reason.
- The **change history**: every change to the content (see section 9).

---

## 7. Seller: changing a listing

A seller can change their own listings at any time. What happens next depends on the **status**:

| The listing is | When the seller saves a change |
|---|---|
| **Pending** | It stays Pending. It keeps its place in the pending list. |
| **Approved** | It **stays Approved**, whatever the seller changes (text, photos, thumbnail, options, prices, stock). It does **not** go back for checking. The change is written in the change history, so the admin can see it. |
| **Rejected** or **Changes requested** | It goes back to **Pending** at once and appears at the top of the admin's pending list. |

**There is no "Resubmit" button.** For a rejected listing, **saving is resubmitting.** Even saving without changing
anything sends it back for checking.

**The seller's message.** When a seller saves a rejected listing, they can write a short message to the admin
("I added a clear photo"). It is shown as the listing's current note. The admin's old reason stays in the history.
For listings that are not rejected, a message is ignored.

**What the seller sees:** the status, the admin's reason when rejected, and the status history. The seller does
**not** see the change history of their listing (that is for admins).

**The flow in one picture**

```
Seller creates  ->  PENDING  ->  appears in the admin's pending list
                       |
               Admin decides
        ________________|__________________________
       |                |                          |
    APPROVE           REJECT                CHANGES REQUESTED
   (Approved)     (reason required)         (reason required)
       |                |                          |
  Seller can still      Seller reads the reason, changes the
  edit it freely;       listing and saves it
  it stays Approved                  |
                         PENDING again, at the TOP of the list
```

---

## 8. Seeing and searching listings

**A seller** sees a list of their own products (never anyone else's; gigs are in the Gigs list). The list shows the thumbnail,
title, category, price, status, the reason (if rejected), and the dates. The seller can open any of their products to see everything.

The seller can filter the list by: status, listing type, category, brand, and the dates the
listing was created or requested. They can search by title (English or Bangla), by an option code (SKU), or by brand
name. They can sort by date, title or status.

**An admin** sees all listings and can filter by the same things plus the seller. Admins also use the pending list
(section 6).

A seller who opens a listing that belongs to someone else sees "not found".

---

## 9. The change history (admins only)

Every time a listing is saved and something **really changed**, the system writes **one record**. It is done for
changes by the seller **and** by an admin.

What a record shows:

- **Who** made the change (seller or admin, and their name) and **when**.
- **What** changed, with the **old value** and the **new value**.

Example: in one save the seller changed the description and the Bangla title. That is **one** record with both changes
shown side by side.

**What is recorded:** all the text and Bangla texts, category, brand, measurement, the owner, the place, quantity prices, the
options with their prices, discounts and active/hidden state, the **thumbnail**, and the photos (which were added or removed). For a gig
it also records the package details (price type, descriptions); see section 12.

**What is not recorded:** the **stock** number. Stock changes all the time, and recording it would hide the changes
that matter. Changes of status are not here either; they are in the status history.

If a save changes nothing, nothing is recorded. Records are never edited or deleted.

---

## 10. Deleting

- **Sellers cannot delete listings.**
- **Admins can delete any listing.** It disappears from every list, but it is hidden, not erased: its history and
  options are kept. There is no "restore" button yet.
- When a **photo** is removed from a listing, its file is deleted from storage straight away.
- When an admin deletes a listing, its **thumbnail** file is deleted too (the gallery files stay).
- A deleted listing's title becomes free for the seller to use again.

---

## 11. When an admin creates a listing

An admin can create a product for a **seller** or for **nobody**. (A buyer's request, called a job, can be created by an admin
too; a seller's service is created as a gig under **Gigs**.)

- It is **Approved** straight away, unless the admin chooses another status.
- If it is for a seller, the same **title rule** applies. The seller then sees it in their list and can edit it. It
  stays Approved when the seller edits it.
- An admin can also change the owner later. That change is recorded.

---

## 12. Gigs (a seller's service offers)

A **gig** is work a seller offers (cleaning, photography, logo design, repair). It has its own place in the admin and seller panels (**Gigs**, with
Service chosen by default), its own pending list and its own price rules. Everything in sections 3 (statuses), 5 (same title), 6 (checking),
7 (changing), 9 (change history), 10 (deleting) and 4.1 (thumbnail) works the same way for gigs; this section lists what is different.

### 12.1 What a gig holds

| Part | What it is |
|---|---|
| **Title and description** | The name and the details. Both can also be written in **Bangla**. |
| **Category** | Must be a **service** category (for example Cleaning) and must be active. |
| **Delivery and extras** | Days to deliver, urgent or not, what the package includes (also in Bangla), and when it is available. |
| **Packages** | The prices. See 12.2. |
| **Photos and files** | The gallery: pictures or other files that show the work. |
| **Thumbnail** | One cover picture for lists (section 4.1). |
| **Place** | Country, state, city, thana (optional). |

A gig does **not** have: brand, model, origin, warranty, condition, unit of measure, sizes and colours, stock, or quantity prices. These
belong to products. If someone sends them for a gig, they are refused with a clear message.

### 12.2 Packages and prices

A gig is not sold by quantity. It is sold by **time**. The seller creates one **package** for each way of charging, and every package has:

| Part | What it means |
|---|---|
| **Price type** | What the price is for: **hourly**, **daily**, **weekly**, **monthly**, or **fixed** (one price for the whole job). A price type is **required**. |
| **Price** | The **rate** for that price type. For a weekly package, the price is the price of one week. |
| **Discount** | An optional lower price, with an optional start and end date. |
| **Description** | A few words about this package (also in Bangla). Only gigs have this. |

**How long the buyer buys.** A package has **no duration of its own**. When the buyer orders, they choose how many hours, days, weeks or months
they want (a fixed price is always one). The order records that number, and the buyer pays the rate **times** that number. Example: weekly rate
12,000 and the buyer chooses 2 weeks: 24,000. If a discount is running when they order, the discounted rate is used. (The buyer side is not built yet.)

**Several ways of charging, one gig.** A seller who wants to be paid hourly **and** weekly creates two packages:

| Package | Price type | Price (the rate) | Example: the buyer chooses | Buyer pays |
|---|---|---|---|---|
| Quick clean | hourly | 500 | 3 hours | 1,500 |
| Weekly plan | weekly | 12,000 | 2 weeks | 24,000 |
| Whole house | fixed | 9,000 | (one price) | 9,000 |

**Rules for packages**

- **One package for each price type.** A gig cannot have two hourly packages. A package that was hidden still counts, so a seller shows it
  again instead of adding a new one.
- A gig has **no stock** and **no sizes or colours**. These are refused.
- Packages are **never deleted**. To stop selling one, the seller **hides** it.
- A gig needs at least one package.
- In lists, the "from" price is the **lowest rate**, and the list also says what it is for (for example "450 hourly").

### 12.3 Seller: creating a gig

**Who can create?** Only a seller who is **Verified and Active**. Others see a clear message that says why.

1. The seller opens **Gigs** and chooses **Create gig**.
2. They choose a **service category**.
3. They write the **title** and **description** (and the Bangla versions if they want), and fill in the delivery details.
4. They add the **packages**: price type, price (the rate), an optional discount and an optional description.
5. They save. The gig is created as **Pending** and is owned by the seller.
6. They add the **thumbnail** and photos if they want. These are separate steps after saving.

The seller cannot choose the owner or the status. The gig is always theirs and always Pending. The same title rule (section 5) applies per kind:
a seller may have a product and a gig with the same title.

### 12.4 Admin: checking gigs

Gigs have **their own pending list**, separate from the product pending list (newest request on top; a gig the seller fixed after a rejection goes to
the top again). For each gig the admin can **Approve**, **Reject** (a reason is required) or **Request changes** (a reason is required), one by one or
for many gigs at once. The admin also sees the **change history**, including package changes and the thumbnail. An admin can also create, change and
delete gigs: a gig an admin creates is **Approved** straight away and may have no owner or a seller. Deleting a gig hides it (its history stays) and
removes its thumbnail file.

### 12.5 Seller: changing a gig

The same rules as section 7: a **Pending** gig stays Pending; an **Approved** gig stays Approved whatever changes (packages and prices included); a
**Rejected** or **Changes requested** gig goes back to **Pending** when the seller saves it (changing files does not). There is no Resubmit button, and a
seller **cannot delete** a gig. They can hide a package, and an admin can delete the whole gig.

---

## 13. Quick rules (one page)

| Topic | Rule |
|---|---|
| Who creates | A seller who is **Verified and Active**, or an admin. |
| Seller's new listing | Always **Pending**, always owned by that seller. |
| Admin's new listing | **Approved** by default. |
| Status | Only an admin sets it. |
| Reject / request changes | A **reason is required**. |
| Same title | One title per seller **per kind** (capital letters and spaces do not matter). |
| Rejected listing | The seller **updates it**; saving sends it back to **Pending** (top of the list). |
| Approved listing | A seller's edit keeps it **Approved**, whatever changes. |
| Pending listing | A seller's edit keeps it Pending. |
| Pending list | Admin only. Newest request first. |
| Seller deletes | **Not allowed.** |
| Admin deletes | Allowed. Hidden, not erased. Frees the title. |
| Bangla | Title, description, condition note, warranty, origin (and "package includes" for gigs). All optional. |
| Change history | Admins only. Stock is not recorded. |
| Photos | Deleting a photo deletes its file. |
| Thumbnail and photos | Own "add files" and "change files" steps (not in the save form). Thumbnail JPG, PNG, WEBP, 10 MB. Never changes the status. Old files deleted. |
| Products and gigs | Separate lists, forms and rules. Each place only accepts its own kind. |
| Gig category | A service category, active. |
| Gig package | Price type + price (a rate). The price type is required. The buyer chooses the duration when ordering. |
| Price type | hourly, daily, weekly, monthly or fixed. |
| Gig total | Current rate × the duration the buyer chooses when ordering. |
| One per type | A gig has one package for each price type, hidden ones included. |
| No stock, no options | A gig has none. Brand, model, quantity prices and similar fields are refused. |
| Packages are never deleted | They are hidden. |

---

## 14. Questions we often get (for support and operations)

**A seller says: "I cannot create a listing."**
They must be **Verified and Active**. If they are pending or rejected, they can only edit their profile. If they were
paused, an admin must make them Active again.

**A seller says: "I cannot create a service in Listings."**
Services are gigs, which have their own place: **Gigs** (see section 12).

**A seller says: "It says I already have a listing with this title."**
They already created a product with that title. Ask them to find it in their list and update it. If it was rejected,
updating and saving it sends it back for checking.

**A seller says: "My listing was rejected. How do I send it again?"**
They open the listing, read the reason, fix it, and save. Saving sends it back to Pending. There is no extra button.

**A seller says: "I changed my approved listing. Will it be checked again?"**
No. An approved listing stays approved when the seller edits it. Admins can see what was changed in the change history.

**A seller wants to delete a listing.**
Sellers cannot delete. Ask an admin. (If the seller only wants to stop selling a product, an admin can reject it or
delete it.)

**An admin wants to know what a seller changed.**
Open the listing. The change history shows every change with the old and new values.

**An admin wants to check only the new listings.**
Use the **pending list**. The newest requests are at the top.

**Why is a listing at the top of the pending list again?**
Its seller fixed and saved it after a rejection, so it is a new request.

**Can a seller see why their listing was rejected?**
Yes. The reason is shown on the listing, and the status history keeps every reason.

**A seller cannot find a category or brand in the list.**
Sellers only see **active** categories, brands and options. Ask an admin to activate it if it should be available.

**A seller says: "I cannot find where to create a gig."**
Gigs are in their own place, **Gigs**, not in **Listings**. They must be **Verified and Active**.

**A seller says: "It says a gig needs a price type."**
Every package needs one. For a single price for the whole job, choose **fixed**.

**A seller says: "It says I cannot add stock / sizes / a brand to my gig."**
Those are product features. A gig is priced only by packages.

**A seller says: "I cannot add a second hourly package."**
A gig has one package per price type. Edit the existing hourly package (or show it again if it was hidden).

**A seller says: "I changed the picture of my rejected gig and it went back to review."**
That is expected: changing the thumbnail counts as an edit, and saving a rejected gig or product sends it back.

**An admin created a gig but the seller cannot see it.**
Check that the admin chose the seller as the owner. A gig with no owner is not shown to any seller.

**Why does the product list not show my gig?**
Products and gigs are separate lists. Open the **Gigs** list.

**Did the seller get a message when I approved or rejected the listing?**
**No.** There are no automatic messages yet. Please tell the seller yourself.

---

## 15. Not available yet

Please do not promise these to sellers yet.

- **Messages to sellers** (email, SMS or app) when a listing is approved, rejected or sent back.
- **Buyers browsing and buying** from listings. The buyer side is not built yet.
- **Sellers deleting or hiding** their own listings.
- **Saving a draft** before sending. A seller's new listing always goes straight to Pending.
- **Restoring** a deleted listing.
- **Uploading many listings at once.**
- **Sellers seeing the change history** of their listings.
- **Creating a listing with its files in one step.** Files are added after the listing is saved.
- **Buyers browsing, buying or hiring a gig** (the buyer side, cart and payment are not built).
- **The seller's hire requests** (accepting, declining, delivering) and the **job board and bidding**: the next steps.
- **Different delivery times for each package** (delivery days belongs to the gig).
- **Buyer requests created by buyers.** Admins can create them for now.

---

## 16. Words used in this guide

| Word | Meaning |
|---|---|
| **Listing** | One product for sale (gigs and jobs are the same kind of record but have their own screens). |
| **Gig** | Work a seller offers (section 12). |
| **Job** | Work a buyer asks for. Admins manage it for now. |
| **Package** | One way of charging for a gig (price type and price). Technically a SKU. |
| **Price type** | What a gig's price is for: hourly, daily, weekly, monthly or fixed. |
| **Duration** | How many price-type units the buyer chooses when ordering (3 hours, 2 weeks). Kept on the order, not on the package. |
| **Thumbnail** | The one cover picture of a product or gig. |
| **Pending list** | The admin's list of products (or, separately, gigs) waiting for a decision. |
| **Approved / Rejected / Changes requested** | The decisions an admin can make. |
| **Reason (note)** | The explanation an admin writes when rejecting or asking for changes. |
| **Option (SKU)** | One combination of size, colour and so on, with its own price, discount and stock. |
| **Quantity price** | A lower price when more pieces are bought. |
| **Status history** | The list of every status change of a listing, with reasons. |
| **Change history** | The list of every content change of a listing, with old and new values. Admins only. |
| **Verified and Active** | The state a seller needs to create listings. See the Seller Guide. |
