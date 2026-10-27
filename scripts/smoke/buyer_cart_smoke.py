#!/usr/bin/env python3
"""Smoke test: the buyer's own cart(s).

    GET    /buyer/cart/?type=product|service[&seller=]
    POST   /buyer/cart/items/
    PATCH  /buyer/cart/items/{id}/
    DELETE /buyer/cart/items/{id}/
    DELETE /buyer/cart/?type=product|service[&seller=]

One active cart per (buyer, type, seller) — a cart never spans sellers. GET and
DELETE are pure lookups, never creating a cart: with `?seller=` they act on
that seller's cart (`0` = the shared cart for admin-owned listings); without
it, on whichever active cart of that type was touched most recently. `null`
(GET) or a no-op (DELETE) when there is none. Adding a listing picks the cart
by its own catalog_type and seller, merges into an existing line for the same
SKU, and every add-time rule (visibility, qty vs duration, stock). Everything
it creates is named "Smoke Cart ..." and removed at the end (and at the
start). Runs against SMOKE_BASE (default http://127.0.0.1:8000). Standard
library only.
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
        "from apps.accounts.models import Seller, User\n"
        "from apps.catalog.models import Listing\n"
        "Listing.all_objects.filter(title__istartswith='Smoke Cart').delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.cart.').delete()\n"
        "User.objects.filter(phone__startswith='+8801700093').delete()\n"
    )


cleanup()

s, admin_login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = admin_login["access"]
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731

s, seller = A("POST", "/accounts/sellers/", {
    "name": "Smoke Cart Seller", "email": "smoke.cart.seller@example.com",
    "phone": "+8801700093000", "password": "Sell@12345",
})
assert s == 201, seller
SELLER = seller["id"]

s, seller2 = A("POST", "/accounts/sellers/", {
    "name": "Smoke Cart Seller Two", "email": "smoke.cart.seller2@example.com",
    "phone": "+8801700093010", "password": "Sell@12345",
})
assert s == 201, seller2
SELLER2 = seller2["id"]

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke Cart Buyer", "phone": "+8801700093001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731


def product(title, seller_id=SELLER, **extra):
    body = {
        "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general",
        "title": title, "description": "d", "seller": seller_id, "price": "100",
    }
    body.update(extra)
    s, r = A("POST", "/catalog/listings/", body)
    assert s == 201, (title, r)
    return r


def product_no_seller(title, **extra):
    body = {
        "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general",
        "title": title, "description": "d", "price": "100",
    }
    body.update(extra)
    s, r = A("POST", "/catalog/listings/", body)
    assert s == 201, (title, r)
    return r


def gig(title, **extra):
    body = {
        "category": SERVICE_CATEGORY, "catalog_type": "service", "title": title,
        "description": "d", "seller": SELLER, "price": "500", "price_type": "hourly",
    }
    body.update(extra)
    s, r = A("POST", "/catalog/gigs/", body)
    assert s == 201, (title, r)
    return r


def sku_id(listing):
    return listing["skus"][0]["id"]


TEE = product("Smoke Cart Tee")
TEE_SKU = sku_id(TEE)

CLEANING = gig("Smoke Cart Cleaning")
CLEANING_SKU = sku_id(CLEANING)

STOCKED = product("Smoke Cart Stocked")
STOCKED_SKU = sku_id(STOCKED)
A("PATCH", f"/catalog/listings/{STOCKED['id']}/", {"skus": [{"id": STOCKED_SKU, "stock_qty": 2}]})

OTHER = product("Smoke Cart Other")

OTHER_SELLER_TEE = product("Smoke Cart Other Seller Tee", seller_id=SELLER2)
OTHER_SELLER_SKU = sku_id(OTHER_SELLER_TEE)

NO_SELLER_TEE = product_no_seller("Smoke Cart No Seller Tee")
NO_SELLER_SKU = sku_id(NO_SELLER_TEE)
NO_SELLER_TEE2 = product_no_seller("Smoke Cart No Seller Tee Two")
NO_SELLER_SKU2 = sku_id(NO_SELLER_TEE2)

print("=== Nothing yet ===")
check("GET (no seller) -> 200, null", (200, None), B("GET", "/buyer/cart/?type=product"))
check("GET (with seller) -> 200, null", (200, None), B("GET", f"/buyer/cart/?type=product&seller={SELLER}"))

print("\n=== Add to cart ===")
s, item = B("POST", "/buyer/cart/items/", {"listing": TEE["id"], "listing_sku": TEE_SKU, "qty": 2})
check("add product -> 201", 201, s)
check("qty saved", 2, item["qty"])
check("unit_price / line_subtotal", ("100.00", "200.00"), (item["unit_price"], item["line_subtotal"]))
check("no color/size on a plain SKU", (None, None), (item["color"], item["size"]))
ITEM_ID = item["id"]

s, item2 = B("POST", "/buyer/cart/items/", {"listing": TEE["id"], "listing_sku": TEE_SKU, "qty": 3})
check("adding the same SKU again merges (qty sums)", (201, 5), (s, item2["qty"]))
check("merge keeps the same row id", ITEM_ID, item2["id"])

s, cart = B("GET", "/buyer/cart/?type=product")
check("GET with nothing else going on -> this seller's cart", (200, "Smoke Cart Seller"), (s, cart["seller"]["name"]))
check("cart_type", "product", cart["cart_type"])
check("one line after merging", 1, len(cart["items"]))
check("cart subtotal", "500.00", cart["subtotal"])

print("\n=== A different seller's listing gets its own cart, and becomes 'latest' ===")
s, other_seller_item = B("POST", "/buyer/cart/items/", {"listing": OTHER_SELLER_TEE["id"], "listing_sku": OTHER_SELLER_SKU, "qty": 1})
check("add from a second seller -> 201", 201, s)
s, latest = B("GET", "/buyer/cart/?type=product")
check("no-seller-param GET now returns the just-touched (second seller's) cart", (200, "Smoke Cart Seller Two"), (s, latest["seller"]["name"]))
s, s1cart = B("GET", f"/buyer/cart/?type=product&seller={SELLER}")
check("seller1's cart is still there and unaffected, via explicit ?seller=", 1, len(s1cart["items"]))

print("\n=== Touching an older cart again makes it 'latest' once more ===")
s, _ = B("POST", "/buyer/cart/items/", {"listing": TEE["id"], "listing_sku": TEE_SKU, "qty": 1})
s, latest = B("GET", "/buyer/cart/?type=product")
check("re-touching seller1's cart makes it latest again", (200, "Smoke Cart Seller"), (s, latest["seller"]["name"]))

print("\n=== Admin-owned (no-seller) listings share ONE cart ===")
s, no_seller_item = B("POST", "/buyer/cart/items/", {"listing": NO_SELLER_TEE["id"], "listing_sku": NO_SELLER_SKU, "qty": 1})
check("add a no-seller listing -> 201", 201, s)
s, no_seller_item2 = B("POST", "/buyer/cart/items/", {"listing": NO_SELLER_TEE2["id"], "listing_sku": NO_SELLER_SKU2, "qty": 1})
check("add a second no-seller listing -> 201", 201, s)
s, no_seller_cart = B("GET", "/buyer/cart/?type=product&seller=0")
check("both no-seller listings share the same cart (seller=0)", (200, None, 2), (s, no_seller_cart["seller"], len(no_seller_cart["items"])))

print("\n=== A gig gets its own (service) cart, independent of the product carts ===")
s, gitem = B("POST", "/buyer/cart/items/", {"listing": CLEANING["id"], "listing_sku": CLEANING_SKU, "duration": 3})
check("add gig -> 201", 201, s)
check("duration saved, qty stays null", (3, None), (gitem["duration"], gitem["qty"]))
check("gig line_subtotal (rate x duration)", "1500.00", gitem["line_subtotal"])
s, scart = B("GET", "/buyer/cart/?type=service")
check("service cart -> 200, one line", (200, 1), (s, len(scart["items"])))
s, pcart = B("GET", f"/buyer/cart/?type=product&seller={SELLER}")
check("seller1's product cart is untouched by the gig add", 1, len(pcart["items"]))

print("\n=== Validation ===")
check("qty on a gig -> 400", 400, B("POST", "/buyer/cart/items/", {"listing": CLEANING["id"], "listing_sku": CLEANING_SKU, "qty": 1})[0])
check("duration on a product -> 400", 400, B("POST", "/buyer/cart/items/", {"listing": TEE["id"], "listing_sku": TEE_SKU, "duration": 1})[0])
check("missing qty on a product -> 400", 400, B("POST", "/buyer/cart/items/", {"listing": TEE["id"], "listing_sku": TEE_SKU})[0])
check("missing duration on a gig -> 400", 400, B("POST", "/buyer/cart/items/", {"listing": CLEANING["id"], "listing_sku": CLEANING_SKU})[0])
check("SKU that belongs to another listing -> 400", 400, B("POST", "/buyer/cart/items/", {"listing": TEE["id"], "listing_sku": sku_id(OTHER), "qty": 1})[0])
check("unknown listing -> 400", 400, B("POST", "/buyer/cart/items/", {"listing": 999999999, "listing_sku": TEE_SKU, "qty": 1})[0])
check("qty over stock -> 400", 400, B("POST", "/buyer/cart/items/", {"listing": STOCKED["id"], "listing_sku": STOCKED_SKU, "qty": 5})[0])
check("qty within stock -> 201", 201, B("POST", "/buyer/cart/items/", {"listing": STOCKED["id"], "listing_sku": STOCKED_SKU, "qty": 2})[0])
check("GET without ?type -> 400", 400, B("GET", "/buyer/cart/")[0])
check("GET with a bad ?type -> 400", 400, B("GET", "/buyer/cart/?type=bogus")[0])
check("GET with a non-numeric ?seller -> 400", 400, B("GET", "/buyer/cart/?type=product&seller=abc")[0])
check("no token -> 401", 401, call("GET", "/buyer/cart/?type=product")[0])

s, slogin = call("POST", "/auth/seller/login/", body={"phone": "+8801700093000", "password": "Sell@12345"})
check("a seller token -> 403", 403, call("GET", "/buyer/cart/?type=product", token=slogin.get("access"))[0])

print("\n=== Edit / remove a line, scoped to its own buyer ===")
s, patched = B("PATCH", f"/buyer/cart/items/{ITEM_ID}/", {"qty": 1})
check("PATCH qty -> 200, replaces (not adds)", (200, 1), (s, patched["qty"]))
check("PATCH duration on a product line -> 400", 400, B("PATCH", f"/buyer/cart/items/{ITEM_ID}/", {"duration": 1})[0])

s, other_buyer = call("POST", "/auth/buyer/register/", body={"name": "Smoke Cart Buyer Two", "phone": "+8801700093002", "password": "Buy@12345"})
OT = other_buyer["access"]
check("another buyer cannot touch this item -> 404", 404, call("PATCH", f"/buyer/cart/items/{ITEM_ID}/", token=OT, body={"qty": 1})[0])

s, _ = B("DELETE", f"/buyer/cart/items/{ITEM_ID}/")
check("DELETE item -> 204", 204, s)
s, s1cart = B("GET", f"/buyer/cart/?type=product&seller={SELLER}")
check("item gone, the stocked line remains in seller1's cart", 1, len(s1cart["items"]))

print("\n=== Clear one seller's cart only ===")
s, _ = B("DELETE", f"/buyer/cart/?type=product&seller={SELLER}")
check("DELETE (clear seller1 only) -> 204", 204, s)
s, s1cart = B("GET", f"/buyer/cart/?type=product&seller={SELLER}")
check("seller1's cart is now empty but still active and present", (0, True), (len(s1cart["items"]), s1cart["is_active"]))
s, s2cart = B("GET", f"/buyer/cart/?type=product&seller={SELLER2}")
check("the other carts are untouched", 1, len(s2cart["items"]))

print("\n=== DELETE with no seller clears whichever cart is 'latest' ===")
B("POST", "/buyer/cart/items/", {"listing": OTHER_SELLER_TEE["id"], "listing_sku": OTHER_SELLER_SKU, "qty": 1})  # re-touch seller2 -> latest
s, _ = B("DELETE", "/buyer/cart/?type=product")
check("DELETE (no seller) -> 204", 204, s)
s, s2cart = B("GET", f"/buyer/cart/?type=product&seller={SELLER2}")
check("the latest (seller2) cart is now empty", 0, len(s2cart["items"]))
s, no_seller_cart = B("GET", "/buyer/cart/?type=product&seller=0")
check("the no-seller cart, untouched, still has its two lines", 2, len(no_seller_cart["items"]))

print("\n=== DELETE when there is nothing to clear is still a no-op 204 ===")
check("DELETE an unused type -> 204, no error", 204, B("DELETE", "/buyer/cart/?type=service&seller=999999999")[0])

cleanup()
shell(
    "from apps.accounts.models import User\n"
    "User.objects.filter(phone__in=['+8801700093002']).delete()\n"
)
print("\n=== Cleanup ===")
check("no Smoke Cart listings left", 0, int(shell("from apps.catalog.models import Listing; print(Listing.all_objects.filter(title__istartswith='Smoke Cart').count())") or 0))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
