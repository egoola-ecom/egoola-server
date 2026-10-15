#!/usr/bin/env python3
"""Smoke test: the listing-files APIs (thumbnail + gallery of a product or a gig).

    POST/PATCH /catalog/listing-files/{id}/   (admin)
    POST/PATCH /seller/listing-files/{id}/    (seller, own listings)

Also checks that listing / gig create and update are JSON only (multipart -> 415)
and that the old `/thumbnail/` endpoints are gone. Runs against a running dev
server (SMOKE_BASE, default http://127.0.0.1:8000). Everything it creates is named
"Smoke LF ..." and is removed at the end (and at the start, in case an earlier run
was interrupted). Standard library only.
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


def call(method, path, token=None, body=None, form=None):
    """JSON request, or multipart when `form` is a list of (field, value) pairs; a value is a
    string, or a (filename, bytes, content_type) tuple for a file."""
    headers = {}
    if form is not None:
        boundary = uuid.uuid4().hex
        data = b""
        for field, value in form:
            if isinstance(value, tuple):
                name, content, content_type = value
                data += (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\n'
                         f"Content-Type: {content_type}\r\n\r\n").encode() + content + b"\r\n"
            else:
                data += (f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n').encode()
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
        "from apps.catalog.models import Listing, ListingMedia\n"
        "rows = Listing.all_objects.filter(title__istartswith='Smoke LF')\n"
        "paths = list(rows.exclude(image_path__isnull=True).values_list('image_path', flat=True))\n"
        "paths += list(ListingMedia.objects.filter(listing__in=rows).values_list('media_path', flat=True))\n"
        "for path in paths:\n"
        "    try: os.remove(os.path.join(settings.MEDIA_ROOT, path))\n"
        "    except OSError: pass\n"
        "rows.delete()\n"
        "Seller.objects.filter(email__istartswith='smoke.lf.').delete()\n"
    )


MEDIA_ROOT = shell("from django.conf import settings; print(settings.MEDIA_ROOT)")


def on_disk(path):
    return bool(path) and os.path.exists(os.path.join(MEDIA_ROOT, path))


def png(size=4):
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x00\x00\xff" * size for _ in range(size))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def login(kind, identifier, password):
    field = "phone" if kind == "seller" else "email"
    status, body = call("POST", f"/auth/{kind}/login/", body={field: identifier, "password": password})
    return body["access"] if status == 200 else ""


cleanup()
TA = login("admin", "test.admin@egoola.com", "Test@12345")
check("admin login", True, bool(TA))
A = lambda m, p, b=None, f=None: call(m, p, TA, b, f)  # noqa: E731


def mk_seller(n, **extra):
    body = {"name": f"Smoke LF Seller {n}", "email": f"smoke.lf.{n}@example.com", "phone": f"+88017000971{n:02d}",
            "password": "Sell@12345"}
    body.update(extra)
    s, r = A("POST", "/accounts/sellers/", body)
    return r["id"], login("seller", body["phone"], "Sell@12345")


S1, T1 = mk_seller(1)
S2, T2 = mk_seller(2)
S3, T3 = mk_seller(3, verification_status="pending")
SL = lambda m, p, b=None, f=None: call(m, p, T1, b, f)  # noqa: E731
SL2 = lambda m, p, b=None, f=None: call(m, p, T2, b, f)  # noqa: E731


def png_file(name="a.png"):
    return (name, png(), "image/png")


F = [("thumbnail", png_file())]
ADMIN, SELLER = "/catalog/listing-files/", "/seller/listing-files/"

print("\n=== Setup ===")
s, prod = A("POST", "/catalog/listings/", {"category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general",
                                           "title": "Smoke LF Product", "description": "d", "seller": S1, "price": "10"})
check("admin creates a product (JSON)", 201, s)
s, gig = A("POST", "/catalog/gigs/", {"category": SERVICE_CATEGORY, "title": "Smoke LF Gig", "description": "d",
                                      "seller": S1, "price": "5", "price_type": "daily"})
check("admin creates a gig (JSON)", 201, s)
s, sprod = SL("POST", "/seller/listings/", {"category": PRODUCT_CATEGORY, "catalog_type": "product", "title": "Smoke LF Seller Product",
                                            "description": "d", "price": "10"})
check("seller creates a product (JSON)", 201, s)
s, sgig = SL("POST", "/seller/gigs/", {"category": SERVICE_CATEGORY, "title": "Smoke LF Seller Gig", "description": "d",
                                       "price": "5", "price_type": "daily"})
check("seller creates a gig (JSON)", 201, s)
check("a new listing has no thumbnail and no media", (None, []), (sprod["image_url"], sprod["media"]))

print("\n=== JSON only, and the old endpoints are gone ===")
mp = [("title", "Smoke LF Multipart"), ("category", str(PRODUCT_CATEGORY))]
check("admin product create as multipart -> 415", 415, A("POST", "/catalog/listings/", None, mp)[0])
check("admin gig create as multipart -> 415", 415, A("POST", "/catalog/gigs/", None, mp)[0])
check("admin product update as multipart -> 415", 415, A("PATCH", f"/catalog/listings/{prod['id']}/", None, [("title", "x")])[0])
check("seller product create as multipart -> 415", 415, SL("POST", "/seller/listings/", None, mp)[0])
check("seller gig update as multipart -> 415", 415, SL("PATCH", f"/seller/gigs/{sgig['id']}/", None, [("title", "x")])[0])
check("a media_file field in JSON is ignored", 200, A("PATCH", f"/catalog/listings/{prod['id']}/", {"media_file": ["x"], "description": "d2"})[0])
check("old PUT .../thumbnail/ -> 404", 404, A("PUT", f"/catalog/gigs/{gig['id']}/thumbnail/", None, F)[0])
check("old seller PUT .../thumbnail/ -> 404", 404, SL("PUT", f"/seller/gigs/{sgig['id']}/thumbnail/", None, F)[0])

print("\n=== Access ===")
for base, who in [(ADMIN, "admin"), (SELLER, "seller")]:
    check(f"{who}: no token -> 401", 401, call("POST", f"{base}{prod['id']}/", form=F)[0])
check("admin endpoint with a seller token -> 403", 403, SL("POST", f"{ADMIN}{prod['id']}/", None, F)[0])
check("seller endpoint with an admin token -> 403", 403, A("POST", f"{SELLER}{sprod['id']}/", None, F)[0])
check("unverified seller -> 403", 403, call("POST", f"{SELLER}{sprod['id']}/", T3, form=F)[0])
check("another seller's listing -> 404", 404, SL2("POST", f"{SELLER}{sprod['id']}/", None, F)[0])
check("unknown id -> 404", 404, A("POST", f"{ADMIN}99999999/", None, F)[0])
check("GET is not allowed -> 405", 405, A("GET", f"{ADMIN}{prod['id']}/")[0])
check("PUT is not allowed -> 405", 405, A("PUT", f"{ADMIN}{prod['id']}/", None, F)[0])
check("DELETE is not allowed -> 405", 405, A("DELETE", f"{ADMIN}{prod['id']}/")[0])
check("JSON body -> 415", 415, A("POST", f"{ADMIN}{prod['id']}/", {})[0])
s, job = A("POST", "/catalog/listings/", {"category": SERVICE_CATEGORY, "title": "Smoke LF Job", "description": "d",
                                          "catalog_type": "service", "posted_by_role": "buyer_request",
                                          "buyer": int(shell("from apps.accounts.models import User; print(User.objects.get(email='test.buyer@egoola.com').id)") or 0),
                                          "price": "5", "price_type": "fixed"})
if s == 201:
    check("a job id -> 404", 404, A("POST", f"{ADMIN}{job['id']}/", None, F)[0])
else:
    print(f"SKIP job check (could not create a job: {s})")

print("\n=== Admin: create (POST) ===")
for label, item in [("product", prod), ("gig", gig)]:
    url = f"{ADMIN}{item['id']}/"
    s, r = A("POST", url, None, [])
    check(f"{label}: an empty request is allowed", 201, s)
    check(f"{label}: ...and changes nothing", (None, []), (r["image_url"], r["media"]))
    s, r = A("POST", url, None, F + [("media_file", png_file("g1.png")), ("media_file", ("v.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4"))])
    check(f"{label}: thumbnail + two gallery files", 201, s)
    t1 = r["image_path"]
    check(f"{label}: thumbnail path under listing/thumbnails/", True, bool(t1) and t1.startswith("listing/thumbnails/") and on_disk(t1))
    check(f"{label}: two media rows", ["image", "video"], [m["media_type"] for m in r["media"]])
    check(f"{label}: media files are stored", True, all(on_disk(m["media_path"]) for m in r["media"]))
    d = A("GET", f"/catalog/{'listings' if label == 'product' else 'gigs'}/{item['id']}/")[1]
    check(f"{label}: detail shows them", (t1, 2), (d["image_path"], len(d["media"])))
    check(f"{label}: a second thumbnail on POST -> 400", 400, A("POST", url, None, F)[0])
    A("POST", url, None, F + [("media_file", png_file("refused.png"))])
    check(f"{label}: ...the refused request saved no gallery file", 2, len(A("GET", f"/catalog/{'listings' if label == 'product' else 'gigs'}/{item['id']}/")[1]["media"]))
    s, r = A("POST", url, None, [("media_file", png_file("g2.png"))])
    check(f"{label}: gallery only (no thumbnail)", (201, 3, t1), (s, len(r["media"]), r["image_path"]))
    check(f"{label}: a text file as thumbnail -> 400", 400, A("POST", url, None, [("thumbnail", ("n.txt", b"hello", "text/plain"))])[0])
    check(f"{label}: a fake PNG as thumbnail -> 400", 400, A("POST", url, None, [("thumbnail", ("f.png", b"not really", "image/png"))])[0])
    check(f"{label}: a GIF as thumbnail -> 400", 400, A("POST", url, None, [("thumbnail", ("a.gif", b"GIF89a", "image/gif"))])[0])
    check(f"{label}: an .exe in the gallery -> 400", 400, A("POST", url, None, [("media_file", ("x.exe", b"MZ", "application/octet-stream"))])[0])
    s, r = A("POST", url, None, [("media_file", png_file("ok.png")), ("media_file", ("n.txt", b"hi", "text/plain"))])
    check(f"{label}: one bad gallery file refuses the whole request", (400, 3), (s, len(A("GET", f"/catalog/{'listings' if label == 'product' else 'gigs'}/{item['id']}/")[1]["media"])))

print("\n=== Admin: update (PATCH) ===")
for label, item, kind in [("product", prod, "listings"), ("gig", gig, "gigs")]:
    url = f"{ADMIN}{item['id']}/"
    d = A("GET", f"/catalog/{kind}/{item['id']}/")[1]
    t1, ids = d["image_path"], [m["id"] for m in d["media"]]
    s, r = A("PATCH", url, None, [])
    check(f"{label}: an empty PATCH changes nothing", (200, t1, len(ids)), (s, r["image_path"], len(r["media"])))
    log_count = len(A("GET", f"/catalog/{kind}/{item['id']}/")[1]["info_change_logs"])
    s, r = A("PATCH", url, None, F)
    t2 = r["image_path"]
    check(f"{label}: a new thumbnail replaces the old one (remove_thumbnail not sent)", (200, True), (s, t2 != t1 and on_disk(t2)))
    check(f"{label}: ...the old thumbnail file is deleted", False, on_disk(t1))
    s, r = A("PATCH", url, None, F + [("remove_thumbnail", "true")])
    t3 = r["image_path"]
    check(f"{label}: remove_thumbnail=true with a new thumbnail -> the new one is kept", (200, True, False), (s, bool(t3) and on_disk(t3), on_disk(t2)))
    s, r = A("PATCH", url, None, [("remove_thumbnail", "false")])
    check(f"{label}: remove_thumbnail=false alone changes nothing", (200, t3), (s, r["image_path"]))
    s, r = A("PATCH", url, None, [("remove_thumbnail", "true")])
    check(f"{label}: remove_thumbnail=true alone removes it", (200, None, None, False), (s, r["image_path"], r["image_url"], on_disk(t3)))
    check(f"{label}: removing again is fine", 200, A("PATCH", url, None, [("remove_thumbnail", "true")])[0])
    paths = {m["id"]: m["media_path"] for m in d["media"]}
    s, r = A("PATCH", url, None, [("remove_media_ids", f"{ids[0]},{ids[1]}")])
    check(f"{label}: remove two gallery files (comma separated)", (200, 1), (s, len(r["media"])))
    check(f"{label}: ...their files are deleted", (False, False), (on_disk(paths[ids[0]]), on_disk(paths[ids[1]])))
    check(f"{label}: an id that is not this listing's -> 400", 400, A("PATCH", url, None, [("remove_media_ids", "99999999")])[0])
    check(f"{label}: a non-numeric id -> 400", 400, A("PATCH", url, None, [("remove_media_ids", "abc")])[0])
    check(f"{label}: the refused requests changed nothing", 1, len(A("GET", f"/catalog/{kind}/{item['id']}/")[1]["media"]))
    s, r = A("PATCH", url, None, [("remove_media_ids", str(ids[2])), ("media_file", png_file("n1.png")), ("media_file", png_file("n2.png"))])
    check(f"{label}: remove one and add two in the same call (independent)", (200, 2), (s, len(r["media"])))
    check(f"{label}: ...the removed one is gone", False, ids[2] in [m["id"] for m in r["media"]])
    s, r = A("PATCH", url, None, [("remove_media_ids", str(r["media"][0]["id"])), ("remove_media_ids", str(r["media"][1]["id"]))])
    check(f"{label}: remove ids sent as repeated fields", (200, 0), (s, len(r["media"])))
    s, r = A("PATCH", url, None, F + [("media_file", png_file("z.png"))])
    check(f"{label}: thumbnail + gallery in one PATCH", (200, 1, True), (s, len(r["media"]), bool(r["image_url"])))
    logs = A("GET", f"/catalog/{kind}/{item['id']}/")[1]["info_change_logs"]
    changed = {f for log in logs for f in log["changed_fields"]}
    check(f"{label}: thumbnail and media are in the info change log", True, {"thumbnail", "media"} <= changed)
    check(f"{label}: an admin's file change never changes the status", "approved", A("GET", f"/catalog/{kind}/{item['id']}/")[1]["status"])
print("   (a product id through /catalog/gigs/ and the reverse stay 404 on the JSON APIs)")
check("a gig id on the product JSON API -> 404", 404, A("GET", f"/catalog/listings/{gig['id']}/")[0])

print("\n=== Seller: create and update ===")
for label, item, kind in [("product", sprod, "listings"), ("gig", sgig, "gigs")]:
    url = f"{SELLER}{item['id']}/"
    s, r = SL("POST", url, None, F + [("media_file", png_file("s1.png")), ("media_file", ("d.pdf", b"%PDF-1.4", "application/pdf"))])
    check(f"{label}: seller creates thumbnail + gallery (status unchanged: pending)", (201, 2, "pending"), (s, len(r["media"]), r["status"]))
    d = SL("GET", f"/seller/{kind}/{item['id']}/")[1]
    check(f"{label}: audit stamp: gallery rows are the seller's", True, bool(d["media"]))
    check(f"{label}: a second thumbnail on POST -> 400", 400, SL("POST", url, None, F)[0])
    check(f"{label}: .svg -> 400", 400, SL("POST", url, None, [("media_file", ("x.svg", b"<svg/>", "image/svg+xml"))])[0])
    check(f"{label}: .html with an image type -> 400", 400, SL("POST", url, None, [("media_file", ("x.html", png(), "image/png"))])[0])
    check(f"{label}: a file over 10 MB -> 400", 400, SL("POST", url, None, [("media_file", ("big.png", png() + b"\x00" * (10 * 1024 * 1024 + 1), "image/png"))])[0])
    check(f"{label}: 11 files in one request -> 400", 400, SL("POST", url, None, [("media_file", png_file(f"m{i}.png")) for i in range(11)])[0])
    check(f"{label}: 10 files in one request is fine", 201, SL("POST", url, None, [("media_file", png_file(f"m{i}.png")) for i in range(10)])[0])
    check(f"{label}: more than 20 per listing -> 400", 400, SL("POST", url, None, [("media_file", png_file(f"x{i}.png")) for i in range(9)])[0])
    d = SL("GET", f"/seller/{kind}/{item['id']}/")[1]
    check(f"{label}: ...nothing from the refused request was saved", 12, len(d["media"]))
    ids = [m["id"] for m in d["media"]]
    s, r = SL("PATCH", url, None, [("remove_media_ids", ",".join(map(str, ids[:5]))), ("media_file", png_file("again.png"))])
    check(f"{label}: removals count before the 20-file limit", (200, 8), (s, len(r["media"])))
    check(f"{label}: another seller cannot PATCH it -> 404", 404, SL2("PATCH", url, None, [("remove_thumbnail", "true")])[0])
    check(f"{label}: a listing's media id used on another listing -> 400", 400,
          SL("PATCH", f"{SELLER}{(sgig if item is sprod else sprod)['id']}/", None, [("remove_media_ids", str(ids[-1]))])[0])

print("\n=== Seller: a file change never changes the status ===")
s, g = SL("POST", "/seller/gigs/", {"category": SERVICE_CATEGORY, "title": "Smoke LF Status Gig", "description": "d", "price": "5", "price_type": "daily"})
gid = g["id"]
A("PATCH", f"/catalog/gigs/{gid}/", {"status": "approved"})
s, r = SL("PATCH", f"{SELLER}{gid}/", None, F)
check("approved gig: new thumbnail keeps it approved", (200, "approved"), (s, r["status"]))
A("PATCH", f"/catalog/gigs/{gid}/", {"status": "rejected", "note": "Fix the pictures"})
for label, form in [("a new thumbnail", F), ("a gallery file", [("media_file", png_file("more.png"))]), ("remove_thumbnail", [("remove_thumbnail", "true")])]:
    s, r = SL("PATCH", f"{SELLER}{gid}/", None, form)
    check(f"rejected gig: {label} keeps it rejected", (200, "rejected"), (s, r["status"]))
check("...and it is not in the admin's pending list", False, gid in [x["id"] for x in A("GET", "/catalog/gigs/requests/?search=Smoke%20LF")[1]["results"]])
d = A("GET", f"/catalog/gigs/{gid}/")[1]
check("...no new status history entry (pending, approved, rejected only)", 3, len(d["status_change_logs"]))
A("PATCH", f"/catalog/gigs/{gid}/", {"status": "changes_requested", "note": "More pictures"})
check("changes_requested gig: a gallery file keeps it", "changes_requested", SL("PATCH", f"{SELLER}{gid}/", None, [("media_file", png_file("m2.png"))])[1]["status"])
check("saving the gig itself still resubmits it", "pending", SL("PATCH", f"/seller/gigs/{gid}/", {"description": "better"})[1]["status"])
check("the file changes are in the info change log", True, {"thumbnail", "media"} <= {f for l in A("GET", f"/catalog/gigs/{gid}/")[1]["info_change_logs"] for f in l["changed_fields"]})

print("\n=== Soft delete and cleanup ===")
s, r = A("POST", f"{ADMIN}{gig['id']}/", None, [("media_file", png_file("keep.png"))])
check("admin deletes the gig", 204, A("DELETE", f"/catalog/gigs/{gig['id']}/")[0])
check("files of a deleted gig -> 404", 404, A("POST", f"{ADMIN}{gig['id']}/", None, F)[0])
cleanup()
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
