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
login() { curl -s -X POST "$BASE/auth/admin/login/" -H "Content-Type: application/json" -d "{\"email\":\"$1\",\"password\":\"$2\"}" | python -c "import sys,json;print(json.load(sys.stdin).get('access',''))"; }
S="search=Smoke%20Adm"

ensure_smoke_super
SUPER=$(login smoke.super@egoola.com 'Test@12345'); AUTH="Authorization: Bearer $SUPER"
[ -n "$SUPER" ] && echo "OK   super-admin login" && PASS=$((PASS+1))
PLAIN=$(login test.admin@egoola.com 'Test@12345')
check "plain admin logs in" "True" "$([ -n "$PLAIN" ] && echo True)"

echo "=== Access control ==="
check "no token -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/)"
check "plain admin list -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $PLAIN")"
check "plain admin create -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/accounts/admins/ -H "Authorization: Bearer $PLAIN" -H 'Content-Type: application/json' -d '{"name":"X","email":"x@e.com","mobile":"+8801700099900","password":"Adm@12345","type":"admin"}')"
check "plain admin retrieve -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/17/ -H "Authorization: Bearer $PLAIN")"
check "plain admin delete -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' -X DELETE $BASE/accounts/admins/17/ -H "Authorization: Bearer $PLAIN")"
check "plain admin still reaches sellers" 200 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/sellers/ -H "Authorization: Bearer $PLAIN")"
BT=$(curl -s -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"test.buyer@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin).get('access',''))")
if [ -n "$BT" ]; then check "buyer token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $BT")"; fi

echo "=== Create (as super-admin) ==="
R=$(req POST /accounts/admins/ '{"name":"Smoke Admin One","email":"smoke.admin.one@example.com","mobile":"+8801700099201","password":"Adm@12345","type":"admin"}')
check "create admin" 201 "$(code "$R")"; A1=$(body "$R" | jget "['id']")
check "type admin" admin "$(body "$R" | jget "['type']")"
check "status defaults active" active "$(body "$R" | jget "['status']")"
check "password not returned" None "$(body "$R" | jget ".get('password')")"
R=$(req POST /accounts/admins/ '{"name":"Smoke Admin Two","email":"smoke.admin.two@example.com","mobile":"+8801700099202","password":"Adm@12345","type":"super_admin","present_address":"Dhaka","country":126,"state":13,"city":8,"skills":["ops"]}')
check "create super_admin with details" 201 "$(code "$R")"; A2=$(body "$R" | jget "['id']")
check "address stored" Dhaka "$(body "$R" | jget "['present_address']")"
check "moderator type -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"X","email":"x.m@example.com","mobile":"+8801700099203","password":"Adm@12345","type":"moderator"}')")"
check "support type -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"X","email":"x.s@example.com","mobile":"+8801700099204","password":"Adm@12345","type":"support"}')")"
check "missing type -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"X","email":"x.t@example.com","mobile":"+8801700099205","password":"Adm@12345"}')")"
check "missing password -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"X","email":"x.p@example.com","mobile":"+8801700099206","type":"admin"}')")"
check "duplicate email -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"X","email":"smoke.admin.one@example.com","mobile":"+8801700099207","password":"Adm@12345","type":"admin"}')")"
check "duplicate mobile -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"X","email":"x.d@example.com","mobile":"+8801700099201","password":"Adm@12345","type":"admin"}')")"

echo "=== New admins can log in; role gate applies to them ==="
N1=$(login smoke.admin.one@example.com 'Adm@12345'); check "new admin logs in" True "$([ -n "$N1" ] && echo True)"
check "new plain admin -> admins 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $N1")"
N2=$(login smoke.admin.two@example.com 'Adm@12345')
check "new super_admin -> admins 200" 200 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $N2")"

echo "=== Retrieve ==="
check "retrieve" 200 "$(code "$(req GET /accounts/admins/$A1/)")"
check "unknown id -> 404" 404 "$(code "$(req GET /accounts/admins/99999999/)")"

