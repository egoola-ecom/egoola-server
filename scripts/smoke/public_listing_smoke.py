#!/usr/bin/env python3
"""Smoke test: the public (no login) product and gig APIs and the public seller page.

    GET /public/catalog/products/  and  /products/{id}/
    GET /public/catalog/gigs/      and  /gigs/{id}/
    GET /public/sellers/{id}/

Visibility (approved only, not deleted, seller verified and active, an active SKU),
every filter, ordering, paging, the product / gig / job separation and that nothing
private leaks. Everything it creates is named "Smoke Pub ..." and is removed at the
end (and at the start). Runs against SMOKE_BASE (default http://127.0.0.1:8000).
Standard library only.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
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
        "from apps.catalog.models import Brand, Category, Listing\n"
        "Listing.all_objects.filter(title__istartswith='Smoke Pub').delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.pub.').delete()\n"
        "Brand.objects.filter(name__istartswith='Smoke Pub').delete()\n"
        "Category.objects.filter(name__istartswith='Smoke Pub').order_by('-id').delete()\n"
    )


cleanup()
s, login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
T = login["access"]
A = lambda m, p, b=None: call(m, p, T, b)  # noqa: E731
PUB = "/public/catalog/"
G = lambda path, q="": call("GET", PUB + path + q)  # noqa: E731
titles = lambda r: [x["title"] for x in r["results"]]  # noqa: E731


def mk_seller(n, **extra):
    body = {"name": f"Smoke Pub Seller {n}", "email": f"smoke.pub.{n}@example.com", "phone": f"+88017000961{n:02d}", "password": "Sell@12345"}
    body.update(extra)
    s, r = A("POST", "/accounts/sellers/", body)
    assert s == 201, r
    return r["id"]


S1, S2, S3 = mk_seller(1), mk_seller(2), mk_seller(3)
s, brand = A("POST", "/catalog/brands/", {"name": "Smoke Pub Brand"})
s, child = A("POST", "/catalog/categories/", {"name": "Smoke Pub Child", "slug": "smoke-pub-child", "type": "product", "parent": PRODUCT_CATEGORY, "status": "active", "sort_order": 1})
CHILD = child["id"]


def product(title, seller, **extra):
    body = {"category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general", "title": title, "description": "d", "seller": seller, "price": "100"}
    body.update(extra)
    s, r = A("POST", "/catalog/listings/", body)
    assert s == 201, (title, r)
    return r


def gig(title, seller, **extra):
    body = {"category": SERVICE_CATEGORY, "title": title, "description": "d", "seller": seller}
    body.update(extra)
    s, r = A("POST", "/catalog/gigs/", body)
    assert s == 201, (title, r)
    return r


print("\n=== Setup ===")
p1 = product("Smoke Pub Phone", S1, price="100", discounted_price="80", stock_qty=5, brand=brand["id"], listing_type="brand", model="X1")
p2 = product("Smoke Pub Used Laptop", S1, price="300", stock_qty=0, listing_type="used", category=CHILD)
p3 = product("Smoke Pub Pending", S1, status="pending")
p4 = product("Smoke Pub Rejected", S1, status="rejected", note="no")
p5 = product("Smoke Pub Paused Seller Item", S2)
p6 = product("Smoke Pub Admin Owned", None, price="50")
p7 = product("Smoke Pub Deleted", S1)
p8 = product("Smoke Pub No Active SKU", S1)
A("DELETE", f"/catalog/listings/{p7['id']}/")
A("PATCH", f"/catalog/listings/{p8['id']}/", {"skus": [{"id": p8["skus"][0]["id"], "is_active": False}]})
A("PATCH", f"/accounts/sellers/{S2}/", {"status": "inactive"})
A("PATCH", f"/accounts/sellers/{S3}/", {"verification_status": "pending", "status": "inactive"})
p10 = product("Smoke Pub Pending Seller Item", S3)

g1 = gig("Smoke Pub Cleaning", S1, delivery_days=3, urgent=True, skus=[
    {"price": "50", "price_type": "hourly", "description": "per hour"}, {"price": "1000", "price_type": "weekly"}])
g2 = gig("Smoke Pub Logo", S1, delivery_days=10, price="500", price_type="fixed")
g3 = gig("Smoke Pub Gig Pending", S1, status="pending", price="5", price_type="daily")
g4 = gig("Smoke Pub Gig Paused Seller", S2, price="5", price_type="daily")
g5 = gig("Smoke Pub Gig Discount", S1, delivery_days=1, price="200", discounted_price="150", price_type="daily")
buyer = int(shell("from apps.accounts.models import User; print(User.objects.get(email='test.buyer@egoola.com').id)") or 0)
s, job = A("POST", "/catalog/listings/", {"category": SERVICE_CATEGORY, "catalog_type": "service", "posted_by_role": "buyer_request", "buyer": buyer,
                                          "title": "Smoke Pub Job", "description": "d", "price": "5", "price_type": "fixed"})

print("\n=== Products: visibility ===")
s, r = G("products/", "?search=Smoke%20Pub&page_size=100")
check("no login needed -> 200", 200, s)
check("page format", {"count", "page", "page_size", "total_pages", "results"}, set(r))
check("only approved, live, visible-seller, with an active SKU", {"Smoke Pub Phone", "Smoke Pub Used Laptop", "Smoke Pub Admin Owned"}, set(titles(r)))
check("pending / rejected / deleted / paused seller / unverified seller / no active SKU are hidden", True,
      not {"Smoke Pub Pending", "Smoke Pub Rejected", "Smoke Pub Deleted", "Smoke Pub Paused Seller Item", "Smoke Pub Pending Seller Item", "Smoke Pub No Active SKU"} & set(titles(r)))
check("a gig is not in the products list", False, any("Cleaning" in t for t in titles(r)))
check("an invalid token is ignored", 200, call("GET", PUB + "products/", "garbage")[0])
check("POST is not allowed", 405, call("POST", PUB + "products/", T, {})[0])
row = [x for x in r["results"] if x["title"] == "Smoke Pub Phone"][0]
check("row keys", ["brand", "category", "created_at", "currency", "discounted_price", "id", "image_url", "in_stock", "listing_type", "price", "seller", "slug", "title", "title_bn"], sorted(row))
check("price and discounted price", ("100.00", "80.00"), (row["price"], row["discounted_price"]))
check("brand block", {"id": brand["id"], "name": "Smoke Pub Brand"}, row["brand"])
check("seller block (id, name, profile_pic_url)", {"id": S1, "name": "Smoke Pub Seller 1", "profile_pic_url": None}, row["seller"])
check("category block", ["id", "name", "name_bn", "slug"], sorted(row["category"]))
check("in_stock true / false", (True, False), (row["in_stock"], [x for x in r["results"] if x["title"] == "Smoke Pub Used Laptop"][0]["in_stock"]))
check("an admin-owned listing has seller null", None, [x for x in r["results"] if x["title"] == "Smoke Pub Admin Owned"][0]["seller"])
check("no private fields in a row", True, not ({"status", "note", "requested_at", "created_by", "info_change_logs"} & set(row)))

print("\n=== Products: filters and ordering ===")
q = lambda extra: titles(G("products/", "?search=Smoke%20Pub&page_size=100&" + extra)[1])  # noqa: E731
check("category includes its sub-categories", {"Smoke Pub Used Laptop", "Smoke Pub Phone", "Smoke Pub Admin Owned"}, set(q(f"category={PRODUCT_CATEGORY}")))
check("a sub-category alone", ["Smoke Pub Used Laptop"], q(f"category={CHILD}"))
check("listing_type", ["Smoke Pub Used Laptop"], q("listing_type=used"))
check("brand", ["Smoke Pub Phone"], q(f"brand={brand['id']}"))
check("in_stock=true excludes the sold-out one", False, "Smoke Pub Used Laptop" in q("in_stock=true"))
check("in_stock=false is only the sold-out one", ["Smoke Pub Used Laptop"], q("in_stock=false"))
check("price_min (on the current price)", {"Smoke Pub Used Laptop"}, set(q("price_min=200")))
check("price_max uses the discounted price", {"Smoke Pub Phone", "Smoke Pub Admin Owned"}, set(q("price_max=90")))
check("price_min + price_max", ["Smoke Pub Phone"], q("price_min=60&price_max=90"))
check("seller", {"Smoke Pub Phone", "Smoke Pub Used Laptop"}, set(q(f"seller={S1}")))
check("search by model", ["Smoke Pub Phone"], titles(G("products/", "?search=X1")[1]))
check("search by brand name", ["Smoke Pub Phone"], titles(G("products/", "?search=Smoke%20Pub%20Brand")[1]))
check("ordering price_asc", ["Smoke Pub Admin Owned", "Smoke Pub Phone", "Smoke Pub Used Laptop"], q("ordering=price_asc"))
check("ordering price_desc", ["Smoke Pub Used Laptop", "Smoke Pub Phone", "Smoke Pub Admin Owned"], q("ordering=price_desc"))
check("ordering title", sorted(q("ordering=title")), q("ordering=title"))
check("default order is newest first", ["Smoke Pub Admin Owned", "Smoke Pub Used Laptop", "Smoke Pub Phone"], q(""))
check("ordering=oldest is the reverse", ["Smoke Pub Phone", "Smoke Pub Used Laptop", "Smoke Pub Admin Owned"], q("ordering=oldest"))
s, r = G("products/", "?search=Smoke%20Pub&page_size=2")
check("page_size=2", (2, 1, True), (len(r["results"]), r["page"], r["total_pages"] >= 2))
check("page 2 differs", True, set(titles(r)).isdisjoint(titles(G("products/", "?search=Smoke%20Pub&page_size=2&page=2")[1])))
for bad in ["price_min=-1", "price_min=abc", "price_min=10&price_max=5", "listing_type=other", "ordering=cheap", "category=abc", "in_stock=maybe", "page_size=101", "page=0", "brand=0"]:
    check(f"bad query {bad} -> 400", 400, G("products/", "?" + bad)[0])
check("a page past the last -> 404", 404, G("products/", "?page=99999")[0])
check("no match -> empty page", (200, 0, 0), (lambda x: (x[0], x[1]["count"], x[1]["total_pages"]))(G("products/", "?search=zzzqqq")))

print("\n=== Product detail ===")
s, d = G(f"products/{p1['id']}/")
check("detail -> 200", 200, s)
check("has description, SKUs, tiers, media, location", True, {"description", "skus", "price_tiers", "media", "location", "measurement", "attributes"} <= set(d))
check("SKU rows", ["available_qty", "discounted_price", "id", "in_stock", "is_discount_active", "price", "sku", "variants"], sorted(d["skus"][0]))
check("SKU stock fields", (True, 5, True), (d["skus"][0]["in_stock"], d["skus"][0]["available_qty"], d["skus"][0]["is_discount_active"]))
check("no private fields in the detail", True, not ({"status", "note", "requested_at", "status_change_logs", "info_change_logs", "created_by", "image_path"} & set(d)))
check("the hidden SKU is not shown", True, all(sku["id"] != p8["skus"][0]["id"] for sku in d["skus"]))
for label, hidden in [("pending", p3), ("rejected", p4), ("deleted", p7), ("paused seller", p5), ("unverified seller", p10), ("no active SKU", p8)]:
    check(f"detail of a {label} listing -> 404", 404, G(f"products/{hidden['id']}/")[0])
check("a gig id on the product detail -> 404", 404, G(f"products/{g1['id']}/")[0])
check("a job id on the product detail -> 404", 404, G(f"products/{job['id']}/")[0] if job else 404)
check("an unknown id -> 404", 404, G("products/99999999/")[0])

print("\n=== Gigs ===")
s, r = G("gigs/", "?search=Smoke%20Pub&page_size=100")
check("gigs list -> 200", 200, s)
check("only visible gigs", {"Smoke Pub Cleaning", "Smoke Pub Logo", "Smoke Pub Gig Discount"}, set(titles(r)))
check("a product is not in the gigs list", False, any("Phone" in t for t in titles(r)))
check("a job request is not in the gigs list", False, "Smoke Pub Job" in titles(r))
row = [x for x in r["results"] if x["title"] == "Smoke Pub Cleaning"][0]
check("gig row keys", ["category", "created_at", "currency", "delivery_days", "discounted_price", "id", "image_url", "price", "price_type", "seller", "slug", "title", "title_bn", "urgent"], sorted(row))
check("from price is the cheapest package", ("50.00", "50.00", "hourly"), (row["price"], row["discounted_price"], row["price_type"]))
gq = lambda extra: titles(G("gigs/", "?search=Smoke%20Pub&page_size=100&" + extra)[1])  # noqa: E731
check("price_type=weekly", ["Smoke Pub Cleaning"], gq("price_type=weekly"))
check("price_type=fixed", ["Smoke Pub Logo"], gq("price_type=fixed"))
check("price_type=monthly (none)", [], gq("price_type=monthly"))
s, r = G("gigs/", "?search=Smoke%20Pub&price_type=weekly")
check("with price_type the row shows that package", ("1000.00", "weekly"), (r["results"][0]["price"], r["results"][0]["price_type"]))
check("price range applies to that price type's rate", ["Smoke Pub Cleaning"], gq("price_type=weekly&price_min=900"))
check("...and not to the other packages", [], gq("price_type=weekly&price_max=100"))
check("delivery_days_max", {"Smoke Pub Cleaning", "Smoke Pub Gig Discount"}, set(gq("delivery_days_max=3")))
check("urgent=true", ["Smoke Pub Cleaning"], gq("urgent=true"))
check("urgent=false", {"Smoke Pub Logo", "Smoke Pub Gig Discount"}, set(gq("urgent=false")))
check("category filter", {"Smoke Pub Cleaning", "Smoke Pub Logo", "Smoke Pub Gig Discount"}, set(gq(f"category={SERVICE_CATEGORY}")))
check("seller filter", 3, len(gq(f"seller={S1}")))
check("price_max uses the discounted rate", {"Smoke Pub Gig Discount", "Smoke Pub Cleaning"}, set(gq("price_max=150")))
check("ordering price_asc", ["Smoke Pub Cleaning", "Smoke Pub Gig Discount", "Smoke Pub Logo"], gq("ordering=price_asc"))
for bad in ["price_type=yearly", "delivery_days_max=-1", "urgent=maybe", "ordering=cheap"]:
    check(f"bad query {bad} -> 400", 400, G("gigs/", "?" + bad)[0])
s, d = G(f"gigs/{g1['id']}/")
check("gig detail -> 200", 200, s)
check("packages with price type and descriptions", [("hourly", "per hour"), ("weekly", None)], [(x["price_type"], x["description"]) for x in d["packages"]])
check("package keys", ["description", "description_bn", "discounted_price", "id", "is_discount_active", "price", "price_type"], sorted(d["packages"][0]))
check("gig detail has service details", True, {"delivery_days", "urgent", "package_includes", "available_from", "available_to", "media", "location", "seller"} <= set(d))
check("no private fields in the gig detail", True, not ({"status", "note", "requested_at", "status_change_logs", "info_change_logs", "skus"} & set(d)))
check("a product id on the gig detail -> 404", 404, G(f"gigs/{p1['id']}/")[0])
check("a pending gig -> 404", 404, G(f"gigs/{g3['id']}/")[0])
check("a paused seller's gig -> 404", 404, G(f"gigs/{g4['id']}/")[0])

print("\n=== Public seller page ===")
s, d = call("GET", f"/public/sellers/{S1}/")
check("seller page -> 200, no login", 200, s)
check("keys", ["business", "contact", "education", "experience", "gig_count", "id", "location", "member_since", "name", "product_count", "profile_pic_url", "skills"], sorted(d))
check("counts of live products and gigs", (2, 3), (d["product_count"], d["gig_count"]))
check("no private fields (email, phone, balance, status)", True, not ({"email", "phone", "wallet_balance", "status", "verification_status", "present_address", "media"} & set(d)))
check("a paused seller -> 404", 404, call("GET", f"/public/sellers/{S2}/")[0])
check("an unverified seller -> 404", 404, call("GET", f"/public/sellers/{S3}/")[0])
check("an unknown seller -> 404", 404, call("GET", "/public/sellers/99999999/")[0])
check("POST is not allowed", 405, call("POST", f"/public/sellers/{S1}/", T, {})[0])

print("\n=== A paused seller's listings come back when the seller is active again ===")
A("PATCH", f"/accounts/sellers/{S2}/", {"status": "active"})
check("the paused seller's product is public again", True, "Smoke Pub Paused Seller Item" in titles(G("products/", "?search=Smoke%20Pub&page_size=100")[1]))
check("...and the seller page", 200, call("GET", f"/public/sellers/{S2}/")[0])

print("\n=== Cleanup ===")
cleanup()
check("no Smoke Pub data left", 0, G("products/", "?search=Smoke%20Pub")[1]["count"] + G("gigs/", "?search=Smoke%20Pub")[1]["count"])
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
