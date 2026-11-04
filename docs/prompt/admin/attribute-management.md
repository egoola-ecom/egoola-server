Admin Attribute & Attribute Value Management APIs are ready on egoola-server. Base URL:
/api/v1/catalog/. Admin bearer token only (401 no token, 403 seller/buyer token).

Two separate resources — read together, written separately:

Attribute (Size, Colour, ...):
- GET    /catalog/attributes/?name=&is_active=&search=&limit=&offset=   (list)
- POST   /catalog/attributes/                                           (create)
- GET    /catalog/attributes/{id}/                                      (retrieve, includes
                                                                           nested "values" —
                                                                           read-only here)
- PATCH  /catalog/attributes/{id}/                                      (update own fields only)
- DELETE /catalog/attributes/{id}/                                      (409 if used by a SKU;
                                                                           deleting an unused one
                                                                           also deletes its values)

AttributeValue (Size -> S, M, L, XL):
- GET    /catalog/attribute-values/?attribute=&name=&is_active=&search=&limit=&offset=
- POST   /catalog/attribute-values/     (attribute id required, immutable after creation)
- GET    /catalog/attribute-values/{id}/
- PATCH  /catalog/attribute-values/{id}/
- DELETE /catalog/attribute-values/{id}/  (409 if used by a SKU)

Important: to add/remove a value, use the AttributeValue endpoints directly — there is no
nested write on the Attribute's own PATCH. To show an attribute with its values, one call to
GET /catalog/attributes/{id}/ is enough (values already nested).

Fields: see docs/admin/admin-attribute-api-guide.md for full tables. No image field on either
resource. Both expose created_at/updated_at (unlike Category/Brand/Measurement).

Full reference: egoola-server/docs/admin/admin-attribute-api-guide.md and
egoola-server/docs/attribute-sku-guide.md (broader guide: how these feed into listing SKUs).
Postman: egoola-server/postman/admin/Egoola-Attribute.postman_collection.json.

Implement the admin Attribute management screen (list/create/edit/delete attributes, and
manage each attribute's values inline on its detail view, calling the separate
AttributeValue endpoints for the add/remove actions).
