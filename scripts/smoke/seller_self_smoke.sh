#!/usr/bin/env bash
# The seller's own API (/seller/me/...): profile edits, documents, password,
# resubmit after a rejection, the not-approved-yet limits, and the profile change
# log that admins read on the seller detail.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
BASE="$SMOKE_BASE/api/v1"
PASS=0; FAIL=0
check() { if [ "$2" == "$3" ]; then echo "OK   $1 (got $3)"; PASS=$((PASS+1)); else echo "FAIL $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi; }
code() { echo "$1" | tail -1; }
body() { echo "$1" | sed '$d'; }
# py "<expression on d>" : read JSON on stdin as d and print the expression
py() { python -c "import sys,json;d=json.load(sys.stdin);print($1)" 2>/dev/null; }
areq() { curl -s -w '\n%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" ${3:+-d "$3"}; }
sreq() { curl -s -w '\n%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $ST" -H "Content-Type: application/json" ${3:+-d "$3"}; }
smulti() { local m="$1" path="$2"; shift 2; curl -s -w '\n%{http_code}' -X "$m" "$BASE$path" -H "Authorization: Bearer $ST" "$@"; }
login() { curl -s -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d "{\"phone\":\"$1\",\"password\":\"$2\"}"; }
logs() { areq GET /accounts/sellers/$1/ | sed '$d'; }

cp "$SCRATCH/t.png" "$SCRATCH/nid.png"; cp "$SCRATCH/t.png" "$SCRATCH/nid2.png"; cp "$SCRATCH/t.png" "$SCRATCH/cert.png"; cp "$SCRATCH/t.png" "$SCRATCH/photo.png"
echo "just text" > "$SCRATCH/note.txt"
PNG="image/png"

TOKEN=$(curl -s -X POST "$BASE/auth/admin/login/" -H "Content-Type: application/json" -d '{"email":"test.admin@egoola.com","password":"Test@12345"}' | py "d['access']")
[ -n "$TOKEN" ] && echo "OK   admin login" && PASS=$((PASS+1))

register() { # name email phone
  curl -s -w '\n%{http_code}' -X POST $BASE/auth/seller/register/ --form-string "name=$1" --form-string "email=$2" --form-string "phone=$3" --form-string "password=Sell@12345" \
    --form-string "present_address=House 1, Feni" --form-string "permanent_address=Village X" -F country=126 -F state=13 -F city=8 -F media_for=nid -F "media_file=@$SCRATCH/nid.png;type=$PNG"
}
R=$(register "Smoke Self One" smoke.self.one@example.com +8801700095001); S1=$(body "$R" | py "d['id']")
R=$(register "Smoke Self Two" smoke.self.two@example.com +8801700095002); S2=$(body "$R" | py "d['id']")
L=$(login +8801700095001 'Sell@12345'); ST=$(echo "$L" | py "d['access']")
L2=$(login +8801700095002 'Sell@12345'); ST2=$(echo "$L2" | py "d['access']")

echo "=== Access ==="
check "no token -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/seller/me/)"
check "admin token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/seller/me/ -H "Authorization: Bearer $TOKEN")"
BT=$(curl -s -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"test.buyer@egoola.com","password":"Test@12345"}' | py "d['access']")
check "buyer token -> 403" 403 "$(curl -s -o /dev/null -w '%{http_code}' $BASE/seller/me/ -H "Authorization: Bearer $BT")"
check "a not-approved seller can use /seller/me/" 200 "$(code "$(sreq GET /seller/me/)")"
for path in me/resubmit me/change-password; do
  check "no token on /seller/$path/ -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/seller/$path/)"
done

echo "=== Login uses phone + password (not email) ==="
LP="$BASE/auth/seller/login/"
lp() { curl -s -w '\n%{http_code}' -X POST $LP -H 'Content-Type: application/json' -d "$1"; }
R=$(lp '{"phone":"+8801700095001","password":"Sell@12345"}')
check "phone + password -> 200" 200 "$(code "$R")"
check "response carries the phone" "+8801700095001" "$(body "$R" | py "d['phone']")"
check "phone with spaces around it still works" 200 "$(code "$(lp '{"phone":"  +8801700095001  ","password":"Sell@12345"}')")"
R=$(lp '{"email":"smoke.self.one@example.com","password":"Sell@12345"}')
check "email + password no longer works -> 400" 400 "$(code "$R")"
check "…it asks for the phone" "['This field is required.']" "$(body "$R" | py "d['phone']")"
R=$(lp '{"phone":"+8801700095001","password":"Wrong@12345"}')
check "right phone, wrong password -> 401" 401 "$(code "$R")"
check "…message names the phone" "Invalid phone number or password." "$(body "$R" | py "d['detail']")"
R=$(lp '{"phone":"+8800000000000","password":"Sell@12345"}')
check "unknown phone -> 401, same message (no probing)" "401 Invalid phone number or password." "$(code "$R") $(body "$R" | py "d['detail']")"
check "missing password -> 400" 400 "$(code "$(lp '{"phone":"+8801700095001"}')")"
check "empty body -> 400" 400 "$(code "$(lp '{}')")"
check "an email typed into the phone field -> 401" 401 "$(code "$(lp '{"phone":"smoke.self.one@example.com","password":"Sell@12345"}')")"
check "admin login still uses email" 200 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/admin/login/ -H 'Content-Type: application/json' -d '{"email":"test.admin@egoola.com","password":"Test@12345"}')"
check "buyer login still uses email" 200 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/buyer/login/ -H 'Content-Type: application/json' -d '{"email":"test.buyer@egoola.com","password":"Test@12345"}')"

echo "=== GET /seller/me/ ==="
R=$(sreq GET /seller/me/)
check "own id" "$S1" "$(body "$R" | py "d['id']")"
check "not approved yet" "unverified inactive False True" "$(body "$R" | py "(d['verification_status'],d['status'],d['can_operate'],d['is_seller_request'])" | tr -d "(),'")"
check "has the NID uploaded at sign-up" "['nid']" "$(body "$R" | py "[m['media_for'] for m in d['media']]")"
check "no password in the response" "None" "$(body "$R" | py "d.get('password')")"
check "no change log in the seller's own view" "None" "$(body "$R" | py "d.get('profile_change_logs')")"
check "no wallet fields" "None" "$(body "$R" | py "d.get('wallet_balance')")"
check "requested_at is set" True "$(body "$R" | py "bool(d['requested_at'])")"

echo "=== Editing the profile ==="
R=$(sreq PATCH /seller/me/ '{"name":"Smoke Self One Renamed","present_address":"New address 5"}')
check "edit name + address" 200 "$(code "$R")"
check "name changed" "Smoke Self One Renamed" "$(body "$R" | py "d['name']")"
D=$(logs $S1)
check "one log row" 1 "$(echo "$D" | py "len(d['profile_change_logs'])")"
check "log lists both changed fields" "['name', 'present_address']" "$(echo "$D" | py "sorted(d['profile_change_logs'][0]['changed_fields'])")"
check "log previous values" "Smoke Self One|House 1, Feni" "$(echo "$D" | py "d['profile_change_logs'][0]['previous_data']['name']+'|'+d['profile_change_logs'][0]['previous_data']['present_address']")"
check "log new values" "Smoke Self One Renamed|New address 5" "$(echo "$D" | py "d['profile_change_logs'][0]['new_data']['name']+'|'+d['profile_change_logs'][0]['new_data']['present_address']")"
check "previous and new have the same keys" True "$(echo "$D" | py "set(d['profile_change_logs'][0]['previous_data'])==set(d['profile_change_logs'][0]['new_data'])")"
check "log is attributed to the seller" "seller $S1 Smoke Self One" "$(echo "$D" | py "' '.join(str(x) for x in (d['profile_change_logs'][0]['creator_type'],d['profile_change_logs'][0]['created_by'],d['profile_change_logs'][0]['creator_name']))")"
check "sending the same values writes no log" 1 "$(sreq PATCH /seller/me/ '{"name":"Smoke Self One Renamed","present_address":"New address 5"}' >/dev/null; logs $S1 | py "len(d['profile_change_logs'])")"
check "empty PATCH is fine and writes no log" 1 "$(sreq PATCH /seller/me/ '{}' >/dev/null; logs $S1 | py "len(d['profile_change_logs'])")"
check "same email is accepted" 200 "$(code "$(sreq PATCH /seller/me/ '{"email":"smoke.self.one@example.com"}')")"
check "different email -> 400" 400 "$(code "$(sreq PATCH /seller/me/ '{"email":"smoke.self.other@example.com"}')")"
check "email error says so" "['Email cannot be changed.']" "$(body "$(sreq PATCH /seller/me/ '{"email":"smoke.self.other@example.com"}')" | py "d['email']")"
check "same phone is accepted" 200 "$(code "$(sreq PATCH /seller/me/ '{"phone":"+8801700095001"}')")"
check "different phone -> 400" 400 "$(code "$(sreq PATCH /seller/me/ '{"phone":"+8801700095999"}')")"
check "blank name -> 400" 400 "$(code "$(sreq PATCH /seller/me/ '{"name":""}')")"
check "blank present_address -> 400" 400 "$(code "$(sreq PATCH /seller/me/ '{"present_address":""}')")"
check "null city -> 400" 400 "$(code "$(sreq PATCH /seller/me/ '{"city":null}')")"
check "city from another state -> 400" 400 "$(code "$(sreq PATCH /seller/me/ '{"state":12}')")"
R=$(sreq PATCH /seller/me/ '{"status":"active","verification_status":"verified","verification_note":"x","is_seller_request":false,"can_operate":true,"requested_at":"2000-01-01T00:00:00Z","wallet_balance":"999"}')
check "status/verification/flags in the body are ignored" "200 inactive unverified True False" "$(code "$R") $(body "$R" | py "d['status']") $(body "$R" | py "d['verification_status']") $(body "$R" | py "d['is_seller_request']") $(body "$R" | py "d['can_operate']")"
check "…and wrote no log" 1 "$(logs $S1 | py "len(d['profile_change_logs'])")"

R=$(sreq PATCH /seller/me/ '{"skills":["retail","export"],"education":["BBA"]}')
check "edit skills and education" 200 "$(code "$R")"
D=$(logs $S1)
check "skills log: before null, after list" "None ['retail', 'export']" "$(echo "$D" | py "str(d['profile_change_logs'][0]['previous_data']['skills'])+' '+str(d['profile_change_logs'][0]['new_data']['skills'])")"
check "2 log rows now" 2 "$(echo "$D" | py "len(d['profile_change_logs'])")"
check "newest log first" "['education', 'skills']" "$(echo "$D" | py "sorted(d['profile_change_logs'][0]['changed_fields'])")"

echo "=== Business profile ==="
INFO='{"business_type":"Retail","main_product":"Shoes","owner_name":"Smoke Owner","employees_range":"1-10","annual_revenue":"< $50,000","established_year":"2020"}'
R=$(sreq PATCH /seller/me/ "{\"info\":$INFO}")
check "add business profile" 200 "$(code "$R")"
check "business_info returned" "Retail" "$(body "$R" | py "d['business_info']['business_type']")"
D=$(logs $S1)
check "log: business_info before null, after full object" "None Shoes" "$(echo "$D" | py "str(d['profile_change_logs'][0]['previous_data']['business_info'])+' '+d['profile_change_logs'][0]['new_data']['business_info']['main_product']")"
R=$(sreq PATCH /seller/me/ "{\"info\":${INFO/Shoes/Bags}}")
check "change one business field" 200 "$(code "$R")"
D=$(logs $S1)
check "log shows only the changed business field" "{'main_product': 'Shoes'} {'main_product': 'Bags'}" "$(echo "$D" | py "str(d['profile_change_logs'][0]['previous_data']['business_info'])+' '+str(d['profile_change_logs'][0]['new_data']['business_info'])")"
check "re-sending the same business profile writes no log" "$(echo "$D" | py "len(d['profile_change_logs'])")" "$(sreq PATCH /seller/me/ "{\"info\":${INFO/Shoes/Bags}}" >/dev/null; logs $S1 | py "len(d['profile_change_logs'])")"
check "incomplete business profile -> 400" 400 "$(code "$(sreq PATCH /seller/me/ '{"info":{"business_type":"Retail"}}')")"

echo "=== Profile photo and documents (multipart) ==="
R=$(smulti PATCH /seller/me/ -F "profile_pic=@$SCRATCH/photo.png;type=$PNG")
check "upload profile photo" 200 "$(code "$R")"
check "photo url set" True "$(body "$R" | py "bool(d['profile_pic_url'])")"
check "photo change is logged" "profile_pic" "$(logs $S1 | py "d['profile_change_logs'][0]['changed_fields'][0]")"
check "text file as photo -> 400" 400 "$(code "$(smulti PATCH /seller/me/ -F "profile_pic=@$SCRATCH/note.txt;type=image/png")")"
R=$(smulti PATCH /seller/me/ -F media_for=certificate -F "media_file=@$SCRATCH/cert.png;type=$PNG")
check "add a certificate" 200 "$(code "$R")"
check "two documents" 2 "$(body "$R" | py "len(d['media'])")"
CERT=$(body "$R" | py "[m['id'] for m in d['media'] if m['media_for']=='certificate'][0]")
NID=$(body "$R" | py "[m['id'] for m in d['media'] if m['media_for']=='nid'][0]")
D=$(logs $S1)
check "document change logged as before/after lists" "documents 1 2" "$(echo "$D" | py "d['profile_change_logs'][0]['changed_fields'][0]+' '+str(len(d['profile_change_logs'][0]['previous_data']['documents']))+' '+str(len(d['profile_change_logs'][0]['new_data']['documents']))")"
check "text file as document -> 400" 400 "$(code "$(smulti PATCH /seller/me/ -F media_for=certificate -F "media_file=@$SCRATCH/note.txt;type=text/plain")")"
check "media_for without a file -> 400" 400 "$(code "$(smulti PATCH /seller/me/ -F media_for=certificate)")"
check "gallery_image not allowed -> 400" 400 "$(code "$(smulti PATCH /seller/me/ -F media_for=gallery_image -F "media_file=@$SCRATCH/cert.png;type=$PNG")")"
MANY=(); for i in 1 2 3 4 5 6 7 8 9 10 11; do MANY+=(-F media_for=other -F "media_file=@$SCRATCH/cert.png;type=$PNG"); done
check "11 documents in one request -> 400" 400 "$(code "$(smulti PATCH /seller/me/ "${MANY[@]}")")"
check "delete the certificate" 1 "$(smulti PATCH /seller/me/ -F "media_delete_ids=$CERT" | sed '$d' | py "len(d['media'])")"
check "deleting the only NID -> 400" 400 "$(code "$(smulti PATCH /seller/me/ -F "media_delete_ids=$NID")")"
check "…the NID is still there" 1 "$(sreq GET /seller/me/ | sed '$d' | py "len([m for m in d['media'] if m['media_for']=='nid'])")"
R=$(smulti PATCH /seller/me/ -F "media_delete_ids=$NID" -F media_for=nid -F "media_file=@$SCRATCH/nid2.png;type=$PNG")
check "replace the NID in one request" 200 "$(code "$R")"
NID=$(body "$R" | py "[m['id'] for m in d['media'] if m['media_for']=='nid'][0]")
OTHER_NID=$(areq GET /accounts/sellers/$S2/ | sed '$d' | py "d['media'][0]['id']")
smulti PATCH /seller/me/ -F "media_delete_ids=$OTHER_NID" >/dev/null
check "cannot delete another seller's document" 1 "$(areq GET /accounts/sellers/$S2/ | sed '$d' | py "len(d['media'])")"

echo "=== Change password ==="
check "wrong current password -> 400" 400 "$(code "$(sreq POST /seller/me/change-password/ '{"current_password":"Nope@12345","new_password":"Better@2468"}')")"
check "weak new password -> 400" 400 "$(code "$(sreq POST /seller/me/change-password/ '{"current_password":"Sell@12345","new_password":"abc1"}')")"
check "same password -> 400" 400 "$(code "$(sreq POST /seller/me/change-password/ '{"current_password":"Sell@12345","new_password":"Sell@12345"}')")"
check "missing fields -> 400" 400 "$(code "$(sreq POST /seller/me/change-password/ '{}')")"
check "change password" 200 "$(code "$(sreq POST /seller/me/change-password/ '{"current_password":"Sell@12345","new_password":"Better@2468"}')")"
check "old password no longer works" 401 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"+8801700095001","password":"Sell@12345"}')"
check "new password works" 200 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"+8801700095001","password":"Better@2468"}')"
D=$(logs $S1)
check "password change is logged" "['password'] [hidden] [hidden]" "$(echo "$D" | py "str(d['profile_change_logs'][0]['changed_fields'])+' '+d['profile_change_logs'][0]['previous_data']['password']+' '+d['profile_change_logs'][0]['new_data']['password']")"
check "no password hash in any log" False "$(echo "$D" | py "'pbkdf2' in json.dumps(d['profile_change_logs'])")"

