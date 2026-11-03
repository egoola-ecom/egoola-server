#!/usr/bin/env python3
"""Smoke test: a buyer accepting a bid, and the cascades that follow.

    POST /buyer/jobs/{job_id}/bids/{bid_id}/accept/

Accepting creates an Order directly (no cart), auto-rejects every other
pending bid on the job, and moves the job to `in_progress`. Marking an
in_progress job `completed` carries its accepted bid and Order to
`completed` too. Cancelling a job cancels every *live* bid on it (pending
or accepted — never the already-rejected ones) and, if one was accepted,
its Order. Everything created is named "Smoke Accept ..." and removed at
the end (and at the start). Runs against SMOKE_BASE (default
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
        "jobs = Listing.all_objects.filter(title__istartswith='Smoke Accept')\n"
        "OrderItem.objects.filter(order__listing__in=jobs).delete()\n"
        "Order.objects.filter(listing__in=jobs).delete()\n"
        "Bid.objects.filter(listing__in=jobs).delete()\n"
        "jobs.delete()\n"
        "User.objects.filter(phone__startswith='+8801700095').delete()\n"
        "Seller.objects.filter(phone__startswith='+8801700095').delete()\n"
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
        "name": f"Smoke Accept Seller {n}", "email": f"smoke.accept.{n}@example.com",
        "phone": f"+88017000951{n:02d}", "password": "Sell@12345",
    }
    s, r = A("POST", "/accounts/sellers/", body)
    assert s == 201, r
    return login("seller", body["phone"], "Sell@12345")


T1, T2 = mk_seller(1), mk_seller(2)
S1 = lambda m, p, b=None: call(m, p, T1, b)  # noqa: E731
S2 = lambda m, p, b=None: call(m, p, T2, b)  # noqa: E731

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke Accept Buyer", "phone": "+8801700095001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731


def mk_job(title, price="5000"):
    s, job = B("POST", "/buyer/jobs/", {
        "category": SERVICE_CATEGORY, "title": title, "description": "d",
        "skus": [{"price_type": "fixed", "price": price}],
    })
    assert s == 201, job
    return job["id"]


print("=== Accept: wins the job, rejects the rival, creates an Order ===")
JOB1 = mk_job("Smoke Accept Job One")
s, bid1 = S1("POST", f"/seller/jobs/{JOB1}/bids/", {"price_tiers": [{"price_type": "fixed", "price": "4500"}]})
s, bid2 = S2("POST", f"/seller/jobs/{JOB1}/bids/", {"price_tiers": [{"price_type": "fixed", "price": "4800"}]})

check("a non-buyer token -> 403", 403, S1("POST", f"/buyer/jobs/{JOB1}/bids/{bid1['id']}/accept/")[0])
s, result = B("POST", f"/buyer/jobs/{JOB1}/bids/{bid1['id']}/accept/")
check("accept -> 200, bid accepted", (200, "accepted"), (s, result["bid"]["status"]))
check("accepted_price_tier set to the one tier", bid1["price_tiers"][0]["id"], result["bid"]["accepted_price_tier"]["id"])
check("an Order was created for the full tier amount", "4500.00", result["order"]["payable"])
ORDER1 = result["order"]["id"]

s, job_detail = B("GET", f"/buyer/jobs/{JOB1}/")
check("job -> in_progress, accepted_bid shown", ("in_progress", bid1["id"]), (job_detail["status"], job_detail["accepted_bid"]["id"]))
s, rival = S2("GET", f"/seller/bids/{bid2['id']}/")
check("the rival pending bid was auto-rejected", "rejected", rival["status"])
check("accepting the rejected rival now -> 400", 400, B("POST", f"/buyer/jobs/{JOB1}/bids/{bid2['id']}/accept/")[0])
check("accepting the same bid twice -> 400", 400, B("POST", f"/buyer/jobs/{JOB1}/bids/{bid1['id']}/accept/")[0])

print("\n=== Completing the job completes the accepted bid and its Order ===")
check("editing an in_progress job -> 400", 400, B("PATCH", f"/buyer/jobs/{JOB1}/", {"title": "nope"})[0])
check("mark complete -> 200", (200, "completed"), (lambda r: (r[0], r[1].get("status")))(B("PATCH", f"/buyer/jobs/{JOB1}/", {"status": "completed"})))
s, bid1_after = S1("GET", f"/seller/bids/{bid1['id']}/")
check("accepted bid -> completed", "completed", bid1_after["status"])
check("order -> completed", "completed", shell(f"from apps.orders.models import Order; print(Order.objects.get(pk={ORDER1}).status)"))

print("\n=== Cancelling a job cancels its live bid(s), not reject ===")
JOB2 = mk_job("Smoke Accept Job Two", price="1000")
s, bid3 = S1("POST", f"/seller/jobs/{JOB2}/bids/", {"price_tiers": [{"price_type": "fixed", "price": "900"}]})
check("cancel the job -> 200", 200, B("PATCH", f"/buyer/jobs/{JOB2}/", {"status": "cancelled"})[0])
s, bid3_after = S1("GET", f"/seller/bids/{bid3['id']}/")
check("its only pending bid is now cancelled (not rejected)", "cancelled", bid3_after["status"])

print("\n=== Cancelling a job with an accepted bid cancels its Order too ===")
JOB3 = mk_job("Smoke Accept Job Three", price="2000")
s, bid4 = S1("POST", f"/seller/jobs/{JOB3}/bids/", {"price_tiers": [{"price_type": "fixed", "price": "1800"}]})
s, accept3 = B("POST", f"/buyer/jobs/{JOB3}/bids/{bid4['id']}/accept/")
ORDER3 = accept3["order"]["id"]
shell(f"from apps.catalog.models import Listing; j = Listing.all_objects.get(pk={JOB3}); j.status = 'open_for_bidding'; j.save()")
check("cancel (forced back open for this test) -> 200", 200, B("PATCH", f"/buyer/jobs/{JOB3}/", {"status": "cancelled"})[0])
s, bid4_after = S1("GET", f"/seller/bids/{bid4['id']}/")
check("the accepted bid is now cancelled", "cancelled", bid4_after["status"])
check("its order is now cancelled too", "cancelled", shell(f"from apps.orders.models import Order; print(Order.objects.get(pk={ORDER3}).status)"))

print("\n=== A multi-tier bid needs an explicit price_tier_id ===")
JOB4 = mk_job("Smoke Accept Job Four", price="3000")
s, bid5 = S1("POST", f"/seller/jobs/{JOB4}/bids/", {
    "price_tiers": [{"price_type": "fixed", "price": "2500"}, {"price_type": "hourly", "price": "100"}],
})
check("accept with no price_tier_id, 2 tiers -> 400", 400, B("POST", f"/buyer/jobs/{JOB4}/bids/{bid5['id']}/accept/")[0])
check("accept with an id that isn't one of the bid's tiers -> 400", 400, B("POST", f"/buyer/jobs/{JOB4}/bids/{bid5['id']}/accept/", {"price_tier_id": 999999999})[0])
hourly = next(t for t in bid5["price_tiers"] if t["price_type"] == "hourly")
s, accepted5 = B("POST", f"/buyer/jobs/{JOB4}/bids/{bid5['id']}/accept/", {"price_tier_id": hourly["id"]})
check("accept with the explicit tier -> 200, that tier wins", (200, hourly["id"]), (s, accepted5["bid"]["accepted_price_tier"]["id"]))

print("\n=== Can't accept on a job that's not open_for_bidding ===")
JOB5 = mk_job("Smoke Accept Job Five", price="1500")
check("pause it", 200, B("PATCH", f"/buyer/jobs/{JOB5}/", {"status": "draft"})[0])
check("job not open_for_bidding -> 400 (checked before the bid even exists)", 400, B("POST", f"/buyer/jobs/{JOB5}/bids/999999999/accept/")[0])
JOB6 = mk_job("Smoke Accept Job Six", price="1200")
check("a nonexistent bid id on an open job -> 404", 404, B("POST", f"/buyer/jobs/{JOB6}/bids/999999999/accept/")[0])

cleanup()
print("\n=== Cleanup ===")
check("no Smoke Accept listings left", 0, int(shell("from apps.catalog.models import Listing; print(Listing.all_objects.filter(title__istartswith='Smoke Accept').count())") or 0))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
