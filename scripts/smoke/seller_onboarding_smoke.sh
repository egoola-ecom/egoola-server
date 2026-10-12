#!/usr/bin/env bash
# Seller self-registration (KYC documents) and the admin "Seller Request" queue.
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
rlen() { python -c "import sys,json;print(len(json.load(sys.stdin)['results']))" 2>/dev/null; }
names() { python -c "import sys,json;print(','.join(r['name'].replace('Smoke Reg ','') for r in json.load(sys.stdin)['results']))" 2>/dev/null; }
Q="/accounts/sellers/requests/?search=Smoke%20Reg"

# --- test files ---------------------------------------------------------
cp "$SCRATCH/t.png" "$SCRATCH/nid1.png"
cp "$SCRATCH/t.png" "$SCRATCH/nid2.png"
cp "$SCRATCH/t.png" "$SCRATCH/cert.png"
printf '%%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%%%EOF\n' > "$SCRATCH/nid.pdf"
echo "just text" > "$SCRATCH/note.txt"
head -c 6000000 /dev/zero > "$SCRATCH/big.png"
PNG="image/png"

# reg_with [key=value | -key]... [-- curl-args...]
# A valid registration form (unique email/phone each call). `key=value` replaces
# a field, `-key` drops it. Everything after `--` is passed to curl (files).
reg_with() {
  declare -A F=([name]="Smoke Reg Probe" [password]='Sell@12345' [present_address]='House 1, Road 2, Feni'
                [permanent_address]='Village X, Feni' [country]=126 [state]=13 [city]=8)
  F[email]="smoke.reg.probe.$RANDOM$RANDOM@example.com"
  F[phone]="+88017$RANDOM$RANDOM"
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    case "$1" in -*) unset "F[${1#-}]" ;; *) F[${1%%=*}]="${1#*=}" ;; esac
    shift
  done
  [ "${1:-}" == "--" ] && shift
  local args=()
  for k in "${!F[@]}"; do args+=(--form-string "$k=${F[$k]}"); done
  curl -s -w '\n%{http_code}' -X POST "$BASE/auth/seller/register/" "${args[@]}" "$@"
}
NID=(-F media_for=nid -F "media_file=@$SCRATCH/nid1.png;type=$PNG")

