#!/usr/bin/env python3
"""Smoke test: the seller's own orders (accept through delivered).

    GET   /seller/orders/            orders placed with me (cursor-paginated)
    GET   /seller/orders/{id}/       detail: buyer, items, address, payment
                                      (+ both status-change histories, nested)
    PATCH /seller/orders/{id}/       move it forward one step:
                                      pending -> accepted|rejected(reason required)
                                      accepted -> in_progress -> shipped -> delivered

Delivered also flips the payment from `due` to `paid` (both on the Payment
row and the order's own denormalized `payment_status`), and writes its own
PaymentStatusChangeHistory row — in addition to the order's own
OrderStatusChangeHistory row for the delivered move itself. See
admin_order_smoke.py for the admin's any-status-any-time override.
Everything it creates is named "Smoke SOrd ..." and removed at the end (and
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
PRODUCT_CATEGORY, SERVICE_CATEGORY = 18, 29
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
        "t = Thana.objects.filter(slug='smoke-sord-thana').first() or Thana.objects.create(\n"
        f"    name='Smoke SOrd Thana', city_id={CITY}, state_id={STATE}, country_id={COUNTRY}, slug='smoke-sord-thana')\n"
        "print(t.id)\n"
    )
    return int(out)


def cleanup():
    shell(
        "from apps.accounts.models import Seller, User\n"
        "from apps.catalog.models import Listing\n"
        "from apps.orders.models import Address, Cart, CartItem, Order, OrderItem, OrderStatusChangeHistory, Payment, PaymentStatusChangeHistory\n"
        "orders = Order.objects.filter(seller__email__istartswith='smoke.sord')\n"
        "OrderStatusChangeHistory.objects.filter(order__in=orders).delete()\n"
        "PaymentStatusChangeHistory.objects.filter(order__in=orders).delete()\n"
        "Payment.objects.filter(order__in=orders).delete()\n"
        "OrderItem.objects.filter(order__in=orders).delete()\n"
        "addr_ids = list(orders.values_list('address_id', flat=True))\n"
        "orders.update(payment=None)\n"
        "orders.delete()\n"
        "Address.objects.filter(id__in=addr_ids).delete()\n"
        "Address.objects.filter(name__istartswith='Smoke SOrd').delete()\n"
        "CartItem.objects.filter(cart__seller__email__istartswith='smoke.sord').delete()\n"
        "Cart.objects.filter(seller__email__istartswith='smoke.sord').delete()\n"
        "Listing.all_objects.filter(title__istartswith='Smoke SOrd').delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.sord').delete()\n"
        "User.objects.filter(phone__startswith='+8801700096').delete()\n"
    )


cleanup()
THANA = ensure_thana()

s, admin_login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = admin_login["access"]
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731

s, cod_list = A("GET", "/orders/payment-gateways/?search=Cash%20on%20Delivery")
GATEWAY = next(g["id"] for g in cod_list["results"] if g["slug"] == "cash-on-delivery")

s, seller = A("POST", "/accounts/sellers/", {
    "name": "Smoke SOrd Seller", "email": "smoke.sord.seller@example.com",
    "phone": "+8801700096500", "password": "Sell@12345",
})
assert s == 201, seller
SELLER = seller["id"]

s, seller2 = A("POST", "/accounts/sellers/", {
    "name": "Smoke SOrd Seller Two", "email": "smoke.sord.seller2@example.com",
    "phone": "+8801700096501", "password": "Sell@12345",
})
assert s == 201, seller2

s, product = A("POST", "/catalog/listings/", {
    "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general", "status": "approved",
    "title": "Smoke SOrd Product", "description": "d", "seller": SELLER, "price": "80", "stock_qty": 100,
})
assert s == 201, product
LISTING, SKU = product["id"], product["skus"][0]["id"]

s, gig = A("POST", "/catalog/gigs/", {
    "category": SERVICE_CATEGORY, "catalog_type": "service", "title": "Smoke SOrd Cleaning",
    "description": "d", "seller": SELLER, "price": "300", "price_type": "fixed",
})
assert s == 201, gig
GIG, GIG_SKU = gig["id"], gig["skus"][0]["id"]

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke SOrd Buyer", "phone": "+8801700096001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

s, addr = B("POST", "/buyer/addresses/", {
    "name": "Smoke SOrd Addr", "phone": "+8801711110004", "country": COUNTRY, "state": STATE, "city": CITY,
    "thana": THANA, "address_line1": "House 7",
})
assert s == 201, addr
ADDR = addr["id"]


def checkout(qty):
    s, _ = call("POST", "/buyer/cart/items/?type=product", BT, {"listing": LISTING, "listing_sku": SKU, "qty": qty})
    assert s == 201, _
    s, summary = B("GET", "/buyer/cart/summary/")
    cart_id = next(c["id"] for c in summary["carts"] if c["seller"] and c["seller"]["id"] == SELLER and c["cart_type"] == "product")
    s, order = B("POST", "/buyer/orders/", {"cart": cart_id, "address": ADDR, "payment_gateway": GATEWAY})
    assert s == 201, order
    return order["id"]


def gig_checkout(duration):
    s, _ = call("POST", "/buyer/cart/items/?type=service", BT, {"listing": GIG, "listing_sku": GIG_SKU, "duration": duration})
    assert s == 201, _
    s, summary = B("GET", "/buyer/cart/summary/")
    cart_id = next(c["id"] for c in summary["carts"] if c["seller"] and c["seller"]["id"] == SELLER and c["cart_type"] == "service")
    s, order = B("POST", "/buyer/orders/", {"cart": cart_id, "address": ADDR, "payment_gateway": GATEWAY})
    assert s == 201, order
    return order["id"]


ORDER = checkout(1)
ORDER_REJECT = checkout(1)
ORDER_SKIP = checkout(1)
GIG_ORDER = gig_checkout(2)

s, seller_login = call("POST", "/auth/seller/login/", body={"phone": "+8801700096500", "password": "Sell@12345"})
ST = seller_login["access"]
S = lambda m, p, b=None: call(m, p, ST, b)  # noqa: E731

s, seller2_login = call("POST", "/auth/seller/login/", body={"phone": "+8801700096501", "password": "Sell@12345"})
ST2 = seller2_login["access"]

print("\n=== Auth / scoping ===")
check("no token -> 401", 401, call("GET", "/seller/orders/")[0])
check("a buyer token -> 403", 403, call("GET", "/seller/orders/", BT)[0])
check("an admin token -> 403", 403, call("GET", "/seller/orders/", AT)[0])
check("a buyer token on PATCH -> 403", 403, call("PATCH", f"/seller/orders/{ORDER}/", BT, {"status": "accepted"})[0])
check("my orders list is cursor-shaped", True, all(k in S("GET", "/seller/orders/")[1] for k in ("next", "previous", "results")))
check("another seller's list doesn't show it", False, any(o["id"] == ORDER for o in call("GET", "/seller/orders/", ST2)[1]["results"]))
check("another seller gets 404 on my order id", 404, call("GET", f"/seller/orders/{ORDER}/", ST2)[0])
check("another seller cannot act on my order -> 404", 404, call("PATCH", f"/seller/orders/{ORDER}/", ST2, {"status": "accepted"})[0])

print("\n=== Filter ===")
s, pending_only = S("GET", "/seller/orders/?status=pending")
check("status filter matches", True, all(o["status"] == "pending" for o in pending_only["results"]))
s, product_only = S("GET", "/seller/orders/?order_type=product")
check("order_type filter matches", True, all(o["order_type"] == "product" for o in product_only["results"]))
check("the gig order is excluded by order_type=product", False, any(o["id"] == GIG_ORDER for o in product_only["results"]))

print("\n=== Gig (service) order — same list, same lifecycle ===")
s, all_orders = S("GET", "/seller/orders/")
check("both the product and a gig order are in the plain list", {ORDER, GIG_ORDER}, {o["id"] for o in all_orders["results"]} & {ORDER, GIG_ORDER})
s, gig_detail = S("GET", f"/seller/orders/{GIG_ORDER}/")
check("gig order_type in detail", "service", gig_detail["order_type"])
check("gig item carries duration/price_type, no qty", (2, "fixed", None), (gig_detail["items"][0]["duration"], gig_detail["items"][0]["price_type_snapshot"], gig_detail["items"][0]["qty"]))
check("gig: pending -> delivered directly -> 400", 400, S("PATCH", f"/seller/orders/{GIG_ORDER}/", {"status": "delivered"})[0])
check("gig accept -> 200", 200, S("PATCH", f"/seller/orders/{GIG_ORDER}/", {"status": "accepted"})[0])
check("gig in_progress -> 200", 200, S("PATCH", f"/seller/orders/{GIG_ORDER}/", {"status": "in_progress"})[0])
check("gig shipped -> 200", 200, S("PATCH", f"/seller/orders/{GIG_ORDER}/", {"status": "shipped"})[0])
s, gig_delivered = S("PATCH", f"/seller/orders/{GIG_ORDER}/", {"status": "delivered"})
check("gig delivered -> 200, same transitions as a product", (200, "delivered", "paid"), (s, gig_delivered["status"], gig_delivered["payment_status"]))

print("\n=== Detail shape ===")
s, detail = S("GET", f"/seller/orders/{ORDER}/")
check("detail -> 200", 200, s)
check("buyer info present", "Smoke SOrd Buyer", detail["buyer"]["name"])
check("payment nested", "due", detail["payment"]["status"])
check("order history nested", 1, len(detail["status_histories"]))
check("payment history nested", 1, len(detail["payment"]["status_histories"]))

print("\n=== Illegal jump ===")
s, r = S("PATCH", f"/seller/orders/{ORDER_SKIP}/", {"status": "delivered"})
check("pending -> delivered directly -> 400", 400, s)
s, r = S("PATCH", f"/seller/orders/{ORDER_SKIP}/", {"status": "shipped"})
check("pending -> shipped directly -> 400", 400, s)

print("\n=== Reject ===")
s, r = S("PATCH", f"/seller/orders/{ORDER_REJECT}/", {"status": "rejected"})
check("reject without reason -> 400", 400, s)
s, rejected = S("PATCH", f"/seller/orders/{ORDER_REJECT}/", {"status": "rejected", "reason": "Smoke SOrd out of stock"})
check("reject with reason -> 200", 200, s)
check("status now rejected", "rejected", rejected["status"])
s, r = S("PATCH", f"/seller/orders/{ORDER_REJECT}/", {"status": "accepted"})
check("a rejected order is terminal for the seller -> 400", 400, s)

print("\n=== Full lifecycle: accept -> in_progress -> shipped -> delivered ===")
check("accept -> 200", 200, S("PATCH", f"/seller/orders/{ORDER}/", {"status": "accepted"})[0])
check("accepted -> rejected is not allowed -> 400", 400, S("PATCH", f"/seller/orders/{ORDER}/", {"status": "rejected", "reason": "x"})[0])
check("in_progress -> 200", 200, S("PATCH", f"/seller/orders/{ORDER}/", {"status": "in_progress"})[0])
check("shipped -> 200", 200, S("PATCH", f"/seller/orders/{ORDER}/", {"status": "shipped"})[0])
check("delivered -> 200", 200, S("PATCH", f"/seller/orders/{ORDER}/", {"status": "delivered"})[0])

s, final = S("GET", f"/seller/orders/{ORDER}/")
check("order status delivered", "delivered", final["status"])
check("payment_status flipped to paid", "paid", final["payment_status"])
check("payment itself is paid", "paid", final["payment"]["status"])
check(
    "payment gained a due -> paid history row",
    True, any(h["previous_status"] == "due" and h["current_status"] == "paid" for h in final["payment"]["status_histories"]),
)
check(
    "order history has the opening row plus all 4 moves", 5,
    len(final["status_histories"]),
)
check("delivered is terminal -> further move -> 400", 400, S("PATCH", f"/seller/orders/{ORDER}/", {"status": "shipped"})[0])

cleanup()
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
