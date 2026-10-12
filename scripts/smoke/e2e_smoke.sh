#!/usr/bin/env bash
# End-to-end smoke: seller approval, listing moderation, buyer management,
# second admin by a super-admin, banner update (CMS). All data is prefixed
# "E2E" / e2e.* and removed at the end.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
BASE="$SMOKE_BASE/api/v1"
SERVER="$SERVER_DIR"
PASS=0; FAIL=0
check() { if [ "$2" == "$3" ]; then echo "OK   $1 (got $3)"; PASS=$((PASS+1)); else echo "FAIL $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi; }
jget() { python -c "import sys,json;d=json.load(sys.stdin);print(d$1)" 2>/dev/null; }
code() { echo "$1" | tail -1; }
body() { echo "$1" | sed '$d'; }
req() { curl -s -w '\n%{http_code}' -X "$1" "$BASE$2" -H "$AUTH" -H "Content-Type: application/json" ${3:+-d "$3"}; }
login() { local field=email; [ "$1" == seller ] && field=phone; curl -s -X POST "$BASE/auth/$1/login/" -H "Content-Type: application/json" -d "{\"$field\":\"$2\",\"password\":\"$3\"}" | python -c "import sys,json;print(json.load(sys.stdin).get('access',''))"; }
dbq() { (cd "$SERVER" && uv run manage.py shell -c "$1" 2>&1 | tail -1); }

PNG="$SCRATCH/t.png"
echo "not an image" > "$SCRATCH/notimg.txt"

ADMIN=$(login admin test.admin@egoola.com 'Test@12345')
SUPER=$(login admin test.super@egoola.com 'Test@12345')
check "plain admin login" True "$([ -n "$ADMIN" ] && echo True)"
check "super admin login" True "$([ -n "$SUPER" ] && echo True)"
LOGIN_JSON() { curl -s -X POST "$BASE/auth/$1/login/" -H "Content-Type: application/json" -d "{\"email\":\"$2\",\"password\":\"$3\"}"; }
check "admin login returns admin_type admin" admin "$(LOGIN_JSON admin test.admin@egoola.com 'Test@12345' | jget "['admin_type']")"
check "super-admin login returns admin_type super_admin" super_admin "$(LOGIN_JSON admin test.super@egoola.com 'Test@12345' | jget "['admin_type']")"
check "seller login has no admin_type" None "$(LOGIN_JSON seller test.seller@egoola.com 'Test@12345' | jget ".get('admin_type')")"
AUTH="Authorization: Bearer $ADMIN"

echo; echo "=== 1) SELLER APPROVAL ==="
R=$(req POST /accounts/sellers/ '{"name":"E2E Seller","email":"e2e.seller@example.com","phone":"+8801700070001","password":"Sell@12345","verification_status":"unverified"}')
check "create seller (explicit unverified)" 201 "$(code "$R")"; SID=$(body "$R" | jget "['id']")
check "seller starts unverified" unverified "$(body "$R" | jget "['verification_status']")"
R=$(req POST /accounts/sellers/ '{"name":"E2E Seller Default","email":"e2e.seller2@example.com","phone":"+8801700070002","password":"Sell@12345"}')
check "admin-created seller defaults to verified" verified "$(body "$R" | jget "['verification_status']")"; SID2=$(body "$R" | jget "['id']")
check "reject without note -> 400" 400 "$(code "$(req PATCH /accounts/sellers/$SID/ '{"verification_status":"rejected"}')")"
R=$(req PATCH /accounts/sellers/$SID/ '{"verification_status":"rejected","verification_note":"NID is blurry"}')
check "reject with note" rejected "$(body "$R" | jget "['verification_status']")"
check "note stored" "NID is blurry" "$(body "$R" | jget "['verification_note']")"
R=$(req PATCH /accounts/sellers/$SID/ '{"verification_status":"verified"}')
check "approve (verified)" 200 "$(code "$R")"
check "approve clears the reject note" None "$(body "$R" | jget "['verification_note']")"
R=$(req GET /accounts/sellers/$SID/)
check "history has 3 entries" 3 "$(body "$R" | jget "['verification_logs'].__len__()")"
check "latest log (newest first) is verified" verified "$(body "$R" | jget "['verification_logs'][0]['verification_status']")"
check "log stamped admin" admin "$(body "$R" | jget "['verification_logs'][0]['creator_type']")"
check "log creator name" "$(dbq "from apps.accounts.models import Admin;print(Admin.objects.get(email='test.admin@egoola.com').name)")" "$(body "$R" | jget "['verification_logs'][0]['creator_name']")"
R=$(req PATCH /accounts/sellers/$SID/ '{"name":"E2E Seller Renamed"}')
check "non-status edit keeps log count" 3 "$(body "$(req GET /accounts/sellers/$SID/)" | jget "['verification_logs'].__len__()")"
check "filter verified" True "$(req GET "/accounts/sellers/?verification_status=verified&search=E2E" | sed '$d' | python -c "import sys,json;d=json.load(sys.stdin);print(d['count']>=2)")"
check "seller token on sellers -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/sellers/ -H "Authorization: Bearer $(login seller +8801700070001 'Sell@12345')")"

echo; echo "=== 2) LISTING MODERATION ==="
mk() { req POST /catalog/listings/ "{\"seller\":$SID,\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"general\",\"posted_by_role\":\"seller_offer\",\"title\":\"$1\",\"description\":\"d\",\"price\":\"100.00\"}"; }
R=$(mk "E2E Listing A"); check "create listing A" 201 "$(code "$R")"; LA=$(body "$R" | jget "['id']")
check "admin-created listing is approved" approved "$(body "$R" | jget "['status']")"
check "discounted_price defaults to price" "100.00" "$(body "$R" | jget "['discounted_price']")"
check "1 status log on create" 1 "$(body "$R" | jget "['status_change_logs'].__len__()")"
R=$(mk "E2E Listing B"); LB=$(body "$R" | jget "['id']")
R=$(mk "E2E Listing C"); LC=$(body "$R" | jget "['id']")
R=$(mk "E2E Listing A"); check "same title gets a unique slug" True "$([ "$(body "$R" | jget "['slug']")" == "e2e-listing-a-2" ] && echo True)"; LD=$(body "$R" | jget "['id']")
check "reject w/o note -> 400" 400 "$(code "$(req PATCH /catalog/listings/$LA/ '{"status":"rejected"}')")"
check "changes_requested w/o note -> 400" 400 "$(code "$(req PATCH /catalog/listings/$LA/ '{"status":"changes_requested"}')")"
R=$(req PATCH /catalog/listings/$LA/ '{"status":"rejected","note":"Photos missing"}')
check "reject with note" rejected "$(body "$R" | jget "['status']")"
check "note on row" "Photos missing" "$(body "$R" | jget "['note']")"
R=$(req PATCH /catalog/listings/$LA/ '{"status":"changes_requested","note":"Add 3 photos"}')
check "changes_requested" changes_requested "$(body "$R" | jget "['status']")"
check "note replaced, not appended" "Add 3 photos" "$(body "$R" | jget "['note']")"
R=$(req PATCH /catalog/listings/$LA/ '{"title":"E2E Listing A edited"}')
check "non-status edit keeps note" "Add 3 photos" "$(body "$R" | jget "['note']")"
R=$(req PATCH /catalog/listings/$LA/ '{"status":"approved"}')
check "approve" approved "$(body "$R" | jget "['status']")"
check "approve clears note" None "$(body "$R" | jget "['note']")"
check "history = create+reject+changes+approve" 4 "$(body "$R" | jget "['status_change_logs'].__len__()")"
LASKU=$(body "$(req GET /catalog/listings/$LA/)" | jget "['skus'][0]['id']")
check "SKU price follows when no discount" "120.00" "$(body "$(req PATCH /catalog/listings/$LA/ "{\"skus\":[{\"id\":$LASKU,\"price\":\"120.00\"}]}")" | jget "['skus'][0]['discounted_price']")"
check "discount above price -> 400" 400 "$(code "$(req PATCH /catalog/listings/$LA/ "{\"skus\":[{\"id\":$LASKU,\"discounted_price\":\"999.00\"}]}")")"
check "both seller and buyer -> 400" 400 "$(code "$(req PATCH /catalog/listings/$LA/ '{"buyer":4}')")"
echo "--- bulk moderate"
check "bulk bad status -> 400" 400 "$(code "$(req POST /catalog/listings/bulk-moderate/ "{\"listing_ids\":[$LB],\"status\":\"pending\"}")")"
check "bulk reject w/o note -> 400" 400 "$(code "$(req POST /catalog/listings/bulk-moderate/ "{\"listing_ids\":[$LB],\"status\":\"rejected\"}")")"
check "bulk empty ids -> 400" 400 "$(code "$(req POST /catalog/listings/bulk-moderate/ '{"listing_ids":[],"status":"approved"}')")"
R=$(req POST /catalog/listings/bulk-moderate/ "{\"listing_ids\":[$LB,$LC,$LA],\"status\":\"rejected\",\"note\":\"Policy breach\"}")
check "bulk reject 200" 200 "$(code "$R")"
check "bulk updated 3" 3 "$(body "$R" | jget "['updated'].__len__()")"
R=$(req POST /catalog/listings/bulk-moderate/ "{\"listing_ids\":[$LB],\"status\":\"rejected\",\"note\":\"again\"}")
check "same status again is skipped" 1 "$(body "$R" | jget "['skipped'].__len__()")"
check "bulk ids not a list -> 400" 400 "$(code "$(req POST /catalog/listings/bulk-moderate/ '{"listing_ids":"1,2","status":"approved"}')")"
check "bulk-malformed ids -> 400 (not 500)" 400 "$(code "$(req POST /catalog/listings/bulk-moderate/ '{"listing_ids":["abc"],"status":"approved"}')")"
check "bulk wrote a log per listing" 2 "$(body "$(req GET /catalog/listings/$LB/)" | jget "['status_change_logs'].__len__()")"
check "bulk log carries the note" "Policy breach" "$(body "$(req GET /catalog/listings/$LB/)" | jget "['status_change_logs'][0]['note']")"
check "bulk stamps updated_by on the row" "$(dbq "from apps.accounts.models import Admin;print(Admin.objects.get(email='test.admin@egoola.com').id)")" "$(dbq "from apps.catalog.models import Listing;print(Listing.objects.get(id=$LB).updated_by)")"
echo "--- soft delete"
check "delete -> 204" 204 "$(code "$(req DELETE /catalog/listings/$LD/)")"
check "deleted is hidden (404)" 404 "$(code "$(req GET /catalog/listings/$LD/)")"
check "soft delete stamps updated_by" "$(dbq "from apps.accounts.models import Admin;print(Admin.objects.get(email='test.admin@egoola.com').id)")" "$(dbq "from apps.catalog.models import Listing;print(Listing.all_objects.get(id=$LD).updated_by)")"
check "row still in DB with deleted_at" True "$(dbq "from apps.catalog.models import Listing;print(Listing.all_objects.get(id=$LD).deleted_at is not None)")"
check "list filter status=rejected" True "$(req GET "/catalog/listings/?status=rejected&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count']>=3)")"
check "seller token on listings -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/catalog/listings/ -H "Authorization: Bearer $(login seller +8801700070001 'Sell@12345')")"

echo; echo "=== 3) BUYER MANAGEMENT ==="
R=$(req POST /accounts/buyers/ '{"name":"E2E Buyer","email":"e2e.buyer@example.com","phone":"+8801700070011","password":"Buy@12345","country":126,"state":13,"city":8}')
check "create buyer" 201 "$(code "$R")"; BID=$(body "$R" | jget "['id']")
check "defaults active" active "$(body "$R" | jget "['status']")"
check "no password in response" None "$(body "$R" | jget ".get('password')")"
check "buyer can log in" True "$([ -n "$(login buyer e2e.buyer@example.com 'Buy@12345')" ] && echo True)"
check "duplicate email -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"X","email":"e2e.buyer@example.com","phone":"+8801700070012","password":"Buy@12345"}')")"
check "detail" 200 "$(code "$(req GET /accounts/buyers/$BID/)")"
BTOK=$(login buyer e2e.buyer@example.com 'Buy@12345')
check "update name" "E2E Buyer Renamed" "$(body "$(req PATCH /accounts/buyers/$BID/ '{"name":"E2E Buyer Renamed"}')" | jget "['name']")"
check "suspend" suspended "$(body "$(req PATCH /accounts/buyers/$BID/ '{"status":"suspended"}')" | jget "['status']")"
check "suspended buyer cannot log in" "" "$(login buyer e2e.buyer@example.com 'Buy@12345')"
check "suspended buyer's earlier token is rejected too" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/buyers/ -H "Authorization: Bearer $BTOK")"
check "filter status=suspended + search" 1 "$(req GET "/accounts/buyers/?status=suspended&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count'])")"
check "filter city" True "$(req GET "/accounts/buyers/?city=8&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count']>=1)")"
check "filter email_verified=false" True "$(req GET "/accounts/buyers/?email_verified=false&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count']>=1)")"
check "filter email_verified=true excludes it" 0 "$(req GET "/accounts/buyers/?email_verified=true&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count'])")"
TODAY=$(python -c "import datetime;print(datetime.date.today())")
check "filter created_from today" True "$(req GET "/accounts/buyers/?created_from=$TODAY&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count']>=1)")"
check "filter created_to yesterday -> 0" 0 "$(req GET "/accounts/buyers/?created_to=2000-01-01&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count'])")"
check "reactivate" active "$(body "$(req PATCH /accounts/buyers/$BID/ '{"status":"active"}')" | jget "['status']")"
check "bad status -> 400" 400 "$(code "$(req PATCH /accounts/buyers/$BID/ '{"status":"banned"}')")"
check "unauth -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/buyers/)"
check "audit: updater stamped" admin "$(dbq "from apps.accounts.models import User;print(User.objects.get(id=$BID).updater_type)")"

