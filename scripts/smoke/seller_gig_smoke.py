#!/usr/bin/env python3
"""Smoke test: the seller gig API (`/seller/gigs/`), the seller thumbnail endpoints,
and that `/seller/listings/` stays products only.

A seller's gig is always `pending`, owned by the seller, priced by SKUs (one per
price type). Runs against a running dev server (SMOKE_BASE,
default http://127.0.0.1:8000) and the accounts in docs/test-accounts.md.
Everything it creates is named "Smoke SGig ..." and is removed at the end (and at
the start, in case an earlier run was interrupted). Standard library only.
"""
import json
import os
import struct
import subprocess
import sys
import urllib.error
import urllib.parse
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
        "rows = Listing.all_objects.filter(title__istartswith='Smoke SGig')\n"
        "for path in rows.exclude(image_path__isnull=True).values_list('image_path', flat=True):\n"
        "    try: os.remove(os.path.join(settings.MEDIA_ROOT, path))\n"
        "    except OSError: pass\n"
        "rows.delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.sgig.').delete()\n"
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
img = ("t.png", png(), "image/png")


def mk_seller(n, **extra):
    body = {"name": f"Smoke SGig Seller {n}", "email": f"smoke.sgig.{n}@example.com", "phone": f"+88017000981{n:02d}",
            "password": "Sell@12345"}
    body.update(extra)
    s, r = A("POST", "/accounts/sellers/", body)
    return r["id"], login("seller", body["phone"], "Sell@12345")


S1, T1 = mk_seller(1)
S2, T2 = mk_seller(2)
S3, T3 = mk_seller(3, verification_status="pending")
S4, T4 = mk_seller(4, status="inactive")
S = lambda m, p, b=None, f=None: call(m, p, T1, b, f)  # noqa: E731
GIGS, PRODUCTS = "/seller/gigs/", "/seller/listings/"


def gig(title, **extra):
    payload = {"category": 29, "title": title, "description": "d"}
    payload.update(extra)
    return payload


def err(response):
    return response[1] if isinstance(response[1], dict) else {}


print("\n=== Access ===")
check("no token -> 401", 401, call("GET", GIGS)[0])
check("admin token -> 403", 403, call("GET", GIGS, T)[0])
check("buyer token -> 403", 403, call("GET", GIGS, login("buyer", "test.buyer@egoola.com", "Test@12345"))[0])
r = call("GET", GIGS, T3)
check("a pending (not approved) seller -> 403", True, r[0] == 403 and "not approved yet" in r[1]["detail"])
r = call("GET", GIGS, T4)
check("an approved but inactive seller -> 403", True, r[0] == 403 and "inactive" in r[1]["detail"])
check("a not-operating seller cannot create -> 403", 403, call("POST", GIGS, T3, gig("Smoke SGig Nope", price="5", price_type="daily"))[0])
check("operating seller -> 200", 200, S("GET", GIGS)[0])

print("\n=== Create a gig ===")
s, g1 = S("POST", GIGS, gig("Smoke SGig One", title_bn="স্মোক সেবা", description_bn="বিবরণ", price="500", price_type="weekly",
                           delivery_days=3, package_includes="Daily visits", seller=S2, status="approved", posted_by_role="buyer_request"))
check("create with the shortcut", 201, s)
check("status is pending whatever was sent", "pending", g1["status"])
check("requested_at is set", True, g1["requested_at"] is not None)
check("catalog_type is service", "service", g1["catalog_type"])
check("the seller response has no owner or role fields", [], [k for k in ("seller", "buyer", "posted_by_role", "info_change_logs") if k in g1])
check("product-only fields are not part of a gig", [], [k for k in ("brand", "model", "listing_type", "measurement", "attributes", "price_tiers") if k in g1])
check("Bangla fields saved", ("স্মোক সেবা", "বিবরণ"), (g1["title_bn"], g1["description_bn"]))
check("status history has the seller's creation entry", [("pending", "seller")], [(l["status"], l["creator_type"]) for l in g1["status_change_logs"]])
check("the SKU is a weekly package (no duration on a SKU)", ("weekly", "500.00", False), (g1["skus"][0]["price_type"], g1["skus"][0]["price"], "duration" in g1["skus"][0]))
a = call("GET", f"/catalog/gigs/{g1['id']}/", T)[1]
check("admin sees the owner = me, seller_offer, created by a seller", (S1, "seller_offer", "seller"), (a["seller"], a["posted_by_role"], a["status_change_logs"][-1]["creator_type"]))

