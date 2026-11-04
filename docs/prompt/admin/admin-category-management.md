Admin Category Management APIs are ready on egoola-server. Base URL: /api/v1/catalog/categories/.
Admin bearer token only (401 no token, 403 seller/buyer token).

Endpoints:
- GET    /catalog/categories/?type=&status=&search=&limit=&offset=   (list, paginated)
- POST   /catalog/categories/                                        (create)
- PATCH  /catalog/categories/{id}/                                   (update)
- DELETE /catalog/categories/{id}/                                   (delete, 409 if in use)
- GET    /catalog/categories/parent-chain/?categoryIds=1,2           (breadcrumb ancestors)
- GET    /catalog/categories/tree/?type=product&categoryName=elec    (full nested tree)
No GET /catalog/categories/{id}/ (405) — list/tree rows already carry every field.

Fields: id, type (product|service), name, slug (read-only, auto), parent (nullable id,
same-type only, no cycles), image (write-only upload), image_path/image_url (read-only),
sort_order, status (active|inactive).

Full reference: egoola-server/docs/admin/admin-category-api-guide.md (CRUD) and
egoola-server/docs/admin/category-tree-api-guide.md (parent-chain + tree, response shapes).
Postman: egoola-server/postman/admin/Egoola-Category.postman_collection.json.

Implement the admin Category management screen (list/create/edit/delete, parent picker via
tree, breadcrumb via parent-chain) against these.
