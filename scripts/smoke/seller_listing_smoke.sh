#!/usr/bin/env bash
# Seller listing management (/seller/listings/ and /seller/lookups/...) and how the
# admin side sees it: the pending list, approve / reject, the info change log, the
# unique-title rule, Bangla fields, and files removed from storage.
set -uo pipefail
export PYTHONIOENCODING=utf-8  # the Bangla checks print non-ASCII text
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
BASE="$SMOKE_BASE/api/v1"
SL="$BASE/seller/listings"
AL="$BASE/catalog/listings"
PASS=0; FAIL=0
check() { if [ "$2" == "$3" ]; then echo "OK   $1 (got $3)"; PASS=$((PASS+1)); else echo "FAIL $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi; }
code() { echo "$1" | tail -1; }
body() { echo "$1" | sed '$d'; }
py() { python -c "import sys,json;d=json.load(sys.stdin);print($1)" 2>/dev/null; }
# JSON bodies go through a file: curl on Windows mangles non-ASCII (Bangla) text given with -d.
jreq() { # token method url [json]
  local data=(); if [ -n "${4:-}" ]; then printf '%s' "$4" > "$SCRATCH/body.json"; data=(--data-binary "@$SCRATCH/body.json"); fi
  curl -s -w '
%{http_code}' -X "$2" "$3" -H "Authorization: Bearer $1" -H "Content-Type: application/json" ${data[@]+"${data[@]}"}; }
areq() { jreq "$TOKEN" "$1" "$2" "${3:-}"; }
sreq() { jreq "$ST" "$1" "$2" "${3:-}"; }
s2req() { jreq "$ST2" "$1" "$2" "${3:-}"; }
login() { curl -s -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d "{\"phone\":\"$1\",\"password\":\"Sell@12345\"}" | py "d.get('access','')"; }
fx() { local list="" p; for p in "$@"; do list="$list'$p',"; done
  (cd "$SERVER_DIR" && uv run manage.py shell -c "
import os
from django.conf import settings
print('FX', ' '.join(str(os.path.exists(os.path.join(settings.MEDIA_ROOT, p))) for p in [$list]))" 2>&1 | grep '^FX' | sed 's/^FX //'); }

cp "$SCRATCH/t.png" "$SCRATCH/l1.png"; cp "$SCRATCH/t.png" "$SCRATCH/l2.png"
echo "just text" > "$SCRATCH/note.txt"
PNG="image/png"

TOKEN=$(curl -s -X POST "$BASE/auth/admin/login/" -H "Content-Type: application/json" -d '{"email":"test.admin@egoola.com","password":"Test@12345"}' | py "d['access']")
[ -n "$TOKEN" ] && echo "OK   admin login" && PASS=$((PASS+1))
BT=$(curl -s -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"test.buyer@egoola.com","password":"Test@12345"}' | py "d['access']")

mk_seller() { # name email phone [extra json]
  body "$(areq POST $BASE/accounts/sellers/ "{\"name\":\"$1\",\"email\":\"$2\",\"phone\":\"$3\",\"password\":\"Sell@12345\"$4}")" | py "d['id']"; }
S1=$(mk_seller "Smoke Lister One" smoke.lister.one@example.com +8801700097101 "")
S2=$(mk_seller "Smoke Lister Two" smoke.lister.two@example.com +8801700097102 "")
S3=$(mk_seller "Smoke Lister Pending" smoke.lister.pending@example.com +8801700097103 ',"verification_status":"pending"')
S4=$(mk_seller "Smoke Lister Paused" smoke.lister.paused@example.com +8801700097104 ',"status":"inactive"')
ST=$(login +8801700097101); ST2=$(login +8801700097102); ST3=$(login +8801700097103); ST4=$(login +8801700097104)

# reference data created for this run
CAT_INACTIVE=$(body "$(areq POST $BASE/catalog/categories/ '{"type":"product","name":"Smoke Inactive Cat","name_bn":"x","status":"inactive"}')" | py "d['id']")
BRAND=$(body "$(areq POST $BASE/catalog/brands/ '{"name":"Smoke Brand"}')" | py "d['id']")
BRAND_OFF=$(body "$(areq POST $BASE/catalog/brands/ '{"name":"Smoke Brand Off","is_active":false}')" | py "d['id']")
ATTR=$(body "$(areq POST $BASE/catalog/attributes/ '{"name":"Smoke Size"}')" | py "d['id']")
ATTR_OFF=$(body "$(areq POST $BASE/catalog/attributes/ '{"name":"Smoke Off Attr","is_active":false}')" | py "d['id']")
AV1=$(body "$(areq POST $BASE/catalog/attribute-values/ "{\"attribute\":$ATTR,\"name\":\"M\",\"name_bn\":\"এম\"}")" | py "d['id']")
AV2=$(body "$(areq POST $BASE/catalog/attribute-values/ "{\"attribute\":$ATTR,\"name\":\"L\"}")" | py "d['id']")
AV_OFF=$(body "$(areq POST $BASE/catalog/attribute-values/ "{\"attribute\":$ATTR,\"name\":\"XXL\",\"is_active\":false}")" | py "d['id']")
MEAS=$(body "$(curl -s -w '\n%{http_code}' "$BASE/catalog/measurements/?limit=1" -H "Authorization: Bearer $TOKEN")" | py "d['results'][0]['id']")

echo "=== Access ==="
check "no token -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $SL/)"
check "admin token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $SL/ -H "Authorization: Bearer $TOKEN")"
check "buyer token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $SL/ -H "Authorization: Bearer $BT")"
R=$(curl -s -w '\n%{http_code}' $SL/ -H "Authorization: Bearer $ST3")
check "pending (not approved) seller -> 403" 403 "$(code "$R")"
check "...message says not approved" True "$(body "$R" | py "'not approved yet' in d['detail']")"
R=$(curl -s -w '\n%{http_code}' $SL/ -H "Authorization: Bearer $ST4")
check "approved but inactive seller -> 403" 403 "$(code "$R")"
check "...message says inactive" True "$(body "$R" | py "'inactive' in d['detail']")"
check "a not-operating seller cannot create either" 403 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $SL/ -H "Authorization: Bearer $ST3" -H "Content-Type: application/json" -d '{"category":18,"catalog_type":"product","title":"Smoke Nope","description":"d","price":"5"}')"
check "operating seller -> 200" 200 "$(code "$(sreq GET $SL/)")"
check "seller cannot DELETE a listing -> 405" 405 "$(code "$(sreq DELETE $SL/1/)")"

echo "=== Lookups for the listing form ==="
LK="$BASE/seller/lookups"
for l in categories brands measurements attributes; do
  check "lookups/$l as seller -> 200" 200 "$(curl -s -o /dev/null -w '%{http_code}' $LK/$l/ -H "Authorization: Bearer $ST")"
  check "lookups/$l as admin -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $LK/$l/ -H "Authorization: Bearer $TOKEN")"
  check "lookups/$l without a login -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $LK/$l/)"
  check "lookups/$l as a not-operating seller -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $LK/$l/ -H "Authorization: Bearer $ST3")"
done
R=$(curl -s $LK/categories/?type=product -H "Authorization: Bearer $ST")
check "categories: product filter returns only products" True "$(echo "$R" | py "all(c['type']=='product' for c in d['results']) and len(d['results'])>0")"
check "categories: row keys" "id,name,name_bn,parent,slug,sort_order,type" "$(echo "$R" | py "','.join(sorted(d['results'][0].keys()))")"
check "categories: inactive category is not offered" False "$(echo "$R" | py "$CAT_INACTIVE in [c['id'] for c in d['results']]")"
check "categories: service filter" True "$(curl -s "$LK/categories/?type=service" -H "Authorization: Bearer $ST" | py "all(c['type']=='service' for c in d['results'])")"
check "categories: search by name" True "$(curl -s "$LK/categories/?search=electronics" -H "Authorization: Bearer $ST" | py "len(d['results'])>=1")"
R=$(curl -s $LK/brands/ -H "Authorization: Bearer $ST")
check "brands: active brand offered" True "$(echo "$R" | py "$BRAND in [b['id'] for b in d['results']]")"
check "brands: inactive brand hidden" False "$(echo "$R" | py "$BRAND_OFF in [b['id'] for b in d['results']]")"
check "brands: row keys" "id,name,slug" "$(echo "$R" | py "','.join(sorted(d['results'][0].keys()))")"
check "measurements: row keys" "id,name,slug,symbol" "$(curl -s $LK/measurements/ -H "Authorization: Bearer $ST" | py "','.join(sorted(d['results'][0].keys()))")"
R=$(curl -s "$LK/attributes/?search=smoke" -H "Authorization: Bearer $ST")
check "attributes: active attribute with its active values" "Smoke Size L,M" "$(echo "$R" | py "[a for a in d['results'] if a['id']==$ATTR][0]['name']+' '+','.join(sorted(v['name'] for v in [a for a in d['results'] if a['id']==$ATTR][0]['values']))")"
check "attributes: inactive attribute hidden" False "$(echo "$R" | py "$ATTR_OFF in [a['id'] for a in d['results']]")"
check "attributes: inactive value hidden" False "$(echo "$R" | py "$AV_OFF in [v['id'] for a in d['results'] for v in a['values']]")"
check "attributes: value carries name_bn" "এম" "$(echo "$R" | py "[v['name_bn'] for a in d['results'] if a['id']==$ATTR for v in a['values'] if v['name']=='M'][0]")"
check "lookups are read-only (POST -> 405)" 405 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $LK/brands/ -H "Authorization: Bearer $ST" -H 'Content-Type: application/json' -d '{"name":"x"}')"

echo "=== Create: always pending, always mine ==="
R=$(sreq POST $SL/ '{"category":18,"catalog_type":"product","listing_type":"general","title":"Smoke Tee","title_bn":"স্মোক টি-শার্ট","description":"Plain tee","description_bn":"সাধারণ টি-শার্ট","origin":"Bangladesh","origin_bn":"বাংলাদেশ","warranty":"6 months","warranty_bn":"৬ মাস","condition_note":"New","condition_note_bn":"নতুন","price":"500","stock_qty":10}')
check "create (price shortcut)" 201 "$(code "$R")"; L1=$(body "$R" | py "d['id']")
check "status is pending" pending "$(body "$R" | py "d['status']")"
check "requested_at is set" True "$(body "$R" | py "bool(d['requested_at'])")"
check "no seller / buyer / posted_by_role in the seller's view" "None None None" "$(body "$R" | py "(d.get('seller'),d.get('buyer'),d.get('posted_by_role'))" | tr -d "(),'")"
check "no info_change_logs in the seller's view" "None" "$(body "$R" | py "d.get('info_change_logs')")"
check "status history has the creation entry by the seller" "1 pending seller" "$(body "$R" | py "str(len(d['status_change_logs']))+' '+d['status_change_logs'][0]['status']+' '+d['status_change_logs'][0]['creator_type']")"
check "all five Bangla fields of a product saved" "স্মোক টি-শার্ট|সাধারণ টি-শার্ট|বাংলাদেশ|৬ মাস|নতুন" "$(body "$R" | py "'|'.join([d['title_bn'],d['description_bn'],d['origin_bn'],d['warranty_bn'],d['condition_note_bn']])")"
check "price comes from the SKU" "500.00" "$(body "$R" | py "d['price']")"
check "slug generated" smoke-tee "$(body "$R" | py "d['slug']")"
cd "$SERVER_DIR"
uv run manage.py shell -c "
from apps.catalog.models import Listing
l = Listing.objects.get(id=$L1)
print('OWN', l.seller_id == $S1, l.buyer_id, l.posted_by_role, l.creator_type, l.created_by == $S1, l.creator_name)" 2>&1 | grep '^OWN' > "$SCRATCH/own.txt"
check "owner is the logged-in seller, seller_offer, created by the seller" "OWN True None seller_offer seller True Smoke Lister One" "$(cat "$SCRATCH/own.txt")"
R=$(sreq POST $SL/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"general\",\"title\":\"Smoke Sneaky\",\"description\":\"d\",\"price\":\"5\",\"status\":\"approved\",\"seller\":$S2,\"buyer\":4,\"posted_by_role\":\"buyer_request\",\"note\":\"x\",\"requested_at\":\"2000-01-01T00:00:00Z\"}")
check "owner, status and role in the body are ignored" "201 pending" "$(code "$R") $(body "$R" | py "d['status']")"
LS=$(body "$R" | py "d['id']")
uv run manage.py shell -c "
from apps.catalog.models import Listing
l = Listing.objects.get(id=$LS)
print('OWN2', l.seller_id == $S1, l.buyer_id, l.posted_by_role, l.note, l.requested_at.year > 2020)" 2>&1 | grep '^OWN2' > "$SCRATCH/own.txt"
check "...stored as: mine, no buyer, seller_offer, no note, real request time" "OWN2 True None seller_offer None True" "$(cat "$SCRATCH/own.txt")"
check "extra spaces in the title are tidied" "Smoke Spaced Tee" "$(body "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"   Smoke   Spaced  Tee ","description":"d","price":"5"}')" | py "d['title']")"

echo "=== Create: every listing kind through the same endpoint ==="
for kind in used village retail wholesale; do
  check "listing_type=$kind" 201 "$(code "$(sreq POST $SL/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"$kind\",\"title\":\"Smoke Kind $kind\",\"description\":\"d\",\"price\":\"10\"}")")"
done
check "listing_type=brand needs a brand -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","listing_type":"brand","title":"Smoke Kind brand","description":"d","price":"10"}')")"
check "listing_type=brand with a brand" 201 "$(code "$(sreq POST $SL/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"brand\",\"brand\":$BRAND,\"title\":\"Smoke Kind brand\",\"description\":\"d\",\"price\":\"10\"}")")"
check "an inactive brand is refused -> 400" 400 "$(code "$(sreq POST $SL/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"general\",\"brand\":$BRAND_OFF,\"title\":\"Smoke Off Brand\",\"description\":\"d\",\"price\":\"10\"}")")"
R=$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke Cleaning Service","title_bn":"পরিষ্কার সেবা","description":"d","origin":"Bangladesh","price":"300"}')
check "a second product (Bangla title)" 201 "$(code "$R")"; LSV=$(body "$R" | py "d['id']")
check "a service on the product endpoint -> 400 (a service offer is a gig)" 400 "$(code "$(sreq POST $SL/ '{"category":29,"catalog_type":"service","title":"Smoke Cleaning Gig","description":"d","price":"300"}')")"
check "a service-only field on a product -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke Cleaning Days","description":"d","price":"300","delivery_days":2}')")"
R=$(sreq POST $SL/ "{\"category\":18,\"catalog_type\":\"product\",\"listing_type\":\"general\",\"title\":\"Smoke Sized Tee\",\"description\":\"d\",\"measurement\":$MEAS,\"min_order_qty\":2,\"skus\":[{\"sku\":\"SMK-LST-M\",\"price\":\"100\",\"discounted_price\":\"80\",\"stock_qty\":4,\"variants\":[{\"attribute\":$ATTR,\"attribute_value\":$AV1}]},{\"sku\":\"SMK-LST-L\",\"price\":\"120\",\"stock_qty\":2,\"variants\":[{\"attribute\":$ATTR,\"attribute_value\":$AV2}]}],\"price_tiers\":[{\"min_qty\":1,\"max_qty\":9,\"price\":\"100\"},{\"min_qty\":10,\"price\":\"90\"}]}")
check "product with SKU options and price tiers" 201 "$(code "$R")"; L3=$(body "$R" | py "d['id']")
check "two SKUs saved" 2 "$(body "$R" | py "len(d['skus'])")"
check "two price tiers saved" 2 "$(body "$R" | py "len(d['price_tiers'])")"
check "listing price is the cheapest SKU's" "100.00 80.00" "$(body "$R" | py "d['price']+' '+d['discounted_price']")"
check "an inactive attribute value is refused -> 400" 400 "$(code "$(sreq POST $SL/ "{\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Bad Variant\",\"description\":\"d\",\"skus\":[{\"price\":\"1\",\"variants\":[{\"attribute\":$ATTR,\"attribute_value\":$AV_OFF}]}]}")")"
echo "--- validation"
check "no title -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","description":"d","price":"5"}')")"
check "no category -> 400" 400 "$(code "$(sreq POST $SL/ '{"catalog_type":"product","title":"Smoke X1","description":"d","price":"5"}')")"
check "no description -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke X2","price":"5"}')")"
check "no SKU and no price -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke X3","description":"d"}')")"
check "a service category on a product -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":29,"catalog_type":"product","title":"Smoke X4","description":"d","price":"5"}')")"
check "an inactive category -> 400" 400 "$(code "$(sreq POST $SL/ "{\"category\":$CAT_INACTIVE,\"catalog_type\":\"product\",\"title\":\"Smoke X5\",\"description\":\"d\",\"price\":\"5\"}")")"
check "negative price -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke X6","description":"d","price":"-1"}')")"
check "discount above price -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke X7","description":"d","price":"5","discounted_price":"9"}')")"
check "city from another state -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke X8","description":"d","price":"5","state":12,"city":8}')")"
check "unknown catalog_type -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"gadget","title":"Smoke X9","description":"d","price":"5"}')")"
check "a SKU code another listing already uses -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke X10","description":"d","price":"5","sku":"SMK-LST-M"}')")"