s, g2 = S("POST", GIGS, gig("Smoke SGig Packages", skus=[
    {"price": "400", "price_type": "hourly", "description": "Three hours", "description_bn": "তিন ঘণ্টা"},
    {"price": "9000", "price_type": "fixed"},
]))
check("several pricing strategies", 201, s)
check("two SKUs", 2, len(g2["skus"]))

print("\n=== Gig rules ===")
check("no price type -> 400", 400, S("POST", GIGS, gig("Smoke SGig E1", skus=[{"price": "5"}]))[0])
check("stock -> 400", 400, S("POST", GIGS, gig("Smoke SGig E3", skus=[{"price": "5", "price_type": "daily", "stock_qty": 1}]))[0])
check("options -> 400", 400, S("POST", GIGS, gig("Smoke SGig E4", skus=[{"price": "5", "price_type": "daily", "variants": [{"attribute": 1, "attribute_value": 1}]}]))[0])
check("the same price type twice -> 400", 400, S("POST", GIGS, gig("Smoke SGig E5", skus=[{"price": "5", "price_type": "daily"}, {"price": "6", "price_type": "daily"}]))[0])
check("no SKU and no price -> 400", 400, S("POST", GIGS, gig("Smoke SGig E6"))[0])
for field, value in [("brand", 1), ("listing_type", "general"), ("measurement", 13), ("min_order_qty", 2), ("model", "x"), ("attributes", {"a": 1})]:
    r = S("POST", GIGS, gig("Smoke SGig P " + field, price="5", price_type="daily", **{field: value}))
    check(f"product-only field '{field}' -> 400", True, r[0] == 400 and field in err(r))
check("quantity prices -> 400", 400, S("POST", GIGS, gig("Smoke SGig E7", price="5", price_type="daily", price_tiers=[{"min_qty": 1, "price": "4"}]))[0])
check("catalog_type=product -> 400", 400, S("POST", GIGS, gig("Smoke SGig E8", price="5", price_type="daily", catalog_type="product"))[0])
check("a product category -> 400", 400, S("POST", GIGS, gig("Smoke SGig E9", price="5", price_type="daily", category=18))[0])
check("negative price -> 400", 400, S("POST", GIGS, gig("Smoke SGig E10", price="-5", price_type="daily"))[0])

print("\n=== The same title rule is per type ===")
r = S("POST", GIGS, gig("smoke  sgig   ONE", price="5", price_type="daily"))
check("the same gig title (other case, extra spaces) -> 400", True, r[0] == 400 and "You already have a listing with this title" in json.dumps(r[1]))
check("another seller may use it", 201, call("POST", GIGS, T2, gig("Smoke SGig One", price="5", price_type="daily"))[0])
s, prod = S("POST", PRODUCTS, {"category": 18, "catalog_type": "product", "title": "Smoke SGig One", "description": "d", "price": "5"})
check("the same title as a PRODUCT is allowed (per type)", 201, s)

print("\n=== Product, gig and job stay apart ===")
check("a service on the product endpoint -> 400", 400, S("POST", PRODUCTS, {"category": 29, "catalog_type": "service", "title": "Smoke SGig E11", "description": "d", "price": "5"})[0])
check("service-only field on a product -> 400", 400, S("POST", PRODUCTS, {"category": 18, "catalog_type": "product", "title": "Smoke SGig E12", "description": "d", "price": "5", "delivery_days": 2})[0])
check("price_type on a product SKU -> 400", 400, S("POST", PRODUCTS, {"category": 18, "catalog_type": "product", "title": "Smoke SGig E13", "description": "d", "price": "5", "price_type": "daily"})[0])
check("the product endpoint needs no catalog_type", 201, S("POST", PRODUCTS, {"category": 18, "title": "Smoke SGig E14", "description": "d", "price": "5"})[0])
check("a gig id on the product endpoint -> 404", 404, S("GET", f"{PRODUCTS}{g1['id']}/")[0])
check("a product id on the gig endpoint -> 404", 404, S("GET", f"{GIGS}{prod['id']}/")[0])
check("PATCH a product through the gig endpoint -> 404", 404, S("PATCH", f"{GIGS}{prod['id']}/", {"description": "x"})[0])
check("thumbnail of a product through the gig endpoint -> 404", 404, S("PUT", f"{GIGS}{prod['id']}/thumbnail/", None, {"image": img})[0])
check("the product list has no gigs", True, all(r["catalog_type"] == "product" for r in S("GET", PRODUCTS + "?search=Smoke%20SGig")[1]["results"]))
check("the gig list has no products", 0, S("GET", GIGS + "?search=Smoke%20SGig%20E14")[1]["count"])
check("a seller cannot DELETE a gig -> 405", 405, S("DELETE", f"{GIGS}{g1['id']}/")[0])

