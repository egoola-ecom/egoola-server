#!/usr/bin/env python3
"""Smoke test: admin, read-only oversight of buyers' carts.

    GET /api/v1/orders/carts/           cursor-paginated list, filters, search
    GET /api/v1/orders/carts/{id}/      detail (items, audit columns)

Read-only (no POST/PATCH/DELETE), admin or super-admin, every cart shown
regardless of listing visibility. Everything it creates is named "Smoke
AdminCart ..." and removed at the end (and at the start). Runs against
SMOKE_BASE (default http://127.0.0.1:8000). Standard library only.
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


def cleanup():
    shell(
        "from apps.accounts.models import Seller\n"
        "from apps.catalog.models import Listing\n"
        "from apps.orders.models import Cart\n"
        "Listing.all_objects.filter(title__istartswith='Smoke AdminCart').delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.admincart.').delete()\n"
        "from apps.accounts.models import User\n"
        "User.objects.filter(phone__startswith='+8801700097').delete()\n"
    )


cleanup()

s, admin_login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = admin_login["access"]
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731

s, seller = A("POST", "/accounts/sellers/", {
    "name": "Smoke AdminCart Seller", "email": "smoke.admincart.seller@example.com",
    "phone": "+8801700097000", "password": "Sell@12345",
})
assert s == 201, seller
SELLER = seller["id"]

s, product = A("POST", "/catalog/listings/", {
    "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general",
    "title": "Smoke AdminCart Tee", "description": "d", "seller": SELLER, "price": "100",
})
assert s == 201, product
PRODUCT_ID, PRODUCT_SKU = product["id"], product["skus"][0]["id"]

s, gig = A("POST", "/catalog/gigs/", {
    "category": SERVICE_CATEGORY, "catalog_type": "service", "title": "Smoke AdminCart Cleaning",
    "description": "d", "seller": SELLER, "price": "500", "price_type": "hourly",
})
assert s == 201, gig
GIG_ID, GIG_SKU = gig["id"], gig["skus"][0]["id"]

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke AdminCart Buyer", "phone": "+8801700097001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

B("POST", "/buyer/cart/items/", {"listing": PRODUCT_ID, "listing_sku": PRODUCT_SKU, "qty": 2})
B("POST", "/buyer/cart/items/", {"listing": GIG_ID, "listing_sku": GIG_SKU, "duration": 3})

print("=== Auth ===")
check("no token -> 401", 401, call("GET", "/orders/carts/")[0])
s, slogin = call("POST", "/auth/seller/login/", body={"phone": "+8801700097000", "password": "Sell@12345"})
check("a seller token -> 403", 403, call("GET", "/orders/carts/", token=slogin.get("access"))[0])
check("an admin token -> 200", 200, A("GET", "/orders/carts/")[0])

print("\n=== List shape and content ===")
s, carts = A("GET", "/orders/carts/?search=Smoke+AdminCart+Buyer&ordering=-created_at")
check("list -> 200", 200, s)
check("cursor shape (next/previous, no count)", {"next", "previous", "results"}, set(carts.keys()))
by_type = {row["cart_type"]: row for row in carts["results"] if row["buyer"]["phone"] == "+8801700097001"}
check("both a product and a service cart exist", {"product", "service"}, set(by_type) & {"product", "service"})
check("product cart item_count / subtotal", (1, "200.00"), (by_type["product"]["item_count"], by_type["product"]["subtotal"]))
check("service cart item_count / subtotal", (1, "1500.00"), (by_type["service"]["item_count"], by_type["service"]["subtotal"]))
check("buyer block has contact info", True, "email" in by_type["product"]["buyer"] and "phone" in by_type["product"]["buyer"])

print("\n=== Filters ===")
s, by_buyer_search = A("GET", "/orders/carts/?search=8801700097001")
check("search by buyer email matches at least these two", True, {c["id"] for c in by_type.values()} <= {c["id"] for c in by_buyer_search["results"]})
s, by_cart_type = A("GET", "/orders/carts/?cart_type=service")
check("cart_type=service excludes the product cart", False, by_type["product"]["id"] in [c["id"] for c in by_cart_type["results"]])
s, by_listing = A("GET", f"/orders/carts/?listing={PRODUCT_ID}")
check("filter by listing id finds the product cart", True, by_type["product"]["id"] in [c["id"] for c in by_listing["results"]])
check("filter by listing id excludes the service cart", False, by_type["service"]["id"] in [c["id"] for c in by_listing["results"]])
s, by_active = A("GET", "/orders/carts/?is_active=true")
check("is_active=true includes both (neither checked out)", True, {by_type["product"]["id"], by_type["service"]["id"]} <= {c["id"] for c in by_active["results"]})
s, by_order = A("GET", "/orders/carts/?has_order=true")
check("has_order=true excludes both (no order yet)", True, {by_type["product"]["id"], by_type["service"]["id"]}.isdisjoint({c["id"] for c in by_order["results"]}))

print("\n=== Detail ===")
s, detail = A("GET", f"/orders/carts/{by_type['product']['id']}/")
check("detail -> 200", 200, s)
check("detail has one item line", 1, len(detail["items"]))
item = detail["items"][0]
check("item shows listing, sku, qty, price, availability", True, all(k in item for k in ("listing", "listing_sku", "qty", "unit_price", "line_subtotal", "available")))
check("item carries audit columns", True, all(k in item for k in ("created_by", "creator_type", "creator_name")))
check("cart detail carries audit columns", True, all(k in detail for k in ("created_by", "creator_type", "creator_name")))

print("\n=== Validation ===")
check("bad cart_type -> 400", 400, A("GET", "/orders/carts/?cart_type=bogus")[0])
check("unknown cart id -> 404", 404, A("GET", "/orders/carts/999999999/")[0])

cleanup()
print("\n=== Cleanup ===")
check("no Smoke AdminCart listings left", 0, int(shell("from apps.catalog.models import Listing; print(Listing.all_objects.filter(title__istartswith='Smoke AdminCart').count())") or 0))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
