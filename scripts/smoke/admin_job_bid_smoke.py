#!/usr/bin/env python3
"""Smoke test: the admin job + bid panel — "admin can do everything".

    GET/POST  /catalog/jobs/
    GET/PATCH /catalog/jobs/{id}/
    GET/POST  /bidding/bids/
    GET/PATCH /bidding/bids/{id}/
    POST      /bidding/bids/{id}/accept/
    POST      /bidding/bids/{id}/reject/

Covers: creating a job on a buyer's behalf, creating a bid on a seller's
behalf, accepting on the buyer's behalf (same cascade as the buyer's own
accept), undoing a hire with `reject` (job reopens, the other bid that
auto-rejected earlier stays rejected, the Order is cancelled), and the one
admin-only transition — `in_progress -> cancelled` with a mandatory reason.
Also re-confirms a job is no longer reachable through `/catalog/listings/`
or `/catalog/gigs/` now that it has its own endpoint. Everything created is
named "Smoke AdminJob ..." and removed at the end (and at the start). Runs
against SMOKE_BASE (default http://127.0.0.1:8000). Standard library only.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:8000") + "/api/v1"
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVICE_CATEGORY = 29
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
    out = subprocess.run(["uv", "run", "manage.py", "shell", "-c", code], cwd=SERVER_DIR, capture_output=True, text=True)
    return out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""


def cleanup():
    shell(
        "from apps.orders.models import Order, OrderItem\n"
        "from apps.bidding.models import Bid\n"
        "from apps.catalog.models import Listing\n"
        "from apps.accounts.models import User, Seller\n"
        "jobs = Listing.all_objects.filter(title__istartswith='Smoke AdminJob')\n"
        "OrderItem.objects.filter(order__listing__in=jobs).delete()\n"
        "Order.objects.filter(listing__in=jobs).delete()\n"
        "Bid.objects.filter(listing__in=jobs).delete()\n"
        "jobs.delete()\n"
        "User.objects.filter(phone__startswith='+8801700094').delete()\n"
        "Seller.objects.filter(phone__startswith='+8801700094').delete()\n"
    )


def login(kind, identifier, password):
    field = "phone" if kind == "seller" else "email"
    status, body = call("POST", f"/auth/{kind}/login/", body={field: identifier, "password": password})
    return body["access"] if status == 200 else ""


cleanup()
AT = login("admin", "test.admin@egoola.com", "Test@12345")
check("admin login", True, bool(AT))
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731


def mk_seller(n):
    body = {
        "name": f"Smoke AdminJob Seller {n}", "email": f"smoke.adminjob.{n}@example.com",
        "phone": f"+88017000941{n:02d}", "password": "Sell@12345",
    }
    s, r = A("POST", "/accounts/sellers/", body)
    assert s == 201, r
    return r["id"], login("seller", body["phone"], "Sell@12345")


S1, T1 = mk_seller(1)
S2, T2 = mk_seller(2)
S1C = lambda m, p, b=None: call(m, p, T1, b)  # noqa: E731
S2C = lambda m, p, b=None: call(m, p, T2, b)  # noqa: E731

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke AdminJob Buyer", "phone": "+8801700094001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BUYER_ID, BT = buyer_reg["id"], buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

print("=== Admin creates a job on a buyer's behalf ===")
check("no buyer -> 400", 400, A("POST", "/catalog/jobs/", {"category": SERVICE_CATEGORY, "title": "Smoke AdminJob No Buyer", "description": "d", "skus": [{"price": "1"}]})[0])
s, job = A("POST", "/catalog/jobs/", {
    "buyer": BUYER_ID, "category": SERVICE_CATEGORY, "title": "Smoke AdminJob One", "description": "d",
    "skus": [{"price_type": "fixed", "price": "5000"}],
})
check("create -> 201, open_for_bidding", (201, "open_for_bidding"), (s, job.get("status")))
check("buyer brief shown", BUYER_ID, job["buyer"]["id"])
JOB_ID = job["id"]
check("the buyer sees it on their own /buyer/jobs/ too", [JOB_ID], [r["id"] for r in B("GET", "/buyer/jobs/")[1]["results"]])

print("\n=== It's not reachable on the old product/gig endpoints ===")
check("a job id on /catalog/listings/ -> 404", 404, A("GET", f"/catalog/listings/{JOB_ID}/")[0])
check("a job id on /catalog/gigs/ -> 404", 404, A("GET", f"/catalog/gigs/{JOB_ID}/")[0])
check("posting a buyer_request to /catalog/listings/ -> 400", 400, A("POST", "/catalog/listings/", {
    "category": SERVICE_CATEGORY, "catalog_type": "service", "posted_by_role": "buyer_request",
    "buyer": BUYER_ID, "title": "Smoke AdminJob Sneaky", "description": "d", "price": "1",
})[0])

print("\n=== Admin creates a bid on a seller's behalf ===")
check("no listing/bidder -> 400", 400, A("POST", "/bidding/bids/", {"price_tiers": [{"price": "1"}]})[0])
s, bid1 = A("POST", "/bidding/bids/", {"listing": JOB_ID, "bidder": S1, "price_tiers": [{"price_type": "fixed", "price": "4500"}]})
check("create bid for seller 1 -> 201, pending", (201, "pending"), (s, bid1.get("status")))
s, bid2 = A("POST", "/bidding/bids/", {"listing": JOB_ID, "bidder": S2, "price_tiers": [{"price_type": "fixed", "price": "4800"}]})
check("create bid for seller 2 -> 201", 201, s)
check("the seller sees the bid admin placed for them", [bid1["id"]], [b["id"] for b in S1C("GET", "/seller/bids/")[1]["results"]])
check("a second live bid for the same seller/job -> 400", 400, A("POST", "/bidding/bids/", {"listing": JOB_ID, "bidder": S1, "price_tiers": [{"price": "1"}]})[0])

print("\n=== Admin oversight list/filters ===")
s, lst = A("GET", f"/bidding/bids/?listing={JOB_ID}")
check("filter by listing -> 2 bids", 2, len(lst["results"]))
s, lst2 = A("GET", f"/bidding/bids/?bidder={S1}")
check("filter by bidder -> 1 bid", 1, len(lst2["results"]))

print("\n=== Admin accepts bid 1 on the buyer's behalf ===")
check("a seller token -> 403", 403, call("POST", f"/bidding/bids/{bid1['id']}/accept/", token=T1)[0])
s, result = A("POST", f"/bidding/bids/{bid1['id']}/accept/")
check("accept -> 200, accepted", (200, "accepted"), (s, result["bid"]["status"]))
ORDER_ID = result["order"]["id"]
check("job -> in_progress", "in_progress", A("GET", f"/catalog/jobs/{JOB_ID}/")[1]["status"])
s, bid2_after = A("GET", f"/bidding/bids/{bid2['id']}/")
check("the rival bid was auto-rejected", "rejected", bid2_after["status"])

print("\n=== Admin undoes the hire (reject an accepted bid) ===")
check("reject without a note -> 400", 400, A("POST", f"/bidding/bids/{bid1['id']}/reject/")[0])
s, rejected = A("POST", f"/bidding/bids/{bid1['id']}/reject/", {"note": "Seller backed out"})
check("reject -> 200, now rejected", (200, "rejected"), (s, rejected.get("status")))
check("job reopened for bidding", "open_for_bidding", A("GET", f"/catalog/jobs/{JOB_ID}/")[1]["status"])
check("the order is now cancelled", "cancelled", shell(f"from apps.orders.models import Order; print(Order.objects.get(pk={ORDER_ID}).status)"))
s, bid2_still = A("GET", f"/bidding/bids/{bid2['id']}/")
check("the earlier auto-rejected bid stays rejected (not restored)", "rejected", bid2_still["status"])
check("rejecting an already-rejected bid again -> 400", 400, A("POST", f"/bidding/bids/{bid1['id']}/reject/", {"note": "x"})[0])

print("\n=== Admin-only transition: in_progress -> cancelled, with a mandatory reason ===")
s, bid3 = A("POST", "/bidding/bids/", {"listing": JOB_ID, "bidder": S1, "price_tiers": [{"price_type": "fixed", "price": "4000"}]})
s, accept3 = A("POST", f"/bidding/bids/{bid3['id']}/accept/")
ORDER3_ID = accept3["order"]["id"]
check("job is in_progress again", "in_progress", A("GET", f"/catalog/jobs/{JOB_ID}/")[1]["status"])
check("the buyer cannot cancel an in_progress job", 400, B("PATCH", f"/buyer/jobs/{JOB_ID}/", {"status": "cancelled"})[0])
check("admin cancel with no note -> 400", 400, A("PATCH", f"/catalog/jobs/{JOB_ID}/", {"status": "cancelled"})[0])
s, admin_cancel = A("PATCH", f"/catalog/jobs/{JOB_ID}/", {"status": "cancelled", "note": "Buyer and admin agreed to call it off"})
check("admin cancel with a note -> 200", (200, "cancelled"), (s, admin_cancel.get("status")))
s, bid3_after = A("GET", f"/bidding/bids/{bid3['id']}/")
check("the accepted bid is now cancelled (not rejected)", "cancelled", bid3_after["status"])
check("its order is cancelled too", "cancelled", shell(f"from apps.orders.models import Order; print(Order.objects.get(pk={ORDER3_ID}).status)"))

cleanup()
print("\n=== Cleanup ===")
check("no Smoke AdminJob listings left", 0, int(shell("from apps.catalog.models import Listing; print(Listing.all_objects.filter(title__istartswith='Smoke AdminJob').count())") or 0))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
