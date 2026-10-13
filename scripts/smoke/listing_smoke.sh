#!/usr/bin/env bash
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
BASE="$SMOKE_BASE/api/v1"
PASS=0
FAIL=0

check() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" == "$actual" ]; then
    echo "OK   $desc (got $actual)"
    PASS=$((PASS+1))
  else
    echo "FAIL $desc (expected $expected, got $actual)"
    FAIL=$((FAIL+1))
  fi
}

jget() { python -c "import sys,json;d=json.load(sys.stdin);print(d$1)" 2>/dev/null; }

echo "=== Admin login ==="
TOKEN=$(curl -s -X POST "$BASE/auth/admin/login/" -H "Content-Type: application/json" \
  -d '{"email":"test.admin@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
[ -n "$TOKEN" ] && echo "OK   admin login (token acquired)" && PASS=$((PASS+1)) || { echo "FAIL admin login"; FAIL=$((FAIL+1)); }
AUTH="Authorization: Bearer $TOKEN"

echo
echo "=== 0) Regression: Category / Measurement still work ==="
R=$(curl -s -w '\n%{http_code}' "$BASE/catalog/categories/?type=product&limit=1" -H "$AUTH")
check "category list" 200 "$(echo "$R" | tail -1)"

R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/categories/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"type":"product","name":"Smoke Regression Category"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "create regression category" 201 "$CODE"
REG_CAT_ID=$(echo "$BODY" | jget "['id']")

R=$(curl -s -w '\n%{http_code}' "$BASE/catalog/measurements/?limit=1" -H "$AUTH")
check "measurement list" 200 "$(echo "$R" | tail -1)"

R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/measurements/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Smoke Regression Unit","symbol":"sru"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "create regression measurement" 201 "$CODE"
REG_MEAS_ID=$(echo "$BODY" | jget "['id']")

curl -s -o /dev/null -X DELETE "$BASE/catalog/categories/$REG_CAT_ID/" -H "$AUTH"
curl -s -o /dev/null -X DELETE "$BASE/catalog/measurements/$REG_MEAS_ID/" -H "$AUTH"
echo "(regression category/measurement cleaned up)"

echo
echo "=== Setup: smoke Seller + Buyer to attach listings to ==="
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/accounts/sellers/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Listing Smoke Seller","email":"listing.smoke.seller@example.com","phone":"+8801700020001","password":"Sell@12345"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "create smoke seller" 201 "$CODE"
SELLER_ID=$(echo "$BODY" | jget "['id']")

R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/accounts/buyers/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Listing Smoke Buyer","email":"listing.smoke.buyer@example.com","phone":"+8801700020002","password":"Buy@12345"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "create smoke buyer" 201 "$CODE"
BUYER_ID=$(echo "$BODY" | jget "['id']")

# reference data (looked up beforehand): product category 18, service category 29, measurement 13
# country 126, state 13, city 8

echo
echo "=== 1) Create Listing A (product, seller_offer, minimal) -> expect approved, note null ==="
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"seller\":$SELLER_ID,\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"general\",\"posted_by_role\":\"seller_offer\",\"title\":\"Smoke Listing A\",\"description\":\"desc\",\"price\":\"100.00\"}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "create listing A status code" 201 "$CODE"
LISTING_A=$(echo "$BODY" | jget "['id']")
check "listing A default status" "approved" "$(echo "$BODY" | jget "['status']")"
check "listing A note null" "None" "$(echo "$BODY" | jget "['note']")"
LOGCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['status_change_logs']))")
check "listing A status_change_logs count" "1" "$LOGCOUNT"
LOGCREATOR=$(echo "$BODY" | python -c "import sys,json;print(json.load(sys.stdin)['status_change_logs'][0]['creator_type'])")
check "listing A log creator_type" "admin" "$LOGCREATOR"

echo
echo "=== 2) Create Listing B with explicit status=pending (override honored) ==="
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"seller\":$SELLER_ID,\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"general\",\"posted_by_role\":\"seller_offer\",\"title\":\"Smoke Listing B\",\"description\":\"desc\",\"price\":\"50.00\",\"status\":\"pending\"}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "create listing B status code" 201 "$CODE"
LISTING_B=$(echo "$BODY" | jget "['id']")
check "listing B explicit pending honored" "pending" "$(echo "$BODY" | jget "['status']")"

echo
echo "=== 3) Create Listing C (service, buyer_request) ==="
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"buyer\":$BUYER_ID,\"category\":29,\"catalog_type\":\"service\",\"posted_by_role\":\"buyer_request\",\"title\":\"Smoke Listing C\",\"description\":\"need cleaning\",\"price\":\"30.00\",\"price_type\":\"hourly\"}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "create listing C (service/buyer_request) status code" 201 "$CODE"
LISTING_C=$(echo "$BODY" | jget "['id']")