echo "=== Update ==="
check "rename" "Smoke Admin 1 Renamed" "$(body "$(req PATCH /accounts/admins/$A1/ '{"name":"Smoke Admin 1 Renamed"}')" | jget "['name']")"
check "promote to super_admin" super_admin "$(body "$(req PATCH /accounts/admins/$A1/ '{"type":"super_admin"}')" | jget "['type']")"
check "promoted admin now reaches admins" 200 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $N1")"
check "demote back to admin" admin "$(body "$(req PATCH /accounts/admins/$A1/ '{"type":"admin"}')" | jget "['type']")"
check "demotion takes effect immediately (same token) -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $N1")"
check "deactivate other admin" inactive "$(body "$(req PATCH /accounts/admins/$A1/ '{"status":"inactive"}')" | jget "['status']")"
check "inactive admin cannot log in" "" "$(login smoke.admin.one@example.com 'Adm@12345')"
check "reactivate" active "$(body "$(req PATCH /accounts/admins/$A1/ '{"status":"active"}')" | jget "['status']")"
check "bad type on update -> 400" 400 "$(code "$(req PATCH /accounts/admins/$A1/ '{"type":"moderator"}')")"
check "change password" 200 "$(code "$(req PATCH /accounts/admins/$A1/ '{"password":"New@12345"}')")"
check "login with new password" True "$([ -n "$(login smoke.admin.one@example.com 'New@12345')" ] && echo True)"

echo "=== Self-protection ==="
ME=$(cd "$SERVER_DIR" && uv run manage.py shell -c "from apps.accounts.models import Admin;print(Admin.objects.get(email='smoke.super@egoola.com').id)" 2>&1 | tail -1)
check "cannot demote self" 400 "$(code "$(req PATCH /accounts/admins/$ME/ '{"type":"admin"}')")"
check "cannot deactivate self" 400 "$(code "$(req PATCH /accounts/admins/$ME/ '{"status":"inactive"}')")"
check "cannot delete self" 400 "$(code "$(req DELETE /accounts/admins/$ME/)")"
check "can edit own name" 200 "$(code "$(req PATCH /accounts/admins/$ME/ '{"name":"Smoke Super"}')")"
check "PUT own record unchanged type/status ok" 200 "$(code "$(req PUT /accounts/admins/$ME/ '{"name":"Smoke Super","email":"smoke.super@egoola.com","mobile":"+8801700099100","type":"super_admin","status":"active"}')")"
check "super can demote another super" admin "$(body "$(req PATCH /accounts/admins/$A2/ '{"type":"admin"}')" | jget "['type']")"

echo "=== List / filters ==="
check "search" 2 "$(body "$(req GET "/accounts/admins/?$S")" | cnt)"
check "filter type=admin" 2 "$(body "$(req GET "/accounts/admins/?$S&type=admin")" | cnt)"
check "filter type=super_admin" 0 "$(body "$(req GET "/accounts/admins/?$S&type=super_admin")" | cnt)"
check "filter status=inactive" 0 "$(body "$(req GET "/accounts/admins/?$S&status=inactive")" | cnt)"
check "search by mobile" 1 "$(body "$(req GET "/accounts/admins/?search=%2B8801700099202")" | cnt)"
check "list row has no media" None "$(body "$(req GET "/accounts/admins/?$S")" | jget "['results'][0].get('media')")"

echo "=== Audit stamping (DB) ==="
cd "$SERVER_DIR"
uv run manage.py shell -c "
from apps.accounts.models import Admin
a=Admin.objects.get(id=$A1); print('AUDIT', a.creator_type, a.creator_name, a.created_by, a.updater_type, a.updater_name, a.updated_by)" 2>&1 | grep AUDIT

echo "=== Delete ==="
check "delete other admin" 204 "$(code "$(req DELETE /accounts/admins/$A1/)")"
check "delete second" 204 "$(code "$(req DELETE /accounts/admins/$A2/)")"
check "deleted -> 404" 404 "$(code "$(req GET /accounts/admins/$A1/)")"
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