TOKEN=$(curl -s -X POST "$BASE/auth/admin/login/" -H "Content-Type: application/json" -d '{"email":"test.admin@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
AUTH="Authorization: Bearer $TOKEN"
[ -n "$TOKEN" ] && echo "OK   admin login" && PASS=$((PASS+1))

echo "=== Register: happy paths (no login needed) ==="
R=$(reg_with name="Smoke Reg One" email=smoke.reg.one@example.com phone=+8801700091001 -- "${NID[@]}")
check "minimal registration (1 NID image)" 201 "$(code "$R")"; S1=$(body "$R" | jget "['id']")
check "verification_status is unverified" unverified "$(body "$R" | jget "['verification_status']")"
check "status is inactive" inactive "$(body "$R" | jget "['status']")"
check "is_seller_request is true" True "$(body "$R" | jget "['is_seller_request']")"
check "password not returned" "None" "$(body "$R" | jget ".get('password')")"
check "no token returned" "None" "$(body "$R" | jget ".get('access')")"
check "message returned" True "$(body "$R" | python -c "import sys,json;print('review' in json.load(sys.stdin)['message'])")"

INFO='{"business_type":"Retail","main_product":"Shoes","owner_name":"Smoke Two","employees_range":"1-10","annual_revenue":"< $50,000","established_year":"2020","country":126,"state":13,"city":8}'
R=$(reg_with name="Smoke Reg Two" email=smoke.reg.two@example.com phone=+8801700091002 -- \
  -F media_for=nid -F "media_file=@$SCRATCH/nid.pdf;type=application/pdf" \
  -F media_for=certificate -F "media_file=@$SCRATCH/cert.png;type=$PNG" \
  -F "profile_pic=@$SCRATCH/t.png;type=$PNG" --form-string "info=$INFO")
check "full registration (PDF NID + certificate + photo + business profile)" 201 "$(code "$R")"; S2=$(body "$R" | jget "['id']")

R=$(reg_with name="Smoke Reg Three" email=smoke.reg.three@example.com phone=+8801700091003 -- \
  -F media_for=nid -F "media_file=@$SCRATCH/nid1.png;type=$PNG" -F media_for=nid -F "media_file=@$SCRATCH/nid2.png;type=$PNG")
check "two NID files (front and back)" 201 "$(code "$R")"; S3=$(body "$R" | jget "['id']")
R=$(reg_with name="Smoke Reg Four" email=smoke.reg.four@example.com phone=+8801700091004 -- "${NID[@]}")
check "fourth registration" 201 "$(code "$R")"; S4=$(body "$R" | jget "['id']")
R=$(reg_with name="Smoke Reg Five" email=smoke.reg.five@example.com phone=+8801700091005 -- "${NID[@]}" -H "Authorization: Bearer not-a-real-token")
check "a bad Authorization header does not block registering" 201 "$(code "$R")"; S5=$(body "$R" | jget "['id']")

echo "=== Register: client cannot choose the account state ==="
R=$(reg_with name="Smoke Reg Six" email=smoke.reg.six@example.com phone=+8801700091006 status=active verification_status=verified is_seller_request=false -- "${NID[@]}")
check "status/verification/flag in the form are ignored" 201 "$(code "$R")"; S6=$(body "$R" | jget "['id']")
check "still inactive" inactive "$(body "$R" | jget "['status']")"
check "still unverified" unverified "$(body "$R" | jget "['verification_status']")"
check "flag still true" True "$(body "$R" | jget "['is_seller_request']")"

echo "=== Register: required fields ==="
for f in name email phone password present_address permanent_address country state city; do
  check "missing $f -> 400" 400 "$(code "$(reg_with -$f -- "${NID[@]}")")"
done
check "blank name -> 400" 400 "$(code "$(reg_with name= -- "${NID[@]}")")"
check "blank present_address -> 400" 400 "$(code "$(reg_with present_address= -- "${NID[@]}")")"
check "bad email -> 400" 400 "$(code "$(reg_with email=not-an-email -- "${NID[@]}")")"
check "short password -> 400" 400 "$(code "$(reg_with password=abc1 -- "${NID[@]}")")"
check "common password -> 400" 400 "$(code "$(reg_with password=password123 -- "${NID[@]}")")"
check "all-numeric password -> 400" 400 "$(code "$(reg_with password=84930274619 -- "${NID[@]}")")"

echo "=== Register: duplicates and location ==="
check "duplicate email -> 400" 400 "$(code "$(reg_with email=smoke.reg.one@example.com -- "${NID[@]}")")"
check "duplicate email, different case -> 400" 400 "$(code "$(reg_with email=SMOKE.REG.ONE@example.com -- "${NID[@]}")")"
check "duplicate phone -> 400" 400 "$(code "$(reg_with phone=+8801700091001 -- "${NID[@]}")")"
check "state not in country -> 400" 400 "$(code "$(reg_with country=127 -- "${NID[@]}")")"
check "city not in state -> 400" 400 "$(code "$(reg_with state=12 -- "${NID[@]}")")"
check "unknown country id -> 400" 400 "$(code "$(reg_with country=999999 -- "${NID[@]}")")"

echo "=== Register: documents ==="
check "no document at all -> 400" 400 "$(code "$(reg_with)")"
check "media_for without a file -> 400" 400 "$(code "$(reg_with -- -F media_for=nid)")"
check "file without media_for -> 400" 400 "$(code "$(reg_with -- -F "media_file=@$SCRATCH/nid1.png;type=$PNG")")"
check "certificate only (no NID) -> 400" 400 "$(code "$(reg_with -- -F media_for=certificate -F "media_file=@$SCRATCH/cert.png;type=$PNG")")"
check "gallery_image is not allowed at registration -> 400" 400 "$(code "$(reg_with -- "${NID[@]}" -F media_for=gallery_image -F "media_file=@$SCRATCH/cert.png;type=$PNG")")"
check "text file as NID -> 400" 400 "$(code "$(reg_with -- -F media_for=nid -F "media_file=@$SCRATCH/note.txt;type=text/plain")")"
check "text bytes named .png with text type -> 400" 400 "$(code "$(reg_with -- -F media_for=nid -F "media_file=@$SCRATCH/note.txt;filename=nid.png;type=text/plain")")"
check "png bytes with .exe name -> 400" 400 "$(code "$(reg_with -- -F media_for=nid -F "media_file=@$SCRATCH/nid1.png;filename=nid.exe;type=$PNG")")"
check "file over 5 MB -> 400" 400 "$(code "$(reg_with -- -F media_for=nid -F "media_file=@$SCRATCH/big.png;type=$PNG")")"
MANY=(); for i in 1 2 3 4 5 6 7 8 9 10 11; do MANY+=(-F media_for=nid -F "media_file=@$SCRATCH/nid1.png;type=$PNG"); done
check "11 documents -> 400" 400 "$(code "$(reg_with -- "${MANY[@]}")")"
check "bad profile photo -> 400" 400 "$(code "$(reg_with -- "${NID[@]}" -F "profile_pic=@$SCRATCH/note.txt;type=image/png")")"

echo "=== Register: business profile is optional but must be complete ==="
check "incomplete business profile -> 400" 400 "$(code "$(reg_with 'info={"business_type":"Retail"}' -- "${NID[@]}")")"
check "business profile with mismatched city -> 400" 400 "$(code "$(reg_with -- "${NID[@]}" --form-string 'info={"business_type":"Retail","main_product":"x","owner_name":"x","employees_range":"1-10","annual_revenue":"x","established_year":"2020","state":12,"city":8}')")"
check "info that is not JSON -> 400" 400 "$(code "$(reg_with -- "${NID[@]}" --form-string 'info=not json')")"

echo "=== Failed registrations leave nothing behind ==="
check "no 'Smoke Reg Probe' seller exists" 0 "$(body "$(req GET "/accounts/sellers/?search=Smoke%20Reg%20Probe")" | cnt)"

echo "=== A seller who is not approved yet can log in (profile only) ==="
R=$(curl -s -w '\n%{http_code}' -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"+8801700091001","password":"Sell@12345"}')
check "pending seller login -> 200" 200 "$(code "$R")"
check "login says not approved" "unverified inactive False" "$(body "$R" | python -c "import sys,json;d=json.load(sys.stdin);print(d['verification_status'],d['status'],d['can_operate'])")"
check "login gives a token" True "$(body "$R" | python -c "import sys,json;print(bool(json.load(sys.stdin)['access']))")"
check "wrong password -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"+8801700091001","password":"Wrong@12345"}')"

echo "=== Seller Request queue: basics ==="
R=$(req GET "$Q")
check "queue returns 200" 200 "$(code "$R")"
check "queue holds the 6 requests" 6 "$(body "$R" | rlen)"
check "cursor response has no count" "None" "$(body "$R" | jget ".get('count')")"
check "cursor response has next key" True "$(body "$R" | python -c "import sys,json;print('next' in json.load(sys.stdin))")"
check "row has is_seller_request" True "$(body "$R" | jget "['results'][0]['is_seller_request']")"
check "row has created_at" True "$(body "$R" | python -c "import sys,json;print(bool(json.load(sys.stdin)['results'][0]['created_at']))")"
check "row has no password" "None" "$(body "$R" | jget "['results'][0].get('password')")"
check "default order is newest first" "Six,Five,Four,Three,Two,One" "$(body "$R" | names)"
check "ordering=created_at is oldest first" "One,Two,Three,Four,Five,Six" "$(body "$(req GET "$Q&ordering=created_at")" | names)"
check "ordering=name" "Five,Four,One,Six,Three,Two" "$(body "$(req GET "$Q&ordering=name")" | names)"
check "ordering=-name" "Two,Three,Six,One,Four,Five" "$(body "$(req GET "$Q&ordering=-name")" | names)"
check "unknown ordering falls back to newest first" "Six,Five,Four,Three,Two,One" "$(body "$(req GET "$Q&ordering=wallet_balance")" | names)"

echo "=== Seller Request queue: cursor paging ==="
P1=$(req GET "$Q&limit=4")
check "page 1 has 4 rows" 4 "$(body "$P1" | rlen)"
check "page 1 first rows" "Six,Five,Four,Three" "$(body "$P1" | names)"
check "page 1 has a next link" True "$(body "$P1" | python -c "import sys,json;print(bool(json.load(sys.stdin)['next']))")"
check "page 1 has no previous link" "None" "$(body "$P1" | jget "['previous']")"
NEXT=$(body "$P1" | jget "['next']")
P2=$(curl -s -w '\n%{http_code}' -H "$AUTH" "$NEXT")
check "page 2 returns 200" 200 "$(code "$P2")"
check "page 2 continues where page 1 stopped" "Two,One" "$(body "$P2" | names)"
check "page 2 has no next link" "None" "$(body "$P2" | jget "['next']")"
PREV=$(body "$P2" | jget "['previous']")
P1B=$(curl -s -H "$AUTH" "$PREV")
check "previous link returns to page 1" "Six,Five,Four,Three" "$(echo "$P1B" | names)"
check "limit=1 returns 1 row" 1 "$(body "$(req GET "$Q&limit=1")" | rlen)"
check "limit above max is capped (no error)" 200 "$(code "$(req GET "$Q&limit=5000")")"
check "garbage cursor -> 404" 404 "$(code "$(req GET "$Q&cursor=garbage")")"
WALK=$(python - "$BASE" "$TOKEN" <<'PY'
import json, sys, urllib.parse, urllib.request
base, token = sys.argv[1], sys.argv[2]
url = base + "/accounts/sellers/requests/?search=" + urllib.parse.quote("Smoke Reg") + "&limit=1"
seen = []
while url:
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    data = json.load(urllib.request.urlopen(request))
    seen += [row["id"] for row in data["results"]]
    url = data["next"]
print(len(seen), len(set(seen)), seen == sorted(seen, reverse=True))
PY
)
check "walking limit=1 pages visits every request once, newest first" "6 6 True" "$WALK"

echo "=== Seller Request queue: filters ==="
check "status=inactive" 6 "$(body "$(req GET "$Q&status=inactive")" | rlen)"
check "status=active" 0 "$(body "$(req GET "$Q&status=active")" | rlen)"
check "status__in=inactive,active" 6 "$(body "$(req GET "$Q&status__in=inactive,active")" | rlen)"
check "verification_status=unverified" 6 "$(body "$(req GET "$Q&verification_status=unverified")" | rlen)"
check "verification_status=verified" 0 "$(body "$(req GET "$Q&verification_status=verified")" | rlen)"
check "verification_status__in=unverified,pending" 6 "$(body "$(req GET "$Q&verification_status__in=unverified,pending")" | rlen)"
check "has_business_profile=true" Two "$(body "$(req GET "$Q&has_business_profile=true")" | names)"
check "has_business_profile=false" 5 "$(body "$(req GET "$Q&has_business_profile=false")" | rlen)"
check "business_type=retail (case-insensitive)" Two "$(body "$(req GET "$Q&business_type=retail")" | names)"
check "business_type=wholesale" "" "$(body "$(req GET "$Q&business_type=wholesale")" | names)"
check "creator_type=seller" 6 "$(body "$(req GET "$Q&creator_type=seller")" | rlen)"
check "creator_type=admin" 0 "$(body "$(req GET "$Q&creator_type=admin")" | rlen)"
check "country=126" 6 "$(body "$(req GET "$Q&country=126")" | rlen)"
check "country=127" 0 "$(body "$(req GET "$Q&country=127")" | rlen)"
check "state=13" 6 "$(body "$(req GET "$Q&state=13")" | rlen)"
check "state=12" 0 "$(body "$(req GET "$Q&state=12")" | rlen)"
check "city=8" 6 "$(body "$(req GET "$Q&city=8")" | rlen)"
check "email_verified=false" 6 "$(body "$(req GET "$Q&email_verified=false")" | rlen)"
check "email_verified=true" 0 "$(body "$(req GET "$Q&email_verified=true")" | rlen)"
check "phone_verified=false" 6 "$(body "$(req GET "$Q&phone_verified=false")" | rlen)"
TODAY=$(date +%F)
check "created_from=today" 6 "$(body "$(req GET "$Q&created_from=$TODAY")" | rlen)"
check "created_from=2999-01-01" 0 "$(body "$(req GET "$Q&created_from=2999-01-01")" | rlen)"
check "created_to=2000-01-01" 0 "$(body "$(req GET "$Q&created_to=2000-01-01")" | rlen)"
check "created_from+created_to=today" 6 "$(body "$(req GET "$Q&created_from=$TODAY&created_to=$TODAY")" | rlen)"
check "search by phone" Three "$(body "$(req GET "/accounts/sellers/requests/?search=%2B8801700091003")" | names)"
check "search by email" Four "$(body "$(req GET "/accounts/sellers/requests/?search=smoke.reg.four")" | names)"
check "filters combine (verification_status + has_business_profile)" Two "$(body "$(req GET "$Q&verification_status=unverified&has_business_profile=true")" | names)"
check "is_seller_request=false inside the queue is empty" 0 "$(body "$(req GET "$Q&is_seller_request=false")" | rlen)"

echo "=== Normal seller list shows the flag too ==="
L="/accounts/sellers/?search=Smoke%20Reg"
check "list: is_seller_request=true" 6 "$(body "$(req GET "$L&is_seller_request=true")" | cnt)"
check "list: is_seller_request=false" 0 "$(body "$(req GET "$L&is_seller_request=false")" | cnt)"
check "list row has is_seller_request" True "$(body "$(req GET "$L")" | jget "['results'][0]['is_seller_request']")"
check "list: creator_type=seller" 6 "$(body "$(req GET "$L&creator_type=seller")" | cnt)"
check "list: status__in works" 6 "$(body "$(req GET "$L&status__in=inactive,suspended")" | cnt)"
check "list: has_business_profile=true" 1 "$(body "$(req GET "$L&has_business_profile=true")" | cnt)"

echo "=== Seller Request queue: permissions ==="
check "no token -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/sellers/requests/)"
ST=$(curl -s -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"0100000002","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin).get('access',''))")
check "seller token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/sellers/requests/ -H "Authorization: Bearer $ST")"
BT=$(curl -s -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"test.buyer@egoola.com","password":"Test@12345"}' | python -c "import sys,json;print(json.load(sys.stdin).get('access',''))")
check "buyer token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/accounts/sellers/requests/ -H "Authorization: Bearer $BT")"
check "registering needs no token (also fine with a real admin token)" 201 "$(code "$(reg_with name='Smoke Reg Eight' email=smoke.reg.eight@example.com phone=+8801700091008 -- "${NID[@]}" -H "$AUTH")")"
S8=$(body "$(req GET "/accounts/sellers/?search=smoke.reg.eight")" | jget "['results'][0]['id']")
check "POST on the queue -> 405" 405 "$(code "$(req POST /accounts/sellers/requests/ '{}')")"

echo "=== What the admin sees on a request ==="
R=$(req GET /accounts/sellers/$S2/)
check "detail 200" 200 "$(code "$R")"
check "detail is_seller_request" True "$(body "$R" | jget "['is_seller_request']")"
check "detail has two documents" 2 "$(body "$R" | python -c "import sys,json;print(len(json.load(sys.stdin)['media']))")"
check "document kinds" "certificate,nid" "$(body "$R" | python -c "import sys,json;print(','.join(sorted(m['media_for'] for m in json.load(sys.stdin)['media'])))")"
check "PDF stored as document" document "$(body "$R" | python -c "import sys,json;print([m['media_type'] for m in json.load(sys.stdin)['media'] if m['media_for']=='nid'][0])")"
check "document has a url" True "$(body "$R" | python -c "import sys,json;print(all(m['media_url'] for m in json.load(sys.stdin)['media']))")"
check "business profile saved" Retail "$(body "$R" | jget "['business_info']['business_type']")"
check "profile photo saved" True "$(body "$R" | python -c "import sys,json;print(bool(json.load(sys.stdin)['profile_pic_url']))")"
check "address and geography saved" "House 1, Road 2, Feni 126 13 8" "$(body "$R" | python -c "import sys,json;d=json.load(sys.stdin);print(d['present_address'],d['country'],d['state'],d['city'])")"
check "history has the registration entry" "1 unverified seller" "$(body "$R" | python -c "import sys,json;l=json.load(sys.stdin)['verification_logs'];print(len(l),l[0]['verification_status'],l[0]['creator_type'])")"
check "two NIDs stored for Three" 2 "$(body "$(req GET /accounts/sellers/$S3/)" | python -c "import sys,json;print(len([m for m in json.load(sys.stdin)['media'] if m['media_for']=='nid']))")"

echo "=== Admin actions take a seller out of the queue ==="
check "editing an address keeps it in the queue" True "$(body "$(req PATCH /accounts/sellers/$S1/ '{"present_address":"New address 5"}')" | jget "['is_seller_request']")"
check "re-sending the same status keeps it in the queue" True "$(body "$(req PATCH /accounts/sellers/$S1/ '{"status":"inactive","verification_status":"unverified"}')" | jget "['is_seller_request']")"
check "a note alone keeps it in the queue" True "$(body "$(req PATCH /accounts/sellers/$S1/ '{"verification_note":"just a note"}')" | jget "['is_seller_request']")"
check "admin cannot set the flag directly" True "$(body "$(req PATCH /accounts/sellers/$S1/ '{"is_seller_request":false}')" | jget "['is_seller_request']")"
check "still 7 in queue after those edits" 7 "$(body "$(req GET "$Q&limit=50")" | rlen)"

R=$(req PATCH /accounts/sellers/$S1/ '{"verification_status":"verified","status":"active"}')
check "approve (verified + active)" 200 "$(code "$R")"
check "flag cleared on approve" False "$(body "$R" | jget "['is_seller_request']")"
check "approved seller left the queue" "Eight,Six,Five,Four,Three,Two" "$(body "$(req GET "$Q")" | names)"
check "approved seller can log in" 200 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"+8801700091001","password":"Sell@12345"}')"
check "history now has 2 entries" 2 "$(body "$(req GET /accounts/sellers/$S1/)" | python -c "import sys,json;print(len(json.load(sys.stdin)['verification_logs']))")"