echo "=== Unique title per seller ==="
R=$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke Tee","description":"again","price":"5"}')
check "same title -> 400" 400 "$(code "$R")"
check "...message tells the seller to update the existing one" True "$(body "$R" | py "'You already have a listing with this title' in d['title'][0] and '#$L1' in d['title'][0]")"
check "same title in other letter case -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"SMOKE TEE","description":"x","price":"5"}')")"
check "same title with extra spaces -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":" smoke   tee ","description":"x","price":"5"}')")"
check "another seller may use the same title" 201 "$(code "$(s2req POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke Tee","description":"theirs","price":"5"}')")"
LS2=$(body "$(s2req GET $SL/?search=smoke)" | py "d['results'][0]['id']")
check "admin creating for a seller with a title they already have -> 400" 400 "$(code "$(areq POST $AL/ "{\"seller\":$S1,\"posted_by_role\":\"seller_offer\",\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Tee\",\"description\":\"d\",\"price\":\"5\"}")")"
check "...message says the seller already has it" True "$(body "$(areq POST $AL/ "{\"seller\":$S1,\"posted_by_role\":\"seller_offer\",\"category\":18,\"catalog_type\":\"product\",\"title\":\"smoke tee\",\"description\":\"d\",\"price\":\"5\"}")" | py "'This seller already has a listing' in d['title'][0]")"
check "admin listing with no seller may reuse a title" 201 "$(code "$(areq POST $AL/ '{"category":18,"catalog_type":"product","title":"Smoke Tee","description":"admin own","price":"5"}')")"
check "renaming my listing to one I already have -> 400" 400 "$(code "$(sreq PATCH $SL/$L3/ '{"title":"Smoke Tee"}')")"
check "sending my own title again is fine" 200 "$(code "$(sreq PATCH $SL/$L1/ '{"title":"Smoke Tee"}')")"
check "a title freed by an admin delete can be used again" 204 "$(code "$(areq DELETE $AL/$LS/)")"
check "...and the seller creates it again" 201 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke Sneaky","description":"again","price":"5"}')")"
uv run manage.py shell -c "
from django.db import IntegrityError, transaction
from apps.catalog.models import Listing
try:
    with transaction.atomic():
        Listing.objects.create(seller_id=$S1, category_id=18, catalog_type='product', title='SMOKE TEE', slug='smoke-tee-dup', description='x')
    print('DBU allowed')