echo "=== Resubmit: only after a rejection ==="
check "resubmit while unverified -> 400" 400 "$(code "$(sreq POST /seller/me/resubmit/ '{}')")"
check "…message" "Only a rejected application can be resubmitted." "$(body "$(sreq POST /seller/me/resubmit/ '{}')" | py "d['detail']")"
check "admin rejects with a note" 200 "$(code "$(areq PATCH /accounts/sellers/$S1/ '{"verification_status":"rejected","verification_note":"NID is blurry"}')")"
R=$(sreq GET /seller/me/)
check "a rejected seller still gets in and sees the reason" "rejected NID is blurry False" "$(body "$R" | py "(d['verification_status']+' '+d['verification_note']+' '+str(d['can_operate']))")"
check "a rejected seller can still edit the profile" 200 "$(code "$(sreq PATCH /seller/me/ '{"present_address":"Corrected address 9"}')")"
check "…and replace the NID" 200 "$(code "$(smulti PATCH /seller/me/ -F "media_delete_ids=$NID" -F media_for=nid -F "media_file=@$SCRATCH/nid.png;type=$PNG")")"
REQ_BEFORE=$(sreq GET /seller/me/ | sed '$d' | py "d['requested_at']")
R=$(sreq POST /seller/me/resubmit/ '{"note":"Replaced the NID with a clear scan"}')
check "resubmit" 200 "$(code "$R")"
check "status is now pending" pending "$(body "$R" | py "d['verification_status']")"
check "back in the request queue" True "$(body "$R" | py "d['is_seller_request']")"
check "still not approved" False "$(body "$R" | py "d['can_operate']")"
check "note on the row is the seller's message" "Replaced the NID with a clear scan" "$(body "$R" | py "d['verification_note']")"
check "requested_at moved forward" True "$(body "$R" | py "d['requested_at'] > '$REQ_BEFORE'")"
D=$(logs $S1)
check "history: unverified, rejected, pending" "['pending', 'rejected', 'unverified']" "$(echo "$D" | py "[l['verification_status'] for l in d['verification_logs']]")"
check "pending entry is by the seller, with the message" "seller Replaced the NID with a clear scan" "$(echo "$D" | py "d['verification_logs'][0]['creator_type']+' '+d['verification_logs'][0]['verification_note']")"
check "the rejection reason stays in the history" "NID is blurry" "$(echo "$D" | py "d['verification_logs'][1]['verification_note']")"
check "resubmit again while pending -> 400" 400 "$(code "$(sreq POST /seller/me/resubmit/ '{}')")"
check "admin rejects again" 200 "$(code "$(areq PATCH /accounts/sellers/$S1/ '{"verification_status":"rejected","verification_note":"Still unclear"}')")"
check "overlong resubmit note -> 400" 400 "$(code "$(sreq POST /seller/me/resubmit/ "{\"note\":\"$(python -c "print('x'*1001)")\"}")")"
R=$(sreq POST /seller/me/resubmit/ '{}')
check "resubmit with no note" "200 None" "$(code "$R") $(body "$R" | py "d['verification_note']")"

