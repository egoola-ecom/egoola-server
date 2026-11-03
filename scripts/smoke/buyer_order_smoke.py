#!/usr/bin/env python3
"""Smoke test: the buyer's own orders (checkout through cancel).

    POST  /buyer/orders/            checkout: {"cart", "address", "payment_gateway"}
    GET   /buyer/orders/            my orders (page-paginated)
    GET   /buyer/orders/{id}/       detail: seller, items, address, payment (+ both
                                    status-change histories, nested)
    PATCH /buyer/orders/{id}/       for now, only {"status": "cancelled"}

Checkout creates the Order, its OrderItems, a Payment (status `due` — cash
on delivery is the only gateway today) and the opening history row on each,
and closes the cart it was built from. See seller_order_smoke.py for the
seller's own accept/reject/ship/deliver side and the payment flipping to
`paid`, and admin_order_smoke.py for the admin override. Everything it
creates is named "Smoke BOrd ..." and removed at the end (and at the start).
Runs against SMOKE_BASE (default http://127.0.0.1:8000). Standard library only.
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
        "t = Thana.objects.filter(slug='smoke-bord-thana').first() or Thana.objects.create(\n"
        f"    name='Smoke BOrd Thana', city_id={CITY}, state_id={STATE}, country_id={COUNTRY}, slug='smoke-bord-thana')\n"
        "print(t.id)\n"
    )
    return int(out)


def cleanup():
    shell(
        "from apps.accounts.models import Seller, User\n"
        "from apps.catalog.models import Listing\n"
        "from apps.orders.models import Address, Cart, CartItem, Order, OrderItem, OrderStatusChangeHistory, Payment, PaymentStatusChangeHistory\n"
        "orders = Order.objects.filter(buyer__phone__startswith='+8801700095')\n"
        "OrderStatusChangeHistory.objects.filter(order__in=orders).delete()\n"
        "PaymentStatusChangeHistory.objects.filter(order__in=orders).delete()\n"
        "Payment.objects.filter(order__in=orders).delete()\n"
        "OrderItem.objects.filter(order__in=orders).delete()\n"
        "addr_ids = list(orders.values_list('address_id', flat=True))\n"
        "orders.update(payment=None)\n"
        "orders.delete()\n"
        "Address.objects.filter(id__in=addr_ids).delete()\n"
        "Address.objects.filter(name__istartswith='Smoke BOrd').delete()\n"
        "CartItem.objects.filter(cart__buyer__phone__startswith='+8801700095').delete()\n"
        "Cart.objects.filter(buyer__phone__startswith='+8801700095').delete()\n"
        "Listing.all_objects.filter(title__istartswith='Smoke BOrd').delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.bord').delete()\n"
        "User.objects.filter(phone__startswith='+8801700095').delete()\n"
    )


cleanup()
THANA = ensure_thana()

s, admin_login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = admin_login["access"]
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731

s, cod_list = A("GET", "/orders/payment-gateways/?search=Cash%20on%20Delivery")
GATEWAY = next(g["id"] for g in cod_list["results"] if g["slug"] == "cash-on-delivery")

s, seller = A("POST", "/accounts/sellers/", {
    "name": "Smoke BOrd Seller", "email": "smoke.bord.seller@example.com",
    "phone": "+8801700095500", "password": "Sell@12345",
})
assert s == 201, seller
SELLER = seller["id"]

s, product = A("POST", "/catalog/listings/", {
    "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general", "status": "approved",
    "title": "Smoke BOrd Product", "description": "d", "seller": SELLER, "price": "100", "stock_qty": 50,
})
assert s == 201, product
LISTING, SKU = product["id"], product["skus"][0]["id"]

s, no_seller_product = A("POST", "/catalog/listings/", {
    "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general", "status": "approved",
    "title": "Smoke BOrd No-Seller Product", "description": "d", "price": "50", "stock_qty": 50,
})
assert s == 201, no_seller_product
NS_LISTING, NS_SKU = no_seller_product["id"], no_seller_product["skus"][0]["id"]

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke BOrd Buyer", "phone": "+8801700095001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

s, buyer_reg2 = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke BOrd Buyer Two", "phone": "+8801700095002", "password": "Buy@12345",
})
assert s == 201, buyer_reg2
BT2 = buyer_reg2["access"]

s, addr = B("POST", "/buyer/addresses/", {
    "name": "Smoke BOrd Addr", "phone": "+8801711110002", "country": COUNTRY, "state": STATE, "city": CITY,
    "thana": THANA, "address_line1": "House 5",
})
assert s == 201, addr
ADDR = addr["id"]


def add_to_cart(listing_id, sku_id, qty, token=BT):
    s, _ = call("POST", "/buyer/cart/items/?type=product", token, {"listing": listing_id, "listing_sku": sku_id, "qty": qty})
    assert s == 201, _


def cart_for(seller_id, token=BT):
    s, summary = call("GET", "/buyer/cart/summary/", token)
    for c in summary["carts"]:
        if (c["seller"]["id"] if c["seller"] else None) == seller_id:
            return c["id"]
    raise AssertionError(f"no cart for seller {seller_id}")


print("\n=== Checkout validation ===")
check("no token -> 401", 401, call("POST", "/buyer/orders/")[0])

add_to_cart(NS_LISTING, NS_SKU, 1)
ns_cart = cart_for(None)
s, r = B("POST", "/buyer/orders/", {"cart": ns_cart, "address": ADDR, "payment_gateway": GATEWAY})
check("a no-seller cart cannot be checked out -> 400", 400, s)

add_to_cart(LISTING, SKU, 2)
CART = cart_for(SELLER)
s, r = call("POST", "/buyer/orders/", BT2, {"cart": CART, "address": ADDR, "payment_gateway": GATEWAY})
check("checking out someone else's cart -> 400", 400, s)

s, addr2 = B("POST", "/buyer/addresses/", {
    "name": "Smoke BOrd Addr2", "phone": "+8801711110003", "country": COUNTRY, "state": STATE, "city": CITY,
    "thana": THANA, "address_line1": "House 6",
})
s, r = call("POST", "/buyer/orders/", BT2, {"cart": CART, "address": addr2["id"], "payment_gateway": GATEWAY})
check("checking out with someone else's address -> 400", 400, s)

print("\n=== Checkout ===")
s, order = B("POST", "/buyer/orders/", {"cart": CART, "address": ADDR, "payment_gateway": GATEWAY})
check("checkout -> 201", 201, s)
check("status starts pending", "pending", order["status"])
check("payment_status starts due", "due", order["payment_status"])
check("subtotal = main price x qty", "200.00", order["subtotal"])
check("payable = subtotal (no delivery/discount yet)", "200.00", order["payable"])
check("one order item", 1, len(order["items"]))
check("item total = price x qty", "200.00", order["items"][0]["total"])
check("payment amount matches payable", "200.00", order["payment"]["amount"])
check("payment method is the gateway's name", "Cash on Delivery", order["payment"]["method"])
check("payment gateway_slug snapshot", "cash-on-delivery", order["payment"]["gateway_slug"])
check("payment has its opening history row", [(None, "due")], [(h["previous_status"], h["current_status"]) for h in order["payment"]["status_histories"]])
check("order has its opening history row", [(None, "pending")], [(h["previous_status"], h["current_status"]) for h in order["status_histories"]])
check("address snapshot carries through", "House 5", order["address"]["address_line1"])
ORDER = order["id"]

s, r = B("POST", "/buyer/orders/", {"cart": CART, "address": ADDR, "payment_gateway": GATEWAY})
check("the same (now-closed) cart cannot be checked out again -> 400", 400, s)

print("\n=== Empty cart ===")
add_to_cart(LISTING, SKU, 1)
EMPTY_CART = cart_for(SELLER)
s, cart_detail = B("GET", "/buyer/cart/?type=product&seller=" + str(SELLER))
item_id = cart_detail["items"][0]["id"]
check("remove the only line -> 204", 204, B("DELETE", f"/buyer/cart/items/{item_id}/")[0])
s, r = B("POST", "/buyer/orders/", {"cart": EMPTY_CART, "address": ADDR, "payment_gateway": GATEWAY})
check("an emptied cart cannot be checked out -> 400", 400, s)

print("\n=== List / detail / scoping ===")
s, listing_page = B("GET", "/buyer/orders/")
check("page shape", True, all(k in listing_page for k in ("count", "page", "page_size", "total_pages", "results")))
check("my order is in it", True, any(o["id"] == ORDER for o in listing_page["results"]))
check("another buyer's list doesn't show it", False, any(o["id"] == ORDER for o in call("GET", "/buyer/orders/", BT2)[1]["results"]))
check("another buyer gets 404 on my order id", 404, call("GET", f"/buyer/orders/{ORDER}/", BT2)[0])

print("\n=== The old dedicated /cancel/ action is gone ===")
check("POST .../cancel/ -> 404 now", 404, B("POST", f"/buyer/orders/{ORDER}/cancel/")[0])

print("\n=== Generalized PATCH: only cancelled is allowed ===")
s, r = B("PATCH", f"/buyer/orders/{ORDER}/", {"status": "delivered"})
check("buyer cannot move to delivered -> 400", 400, s)
check("another buyer cannot cancel my order -> 404", 404, call("PATCH", f"/buyer/orders/{ORDER}/", BT2, {"status": "cancelled"})[0])

s, cancelled = B("PATCH", f"/buyer/orders/{ORDER}/", {"status": "cancelled", "reason": "Smoke BOrd changed my mind"})
check("cancel -> 200", 200, s)
check("status now cancelled", "cancelled", cancelled["status"])
check("cancelled_reason recorded", "Smoke BOrd changed my mind", cancelled["cancelled_reason"])
check("history gained the cancel row", ("pending", "cancelled"), (cancelled["status_histories"][0]["previous_status"], cancelled["status_histories"][0]["current_status"]))
check("cancel history carries the reason", "Smoke BOrd changed my mind", cancelled["status_histories"][0]["reason"])

s, r = B("PATCH", f"/buyer/orders/{ORDER}/", {"status": "cancelled"})
check("cancelling an already-cancelled order -> 400", 400, s)

cleanup()
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
