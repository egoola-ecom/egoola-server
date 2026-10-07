# Test Accounts (local development only)

These accounts exist in the **local dev database** for testing and Postman. They
are not for staging or production. Last verified: 2026-10-08.

Password for every account below: **`Test@12345`**

## Accounts

| Role | Email | Type / state | Use it for |
|---|---|---|---|
| Admin | `test.admin@egoola.com` | `admin` (plain admin) | Sellers, buyers, listings, brands, categories … **not** Admin Management (gets 403) |
| Super-admin | `test.super@egoola.com` | `super_admin` | Everything, including Admin Management |
| Seller | `test.seller@egoola.com` | verification `unverified`, status `active` | Seller login |
| Buyer | `test.buyer@egoola.com` | status `active` | Buyer login |

Other admin rows in the dev database (`admin@egoola.com` — super_admin,
`emrul.hasan@egoola.com` — admin) are real accounts with their own passwords.
They don't use `Test@12345`; don't rely on them for tests.

## Logging in

Base URL: `http://127.0.0.1:8000`

| Actor | Endpoint |
|---|---|
| Admin / super-admin | `POST /api/v1/auth/admin/login/` |
| Seller | `POST /api/v1/auth/seller/login/` |
| Buyer | `POST /api/v1/auth/buyer/login/` |
| Refresh | `POST /api/v1/auth/token/refresh/` |

```json
{ "email": "test.super@egoola.com", "password": "Test@12345" }
```
The response has `access` (1 hour) and `refresh` (14 days). Send
`Authorization: Bearer <access>`. A wrong password, a suspended buyer/seller or
an inactive admin cannot log in (403). See `authentication.md`.

In Postman (`postman/` folder): **Auth > Admin Login**, **Super-Admin Login**,
**Seller Login**, **Buyer Login** use these accounts and save the tokens.

## Reference ids used in tests (dev database)

| Thing | Id |
|---|---|
| Product category "Electronics" | 18 |
| Service category "Cleaning" | 29 |
| Measurement "Box" | 13 |
| Country Bangladesh / State Dhaka / City Feni | 126 / 12 / 8 |

If the database is rebuilt these ids will differ — check with the list APIs.

## Re-creating the accounts

If the dev database is reset, run in `uv run manage.py shell`:

```python
from django.contrib.auth.hashers import make_password
from apps.accounts.models import Admin, Seller, User

pw = make_password("Test@12345")
Admin.objects.get_or_create(email="test.admin@egoola.com", defaults=dict(
    name="Test Admin", mobile="+8801700000001", password=pw, type="admin", status="active"))
Admin.objects.get_or_create(email="test.super@egoola.com", defaults=dict(
    name="Test Super Admin", mobile="+8801700000010", password=pw, type="super_admin", status="active"))
Seller.objects.get_or_create(email="test.seller@egoola.com", defaults=dict(
    name="Test Seller", phone="+8801700000002", password=pw))
User.objects.get_or_create(email="test.buyer@egoola.com", defaults=dict(
    name="Test Buyer", phone="+8801700000003", password=pw))
```

## Rules for test data

- Smoke tests create their own temporary rows (names starting with "Smoke" or
  "Demo") and delete them afterwards. If you find leftovers, they are safe to remove.
- Don't change these accounts' passwords or types — Postman collections and
  smoke tests depend on them.
- This file contains plain-text dev credentials on purpose. Never reuse these
  passwords anywhere real.