echo
echo "=== 4) Seller/buyer exclusivity validation ==="
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"seller\":$SELLER_ID,\"buyer\":$BUYER_ID,\"category\":18,\"catalog_type\":\"product\",\"posted_by_role\":\"seller_offer\",\"title\":\"Bad Listing\",\"description\":\"desc\",\"price\":\"10.00\"}")
check "seller_offer with both seller+buyer -> 400" 400 "$(echo "$R" | tail -1)"

R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"category\":18,\"catalog_type\":\"product\",\"posted_by_role\":\"seller_offer\",\"title\":\"Bad Listing 2\",\"description\":\"desc\",\"price\":\"10.00\"}")
check "seller_offer with no seller (Admin-owned) -> 201" 201 "$(echo "$R" | tail -1)"

echo
echo "=== 5) Retrieve Listing A ==="
R=$(curl -s -w '\n%{http_code}' "$BASE/catalog/listings/$LISTING_A/" -H "$AUTH")
check "retrieve listing A" 200 "$(echo "$R" | tail -1)"

echo
echo "=== 6) List / filter / search ==="
R=$(curl -s -w '\n%{http_code}' "$BASE/catalog/listings/?status=approved&catalog_type=product" -H "$AUTH")
check "list filter status+catalog_type" 200 "$(echo "$R" | tail -1)"
R=$(curl -s -w '\n%{http_code}' "$BASE/catalog/listings/?search=Smoke%20Listing%20A" -H "$AUTH")
check "list search title" 200 "$(echo "$R" | tail -1)"

echo
echo "=== 7) Update Listing A unrelated field only -> status/note untouched, no new log ==="
R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_A/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"description":"updated description"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "update A unrelated field status" 200 "$CODE"
check "update A status still approved" "approved" "$(echo "$BODY" | jget "['status']")"
LOGCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['status_change_logs']))")
check "update A unrelated field log count still 1" "1" "$LOGCOUNT"

echo
echo "=== 8) Reject Listing A without note -> 400 ==="
R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_A/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"status":"rejected"}')
check "reject without note -> 400" 400 "$(echo "$R" | tail -1)"

echo
echo "=== 9) Reject Listing A with note -> 200, note stored, log count 2 ==="
R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_A/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"status":"rejected","note":"Photos are low quality"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "reject with note status code" 200 "$CODE"
check "reject with note stored" "Photos are low quality" "$(echo "$BODY" | jget "['note']")"
LOGCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['status_change_logs']))")
check "reject log count 2" "2" "$LOGCOUNT"

echo
echo "=== 10) Request changes with note -> 200, log count 3 ==="
R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_A/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"status":"changes_requested","note":"Please add more photos"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "changes_requested status code" 200 "$CODE"
LOGCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['status_change_logs']))")
check "changes_requested log count 3" "3" "$LOGCOUNT"

echo
echo "=== 11) Re-approve with no note -> note clears to null, log count 4 ==="
R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_A/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"status":"approved"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "re-approve status code" 200 "$CODE"
check "re-approve note cleared to null" "None" "$(echo "$BODY" | jget "['note']")"
LOGCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['status_change_logs']))")
check "re-approve log count 4" "4" "$LOGCOUNT"

echo
echo "=== 12) price_tiers: create wholesale Listing D with 2 tiers ==="
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"seller\":$SELLER_ID,\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"wholesale\",\"posted_by_role\":\"seller_offer\",\"title\":\"Smoke Listing D\",\"description\":\"desc\",\"price\":\"20.00\",\"measurement\":13,\"price_tiers\":[{\"min_qty\":1,\"max_qty\":9,\"price\":\"20.00\"},{\"min_qty\":10,\"max_qty\":null,\"price\":\"18.00\"}]}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "create listing D status code" 201 "$CODE"
LISTING_D=$(echo "$BODY" | jget "['id']")
TIERCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['price_tiers']))")
check "listing D initial tier count" "2" "$TIERCOUNT"

R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_D/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"price_tiers":[{"min_qty":1,"max_qty":null,"price":"19.00"}]}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "replace tiers status code" 200 "$CODE"
TIERCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['price_tiers']))")
check "listing D replaced tier count" "1" "$TIERCOUNT"

R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_D/" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"description":"desc updated"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "unrelated update on D status code" 200 "$CODE"
TIERCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['price_tiers']))")
check "listing D tiers untouched on unrelated update" "1" "$TIERCOUNT"

echo
echo "=== 13) Media upload (multipart) + delete ==="
printf '\xff\xd8\xff\xe0test-jpeg-bytes' > "$SCRATCH/smoke_listing.jpg"
echo "test document content" > "$SCRATCH/smoke_listing.txt"
R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_A/" -H "$AUTH" \
  -F "media_file=@$SCRATCH/smoke_listing.jpg;type=image/jpeg" \
  -F "media_file=@$SCRATCH/smoke_listing.txt;type=text/plain")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "media upload status code" 200 "$CODE"
MEDIACOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['media']))")
check "media count after upload" "2" "$MEDIACOUNT"
IMGTYPE=$(echo "$BODY" | python -c "import sys,json;d=json.load(sys.stdin)['media'];print([m['media_type'] for m in d if m['media_path'].endswith('.jpg')][0])")
check "jpg inferred as image" "image" "$IMGTYPE"
DOCTYPE=$(echo "$BODY" | python -c "import sys,json;d=json.load(sys.stdin)['media'];print([m['media_type'] for m in d if m['media_path'].endswith('.txt')][0])")
check "txt inferred as document" "document" "$DOCTYPE"

MEDIA_IDS=$(echo "$BODY" | python -c "import sys,json;print(','.join(str(m['id']) for m in json.load(sys.stdin)['media']))")
R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/catalog/listings/$LISTING_A/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"media_delete_ids\":[$MEDIA_IDS]}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "media delete status code" 200 "$CODE"
MEDIACOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['media']))")
check "media count after delete" "0" "$MEDIACOUNT"

echo
echo "=== 14) Soft delete Listing B ==="
R=$(curl -s -w '\n%{http_code}' -X DELETE "$BASE/catalog/listings/$LISTING_B/" -H "$AUTH")
check "soft delete status code" 204 "$(echo "$R" | tail -1)"

R=$(curl -s -w '\n%{http_code}' "$BASE/catalog/listings/$LISTING_B/" -H "$AUTH")
check "retrieve soft-deleted listing -> 404" 404 "$(echo "$R" | tail -1)"

R=$(curl -s "$BASE/catalog/listings/?search=Smoke%20Listing%20B" -H "$AUTH")
STILLTHERE=$(echo "$R" | python -c "import sys,json;print(len(json.load(sys.stdin)['results']))")
check "soft-deleted listing absent from list" "0" "$STILLTHERE"

echo
echo "=== 15) Bulk moderate: create E, F then bulk actions ==="
R=$(curl -s -X POST "$BASE/catalog/listings/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"seller\":$SELLER_ID,\"category\":18,\"catalog_type\":\"product\",\"posted_by_role\":\"seller_offer\",\"title\":\"Smoke Listing E\",\"description\":\"desc\",\"price\":\"5.00\"}")
LISTING_E=$(echo "$R" | jget "['id']")
R=$(curl -s -X POST "$BASE/catalog/listings/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"seller\":$SELLER_ID,\"category\":18,\"catalog_type\":\"product\",\"posted_by_role\":\"seller_offer\",\"title\":\"Smoke Listing F\",\"description\":\"desc\",\"price\":\"6.00\"}")
LISTING_F=$(echo "$R" | jget "['id']")

R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/bulk-moderate/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"listing_ids\":[$LISTING_E,$LISTING_F],\"status\":\"rejected\"}")
check "bulk reject without note -> 400" 400 "$(echo "$R" | tail -1)"

R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/bulk-moderate/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"listing_ids\":[$LISTING_E,$LISTING_F],\"status\":\"approved\"}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "bulk approve (both already approved) status code" 200 "$CODE"
SKIPCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['skipped']))")
check "bulk approve both skipped (already approved)" "2" "$SKIPCOUNT"

R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/catalog/listings/bulk-moderate/" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"listing_ids\":[$LISTING_E,$LISTING_F],\"status\":\"rejected\",\"note\":\"Bulk rejected in smoke test\"}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | sed '$d')
check "bulk reject with note status code" 200 "$CODE"
UPDCOUNT=$(echo "$BODY" | python -c "import sys,json;print(len(json.load(sys.stdin)['updated']))")
check "bulk reject with note updated count" "2" "$UPDCOUNT"

R=$(curl -s "$BASE/catalog/listings/$LISTING_E/" -H "$AUTH")
check "listing E status after bulk reject" "rejected" "$(echo "$R" | jget "['status']")"
LOGCOUNT=$(echo "$R" | python -c "import sys,json;print(len(json.load(sys.stdin)['status_change_logs']))")
check "listing E log count after bulk reject" "2" "$LOGCOUNT"

echo
echo "=== Cleanup ==="
for LID in "$LISTING_A" "$LISTING_C" "$LISTING_D" "$LISTING_E" "$LISTING_F"; do
  curl -s -o /dev/null -X DELETE "$BASE/catalog/listings/$LID/" -H "$AUTH"
done
curl -s -o /dev/null -X DELETE "$BASE/accounts/sellers/$SELLER_ID/" -H "$AUTH"
curl -s -o /dev/null -X DELETE "$BASE/accounts/buyers/$BUYER_ID/" -H "$AUTH"
rm -f "$SCRATCH/smoke_listing.jpg" "$SCRATCH/smoke_listing.txt"
echo "(all smoke listings/seller/buyer soft/hard-cleaned as applicable)"

echo
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
