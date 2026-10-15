#!/usr/bin/env python3
"""Smoke test: the admin gig API (`/catalog/gigs/`), the listing thumbnail endpoints
and the product / gig / job separation.

A gig is a seller's service offer, priced by SKUs: one per price type (hourly,
daily, weekly, monthly, fixed); no options, stock or
quantity prices. Runs against a running dev server (SMOKE_BASE, default
http://127.0.0.1:8000) and the accounts in docs/test-accounts.md. Everything it
creates is named "Smoke Gig ..." and is removed at the end (and at the start, in
case an earlier run was interrupted). Standard library only.
"""
import json
import os
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
import zlib

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:8000") + "/api/v1"
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PRODUCT_CATEGORY, SERVICE_CATEGORY = 18, 29
PASS = FAIL = 0


def call(method, path, token=None, body=None, files=None):
    """JSON request, or multipart when `files` ({field: (name, bytes, content_type)}) is given."""
    headers = {}
    if files is not None:
        boundary = uuid.uuid4().hex
        data = b""
        for field, (name, content, content_type) in files.items():
            data += (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\n'
                     f"Content-Type: {content_type}\r\n\r\n").encode() + content + b"\r\n"
        data += f"--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    else:
        data = json.dumps(body).encode() if body is not None else None
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
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
    out = subprocess.run(["uv", "run", "manage.py", "shell", "-c", code], cwd=SERVER_DIR,
                         capture_output=True, text=True).stdout
    return out.strip().splitlines()[-1] if out.strip() else ""


def cleanup():
    shell(
        "import os\n"
        "from django.conf import settings\n"
        "from apps.accounts.models import Seller\n"
        "from apps.catalog.models import Listing\n"
        "rows = Listing.all_objects.filter(title__istartswith='Smoke Gig')\n"
        "for path in rows.exclude(image_path__isnull=True).values_list('image_path', flat=True):\n"
        "    try: os.remove(os.path.join(settings.MEDIA_ROOT, path))\n"
        "    except OSError: pass\n"
        "rows.delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.gig.').delete()\n"
    )


MEDIA_ROOT = shell("from django.conf import settings; print(settings.MEDIA_ROOT)")


def on_disk(path):
    return bool(path) and os.path.exists(os.path.join(MEDIA_ROOT, path))


def png():
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x00\x00\xff" * 4 for _ in range(4))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def login(kind, identifier, password):
    field = "phone" if kind == "seller" else "email"
    status, body = call("POST", f"/auth/{kind}/login/", body={field: identifier, "password": password})
    return body["access"] if status == 200 else ""


cleanup()
T = login("admin", "test.admin@egoola.com", "Test@12345")
check("admin login", True, bool(T))
A = lambda m, p, b=None, f=None: call(m, p, T, b, f)  # noqa: E731


def gig(title, skus=None, **extra):
    payload = {"category": SERVICE_CATEGORY, "title": title, "description": "d"}
    if skus is not None:
        payload["skus"] = skus
    payload.update(extra)
    return payload


def product(title, **extra):
    payload = {"category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general",
               "title": title, "description": "d", "price": "100"}
    payload.update(extra)
    return payload


def err(response):
    """The error body keyed by field, or {}."""
    return response[1] if isinstance(response[1], dict) else {}


s, seller = A("POST", "/accounts/sellers/", {"name": "Smoke Gig Seller", "email": "smoke.gig.one@example.com",
                                           "phone": "+8801700098101", "password": "Sell@12345"})
check("create smoke seller", 201, s)

print("\n=== Access ===")
check("no token -> 401", 401, call("GET", "/catalog/gigs/")[0])
check("seller token -> 403", 403, call("GET", "/catalog/gigs/", login("seller", "0100000002", "Test@12345"))[0])
check("buyer token -> 403", 403, call("GET", "/catalog/gigs/", login("buyer", "test.buyer@egoola.com", "Test@12345"))[0])

print("\n=== Create a gig ===")
s, g1 = A("POST", "/catalog/gigs/", gig("Smoke Gig One", price="500", price_type="weekly",
                                       seller=seller["id"], delivery_days=3, urgent=False,
                                       package_includes="Two weeks of daily cleaning"))
