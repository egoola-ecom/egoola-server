#!/usr/bin/env python3
"""Smoke test: the seller job board and bidding.

    GET       /seller/jobs/
    GET       /seller/jobs/{id}/
    GET       /seller/jobs/mine/
    POST      /seller/jobs/{job_id}/bids/
    GET/PATCH /seller/bids/{id}/
    GET       /seller/bids/

A bid can only be created on an `open_for_bidding` job, and a seller may
have only one *live* (pending/accepted) bid on a job at a time, though
cancelling and re-bidding leaves two historical rows. Editing a pending
bid's price tiers reconciles the same way a listing's SKUs do. Everything
created is named "Smoke SJob ..." (job) / "+8801700099..." (sellers) and
removed at the end (and at the start). Runs against SMOKE_BASE (default
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
    out = subprocess.run(["uv", "run", "manage.py", "shell", "-c", code], cwd=SERVER_DIR, capture_output=True, text=True).stdout
    return out.strip().splitlines()[-1] if out.strip() else ""


def cleanup():
    shell(
        "from apps.accounts.models import Seller, User\n"
        "from apps.orders.models import Order, OrderItem\n"
        "from apps.bidding.models import Bid\n"
        "from apps.catalog.models import Listing\n"
        "jobs = Listing.all_objects.filter(title__istartswith='Smoke SJob')\n"
        "OrderItem.objects.filter(order__listing__in=jobs).delete()\n"
        "Order.objects.filter(listing__in=jobs).delete()\n"
        "Bid.objects.filter(listing__in=jobs).delete()\n"
        "jobs.delete()\n"
        "User.objects.filter(phone__startswith='+8801700099').delete()\n"
        "Seller.objects.filter(phone__startswith='+8801700098').delete()\n"
    )


def login(kind, identifier, password):
    field = "phone" if kind == "seller" else "email"
    status, body = call("POST", f"/auth/{kind}/login/", body={field: identifier, "password": password})
    return body["access"] if status == 200 else ""


cleanup()

AT = login("admin", "test.admin@egoola.com", "Test@12345")
check("admin login", True, bool(AT))
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731


def mk_seller(n, **extra):
    body = {
        "name": f"Smoke SJob Seller {n}", "email": f"smoke.sjob.{n}@example.com",
        "phone": f"+88017000982{n:02d}", "password": "Sell@12345",
    }
    body.update(extra)
    s, r = A("POST", "/accounts/sellers/", body)
    assert s == 201, r
    return r["id"], login("seller", body["phone"], "Sell@12345")


S1, T1 = mk_seller(1)
_, TPENDING = mk_seller(2, verification_status="pending")
S3, T3 = mk_seller(3)
S = lambda m, p, b=None: call(m, p, T1, b)  # noqa: E731
S_OTHER = lambda m, p, b=None: call(m, p, T3, b)  # noqa: E731

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke SJob Buyer", "phone": "+8801700099001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

s, job = B("POST", "/buyer/jobs/", {
    "category": SERVICE_CATEGORY, "title": "Smoke SJob Logo Design", "description": "Need a logo",
    "skus": [{"price_type": "fixed", "price": "5000"}],
})
assert s == 201, job
JOB_ID = job["id"]

print("=== Job board ===")
check("no token -> 401", 401, call("GET", "/seller/jobs/")[0])
check("buyer token -> 403", 403, B("GET", "/seller/jobs/")[0])
check("a pending (unverified) seller -> 403", 403, call("GET", "/seller/jobs/", token=TPENDING)[0])
s, board = S("GET", "/seller/jobs/")
check("board -> 200, the open job shows up", (200, [JOB_ID]), (s, [r["id"] for r in board["results"]]))
check("board row has budget, bid_count 0, my_bid_count 0", ({"price": "5000.00", "price_type": "fixed"}, 0, 0), (board["results"][0]["budget"], board["results"][0]["bid_count"], board["results"][0]["my_bid_count"]))

print("\n=== Job detail ===")
s, detail = S("GET", f"/seller/jobs/{JOB_ID}/")
check("detail -> 200, my_bids empty, location present", (200, [], True), (s, detail["my_bids"], "location" in detail))

print("\n=== Mine (nothing bid on yet) ===")
s, mine = S("GET", "/seller/jobs/mine/")
check("mine -> 200, empty", (200, 0), (s, len(mine["results"])))

print("\n=== Placing a bid ===")
check("no price_tiers -> 400", 400, S("POST", f"/seller/jobs/{JOB_ID}/bids/", {"description": "x"})[0])
check("a pending (unverified) seller -> 403", 403, call("POST", f"/seller/jobs/{JOB_ID}/bids/", token=TPENDING, body={"price_tiers": [{"price_type": "fixed", "price": "1"}]})[0])
s, bid = S("POST", f"/seller/jobs/{JOB_ID}/bids/", {
    "description": "I can do this", "price_tiers": [{"price_type": "fixed", "price": "4500"}],
})
check("create -> 201, starts pending", (201, "pending"), (s, bid.get("status")))
check("total_price computed (price * duration)", "4500.00", bid["price_tiers"][0]["total_price"])
BID_ID, TIER_ID = bid["id"], bid["price_tiers"][0]["id"]
check("a second live bid on the same job by the same seller -> 400", 400, S("POST", f"/seller/jobs/{JOB_ID}/bids/", {"price_tiers": [{"price_type": "hourly", "price": "100"}]})[0])
check("bid on a nonexistent job -> 404", 404, S_OTHER("POST", "/seller/jobs/999999999/bids/", {"price_tiers": [{"price_type": "fixed", "price": "1"}]})[0])

print("\n=== Board / detail / mine reflect the live bid ===")
s, board2 = S("GET", "/seller/jobs/")
check("bid_count and my_bid_count both 1", (1, 1), (board2["results"][0]["bid_count"], board2["results"][0]["my_bid_count"]))
s, detail2 = S("GET", f"/seller/jobs/{JOB_ID}/")
check("detail now lists my bid", [BID_ID], [b["id"] for b in detail2["my_bids"]])
s, mine2 = S("GET", "/seller/jobs/mine/")
check("mine now shows the job", [JOB_ID], [r["id"] for r in mine2["results"]])
check("mine?won=true is empty — bid is still pending, not won yet", 0, len(S("GET", "/seller/jobs/mine/?won=true")[1]["results"]))
s, other_board = S_OTHER("GET", "/seller/jobs/")
check("another seller sees total bid_count but my_bid_count 0", (1, 0), (other_board["results"][0]["bid_count"], other_board["results"][0]["my_bid_count"]))

print("\n=== My bids list / detail ===")
s, mybids = S("GET", "/seller/bids/")
check("my bids -> 200, job embedded", (200, JOB_ID), (s, mybids["results"][0]["job"]["id"]))
check("?status= filter", 1, len(S("GET", "/seller/bids/?status=pending")[1]["results"]))
check("?status= filter, none rejected", 0, len(S("GET", "/seller/bids/?status=rejected")[1]["results"]))
s, biddetail = S("GET", f"/seller/bids/{BID_ID}/")
check("bid detail -> 200", 200, s)
check("another seller's bid list is empty", 0, S_OTHER("GET", "/seller/bids/")[1]["count"] if "count" in S_OTHER("GET", "/seller/bids/")[1] else len(S_OTHER("GET", "/seller/bids/")[1]["results"]))
check("another seller cannot see this bid -> 404", 404, S_OTHER("GET", f"/seller/bids/{BID_ID}/")[0])
check("another seller cannot edit this bid -> 404", 404, S_OTHER("PATCH", f"/seller/bids/{BID_ID}/", {"description": "nope"})[0])

print("\n=== Editing a pending bid (price tier reconcile) ===")
check("two tiers with the same new price_type -> 400", 400, S("PATCH", f"/seller/bids/{BID_ID}/", {
    "price_tiers": [{"price_type": "hourly", "price": "10"}, {"price_type": "hourly", "price": "20"}],
})[0])
s, edited = S("PATCH", f"/seller/bids/{BID_ID}/", {
    "description": "Updated pitch",
    "price_tiers": [{"id": TIER_ID, "price": "4800"}, {"price_type": "hourly", "price": "200"}],
})
check("edit -> 200, now 2 tiers, first one updated in place", (200, 2, "4800.00"), (s, len(edited["price_tiers"]), edited["price_tiers"][0]["price"]))
check("description updated", "Updated pitch", edited["description"])

print("\n=== Cancel ===")
s, cancelled = S("PATCH", f"/seller/bids/{BID_ID}/", {"status": "cancelled"})
check("cancel -> 200", (200, "cancelled"), (s, cancelled.get("status")))
check("editing a cancelled bid -> 400", 400, S("PATCH", f"/seller/bids/{BID_ID}/", {"description": "nope"})[0])

print("\n=== Re-bid after cancelling: a new historical row, not a reuse ===")
s, bid2 = S("POST", f"/seller/jobs/{JOB_ID}/bids/", {"price_tiers": [{"price_type": "fixed", "price": "4700"}]})
check("re-bid -> 201", 201, s)
check("now a second live bid blocks a third", 400, S("POST", f"/seller/jobs/{JOB_ID}/bids/", {"price_tiers": [{"price_type": "fixed", "price": "1"}]})[0])
check("two historical bid rows for this seller on this job now", 2, len([b for b in S("GET", "/seller/bids/")[1]["results"] if b["job"]["id"] == JOB_ID]))

print("\n=== A closed job drops off the board and refuses new bids ===")
check("pause the job -> 200", 200, B("PATCH", f"/buyer/jobs/{JOB_ID}/", {"status": "draft"})[0])
check("no longer on the open board", 0, len(S_OTHER("GET", "/seller/jobs/")[1]["results"]))
check("bidding on it now -> 400", 400, S_OTHER("POST", f"/seller/jobs/{JOB_ID}/bids/", {"price_tiers": [{"price_type": "fixed", "price": "1"}]})[0])
check("a seller who already bid can still see it by id -> 200", 200, S("GET", f"/seller/jobs/{JOB_ID}/")[0])
check("a seller who never bid gets 404 once it's not open", 404, S_OTHER("GET", f"/seller/jobs/{JOB_ID}/")[0])

print("\n=== mine?won=true — only jobs this seller actually got ===")
s, job2 = B("POST", "/buyer/jobs/", {"category": SERVICE_CATEGORY, "title": "Smoke SJob Two", "description": "d", "skus": [{"price_type": "fixed", "price": "2000"}]})
JOB2_ID = job2["id"]
s, bid3 = S("POST", f"/seller/jobs/{JOB2_ID}/bids/", {"price_tiers": [{"price_type": "fixed", "price": "1900"}]})
check("accept it -> 200", 200, B("POST", f"/buyer/jobs/{JOB2_ID}/bids/{bid3['id']}/accept/")[0])
s, won = S("GET", "/seller/jobs/mine/?won=true")
check("won=true shows only the job this seller was hired for", [JOB2_ID], [r["id"] for r in won["results"]])

cleanup()
print("\n=== Cleanup ===")
check("no Smoke SJob listings left", 0, int(shell("from apps.catalog.models import Listing; print(Listing.all_objects.filter(title__istartswith='Smoke SJob').count())") or 0))

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