check "reject without a note -> 400" 400 "$(code "$(req PATCH /accounts/sellers/$S4/ '{"verification_status":"rejected"}')")"
check "failed reject keeps it in the queue" True "$(body "$(req GET /accounts/sellers/$S4/)" | jget "['is_seller_request']")"
R=$(req PATCH /accounts/sellers/$S4/ '{"verification_status":"rejected","verification_note":"NID photo is unreadable"}')
check "reject with a note" 200 "$(code "$R")"
check "flag cleared on reject" False "$(body "$R" | jget "['is_seller_request']")"
R4L=$(curl -s -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"+8801700091004","password":"Sell@12345"}')
check "rejected seller can still log in (to fix and resubmit)" "rejected inactive False" "$(echo "$R4L" | python -c "import sys,json;d=json.load(sys.stdin);print(d['verification_status'],d['status'],d['can_operate'])")"

R=$(req PATCH /accounts/sellers/$S3/ '{"status":"suspended"}')
check "changing only the account status" 200 "$(code "$R")"
check "flag cleared on a status-only change" False "$(body "$R" | jget "['is_seller_request']")"
check "status change adds no history entry" 1 "$(body "$R" | python -c "import sys,json;print(len(json.load(sys.stdin)['verification_logs']))")"
check "a suspended seller cannot log in" 401 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"+8801700091003","password":"Sell@12345"}')"

