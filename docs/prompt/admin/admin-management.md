Admin Management APIs are ready on egoola-server. Base URL: /api/v1/accounts/admins/.
Super-admin token only (401 no token, 403 seller/buyer token, 403 plain admin token — a plain
admin can use Seller/Buyer/Listing management elsewhere, but not this resource).

Endpoints:
- GET    /accounts/admins/?type=&status=&search=&limit=&offset=   (list, paginated)
- POST   /accounts/admins/                                        (create, JSON or multipart)
- GET    /accounts/admins/{id}/                                   (retrieve, full record + media)
- PATCH  /accounts/admins/{id}/                                   (update, JSON or multipart)
- DELETE /accounts/admins/{id}/                                   (delete)

Safety rules: an admin cannot change their own type or status (400), and cannot delete their
own account (400) — always at least one active super-admin left. Role changes take effect
immediately (read fresh from DB every request, not cached in the token).

Fields: id, name, email (unique), mobile (unique), password (write-only, required on create
only, hashed, min 8 chars/not common/not all-digits), type (admin|super_admin), status
(active|inactive), profile_pic (write-only upload, <=2MB), remove_profile_pic (write-only
bool, clears the picture back to empty — update only, a new profile_pic in the same request
wins over it), profile_pic_path/profile_pic_url (read-only), skills/experiences/interests/
educations (JSON), present_address/permanent_address, country/state/city/thana,
last_logged_at (read-only), media (read-only, nested), media_for/media_file/media_delete_ids
(write-only — add media_for+media_file pairs by position, remove by media_delete_ids;
media_for is one of nid, birth_certificate, profile_document, other).

Full reference: egoola-server/docs/admin/admin-management-guide.md.
Postman: egoola-server/postman/admin/Egoola-Admin.postman_collection.json (dedicated — the
Admins folder in Egoola.postman_collection.json also exists but only covers basic CRUD, not
profile_pic/remove_profile_pic/media).

Implement the Admin management screen (list/create/edit/delete admins, role/status toggles,
profile picture set/replace/remove, document upload/remove) against these.
