#!/usr/bin/env bash
# Public (no login) geography lists used by the seller sign-up form.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
BASE="$SMOKE_BASE/api/v1"
P="$BASE/public/geography"
PASS=0; FAIL=0
check() { if [ "$2" == "$3" ]; then echo "OK   $1 (got $3)"; PASS=$((PASS+1)); else echo "FAIL $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi; }
jget() { python -c "import sys,json;d=json.load(sys.stdin);print(d$1)" 2>/dev/null; }
get() { curl -s -w '\n%{http_code}' "$@"; }
code() { echo "$1" | tail -1; }
body() { echo "$1" | sed '$d'; }
cnt() { python -c "import sys,json;print(json.load(sys.stdin)['count'])" 2>/dev/null; }
keys() { python -c "import sys,json;print(','.join(sorted(json.load(sys.stdin)['results'][0].keys())))" 2>/dev/null; }

TOKEN=$(curl -s -X POST "$BASE/auth/admin/login/" -H "Content-Type: application/json" -d '{"email":"test.admin@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
AUTH="Authorization: Bearer $TOKEN"
# A thana to test with (the dev data has none). Removed again at the end.
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/geography/thanas/" -H "$AUTH" -H "Content-Type: application/json" -d '{"name":"Smoke Thana","country":126,"state":13,"city":8}')
check "admin creates a test thana" 201 "$(code "$R")"; TH=$(body "$R" | jget "['id']")

echo "=== No login needed ==="
for r in countries states cities thanas; do
  check "$r without a token -> 200" 200 "$(code "$(get "$P/$r/")")"
done
check "a stale/bad token does not break a public read" 200 "$(code "$(get "$P/countries/" -H "Authorization: Bearer not-a-token")")"
check "a valid admin token also works" 200 "$(code "$(get "$P/countries/" -H "Authorization: Bearer $TOKEN")")"

echo "=== Shape: only what a dropdown needs ==="
check "country keys" "country_code,flag_url,id,name,slug" "$(body "$(get "$P/countries/")" | keys)"
check "state keys" "country,id,name,slug" "$(body "$(get "$P/states/")" | keys)"
check "city keys" "country,id,name,slug,state" "$(body "$(get "$P/cities/")" | keys)"
check "thana keys" "city,country,id,name,slug,state" "$(body "$(get "$P/thanas/?city=8")" | keys)"
check "no audit data leaks (creator_name)" "None" "$(body "$(get "$P/countries/")" | jget "['results'][0].get('creator_name')")"
check "parents are plain ids" "126" "$(body "$(get "$P/states/")" | jget "['results'][0]['country']")"
check "list is wrapped with count" True "$(body "$(get "$P/countries/")" | python -c "import sys,json;d=json.load(sys.stdin);print(set(d)=={'count','next','previous','results'})")"
check "sorted by name" "Bangladesh,India,Pakistan" "$(body "$(get "$P/countries/")" | python -c "import sys,json;print(','.join(r['name'] for r in json.load(sys.stdin)['results']))")"

echo "=== Filtering by parent (the cascading dropdowns) ==="
check "states of country 126" 2 "$(body "$(get "$P/states/?country=126")" | cnt)"
check "states of country 127 (none seeded)" 0 "$(body "$(get "$P/states/?country=127")" | cnt)"
check "cities of state 13" 2 "$(body "$(get "$P/cities/?state=13")" | cnt)"
check "cities of state 12" 0 "$(body "$(get "$P/cities/?state=12")" | cnt)"
check "cities of country 126" 2 "$(body "$(get "$P/cities/?country=126")" | cnt)"
check "thanas of city 8 include the test thana" "Smoke Thana" "$(body "$(get "$P/thanas/?city=8&search=smoke")" | jget "['results'][0]['name']")"
check "thanas of city 9 are empty" 0 "$(body "$(get "$P/thanas/?city=9&search=smoke")" | cnt)"
check "thanas by state" 1 "$(body "$(get "$P/thanas/?state=13&search=smoke")" | cnt)"
check "search by name" 1 "$(body "$(get "$P/states/?search=chitt")" | cnt)"
check "search with no match" 0 "$(body "$(get "$P/states/?search=zzzz")" | cnt)"
check "non-numeric parent id -> 400" 400 "$(code "$(get "$P/states/?country=abc")")"
check "limit=1 paginates" 1 "$(body "$(get "$P/countries/?limit=1")" | python -c "import sys,json;print(len(json.load(sys.stdin)['results']))")"
check "limit is capped, not an error" 200 "$(code "$(get "$P/countries/?limit=100000")")"

echo "=== Read-only ==="
for r in countries states cities thanas; do
  check "POST $r -> 405" 405 "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$P/$r/" -H "Content-Type: application/json" -d '{"name":"Smoke X"}')"
  check "no detail route for $r -> 404" 404 "$(curl -s -o /dev/null -w '%{http_code}' "$P/$r/126/")"
done
check "PATCH -> 404" 404 "$(curl -s -o /dev/null -w '%{http_code}' -X PATCH "$P/countries/126/" -H "Content-Type: application/json" -d '{"name":"x"}')"
check "DELETE -> 404" 404 "$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$P/countries/126/")"
check "country 126 untouched" Bangladesh "$(body "$(get "$P/countries/?search=bangla")" | jget "['results'][0]['name']")"

echo "=== The admin geography API is still admin-only ==="
check "admin list without a token -> 401" 401 "$(code "$(get "$BASE/geography/countries/")")"
check "admin list shows audit fields to an admin" True "$(body "$(get "$BASE/geography/countries/" -H "$AUTH")" | python -c "import sys,json;print('creator_name' in json.load(sys.stdin)['results'][0])")"

echo "=== The sign-up form can use these ids ==="
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/auth/seller/register/" --form-string "name=Smoke Geo Seller" --form-string "email=smoke.geo@example.com" --form-string "phone=+8801700092001" --form-string "password=Sell@12345" --form-string "present_address=House 1" --form-string "permanent_address=Village" -F country=126 -F state=13 -F city=8 -F "thana=$TH" -F media_for=nid -F "media_file=@$SCRATCH/t.png;type=image/png")
check "register with a country/state/city/thana picked from the public lists" 201 "$(code "$R")"
check "thana saved" "$TH" "$(body "$R" | jget "['thana']")"

echo "=== Cleanup ==="
SID=$(body "$R" | jget "['id']")
curl -s -o /dev/null -X DELETE "$BASE/accounts/sellers/$SID/" -H "$AUTH"
check "delete the test thana" 204 "$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$BASE/geography/thanas/$TH/" -H "$AUTH")"
check "no test thana left" 0 "$(body "$(get "$P/thanas/?search=smoke")" | cnt)"

echo
echo "RESULT: $PASS passed, $FAIL failed"