print("\n=== List, detail, filters ===")
s, lst = S("GET", GIGS + "?search=Smoke%20SGig&limit=100")
check("list is limit/offset with a count", True, s == 200 and "count" in lst)
check("I only see my own gigs", True, all(r["title"] in ("Smoke SGig One", "Smoke SGig Packages") for r in lst["results"]))
row = [r for r in lst["results"] if r["title"] == "Smoke SGig One"][0]
check("row keys", ["category", "created_at", "discounted_price", "id", "image_url", "note", "price", "price_type", "requested_at", "slug", "status", "title", "title_bn", "updated_at"], sorted(row))
check("row price type", "weekly", row["price_type"])
check("filter price_type=fixed", {"Smoke SGig Packages"}, {r["title"] for r in S("GET", GIGS + "?price_type=fixed&search=Smoke%20SGig")[1]["results"]})
check("filter status=pending", True, S("GET", GIGS + "?status=pending")[1]["count"] >= 2)
check("search by Bangla title", True, any(r["title"] == "Smoke SGig One" for r in S("GET", GIGS + "?search=" + urllib.parse.quote("স্মোক"))[1]["results"]))
check("detail of my gig", 200, S("GET", f"{GIGS}{g1['id']}/")[0])
check("another seller's gig -> 404", 404, call("GET", f"{GIGS}{g1['id']}/", T2)[0])

print("\n=== Editing and moderation ===")
r = S("PATCH", f"{GIGS}{g1['id']}/", {"description": "more"})
check("edit a pending gig: stays pending", ("pending", g1["requested_at"]), (r[1]["status"], r[1]["requested_at"]))
s, q = call("GET", "/catalog/gigs/requests/?search=Smoke%20SGig", T)
check("the admin pending gig list shows it", True, "Smoke SGig One" in {r["title"] for r in q["results"]})
check("admin approves", 200, call("PATCH", f"/catalog/gigs/{g1['id']}/", T, {"status": "approved"})[0])
r = S("PATCH", f"{GIGS}{g1['id']}/", {"description": "approved edit", "note": "ignored"})
check("edit an approved gig: stays approved", "approved", r[1]["status"])
check("...the note is ignored", None, r[1]["note"])
r = S("PATCH", f"{GIGS}{g1['id']}/", {"skus": [{"id": g1["skus"][0]["id"], "price": "600"}]})
check("change a package on an approved gig: stays approved", ("approved", "600.00"), (r[1]["status"], r[1]["skus"][0]["price"]))
check("a seller cannot set status", "approved", S("PATCH", f"{GIGS}{g1['id']}/", {"status": "rejected"})[1]["status"])
check("a seller cannot change catalog_type", 400, S("PATCH", f"{GIGS}{g1['id']}/", {"catalog_type": "product"})[0])
check("admin rejects with a note", 200, call("PATCH", f"/catalog/gigs/{g1['id']}/", T, {"status": "rejected", "note": "Add photos"})[0])
r = S("GET", f"{GIGS}{g1['id']}/")[1]
check("the seller sees the reason", ("rejected", "Add photos"), (r["status"], r["note"]))
r = S("PATCH", f"{GIGS}{g1['id']}/", {"description": "fixed", "note": "Added photos"})
check("saving a rejected gig sends it back to pending", ("pending", "Added photos"), (r[1]["status"], r[1]["note"]))
check("...with a new request time", True, r[1]["requested_at"] > g1["requested_at"])
check("history (oldest first): pending, approved, rejected, pending", ["pending", "approved", "rejected", "pending"], [l["status"] for l in reversed(r[1]["status_change_logs"])])
d = call("GET", f"/catalog/gigs/{g1['id']}/", T)[1]
check("admin info log has the package change", True, any("skus" in l["changed_fields"] for l in d["info_change_logs"]))