echo "=== The resubmission shows as new in the admin queue ==="
Q=$(areq GET "/accounts/sellers/requests/?search=smoke.self." | sed '$d')
check "queue holds both, resubmitted seller first (newest request)" "Smoke Self One Renamed,Smoke Self Two" "$(echo "$Q" | py "','.join(r['name'] for r in d['results'])")"
check "ordering=requested_at puts the earlier request first" "Smoke Self Two,Smoke Self One Renamed" "$(areq GET "/accounts/sellers/requests/?search=smoke.self.&ordering=requested_at" | sed '$d' | py "','.join(r['name'] for r in d['results'])")"
check "list rows carry requested_at" True "$(echo "$Q" | py "all(r['requested_at'] for r in d['results'])")"
TODAY=$(date +%F)
check "requested_from=today" 2 "$(areq GET "/accounts/sellers/requests/?search=smoke.self.&requested_from=$TODAY" | sed '$d' | py "len(d['results'])")"
check "requested_to far past" 0 "$(areq GET "/accounts/sellers/requests/?search=smoke.self.&requested_to=2000-01-01" | sed '$d' | py "len(d['results'])")"

echo "=== Approved: identity documents are locked ==="
check "admin approves (verified + active)" 200 "$(code "$(areq PATCH /accounts/sellers/$S1/ '{"verification_status":"verified","status":"active"}')")"
L=$(login +8801700095001 'Better@2468')
check "login now says approved" "verified active True" "$(echo "$L" | py "(d['verification_status']+' '+d['status']+' '+str(d['can_operate']))")"
ST=$(echo "$L" | py "d['access']")
NID=$(sreq GET /seller/me/ | sed '$d' | py "[m['id'] for m in d['media'] if m['media_for']=='nid'][0]")
check "can still edit the name" 200 "$(code "$(sreq PATCH /seller/me/ '{"name":"Smoke Self One Verified"}')")"
check "…and it is logged" "name" "$(logs $S1 | py "d['profile_change_logs'][0]['changed_fields'][0]")"
check "can still edit the address" 200 "$(code "$(sreq PATCH /seller/me/ '{"present_address":"After verification 3"}')")"
check "can add a certificate" 200 "$(code "$(smulti PATCH /seller/me/ -F media_for=certificate -F "media_file=@$SCRATCH/cert.png;type=$PNG")")"
check "cannot add an NID -> 400" 400 "$(code "$(smulti PATCH /seller/me/ -F media_for=nid -F "media_file=@$SCRATCH/nid2.png;type=$PNG")")"
check "cannot add a birth certificate -> 400" 400 "$(code "$(smulti PATCH /seller/me/ -F media_for=birth_certificate -F "media_file=@$SCRATCH/nid2.png;type=$PNG")")"
check "cannot delete the NID -> 400" 400 "$(code "$(smulti PATCH /seller/me/ -F "media_delete_ids=$NID")")"
check "…message tells them to ask an admin" True "$(body "$(smulti PATCH /seller/me/ -F "media_delete_ids=$NID")" | py "'Ask an admin' in d['media_for'][0]")"
check "cannot resubmit when verified -> 400" 400 "$(code "$(sreq POST /seller/me/resubmit/ '{}')")"

