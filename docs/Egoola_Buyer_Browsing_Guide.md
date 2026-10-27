# Egoola Buyer Browsing Guide (in plain words)

This guide explains what a **buyer** can see and do when browsing Egoola: the **categories**, the **products**, the **gigs** and the **seller pages**. It has no technical terms. It says
what is shown, what is hidden, and which choices (filters) a buyer has to narrow the list.

For the technical details (addresses, fields, examples), see [`public-api-guide.md`](public-api-guide.md).

**Web version of this guide (easy to read in a browser):** https://claude.ai/artifact/EGfrxisReoLdZS4Lq73nxf (private: the owner must share it from the page's Share menu before others can open it).

---

## 1. The big picture

A buyer does not need to log in to look around. Anyone can open the shop and browse. The buyer moves through four kinds of pages:

| Page | What it shows |
|---|---|
| **Categories** | The shelves of the shop: Electronics, Fashion, Cleaning, and so on. Each can have smaller shelves inside. |
| **Products** | Things a seller sells: a phone, a shirt, a chair. |
| **Gigs** | Services a seller offers: house cleaning, logo design, repairs. |
| **Seller page** | A page about the seller: who they are, where they are, how to contact them, and how much they sell. |

A normal path: the buyer picks a category, looks at the products or gigs in it, opens one, and if they want to know more about the seller, taps the seller's name.

---

## 2. What the buyer is allowed to see

Not everything in the system is shown to buyers. A product or a gig appears **only if all of these are true**:

1. **An admin has approved it.** Items waiting for review, rejected, sent back for changes, or saved as a draft are never shown.
2. **It has not been deleted.**
3. **Its seller is in good standing.** The seller must be both **verified** (the admin accepted their documents) and **active**. If a seller is still waiting for approval, was rejected,
   was paused or was suspended, **none of their products or gigs are shown**. When the seller is active again, everything comes back.
4. **There is something to buy.** The item must have at least one price option that is switched on. An item with every price option hidden is not shown.

Items that an admin posted themselves (with no seller) are shown too, as long as they are approved.

A buyer who types the direct link of a hidden item gets a "not found" page, exactly as if it did not exist.

**Only the "on" price options count.** Whenever a price is shown or compared, it is worked out from the price options that are switched on. Hidden options are ignored.

---

## 3. Categories

Categories are the shelves of the shop. They form a tree: a big category (for example **Electronics**) can hold smaller ones (**Mobile Phones**, **Laptops**), and those can hold even smaller ones.

**How a buyer browses categories**
- At the start, the buyer sees the **top-level** categories only (the biggest shelves).
- Tapping a category shows the smaller categories inside it. The buyer can keep going down until there is nothing smaller. A category with nothing inside is the end of the road,
  and the buyer then sees its products or gigs.
- Each category tells the app whether it has smaller ones inside, so the app knows whether to show an arrow.

**What each category shows:** its name (English and Bangla), a picture if it has one, and its place in the order.

**Choices (filters) the buyer has**

| Choice | What it does |
|---|---|
| Search by name | Finds categories whose name contains the typed text. Works with English and Bangla names, and small or capital letters do not matter. Typing "phone" finds "Mobile Phones". |
| Inside one category | Shows only the smaller categories of the category the buyer picked. |
| Products or services | Shows only product categories, or only service categories. |

If the buyer searches without picking a category first, the search looks through **all levels** of the shop. If they search after picking a category, it looks only inside that one.

**What is hidden:** a category that an admin switched off, **and everything inside it**, even if the smaller categories are still switched on.

**Order:** categories appear in the order the admin set, then by name.

---

## 4. Products

A product list shows things that sellers sell.

**What each product card shows**
- the title (English and Bangla) and the cover picture
- the category it belongs to, and the brand if it has one
- the **price**, and the **sale price** if there is a discount running right now (the app can show the old price crossed out)
- whether it is **in stock**
- the **seller's name**, which the buyer can tap to open the seller page

**What the product page shows (when the buyer opens one)**
- everything on the card, plus the full description (English and Bangla)
- all the **price options**: for example a T-shirt in Small, Medium and Large, in Black and White. Each option has its own price and its own stock ("20 left" or "sold out").
- **bulk prices**, when the seller gives a lower price for buying more (for example "10 or more: 450 each")
- the model, where it is made, warranty, the condition (for used items), and extra details such as RAM or size
- all pictures and videos
- where the item is located

**Which price is shown on the card:** the **cheapest** price option that is switched on, counting the sale price while the sale is running.

**Choices (filters) the buyer has**

| Choice | What it does |
|---|---|
| Category | Shows the products of the chosen category **and of every smaller category inside it**. Choosing "Electronics" also finds phones and laptops. |
| Search | Finds products by title (English or Bangla), brand name or model. |
| Type | General, Used, Village, Retail, Wholesale or Brand. |
| Brand | Only products of that brand. |
| In stock | Only products that can be bought now, or only the sold-out ones. |
| Price from / to | Keeps products whose price is inside the range. The sale price is used while a sale is running. |
| Seller | Only the products of one seller (used by the seller page). |
| Place | Country, division, district or area (thana). |
| Sort by | Newest (the default), oldest, cheapest first, most expensive first, or by title. |