check("create with the price shortcut (weekly x 2)", 201, s)
check("catalog_type is service", "service", g1["catalog_type"])
check("posted_by_role is seller_offer", "seller_offer", g1["posted_by_role"])
check("admin-created gig is approved", "approved", g1["status"])
sku = g1["skus"][0]
check("one SKU", 1, len(g1["skus"]))
check("SKU price type", "weekly", sku["price_type"])
check("price is the weekly rate", "500.00", sku["price"])
check("a SKU has no duration (the buyer chooses it when ordering)", [], [k for k in ("duration", "total_price") if k in sku])
check("no stock on a gig", None, sku["stock_qty"])
check("no options on a gig", [], sku["variants"])
check("product-only fields are not part of a gig", [], [k for k in ("brand", "model", "listing_type", "measurement", "attributes", "price_tiers", "min_order_qty", "warranty") if k in g1])

s, g2 = A("POST", "/catalog/gigs/", gig("Smoke Gig Packages", seller=seller["id"], skus=[
    {"price": "400", "price_type": "hourly", "description": "Three hours", "description_bn": "তিন ঘণ্টা"},
    {"price": "3000", "discounted_price": "2500", "price_type": "daily"},
    {"price": "9000", "price_type": "fixed", "sku": "SMOKE-GIG-FIXED"},
]))
check("several pricing strategies (hourly, daily, fixed)", 201, s)
check("three SKUs", 3, len(g2["skus"]))
by_type = {k["price_type"]: k for k in g2["skus"]}
check("SKU description saved", "Three hours", by_type["hourly"]["description"])
check("SKU Bangla description saved", "তিন ঘণ্টা", by_type["hourly"]["description_bn"])
check("daily discount applies to the rate", "2500.00", by_type["daily"]["effective_price"])
check("from price = cheapest whole package (daily 2500 vs hourly 1200)", "400.00", g2["price"])

print("\n=== Gig rules (create) ===")
for label, payload, key in [
    ("price type is required", gig("Smoke Gig E1", skus=[{"price": "5"}]), "price_type"),
    ("a gig has no stock", gig("Smoke Gig E3", skus=[{"price": "5", "price_type": "daily", "stock_qty": 4}]), "stock_qty"),
    ("a gig SKU has no options", gig("Smoke Gig E4", skus=[{"price": "5", "price_type": "daily", "variants": [{"attribute": 1, "attribute_value": 1}]}]), "variants"),
    ("unknown price type is refused", gig("Smoke Gig E6", skus=[{"price": "5", "price_type": "yearly"}]), "price_type"),
]:
    r = A("POST", "/catalog/gigs/", payload)
    check(f"{label} -> 400", 400, r[0])
    check(f"...error is on skus.0.{key}", True, key in err(r).get("skus", {}).get("0", {}) if isinstance(err(r).get("skus"), dict) else False)