except IntegrityError:
    print('DBU blocked')" 2>&1 | grep '^DBU' > "$SCRATCH/dbu.txt"
check "the database itself also blocks a duplicate (case-insensitive)" "DBU blocked" "$(cat "$SCRATCH/dbu.txt")"

echo "=== My list, detail and filters ==="
R=$(sreq GET $SL/)
check "list is limit/offset with a count" True "$(body "$R" | py "'count' in d and 'results' in d")"
check "list rows carry the seller's view (no owner fields)" "None None" "$(body "$R" | py "(d['results'][0].get('seller'),d['results'][0].get('buyer'))" | tr -d "(),'")"
check "list row keys" "brand,catalog_type,category,created_at,discounted_price,id,image_url,listing_type,note,price,requested_at,slug,status,title,title_bn,updated_at" "$(body "$R" | py "','.join(sorted(d['results'][0].keys()))")"
TOTAL=$(body "$R" | py "d['count']")
check "I only see my own listings" True "$(body "$(sreq GET "$SL/?limit=100")" | py "all(x['id'] != $LS2 for x in d['results'])")"
check "detail of my listing" 200 "$(code "$(sreq GET $SL/$L1/)")"
check "detail of another seller's listing -> 404" 404 "$(code "$(sreq GET $SL/$LS2/)")"
check "editing another seller's listing -> 404" 404 "$(code "$(sreq PATCH $SL/$LS2/ '{"description":"hacked"}')")"
check "PUT on another seller's listing -> 404" 404 "$(code "$(sreq PUT $SL/$LS2/ '{}')")"
check "an admin-owned listing is not mine either" 404 "$(code "$(sreq GET $SL/$(body "$(areq GET "$AL/?search=admin%20own")" | py "d['results'][0]['id']")/)")"
Q="$SL/?search=smoke"
check "filter status=pending" True "$(body "$(sreq GET "$SL/?status=pending&limit=100")" | py "all(x['status']=='pending' for x in d['results']) and d['count']>0")"
check "filter status=approved (none yet)" 0 "$(body "$(sreq GET "$SL/?status=approved")" | py "d['count']")"
check "filter listing_type=used" 1 "$(body "$(sreq GET "$SL/?listing_type=used")" | py "d['count']")"
check "filter category=29 (a service category: no gigs on the product list)" 0 "$(body "$(sreq GET "$SL/?category=29")" | py "d['count']")"
check "filter brand" 1 "$(body "$(sreq GET "$SL/?brand=$BRAND")" | py "d['count']")"
check "search by title" True "$(body "$(sreq GET "$SL/?search=Cleaning")" | py "d['count']==1 and d['results'][0]['id']==$LSV")"
check "search by Bangla title" True "$(body "$(sreq GET "$SL/?search=%E0%A6%AA%E0%A6%B0%E0%A6%BF%E0%A6%B7%E0%A7%8D%E0%A6%95%E0%A6%BE%E0%A6%B0")" | py "d['count']==1 and d['results'][0]['id']==$LSV")"
check "search by SKU code" True "$(body "$(sreq GET "$SL/?search=SMK-LST-L")" | py "d['count']==1 and d['results'][0]['id']==$L3")"
TODAY=$(date +%F)
check "created_from=today" "$TOTAL" "$(body "$(sreq GET "$SL/?created_from=$TODAY")" | py "d['count']")"
check "created_from=2999-01-01" 0 "$(body "$(sreq GET "$SL/?created_from=2999-01-01")" | py "d['count']")"
check "requested_from=today" "$TOTAL" "$(body "$(sreq GET "$SL/?requested_from=$TODAY")" | py "d['count']")"
check "requested_to=2000-01-01" 0 "$(body "$(sreq GET "$SL/?requested_to=2000-01-01")" | py "d['count']")"
check "ordering=title" True "$(body "$(sreq GET "$SL/?ordering=title&limit=100")" | py "[x['title'] for x in d['results']]==sorted([x['title'] for x in d['results']])")"
check "ordering=-created_at is the default (newest first)" True "$(body "$(sreq GET "$SL/?limit=100")" | py "[x['id'] for x in d['results']]==sorted([x['id'] for x in d['results']],reverse=True)")"
check "limit=2 paginates" 2 "$(body "$(sreq GET "$SL/?limit=2")" | py "len(d['results'])")"
check "the other seller sees only theirs" 1 "$(body "$(s2req GET "$SL/")" | py "d['count']")"

