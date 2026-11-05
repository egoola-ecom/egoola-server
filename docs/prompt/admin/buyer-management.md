Buyer Management APIs are ready on egoola-server. Base URL: /api/v1/accounts/buyers/.
Admin bearer token only (401 no token, 403 seller/buyer token — any admin, not super-admin-only).

Endpoints:
- GET    /accounts/buyers/?search=&status=&country=&state=&city=&thana=&email_verified=
         &phone_verified=&created_from=&created_to=&limit=&offset=     (list, paginated)
- POST   /accounts/buyers/                                             (create, JSON or multipart)
- GET    /accounts/buyers/{id}/                                        (retrieve, full record)
- PATCH  /accounts/buyers/{id}/                                        (update, JSON or multipart)
- DELETE /accounts/buyers/{id}/                                        (delete; 409 if the buyer has
                                                                          any order — suspend instead)

One status field, not two — simpler than Seller, no verification workflow and no access tiers:
- status: active | suspended. A suspended buyer cannot log in at all (unlike Seller, where every
  status can log in — see Seller.can_operate/can_edit_profile for that). Default active.

Model is named `User`, not `Buyer` (matches the Planning document's app/model table) — this is
the buyer, not Django's own auth user.

Profile pic / documents — same single create/update call, not separate endpoints:
- profile_pic (write-only file, <=2MB) to set/replace
- remove_profile_pic (write-only bool) to clear it back to empty (update only; a profile_pic
  in the same request wins over this)
- media_for + media_file (paired by position) to add documents; media_for is one of nid,
  birth_certificate, profile_document, other
- media_delete_ids to remove existing document rows

wallet_balance is read only here (changed only by the wallet flow, not this API).

Full reference: egoola-server/docs/admin/buyer-management-guide.md.
Postman: egoola-server/postman/admin/Egoola-Buyer.postman_collection.json.

The admin Buyer management screen already exists (list/create/edit/delete, profile picture and
document upload/remove). Audit it against this brief the same way `docs/admin-seller-audit.md`
checked the Seller screen — cross-check every field, filter and status code against the live
server, and call out any gap. Two things changed server-side since that screen was likely built
and are worth checking specifically:
- Delete now answers 409 (not a 500) when the buyer has an order, with the message
  "This buyer has one or more orders. Suspend the account instead of deleting." — confirm the
  screen shows this reason instead of a generic failure, the way the Seller screen's delete does.
- remove_profile_pic (clear the photo without replacing it) and media_delete_ids (remove a
  document) were already on the API; confirm the screen actually exposes both, not just
  profile_pic / media_for+media_file.
