#!/usr/bin/env python3
"""Smoke test: admin, read-only oversight of buyers' wishlists.

    GET /api/v1/engagement/favourites/          cursor-paginated list, filters, search
    GET /api/v1/engagement/favourites/{id}/     detail (audit columns)

Read-only (no POST/PATCH/DELETE), admin or super-admin, every favourite shown
regardless of listing visibility — `listing_visible` says which, and can be
filtered on. Everything it creates is named "Smoke AdminFav ..." and removed
at the end (and at the start). Runs against SMOKE_BASE (default
http://127.0.0.1:8000). Standard library only.
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
        "Listing.all_objects.filter(title__istartswith='Smoke AdminFav').delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.adminfav.').delete()\n"
        "User.objects.filter(phone__startswith='+8801700098').delete()\n"
    )


cleanup()

s, admin_login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = admin_login["access"]
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731

s, seller = A("POST", "/accounts/sellers/", {
    "name": "Smoke AdminFav Seller", "email": "smoke.adminfav.seller@example.com",
    "phone": "+8801700098000", "password": "Sell@12345",
})
assert s == 201, seller
SELLER = seller["id"]

s, product = A("POST", "/catalog/listings/", {
    "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general",
    "title": "Smoke AdminFav Tee", "description": "d", "seller": SELLER, "price": "100",
})
assert s == 201, product
PRODUCT_ID = product["id"]

s, gig = A("POST", "/catalog/gigs/", {
    "category": SERVICE_CATEGORY, "catalog_type": "service", "title": "Smoke AdminFav Cleaning",
    "description": "d", "seller": SELLER, "price": "500", "price_type": "hourly",
})
assert s == 201, gig
GIG_ID = gig["id"]

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke AdminFav Buyer", "phone": "+8801700098001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

B("POST", "/buyer/favourites/", {"listing": PRODUCT_ID})
B("POST", "/buyer/favourites/", {"listing": GIG_ID})

print("=== Auth ===")
check("no token -> 401", 401, call("GET", "/engagement/favourites/")[0])
s, slogin = call("POST", "/auth/seller/login/", body={"phone": "+8801700098000", "password": "Sell@12345"})
check("a seller token -> 403", 403, call("GET", "/engagement/favourites/", token=slogin.get("access"))[0])
check("an admin token -> 200", 200, A("GET", "/engagement/favourites/")[0])

print("\n=== List shape and content ===")
s, favs = A("GET", "/engagement/favourites/?search=8801700098001")
check("list -> 200", 200, s)
check("cursor shape (next/previous, no count)", {"next", "previous", "results"}, set(favs.keys()))
by_listing = {row["listing"]["id"]: row for row in favs["results"]}
check("both saved listings are there", {PRODUCT_ID, GIG_ID}, set(by_listing) & {PRODUCT_ID, GIG_ID})
check("product row shows catalog_type and seller block", ("product", "Smoke AdminFav Seller"), (by_listing[PRODUCT_ID]["listing"]["catalog_type"], by_listing[PRODUCT_ID]["listing"]["seller"]["name"]))
check("both visible right now", (True, True), (by_listing[PRODUCT_ID]["listing_visible"], by_listing[GIG_ID]["listing_visible"]))

print("\n=== Filters ===")
s, by_type = A("GET", "/engagement/favourites/?catalog_type=service")
check("catalog_type=service excludes the product favourite", False, PRODUCT_ID in [r["listing"]["id"] for r in by_type["results"]])
s, by_listing_filter = A("GET", f"/engagement/favourites/?listing={PRODUCT_ID}")
check("filter by listing id finds only that one", {PRODUCT_ID}, {r["listing"]["id"] for r in by_listing_filter["results"]})
s, by_buyer = A("GET", f"/engagement/favourites/?buyer={by_listing[PRODUCT_ID]['buyer']['id']}")
check("filter by buyer id finds both", {PRODUCT_ID, GIG_ID}, {r["listing"]["id"] for r in by_buyer["results"]} & {PRODUCT_ID, GIG_ID})

print("\n=== listing_visible reacts to the seller's standing ===")
A("PATCH", f"/accounts/sellers/{SELLER}/", {"status": "inactive"})
s, hidden = A("GET", "/engagement/favourites/?listing_visible=false")
check("listing_visible=false now includes both", {PRODUCT_ID, GIG_ID}, {r["listing"]["id"] for r in hidden["results"]} & {PRODUCT_ID, GIG_ID})
s, still_shown = A("GET", "/engagement/favourites/?search=8801700098001")
check("admin still sees them in the plain list (not hidden like the buyer's own view)", {PRODUCT_ID, GIG_ID}, {r["listing"]["id"] for r in still_shown["results"]} & {PRODUCT_ID, GIG_ID})
A("PATCH", f"/accounts/sellers/{SELLER}/", {"status": "active"})
s, visible_again = A("GET", "/engagement/favourites/?listing_visible=true")
check("active again -> listing_visible=true includes both", {PRODUCT_ID, GIG_ID}, {r["listing"]["id"] for r in visible_again["results"]} & {PRODUCT_ID, GIG_ID})

print("\n=== Detail ===")
fav_id = by_listing[PRODUCT_ID]["id"]
s, detail = A("GET", f"/engagement/favourites/{fav_id}/")
check("detail -> 200", 200, s)
check("detail carries audit columns", True, all(k in detail for k in ("created_by", "creator_type", "creator_name")))

print("\n=== Validation ===")
check("bad catalog_type -> 400", 400, A("GET", "/engagement/favourites/?catalog_type=bogus")[0])
check("unknown favourite id -> 404", 404, A("GET", "/engagement/favourites/999999999/")[0])

cleanup()
print("\n=== Cleanup ===")
check("no Smoke AdminFav listings left", 0, int(shell("from apps.catalog.models import Listing; print(Listing.all_objects.filter(title__istartswith='Smoke AdminFav').count())") or 0))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