r = A("POST", "/catalog/gigs/", gig("Smoke Gig E7", skus=[{"price": "5", "price_type": "daily"}, {"price": "6", "price_type": "daily"}]))
check("two SKUs with the same price type -> 400", 400, r[0])
check("no SKU and no price -> 400", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E8"))[0])
check("negative price -> 400", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E9", price="-1", price_type="daily"))[0])
check("discount above price -> 400", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E10", price="5", discounted_price="9", price_type="daily"))[0])
for field, value in [("brand", 1), ("model", "x"), ("listing_type", "general"), ("measurement", 13), ("min_order_qty", 2),
                     ("origin", "BD"), ("warranty", "1y"), ("condition_note", "used"), ("attributes", {"a": 1})]:
    r = A("POST", "/catalog/gigs/", gig("Smoke Gig P " + field, price="5", price_type="daily", **{field: value}))
    check(f"product-only field '{field}' -> 400", True, r[0] == 400 and field in err(r))
r = A("POST", "/catalog/gigs/", gig("Smoke Gig Tiers", price="5", price_type="daily", price_tiers=[{"min_qty": 1, "price": "4"}]))
check("quantity prices on a gig -> 400", True, r[0] == 400 and "price_tiers" in err(r))
check("catalog_type=product on the gig endpoint -> 400", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E11", price="5", price_type="daily", catalog_type="product"))[0])
check("posted_by_role=buyer_request on the gig endpoint -> 400", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E12", price="5", price_type="daily", posted_by_role="buyer_request"))[0])
check("a product category -> 400", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E13", price="5", price_type="daily", category=PRODUCT_CATEGORY))[0])
check("catalog_type / posted_by_role may be sent when they match", 201, A("POST", "/catalog/gigs/", gig("Smoke Gig Match", price="5", price_type="hourly", catalog_type="service", posted_by_role="seller_offer"))[0])
check("the shortcut and skus together -> 400", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E14", price="5", price_type="daily", skus=[{"price": "5", "price_type": "daily"}]))[0])
check("same SKU code twice -> 400", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E15", skus=[{"price": "5", "price_type": "daily", "sku": "SMOKE-GIG-FIXED"}]))[0])

print("\n=== Edit a gig ===")
gid = g2["id"]
s, r = A("PATCH", f"/catalog/gigs/{gid}/", {"skus": [{"price": "30000", "price_type": "monthly"}]})
check("add a monthly package", 200, s)
check("now four SKUs", 4, len(r["skus"]))
check("a second hourly package -> 400", 400, A("PATCH", f"/catalog/gigs/{gid}/", {"skus": [{"price": "1", "price_type": "hourly"}]})[0])
hourly_id = by_type["hourly"]["id"]
s, r = A("PATCH", f"/catalog/gigs/{gid}/", {"skus": [{"id": hourly_id, "price": "450"}]})
check("change a package by id", 200, s)
h = [k for k in r["skus"] if k["id"] == hourly_id][0]
check("price changed", "450.00", h["price"])
check("price type kept", "hourly", h["price_type"])
s, r = A("PATCH", f"/catalog/gigs/{gid}/", {"skus": [{"id": hourly_id, "is_active": False}]})
check("hide a package", 200, s)
check("it stays in the list, inactive", False, [k for k in r["skus"] if k["id"] == hourly_id][0]["is_active"])
check("a hidden package still holds its price type -> 400", 400, A("PATCH", f"/catalog/gigs/{gid}/", {"skus": [{"price": "1", "price_type": "hourly"}]})[0])
check("reactivate it", 200, A("PATCH", f"/catalog/gigs/{gid}/", {"skus": [{"id": hourly_id, "is_active": True}]})[0])
check("move a package onto an existing price type -> 400", 400, A("PATCH", f"/catalog/gigs/{gid}/", {"skus": [{"id": hourly_id, "price_type": "daily"}]})[0])
check("give a package a stock -> 400", 400, A("PATCH", f"/catalog/gigs/{gid}/", {"skus": [{"id": hourly_id, "stock_qty": 3}]})[0])
check("price / stock at the top level of an update -> 400", 400, A("PATCH", f"/catalog/gigs/{gid}/", {"price": "5"})[0])
check("edit the text", 200, A("PATCH", f"/catalog/gigs/{gid}/", {"description": "new text", "delivery_days": 5})[0])
check("catalog_type cannot be changed -> 400", 400, A("PATCH", f"/catalog/gigs/{gid}/", {"catalog_type": "product"})[0])
check("posted_by_role cannot be changed -> 400", 400, A("PATCH", f"/catalog/gigs/{gid}/", {"posted_by_role": "buyer_request"})[0])
r = A("GET", f"/catalog/gigs/{gid}/")[1]
changed = [log["changed_fields"] for log in r["info_change_logs"]]
check("package changes are in the info change log", True, any("skus" in c for c in changed))
sku_logs = [log for log in r["info_change_logs"] if "skus" in log["changed_fields"]]
check("the log keeps the price type", True, "price_type" in json.dumps(sku_logs[0]["new_data"]))

print("\n=== List, search, filter ===")
s, lst = A("GET", "/catalog/gigs/?search=Smoke%20Gig&limit=100")
check("list is limit/offset with a count", True, s == 200 and "count" in lst)
titles = {row["title"] for row in lst["results"]}
check("list shows gigs", True, {"Smoke Gig One", "Smoke Gig Packages"} <= titles)
row = [r for r in lst["results"] if r["title"] == "Smoke Gig One"][0]
check("row has the price_type of the lowest rate", "weekly", row["price_type"])
check("row keys", ["category", "created_at", "discounted_price", "id", "image_url", "price", "price_type", "requested_at", "seller", "slug", "status", "title", "title_bn"], sorted(row))
check("filter price_type=monthly", True, {r["title"] for r in A("GET", "/catalog/gigs/?price_type=monthly&search=Smoke%20Gig")[1]["results"]} == {"Smoke Gig Packages"})
check("filter price_type=weekly", True, "Smoke Gig One" in {r["title"] for r in A("GET", "/catalog/gigs/?price_type=weekly&search=Smoke%20Gig")[1]["results"]})
check("filter by seller", True, {r["title"] for r in A("GET", f"/catalog/gigs/?seller={seller['id']}")[1]["results"]} >= {"Smoke Gig One", "Smoke Gig Packages"})
check("search by SKU code", True, {r["title"] for r in A("GET", "/catalog/gigs/?search=SMOKE-GIG-FIXED")[1]["results"]} == {"Smoke Gig Packages"})
check("filter status=approved", True, all(r["status"] == "approved" for r in A("GET", "/catalog/gigs/?status=approved&search=Smoke%20Gig")[1]["results"]))

print("\n=== Product, gig and job stay apart ===")
s, p1 = A("POST", "/catalog/listings/", product("Smoke Gig Product"))
check("create a product", 201, s)
check("a gig is not in the listing list", 0, A("GET", "/catalog/listings/?search=Smoke%20Gig%20One")[1]["count"])
check("a product is not in the gig list", 0, A("GET", "/catalog/gigs/?search=Smoke%20Gig%20Product")[1]["count"])
check("a gig id on the listing endpoint -> 404", 404, A("GET", f"/catalog/listings/{g1['id']}/")[0])
check("a product id on the gig endpoint -> 404", 404, A("GET", f"/catalog/gigs/{p1['id']}/")[0])
check("PATCH a product through the gig endpoint -> 404", 404, A("PATCH", f"/catalog/gigs/{p1['id']}/", {"description": "x"})[0])
check("DELETE a product through the gig endpoint -> 404", 404, A("DELETE", f"/catalog/gigs/{p1['id']}/")[0])
r = A("POST", "/catalog/listings/", gig("Smoke Gig Wrong", price="5", price_type="daily", catalog_type="service", posted_by_role="seller_offer"))
check("a seller's service offer on the listing endpoint -> 400", True, r[0] == 400 and "catalog_type" in err(r))
r = A("POST", "/catalog/listings/", gig("Smoke Gig Wrong2", price="5", catalog_type="service"))
check("a service with no role on the listing endpoint -> 400", 400, r[0])
check("price_type on a product SKU -> 400", 400, A("POST", "/catalog/listings/", product("Smoke Gig E20", price_type="daily"))[0])
check("price_type on a product SKU (shortcut) -> 400", 400, A("POST", "/catalog/listings/", product("Smoke Gig E21", price_type="hourly"))[0])
check("SKU description on a product -> 400", 400, A("POST", "/catalog/listings/", product("Smoke Gig E22", price=None, skus=[{"price": "5", "description": "x"}]))[0])
check("service-only field on a product -> 400", 400, A("POST", "/catalog/listings/", product("Smoke Gig E23", delivery_days=3))[0])
check("a product cannot be a buyer_request -> 400", 400, A("POST", "/catalog/listings/", product("Smoke Gig E24", posted_by_role="buyer_request"))[0])
s, buyer = A("GET", "/accounts/buyers/?limit=1")
buyer_id = buyer["results"][0]["id"]
job = {"category": SERVICE_CATEGORY, "catalog_type": "service", "posted_by_role": "buyer_request", "buyer": buyer_id,
       "title": "Smoke Gig Job", "description": "need cleaning", "price": "300", "price_type": "hourly", "urgent": True, "delivery_days": 2}
s, j = A("POST", "/catalog/listings/", job)
check("a buyer's job request still works on the listing endpoint (for now)", 201, s)
check("a job request is not a gig (not on the gig endpoint)", 404, A("GET", f"/catalog/gigs/{j['id']}/")[0])
check("a job SKU may carry a price type", "hourly", j["skus"][0]["price_type"])
check("job: product-only field -> 400", 400, A("POST", "/catalog/listings/", dict(job, title="Smoke Gig Job2", brand=1))[0])
check("job: SKU description -> 400", 400, A("POST", "/catalog/listings/", dict(job, title="Smoke Gig Job3", price=None, skus=[{"price": "5", "description": "x"}]))[0])
jb = {k: v for k, v in job.items() if k not in ("price", "price_type")}
r = A("POST", "/catalog/listings/", dict(jb, title="Smoke Gig Job4", skus=[{"price": "5", "price_type": "hourly"}, {"price": "6", "price_type": "hourly"}]))
check("job: two SKUs with the same price type -> 400 (not a database error)", True, r[0] == 400 and "price type" in json.dumps(r[1]))
check("a zero in a service-only field on a product is still refused", 400, A("POST", "/catalog/listings/", product("Smoke Gig E25", delivery_days=0))[0])
check("a zero in a product-only field on a gig is still refused", 400, A("POST", "/catalog/gigs/", gig("Smoke Gig E26", price="5", price_type="daily", min_order_qty=0))[0])
check("job: category / type cannot change", 400, A("PATCH", f"/catalog/listings/{j['id']}/", {"posted_by_role": "seller_offer"})[0])

print("\n=== Moderation and the pending list ===")
s, gp = A("POST", "/catalog/gigs/", gig("Smoke Gig Pending", price="5", price_type="daily", seller=seller["id"], status="pending"))
check("create a pending gig", 201, s)
s, queue = A("GET", "/catalog/gigs/requests/?search=Smoke%20Gig")
check("pending list (cursor, no count)", True, s == 200 and "count" not in queue and "results" in queue)
check("the gig is in the pending list", True, "Smoke Gig Pending" in {r["title"] for r in queue["results"]})
check("a product is not in the gig pending list", True, "Smoke Gig Product" not in {r["title"] for r in queue["results"]})
check("reject without a note -> 400", 400, A("PATCH", f"/catalog/gigs/{gp['id']}/", {"status": "rejected"})[0])
s, r = A("PATCH", f"/catalog/gigs/{gp['id']}/", {"status": "rejected", "note": "Add a clear description"})
check("reject with a note", 200, s)
check("history has creation + rejection", 2, len(r["status_change_logs"]))
s, r = A("POST", "/catalog/gigs/bulk-moderate/", {"listing_ids": [gp["id"], p1["id"], g1["id"]], "status": "approved"})
check("bulk approve through the gig endpoint", 200, s)
check("only gigs are touched (the product id is ignored)", ([gp["id"]], [g1["id"]]), (r["updated"], r["skipped"]))
check("the product stayed as it was", "approved", A("GET", f"/catalog/listings/{p1['id']}/")[1]["status"])
check("bulk-moderate on listings ignores gigs", ([], []), (lambda x: (x["updated"], x["skipped"]))(A("POST", "/catalog/listings/bulk-moderate/", {"listing_ids": [gp["id"]], "status": "rejected", "note": "n"})[1]))

print("\n=== Soft delete ===")
check("deleting a gig works", 204, A("DELETE", f"/catalog/gigs/{g2['id']}/")[0])
check("a deleted gig is a 404", 404, A("GET", f"/catalog/gigs/{g2['id']}/")[0])
check("...and drops out of the list", 0, A("GET", "/catalog/gigs/?search=Smoke%20Gig%20Packages")[1]["count"])
print("(thumbnail and gallery files: see listing_files_smoke.py)")

print("\n=== Cleanup ===")
cleanup()
check("no Smoke Gig listings left", 0, A("GET", "/catalog/gigs/?search=Smoke%20Gig")[1]["count"] + A("GET", "/catalog/listings/?search=Smoke%20Gig")[1]["count"])
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