R=$(req PATCH /accounts/sellers/$S5/ '{"verification_status":"pending"}')
check "moving to pending is also an action" False "$(body "$R" | jget "['is_seller_request']")"

check "admin cannot put a handled seller back in the queue" False "$(body "$(req PATCH /accounts/sellers/$S1/ '{"is_seller_request":true}')" | jget "['is_seller_request']")"
check "queue now holds only the untouched ones (Two, Six, Eight)" "Eight,Six,Two" "$(body "$(req GET "$Q")" | names)"
check "count of waiting requests via the normal list" 3 "$(body "$(req GET "$L&is_seller_request=true&limit=1")" | cnt)"

echo "=== Sellers an admin creates are not requests ==="
R=$(req POST /accounts/sellers/ '{"name":"Smoke Reg Admin Made","email":"smoke.reg.adminmade@example.com","phone":"+8801700091099","password":"Sell@12345"}')
check "admin creates a seller" 201 "$(code "$R")"
check "admin-made seller is not a request" False "$(body "$R" | jget "['is_seller_request']")"
check "admin-made seller is verified by default" verified "$(body "$R" | jget "['verification_status']")"
check "admin-made seller is not in the queue" 3 "$(body "$(req GET "$Q&limit=50")" | rlen)"
check "creator_type=admin finds it" 1 "$(body "$(req GET "$L&creator_type=admin")" | cnt)"