---

## 5. Gigs

A gig is a service. The buyer does not buy a thing; they hire someone for work. A gig has **packages**, and each package says how the work is priced:

| Package type | Meaning |
|---|---|
| Hourly | A price for each hour of work |
| Daily | A price for each day |
| Weekly | A price for each week |
| Monthly | A price for each month |
| Fixed | One price for the whole job |

A gig can have several packages, but only one of each type. For example, a cleaner might offer "500 per hour" and "12,000 per week". The buyer chooses how many hours, days, weeks or months
they want **when they order**, not on the gig page. A gig has no stock and no sizes or colours.

**What each gig card shows**
- the title (English and Bangla) and the cover picture, and the category
- the **starting price**: the cheapest package, with what it is for ("from 500 per hour")
- how many days the work takes, and whether the seller can do **urgent** work
- the **seller's name**, which the buyer can tap

**What the gig page shows (when the buyer opens one)**
- everything on the card, plus the full description (English and Bangla)
- **every package** with its price, its sale price if any, and a short note about what that package includes
- what the service includes, and the dates when the seller is available
- all pictures and videos, and where the service is offered

**Choices (filters) the buyer has**

| Choice | What it does |
|---|---|
| Category | The chosen category and every smaller category inside it. |
| Search | Finds gigs by title (English or Bangla). |
| Package type | Only gigs that have a package of that type (for example only gigs with an hourly package). When this is chosen, the card shows **that** package's price, and the price range below is measured on it. |
| Price from / to | Keeps gigs whose price is inside the range. For a fair comparison, choose a package type as well (an hourly price and a monthly price are not the same thing). |
| Delivery within | Only gigs that finish the work in the chosen number of days or less. Gigs that do not say how long they take are left out. |
| Urgent | Only gigs that offer urgent work, or only those that do not. |
| Seller | Only the gigs of one seller. |
| Place | Country, division, district or area (thana). |
| Sort by | Newest (the default), oldest, cheapest first, most expensive first, or by title. |

---

## 6. The seller page

When a buyer taps a seller's name on a product or a gig, they land on the seller page. It helps the buyer decide whether to trust the seller.

**What it shows**
- **Who:** the seller's name and photo, and the date they joined Egoola
- **Where:** country, division, district and area (the town, not the home address)
- **About the business:** the kind of business, what they mainly sell, a short description, the year it started and the team size
- **How to contact them (only what the seller chose to make public):** a public email, WhatsApp, Facebook, WeChat and Skype
- **Skills, education and experience**, if the seller filled them in
- **How much they offer:** the number of products and the number of gigs that are visible to buyers right now

From the seller page the buyer can open the seller's products and gigs (the product and gig lists, filtered to that seller).

**Who has a seller page:** only sellers who are verified and active. For any other seller (waiting, rejected, paused or suspended) the page does not exist.

**What is never shown to buyers:** the seller's private email and phone number, home address, ID documents, money balance, and anything about how the admin judged their application.

---

## 7. How lists are paged

Lists can be long, so they come in pages. The app asks for a page number and how many items it wants per page (20 by default, 100 at most). The answer says:

- how many items match in total
- which page this is, and how big the pages are
- how many pages there are in total

The app keeps loading the next page until it reaches the last one. If nothing matches, the list is simply empty, which is not an error.

---

## 8. What a buyer will never see

| Never shown | Why |
|---|---|
| Items waiting for approval, rejected, sent back, drafts and deleted items | Only approved items are for sale. |
| Items of a seller who is waiting, rejected, paused or suspended | Only trusted sellers are shown. |
| Items with no price option switched on | There is nothing to buy. |
| Switched-off categories and everything inside them | An admin has taken them off the shelf. |
| Admin notes, review history, who edited what | Internal information. |
| A seller's private phone, email, address, documents and money | Private information. |

---

## 9. What is not part of this yet

- **Ratings and reviews** on products, gigs and sellers (reviews are not connected yet).
- **Checkout, orders, hiring and bidding.** The cart and the wishlist exist (see `buyer-api-guide.md`); actually buying or hiring does not yet.
- **Messaging a seller.**
- **A full seller directory** (a list of all sellers). For now a buyer reaches a seller from one of their items.

---

## 10. Quick summary

| | Categories | Products | Gigs | Seller page |
|---|---|---|---|---|
| Needs login | No | No | No | No |
| Shown only if | Switched on, and not inside a switched-off category | Approved, not deleted, seller verified and active, has an active price option | Same as products | Seller verified and active |
| Main filters | Search, inside one category, product or service | Category, search, type, brand, in stock, price, seller, place | Category, search, package type, price, delivery days, urgent, seller, place | None (it is a single page) |
| Price shown | None | Cheapest active option (sale price while a sale runs) | Cheapest package (or the chosen type) | None |
| Sorting | Admin order, then name | Newest, oldest, cheapest, most expensive, title | Same as products | None |
| Paged | Yes | Yes | Yes | No |
