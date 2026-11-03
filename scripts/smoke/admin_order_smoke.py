#!/usr/bin/env python3
"""Smoke test: admin oversight of orders.

    GET   /orders/orders/           every product order (cursor-paginated)
    GET   /orders/orders/{id}/      full detail: buyer, seller, items, address,
                                     payment (+ both status-change histories, nested),
                                     plus the audit columns
    PATCH /orders/orders/{id}/      {"status": "...", "reason": "..."} — any
                                     status, at any time, no transition check

See buyer_order_smoke.py for checkout and seller_order_smoke.py for the
seller's own step-by-step lifecycle and the payment auto-flip on delivered.
Everything it creates is named "Smoke AOrd ..." and removed at the end (and
at the start). Runs against SMOKE_BASE (default http://127.0.0.1:8000).
Standard library only.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:8000") + "/api/v1"
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PRODUCT_CATEGORY = 18
COUNTRY, STATE, CITY = 126, 13, 8
PASS = FAIL = 0


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, (json.loads(raw) if raw else None)
        except ValueError:
            return err.code, None


def check(label, expected, actual):
    global PASS, FAIL
    if expected == actual:
        PASS += 1
        print(f"OK   {label} (got {actual})")
    else:
        FAIL += 1
        print(f"FAIL {label} (expected {expected}, got {actual})")


def shell(code):
    out = subprocess.run(["uv", "run", "manage.py", "shell", "-c", code], cwd=SERVER_DIR, capture_output=True, text=True).stdout
    return out.strip().splitlines()[-1] if out.strip() else ""


def ensure_thana():
    out = shell(
        "from apps.geography.models import Thana\n"
        "t = Thana.objects.filter(slug='smoke-aord-thana').first() or Thana.objects.create(\n"
        f"    name='Smoke AOrd Thana', city_id={CITY}, state_id={STATE}, country_id={COUNTRY}, slug='smoke-aord-thana')\n"
        "print(t.id)\n"
    )
    return int(out)


def cleanup():
    shell(
        "from apps.accounts.models import Seller, User\n"
        "from apps.catalog.models import Listing\n"
        "from apps.orders.models import Address, Cart, CartItem, Order, OrderItem, OrderStatusChangeHistory, Payment, PaymentStatusChangeHistory\n"
        "orders = Order.objects.filter(seller__email__istartswith='smoke.aord')\n"
        "OrderStatusChangeHistory.objects.filter(order__in=orders).delete()\n"
        "PaymentStatusChangeHistory.objects.filter(order__in=orders).delete()\n"
        "Payment.objects.filter(order__in=orders).delete()\n"
        "OrderItem.objects.filter(order__in=orders).delete()\n"
        "addr_ids = list(orders.values_list('address_id', flat=True))\n"
        "orders.update(payment=None)\n"
        "orders.delete()\n"
        "Address.objects.filter(id__in=addr_ids).delete()\n"
        "Address.objects.filter(name__istartswith='Smoke AOrd').delete()\n"
        "CartItem.objects.filter(cart__seller__email__istartswith='smoke.aord').delete()\n"
        "Cart.objects.filter(seller__email__istartswith='smoke.aord').delete()\n"
        "Listing.all_objects.filter(title__istartswith='Smoke AOrd').delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.aord').delete()\n"
        "User.objects.filter(phone__startswith='+8801700097').delete()\n"
    )


cleanup()
THANA = ensure_thana()

s, admin_login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = admin_login["access"]
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731

s, seller_login = call("POST", "/auth/seller/login/", body={"phone": "0100000002", "password": "Test@12345"})
ST = seller_login["access"]

s, cod_list = A("GET", "/orders/payment-gateways/?search=Cash%20on%20Delivery")
GATEWAY = next(g["id"] for g in cod_list["results"] if g["slug"] == "cash-on-delivery")

s, seller = A("POST", "/accounts/sellers/", {
    "name": "Smoke AOrd Seller", "email": "smoke.aord.seller@example.com",
    "phone": "+8801700097500", "password": "Sell@12345",
})
assert s == 201, seller
SELLER = seller["id"]

s, product = A("POST", "/catalog/listings/", {
    "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general", "status": "approved",
    "title": "Smoke AOrd Product", "description": "d", "seller": SELLER, "price": "60", "stock_qty": 100,
})
assert s == 201, product
LISTING, SKU = product["id"], product["skus"][0]["id"]

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke AOrd Buyer", "phone": "+8801700097001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

s, addr = B("POST", "/buyer/addresses/", {
    "name": "Smoke AOrd Addr", "phone": "+8801711110005", "country": COUNTRY, "state": STATE, "city": CITY,
    "thana": THANA, "address_line1": "House 8",
})
assert s == 201, addr
ADDR = addr["id"]

s, _ = B("POST", "/buyer/cart/items/?type=product", {"listing": LISTING, "listing_sku": SKU, "qty": 1})
assert s == 201, _
s, summary = B("GET", "/buyer/cart/summary/")
CART = next(c["id"] for c in summary["carts"] if c["seller"]["id"] == SELLER)
s, order = B("POST", "/buyer/orders/", {"cart": CART, "address": ADDR, "payment_gateway": GATEWAY})
assert s == 201, order
ORDER = order["id"]

print("\n=== Auth ===")
check("no token -> 401", 401, call("GET", "/orders/orders/")[0])
check("seller token -> 403", 403, call("GET", "/orders/orders/", ST)[0])
check("buyer token -> 403", 403, B("GET", "/orders/orders/")[0])

print("\n=== List / filter / detail ===")
s, listing_page = A("GET", "/orders/orders/")
check("cursor shape", True, all(k in listing_page for k in ("next", "previous", "results")))
check("it's in the unfiltered list", True, any(o["id"] == ORDER for o in listing_page["results"]))
s, by_buyer = A(f"GET", f"/orders/orders/?buyer={buyer_reg['id']}")
check("filter by buyer", [ORDER], [o["id"] for o in by_buyer["results"]])
s, by_seller = A("GET", f"/orders/orders/?seller={SELLER}")
check("filter by seller", [ORDER], [o["id"] for o in by_seller["results"]])
s, by_status = A("GET", "/orders/orders/?status=pending")
check("filter by status matches", True, all(o["status"] == "pending" for o in by_status["results"]))
s, by_type = A("GET", "/orders/orders/?order_type=product")
check("filter by order_type matches", True, all(o["order_type"] == "product" for o in by_type["results"]))

s, detail = A("GET", f"/orders/orders/{ORDER}/")
check("detail -> 200", 200, s)
check("buyer nested", "Smoke AOrd Buyer", detail["buyer"]["name"])
check("seller nested", "Smoke AOrd Seller", detail["seller"]["name"])
check("payment nested", "due", detail["payment"]["status"])
check("audit columns present", True, all(k in detail for k in ("created_by", "creator_type", "creator_name")))
check("unknown id -> 404", 404, A("GET", "/orders/orders/999999/")[0])

print("\n=== Any status, any time, no transition check ===")
s, jumped = A("PATCH", f"/orders/orders/{ORDER}/", {"status": "delivered"})
check("admin can jump straight from pending to delivered -> 200", 200, s)
check("status is delivered", "delivered", jumped["status"])
check("payment auto-flipped to paid (same rule as the seller's own delivered)", "paid", jumped["payment"]["status"])

s, backwards = A("PATCH", f"/orders/orders/{ORDER}/", {"status": "pending"})
check("admin can even move it backwards -> 200", 200, s)
check("status back to pending", "pending", backwards["status"])

s, rejected = A("PATCH", f"/orders/orders/{ORDER}/", {"status": "rejected", "reason": "Smoke AOrd admin reason"})
check("admin reject with reason -> 200", 200, s)
check("rejected_reason recorded", "Smoke AOrd admin reason", rejected["rejected_reason"])

s, cancelled = A("PATCH", f"/orders/orders/{ORDER}/", {"status": "cancelled", "reason": "Smoke AOrd admin cancel"})
check("admin cancel from rejected (still no restriction) -> 200", 200, s)
check("cancelled_reason recorded", "Smoke AOrd admin cancel", cancelled["cancelled_reason"])

s, final = A("GET", f"/orders/orders/{ORDER}/")
check(
    "every admin move landed its own history row",
    ["delivered", "pending", "rejected", "cancelled"],
    [h["current_status"] for h in reversed(final["status_histories"][:4])],
)

cleanup()
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
