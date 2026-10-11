#!/usr/bin/env bash
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
BASE="$SMOKE_BASE/api/v1"
PASS=0; FAIL=0
check() { if [ "$2" == "$3" ]; then echo "OK   $1 (got $3)"; PASS=$((PASS+1)); else echo "FAIL $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi; }
jget() { python -c "import sys,json;d=json.load(sys.stdin);print(d$1)" 2>/dev/null; }
post() { curl -s -w '\n%{http_code}' -X "$1" "$BASE$2" -H "$AUTH" -H "Content-Type: application/json" ${3:+-d "$3"}; }
code() { echo "$1" | tail -1; }
body() { echo "$1" | sed '$d'; }

TOKEN=$(curl -s -X POST "$BASE/auth/admin/login/" -H "Content-Type: application/json" \
  -d '{"email":"test.admin@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
AUTH="Authorization: Bearer $TOKEN"
[ -n "$TOKEN" ] && echo "OK   admin login" && PASS=$((PASS+1))

echo "=== Brand CRUD ==="
R=$(post POST /catalog/brands/ '{"name":"Smoke Samsung"}')
check "create brand" 201 "$(code "$R")"
B1=$(body "$R" | jget "['id']")
check "slug generated" "smoke-samsung" "$(body "$R" | jget "['slug']")"
check "is_active default true" "True" "$(body "$R" | jget "['is_active']")"
check "creator_type admin" "admin" "$(body "$R" | jget "['creator_type']")"
check "creator_name stamped" "Test Admin" "$(body "$R" | jget "['creator_name']")"
R=$(post POST /catalog/brands/ '{"name":"smoke samsung"}')
check "duplicate (slug clash) -> 400" 400 "$(code "$R")"
R=$(post POST /catalog/brands/ '{}')
check "name required -> 400" 400 "$(code "$R")"
R=$(post POST /catalog/brands/ '{"name":"Smoke Apple","is_active":false}')
check "create inactive brand" 201 "$(code "$R")"
B2=$(body "$R" | jget "['id']")
check "inactive honored" "False" "$(body "$R" | jget "['is_active']")"
R=$(post PATCH /catalog/brands/$B1/ '{"name":"Smoke Samsung Electronics"}')
check "update name" 200 "$(code "$R")"
check "slug regenerated" "smoke-samsung-electronics" "$(body "$R" | jget "['slug']")"
R=$(post PATCH /catalog/brands/$B1/ '{"name":"Smoke Apple"}')
check "rename onto existing slug -> 400" 400 "$(code "$R")"
R=$(post PATCH /catalog/brands/$B1/ '{"is_active":true}')
check "update is_active only" 200 "$(code "$R")"
R=$(post GET "/catalog/brands/?name=smoke")
check "list filter by name" 200 "$(code "$R")"
check "list name filter count" 2 "$(body "$R" | python -c "import sys,json;d=json.load(sys.stdin);print(len(d['results']) if isinstance(d,dict) else len(d))")"
R=$(post GET "/catalog/brands/?name=zzzz-none")
check "list filter no match" 0 "$(body "$R" | python -c "import sys,json;d=json.load(sys.stdin);print(len(d['results']) if isinstance(d,dict) else len(d))")"
R=$(post GET "/catalog/brands/?is_active=false&name=smoke")
check "list is_active=false" 1 "$(body "$R" | python -c "import sys,json;d=json.load(sys.stdin);print(len(d['results']) if isinstance(d,dict) else len(d))")"
R=$(curl -s -w '\n%{http_code}' "$BASE/catalog/brands/")
check "no token -> 403/401" 401 "$(code "$R")"

echo "=== Listing: brand + optional owner + discounted_price ==="
R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"brand\",\"title\":\"Smoke Brand Listing\",\"description\":\"d\",\"price\":\"150.00\"}")
check "brand listing without brand -> 400" 400 "$(code "$R")"
R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"brand\",\"brand\":$B2,\"title\":\"Smoke Brand Listing\",\"description\":\"d\",\"price\":\"150.00\"}")
check "inactive brand rejected -> 400" 400 "$(code "$R")"
R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"brand\",\"brand\":999999,\"title\":\"Smoke Brand Listing\",\"description\":\"d\",\"price\":\"150.00\"}")
check "unknown brand id -> 400" 400 "$(code "$R")"
R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"brand\",\"brand\":$B1,\"title\":\"Smoke Brand Listing\",\"description\":\"d\",\"price\":\"150.00\",\"discounted_price\":\"120.00\",\"price_tiers\":[{\"min_qty\":1,\"max_qty\":9,\"price\":\"150.00\",\"discounted_price\":\"120.00\"},{\"min_qty\":10,\"price\":\"140.00\"}]}")
check "admin-created, no seller/buyer, brand+discount+tiers -> 201" 201 "$(code "$R")"
L1=$(body "$R" | jget "['id']")
check "seller null" None "$(body "$R" | jget "['seller']")"
check "buyer null" None "$(body "$R" | jget "['buyer']")"
check "brand stored" "$B1" "$(body "$R" | jget "['brand']")"
check "brand_name shown" "Smoke Samsung Electronics" "$(body "$R" | jget "['brand_name']")"
check "price kept original" "150.00" "$(body "$R" | jget "['price']")"
check "discounted_price" "120.00" "$(body "$R" | jget "['discounted_price']")"
check "old_price gone" "None" "$(body "$R" | jget ".get('old_price')")"
check "tier 1 discounted" "120.00" "$(body "$R" | jget "['price_tiers'][0]['discounted_price']")"
check "tier 2 no discount -> equals tier price" "140.00" "$(body "$R" | jget "['price_tiers'][1]['discounted_price']")"

