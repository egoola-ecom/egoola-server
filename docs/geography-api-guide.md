# Frontend API Guide — Geography

Reference data — Country → State → City → Thana, in that parent/child
order — populated by hand through these endpoints (there's no bulk import
from anywhere; an Admin creates each row). 16 endpoints total: Create,
Update, List, Delete for each of the four resources. Everything below was
tested against the running server before being written down — every
example request/response is real, not made up.

Also in this repo:
- **[Egoola-Geography.postman_collection.json](Egoola-Geography.postman_collection.json)** +
  **[Egoola-Local.postman_environment.json](Egoola-Local.postman_environment.json)**
  — import both into Postman and you can call every endpoint below without
  typing anything by hand. Logging in auto-saves the token for you.
- **[openapi.json](openapi.json)** — the exact, always-up-to-date machine
  schema. If this guide and that file ever disagree, trust `openapi.json`.
- **[frontend-api-guide.md](frontend-api-guide.md)** — covers login and
  Admin/Seller/Buyer management. Look there for how to get an Admin token
  in the first place — every endpoint here needs one.

---

## 1. Base URL and auth

```
http://127.0.0.1:8000/api/v1/geography/
```

Every path below is relative to that. All four resources are
**Admin-only** — log in via `POST /api/v1/auth/admin/login/` (see
[frontend-api-guide.md](frontend-api-guide.md) §3) and send the token on
every request:

```
Authorization: Bearer <access token>
```

No/invalid token → `401`. A valid Seller or Buyer token → `403`.

---

## 2. Rules shared by all four resources

- **No Retrieve.** There's only List, Create, Update, Delete — calling
  `GET /{id}/` on any of these four returns `405`. Work off the List rows
  (a table, or a dropdown feeding the next level down) rather than a
  separate detail screen.
- **`slug` and the `*_code` field (`country_code`/`state_code`/`city_code`/
  `thana_code`) are always server-generated.** Don't send them — they're
  read-only in the response, generated fresh on create and re-generated
  (slug only) whenever `name` changes on update.
- **Duplicate names are checked against the parent, not globally.** Two
  countries can each have a state called "Central"; what's blocked is the
  *same* name twice under the *same* parent. See each resource below for
  exactly what "parent" means at that level.
- **List embeds the parent(s) as full objects; Create/Update/Delete use
  plain ids.** A State's `country` field is a nested `{id, name, slug,
  country_code}` object in a List response, but a plain numeric id
  everywhere else (what you send on Create/Update, and what comes back in
  the Create/Update response). This is deliberate: List rows are for
  rendering a table without a separate lookup per row; Create/Update just
  need the id you already picked from a dropdown. Same pattern one level
  deeper for City (`country` + `state` nested) and Thana (`country` +
  `state` + `city` nested) — see each resource's List example below.
- **All 6 audit fields are on every row**, read-only: `created_by`,
  `creator_type`, `creator_name` (who created it), and `updated_by`,
  `updater_type`, `updater_name` (who last updated it — `null` until the
  first update). These reflect whichever Admin's token made the request.
- **`flag_path`/`flag_url` always come back `null`.** The columns exist but
  there's no image-upload step for geography rows yet (see §4 below).
- **Validation errors** are the same `{field: [messages]}` shape as every
  other endpoint in this API — see frontend-api-guide.md §4 if you haven't
  built a generic handler for that shape yet.
- **List responses** use the same limit/offset pagination envelope
  (`count`/`next`/`previous`/`results`) as every other list endpoint — see
  frontend-api-guide.md §5. **Filter query params still take a plain id**
  (`?country=124`), even though the field they filter on is nested in the
  response.

---

## 3. The four resources

### 3.1 Country

Base path: `/api/v1/geography/countries/`

#### Create — `POST`

The only field you send is `name`:
```json
{ "name": "Bangladesh" }
```
→ `201`
```json
{
  "id": 124,
  "name": "Bangladesh",
  "slug": "bangladesh",
  "country_code": "699",
  "flag_path": null,
  "flag_url": null,
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "updated_by": null,
  "updater_type": null,
  "updater_name": null
}
```

**Duplicate name — `400`** (case/spacing don't matter — compared via the
generated slug, so `"  bangladesh  "` collides with `"Bangladesh"`):
```json
{ "name": ["A country with this name already exists."] }
```

#### List — `GET /api/v1/geography/countries/?search=bangla`

`search` partial-matches `name`:
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 124,
      "name": "Bangladesh",
      "slug": "bangladesh",
      "country_code": "699",
      "flag_path": null,
      "flag_url": null,
      "created_by": 10,
      "creator_type": "admin",
      "creator_name": "Test Admin",
      "updated_by": null,
      "updater_type": null,
      "updater_name": null
    }
  ]
}
```

#### Update — `PATCH /api/v1/geography/countries/{id}/`

```json
{ "name": "Testland Updated" }
```
→ `200`
```json
{
  "id": 125,
  "name": "Testland Updated",
  "slug": "testland-updated",
  "country_code": "637",
  "flag_path": null,
  "flag_url": null,
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "updated_by": 10,
  "updater_type": "admin",
  "updater_name": "Test Admin"
}
```
Regenerates `slug`, re-runs the duplicate check (excluding itself), stamps
`updated_by`/`updater_type`/`updater_name`.