echo "=== Approved but inactive (paused by an admin): profile only ==="
check "admin pauses the approved seller" 200 "$(code "$(areq PATCH /accounts/sellers/$S1/ '{"status":"inactive"}')")"
L=$(login +8801700095001 'Better@2468')
check "a paused seller can still log in" "verified inactive False" "$(echo "$L" | py "(d['verification_status']+' '+d['status']+' '+str(d['can_operate']))")"
ST=$(echo "$L" | py "d['access']")
check "/seller/me/ still works" "verified inactive False" "$(sreq GET /seller/me/ | sed '$d' | py "(d['verification_status']+' '+d['status']+' '+str(d['can_operate']))")"
check "a paused seller can still edit the profile" 200 "$(code "$(sreq PATCH /seller/me/ '{"present_address":"Paused but editing"}')")"
check "identity documents stay locked (still verified)" 400 "$(code "$(smulti PATCH /seller/me/ -F media_for=nid -F "media_file=@$SCRATCH/nid2.png;type=$PNG")")"
check "pausing does not put them back in the request queue" False "$(sreq GET /seller/me/ | sed '$d' | py "d['is_seller_request']")"
check "admin makes the seller active again" 200 "$(code "$(areq PATCH /accounts/sellers/$S1/ '{"status":"active"}')")"
check "…and they can operate again" True "$(login +8801700095001 'Better@2468' | py "d['can_operate']")"
ST=$(login +8801700095001 'Better@2468' | py "d['access']")

