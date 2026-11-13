# Brief for the Egoola Web session — buyer gig (service) cart & order cross-check

Buyer Web already has cart, checkout and order screens for **products**, built from
`frontend-buyer-cart-wishlist-prompt.md` and `frontend-buyer-order-prompt.md`. Backend now also supports a buyer
adding one or more of a seller's **gigs** to a cart and checking out — through the **exact same endpoints**, no new
routes. This brief is a **cross-check**, not a new build: find and fix every place the existing product-only
screens silently assumed `qty` is always present, `order_type` is always `"product"`, or a gig line can't happen.
Do not push; commit locally only if asked. Do not change `egoola-server` — if something looks wrong on the
backend, stop and report it instead of working around it.

Read first: `egoola-server/docs/buyer/buyer-api-guide.md` §3 (gig lines in the cart — this was already written
generically for both types), `egoola-server/docs/buyer/buyer-order-api-guide.md` §5 ("Only product orders show up
here" is now out of date — both product and gig orders show up, `order_type` tells them apart),
`egoola-server/docs/Egoola_Cart_Guide.md` and `egoola-server/docs/Egoola_Order_Guide.md` (plain-language, both
updated for gigs — read the Order Guide's status flow and its "Why does a gig order say shipped?" FAQ entry).
Postman: `Egoola-BuyerApp` → **Cart**, **Orders**. Run the backend with `uv run manage.py runserver 8000`; buyer
account in `docs/test-accounts.md`.

---

## 1. What actually changed (nothing on the wire)

Nothing new to call. `POST /buyer/cart/items/`, `GET/DELETE /buyer/cart/`, `POST /buyer/orders/`,
`GET /buyer/orders/`, `GET /buyer/orders/{id}/`, `PATCH /buyer/orders/{id}/` are the same endpoints the product
screens already call. A gig cart and a gig order just carry different field values on that same shape:

| Field | Product line | Gig line |
|---|---|---|
| `qty` | a whole number | `null` |
| `duration` | `null` | a whole number (hours/days/weeks/months — whatever the SKU's `price_type` is) |
| `listing.catalog_type` (cart) | `"product"` | `"service"` |
| `order_type` (order) | `"product"` | `"service"` |
| `price_type_snapshot` (order item) | `null` | `"hourly"\|"daily"\|"weekly"\|"monthly"\|"fixed"` |

If any screen branches on "does this order have `qty`" to decide how to render a line, that branch now needs a
`duration` + `price_type_snapshot` path too. If any screen filters or assumes `order_type === "product"` anywhere
(a hardcoded query, a type guard, a Zod/TS schema with `qty: number` non-nullable), that is the bug to find.

## 2. Cross-check tasks

1. **Cart line rendering**: open a cart that has a gig line in it (add one via a gig's detail page, or via the API
   directly if that UI isn't wired up yet) and confirm the cart screen shows "3 hours" (or whatever the duration/
   price_type is) instead of a blank/zero/`NaN` where a quantity stepper would normally go, and that the stepper
   itself edits `duration` not `qty` for that line (`PATCH` with the wrong field is a `400` — confirm the UI sends
   the right one per line, not a hardcoded `qty`).
2. **Checkout button from a service cart**: confirm the same "Checkout" flow the product cart uses (address picker,
   payment gateway, confirm) works unmodified from a gig cart — same request shape, same response shape, lands on
   the same order-detail screen.
3. **Order list**: confirm both a product and a gig order render in the same `GET /buyer/orders/` list without
   either crashing the row component or silently hiding the gig one. If there's a type filter/tab, confirm it
   actually filters by `order_type`, not something client-side guessed from other fields.
4. **Order detail — item rendering**: confirm a gig order's item row shows title, rate, `duration`, and
   `price_type_snapshot` (e.g. "100.00 / hour × 3 hours = 300.00") instead of whatever the product row shows for
   `qty` — this is almost certainly the one place a non-nullable `qty` assumption will break first.
5. **Status/cancel logic**: confirm the status badge map and the Cancel-button visibility rule (`pending`/
   `accepted`/`in_progress` only) are driven by `status` alone, not anything that assumes `order_type === "product"`
   — a gig order moves through the identical ladder, so nothing here should need an `order_type` check at all. If
   you find one, that's the bug.
6. **Copy check**: `shipped`/`delivered` read oddly for a gig ("handed over" / "the buyer has it" is the intended
   reading — see the Order Guide FAQ). Flag it rather than silently renaming the status labels — a wording change
   is a product decision, not something to invent while cross-checking.
7. **Empty/mixed states**: a buyer with only gig orders, only product orders, and a mix of both — confirm none of
   these states crash or show a wrong empty-state message in the order list.

## 3. Verify (browser, buyer token; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Add a gig to cart, open the cart screen | line shows duration + price type, not a qty stepper or a blank |
| 2 | Checkout the gig cart (address + Cash on Delivery) | `201`, lands on order detail, `order_type: "service"` |
| 3 | Order list with one product order and one gig order | both render, correct badges, no crash |
| 4 | Open the gig order's detail | item shows rate × duration = line total, not `qty` |
| 5 | Cancel the gig order while `pending` | `200`, same as a product cancel |
| 6 | Try to check out the gig cart again after it closed | `400`, same message style as a product's reused cart |
| 7 | A buyer with zero gig orders, only product ones | order list still renders correctly, no gig-shaped empty slot |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong, missing, or unclear
once you tried it against the real API.
