#!/usr/bin/env python3
"""Smoke test: the buyer's own wishlist (favourites).

    GET    /buyer/favourites/?type=product|service
    POST   /buyer/favourites/
    DELETE /buyer/favourites/{listing_id}/

A plain, idempotent toggle (unlike the cart): saving twice changes nothing,
removing a listing that was never saved is not an error. A favourite survives
its listing going private (seller inactive, listing rejected) but drops out
of the list until it is public again. Everything it creates is named
"Smoke Fav ..." and removed at the end (and at the start). Runs against
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
        "from apps.accounts.models import Seller, User\n"
        "from apps.catalog.models import Listing\n"
        "from apps.engagement.models import Favourite\n"
        "Listing.all_objects.filter(title__istartswith='Smoke Fav').delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.fav.').delete()\n"
        "User.objects.filter(phone__startswith='+8801700095').delete()\n"
        "Favourite.objects.filter(buyer__phone__startswith='+8801700095').delete()\n"
    )


cleanup()

s, admin_login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = admin_login["access"]
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731

s, seller = A("POST", "/accounts/sellers/", {
    "name": "Smoke Fav Seller", "email": "smoke.fav.seller@example.com",
    "phone": "+8801700095000", "password": "Sell@12345",
})
assert s == 201, seller
SELLER = seller["id"]

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke Fav Buyer", "phone": "+8801700095001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731


def product(title, **extra):
    body = {
        "category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general",
        "title": title, "description": "d", "seller": SELLER, "price": "100",
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


TEE = product("Smoke Fav Tee")
CLEANING = gig("Smoke Fav Cleaning")

print("=== Empty list ===")
s, empty = B("GET", "/buyer/favourites/")
check("empty list -> 200", 200, s)
check("count 0, results []", (0, []), (empty["count"], empty["results"]))

print("\n=== Save / idempotent / list ===")
s, fav = B("POST", "/buyer/favourites/", {"listing": TEE["id"]})
check("save -> 201", 201, s)
FAV_ID = fav["id"]
check("row shows the listing's title and type", ("Smoke Fav Tee", "product"), (fav["listing"]["title"], fav["catalog_type"]))

s, fav_again = B("POST", "/buyer/favourites/", {"listing": TEE["id"]})
check("saving again -> 200 (idempotent, not a duplicate)", (200, FAV_ID), (s, fav_again["id"]))

s, gfav = B("POST", "/buyer/favourites/", {"listing": CLEANING["id"]})
check("save a gig -> 201", 201, s)

s, listed = B("GET", "/buyer/favourites/")
check("both saved, newest first", ["Smoke Fav Cleaning", "Smoke Fav Tee"], [r["listing"]["title"] for r in listed["results"]])

print("\n=== Filter by type ===")
s, prod_only = B("GET", "/buyer/favourites/?type=product")
check("type=product -> only the tee", ["Smoke Fav Tee"], [r["listing"]["title"] for r in prod_only["results"]])
s, svc_only = B("GET", "/buyer/favourites/?type=service")
check("type=service -> only the gig", ["Smoke Fav Cleaning"], [r["listing"]["title"] for r in svc_only["results"]])
check("bad type -> 400", 400, B("GET", "/buyer/favourites/?type=bogus")[0])

print("\n=== Validation and auth ===")
check("unknown listing -> 400", 400, B("POST", "/buyer/favourites/", {"listing": 999999999})[0])
check("no token -> 401", 401, call("GET", "/buyer/favourites/")[0])
s, slogin = call("POST", "/auth/seller/login/", body={"phone": "+8801700095000", "password": "Sell@12345"})
check("a seller token -> 403", 403, call("GET", "/buyer/favourites/", token=slogin.get("access"))[0])

print("\n=== Drops out (not deleted) when the listing goes private ===")
A("PATCH", f"/accounts/sellers/{SELLER}/", {"status": "inactive"})
s, hidden = B("GET", "/buyer/favourites/")
check("seller inactive -> both favourites hidden", [], hidden["results"])
A("PATCH", f"/accounts/sellers/{SELLER}/", {"status": "active"})
s, back = B("GET", "/buyer/favourites/")
check("seller active again -> both favourites are back", 2, back["count"])

print("\n=== Per-buyer scoping ===")
s, other_reg = call("POST", "/auth/buyer/register/", body={"name": "Smoke Fav Buyer Two", "phone": "+8801700095002", "password": "Buy@12345"})
OT = other_reg["access"]
s, other_list = call("GET", "/buyer/favourites/", token=OT)
check("another buyer sees none of these", (200, 0), (s, other_list["count"]))

print("\n=== Remove ===")
check("remove -> 204", 204, B("DELETE", f"/buyer/favourites/{TEE['id']}/")[0])
check("removing again -> still 204 (idempotent)", 204, B("DELETE", f"/buyer/favourites/{TEE['id']}/")[0])
check("removing a never-saved listing id -> still 204", 204, B("DELETE", "/buyer/favourites/88888888/")[0])
s, after = B("GET", "/buyer/favourites/")
check("only the gig remains", ["Smoke Fav Cleaning"], [r["listing"]["title"] for r in after["results"]])

cleanup()
shell("from apps.accounts.models import User\nUser.objects.filter(phone__in=['+8801700095002']).delete()\n")

print("\n=== Cleanup ===")
check("no Smoke Fav listings left", 0, int(shell("from apps.catalog.models import Listing; print(Listing.all_objects.filter(title__istartswith='Smoke Fav').count())") or 0))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