print("\n=== Thumbnail (seller) ===")
url = f"{GIGS}{g2['id']}/thumbnail/"
check("no token -> 401", 401, call("PUT", url, files={"image": img})[0])
check("another seller -> 404", 404, call("PUT", url, T2, files={"image": img})[0])
check("a not-operating seller -> 403", 403, call("PUT", url, T3, files={"image": img})[0])
check("admin token -> 403", 403, call("PUT", url, T, files={"image": img})[0])
s, r = S("PUT", url, None, {"image": img})
check("upload", 200, s)
p1 = r["image_path"]
check("stored under listing/thumbnails/", True, p1.startswith("listing/thumbnails/") and on_disk(p1))
check("detail and list show it", (r["image_url"], r["image_url"]), (S("GET", f"{GIGS}{g2['id']}/")[1]["image_url"], [x for x in S("GET", GIGS + "?search=Smoke%20SGig%20Packages")[1]["results"]][0]["image_url"]))
check("the gig was pending: stays pending, no extra history", ("pending", 1), (r["status"], len(S("GET", f"{GIGS}{g2['id']}/")[1]["status_change_logs"])))
s, r = S("PUT", url, None, {"image": img})
check("replace deletes the old file", (200, False, True), (s, on_disk(p1), on_disk(r["image_path"])))
p2 = r["image_path"]
check("a text file -> 400", 400, S("PUT", url, None, {"image": ("n.txt", b"x", "text/plain")})[0])
check("a GIF -> 400", 400, S("PUT", url, None, {"image": ("a.gif", b"GIF89a", "image/gif")})[0])
check("a fake PNG -> 400", 400, S("PUT", url, None, {"image": ("f.png", b"nope", "image/png")})[0])
check("a 10 MB+ picture -> 400", 400, S("PUT", url, None, {"image": ("b.png", png() + b"\0" * (10 * 1024 * 1024 + 1), "image/png")})[0])
check("a refused upload keeps the file", True, on_disk(p2))

print("\n-- thumbnail on an approved and on a rejected gig")
s, g3 = S("POST", GIGS, gig("Smoke SGig Three", price="5", price_type="daily"))
check("approve it", 200, call("PATCH", f"/catalog/gigs/{g3['id']}/", T, {"status": "approved"})[0])
r = S("PUT", f"{GIGS}{g3['id']}/thumbnail/", None, {"image": img})
check("approved gig: a new thumbnail keeps it approved", ("approved", 200), (r[1]["status"], r[0]))
check("reject it", 200, call("PATCH", f"/catalog/gigs/{g3['id']}/", T, {"status": "rejected", "note": "bad picture"})[0])
r = S("PUT", f"{GIGS}{g3['id']}/thumbnail/", None, {"image": img})
check("rejected gig: a new thumbnail sends it back to pending", ("pending", 200), (r[1]["status"], r[0]))
d = S("GET", f"{GIGS}{g3['id']}/")[1]
check("...with a status history entry by the seller", ("pending", "seller"), (d["status_change_logs"][0]["status"], d["status_change_logs"][0]["creator_type"]))
check("...and the admin sees it in the pending list", True, "Smoke SGig Three" in {x["title"] for x in call("GET", "/catalog/gigs/requests/?search=Smoke%20SGig", T)[1]["results"]})
d = call("GET", f"/catalog/gigs/{g3['id']}/", T)[1]
check("the info change log has the thumbnail", True, any("thumbnail" in l["changed_fields"] for l in d["info_change_logs"]))
check("delete the thumbnail", (204, None), (S("DELETE", f"{GIGS}{g3['id']}/thumbnail/")[0], S("GET", f"{GIGS}{g3['id']}/")[1]["image_url"]))

print("\n-- product thumbnail")
s, r = S("PUT", f"{PRODUCTS}{prod['id']}/thumbnail/", None, {"image": img})
check("upload on a product", 200, s)
pp = r["image_path"]
check("delete on a product removes the file", (204, False), (S("DELETE", f"{PRODUCTS}{prod['id']}/thumbnail/")[0], on_disk(pp)))
check("a gig id on the product thumbnail endpoint -> 404", 404, S("PUT", f"{PRODUCTS}{g1['id']}/thumbnail/", None, {"image": img})[0])
check("GET on the thumbnail endpoint -> 405", 405, S("GET", url)[0])

print("\n=== Cleanup ===")
cleanup()
check("no Smoke SGig data left", 0, call("GET", "/catalog/gigs/?search=Smoke%20SGig", T)[1]["count"] + call("GET", "/catalog/listings/?search=Smoke%20SGig", T)[1]["count"])
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
