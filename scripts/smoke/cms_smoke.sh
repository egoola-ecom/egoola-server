#!/usr/bin/env bash
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
BASE="$SMOKE_BASE/api/v1/cms"
API="$SMOKE_BASE/api/v1"
PASS=0; FAIL=0
check() { if [ "$2" == "$3" ]; then echo "OK   $1 (got $3)"; PASS=$((PASS+1)); else echo "FAIL $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi; }
jget() { python -c "import sys,json;d=json.load(sys.stdin);print(d$1)" 2>/dev/null; }
req() { curl -s -w '\n%{http_code}' -X "$1" "$BASE$2" -H "$AUTH" -H "Content-Type: application/json" ${3:+-d "$3"}; }
code() { echo "$1" | tail -1; }
body() { echo "$1" | sed '$d'; }
cnt() { python -c "import sys,json;print(json.load(sys.stdin)['count'])" 2>/dev/null; }
mp() { curl -s -w '\n%{http_code}' -X "$1" "$BASE$2" -H "$AUTH" "${@:3}"; }
IMG="$SCRATCH/cms_img.png"
python -c "import base64,sys;open(sys.argv[1],'wb').write(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='))" "$IMG"
echo "not an image" > "$SCRATCH/cms_notimg.txt"

TOKEN=$(curl -s -X POST "$API/auth/admin/login/" -H "Content-Type: application/json" -d '{"email":"test.admin@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
AUTH="Authorization: Bearer $TOKEN"
[ -n "$TOKEN" ] && echo "OK   admin login" && PASS=$((PASS+1))

# The logo checks need an empty logo. If the dev site already has one, keep a
# copy, remove it for the run, and put it back when the script exits.
ORIG_LOGO_URL=$(curl -s "$BASE/site-logo/" -H "$AUTH" | jget "['url']")
if [ -n "$ORIG_LOGO_URL" ] && [ "$ORIG_LOGO_URL" != "None" ]; then
  curl -s "$SMOKE_BASE$ORIG_LOGO_URL" -o "$SCRATCH/orig_logo.png"
  curl -s -o /dev/null -X DELETE "$BASE/site-logo/" -H "$AUTH"
fi
restore_logo() {
  if [ -s "$SCRATCH/orig_logo.png" ]; then
    curl -s -o /dev/null -X POST "$BASE/site-logo/" -H "$AUTH" -F "image=@$SCRATCH/orig_logo.png;type=image/png"
  fi
}
trap 'restore_logo; _smoke_exit' EXIT

echo "=== Access control ==="
for path in banners email-templates settings site-logo; do
  check "$path no token -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/$path/)"
done
BT=$(curl -s -X POST $API/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"test.buyer@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin).get('access',''))")
for path in banners email-templates settings site-logo; do
  check "$path buyer token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/$path/ -H "Authorization: Bearer $BT")"
done

echo "=== Banners ==="
R=$(mp POST /banners/ -F placement=hero -F "heading=Smoke Eid Sale" -F "small_heading=Up to 40% off" -F link_url=/categories/electronics -F sort_order=1 -F "image=@$IMG;type=image/png")
check "create hero banner" 201 "$(code "$R")"; BN1=$(body "$R" | jget "['id']")
check "status defaults active" active "$(body "$R" | jget "['status']")"
check "image_url set" True "$(body "$R" | python -c "import sys,json;print(bool(json.load(sys.stdin)['image_url']))")"
IMGPATH1=$(body "$R" | jget "['image_path']")
check "image file stored" True "$([ -f "$SERVER_DIR/media/$IMGPATH1" ] && echo True)"
check "no image -> 400" 400 "$(code "$(mp POST /banners/ -F placement=hero -F heading=NoImg)")"
check "non-image file -> 400" 400 "$(code "$(mp POST /banners/ -F placement=hero -F heading=Bad -F "image=@$SCRATCH/cms_notimg.txt;type=text/plain")")"
check "bad placement -> 400" 400 "$(code "$(mp POST /banners/ -F placement=footer -F heading=Bad -F "image=@$IMG;type=image/png")")"
check "missing placement -> 400" 400 "$(code "$(mp POST /banners/ -F heading=Bad -F "image=@$IMG;type=image/png")")"
check "category on hero -> 400" 400 "$(code "$(mp POST /banners/ -F placement=hero -F heading=Bad -F category=18 -F "image=@$IMG;type=image/png")")"
check "ends before starts -> 400" 400 "$(code "$(mp POST /banners/ -F placement=hero -F heading=Bad -F starts_at=2026-12-02T00:00:00Z -F ends_at=2026-12-01T00:00:00Z -F "image=@$IMG;type=image/png")")"
R=$(mp POST /banners/ -F placement=sidebar -F "heading=Smoke Sidebar" -F category=18 -F sort_order=2 -F status=inactive -F "image=@$IMG;type=image/png")
check "create sidebar banner with category" 201 "$(code "$R")"; BN2=$(body "$R" | jget "['id']")
check "category stored" 18 "$(body "$R" | jget "['category']")"
check "unknown category -> 400" 400 "$(code "$(mp POST /banners/ -F placement=sidebar -F heading=Bad -F category=99999999 -F "image=@$IMG;type=image/png")")"
R=$(mp POST /banners/ -F placement=category -F "heading=Smoke Scheduled" -F starts_at=2999-01-01T00:00:00Z -F ends_at=2999-02-01T00:00:00Z -F "image=@$IMG;type=image/png")
check "create future-scheduled banner" 201 "$(code "$R")"; BN3=$(body "$R" | jget "['id']")
check "retrieve" 200 "$(code "$(req GET /banners/$BN1/)")"
check "unknown id -> 404" 404 "$(code "$(req GET /banners/99999999/)")"
check "patch heading (JSON)" "Smoke Eid Sale 2" "$(body "$(req PATCH /banners/$BN1/ '{"heading":"Smoke Eid Sale 2"}')" | jget "['heading']")"
check "patch status inactive" inactive "$(body "$(req PATCH /banners/$BN1/ '{"status":"inactive"}')" | jget "['status']")"
check "patch status active" active "$(body "$(req PATCH /banners/$BN1/ '{"status":"active"}')" | jget "['status']")"
check "move sidebar banner to hero w/ category -> 400" 400 "$(code "$(req PATCH /banners/$BN2/ '{"placement":"hero"}')")"
check "move to hero and clear category" 200 "$(code "$(req PATCH /banners/$BN2/ '{"placement":"hero","category":null}')")"
check "ends_at before existing starts_at -> 400" 400 "$(code "$(req PATCH /banners/$BN3/ '{"ends_at":"2998-01-01T00:00:00Z"}')")"
R=$(mp PATCH /banners/$BN1/ -F "image=@$IMG;type=image/png")
check "replace image" 200 "$(code "$R")"
IMGPATH1B=$(body "$R" | jget "['image_path']")
check "new image path differs" True "$([ "$IMGPATH1" != "$IMGPATH1B" ] && echo True)"
check "old image file removed" True "$([ ! -f "$SERVER_DIR/media/$IMGPATH1" ] && echo True)"
check "list search" 3 "$(body "$(req GET "/banners/?search=Smoke")" | cnt)"
check "filter placement=hero" 2 "$(body "$(req GET "/banners/?search=Smoke&placement=hero")" | cnt)"
check "filter status=inactive" 1 "$(body "$(req GET "/banners/?search=Smoke&status=inactive")" | cnt)"
check "filter active_now=true" 1 "$(body "$(req GET "/banners/?search=Smoke&active_now=true")" | cnt)"
check "filter active_now=false" 2 "$(body "$(req GET "/banners/?search=Smoke&active_now=false")" | cnt)"
check "list ordered by placement then sort_order" "Smoke Scheduled" "$(body "$(req GET "/banners/?search=Smoke")" | jget "['results'][0]['heading']")"
check "delete banner" 204 "$(code "$(req DELETE /banners/$BN1/)")"
check "deleted banner image file removed" True "$([ ! -f "$SERVER_DIR/media/$IMGPATH1B" ] && echo True)"
check "delete again -> 404" 404 "$(code "$(req DELETE /banners/$BN1/)")"
req DELETE /banners/$BN2/ >/dev/null; req DELETE /banners/$BN3/ >/dev/null

echo "=== Email templates ==="
R=$(req POST /email-templates/ '{"key":"smoke_order_approved","subject":"Your Egoola order has been approved","content":"Hi {{buyerName}}, your order #{{orderId}} has been approved."}')
check "create template" 201 "$(code "$R")"; T1=$(body "$R" | jget "['id']")
check "is_active defaults true" True "$(body "$R" | jget "['is_active']")"
check "duplicate key -> 400" 400 "$(code "$(req POST /email-templates/ '{"key":"smoke_order_approved","subject":"x","content":"y"}')")"
check "bad key (uppercase) -> 400" 400 "$(code "$(req POST /email-templates/ '{"key":"Bad-Key","subject":"x","content":"y"}')")"
check "bad key (leading digit) -> 400" 400 "$(code "$(req POST /email-templates/ '{"key":"1abc","subject":"x","content":"y"}')")"
check "missing subject -> 400" 400 "$(code "$(req POST /email-templates/ '{"key":"smoke_x","content":"y"}')")"
check "missing content -> 400" 400 "$(code "$(req POST /email-templates/ '{"key":"smoke_x","subject":"y"}')")"
R=$(req POST /email-templates/ '{"key":"smoke_welcome","subject":"Smoke Welcome","content":"Hello {{name}}","is_active":false}')
check "create inactive template" 201 "$(code "$R")"; T2=$(body "$R" | jget "['id']")
check "retrieve" 200 "$(code "$(req GET /email-templates/$T1/)")"
check "patch subject+content" "Order approved!" "$(body "$(req PATCH /email-templates/$T1/ '{"subject":"Order approved!","content":"Hi {{buyerName}}"}')" | jget "['subject']")"
check "deactivate" False "$(body "$(req PATCH /email-templates/$T1/ '{"is_active":false}')" | jget "['is_active']")"
check "key change -> 400" 400 "$(code "$(req PATCH /email-templates/$T1/ '{"key":"smoke_other"}')")"
check "PUT with same key ok" 200 "$(code "$(req PUT /email-templates/$T1/ '{"key":"smoke_order_approved","subject":"S","content":"C","is_active":true}')")"
check "list search" 2 "$(body "$(req GET "/email-templates/?search=smoke")" | cnt)"
check "filter is_active=false" 1 "$(body "$(req GET "/email-templates/?search=smoke&is_active=false")" | cnt)"
check "search by subject" 1 "$(body "$(req GET "/email-templates/?search=Smoke%20Welcome")" | cnt)"
check "delete template" 204 "$(code "$(req DELETE /email-templates/$T1/)")"
check "delete template 2" 204 "$(code "$(req DELETE /email-templates/$T2/)")"
check "deleted -> 404" 404 "$(code "$(req GET /email-templates/$T1/)")"

echo "=== Settings ==="
check "create number setting" 201 "$(code "$(req POST /settings/ '{"key":"smoke_commission_rate","value":10}')")"
check "create object setting" 201 "$(code "$(req POST /settings/ '{"key":"smoke_contact","value":{"email":"help@egoola.com","phones":["+8801700000000"]}}')")"
check "create string setting" 201 "$(code "$(req POST /settings/ '{"key":"smoke_site_name","value":"Egoola"}')")"
check "create bool setting" 201 "$(code "$(req POST /settings/ '{"key":"smoke_maintenance","value":false}')")"
check "duplicate key -> 400" 400 "$(code "$(req POST /settings/ '{"key":"smoke_site_name","value":"x"}')")"
check "bad key -> 400" 400 "$(code "$(req POST /settings/ '{"key":"Bad Key","value":1}')")"
check "missing value -> 400" 400 "$(code "$(req POST /settings/ '{"key":"smoke_novalue"}')")"
check "reserved key create -> 400" 400 "$(code "$(req POST /settings/ '{"key":"site_logo_url","value":"x"}')")"
check "retrieve by key" 10 "$(body "$(req GET /settings/smoke_commission_rate/)" | jget "['value']")"
check "retrieve object value" "help@egoola.com" "$(body "$(req GET /settings/smoke_contact/)" | jget "['value']['email']")"
check "unknown key -> 404" 404 "$(code "$(req GET /settings/smoke_nope/)")"
check "update value" 12 "$(body "$(req PATCH /settings/smoke_commission_rate/ '{"value":12}')" | jget "['value']")"
check "value type can change" '{'"'"'a'"'"': 1}' "$(body "$(req PATCH /settings/smoke_commission_rate/ '{"value":{"a":1}}')" | jget "['value']")"
check "key change -> 400" 400 "$(code "$(req PATCH /settings/smoke_commission_rate/ '{"key":"smoke_other"}')")"
check "PUT" 200 "$(code "$(req PUT /settings/smoke_maintenance/ '{"key":"smoke_maintenance","value":true}')")"
check "list search" 4 "$(body "$(req GET "/settings/?search=smoke")" | cnt)"
for k in smoke_commission_rate smoke_contact smoke_site_name smoke_maintenance; do req DELETE /settings/$k/ >/dev/null; done
check "deleted -> 404" 404 "$(code "$(req GET /settings/smoke_site_name/)")"

echo "=== Site logo ==="
R=$(req GET /site-logo/)
check "GET empty logo" 200 "$(code "$R")"; check "empty path null" None "$(body "$R" | jget "['path']")"
check "no image -> 400" 400 "$(code "$(mp POST /site-logo/)")"
check "non-image -> 400" 400 "$(code "$(mp POST /site-logo/ -F "image=@$SCRATCH/cms_notimg.txt;type=text/plain")")"
R=$(mp POST /site-logo/ -F "image=@$IMG;type=image/png")
check "upload logo" 200 "$(code "$R")"; L1=$(body "$R" | jget "['path']")
check "logo url set" True "$(body "$R" | python -c "import sys,json;print(bool(json.load(sys.stdin)['url']))")"
check "logo file stored" True "$([ -f "$SERVER_DIR/media/$L1" ] && echo True)"
check "GET returns logo" "$L1" "$(body "$(req GET /site-logo/)" | jget "['path']")"
check "setting site_logo_path visible" "$L1" "$(body "$(req GET /settings/site_logo_path/)" | jget "['value']")"
check "edit logo setting -> 400" 400 "$(code "$(req PATCH /settings/site_logo_url/ '{"value":"hacked"}')")"
check "delete logo setting -> 400" 400 "$(code "$(req DELETE /settings/site_logo_path/)")"
R=$(mp PUT /site-logo/ -F "image=@$IMG;type=image/png")
check "replace logo (PUT)" 200 "$(code "$R")"; L2=$(body "$R" | jget "['path']")
check "new logo path differs" True "$([ "$L1" != "$L2" ] && echo True)"
check "old logo file removed" True "$([ ! -f "$SERVER_DIR/media/$L1" ] && echo True)"
check "delete logo" 204 "$(code "$(req DELETE /site-logo/)")"
check "logo file removed" True "$([ ! -f "$SERVER_DIR/media/$L2" ] && echo True)"
check "GET after delete empty" None "$(body "$(req GET /site-logo/)" | jget "['url']")"
check "delete when none is ok" 204 "$(code "$(req DELETE /site-logo/)")"

echo "=== Audit stamping (DB) ==="
cd "$SERVER_DIR"
uv run manage.py shell -c "
from apps.cms.models import Banner, EmailTemplate, Setting
print('LEFT', Banner.objects.filter(heading__startswith='Smoke').count(), EmailTemplate.objects.filter(key__startswith='smoke').count(), Setting.objects.filter(key__startswith='smoke').count(), Setting.objects.filter(key__startswith='site_logo').count())" 2>&1 | grep LEFT
rm -f "$IMG" "$SCRATCH/cms_notimg.txt"
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