echo; echo "=== 4) SECOND ADMIN BY A SUPER-ADMIN ==="
check "plain admin cannot create admin -> 403" 403 "$(code "$(req POST /accounts/admins/ '{"name":"E2E Nope","email":"e2e.nope@example.com","mobile":"+8801700070020","password":"Adm@12345","type":"admin"}')")"
AUTH="Authorization: Bearer $SUPER"
R=$(req POST /accounts/admins/ '{"name":"E2E Admin Two","email":"e2e.admin2@example.com","mobile":"+8801700070021","password":"Adm@12345","type":"admin"}')
check "super-admin creates admin" 201 "$(code "$R")"; AID=$(body "$R" | jget "['id']")
check "type admin" admin "$(body "$R" | jget "['type']")"
check "created_by stamped as super admin" "$(dbq "from apps.accounts.models import Admin;print(Admin.objects.get(email='test.super@egoola.com').id)")" "$(dbq "from apps.accounts.models import Admin;print(Admin.objects.get(id=$AID).created_by)")"
check "role 'moderator' rejected -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"X","email":"e2e.x@example.com","mobile":"+8801700070022","password":"Adm@12345","type":"moderator"}')")"
check "duplicate email -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"X","email":"e2e.admin2@example.com","mobile":"+8801700070023","password":"Adm@12345","type":"admin"}')")"
check "list contains new admin" True "$(req GET "/accounts/admins/?search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count']==1)")"
N2=$(login admin e2e.admin2@example.com 'Adm@12345')
check "new admin logs in" True "$([ -n "$N2" ] && echo True)"
check "new plain admin -> admins list 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $N2")"
check "new plain admin can reach sellers" 200 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/sellers/ -H "Authorization: Bearer $N2")"
check "new plain admin can reach CMS" 200 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/cms/banners/ -H "Authorization: Bearer $N2")"
check "super-admin promotes new admin" super_admin "$(body "$(req PATCH /accounts/admins/$AID/ '{"type":"super_admin"}')" | jget "['type']")"
check "promoted admin reaches admins (same token)" 200 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $N2")"
check "super-admin demotes new admin" admin "$(body "$(req PATCH /accounts/admins/$AID/ '{"type":"admin"}')" | jget "['type']")"
check "demotion immediate (same token) -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/admins/ -H "Authorization: Bearer $N2")"
SUPER_ID=$(dbq "from apps.accounts.models import Admin;print(Admin.objects.get(email='test.super@egoola.com').id)")
check "cannot delete self -> 400" 400 "$(code "$(req DELETE /accounts/admins/$SUPER_ID/)")"
check "cannot change own type -> 400" 400 "$(code "$(req PATCH /accounts/admins/$SUPER_ID/ '{"type":"admin"}')")"
check "cannot deactivate self -> 400" 400 "$(code "$(req PATCH /accounts/admins/$SUPER_ID/ '{"status":"inactive"}')")"
check "deactivate the new admin" inactive "$(body "$(req PATCH /accounts/admins/$AID/ '{"status":"inactive"}')" | jget "['status']")"
check "inactive admin cannot log in" "" "$(login admin e2e.admin2@example.com 'Adm@12345')"
check "inactive admin's old token stops working" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/cms/banners/ -H "Authorization: Bearer $N2")"