echo "=== Admin: the pending list ==="
AQ="$AL/requests/?search=smoke"
R=$(areq GET "$AQ")
check "pending list 200" 200 "$(code "$R")"
check "cursor shape (next / previous, no count)" "True True False" "$(body "$R" | py "('next' in d, 'previous' in d, 'count' in d)" | tr -d "(),'")"
check "only pending listings" True "$(body "$R" | py "all(x['status']=='pending' for x in d['results']) and len(d['results'])>0")"
check "newest request first" True "$(body "$R" | py "[x['requested_at'] for x in d['results']]==sorted([x['requested_at'] for x in d['results']],reverse=True)")"
check "rows carry requested_at and title_bn" True "$(body "$R" | py "all(x['requested_at'] and 'title_bn' in x for x in d['results'])")"
check "ordering=requested_at is oldest first" True "$(body "$(areq GET "$AQ&ordering=requested_at")" | py "[x['requested_at'] for x in d['results']]==sorted([x['requested_at'] for x in d['results']])")"
check "filter by seller" True "$(body "$(areq GET "$AQ&seller=$S2")" | py "len(d['results'])==1 and d['results'][0]['seller']==$S2")"
check "filter catalog_type=service (a seller's services are gigs, not here)" True "$(body "$(areq GET "$AQ&catalog_type=service")" | py "len(d['results'])==0")"
check "filter requested_from=today" True "$(body "$(areq GET "$AQ&requested_from=$TODAY")" | py "len(d['results'])>0")"
check "filter requested_to=2000-01-01" 0 "$(body "$(areq GET "$AQ&requested_to=2000-01-01")" | py "len(d['results'])")"
P1=$(areq GET "$AQ&limit=2")
check "limit=2 -> 2 rows and a next link" True "$(body "$P1" | py "len(d['results'])==2 and bool(d['next'])")"
NEXT=$(body "$P1" | py "d['next']")
check "following next works" 200 "$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" "$NEXT")"
check "a seller token on the pending list -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' "$AL/requests/" -H "Authorization: Bearer $ST")"
check "no token -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' "$AL/requests/")"
check "pending count for a menu badge (normal list)" True "$(body "$(areq GET "$AL/?status=pending&limit=1")" | py "d['count']>=1")"
R=$(areq GET "$AL/$L1/")
check "admin detail shows owner, status history and the info log" True "$(body "$R" | py "d['seller']==$S1 and d['posted_by_role']=='seller_offer' and 'info_change_logs' in d and len(d['status_change_logs'])==1")"