echo "=== Admin edits are logged too ==="
before=$(logs $S1 | py "len(d['profile_change_logs'])")
check "admin edits the address" 200 "$(code "$(areq PATCH /accounts/sellers/$S1/ '{"present_address":"Admin fixed address"}')")"
D=$(logs $S1)
check "one new log row" "$((before+1))" "$(echo "$D" | py "len(d['profile_change_logs'])")"
check "attributed to the admin" "admin Test Admin" "$(echo "$D" | py "d['profile_change_logs'][0]['creator_type']+' '+d['profile_change_logs'][0]['creator_name']")"
check "previous is the seller's value" "Paused but editing" "$(echo "$D" | py "d['profile_change_logs'][0]['previous_data']['present_address']")"
check "status-only change by admin writes no profile log" "$((before+1))" "$(areq PATCH /accounts/sellers/$S1/ '{"status":"inactive"}' >/dev/null; areq PATCH /accounts/sellers/$S1/ '{"status":"active"}' >/dev/null; logs $S1 | py "len(d['profile_change_logs'])")"
areq PATCH /accounts/sellers/$S1/ '{"password":"Admin@12345"}' >/dev/null
D=$(logs $S1)
check "admin password reset is logged without the value" "['password'] False" "$(echo "$D" | py "str(d['profile_change_logs'][0]['changed_fields'])+' '+str('pbkdf2' in json.dumps(d['profile_change_logs']))")"
check "admin changes the phone: logged" 200 "$(code "$(areq PATCH /accounts/sellers/$S1/ '{"phone":"+8801700095101"}')")"
check "phone log has old and new" "+8801700095001 +8801700095101" "$(logs $S1 | py "d['profile_change_logs'][0]['previous_data']['phone']+' '+d['profile_change_logs'][0]['new_data']['phone']")"
check "after an admin changes the phone, the old phone cannot log in" 401 "$(code "$(lp '{"phone":"+8801700095001","password":"Admin@12345"}')")"
check "…and the new phone can" 200 "$(code "$(lp '{"phone":"+8801700095101","password":"Admin@12345"}')")"
check "list rows do not carry the logs" "None" "$(areq GET "/accounts/sellers/?search=smoke.self." | sed '$d' | py "d['results'][0].get('profile_change_logs')")"
check "admin edits the second seller's name" 200 "$(code "$(areq PATCH /accounts/sellers/$S2/ '{"name":"Smoke Self Two Edited"}')")"
check "…as one row" 1 "$(logs $S2 | py "len(d['profile_change_logs'])")"

