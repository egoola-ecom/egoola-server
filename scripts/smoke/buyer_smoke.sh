#!/usr/bin/env bash
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
BASE="$SMOKE_BASE/api/v1"
PASS=0; FAIL=0
check() { if [ "$2" == "$3" ]; then echo "OK   $1 (got $3)"; PASS=$((PASS+1)); else echo "FAIL $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi; }
jget() { python -c "import sys,json;d=json.load(sys.stdin);print(d$1)" 2>/dev/null; }
req() { curl -s -w '\n%{http_code}' -X "$1" "$BASE$2" -H "$AUTH" -H "Content-Type: application/json" ${3:+-d "$3"}; }
code() { echo "$1" | tail -1; }
body() { echo "$1" | sed '$d'; }
cnt() { python -c "import sys,json;print(json.load(sys.stdin)['count'])" 2>/dev/null; }
S="search=Smoke%20Buyer"

TOKEN=$(curl -s -X POST "$BASE/auth/admin/login/" -H "Content-Type: application/json" -d '{"email":"test.admin@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
AUTH="Authorization: Bearer $TOKEN"
[ -n "$TOKEN" ] && echo "OK   admin login" && PASS=$((PASS+1))

echo "=== Create ==="
R=$(req POST /accounts/buyers/ '{"name":"Smoke Buyer One","email":"smoke.buyer.one@example.com","phone":"+8801700088001","password":"Buy@12345"}')
check "create minimal" 201 "$(code "$R")"; B1=$(body "$R" | jget "['id']")
check "status defaults active" active "$(body "$R" | jget "['status']")"
check "password not returned" "None" "$(body "$R" | jget ".get('password')")"
R=$(req POST /accounts/buyers/ '{"name":"Smoke Buyer Two","email":"smoke.buyer.two@example.com","phone":"+8801700088002","password":"Buy@12345","country":126,"state":13,"city":8,"address_line":"Road 1, Dhaka","skills":["design"],"description":"Second buyer","status":"suspended"}')
check "create with address + status" 201 "$(code "$R")"; B2=$(body "$R" | jget "['id']")
check "address stored" "Road 1, Dhaka" "$(body "$R" | jget "['address_line']")"
check "suspended honored" suspended "$(body "$R" | jget "['status']")"
check "no password -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"X","email":"x.nopw@example.com","phone":"+8801700088003"}')")"
check "duplicate email -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"X","email":"smoke.buyer.one@example.com","phone":"+8801700088004","password":"Buy@12345"}')")"
check "duplicate phone -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"X","email":"x.dup@example.com","phone":"+8801700088001","password":"Buy@12345"}')")"
check "missing name -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"email":"x.nn@example.com","phone":"+8801700088005","password":"Buy@12345"}')")"
check "bad status -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"X","email":"x.bs@example.com","phone":"+8801700088006","password":"Buy@12345","status":"banned"}')")"

echo "=== Retrieve ==="
R=$(req GET /accounts/buyers/$B2/)
check "retrieve" 200 "$(code "$R")"
check "retrieve has media list" "[]" "$(body "$R" | jget "['media']")"
check "unknown id -> 404" 404 "$(code "$(req GET /accounts/buyers/99999999/)")"

echo "=== Update ==="
R=$(req PATCH /accounts/buyers/$B1/ '{"name":"Smoke Buyer 1 Renamed"}')
check "patch name" 200 "$(code "$R")"
check "name changed" "Smoke Buyer 1 Renamed" "$(body "$R" | jget "['name']")"
check "patch status suspended" suspended "$(body "$(req PATCH /accounts/buyers/$B1/ '{"status":"suspended"}')" | jget "['status']")"
check "patch status back active" active "$(body "$(req PATCH /accounts/buyers/$B1/ '{"status":"active"}')" | jget "['status']")"
check "patch email to existing -> 400" 400 "$(code "$(req PATCH /accounts/buyers/$B1/ '{"email":"smoke.buyer.two@example.com"}')")"
check "patch password" 200 "$(code "$(req PATCH /accounts/buyers/$B1/ '{"password":"New@12345"}')")"
check "login with new password" 200 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"smoke.buyer.one@example.com","password":"New@12345"}')"
check "login with old password -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"smoke.buyer.one@example.com","password":"Buy@12345"}')"
check "PUT without password allowed" 200 "$(code "$(req PUT /accounts/buyers/$B1/ '{"name":"Smoke Buyer 1 Put","email":"smoke.buyer.one@example.com","phone":"+8801700088001"}')")"
check "wallet_balance read-only" "0.00" "$(body "$(req PATCH /accounts/buyers/$B1/ '{"wallet_balance":"999.00"}')" | jget "['wallet_balance']")"

