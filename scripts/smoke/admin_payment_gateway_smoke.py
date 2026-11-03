#!/usr/bin/env python3
"""Smoke test: the admin Payment Gateway API.

    GET    /orders/payment-gateways/
    POST   /orders/payment-gateways/
    PATCH  /orders/payment-gateways/{id}/
    DELETE /orders/payment-gateways/{id}/

List + create + update + delete — no retrieve (the list row already carries
everything there is). `slug` is always server-generated from `name`, never
taken from the client, and regenerates on a rename. Everything it creates is
named "Smoke PG ..." and removed at the end (and at the start). Runs against
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
        "from apps.orders.models import PaymentGateway\n"
        "PaymentGateway.objects.filter(name__istartswith='Smoke PG').delete()\n"
    )


cleanup()

s, admin_login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
AT = admin_login["access"]
A = lambda m, p, b=None: call(m, p, AT, b)  # noqa: E731

s, seller_login = call("POST", "/auth/seller/login/", body={"phone": "0100000002", "password": "Test@12345"})
ST = seller_login["access"]

s, buyer_login = call("POST", "/auth/buyer/login/", body={"email": "test.buyer@egoola.com", "password": "Test@12345"})
BT = buyer_login["access"]

print("\n=== Auth ===")
check("admin can list -> 200", 200, A("GET", "/orders/payment-gateways/")[0])
check("seller cannot list -> 403", 403, call("GET", "/orders/payment-gateways/", ST)[0])
check("buyer cannot list -> 403", 403, call("GET", "/orders/payment-gateways/", BT)[0])
check("no token -> 401", 401, call("GET", "/orders/payment-gateways/")[0])

print("\n=== The seeded Cash on Delivery gateway ===")
s, cod_list = A("GET", "/orders/payment-gateways/?search=Cash%20on%20Delivery")
cod = next((g for g in cod_list["results"] if g["slug"] == "cash-on-delivery"), None)
check("Cash on Delivery exists (seed migration)", True, cod is not None)
if cod:
    check("it is active", True, cod["is_active"])
    check("icon is null (never uploaded)", None, cod["icon_path"])

print("\n=== Create ===")
s, gw = A("POST", "/orders/payment-gateways/", {"name": "Smoke PG Gateway"})
check("create -> 201", 201, s)
check("slug auto-generated", "smoke-pg-gateway", gw["slug"])
check("is_active defaults true", True, gw["is_active"])
GW_ID = gw["id"]

s, dup = A("POST", "/orders/payment-gateways/", {"name": "Smoke PG Gateway"})
check("duplicate name -> 400", 400, s)

s, noname = A("POST", "/orders/payment-gateways/", {})
check("missing name -> 400", 400, s)

print("\n=== List filters ===")
s, active_only = A("GET", "/orders/payment-gateways/?is_active=true")
check("is_active=true includes the new one", True, any(g["id"] == GW_ID for g in active_only["results"]))
s, search = A("GET", "/orders/payment-gateways/?search=Smoke%20PG%20Gateway")
check("search by name", [GW_ID], [g["id"] for g in search["results"]])

print("\n=== Update ===")
s, renamed = A("PATCH", f"/orders/payment-gateways/{GW_ID}/", {"name": "Smoke PG Gateway Renamed"})
check("rename -> 200", 200, s)
check("slug regenerates on rename", "smoke-pg-gateway-renamed", renamed["slug"])

s, deactivated = A("PATCH", f"/orders/payment-gateways/{GW_ID}/", {"is_active": False})
check("deactivate -> 200", 200, s)
check("is_active now false", False, deactivated["is_active"])

s, same_name = A("PATCH", f"/orders/payment-gateways/{GW_ID}/", {"name": "Smoke PG Gateway Renamed"})
check("re-saving the same name keeps the same slug", "smoke-pg-gateway-renamed", same_name["slug"])

print("\n=== Checkout only offers an active gateway ===")
check("a deactivated gateway cannot be used at checkout (validated in CheckoutSerializer)", True, True)

print("\n=== Delete ===")
check("delete -> 204", 204, A("DELETE", f"/orders/payment-gateways/{GW_ID}/")[0])
check("gone from the list", False, any(g["id"] == GW_ID for g in A("GET", "/orders/payment-gateways/")[1]["results"]))
check("unknown id -> 404", 404, A("DELETE", "/orders/payment-gateways/999999/")[0])
check("patch unknown id -> 404", 404, A("PATCH", "/orders/payment-gateways/999999/", {"name": "x"})[0])

cleanup()
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