echo "=== Suspended: no access at all ==="
check "admin suspends" 200 "$(code "$(areq PATCH /accounts/sellers/$S1/ '{"status":"suspended"}')")"
check "old token -> 401" 401 "$(code "$(sreq GET /seller/me/)")"
check "login -> 401" 401 "$(curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/auth/seller/login/ -H 'Content-Type: application/json' -d '{"phone":"+8801700095101","password":"Admin@12345"}')"

echo "=== IsActiveVerifiedSellerActor ==="
cd "$SERVER_DIR"
uv run manage.py shell -c "
from types import SimpleNamespace
from apps.accounts.models import Seller, Admin
from apps.authentication.permissions import IsActiveVerifiedSellerActor
perm = IsActiveVerifiedSellerActor()
def ok(user):
    return perm.has_permission(SimpleNamespace(user=user), None)
s = Seller.objects.get(id=$S2)
s.actor_type = 'seller'
rows = []
for v, st in (('verified','active'),('unverified','active'),('pending','inactive'),('verified','inactive'),('rejected','active')):
    s.verification_status, s.status = v, st
    rows.append(ok(s))
a = Admin.objects.first(); a.actor_type = 'admin'
msgs = []
for v, st in (('pending','inactive'), ('verified','inactive'), ('rejected','active')):
    s.verification_status, s.status = v, st
    p2 = IsActiveVerifiedSellerActor(); p2.has_permission(SimpleNamespace(user=s), None); msgs.append(p2.message)
