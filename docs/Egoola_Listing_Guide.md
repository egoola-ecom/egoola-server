# Egoola Listing Guide

**One guide for everyone.** This guide explains, in simple words, how listings work on Egoola: what a listing is,
how a seller creates one, how an admin checks it, what happens when it is rejected, and what each person can and
cannot do.

It is written for all teams: operations, support, product, design, testing and development. You do not need any
technical knowledge to read it.

This guide does **not** explain technical details such as API addresses or the database. Each team has its own
document for that (see the documentation index, `docs/README.md`). For the seller's own side of things (sign-up,
verification, login), read the **Egoola Seller Guide**.

---

## 1. The people in this guide

| Who | What they do with listings |
|---|---|
| **Seller** | Creates and manages their own listings. Can create, change, see and search them. Cannot delete them. |
| **Admin** | Checks the listings sellers create (approve or reject). Can also create, change and delete any listing, for a seller or for nobody. |
| **Buyer** | Will browse and buy from approved listings (the buyer side is not built yet). |
| **Operations / support team** | Helps sellers and admins. Uses the admin panel. |

---

## 2. What is a listing?

A **listing** is one thing for sale, or one request for work. Egoola uses **one** kind of listing for everything.
The old app had separate, repeated screens for each type. Now every type uses the same form.

**Product or service**

- A **product** is a thing you can touch and ship.
- A **service** is work someone does (cleaning, photography, repair).

**The six product formats** (called the *listing type*): General, Used, Village, Retail, Wholesale, and Brand.
A Brand listing must have a brand chosen.

**A listing holds:**

| Part | What it is |
|---|---|
| **Title and description** | The name and the details. Both can also be written in **Bangla**. |
| **Category** | Where it belongs, for example Electronics or Cleaning. Must match the type (a product needs a product category) and must be active. |
| **Brand, model, origin, warranty** | Extra facts for products. Origin and warranty can also be written in Bangla. |
| **Condition note** (used products) | A note about the condition. Can also be written in Bangla. |
| **Service details** | Price type (fixed or hourly), hourly rate, days to deliver, urgent, what the package includes (also in Bangla), and when it is available. |
| **Options (sizes, colours...)** | A product can come in options. Each combination (for example Size M + Colour Black) has its **own price, discount period and stock**. A simple product has just one. |
| **Quantity prices** (wholesale) | A cheaper price when someone buys more, for example 1 to 9 pieces at 100 and 10 or more at 90. |
| **Photos and files** | Pictures or other files that show the listing. |
| **Place** | Country, state, city, thana (optional). |

**Bangla versions.** Six texts can be written in Bangla as well: title, description, package includes, condition note,
warranty and origin. They are all optional.

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

1. The seller opens "Create listing" and chooses **Product** or **Service**.
2. They choose the **listing type** (for products), the **category**, and a **brand** if needed.
3. They write the **title** and **description** (and the Bangla versions if they want).
4. They fill the details: for a product, model, origin, warranty, condition; for a service, price type, rate, days.
5. They set the **price and stock**. If the product has options (sizes, colours), they add each combination with
   its own price, discount and stock.
6. They add **quantity prices** (wholesale) and **photos** if they want.
7. They save. The listing is created as **Pending** and is owned by the seller.

The seller picks categories, brands, measurements and options from lists that show only **active** items.

**What the seller cannot do when creating:** choose the owner, choose the status, or create a buyer's request.
The listing is always theirs and always Pending.

---

## 5. The same title rule

**A seller cannot have two listings with the same title.** Capital or small letters and extra spaces do not matter:
"Blue Tee", "blue tee" and "Blue  Tee" are the same title.

- If a seller tries to create a listing with a title they already have, they see:
  "You already have a listing with this title. Update the existing listing instead." The message also names the
  existing listing.
- This is also true when the earlier listing was **rejected**. The seller must **update that listing** (see section 7),
  not create a new one.
- Another seller may use the same title. The rule is "one title per seller", not "one title for the whole site".
- An admin cannot create a duplicate for a seller either.
- Sellers cannot delete listings, so they cannot get around the rule by deleting and creating again. If an **admin**
  deletes a listing, its title becomes free again.
- Listings with no seller (for example, ones an admin made for nobody) are not part of this rule.

---

## 6. Admin: checking the listings

### 6.1 The pending list

The admin has a separate list called the **pending list**. It shows only the listings that are **waiting for a
decision**.

