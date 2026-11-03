# Brief for the Egoola Web session — admin Payment Gateways (new backend feature)

Backend done and tested in `egoola-server`: admin CRUD for the ways a buyer can pay at checkout. Read this file
top to bottom, then build it in **Admin Web**. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/admin/admin-payment-gateway-api-guide.md` (the technical contract below is a copy of
it), `egoola-server/docs/Egoola_Order_Guide.md` section 3 (plain-language version, if anything below is unclear
conceptually). Postman: `Egoola` → **Payment Gateways (admin)**. Run the backend with
`uv run manage.py runserver 8000`; accounts in `docs/test-accounts.md` (admin: `test.admin@egoola.com` /
`Test@12345`).

Needs an admin token (`Authorization: Bearer <access>`). No token: `401`. A seller or buyer token: `403`.

---

## 1. What this is

A **Payment Gateway** is a way a buyer can pay — today there's exactly one, **Cash on Delivery**, already seeded
in the database (id `1`, slug `cash-on-delivery`). Nothing a buyer or a seller does ever creates or edits one;
this screen is purely for admin to manage the list a buyer picks from at checkout. There's no detail/retrieve
screen needed — the list row already carries every field there is.

Four things to build:
1. **List** with filters (active/inactive, search).
2. **Create** (name + optional icon upload).
3. **Edit** (rename, toggle active, replace the icon).
4. **Delete.**

## 2. The contract

| Call | What it does |
|---|---|
| `GET /orders/payment-gateways/` | list. Filter: `is_active`. Search: `name`/`slug`. Limit/offset paging. |
| `POST /orders/payment-gateways/` | create |
| `PATCH /orders/payment-gateways/{id}/` | edit (partial) |
| `DELETE /orders/payment-gateways/{id}/` | remove |

### Fields

| Field | Notes |
|---|---|
| `name` | Required, must be unique. |
| `slug` | **Read-only** — always server-generated from `name`, regenerates on rename. Never show an editable field for it, only display it. |
| `icon` | Write-only on create/update (multipart). |
| `icon_path` / `icon_url` | Read-only — `icon_url` is what to render; both `null` until an icon is uploaded. |
| `is_active` | Default `true`. |

### Create

```json
POST /orders/payment-gateways/
{ "name": "bKash" }
```
→ `201`, `"slug": "bkash"`. With an icon, send multipart instead of JSON.

### Edit

```json
PATCH /orders/payment-gateways/3/
{ "name": "bKash Mobile Banking" }
```
→ `"slug": "bkash-mobile-banking"`. Toggling: `{"is_active": false}`.

### Errors

| Case | Response |
|---|---|
| Missing `name` | `{"name": ["This field is required."]}`, `400` |
| Duplicate `name` | `{"name": ["payment gateway with this name already exists."]}` (exact wording may vary), `400` |
| Unknown id | `404` |
| Deleting a gateway a `Payment` still references | `400` (foreign-key protection) — show a clear "still in use, deactivate instead" message rather than the raw error |

## 3. Tasks

1. **API client** (`admin-payment-gateways-api.ts`): `listGateways`, `createGateway`, `updateGateway`,
   `deleteGateway`. Create/update need multipart support for the icon.
2. **List screen**: table (icon thumbnail, name, slug, active toggle, created date), filter bar (`is_active`,
   search), limit/offset paging (page-size selector, not infinite scroll). An inline **Active** toggle that
   calls `PATCH {is_active}` directly from the row, no dialog needed.
3. **Create/Edit form**: name field, icon uploader (preview the current `icon_url` when editing, let it be
   replaced), no slug field at all (just display it, read-only, once it exists).
4. **Delete**: confirmation dialog; if the server refuses (`400`, in-use), show a message suggesting
   deactivation instead and don't treat it as a generic failure toast.
5. Entry point: add **Payment Gateways** to the admin nav, near Carts & Wishlists or wherever payment-adjacent
   screens live.

## 4. Verify (browser, admin role; record results)

| # | Case | Expected |
|---|---|---|
| 1 | List on a fresh dev DB | Cash on Delivery shows, active, no icon |
| 2 | Create "Postman Gateway" with no icon | `201`, slug `postman-gateway` |
| 3 | Create it again with the same name | `400`, field error under Name |
| 4 | Rename it to "Postman Gateway Two" | slug updates to `postman-gateway-two` |
| 5 | Upload an icon on edit | `icon_url` now set, thumbnail renders |
| 6 | Toggle it inactive | list shows it as inactive; filtering `is_active=true` hides it |
| 7 | Delete it | gone from the list |
| 8 | Try to delete Cash on Delivery (likely referenced by test orders) | blocked with a clear message, not a raw 400 dump |
| 9 | A non-admin token (if testable from the UI) | handled the same way other admin screens reject it |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong or unclear.