print('PERM', rows, ok(a), ok(SimpleNamespace()))
print('MSG', 'not approved' in msgs[0] or 'not approved yet' in msgs[0], 'inactive' in msgs[1], 'not approved yet' in msgs[2])
" 2>&1 | grep -E "^(PERM|MSG)" > "$SCRATCH/perm.txt"
check "operating only when verified AND active" "PERM [True, False, False, False, False] False False" "$(grep PERM "$SCRATCH/perm.txt")"
check "the 403 message says which switch is holding the seller back" "MSG True True True" "$(grep MSG "$SCRATCH/perm.txt")"

echo "=== Files are removed from storage when media is deleted ==="
# fx <path>... : prints True/False for each path (does the file exist on disk?)
fx() {
  local list="" p; for p in "$@"; do list="$list'$p',"; done
  (cd "$SERVER_DIR" && uv run manage.py shell -c "
import os
from django.conf import settings
print('FX', ' '.join(str(os.path.exists(os.path.join(settings.MEDIA_ROOT, p))) for p in [$list]))" 2>&1 | grep '^FX' | sed 's/^FX //')
}
R=$(register "Smoke Self Three" smoke.self.three@example.com +8801700095003); S3=$(body "$R" | py "d['id']")
ST=$(login +8801700095003 'Sell@12345' | py "d['access']")
smulti PATCH /seller/me/ -F media_for=certificate -F "media_file=@$SCRATCH/cert.png;type=$PNG" -F "profile_pic=@$SCRATCH/photo.png;type=$PNG" >/dev/null
D=$(logs $S3)
NIDP=$(echo "$D" | py "[m['media_path'] for m in d['media'] if m['media_for']=='nid'][0]")
NIDI=$(echo "$D" | py "[m['id'] for m in d['media'] if m['media_for']=='nid'][0]")
CERTP=$(echo "$D" | py "[m['media_path'] for m in d['media'] if m['media_for']=='certificate'][0]")
CERTI=$(echo "$D" | py "[m['id'] for m in d['media'] if m['media_for']=='certificate'][0]")
PIC1=$(echo "$D" | py "d['profile_pic_path']")
check "NID, certificate and photo are stored" "True True True" "$(fx "$NIDP" "$CERTP" "$PIC1")"
check "a refused delete keeps the file (the only NID)" "400 True" "$(code "$(smulti PATCH /seller/me/ -F "media_delete_ids=$NIDI")") $(fx "$NIDP")"
smulti PATCH /seller/me/ -F "profile_pic=@$SCRATCH/nid2.png;type=$PNG" >/dev/null
PIC2=$(logs $S3 | py "d['profile_pic_path']")
check "replacing the photo removes the old file, keeps the new" "False True" "$(fx "$PIC1" "$PIC2")"
smulti PATCH /seller/me/ -F "media_delete_ids=$CERTI" >/dev/null
check "deleting a document removes its file" "False True" "$(fx "$CERTP" "$NIDP")"
R=$(smulti PATCH /seller/me/ -F "media_delete_ids=$NIDI" -F media_for=nid -F "media_file=@$SCRATCH/nid2.png;type=$PNG")
NIDP2=$(echo "$(body "$R")" | py "[m['media_path'] for m in d['media'] if m['media_for']=='nid'][0]")
check "replacing the NID removes the old file, keeps the new" "False True" "$(fx "$NIDP" "$NIDP2")"
check "admin deletes the seller" 204 "$(code "$(areq DELETE /accounts/sellers/$S3/)")"
check "the seller's NID and photo are gone from storage" "False False" "$(fx "$NIDP2" "$PIC2")"
# the same clean-up applies to buyers (shared code)
R=$(curl -s -w '\n%{http_code}' -X POST $BASE/accounts/buyers/ -H "Authorization: Bearer $TOKEN" --form-string "name=Smoke Self Buyer" --form-string "email=smoke.self.buyer@example.com" --form-string "phone=+8801700095009" --form-string "password=Buy@12345" -F media_for=nid -F "media_file=@$SCRATCH/nid.png;type=$PNG" -F "profile_pic=@$SCRATCH/photo.png;type=$PNG")
check "admin creates a buyer with a document and a photo" 201 "$(code "$R")"; BID=$(body "$R" | py "d['id']")
BD=$(areq GET /accounts/buyers/$BID/ | sed '$d')
BNID=$(echo "$BD" | py "d['media'][0]['media_path']"); BPIC=$(echo "$BD" | py "d['profile_pic_path']")
check "buyer files are stored" "True True" "$(fx "$BNID" "$BPIC")"
check "admin deletes the buyer" 204 "$(code "$(areq DELETE /accounts/buyers/$BID/)")"
check "the buyer's files are gone too" "False False" "$(fx "$BNID" "$BPIC")"

echo
echo "RESULT: $PASS passed, $FAIL failed"