echo "=== Stored data (DB) ==="
cd "$SERVER_DIR"
uv run manage.py shell -c "
from apps.accounts.models import Seller, SellerMedia
s = Seller.objects.get(id=$S2)
print('DB1', s.creator_type, s.creator_name, s.created_by == s.id, s.password != 'Sell@12345' and len(s.password) > 40)
print('DB2', SellerMedia.objects.filter(seller_id=$S1).count(), SellerMedia.objects.filter(seller_id=$S3).count())
import os
from django.conf import settings
paths = list(SellerMedia.objects.filter(seller_id=$S2).values_list('media_path', flat=True))
print('DB3', all(os.path.exists(os.path.join(settings.MEDIA_ROOT, p)) for p in paths), len(paths))
print('DB4', Seller.objects.filter(email__istartswith='smoke.reg.probe').count())
" 2>&1 | grep -E "^DB" > "$SCRATCH/db.txt"
check "creator is the seller themselves, password hashed" "DB1 seller Smoke Reg Two True True" "$(grep DB1 "$SCRATCH/db.txt")"
check "document rows stored (1 and 2)" "DB2 1 2" "$(grep DB2 "$SCRATCH/db.txt")"
check "document files exist on disk" "DB3 True 2" "$(grep DB3 "$SCRATCH/db.txt")"
check "no half-registered rows from the failed attempts" "DB4 0" "$(grep DB4 "$SCRATCH/db.txt")"

echo
echo "RESULT: $PASS passed, $FAIL failed"