echo; echo "=== 5) BANNER UPDATE (CMS) ==="
AUTH="Authorization: Bearer $ADMIN"
R=$(curl -s -w '\n%{http_code}' -X POST $BASE/cms/banners/ -H "$AUTH" -F placement=hero -F "heading=E2E Hero" -F link_url=/sale -F sort_order=1 -F "image=@$PNG;type=image/png")
check "create banner" 201 "$(code "$R")"; BNID=$(body "$R" | jget "['id']"); OLDIMG=$(body "$R" | jget "['image_path']")
check "image stored on disk" True "$([ -f "$SERVER/media/$OLDIMG" ] && echo True)"
check "create without image -> 400" 400 "$(code "$(curl -s -w '\n%{http_code}' -X POST $BASE/cms/banners/ -H "$AUTH" -F placement=hero)")"
check "edit heading (JSON PATCH)" "E2E Hero v2" "$(body "$(req PATCH /cms/banners/$BNID/ '{"heading":"E2E Hero v2"}')" | jget "['heading']")"
check "hide banner" inactive "$(body "$(req PATCH /cms/banners/$BNID/ '{"status":"inactive"}')" | jget "['status']")"
check "active_now excludes inactive" 0 "$(req GET "/cms/banners/?active_now=true&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count'])")"
check "re-activate" active "$(body "$(req PATCH /cms/banners/$BNID/ '{"status":"active"}')" | jget "['status']")"
check "active_now includes it" 1 "$(req GET "/cms/banners/?active_now=true&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count'])")"
check "schedule in the past" 200 "$(code "$(req PATCH /cms/banners/$BNID/ '{"starts_at":"2020-01-01T00:00:00Z","ends_at":"2020-02-01T00:00:00Z"}')")"
check "active_now excludes expired" 0 "$(req GET "/cms/banners/?active_now=true&search=E2E" | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['count'])")"
check "ends_at before starts_at -> 400" 400 "$(code "$(req PATCH /cms/banners/$BNID/ '{"ends_at":"2019-01-01T00:00:00Z"}')")"
check "category on hero -> 400" 400 "$(code "$(req PATCH /cms/banners/$BNID/ '{"category":18}')")"
R=$(curl -s -w '\n%{http_code}' -X PATCH $BASE/cms/banners/$BNID/ -H "$AUTH" -F "image=@$PNG;type=image/png" -F "small_heading=New image")
check "replace image (multipart PATCH)" 200 "$(code "$R")"
NEWIMG=$(body "$R" | jget "['image_path']")
check "image path changed" True "$([ "$NEWIMG" != "$OLDIMG" ] && echo True)"
check "old file deleted" False "$([ -f "$SERVER/media/$OLDIMG" ] && echo True || echo False)"
check "new file exists" True "$([ -f "$SERVER/media/$NEWIMG" ] && echo True)"
check "non-image upload -> 400" 400 "$(code "$(curl -s -w '\n%{http_code}' -X PATCH $BASE/cms/banners/$BNID/ -H "$AUTH" -F "image=@$SCRATCH/notimg.txt;type=text/plain")")"
check "retrieve shows edits" "New image" "$(body "$(req GET /cms/banners/$BNID/)" | jget "['small_heading']")"
check "updated_by stamped" admin "$(dbq "from apps.cms.models import Banner;print(Banner.objects.get(id=$BNID).updater_type)")"
check "seller token on CMS -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/cms/banners/ -H "Authorization: Bearer $(login seller +8801700070001 'Sell@12345')")"
check "no token on CMS -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/cms/banners/)"
check "delete banner" 204 "$(code "$(req DELETE /cms/banners/$BNID/)")"
check "banner file removed" False "$([ -f "$SERVER/media/$NEWIMG" ] && echo True || echo False)"
echo "--- other CMS bits"
check "email template create" 201 "$(code "$(req POST /cms/email-templates/ '{"key":"e2e_welcome","subject":"Hi","content":"Hello {{name}}"}')")"
check "email template key immutable" 400 "$(code "$(req PATCH /cms/email-templates/$(req GET '/cms/email-templates/?search=e2e_welcome' | sed '$d' | python -c "import sys,json;print(json.load(sys.stdin)['results'][0]['id'])")/ '{"key":"e2e_other"}')")"
check "setting create" 201 "$(code "$(req POST /cms/settings/ '{"key":"e2e_setting","value":{"a":[1,2]}}')")"
check "setting update" 200 "$(code "$(req PATCH /cms/settings/e2e_setting/ '{"value":7}')")"
check "logo keys reserved" 400 "$(code "$(req POST /cms/settings/ '{"key":"site_logo_url","value":"x"}')")"