R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Bad Disc\",\"description\":\"d\",\"price\":\"100.00\",\"discounted_price\":\"100.00\"}")
check "discounted == price allowed -> 201" 201 "$(code "$R")"
check "equal discount kept" "100.00" "$(body "$R" | jget "['discounted_price']")"
R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Bad Disc2\",\"description\":\"d\",\"price\":\"100.00\",\"discounted_price\":\"120.00\"}")
check "discounted > price -> 400" 400 "$(code "$R")"
R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Bad Tier\",\"description\":\"d\",\"price\":\"100.00\",\"price_tiers\":[{\"min_qty\":1,\"price\":\"50.00\",\"discounted_price\":\"60.00\"}]}")
check "tier discounted > price -> 400" 400 "$(code "$R")"
SK1=$(body "$(post GET /catalog/listings/$L1/)" | jget "['skus'][0]['id']")
R=$(post PATCH /catalog/listings/$L1/ "{\"skus\":[{\"id\":$SK1,\"discounted_price\":\"200.00\"}]}")
check "PATCH discounted > existing price -> 400" 400 "$(code "$R")"
R=$(post PATCH /catalog/listings/$L1/ "{\"skus\":[{\"id\":$SK1,\"discounted_price\":null}]}")
check "PATCH discounted_price null -> price" 200 "$(code "$R")"
check "null resets discounted to price" "150.00" "$(body "$R" | jget "['skus'][0]['discounted_price']")"
R=$(post PATCH /catalog/listings/$L1/ '{"listing_type":"general","brand":null}')
check "non-brand listing may clear brand" 200 "$(code "$R")"
R=$(post PATCH /catalog/listings/$L1/ '{"listing_type":"brand"}')
check "switch to brand listing_type w/o brand -> 400" 400 "$(code "$R")"
R=$(post PATCH /catalog/listings/$L1/ "{\"listing_type\":\"brand\",\"brand\":$B1}")
check "switch to brand with brand" 200 "$(code "$R")"

R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Plain\",\"description\":\"d\",\"price\":\"10.00\"}")
check "listing w/o brand/seller/buyer -> 201" 201 "$(code "$R")"
L2=$(body "$R" | jget "['id']")
R=$(post GET "/catalog/listings/?brand=$B1")
check "filter listings by brand" 1 "$(body "$R" | python -c "import sys,json;d=json.load(sys.stdin);print(len(d['results']) if isinstance(d,dict) else len(d))")"
R=$(post GET "/catalog/listings/?search=Smoke%20Samsung")
check "search listings by brand name" 1 "$(body "$R" | python -c "import sys,json;d=json.load(sys.stdin);print(len(d['results']) if isinstance(d,dict) else len(d))")"

R=$(post POST /catalog/listings/ "{\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke NoDisc\",\"description\":\"d\",\"price\":\"80.00\",\"price_tiers\":[{\"min_qty\":1,\"price\":\"80.00\"}]}")
check "no discounted_price -> 201" 201 "$(code "$R")"
L3=$(body "$R" | jget "['id']")
check "discounted defaults to price" "80.00" "$(body "$R" | jget "['discounted_price']")"
check "tier discounted defaults to tier price" "80.00" "$(body "$R" | jget "['price_tiers'][0]['discounted_price']")"
SK3=$(body "$(post GET /catalog/listings/$L3/)" | jget "['skus'][0]['id']")
R=$(post PATCH /catalog/listings/$L3/ "{\"skus\":[{\"id\":$SK3,\"price\":\"90.00\"}]}")
check "no-discount SKU follows new price" "90.00" "$(body "$R" | jget "['skus'][0]['discounted_price']")"
R=$(post PATCH /catalog/listings/$L3/ "{\"skus\":[{\"id\":$SK3,\"price\":\"100.00\",\"discounted_price\":\"70.00\"}]}")
check "explicit discount kept" "70.00" "$(body "$R" | jget "['skus'][0]['discounted_price']")"
R=$(post PATCH /catalog/listings/$L3/ "{\"skus\":[{\"id\":$SK3,\"price\":\"120.00\"}]}")
check "discounted SKU keeps its discount when price changes" "70.00" "$(body "$R" | jget "['skus'][0]['discounted_price']")"
R=$(post PATCH /catalog/listings/$L3/ "{\"skus\":[{\"id\":$SK3,\"price\":\"60.00\"}]}")
check "price below stored discount -> 400" 400 "$(code "$R")"
R=$(post PATCH /catalog/listings/$L3/ '{"price_tiers":[{"min_qty":1,"price":"50.00","discounted_price":null}]}')
check "tier null discount -> tier price" "50.00" "$(body "$R" | jget "['price_tiers'][0]['discounted_price']")"

echo "=== Brand delete ==="
R=$(post DELETE /catalog/brands/$B1/)
check "delete brand in use -> 409" 409 "$(code "$R")"
curl -s -o /dev/null -X DELETE "$BASE/catalog/listings/$L1/" -H "$AUTH"
R=$(post DELETE /catalog/brands/$B1/)
check "delete brand still referenced by soft-deleted listing -> 409" 409 "$(code "$R")"

echo "=== Cleanup ==="
echo "(listings hard-deleted via shell, then brands deleted via API)"
echo "IDS $B1 $B2 $L1 $L2"
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