echo "=== Media / profile pic ==="
cp "$SCRATCH/t.png" "$SCRATCH/smoke_buyer.png"
R=$(curl -s -w '\n%{http_code}' -X PATCH "$BASE/accounts/buyers/$B1/" -H "$AUTH" -F "profile_pic=@$SCRATCH/smoke_buyer.png;type=image/png")
check "profile_pic upload" 200 "$(code "$R")"
check "profile_pic_url set" "True" "$(body "$R" | python -c "import sys,json;print(bool(json.load(sys.stdin)['profile_pic_url']))")"

echo "=== List / filters ==="
check "search both" 2 "$(body "$(req GET "/accounts/buyers/?$S")" | cnt)"
check "filter status=suspended" 1 "$(body "$(req GET "/accounts/buyers/?$S&status=suspended")" | cnt)"
check "filter city=8" 1 "$(body "$(req GET "/accounts/buyers/?$S&city=8")" | cnt)"
check "filter country=126" 1 "$(body "$(req GET "/accounts/buyers/?$S&country=126")" | cnt)"
check "filter state=13&city=8" 1 "$(body "$(req GET "/accounts/buyers/?$S&state=13&city=8")" | cnt)"
check "filter email_verified=true (none)" 0 "$(body "$(req GET "/accounts/buyers/?$S&email_verified=true")" | cnt)"
check "filter email_verified=false" 2 "$(body "$(req GET "/accounts/buyers/?$S&email_verified=false")" | cnt)"
check "filter phone_verified=false" 2 "$(body "$(req GET "/accounts/buyers/?$S&phone_verified=false")" | cnt)"
TODAY=$(date +%F)
check "created_from today" 2 "$(body "$(req GET "/accounts/buyers/?$S&created_from=$TODAY")" | cnt)"
check "created_from far future" 0 "$(body "$(req GET "/accounts/buyers/?$S&created_from=2999-01-01")" | cnt)"
check "created_to far past" 0 "$(body "$(req GET "/accounts/buyers/?$S&created_to=2000-01-01")" | cnt)"
check "created_from+created_to today" 2 "$(body "$(req GET "/accounts/buyers/?$S&created_from=$TODAY&created_to=$TODAY")" | cnt)"
check "search by phone" 1 "$(body "$(req GET "/accounts/buyers/?search=%2B8801700088002")" | cnt)"
check "list row has no media" "None" "$(body "$(req GET "/accounts/buyers/?$S")" | jget "['results'][0].get('media')")"
check "limit=1 paginates" 1 "$(body "$(req GET "/accounts/buyers/?$S&limit=1")" | python -c "import sys,json;print(len(json.load(sys.stdin)['results']))")"

echo "=== Permissions ==="
check "no token -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/buyers/)"
BT=$(curl -s -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"smoke.buyer.two@example.com","password":"Buy@12345"}' | python -c "import sys,json;print(json.load(sys.stdin).get('access',''))")
check "suspended buyer cannot log in" "" "$BT"
BT=$(curl -s -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"smoke.buyer.one@example.com","password":"New@12345"}' | python -c "import sys,json;print(json.load(sys.stdin).get('access',''))")
check "buyer token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/buyers/ -H "Authorization: Bearer $BT")"

echo "=== Audit stamping (DB) ==="
cd "$SERVER_DIR"
uv run manage.py shell -c "
from apps.accounts.models import User
a=User.objects.get(id=$B1); b=User.objects.get(id=$B2)
print('AUDIT', a.creator_type, a.creator_name, a.created_by is not None, a.updater_type, a.updater_name, a.updated_by is not None, b.creator_type, b.updater_type)" 2>&1 | grep AUDIT
echo "=== Delete ==="
check "delete 1" 204 "$(code "$(req DELETE /accounts/buyers/$B1/)")"
check "delete 2" 204 "$(code "$(req DELETE /accounts/buyers/$B2/)")"
check "deleted -> 404" 404 "$(code "$(req GET /accounts/buyers/$B1/)")"
check "delete again -> 404" 404 "$(code "$(req DELETE /accounts/buyers/$B1/)")"
rm -f "$SCRATCH/smoke_buyer.png"
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