#### Delete — `DELETE /api/v1/geography/countries/{id}/`

→ `204 No Content` (empty body). Cascades — deleting a Country also deletes
every State/City/Thana under it.

### 3.2 State

Base path: `/api/v1/geography/states/`

Adds one required field on top of Country: `country` (the Country's `id`).
The duplicate check here is **scoped to that country** — the same state
name is fine under a different country.

#### Create — `POST`

```json
{ "name": "Dhaka Division", "country": 124 }
```
→ `201`
```json
{
  "id": 8,
  "country": 124,
  "name": "Dhaka Division",
  "slug": "dhaka-division",
  "state_code": "970",
  "flag_path": null,
  "flag_url": null,
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "updated_by": null,
  "updater_type": null,
  "updater_name": null
}
```

**Missing `country` — `400`:**
```json
{ "country": ["This field is required."] }
```

**Invalid `country` id — `400`:**
```json
{ "country": ["Invalid pk \"999999\" - object does not exist."] }
```

**Duplicate name in the same country — `400`:**
```json
{ "name": ["A state with this name already exists in this country."] }
```
The same name under a *different* `country` id succeeds — "Dhaka Division"
exists validly as a state name under both Bangladesh and India, for example.

#### List — `GET /api/v1/geography/states/?country=124`

`country` is exact-match; `search` partial-matches `name`. Note `country`
comes back as a **nested object**, not just an id:
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 8,
      "country": { "id": 124, "name": "Bangladesh", "slug": "bangladesh", "country_code": "699" },
      "name": "Dhaka Division",
      "slug": "dhaka-division",
      "state_code": "970",
      "flag_path": null,
      "flag_url": null,
      "created_by": 10,
      "creator_type": "admin",
      "creator_name": "Test Admin",
      "updated_by": null,
      "updater_type": null,
      "updater_name": null
    },
    {
      "id": 9,
      "country": { "id": 124, "name": "Bangladesh", "slug": "bangladesh", "country_code": "699" },
      "name": "Rajshahi Division",
      "slug": "rajshahi-division",
      "state_code": "848",
      "flag_path": null,
      "flag_url": null,
      "created_by": 10,
      "creator_type": "admin",
      "creator_name": "Test Admin",
      "updated_by": null,
      "updater_type": null,
      "updater_name": null
    }
  ]
}
```

#### Update — `PATCH /api/v1/geography/states/{id}/`

```json
{ "name": "Rajshahi Division Updated" }
```
→ `200`
```json
{
  "id": 9,
  "country": 124,
  "name": "Rajshahi Division Updated",
  "slug": "rajshahi-division-updated",
  "state_code": "848",
  "flag_path": null,
  "flag_url": null,
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "updated_by": 10,
  "updater_type": "admin",
  "updater_name": "Test Admin"
}
```
Note `country` is a plain id here, unlike in List — see §2. Re-assigning
`country` on an existing state re-checks the name against that new
country's other states.

#### Delete — `DELETE /api/v1/geography/states/{id}/`

→ `204 No Content`. Cascades to every City/Thana under it.

### 3.3 City

Base path: `/api/v1/geography/cities/`

Required fields: `name`, `country`, `state`. Two checks happen on every
write:

1. **Parent consistency** — `state` must actually belong to `country`.
   Sending a mismatched pair is rejected rather than trusting whichever one
   you sent (`country` is stored denormalized alongside `state` in the
   database, so this check is what keeps the two from drifting apart).
2. **Duplicate check, scoped to the state** — same city name allowed under
   a different state, blocked twice under the same one.

#### Create — `POST`

```json
{ "name": "Dhaka City", "country": 124, "state": 8 }
```
→ `201`
```json
{
  "id": 5,
  "country": 124,
  "state": 8,
  "name": "Dhaka City",
  "slug": "dhaka-city",
  "city_code": "847",
  "flag_path": null,
  "flag_url": null,
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "updated_by": null,
  "updater_type": null,
  "updater_name": null
}
```

**Mismatched country/state — `400`:**
```json
{ "state": ["This state does not belong to the selected country."] }
```

**Duplicate name in the same state — `400`:**
```json
{ "name": ["A city with this name already exists in this state."] }
```

#### List — `GET /api/v1/geography/cities/?state=8`

`country`/`state` are exact-match; `search` partial-matches `name`. Both
parents come back **nested**:
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 5,
      "country": { "id": 124, "name": "Bangladesh", "slug": "bangladesh", "country_code": "699" },
      "state": { "id": 8, "name": "Dhaka Division", "slug": "dhaka-division", "state_code": "970" },
      "name": "Dhaka City",
      "slug": "dhaka-city",
      "city_code": "847",
      "flag_path": null,
      "flag_url": null,
      "created_by": 10,
      "creator_type": "admin",
      "creator_name": "Test Admin",
      "updated_by": null,
      "updater_type": null,
      "updater_name": null
    },
    {
      "id": 6,
      "country": { "id": 124, "name": "Bangladesh", "slug": "bangladesh", "country_code": "699" },
      "state": { "id": 8, "name": "Dhaka Division", "slug": "dhaka-division", "state_code": "970" },
      "name": "Savar",
      "slug": "savar",
      "city_code": "278",
      "flag_path": null,
      "flag_url": null,
      "created_by": 10,
      "creator_type": "admin",
      "creator_name": "Test Admin",
      "updated_by": null,
      "updater_type": null,
      "updater_name": null
    }
  ]
}
```

