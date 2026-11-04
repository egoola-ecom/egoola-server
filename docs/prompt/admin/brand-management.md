Admin Brand Management APIs are ready on egoola-server. Base URL: /api/v1/catalog/brands/.
Admin bearer token only (401 no token, 403 seller/buyer token).

Endpoints:
- GET    /catalog/brands/?name=&is_active=&search=&limit=&offset=   (list, paginated)
- POST   /catalog/brands/                                           (create, JSON or multipart)
- PATCH  /catalog/brands/{id}/                                      (update, JSON or multipart)
- DELETE /catalog/brands/{id}/                                      (delete, 409 if used by a listing)
No GET /catalog/brands/{id}/ (405) — list rows already carry every field.

Fields: id, name (unique project-wide, not per-type like Category), slug (read-only, auto),
image (write-only upload, <=2MB, same global cap as Category), image_path/image_url
(read-only), is_active (default true), created_by/creator_name/creator_type (read-only).

Image upload works exactly like Category: send `image` as multipart to create or update it.

Full reference: egoola-server/docs/admin/admin-brand-api-guide.md.
Postman: egoola-server/postman/admin/Egoola-Brand.postman_collection.json.

Implement the admin Brand management screen (list/create/edit/delete, logo upload) against
these.
