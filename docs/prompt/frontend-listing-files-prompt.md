# Brief for the Egoola Web session — listing files (thumbnail and gallery): BREAKING backend change

Backend change, done and tested in `egoola-server`. Files (the thumbnail and the gallery) are no longer sent with a listing or a gig and the old
thumbnail endpoints are gone. Read this file top to bottom, then update both the **Admin Web** and the **Seller Web**. Do not push; commit locally only if asked.

Read first: `egoola-server/docs/listing-complete-guide.md` section 15, `egoola-server/docs/seller-api-guide.md` sections 6.6 and 6.8,
`egoola-server/docs/prompt/frontend-listing-audit-prompt.md` sections 6 and 7 (checks T1–T6, M1–M3, P14). Postman: `Egoola-Listing` → **Listing files**,
`Egoola-SellerApp` → **Seller listings / Seller gigs**. Run the backend with `uv run manage.py runserver 8000`; accounts in `docs/test-accounts.md`.

## 1. What changed

1. **Listing and gig create / update are JSON only.** A multipart request to `/catalog/listings/`, `/catalog/gigs/`, `/seller/listings/` or
   `/seller/gigs/` is `415`. `media_file` and `media_delete_ids` are no longer accepted there. `image_path`, `image_url` and `media` are read only.
2. **The old endpoints are removed (they return 404):** `PUT` / `DELETE` on `.../listings/{id}/thumbnail/` and `.../gigs/{id}/thumbnail/` (admin and seller).
3. **Four new multipart APIs** (same for a product id and a gig id; a job id is `404`):

| Who | Add (first time) | Change |
|---|---|---|
| Admin | `POST /api/v1/catalog/listing-files/{id}/` | `PATCH /api/v1/catalog/listing-files/{id}/` |
| Seller (own listings only; another seller's id is `404`; needs a verified, active seller) | `POST /api/v1/seller/listing-files/{id}/` | `PATCH /api/v1/seller/listing-files/{id}/` |

4. **A files change never changes the listing status** (seller or admin). A rejected listing stays rejected after an upload. Only saving the listing itself
   (JSON `PATCH`) sends a rejected / changes-requested listing back to `pending`. Remove any "uploading will resubmit" warning you added earlier.

## 2. The contract

All four take `multipart/form-data`. Never set `Content-Type` yourself (`authFetch` handles `FormData`).

**POST (add)**
- `thumbnail`: optional, one file. JPG, PNG or WEBP, ≤ 10 MB, a real image. If the listing already has a thumbnail: `400` (use `PATCH`).
- `media_file`: optional, repeat the field once per file. JPG, PNG, WEBP, GIF, MP4 or PDF.
- Nothing is required: an empty POST is allowed and changes nothing. Returns `201`.

**PATCH (change).** Every part is independent; send only what changed.
- `remove_thumbnail`: `true` deletes the current thumbnail.
- `thumbnail`: a new thumbnail. It **always replaces** the old one (the old file is deleted), whether or not `remove_thumbnail` is sent.
- `remove_media_ids`: gallery ids to delete, `4,5` or the field repeated. An id that is not this listing's is `400`.
- `media_file`: gallery files to add. Removing ids and adding files can be in the same call.
- Nothing sent: `200`, nothing changes. Returns `200`.

**Response (both):** `{"image_path", "image_url", "media": [{"id", "media_type", "media_path", "media_url"}], "status"}`. Refresh the preview and the gallery from it.

**Limits.** Admin: only the type rules above. Seller gallery: ≤ 10 MB per file, ≤ 10 files per request, ≤ 20 files per listing (files removed in the same call do not count).

**Errors (`400`)**: `{"thumbnail": [...]}`, `{"media_file": [...]}` (a list of messages, one per bad file), `{"remove_media_ids": [...]}`. The request is **all or nothing**:
on a `400` nothing was saved and the current files are untouched. `401` login, `403` not allowed, `404` not found. `415` means you sent multipart or a file to the JSON API.

`media_type` is `image`, `video` or `document`: show images inline, video with a player, documents as links. Resolve URLs with `resolveMediaUrl`.
File changes are in the admin change log (`changed_fields`: `thumbnail`, `media`).

## 3. Tasks

1. **Listing / gig API clients (admin and seller):** send JSON only; drop `media_file` / `media_delete_ids` and every `FormData` use on create and update;
   delete the old thumbnail `PUT` / `DELETE` calls.
2. **One new client** `listing-files-api.ts` with `addFiles(scope, id, {thumbnail?, media?})` and `changeFiles(scope, id, {removeThumbnail?, thumbnail?, removeMediaIds?, media?})`,
   `scope` = `admin` | `seller`. Build the `FormData` (repeat `media_file`; `remove_media_ids` as a comma-separated string).
3. **One reusable files control** used by the product and gig forms and detail pages, in the admin and seller panels:
   - Thumbnail: preview (`image_url` or a placeholder), **Choose / Replace**, **Remove** (with confirmation).
   - Gallery: grid with a per-file **Remove** and **Add files**.
   - Client checks before sending: thumbnail type and 10 MB; gallery types; for a seller 10 MB, 10 per request, 20 per listing (count the files already there).
4. **Create flow:** `POST` the listing (JSON) first, then `POST` the files with the new id. If the file upload fails the listing already exists: stay on its edit page,
   show the error and let the user retry. Do not roll back or delete the listing.
5. **Edit flow:** one `PATCH` with what changed. Replacing the thumbnail = send the new file only (no `remove_thumbnail`). Removing = `remove_thumbnail=true` only.
   Update the screen from the response; show the three error keys next to the right control.
6. Seller panel: no status warning on upload; the status shown is whatever the response says.
7. Update the audit docs in `egoola-web/docs` if they mention the old thumbnail endpoints or multipart create.

## 4. Verify (browser, both roles; record results)

| # | Case | Expected |
|---|---|---|
| 1 | Create a product and a gig (JSON), then add a thumbnail and 2 gallery files | `201`, previews and gallery shown |
| 2 | Add a second thumbnail through the add call (if the UI allows it) | `400`, message shown |
| 3 | Choose a new thumbnail | replaced, old file gone from the screen |
| 4 | Remove the thumbnail only | placeholder shown |
| 5 | Remove 1 gallery file, add 2 in the same save | one request, gallery updated |
| 6 | A `.txt`, a fake `.png`, an `.exe` in the gallery | `400` mapped to the right control, nothing saved |
| 7 | Seller: 11 files at once; 21st file on a listing; a file > 10 MB | blocked client-side and mapped if the server refuses |
| 8 | Remove an id from another listing (crafted) | `400`, no crash |
| 9 | Seller changes files of a **rejected** listing | stays `rejected` |
| 10 | Then the seller saves the listing (JSON) | becomes `pending` |
| 11 | Admin changes files of any product or gig | status unchanged; change log shows `thumbnail` / `media` |
| 12 | A multipart request to the listing JSON API (crafted) | `415`, handled |
| 13 | Another seller's listing id on the seller files API | `404` page |

Report which cases pass, what you changed, and anything in the backend docs that looked wrong.