#### Update — `PATCH /api/v1/geography/cities/{id}/`

```json
{ "name": "Savar Updated" }
```
→ `200`
```json
{
  "id": 6,
  "country": 124,
  "state": 8,
  "name": "Savar Updated",
  "slug": "savar-updated",
  "city_code": "278",
  "flag_path": null,
  "flag_url": null,
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "updated_by": 10,
  "updater_type": "admin",
  "updater_name": "Test Admin"
}
```
`country`/`state` are plain ids here, same as Create — only List nests them.

#### Delete — `DELETE /api/v1/geography/cities/{id}/`

→ `204 No Content`. Cascades to every Thana under it.

### 3.4 Thana

Base path: `/api/v1/geography/thanas/`

Required fields: `name`, `country`, `state`, `city` — one level deeper than
City, same idea:

1. **Parent consistency**, checked down the whole chain: `state` must
   belong to `country`, and `city` must belong to `state`.
2. **Duplicate check, scoped to the city** — same thana name allowed under
   a different city, blocked twice under the same one.

#### Create — `POST`

```json
{ "name": "Dhanmondi", "country": 124, "state": 8, "city": 5 }
```
→ `201`
```json
{
  "id": 3,
  "country": 124,
  "state": 8,
  "city": 5,
  "name": "Dhanmondi",
  "slug": "dhanmondi",
  "thana_code": "626",
  "flag_path": null,
  "flag_url": null,
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "updated_by": null,
  "updater_type": null,
  "updater_name": null
}
```

**Mismatched `city`/`state` — `400`:**
```json
{ "city": ["This city does not belong to the selected state."] }
```
(A mismatched `country`/`state` pair gives the same `{"state": [...]}` shape
as City — that check runs first.)

**Duplicate name in the same city — `400`:**
```json
{ "name": ["A thana with this name already exists in this city."] }
```

#### List — `GET /api/v1/geography/thanas/?city=5`

`country`/`state`/`city` are exact-match; `search` partial-matches `name`.
All three parents come back **nested**:
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 3,
      "country": { "id": 124, "name": "Bangladesh", "slug": "bangladesh", "country_code": "699" },
      "state": { "id": 8, "name": "Dhaka Division", "slug": "dhaka-division", "state_code": "970" },
      "city": { "id": 5, "name": "Dhaka City", "slug": "dhaka-city", "city_code": "847" },
      "name": "Dhanmondi",
      "slug": "dhanmondi",
      "thana_code": "626",
      "flag_path": null,
      "flag_url": null,
      "created_by": 10,
      "creator_type": "admin",
      "creator_name": "Test Admin",
      "updated_by": null,
      "updater_type": null,
      "updater_name": null
    },
    {
      "id": 4,
      "country": { "id": 124, "name": "Bangladesh", "slug": "bangladesh", "country_code": "699" },
      "state": { "id": 8, "name": "Dhaka Division", "slug": "dhaka-division", "state_code": "970" },
      "city": { "id": 5, "name": "Dhaka City", "slug": "dhaka-city", "city_code": "847" },
      "name": "Mirpur",
      "slug": "mirpur",
      "thana_code": "148",
      "flag_path": null,
      "flag_url": null,
      "created_by": 10,
      "creator_type": "admin",
      "creator_name": "Test Admin",
      "updated_by": null,
      "updater_type": null,
      "updater_name": null
    }
  ]
}
```

#### Update — `PATCH /api/v1/geography/thanas/{id}/`

```json
{ "name": "Mirpur Updated" }
```
→ `200`
```json
{
  "id": 4,
  "country": 124,
  "state": 8,
  "city": 5,
  "name": "Mirpur Updated",
  "slug": "mirpur-updated",
  "thana_code": "148",
  "flag_path": null,
  "flag_url": null,
  "created_by": 10,
  "creator_type": "admin",
  "creator_name": "Test Admin",
  "updated_by": 10,
  "updater_type": "admin",
  "updater_name": "Test Admin"
}
```
`country`/`state`/`city` are plain ids here, same as Create — only List
nests them.

#### Delete — `DELETE /api/v1/geography/thanas/{id}/`

→ `204 No Content`.

---

## 4. What's deliberately not here yet

- **Country/State/City/Thana flag images.** `flag_path`/`flag_url` exist on
  every row above but there's no upload endpoint for them yet — same
  reasoning as the profile-picture upload on Admin/Seller/Buyer (see
  frontend-api-guide.md §11), just not built for geography.
- **Bulk import.** Every row is created one at a time through these
  endpoints. There's no CSV/legacy-data import step.

If frontend work needs either of these sooner, flag it.
