#!/usr/bin/env python3
"""Smoke test: the Buyer Panel category list, GET /public/catalog/categories/.

Roots by default, children by `parent_id`, name search, active only (also under an
inactive parent), validation and page-based pagination. No login is needed to read.
Everything it creates is named "Smoke Cat ..." and removed at the end (and at the
start). Runs against SMOKE_BASE (default http://127.0.0.1:8000). Standard library only.
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


def cleanup():
    subprocess.run(["uv", "run", "manage.py", "shell", "-c",
                    "from apps.catalog.models import Category\n"
                    "Category.objects.filter(name__istartswith='Smoke Cat').order_by('-id').delete()"],
                   cwd=SERVER_DIR, capture_output=True, text=True)


cleanup()
s, login = call("POST", "/auth/admin/login/", body={"email": "test.admin@egoola.com", "password": "Test@12345"})
T = login["access"]
A = lambda m, p, b=None: call(m, p, T, b)  # noqa: E731
URL = "/public/catalog/categories/"
G = lambda q="": call("GET", URL + q)  # noqa: E731
names = lambda r: [x["name"] for x in r["results"]]  # noqa: E731


def mk(name, parent=None, type="product", status="active", sort=0, name_bn=""):
    slug = name.lower().replace(" ", "-")
    s, r = A("POST", "/catalog/categories/", {"name": name, "name_bn": name_bn, "slug": slug, "type": type,
                                               "parent": parent, "status": status, "sort_order": sort})
    assert s == 201, (name, s, r)
    return r["id"]


root_a = mk("Smoke Cat Alpha", sort=1)
# The admin API does not write name_bn (it comes from the data migration): set it directly.
subprocess.run(["uv", "run", "manage.py", "shell", "-c",
                f"from apps.catalog.models import Category; Category.objects.filter(pk={root_a}).update(name_bn='আলফা')"],
               cwd=SERVER_DIR, capture_output=True, text=True)
root_b = mk("Smoke Cat Beta", sort=2)
root_off = mk("Smoke Cat Hidden Root", status="inactive")
svc = mk("Smoke Cat Service Root", type="service", sort=3)
kid_a1 = mk("Smoke Cat Alpha Phone", parent=root_a, sort=1)
kid_a2 = mk("Smoke Cat Alpha Laptop", parent=root_a, sort=2)
kid_off = mk("Smoke Cat Alpha Off", parent=root_a, status="inactive")
grand = mk("Smoke Cat Alpha Phone Case", parent=kid_a1)
under_off = mk("Smoke Cat Under Hidden", parent=root_off)

print("\n=== Roots (default) ===")
s, r = G()
check("no token needed -> 200", 200, s)
check("response shape", True, {"count", "page", "page_size", "total_pages", "results"} == set(r))
check("row fields", {"id", "parent", "type", "name", "name_bn", "slug", "image_url", "sort_order", "has_children"}, set(r["results"][0]))
all_roots = []
page = 1
while True:
    s, r = G(f"?page={page}&page_size=100")
    all_roots += r["results"]
    if r["page"] >= r["total_pages"]:
        break
    page += 1
check("only top-level categories", True, all(x["parent"] is None for x in all_roots))
smoke_roots = [x["name"] for x in all_roots if x["name"].startswith("Smoke Cat")]
check("active roots, in sort order", ["Smoke Cat Alpha", "Smoke Cat Beta", "Smoke Cat Service Root"], smoke_roots)
check("an inactive root is not listed", False, "Smoke Cat Hidden Root" in smoke_roots)
check("has_children true / false", (True, False), tuple(x["has_children"] for x in all_roots if x["name"] in ("Smoke Cat Alpha", "Smoke Cat Beta")))
check("an invalid token is ignored", 200, call("GET", URL, "garbage")[0])

print("\n=== Children (parent_id) ===")
s, r = G(f"?parent_id={root_a}")
check("children of a root", (200, ["Smoke Cat Alpha Phone", "Smoke Cat Alpha Laptop"]), (s, names(r)))
check("inactive child is not listed", False, "Smoke Cat Alpha Off" in names(r))
check("has_children of a child", [True, False], [x["has_children"] for x in r["results"]])
s, r = G(f"?parent_id={kid_a1}")
check("next level (grandchildren)", (200, ["Smoke Cat Alpha Phone Case"]), (s, names(r)))
check("a leaf has no children (empty list, 200)", (200, 0), (lambda x: (x[0], x[1]["count"]))(G(f"?parent_id={grand}")))
check("unknown parent -> 404", 404, G("?parent_id=99999999")[0])
check("inactive parent -> 404", 404, G(f"?parent_id={root_off}")[0])
check("a category under an inactive parent -> 404 as a parent_id", 404, G(f"?parent_id={under_off}")[0])

print("\n=== Search ===")
s, r = G("?search=smoke%20cat%20alpha")
check("partial, case-insensitive, across all levels", True, {"Smoke Cat Alpha", "Smoke Cat Alpha Phone", "Smoke Cat Alpha Laptop", "Smoke Cat Alpha Phone Case"} <= set(names(r)))
check("inactive category not found by search", False, "Smoke Cat Alpha Off" in names(r))
check("search by Bangla name", ["Smoke Cat Alpha"], names(G("?search=" + urllib.request.quote("আলফা"))[1]))
check("a category under an inactive parent is not found", [], names(G("?search=Under%20Hidden")[1]))
s, r = G(f"?parent_id={root_a}&search=phone")
check("search + parent_id: only that parent's direct children", ["Smoke Cat Alpha Phone"], names(r))
check("search + parent_id does not reach grandchildren", False, "Smoke Cat Alpha Phone Case" in names(r))
check("a search with no match -> empty 200", (200, 0), (lambda x: (x[0], x[1]["count"]))(G("?search=zzzqqq")))
check("blank search = the default (roots)", True, all(x["parent"] is None for x in G("?search=&page_size=100")[1]["results"]))

print("\n=== Type filter ===")
check("type=service roots", True, "Smoke Cat Service Root" in names(G("?type=service&page_size=100")[1]) and "Smoke Cat Alpha" not in names(G("?type=service&page_size=100")[1]))
check("type=product roots", True, "Smoke Cat Service Root" not in names(G("?type=product&page_size=100")[1]))

print("\n=== Pagination and validation ===")
s, r = G("?page_size=2")
check("page_size=2", (200, 2), (s, len(r["results"])))
check("page info", (1, 2, True), (r["page"], r["page_size"], r["total_pages"] >= 2 and r["count"] >= 3))
s2, r2 = G("?page_size=2&page=2")
check("page 2 differs from page 1", True, set(names(r)).isdisjoint(names(r2)))
check("default page size is 20", True, len(G()[1]["results"]) <= 20)
check("page beyond the last -> 404", 404, G("?page=99999")[0])
check("page_size above the cap -> 400", 400, G("?page_size=101")[0])
check("page_size=0 -> 400", 400, G("?page_size=0")[0])
check("page=0 -> 400", 400, G("?page=0")[0])
check("parent_id=abc -> 400", 400, G("?parent_id=abc")[0])
check("parent_id=0 -> 400", 400, G("?parent_id=0")[0])
check("type=other -> 400", 400, G("?type=other")[0])
check("error shape is {field: [messages]}", True, isinstance(G("?parent_id=abc")[1].get("parent_id"), list))
check("POST is not allowed -> 405", 405, call("POST", URL, T, {})[0])
check("limit / offset are not used (limit is ignored)", True, len(G("?limit=1")[1]["results"]) > 1 or G("?limit=1")[1]["count"] <= 1)

print("\n=== Cleanup ===")
cleanup()
check("no Smoke Cat left", 0, G("?search=Smoke%20Cat")[1]["count"])
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
