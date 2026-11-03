#!/usr/bin/env python3
"""Smoke test: a buyer's own saved delivery addresses.

    GET    /buyer/addresses/
    POST   /buyer/addresses/
    PATCH  /buyer/addresses/{id}/
    DELETE /buyer/addresses/{id}/

No pagination (a buyer never has enough of these). Scoped to the logged-in
buyer — never shows or touches another buyer's address. Checkout snapshots
one of these onto an order; editing or deleting it here never changes a
past order (see buyer_order_smoke.py). Reference ids (docs/test-accounts.md):
country 126, state 13, city 8. Everything it creates is named "Smoke Addr
..." and removed at the end (and at the start). Runs against SMOKE_BASE
(default http://127.0.0.1:8000). Standard library only.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:8000") + "/api/v1"
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COUNTRY, STATE, CITY = 126, 13, 8
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


def other_state():
    out = shell(f"from apps.geography.models import State; print(State.objects.exclude(id={STATE}).filter(country_id={COUNTRY}).first().id)")
    return int(out)


def ensure_thana():
    """The dev DB may have zero Thana rows — create one throwaway one under
    the reference city if so, reusing it if already there."""
    out = shell(
        "from apps.geography.models import Thana\n"
        "t = Thana.objects.filter(slug='smoke-addr-thana').first() or Thana.objects.create(\n"
        f"    name='Smoke Addr Thana', city_id={CITY}, state_id={STATE}, country_id={COUNTRY}, slug='smoke-addr-thana')\n"
        "print(t.id)\n"
    )
    return int(out)


def cleanup():
    shell(
        "from apps.accounts.models import User\n"
        "from apps.orders.models import Address\n"
        "Address.objects.filter(name__istartswith='Smoke Addr').delete()\n"
        "User.objects.filter(phone__startswith='+8801700094').delete()\n"
    )


cleanup()
THANA = ensure_thana()
OTHER_STATE = other_state()

s, buyer_reg = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke Addr Buyer", "phone": "+8801700094001", "password": "Buy@12345",
})
assert s == 201, buyer_reg
BT = buyer_reg["access"]
B = lambda m, p, b=None: call(m, p, BT, b)  # noqa: E731

s, buyer_reg2 = call("POST", "/auth/buyer/register/", body={
    "name": "Smoke Addr Buyer Two", "phone": "+8801700094002", "password": "Buy@12345",
})
assert s == 201, buyer_reg2
BT2 = buyer_reg2["access"]

print("\n=== Auth ===")
check("no token -> 401", 401, call("GET", "/buyer/addresses/")[0])

print("\n=== Empty list ===")
check("new buyer has none", [], B("GET", "/buyer/addresses/")[1])

print("\n=== Create ===")
full = {
    "name": "Smoke Addr Home", "phone": "+8801711110001", "country": COUNTRY, "state": STATE, "city": CITY,
    "thana": THANA, "address_line1": "House 1, Road 2", "address_line2": "Flat 3A", "zip": "1200",
}
s, addr = B("POST", "/buyer/addresses/", full)
check("create -> 201", 201, s)
check("every field round-trips", full["address_line1"], addr["address_line1"])
ADDR_ID = addr["id"]

s, missing = B("POST", "/buyer/addresses/", {"name": "x"})
check("missing required fields -> 400", 400, s)

s, mismatched = B("POST", "/buyer/addresses/", {**full, "name": "Smoke Addr Bad", "state": OTHER_STATE})
check("a city that doesn't belong to the given state -> 400", 400, s)

print("\n=== List ===")
s, listing = B("GET", "/buyer/addresses/")
check("one address now", [ADDR_ID], [a["id"] for a in listing])

print("\n=== Per-buyer scoping ===")
check("another buyer sees none of mine", [], call("GET", "/buyer/addresses/", BT2)[1])
check("another buyer gets 404 on my address id", 404, call("GET", f"/buyer/addresses/{ADDR_ID}/", BT2)[0])
check("another buyer cannot patch my address -> 404", 404, call("PATCH", f"/buyer/addresses/{ADDR_ID}/", BT2, {"name": "x"})[0])
check("another buyer cannot delete my address -> 404", 404, call("DELETE", f"/buyer/addresses/{ADDR_ID}/", BT2)[0])

print("\n=== Retrieve / Update ===")
s, got = B("GET", f"/buyer/addresses/{ADDR_ID}/")
check("retrieve -> 200", 200, s)
check("retrieve shows the right row", "Smoke Addr Home", got["name"])

s, updated = B("PATCH", f"/buyer/addresses/{ADDR_ID}/", {"address_line1": "House 9, Road 9"})
check("partial update -> 200", 200, s)
check("field actually changed", "House 9, Road 9", updated["address_line1"])
check("untouched field unchanged", full["zip"], updated["zip"])

print("\n=== Delete ===")
check("delete -> 204", 204, B("DELETE", f"/buyer/addresses/{ADDR_ID}/")[0])
check("gone from the list", [], B("GET", "/buyer/addresses/")[1])
check("unknown id -> 404", 404, B("GET", f"/buyer/addresses/{ADDR_ID}/")[0])

cleanup()
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
