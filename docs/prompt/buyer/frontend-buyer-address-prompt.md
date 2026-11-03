# Brief for the Egoola Web session — buyer Addresses (new backend feature)

Backend done and tested in `egoola-server`: a buyer's own saved delivery addresses. Read this file top to
bottom, then build it in **Buyer Web**. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/buyer/buyer-address-api-guide.md` (the technical contract below is a copy of it),
`egoola-server/docs/Egoola_Order_Guide.md` section 5 (plain-language version, where this fits into checkout).
Postman: `Egoola-BuyerApp` → **Addresses**. Run the backend with `uv run manage.py runserver 8000`; accounts in
`docs/test-accounts.md` (buyer: `test.buyer@egoola.com` / `Test@12345`).

Needs a buyer token (`Authorization: Bearer <access>`). No token: `401`.

---

## 1. What this is

A buyer's address book — a short list of saved delivery addresses they pick from at checkout (see the Orders
brief). No pagination at all; a buyer never has enough of these to need it. Full CRUD, scoped entirely to the
logged-in buyer (another buyer's address id is `404`, not `403`).

Four things to build:
1. **List** (simple, newest first — no paging controls needed).
2. **Create.**
3. **Edit.**
4. **Delete.**

## 2. The contract

| Call | What it does |
|---|---|
| `GET /buyer/addresses/` | every saved address, newest first, no pagination wrapper (a plain array) |
| `POST /buyer/addresses/` | save a new one |
| `GET /buyer/addresses/{id}/` | one address |
| `PATCH /buyer/addresses/{id}/` | edit (partial) |
| `DELETE /buyer/addresses/{id}/` | remove |

### Fields

| Field | Notes |
|---|---|
| `name` | Required — the recipient's name, not necessarily the buyer's own. |
| `phone` | Required. |
| `country` / `state` / `city` / `thana` | All four **required** ids — unlike a job's location, there's no partial chain here. Use the same cascading pickers (country → state → city → thana) already built for seller/job location fields; wire them to `/public/geography/...`. |
| `country_name` / `state_name` / `city_name` / `thana_name` | **Read-only**, in every response. Use these to show "Feni, Chittagong, Bangladesh" on the list/detail — no need to look the ids up against `/public/geography/...` just to render a saved address. |
| `address_line1` | Required. |
| `address_line2` | Optional. |
| `zip` | Optional. |

### Create

```json
POST /buyer/addresses/
{ "name": "Home", "phone": "+8801711110001", "country": 126, "state": 13, "city": 8, "thana": 24,
  "address_line1": "House 1, Road 2", "address_line2": "Flat 3A", "zip": "1200" }
```
→ `201` with the full address, including its new `id`.

### Errors

| Case | Response |
|---|---|
| Missing a required field | field-keyed `400` |
| `city` doesn't belong to the given `state` (or similar at any level) | `{"city": ["This city does not belong to the selected state."]}`, `400` |
| Unknown id, or another buyer's | `404` |

## 3. Tasks

1. **API client** (`buyer-addresses-api.ts`): `listAddresses`, `createAddress`, `updateAddress`,
   `deleteAddress`.
2. **Address book screen**: a simple card list (name, address line, phone), "Add address" button, edit/delete
   actions per card. Since there's no pagination, just render the whole array.
3. **Create/Edit form**: the four cascading location pickers (reuse whatever component already does this for
   seller onboarding or job posting) plus name/phone/address lines/zip. Surface the "doesn't belong to" error
   under the right field, not as a generic toast.
4. **Delete**: confirmation dialog (mention nothing changes about past orders — deleting here is final for the
   address book only).
5. This screen is also the picker used during checkout (see the Orders brief, which adds a "create new address"
   shortcut inline at checkout time using this same create form).

## 4. Verify (browser, buyer role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Fresh buyer, open the address book | empty list |
| 2 | Create one with all fields | appears in the list |
| 3 | Create one missing `address_line1` | `400`, field error shown |
| 4 | Pick a `city` that doesn't belong to the chosen `state` | `400`, clear message under the location picker |
| 5 | Edit just the `address_line1` of an existing one | saved, every other field unchanged |
| 6 | Delete one | gone from the list |
| 7 | No token (if testable) | `401` handled the same as elsewhere |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