echo "=== Approve: the seller keeps editing freely ==="
check "admin approves" 200 "$(code "$(areq PATCH $AL/$L1/ '{"status":"approved"}')")"
check "it left the pending list" False "$(body "$(areq GET "$AL/requests/?search=Smoke%20Tee&limit=100")" | py "$L1 in [x['id'] for x in d['results']]")"
R=$(sreq GET $SL/$L1/)
check "the seller sees approved" approved "$(body "$R" | py "d['status']")"
REQ0=$(body "$R" | py "d['requested_at']")
R=$(sreq PATCH $SL/$L1/ '{"description":"Plain cotton tee, new wording","description_bn":"নতুন বর্ণনা","title_bn":"নতুন নাম","note":"please ignore"}')
check "seller edits an approved listing (content)" 200 "$(code "$R")"
check "...it stays approved" approved "$(body "$R" | py "d['status']")"
check "...requested_at unchanged" "$REQ0" "$(body "$R" | py "d['requested_at']")"
check "...no new status history entry (still: pending, approved)" 2 "$(body "$R" | py "len(d['status_change_logs'])")"
check "...the note sent on an approved listing is ignored" None "$(body "$R" | py "d['note']")"
SKU1=$(body "$R" | py "d['skus'][0]['id']")
R=$(sreq PATCH $SL/$L1/ "{\"skus\":[{\"id\":$SKU1,\"price\":\"550\",\"discounted_price\":\"500\"}]}")
check "seller changes a SKU price on an approved listing" 200 "$(code "$R")"
check "...still approved" approved "$(body "$R" | py "d['status']")"
check "...new price shows" "550.00" "$(body "$R" | py "d['price']")"
R=$(sreq PATCH $SL/$L1/ "{\"skus\":[{\"id\":$SKU1,\"stock_qty\":99}]}")
check "seller changes only the stock" 200 "$(code "$R")"
check "a seller cannot set status (body ignored)" approved "$(body "$(sreq PATCH $SL/$L1/ '{"status":"rejected","note":"self reject"}')" | py "d['status']")"
sreq PATCH $SL/$L1/ "{\"seller\":$S2}" >/dev/null
check "a seller cannot move a listing to another owner (body ignored)" $S1 "$(areq GET $AL/$L1/ | sed '$d' | py "d['seller']")"