- The **newest request is at the top.** The admin can also sort with the oldest request first.
- A listing that comes back after a rejection goes to the **top** again, as a new request.
- The admin can search and filter by seller, product or service, listing type, category, brand, the date the listing was
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
| **Approved** | It **stays Approved**, whatever the seller changes (text, photos, options, prices, stock). It does **not** go back for checking. The change is written in the change history, so the admin can see it. |
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

**A seller** sees a list of their own listings (never anyone else's). The list shows the title, category, price,
status, the reason (if rejected), and the dates. The seller can open any of their listings to see everything.

The seller can filter the list by: status, product or service, listing type, category, brand, and the dates the
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

**What is recorded:** all the text and Bangla texts, category, brand, measurement, the owner, the place, the service
details, quantity prices, the options with their prices, discounts and active/hidden state, and the photos (which were
added or removed).

**What is not recorded:** the **stock** number. Stock changes all the time, and recording it would hide the changes
that matter. Changes of status are not here either; they are in the status history.

If a save changes nothing, nothing is recorded. Records are never edited or deleted.

---

## 10. Deleting

- **Sellers cannot delete listings.**
- **Admins can delete any listing.** It disappears from every list, but it is hidden, not erased: its history and
  options are kept. There is no "restore" button yet.
- When a **photo** is removed from a listing, its file is deleted from storage straight away.
- A deleted listing's title becomes free for the seller to use again.

---

## 11. When an admin creates a listing

An admin can create a listing for a **seller**, for a **buyer's request**, or for **nobody**.

- It is **Approved** straight away, unless the admin chooses another status.
- If it is for a seller, the same **title rule** applies. The seller then sees it in their list and can edit it. It
  stays Approved when the seller edits it.
- An admin can also change the owner later. That change is recorded.

---

## 12. Quick rules (one page)

| Topic | Rule |
|---|---|
| Who creates | A seller who is **Verified and Active**, or an admin. |
| Seller's new listing | Always **Pending**, always owned by that seller. |
| Admin's new listing | **Approved** by default. |
| Status | Only an admin sets it. |
| Reject / request changes | A **reason is required**. |
| Same title | One title per seller (capital letters and spaces do not matter). |
| Rejected listing | The seller **updates it**; saving sends it back to **Pending** (top of the list). |
| Approved listing | A seller's edit keeps it **Approved**, whatever changes. |
| Pending listing | A seller's edit keeps it Pending. |
| Pending list | Admin only. Newest request first. |
| Seller deletes | **Not allowed.** |
| Admin deletes | Allowed. Hidden, not erased. Frees the title. |
| Bangla | Title, description, package includes, condition note, warranty, origin. All optional. |
| Change history | Admins only. Stock is not recorded. |
| Photos | Deleting a photo deletes its file. |

---

## 13. Questions we often get (for support and operations)

**A seller says: "I cannot create a listing."**
They must be **Verified and Active**. If they are pending or rejected, they can only edit their profile. If they were
paused, an admin must make them Active again.

**A seller says: "It says I already have a listing with this title."**
They already created a listing with that title. Ask them to find it in their list and update it. If it was rejected,
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

**Did the seller get a message when I approved or rejected the listing?**
**No.** There are no automatic messages yet. Please tell the seller yourself.

---

## 14. Not available yet

Please do not promise these to sellers yet.

- **Messages to sellers** (email, SMS or app) when a listing is approved, rejected or sent back.
- **Buyers browsing and buying** from listings. The buyer side is not built yet.
- **Sellers deleting or hiding** their own listings.
- **Saving a draft** before sending. A seller's new listing always goes straight to Pending.
- **Restoring** a deleted listing.
- **Uploading many listings at once.**
- **Sellers seeing the change history** of their listings.
- **Buyer requests created by buyers.** Admins can create them for now.

---

## 15. Words used in this guide

| Word | Meaning |
|---|---|
| **Listing** | One thing for sale, or one request for work. |
| **Pending list** | The admin's list of listings waiting for a decision. |
| **Approved / Rejected / Changes requested** | The decisions an admin can make. |
| **Reason (note)** | The explanation an admin writes when rejecting or asking for changes. |
| **Option (SKU)** | One combination of size, colour and so on, with its own price, discount and stock. |
| **Quantity price** | A lower price when more pieces are bought. |
| **Status history** | The list of every status change of a listing, with reasons. |
| **Change history** | The list of every content change of a listing, with old and new values. Admins only. |
| **Verified and Active** | The state a seller needs to create listings. See the Seller Guide. |
