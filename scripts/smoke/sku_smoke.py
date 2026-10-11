#!/usr/bin/env python3
"""Smoke test: attributes, attribute values, and listing SKUs.

Runs against a running dev server (SMOKE_BASE, default http://127.0.0.1:8000)
and the accounts in docs/test-accounts.md. Everything it creates is named
"Smoke ..." and is removed at the end (and at the start, in case an earlier
run was interrupted). Standard library only.
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:8000") + "/api/v1"
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PRODUCT_CATEGORY = 18
PASS = FAIL = 0


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
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
    code = (
        "from apps.catalog.models import Attribute, Listing\n"
        "Listing.all_objects.filter(title__istartswith='Smoke SKU').delete()\n"
        "Attribute.objects.filter(name__istartswith='Smoke').delete()\n"
        "from apps.catalog.models import Category\n"
        "Category.objects.filter(name__istartswith='Smoke').delete()\n"
    )
    subprocess.run(["uv", "run", "manage.py", "shell", "-c", code], cwd=SERVER_DIR,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def login(kind, email, password):
    status, body = call("POST", f"/auth/{kind}/login/", body={"email": email, "password": password})
    return body["access"] if status == 200 else ""


def iso(delta_days):
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=delta_days)).strftime("%Y-%m-%dT%H:%M:%SZ")


cleanup()
T = login("admin", "test.admin@egoola.com", "Test@12345")
check("admin login", True, bool(T))
A = lambda m, p, b=None: call(m, p, T, b)  # noqa: E731


def listing_payload(title, skus=None, **extra):
    payload = {"category": PRODUCT_CATEGORY, "catalog_type": "product", "listing_type": "general",
               "title": title, "description": "d"}
    if skus is not None:
        payload["skus"] = skus
    payload.update(extra)
    return payload


print("\n=== Access control ===")
check("no token -> 401", 401, call("GET", "/catalog/attributes/")[0])
seller_token = login("seller", "test.seller@egoola.com", "Test@12345")
check("seller token -> 403 (attributes)", 403, call("GET", "/catalog/attributes/", seller_token)[0])
check("seller token -> 403 (values)", 403, call("GET", "/catalog/attribute-values/", seller_token)[0])

print("\n=== Attribute CRUD ===")
s, size = A("POST", "/catalog/attributes/", {"name": "Smoke Size"})
check("create attribute", 201, s)
check("is_active defaults true", True, size["is_active"])
check("name_bn optional (null)", None, size["name_bn"])
check("description optional (null)", None, size["description"])
check("created_by stamped as admin", "admin", size["creator_type"])
check("starts with no values", [], size["values"])
s, colour = A("POST", "/catalog/attributes/", {"name": "Smoke Colour", "name_bn": "স্মোক-রং", "description": "Product colour", "description_bn": "পণ্যের রং"})
check("create with Bangla name and descriptions", 201, s)
check("name_bn saved", "স্মোক-রং", colour["name_bn"])
check("description_bn saved", "পণ্যের রং", colour["description_bn"])
s, material = A("POST", "/catalog/attributes/", {"name": "Smoke Material"})
check("duplicate name (any case) -> 400", 400, A("POST", "/catalog/attributes/", {"name": "smoke SIZE"})[0])
check("missing name -> 400", 400, A("POST", "/catalog/attributes/", {"name_bn": "x"})[0])
check("blank name -> 400", 400, A("POST", "/catalog/attributes/", {"name": "  "})[0])
check("retrieve", 200, A("GET", f"/catalog/attributes/{size['id']}/")[0])
check("unknown id -> 404", 404, A("GET", "/catalog/attributes/99999999/")[0])
s, r = A("PATCH", f"/catalog/attributes/{material['id']}/", {"name": "Smoke Fabric", "name_bn": "কাপড়"})
check("rename + Bangla name", ("Smoke Fabric", "কাপড়"), (r["name"], r["name_bn"]))
check("rename onto an existing name -> 400", 400, A("PATCH", f"/catalog/attributes/{material['id']}/", {"name": "smoke colour"})[0])
check("keep own name on PUT -> 200", 200, A("PUT", f"/catalog/attributes/{material['id']}/", {"name": "Smoke Fabric", "is_active": True})[0])
check("list filter ?name=", 3, A("GET", "/catalog/attributes/?name=smoke")[1]["count"])
check("list filter ?name= narrower", 1, A("GET", "/catalog/attributes/?name=smoke%20colour")[1]["count"])
check("list ?search= matches Bangla name", 1, A("GET", "/catalog/attributes/?search=" + urllib.request.quote("স্মোক-রং"))[1]["count"])
s, r = A("PATCH", f"/catalog/attributes/{material['id']}/", {"is_active": False})
check("deactivate", False, r["is_active"])
check("filter is_active=false", 1, A("GET", "/catalog/attributes/?name=smoke&is_active=false")[1]["count"])
check("filter is_active=true", 2, A("GET", "/catalog/attributes/?name=smoke&is_active=true")[1]["count"])

print("\n=== Attribute value CRUD ===")
values = {}
for n in ("S", "M", "L", "XL"):
    s, r = A("POST", "/catalog/attribute-values/", {"attribute": size["id"], "name": n})
    check(f"create Size {n}", 201, s)
    values[n] = r["id"]
check("value shows attribute name", "Smoke Size", r["attribute_name"])
check("value is_active defaults true", True, r["is_active"])
s, r = A("POST", "/catalog/attribute-values/", {"attribute": colour["id"], "name": "Red", "name_bn": "লাল", "description": "Bright red", "description_bn": "উজ্জ্বল লাল"})
check("create Colour Red with Bangla", 201, s)
values["Red"] = r["id"]
check("value name_bn saved", "লাল", r["name_bn"])
values["Blue"] = A("POST", "/catalog/attribute-values/", {"attribute": colour["id"], "name": "Blue"})[1]["id"]
values["Green"] = A("POST", "/catalog/attribute-values/", {"attribute": colour["id"], "name": "Green"})[1]["id"]
check("duplicate value in same attribute (any case) -> 400", 400, A("POST", "/catalog/attribute-values/", {"attribute": size["id"], "name": "m"})[0])
check("same name under another attribute is fine", 201, A("POST", "/catalog/attribute-values/", {"attribute": colour["id"], "name": "M"})[0])
check("missing attribute -> 400", 400, A("POST", "/catalog/attribute-values/", {"name": "XXL"})[0])
check("unknown attribute -> 400", 400, A("POST", "/catalog/attribute-values/", {"attribute": 99999999, "name": "XXL"})[0])
check("value under an inactive attribute -> 400", 400, A("POST", "/catalog/attribute-values/", {"attribute": material["id"], "name": "Cotton"})[0])
check("attribute cannot be changed -> 400", 400, A("PATCH", f"/catalog/attribute-values/{values['M']}/", {"attribute": colour["id"]})[0])
check("same attribute re-sent on PUT is fine", 200, A("PUT", f"/catalog/attribute-values/{values['M']}/", {"attribute": size["id"], "name": "M"})[0])
check("rename value", "Medium", A("PATCH", f"/catalog/attribute-values/{values['M']}/", {"name": "Medium"})[1]["name"])
A("PATCH", f"/catalog/attribute-values/{values['M']}/", {"name": "M"})
check("filter values by attribute", 4, A("GET", f"/catalog/attribute-values/?attribute={size['id']}")[1]["count"])
check("filter values by name", 1, A("GET", f"/catalog/attribute-values/?attribute={size['id']}&name=xl")[1]["count"])
check("filter values by is_active", 0, A("GET", f"/catalog/attribute-values/?attribute={size['id']}&is_active=false")[1]["count"])
check("retrieve value", 200, A("GET", f"/catalog/attribute-values/{values['S']}/")[0])
check("attribute detail lists its values", 4, len(A("GET", f"/catalog/attributes/{size['id']}/")[1]["values"]))


def combo(size_name, colour_name):
    return [{"attribute": size["id"], "attribute_value": values[size_name]},
            {"attribute": colour["id"], "attribute_value": values[colour_name]}]


print("\n=== Listing with SKUs ===")
skus = [
    {"sku": "SMOKE-M-RED", "price": "1800.00", "discounted_price": "1500.00", "stock_qty": 10, "variants": combo("M", "Red")},
    {"sku": "SMOKE-M-BLUE", "price": "1800.00", "stock_qty": 5, "variants": combo("M", "Blue")},
    {"sku": "SMOKE-L-RED", "price": "1900.00", "stock_qty": 0, "variants": combo("L", "Red")},
    {"sku": "SMOKE-L-BLUE", "price": "1900.00", "stock_qty": 8, "variants": combo("L", "Blue")},
]
s, r = A("POST", "/catalog/listings/", listing_payload("Smoke SKU Panjabi", skus))
check("create with 4 SKUs (2 sizes x 2 colours)", 201, s)
LID = r["id"]
check("4 SKUs saved", 4, len(r["skus"]))
check("each SKU has 2 variant rows", [2, 2, 2, 2], [len(x["variants"]) for x in r["skus"]])
check("variant names returned", ("Smoke Size", "M"), (r["skus"][0]["variants"][0]["attribute_name"], r["skus"][0]["variants"][0]["attribute_value_name"]))
check("discounted_price defaults to price", "1800.00", r["skus"][1]["discounted_price"])
check("explicit discount kept", "1500.00", r["skus"][0]["discounted_price"])
check("effective price = discount (no dates)", "1500.00", r["skus"][0]["effective_price"])
check("is_discount_active true", True, r["skus"][0]["is_discount_active"])
check("no-discount SKU is_discount_active false", False, r["skus"][1]["is_discount_active"])
check("reserved_qty starts 0", 0, r["skus"][0]["reserved_qty"])
check("listing price = cheapest SKU's price", "1800.00", r["price"])
check("listing discounted_price = cheapest effective price", "1500.00", r["discounted_price"])
check("listing no longer has stock/colors/sizes fields", [], [k for k in ("stock_qty", "reserved_qty", "color", "colors", "sizes") if k in r])
check("created listing status approved (admin)", "approved", r["status"])
SKU = {x["sku"]: x["id"] for x in r["skus"]}
row = [x for x in A("GET", "/catalog/listings/?search=Smoke%20SKU%20Panjabi")[1]["results"] if x["id"] == LID][0]
check("list row shows from-price", ("1800.00", "1500.00"), (row["price"], row["discounted_price"]))
check("search by SKU code finds the listing", True, any(x["id"] == LID for x in A("GET", "/catalog/listings/?search=SMOKE-L-BLUE")[1]["results"]))

print("\n=== SKU validation ===")
def patch(body):
    return A("PATCH", f"/catalog/listings/{LID}/", body)

check("duplicate combination (new SKU) -> 400", 400, patch({"skus": [{"price": "10", "variants": combo("M", "Red")}]})[0])
check("duplicate combination inside one request -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU dup", [
    {"price": "10", "variants": combo("S", "Red")}, {"price": "11", "variants": combo("S", "Red")}]))[0])
check("different attribute sets -> 400", 400, patch({"skus": [{"price": "10", "variants": [{"attribute": size["id"], "attribute_value": values["S"]}]}]})[0])
check("value of another attribute -> 400", 400, patch({"skus": [{"price": "10", "variants": [
    {"attribute": size["id"], "attribute_value": values["Red"]}, {"attribute": colour["id"], "attribute_value": values["Green"]}]}]})[0])
check("same attribute twice in one SKU -> 400", 400, patch({"skus": [{"price": "10", "variants": [
    {"attribute": size["id"], "attribute_value": values["S"]}, {"attribute": size["id"], "attribute_value": values["XL"]}]}]})[0])
check("unknown attribute value -> 400", 400, patch({"skus": [{"price": "10", "variants": [{"attribute": size["id"], "attribute_value": 99999999}]}]})[0])
check("new SKU without price -> 400", 400, patch({"skus": [{"variants": combo("S", "Green")}]})[0])
check("negative price -> 400", 400, patch({"skus": [{"price": "-1", "variants": combo("S", "Green")}]})[0])
check("negative stock -> 400", 400, patch({"skus": [{"price": "5", "stock_qty": -2, "variants": combo("S", "Green")}]})[0])
check("discounted_price above price -> 400", 400, patch({"skus": [{"price": "5", "discounted_price": "6", "variants": combo("S", "Green")}]})[0])
check("discount end before start -> 400", 400, patch({"skus": [{"price": "10", "discounted_price": "8", "discount_start_date": iso(5), "discount_end_date": iso(1), "variants": combo("S", "Green")}]})[0])
check("discount dates without a discount -> 400", 400, patch({"skus": [{"price": "10", "discount_end_date": iso(5), "variants": combo("S", "Green")}]})[0])
check("SKU code already used -> 400", 400, patch({"skus": [{"sku": "SMOKE-M-RED", "price": "10", "variants": combo("S", "Green")}]})[0])
check("SKU id of another listing -> 400", 400, patch({"skus": [{"id": 99999999, "price": "10"}]})[0])
check("same SKU twice in one request -> 400", 400, patch({"skus": [{"id": SKU["SMOKE-M-RED"], "price": "10"}, {"id": SKU["SMOKE-M-RED"], "price": "11"}]})[0])
check("price shortcut on update -> 400", 400, patch({"price": "10"})[0])
check("stock shortcut on update -> 400", 400, patch({"stock_qty": 5})[0])
check("skus together with price shortcut on create -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU both", [{"price": "10"}], price="10"))[0])
check("create with no skus and no price -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU none"))[0])
check("create with an empty skus list -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU empty", []))[0])

print("\n=== Update by id (never deletes) ===")
r = patch({"skus": [{"id": SKU["SMOKE-M-BLUE"], "price": "2000.00"}]})[1]
by = {x["sku"]: x for x in r["skus"]}
check("price change on a no-discount SKU: discount follows", "2000.00", by["SMOKE-M-BLUE"]["discounted_price"])
check("other SKUs untouched", ("1800.00", "1500.00"), (by["SMOKE-M-RED"]["price"], by["SMOKE-M-RED"]["discounted_price"]))
check("still 4 SKUs", 4, len(r["skus"]))
r = patch({"skus": [{"id": SKU["SMOKE-M-RED"], "price": "2100.00"}]})[1]
by = {x["sku"]: x for x in r["skus"]}
check("discounted SKU keeps its discount when price changes", "1500.00", by["SMOKE-M-RED"]["discounted_price"])
check("price below the stored discount -> 400", 400, patch({"skus": [{"id": SKU["SMOKE-M-RED"], "price": "1000.00"}]})[0])
r = patch({"skus": [{"id": SKU["SMOKE-L-RED"], "stock_qty": 12}]})[1]
check("stock update only", 12, [x for x in r["skus"] if x["sku"] == "SMOKE-L-RED"][0]["stock_qty"])
check("stock update left price alone", "1900.00", [x for x in r["skus"] if x["sku"] == "SMOKE-L-RED"][0]["price"])
check("variants kept when not sent", 2, len([x for x in r["skus"] if x["sku"] == "SMOKE-L-RED"][0]["variants"]))
r = patch({"skus": [{"id": SKU["SMOKE-L-RED"], "variants": combo("S", "Green")}]})[1]
check("variants replaced when sent", ("S", "Green"), tuple(v["attribute_value_name"] for v in [x for x in r["skus"] if x["sku"] == "SMOKE-L-RED"][0]["variants"]))
patch({"skus": [{"id": SKU["SMOKE-L-RED"], "variants": combo("L", "Red")}]})
r = patch({"skus": [{"sku": "SMOKE-S-GREEN", "price": "1700.00", "stock_qty": 3, "variants": combo("S", "Green")}]})[1]
check("new SKU added with the others kept", 5, len(r["skus"]))
r = patch({"title": "Smoke SKU Panjabi v2"})[1]
check("editing the listing without skus keeps all SKUs", 5, len(r["skus"]))
r = patch({"skus": [{"id": SKU["SMOKE-M-RED"], "is_active": False}]})[1]
check("deactivate a SKU (still returned, flagged)", False, [x for x in r["skus"] if x["sku"] == "SMOKE-M-RED"][0]["is_active"])
check("deactivated SKU still counted (never deleted)", 5, len(r["skus"]))
check("from-price now ignores the deactivated SKU", "1700.00", r["price"])
check("deactivated combo cannot be re-added", 400, patch({"skus": [{"price": "5", "variants": combo("M", "Red")}]})[0])
r = patch({"skus": [{"id": SKU["SMOKE-M-RED"], "is_active": True}]})[1]
check("reactivate it", "1500.00", r["discounted_price"])
every = {x["sku"]: x["id"] for x in A("GET", f"/catalog/listings/{LID}/")[1]["skus"]}
r = patch({"skus": [{"id": i, "is_active": False} for i in every.values()]})[1]
check("all SKUs inactive -> listing price null", (None, None), (r["price"], r["discounted_price"]))
patch({"skus": [{"id": i, "is_active": True} for i in every.values()]})

print("\n=== Discount window ===")
one = every["SMOKE-L-BLUE"]
r = patch({"skus": [{"id": one, "discounted_price": "1500.00", "discount_start_date": iso(-2), "discount_end_date": iso(2)}]})[1]
x = [y for y in r["skus"] if y["id"] == one][0]
check("window open: effective = discounted", "1500.00", x["effective_price"])
check("window open: is_discount_active", True, x["is_discount_active"])
r = patch({"skus": [{"id": one, "discount_start_date": iso(1), "discount_end_date": iso(5)}]})[1]
x = [y for y in r["skus"] if y["id"] == one][0]
check("not started yet: effective = price", "1900.00", x["effective_price"])
check("not started yet: not active", False, x["is_discount_active"])
check("stored discounted_price unchanged", "1500.00", x["discounted_price"])
r = patch({"skus": [{"id": one, "discount_start_date": iso(-9), "discount_end_date": iso(-3)}]})[1]
x = [y for y in r["skus"] if y["id"] == one][0]
check("ended: effective = price", "1900.00", x["effective_price"])
r = patch({"skus": [{"id": one, "discount_start_date": None, "discount_end_date": None}]})[1]
x = [y for y in r["skus"] if y["id"] == one][0]
check("dates cleared: discount applies again", "1500.00", x["effective_price"])

print("\n=== Price tiers with listing_sku ===")
tier = {"min_qty": 10, "max_qty": 49, "price": "1700.00", "discounted_price": "1600.00"}
r = patch({"price_tiers": [{**tier, "listing_sku": every["SMOKE-M-BLUE"]}, {"min_qty": 50, "price": "1500.00"}]})
check("tier tied to this listing's SKU", 200, r[0])
check("tier shows listing_sku", every["SMOKE-M-BLUE"], r[1]["price_tiers"][0]["listing_sku"])
check("tier without listing_sku -> null (listing-wide)", None, r[1]["price_tiers"][1]["listing_sku"])
s, other = A("POST", "/catalog/listings/", listing_payload("Smoke SKU other", price="50", sku="SMOKE-OTHER"))
OTHER = other["id"]
check("tier with another listing's SKU -> 400", 400, patch({"price_tiers": [{**tier, "listing_sku": other["skus"][0]["id"]}]})[0])
check("tier SKU on create -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU t", price="5", price_tiers=[{**tier, "listing_sku": every["SMOKE-M-BLUE"]}]))[0])

print("\n=== Simple listing (price shortcut) ===")
check("shortcut created one SKU", 1, len(other["skus"]))
check("shortcut SKU has no variants", [], other["skus"][0]["variants"])
check("shortcut SKU code saved", "SMOKE-OTHER", other["skus"][0]["sku"])
check("from-price", "50.00", other["price"])
s, r = A("POST", "/catalog/listings/", listing_payload("Smoke SKU simple", price="100", discounted_price="80", stock_qty=7))
check("shortcut with discount and stock -> 201", 201, s)
check("shortcut discount saved", ("100.00", "80.00", 7), (r["skus"][0]["price"], r["skus"][0]["discounted_price"], r["skus"][0]["stock_qty"]))
SIMPLE = r["id"]
check("single-SKU listing can later get options", 200, A("PATCH", f"/catalog/listings/{SIMPLE}/", {"skus": [{"id": r["skus"][0]["id"], "variants": [{"attribute": size["id"], "attribute_value": values["S"]}]}]})[0])
check("negative shortcut price -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU neg", price="-4"))[0])
check("shortcut discount above price -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU hi", price="4", discounted_price="9"))[0])
check("duplicate SKU code on create -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU dupcode", price="4", sku="SMOKE-OTHER"))[0])
s, r = A("POST", "/catalog/listings/", listing_payload("Smoke SKU svc", price="2000", catalog_type="service", category=29, price_type="fixed"))
check("services get SKUs too", 201, s)
check("service has one SKU", 1, len(r["skus"]))

print("\n=== Attribute protection ===")
check("delete attribute in use -> 409", 409, A("DELETE", f"/catalog/attributes/{size['id']}/")[0])
check("delete value in use -> 409", 409, A("DELETE", f"/catalog/attribute-values/{values['L']}/")[0])
check("deactivate a used value is allowed", False, A("PATCH", f"/catalog/attribute-values/{values['L']}/", {"is_active": False})[1]["is_active"])
check("inactive value cannot be newly chosen -> 400", 400, patch({"skus": [{"price": "5", "variants": combo("L", "Green")}]})[0])
check("existing SKU keeps using the inactive value (edit ok)", 200, patch({"skus": [{"id": every["SMOKE-L-BLUE"], "stock_qty": 9}]})[0])
A("PATCH", f"/catalog/attribute-values/{values['L']}/", {"is_active": True})
A("PATCH", f"/catalog/attributes/{colour['id']}/", {"is_active": False})
check("inactive attribute cannot be newly chosen -> 400", 400, patch({"skus": [{"price": "5", "variants": combo("XL", "Green")}]})[0])
A("PATCH", f"/catalog/attributes/{colour['id']}/", {"is_active": True})
s, spare = A("POST", "/catalog/attributes/", {"name": "Smoke Spare"})
s, spare_value = A("POST", "/catalog/attribute-values/", {"attribute": spare["id"], "name": "One"})
check("delete unused value -> 204", 204, A("DELETE", f"/catalog/attribute-values/{spare_value['id']}/")[0])
s, spare_value = A("POST", "/catalog/attribute-values/", {"attribute": spare["id"], "name": "Two"})
check("delete unused attribute (with its values) -> 204", 204, A("DELETE", f"/catalog/attributes/{spare['id']}/")[0])
check("its values are gone", 404, A("GET", f"/catalog/attribute-values/{spare_value['id']}/")[0])

print("\n=== Category protection ===")
s, parent_cat = A("POST", "/catalog/categories/", {"type": "product", "name": "Smoke Parent Category"})
s, child_cat = A("POST", "/catalog/categories/", {"type": "product", "name": "Smoke Child Category", "parent": parent_cat["id"]})
check("a listing can use a category", 201, A("POST", "/catalog/listings/", listing_payload("Smoke SKU category", price="5", category=child_cat["id"]))[0])
check("delete a category used by a listing -> 409", 409, A("DELETE", f"/catalog/categories/{child_cat['id']}/")[0])
check("delete a parent whose child is used -> 409", 409, A("DELETE", f"/catalog/categories/{parent_cat['id']}/")[0])
check("deactivating a used category is fine", 200, A("PATCH", f"/catalog/categories/{child_cat['id']}/", {"status": "inactive"})[0])
check("inactive category cannot receive a new listing -> 400", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU inactive cat", price="5", category=child_cat["id"]))[0])

print("\n=== Soft-deleted listing ===")
check("delete listing -> 204", 204, A("DELETE", f"/catalog/listings/{OTHER}/")[0])
check("its SKU code stays reserved", 400, A("POST", "/catalog/listings/", listing_payload("Smoke SKU again", price="4", sku="SMOKE-OTHER"))[0])

print("\n=== Cleanup ===")
cleanup()
left = A("GET", "/catalog/attributes/?name=smoke")[1]["count"]
check("no Smoke attributes left", 0, left)
check("no Smoke SKU listings left", 0, A("GET", "/catalog/listings/?search=Smoke%20SKU")[1]["count"])
print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