echo; echo "=== 6) VALIDATION & NOTE RULES (review fixes) ==="
AUTH="Authorization: Bearer $ADMIN"
LB2='"category":18,"catalog_type":"product","listing_type":"general","description":"d"'
lc() { code "$(req POST /catalog/listings/ "{$LB2,\"title\":\"E2E $1\",$2}")"; }
check "negative price -> 400" 400 "$(lc neg '"price":"-5"')"
check "negative stock -> 400" 400 "$(lc stock '"price":"5","stock_qty":-1')"
check "tier max < min -> 400" 400 "$(lc t1 '"price":"10","price_tiers":[{"min_qty":10,"max_qty":5,"price":"9"}]')"
check "tier min 0 -> 400" 400 "$(lc t2 '"price":"10","price_tiers":[{"min_qty":0,"price":"9"}]')"
check "overlapping tiers -> 400" 400 "$(lc t3 '"price":"10","price_tiers":[{"min_qty":1,"max_qty":10,"price":"9"},{"min_qty":5,"max_qty":20,"price":"8"}]')"
check "open-ended middle tier -> 400" 400 "$(lc t4 '"price":"10","price_tiers":[{"min_qty":1,"price":"9"},{"min_qty":5,"max_qty":20,"price":"8"}]')"
check "valid 3-tier ladder -> 201" 201 "$(lc t5 '"price":"10","price_tiers":[{"min_qty":1,"max_qty":9,"price":"10"},{"min_qty":10,"max_qty":49,"price":"9"},{"min_qty":50,"price":"8"}]')"
check "service category on product -> 400" 400 "$(code "$(req POST /catalog/listings/ '{"category":29,"catalog_type":"product","listing_type":"general","title":"E2E cat","description":"d","price":"5"}')")"
(cd "$SERVER" && uv run manage.py shell -c "from apps.catalog.models import Category;Category.objects.filter(id=25).update(status='inactive')" >/dev/null 2>&1)
check "inactive category -> 400" 400 "$(code "$(req POST /catalog/listings/ '{"category":25,"catalog_type":"product","listing_type":"general","title":"E2E inactive","description":"d","price":"5"}')")"
(cd "$SERVER" && uv run manage.py shell -c "from apps.catalog.models import Category;Category.objects.filter(id=25).update(status='active')" >/dev/null 2>&1)
check "catalog_type flip vs category -> 400" 400 "$(code "$(req PATCH /catalog/listings/$LA/ '{"catalog_type":"service"}')")"
echo "--- note only belongs to a status change"
req PATCH /catalog/listings/$LA/ '{"status":"approved"}' >/dev/null
req PATCH /catalog/listings/$LA/ '{"status":"rejected","note":"first reason"}' >/dev/null
R=$(req PATCH /catalog/listings/$LA/ '{"note":"sneaky edit"}')
check "note-only PATCH ignored" "first reason" "$(body "$R" | jget "['note']")"
R=$(req PATCH /catalog/listings/$LA/ '{"status":"rejected"}')
check "same status re-sent, no note -> 200 no-op" 200 "$(code "$R")"
check "  note unchanged" "first reason" "$(body "$R" | jget "['note']")"
R=$(req PATCH /catalog/listings/$LA/ '{"status":"rejected","note":"rewritten"}')
check "same status + new note ignored" "first reason" "$(body "$R" | jget "['note']")"
LOGS=$(body "$(req GET /catalog/listings/$LA/)" | jget "['status_change_logs'].__len__()")
LOGN=$(body "$(req GET /catalog/listings/$LA/)" | jget "['status_change_logs'][0]['note']")
check "row note == newest log note" "$LOGN" "$(body "$(req GET /catalog/listings/$LA/)" | jget "['note']")"
req PATCH /accounts/sellers/$SID/ '{"verification_status":"rejected","verification_note":"bad docs"}' >/dev/null
R=$(req PATCH /accounts/sellers/$SID/ '{"verification_note":"sneaky"}')
check "seller note-only PATCH ignored" "bad docs" "$(body "$R" | jget "['verification_note']")"
check "seller same status re-sent -> 200" 200 "$(code "$(req PATCH /accounts/sellers/$SID/ '{"verification_status":"rejected"}')")"
check "seller reject w/o note on a verified seller -> 400" 400 "$(code "$(req PATCH /accounts/sellers/$SID2/ '{"verification_status":"rejected"}')")"
echo "--- bulk keeps request order"
R=$(req POST /catalog/listings/bulk-moderate/ "{\"listing_ids\":[$LC,$LB,$LC],\"status\":\"approved\"}")
check "bulk order = request order, deduped" "[$LC, $LB]" "$(body "$R" | jget "['updated']")"


echo; echo "=== 7) LOCATION & PASSWORD RULES ==="
AUTH="Authorization: Bearer $ADMIN"
check "city from another state -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"E2E Loc","email":"e2e.loc1@example.com","phone":"+8801700070031","password":"Buy@12345","country":126,"state":12,"city":8}')")"
check "state from another country -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"E2E Loc","email":"e2e.loc2@example.com","phone":"+8801700070032","password":"Buy@12345","country":127,"state":13}')")"
R=$(req POST /accounts/buyers/ '{"name":"E2E Loc","email":"e2e.loc3@example.com","phone":"+8801700070033","password":"Buy@12345","country":126,"state":13,"city":8}')
check "consistent country/state/city -> 201" 201 "$(code "$R")"; LOCID=$(body "$R" | jget "['id']")
check "moving to a state that does not hold the city -> 400" 400 "$(code "$(req PATCH /accounts/buyers/$LOCID/ '{"state":12}')")"
check "unrelated edit still fine" 200 "$(code "$(req PATCH /accounts/buyers/$LOCID/ '{"name":"E2E Loc 2"}')")"
check "country only -> 201" 201 "$(code "$(req POST /accounts/buyers/ '{"name":"E2E Loc","email":"e2e.loc4@example.com","phone":"+8801700070034","password":"Buy@12345","country":126}')")"
check "listing: mismatched location -> 400" 400 "$(code "$(req POST /catalog/listings/ '{"category":18,"catalog_type":"product","listing_type":"general","title":"E2E loc","description":"d","price":"5","state":12,"city":8}')")"
check "listing: consistent location -> 201" 201 "$(code "$(req POST /catalog/listings/ '{"category":18,"catalog_type":"product","listing_type":"general","title":"E2E loc ok","description":"d","price":"5","country":126,"state":13,"city":8}')")"
check "seller business info: mismatched location -> 400" 400 "$(code "$(req POST /accounts/sellers/ '{"name":"E2E Loc Seller","email":"e2e.locseller@example.com","phone":"+8801700070035","password":"Sell@12345","info":{"business_type":"Retail","main_product":"x","owner_name":"x","employees_range":"1-10","annual_revenue":"< $50,000","established_year":"2024","state":12,"city":8}}')")"
echo "--- password strength"
check "buyer password '1' -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"E2E Pw","email":"e2e.pw1@example.com","phone":"+8801700070036","password":"1"}')")"
check "buyer password 'password' (too common) -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"E2E Pw","email":"e2e.pw2@example.com","phone":"+8801700070037","password":"password"}')")"
check "buyer password '12345678' (all digits) -> 400" 400 "$(code "$(req POST /accounts/buyers/ '{"name":"E2E Pw","email":"e2e.pw3@example.com","phone":"+8801700070038","password":"12345678"}')")"
check "seller weak password on update -> 400" 400 "$(code "$(req PATCH /accounts/sellers/$SID/ '{"password":"abc"}')")"
check "seller strong password on update -> 200" 200 "$(code "$(req PATCH /accounts/sellers/$SID/ '{"password":"NewSell@54321"}')")"
AUTH="Authorization: Bearer $SUPER"
check "admin weak password -> 400" 400 "$(code "$(req POST /accounts/admins/ '{"name":"E2E Pw","email":"e2e.pw4@example.com","mobile":"+8801700070039","password":"1234","type":"admin"}')")"
AUTH="Authorization: Bearer $ADMIN"

