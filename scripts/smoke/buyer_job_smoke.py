#!/usr/bin/env python3
"""Smoke test: a buyer's own job postings.

    GET/POST  /buyer/jobs/
    GET/PATCH /buyer/jobs/{id}/
    GET       /buyer/jobs/{id}/bids/

A job skips admin moderation entirely (no draft/pending/approved review) —
it starts `open_for_bidding` directly. Covers the full buyer-side state
machine (pause/reopen/cancel), the mandatory budget SKU, category/ownership
scoping, and the bids-on-my-job list. Accepting a bid is a later step (no
seller can bid yet), so only the empty-list and auth shape of the bids
endpoint are checked here. Everything it creates is named "Smoke Job ..."
and removed at the end (and at the start). Runs against SMOKE_BASE (default
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
        "from apps.accounts.models import User\n"
        "from apps.catalog.models import Listing\n"
        "Listing.all_objects.filter(title__istartswith='Smoke Job').delete()\n"
        "User.objects.filter(phone__startswith='+8801700096').delete()\n"
    )


cleanup()

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke Job Buyer", "phone": "+8801700096001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

print("=== Nothing yet ===")
s, empty = B("GET", "/buyer/jobs/")
check("empty list -> 200, count 0", (200, 0), (s, empty["count"]))
check("no token -> 401", 401, call("GET", "/buyer/jobs/")[0])

print("\n=== Create ===")
check("no skus -> 400", 400, B("POST", "/buyer/jobs/", {"category": SERVICE_CATEGORY, "title": "Smoke Job No Budget", "description": "d"})[0])
check("a product category -> 400", 400, B("POST", "/buyer/jobs/", {"category": PRODUCT_CATEGORY, "title": "Smoke Job Wrong Cat", "description": "d", "skus": [{"price": "10"}]})[0])
check(
    "two tiers with the same price_type -> 400", 400,
    B("POST", "/buyer/jobs/", {
        "category": SERVICE_CATEGORY, "title": "Smoke Job Dup Tiers", "description": "d",
        "skus": [{"price_type": "fixed", "price": "10"}, {"price_type": "fixed", "price": "20"}],
    })[0],
)

s, job = B("POST", "/buyer/jobs/", {
    "category": SERVICE_CATEGORY, "title": "Smoke Job Logo Design", "description": "Need a logo",
    "skus": [{"price_type": "fixed", "price": "5000"}],
})
check("create -> 201", 201, s)
check("status starts open_for_bidding, not client-chosen", "open_for_bidding", job["status"])
check("budget reflects the single SKU", {"price": "5000.00", "price_type": "fixed"}, job["budget"])
check("accepted_bid is null, bid_count is 0", (None, 0), (job["accepted_bid"], job["bid_count"]))
JOB_ID = job["id"]
SKU_ID = job["skus"][0]["id"]

print("\n=== Read ===")
s, detail = B("GET", f"/buyer/jobs/{JOB_ID}/")
check("detail -> 200", 200, s)
check("detail has location and skus", True, "location" in detail and len(detail["skus"]) == 1)
s, mine = B("GET", "/buyer/jobs/")
check("shows up in my list", [JOB_ID], [r["id"] for r in mine["results"]])

print("\n=== Bids on my job (none yet — sellers can't bid until a later step) ===")
s, bids = B("GET", f"/buyer/jobs/{JOB_ID}/bids/")
check("empty bids list -> 200, count 0", (200, 0), (s, bids["count"]))

print("\n=== Edit ===")
s, updated = B("PATCH", f"/buyer/jobs/{JOB_ID}/", {
    "title": "Smoke Job Logo Design v2",
    "skus": [{"id": SKU_ID, "price": "5500"}, {"price_type": "hourly", "price": "500"}],
})
check("edit title + add a second budget tier -> 200", 200, s)
check("title updated, now two tiers", ("Smoke Job Logo Design v2", 2), (updated["title"], len(updated["skus"])))

print("\n=== Status: pause / reopen / cancel ===")
check("open_for_bidding -> draft (pause) -> 200", 200, B("PATCH", f"/buyer/jobs/{JOB_ID}/", {"status": "draft"})[0])
check("draft -> open_for_bidding directly -> 400 (must go through pending)", 400, B("PATCH", f"/buyer/jobs/{JOB_ID}/", {"status": "open_for_bidding"})[0])
check("draft -> pending -> 200", 200, B("PATCH", f"/buyer/jobs/{JOB_ID}/", {"status": "pending"})[0])
check("pending -> open_for_bidding (reopen) -> 200", 200, B("PATCH", f"/buyer/jobs/{JOB_ID}/", {"status": "open_for_bidding"})[0])
check("open_for_bidding -> cancelled -> 200", 200, B("PATCH", f"/buyer/jobs/{JOB_ID}/", {"status": "cancelled"})[0])
check("editing a cancelled job -> 400", 400, B("PATCH", f"/buyer/jobs/{JOB_ID}/", {"title": "nope"})[0])

print("\n=== in_progress: only 'mark complete' is allowed, nothing else ===")
in_progress_id = int(shell(
    "from apps.catalog.models import Listing; "
    "j = Listing.all_objects.get(title='Smoke Job Logo Design v2'); "
    "j.status = Listing.Status.IN_PROGRESS; j.save(); print(j.id)"
))
check("editing a field while in_progress -> 400", 400, B("PATCH", f"/buyer/jobs/{in_progress_id}/", {"title": "hacked"})[0])
s, completed = B("PATCH", f"/buyer/jobs/{in_progress_id}/", {"status": "completed"})
check("marking it complete while in_progress -> 200", (200, "completed"), (s, completed.get("status")))
check("editing a completed job -> 400", 400, B("PATCH", f"/buyer/jobs/{in_progress_id}/", {"title": "nope"})[0])

print("\n=== Scoping ===")
s, other_reg = call("POST", "/auth/buyer/register/", body={"name": "Smoke Job Buyer Two", "phone": "+8801700096002", "password": "Buy@12345"})
OT = other_reg["access"]
check("another buyer cannot see this job -> 404", 404, call("GET", f"/buyer/jobs/{JOB_ID}/", token=OT)[0])
check("another buyer cannot edit this job -> 404", 404, call("PATCH", f"/buyer/jobs/{JOB_ID}/", token=OT, body={"title": "nope"})[0])
check("another buyer's job list is empty", 0, call("GET", "/buyer/jobs/", token=OT)[1]["count"])

print("\n=== Auth ===")
s, slogin = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = slogin["access"]
check("an admin token -> 403", 403, call("GET", "/buyer/jobs/", token=AT)[0])

cleanup()
print("\n=== Cleanup ===")
check("no Smoke Job listings left", 0, int(shell("from apps.catalog.models import Listing; print(Listing.all_objects.filter(title__istartswith='Smoke Job').count())") or 0))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