echo "=== Info change log (admin sees it) ==="
D=$(body "$(areq GET $AL/$L1/)")
check "edits were logged: content, then price (stock not logged)" 2 "$(echo "$D" | py "len(d['info_change_logs'])")"
check "newest row: skus changed by the seller" "['skus'] seller Smoke Lister One" "$(echo "$D" | py "str(d['info_change_logs'][0]['changed_fields'])+' '+d['info_change_logs'][0]['creator_type']+' '+d['info_change_logs'][0]['creator_name']")"
check "price before and after" "500.00 -> 550.00" "$(echo "$D" | py "d['info_change_logs'][0]['previous_data']['skus'][0]['price']+' -> '+d['info_change_logs'][0]['new_data']['skus'][0]['price']")"
check "SKU snapshot has no stock" False "$(echo "$D" | py "'stock_qty' in d['info_change_logs'][0]['previous_data']['skus'][0]")"
check "content row lists the changed fields" "['description', 'description_bn', 'title_bn']" "$(echo "$D" | py "sorted(d['info_change_logs'][1]['changed_fields'])")"
check "previous and new have the same keys" True "$(echo "$D" | py "all(set(l['previous_data'])==set(l['new_data']) for l in d['info_change_logs'])")"
check "before / after text" "Plain tee -> Plain cotton tee, new wording" "$(echo "$D" | py "d['info_change_logs'][1]['previous_data']['description']+' -> '+d['info_change_logs'][1]['new_data']['description']")"
check "Bangla before / after" "স্মোক টি-শার্ট -> নতুন নাম" "$(echo "$D" | py "d['info_change_logs'][1]['previous_data']['title_bn']+' -> '+d['info_change_logs'][1]['new_data']['title_bn']")"
check "stock-only edit wrote no row" 2 "$(echo "$D" | py "len(d['info_change_logs'])")"
check "sending the same values writes no row" 2 "$(sreq PATCH $SL/$L1/ '{"description":"Plain cotton tee, new wording"}' >/dev/null; areq GET $AL/$L1/ | sed '$d' | py "len(d['info_change_logs'])")"
R=$(sreq PATCH $SL/$L1/ "{\"brand\":$BRAND,\"price_tiers\":[{\"min_qty\":1,\"max_qty\":4,\"price\":\"500\"},{\"min_qty\":5,\"price\":\"450\"}]}")
D=$(body "$(areq GET $AL/$L1/)")
check "brand and price tiers are logged" "['brand', 'price_tiers']" "$(echo "$D" | py "sorted(d['info_change_logs'][0]['changed_fields'])")"
check "brand logged as id and name" "None -> Smoke Brand" "$(echo "$D" | py "str(d['info_change_logs'][0]['previous_data']['brand'])+' -> '+d['info_change_logs'][0]['new_data']['brand']['name']")"
check "an admin edit is logged with the admin's name" 200 "$(code "$(areq PATCH $AL/$L1/ '{"origin":"Dhaka"}')")"
check "...creator_type admin" "admin" "$(areq GET $AL/$L1/ | sed '$d' | py "d['info_change_logs'][0]['creator_type']")"
check "a status change is not in the info log" True "$(areq GET $AL/$L1/ | sed '$d' | py "all('status' not in l['changed_fields'] for l in d['info_change_logs'])")"