echo; echo "=== CLEANUP ==="
(cd "$SERVER" && uv run manage.py shell -c "
from apps.accounts.models import Admin, Seller, User
from apps.catalog.models import Listing
from apps.cms.models import Banner, EmailTemplate, Setting
Listing.all_objects.filter(title__startswith='E2E').delete()
Seller.objects.filter(email__startswith='e2e.').delete()
User.objects.filter(email__startswith='e2e.').delete()
Admin.objects.filter(email__startswith='e2e.').delete()
Banner.objects.filter(heading__startswith='E2E').delete()
EmailTemplate.objects.filter(key__startswith='e2e_').delete()
Setting.objects.filter(key__startswith='e2e_').delete()
print('cleaned')
" 2>&1 | tail -1)
echo "leftovers (should be 0): $(dbq "
from apps.accounts.models import Admin, Seller, User
from apps.catalog.models import Listing
from apps.cms.models import Banner, EmailTemplate, Setting
print(Listing.all_objects.filter(title__startswith='E2E').count()+Seller.objects.filter(email__startswith='e2e.').count()+User.objects.filter(email__startswith='e2e.').count()+Admin.objects.filter(email__startswith='e2e.').count()+Banner.objects.filter(heading__startswith='E2E').count()+EmailTemplate.objects.filter(key__startswith='e2e_').count()+Setting.objects.filter(key__startswith='e2e_').count())")"
echo; echo "RESULT: $PASS passed, $FAIL failed"
