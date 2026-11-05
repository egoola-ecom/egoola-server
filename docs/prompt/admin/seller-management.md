Seller Management APIs are ready on egoola-server. Base URL: /api/v1/accounts/sellers/.
Admin bearer token only (401 no token, 403 seller/buyer token — any admin, not super-admin-only).

Endpoints:
- GET    /accounts/sellers/?verification_status=&status=&is_seller_request=&creator_type=&
         email_verified=&phone_verified=&has_business_profile=&business_type=&country=&state=
         &city=&thana=&created_from=&created_to=&requested_from=&requested_to=&search=&limit=&
         offset=                                              (list, paginated)
- GET    /accounts/sellers/requests/                           (Seller Request queue, cursor-
                                                                  paginated: self-registered,
                                                                  not yet acted on)
- POST   /accounts/sellers/                                    (create, JSON or multipart)
- GET    /accounts/sellers/{id}/                                (retrieve, full record)
- PATCH  /accounts/sellers/{id}/                                (update, JSON or multipart)
- DELETE /accounts/sellers/{id}/                                (delete; 409 if the seller has
                                                                  any order — deactivate/suspend
                                                                  instead)

Two status fields, now partly coupled (not fully independent) — don't conflate them:
- verification_status: unverified | pending | verified | rejected. verification_note required
  when rejecting. Every change writes a verification_logs row.
- status: active | inactive | suspended. Every value can log in now (status no longer gates
  login by itself) — it instead gates what the seller can do once logged in, see below.

Transition/coupling rules enforced server-side (apps/accounts/admin_api/serializers.py
SellerSerializer.validate()):
- rejected can only move to pending next (not straight to unverified or verified) -> 400
  otherwise.
- Once verification_status has ever been verified, it can never become rejected again, from
  any status, forever (tracked by was_ever_verified, read-only, detail view only, not on the
  list row) -> 400 on any later attempt.
- status is derived from the resulting verification_status in the same request: pending forces
  status to inactive (silently overrides whatever was sent), rejected forces status to
  suspended (same), unverified only allows inactive/suspended (active -> 400), verified is free
  (any of the three). This applies even when you only send status and don't touch
  verification_status, since it's checked against the resulting combination either way.

Three access tiers, reported as two read-only booleans (can_operate, can_edit_profile) on the
detail view and on the seller's own login response:
- Full (can_operate=true): everything.
- Profile-only (can_operate=false, can_edit_profile=true): only their own profile/documents,
  password, and (if rejected) resubmit. unverified+inactive, pending+inactive, and
  rejected+suspended (deliberate carve-out, so a rejected seller can still fix and resubmit).
- Locked (both false): logged in, can only GET their own profile, no writes at all, not even
  their own profile. verified+inactive (an admin pausing an already-approved seller locks them
  out entirely, not just down to profile-only) and every other suspended combination.

is_seller_request clears automatically the first time an admin changes verification_status or
status on that seller (leaves the queue); editing anything else keeps it queued.

Business profile: send `info` (JSON object, or a JSON-encoded string over multipart) on
create/update; read back as `business_info` (nested, read-only). Every real profile change is
logged to profile_change_logs (read-only, detail view).

Profile pic / documents — same single create/update call, not separate endpoints:
- profile_pic (write-only file, <=2MB) to set/replace
- remove_profile_pic (write-only bool) to clear it back to empty (update only; a profile_pic
  in the same request wins over this)
- media_for + media_file (paired by position) to add documents; media_for is one of nid,
  birth_certificate, certificate, gallery_image, gallery_video, other
- media_delete_ids to remove existing document rows

Full reference: egoola-server/docs/admin/seller-verification-guide.md (this is the complete
Seller Management guide, despite the filename — covers verification workflow, the request
queue, profile pics/media, change logs, and the delete/409 behavior).
Postman: egoola-server/postman/admin/Egoola-Seller.postman_collection.json.

Implement the admin Seller management screen (list/create/edit/delete, the Seller Request
queue with approve/reject/reactivate actions, profile picture and document upload/remove,
verification and status history views) against these.