echo "=== Media: add, and delete removes the file ==="
R=$(curl -s -w '\n%{http_code}' -X PATCH $SL/$L1/ -H "Authorization: Bearer $ST" -F "media_file=@$SCRATCH/l1.png;type=$PNG" -F "media_file=@$SCRATCH/l2.png;type=$PNG")
check "upload two pictures" 200 "$(code "$R")"
check "two media rows" 2 "$(body "$R" | py "len(d['media'])")"
M1=$(body "$R" | py "d['media'][0]['id']"); MP1=$(body "$R" | py "d['media'][0]['media_path']"); MP2=$(body "$R" | py "d['media'][1]['media_path']")
check "files are stored" "True True" "$(fx "$MP1" "$MP2")"
check "adding media is logged" True "$(areq GET $AL/$L1/ | sed '$d' | py "'media' in d['info_change_logs'][0]['changed_fields']")"
R=$(curl -s -w '\n%{http_code}' -X PATCH $SL/$L1/ -H "Authorization: Bearer $ST" -F "media_delete_ids=$M1")
check "delete one picture" 200 "$(code "$R")"
check "its file is removed from storage, the other stays" "False True" "$(fx "$MP1" "$MP2")"
check "a text file as listing media -> 400" 400 "$(code "$(curl -s -w '\n%{http_code}' -X PATCH $SL/$L1/ -H "Authorization: Bearer $ST" -F "media_file=@$SCRATCH/note.txt;type=text/plain")")"
check "an .html file with an image type -> 400" 400 "$(code "$(curl -s -w '\n%{http_code}' -X PATCH $SL/$L1/ -H "Authorization: Bearer $ST" -F "media_file=@$SCRATCH/l1.png;filename=x.html;type=image/png")")"
check "an .svg file -> 400" 400 "$(code "$(curl -s -w '\n%{http_code}' -X PATCH $SL/$L1/ -H "Authorization: Bearer $ST" -F "media_file=@$SCRATCH/l1.png;filename=x.svg;type=image/svg+xml")")"
head -c 11000000 /dev/zero > "$SCRATCH/big.png"
check "a file over 10 MB -> 400" 400 "$(code "$(curl -s -w '\n%{http_code}' -X PATCH $SL/$L1/ -H "Authorization: Bearer $ST" -F "media_file=@$SCRATCH/big.png;type=image/png")")"
MANYF=(); for i in 1 2 3 4 5 6 7 8 9 10 11; do MANYF+=(-F "media_file=@$SCRATCH/l1.png;type=$PNG"); done
check "11 files in one request -> 400" 400 "$(code "$(curl -s -w '\n%{http_code}' -X PATCH $SL/$L1/ -H "Authorization: Bearer $ST" "${MANYF[@]}")")"
printf '%%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%%%EOF\n' > "$SCRATCH/doc.pdf"
check "a PDF is accepted" 200 "$(code "$(curl -s -w '\n%{http_code}' -X PATCH $SL/$L1/ -H "Authorization: Bearer $ST" -F "media_file=@$SCRATCH/doc.pdf;type=application/pdf")")"
check "can't delete another listing's media" True "$(curl -s -X PATCH $SL/$L3/ -H "Authorization: Bearer $ST" -F "media_delete_ids=$M1" | py "len(d['media'])==0")"

echo "=== Details from the code review ==="
R=$(sreq GET $SL/$L1/)
check "the seller's status history shows who (seller / admin) but not which admin" "created_at,creator_type,id,note,status" "$(body "$R" | py "','.join(sorted(d['status_change_logs'][0].keys()))")"
check "the admin still sees the admin's name" True "$(areq GET $AL/$L1/ | sed '$d' | py "any(l.get('creator_name') for l in d['status_change_logs'])")"
sreq PATCH $SL/$LSV/ '{"origin":"Nepal"}' >/dev/null
N1=$(areq GET $AL/$LSV/ | sed '$d' | py "len(d['info_change_logs'])")
sreq PATCH $SL/$LSV/ '{"origin":"Nepal"}' >/dev/null
check "the same value sent again writes no log row" "$N1" "$(areq GET $AL/$LSV/ | sed '$d' | py "len(d['info_change_logs'])")"
check "a really different value is logged" True "$(sreq PATCH $SL/$LSV/ '{"origin":"Bhutan"}' >/dev/null; areq GET $AL/$LSV/ | sed '$d' | py "'origin' in d['info_change_logs'][0]['changed_fields']")"
check "the same SKU code twice in one request -> 400, not a crash" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke Dup Codes","description":"d","skus":[{"sku":"SMK-DUP-1","price":"5"},{"sku":"SMK-DUP-1","price":"6"}]}')")"
R=$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"পণ্য","description":"d","price":"5"}')
check "a title with only Bangla letters still saves, with a usable slug" "201 True" "$(code "$R") $(body "$R" | py "d['slug'].startswith('listing')")"
SLUG0=$(body "$(sreq GET $SL/$L1/)" | py "d['slug']")
sreq PATCH $SL/$L1/ '{"title":"SMOKE TEE"}' >/dev/null
check "a case-only rename keeps the slug" "$SLUG0" "$(body "$(sreq GET $SL/$L1/)" | py "d['slug']")"
R=$(areq POST $AL/ "{\"seller\":$S1,\"posted_by_role\":\"seller_offer\",\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Admin Draft\",\"description\":\"d\",\"price\":\"5\",\"status\":\"draft\"}")
LDR=$(body "$R" | py "d['id']")
check "an admin-made draft..." draft "$(body "$R" | py "d['status']")"
check "...is submitted when the seller saves it" pending "$(body "$(sreq PATCH $SL/$LDR/ '{"description":"ready"}')" | py "d['status']")"
cd "$SERVER_DIR"
uv run manage.py shell -c "
from django.db import IntegrityError, transaction
from apps.catalog.models import Listing
try:
    with transaction.atomic():
        Listing.objects.create(category_id=18, catalog_type='product', title='Smoke Pending No Time', slug='smoke-pending-no-time', description='x', status='pending')
    print('PEND allowed')
except IntegrityError:
    print('PEND blocked')" 2>&1 | grep '^PEND' > "$SCRATCH/pend.txt"
check "the database refuses a pending listing with no request time" "PEND blocked" "$(cat "$SCRATCH/pend.txt")"

echo "=== Reject, then the seller fixes it (no Resubmit button) ==="
check "admin rejects with a note" 200 "$(code "$(areq PATCH $AL/$L3/ '{"status":"rejected","note":"Photos are missing"}')")"
R=$(sreq GET $SL/$L3/)
check "seller sees rejected and the reason" "rejected Photos are missing" "$(body "$R" | py "d['status']+' '+d['note']")"
REQ1=$(body "$R" | py "d['requested_at']")
check "the rejected title is still taken: creating it again -> 400" 400 "$(code "$(sreq POST $SL/ '{"category":18,"catalog_type":"product","title":"Smoke Sized Tee","description":"again","price":"5"}')")"
sleep 1
R=$(sreq PATCH $SL/$L3/ '{"description":"Now with a better description","note":"Added a clearer description"}')
check "any save by the seller resubmits" 200 "$(code "$R")"
check "...status is pending again" pending "$(body "$R" | py "d['status']")"
check "...requested_at moved forward" True "$(body "$R" | py "d['requested_at'] > '$REQ1'")"
check "...the note is now the seller's message" "Added a clearer description" "$(body "$R" | py "d['note']")"
check "...history: pending, rejected, pending (last by the seller)" "pending,rejected,pending seller" "$(body "$R" | py "','.join(l['status'] for l in d['status_change_logs'])+' '+d['status_change_logs'][0]['creator_type']")"
check "...the rejection reason is kept in the history" "Photos are missing" "$(body "$R" | py "d['status_change_logs'][1]['note']")"
check "...it is back in the admin's pending list" True "$(body "$(areq GET "$AL/requests/?search=Sized&limit=100")" | py "$L3 in [x['id'] for x in d['results']]")"
check "...at the top (newest request)" $L3 "$(body "$(areq GET "$AL/requests/?search=smoke&limit=100")" | py "d['results'][0]['id']")"
R=$(sreq PATCH $SL/$L3/ '{"description":"Edited while pending"}')
check "editing a pending listing keeps it pending" pending "$(body "$R" | py "d['status']")"
check "...and does not touch requested_at" True "$(body "$R" | py "d['requested_at']=='$(body "$(sreq GET $SL/$L3/)" | py "d['requested_at']")'")"
check "...history still 3 entries" 3 "$(body "$R" | py "len(d['status_change_logs'])")"
echo "--- changes requested"
check "admin requests changes" 200 "$(code "$(areq PATCH $AL/$L3/ '{"status":"changes_requested","note":"Add a size chart"}')")"
check "an EMPTY save by the seller also resubmits" pending "$(body "$(sreq PATCH $SL/$L3/ '{}')" | py "d['status']")"
check "...with no message the note is cleared" None "$(body "$(sreq GET $SL/$L3/)" | py "d['note']")"
areq PATCH $AL/$L3/ '{"status":"rejected","note":"No"}' >/dev/null
check "a full PUT by the seller also resubmits a rejected listing" "200 pending" "$(R=$(sreq PUT $SL/$L3/ "{\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Sized Tee\",\"description\":\"Full form\"}"); echo "$(code "$R") $(body "$R" | py "d['status']")")"
echo "--- the info log kept the seller's fixes"
D=$(body "$(areq GET $AL/$L3/)")
check "description fix by the seller is in the log" True "$(echo "$D" | py "any('description' in l['changed_fields'] and l['creator_type']=='seller' for l in d['info_change_logs'])")"

echo "=== Admin creates on behalf: approved at once ==="
R=$(areq POST $AL/ "{\"seller\":$S2,\"posted_by_role\":\"seller_offer\",\"category\":18,\"catalog_type\":\"product\",\"title\":\"Smoke Admin Made\",\"title_bn\":\"অ্যাডমিন\",\"description\":\"d\",\"price\":\"5\"}")
check "admin creates for a seller" 201 "$(code "$R")"; LA=$(body "$R" | py "d['id']")
check "approved by default" approved "$(body "$R" | py "d['status']")"
check "no requested_at (never waited)" None "$(body "$R" | py "d['requested_at']")"
check "the seller sees it in their list as approved" approved "$(body "$(s2req GET $SL/$LA/)" | py "d['status']")"
check "...and can edit it" 200 "$(code "$(s2req PATCH $SL/$LA/ '{"description":"Seller edit"}')")"
check "...it stays approved" approved "$(body "$(s2req GET $SL/$LA/)" | py "d['status']")"
check "admin can still change the owner" 200 "$(code "$(areq PATCH $AL/$LA/ "{\"seller\":$S1}")")"
check "...the owner change is logged" True "$(areq GET $AL/$LA/ | sed '$d' | py "'seller' in d['info_change_logs'][0]['changed_fields']")"
check "...and it is no longer in the old owner's list" 404 "$(code "$(s2req GET $SL/$LA/)")"
check "admin explicit status=pending on create waits in the list" True "$(body "$(areq POST $AL/ '{"category":18,"catalog_type":"product","title":"Smoke Admin Pending","description":"d","price":"5","status":"pending"}')" | py "bool(d['requested_at'])")"
echo "--- bulk moderation still works on seller listings"
R=$(areq POST $AL/bulk-moderate/ "{\"listing_ids\":[$LS2],\"status\":\"approved\"}")
check "bulk approve" 200 "$(code "$R")"
check "...the other seller sees it approved" approved "$(body "$(s2req GET $SL/$LS2/)" | py "d['status']")"

echo "=== Admin list and detail carry the new fields ==="
R=$(areq GET "$AL/?search=Smoke&limit=100")
check "admin list rows have title_bn and requested_at" True "$(body "$R" | py "all('title_bn' in x and 'requested_at' in x for x in d['results'])")"
check "admin search by Bangla title" True "$(body "$(areq GET "$AL/?search=%E0%A6%AA%E0%A6%B0%E0%A6%BF%E0%A6%B7%E0%A7%8D%E0%A6%95%E0%A6%BE%E0%A6%B0")" | py "d['count']>=1")"
check "admin filter requested_from today" True "$(body "$(areq GET "$AL/?requested_from=$TODAY&search=Smoke")" | py "d['count']>0")"
check "admin filter created_to far past" 0 "$(body "$(areq GET "$AL/?created_to=2000-01-01&search=Smoke")" | py "d['count']")"

echo
echo "RESULT: $PASS passed, $FAIL failed"
