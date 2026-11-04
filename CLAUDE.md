# egoola-server

Django + Django REST Framework + PostgreSQL. This is the ONE shared backend for the
Egoola rebuild — owns all data, business logic, auth, and the API. No other repo
touches the database directly; they all call this repo's API.

You are (or work alongside) the "Egoola Backend" session — see `../CLAUDE.md` for the
shared team rules and `../egoola-document/Egoola_Knowledge_Brief.md` for full project
context before making architecture decisions.

Git commits in this repo: no Claude/Anthropic attribution of any kind — no
`Co-Authored-By`, no "Generated with Claude Code" line, nothing. Plain commit
messages only.

Conventions specific to this repo:
- Models are the schema source of truth for the redesign — don't hand-port the old
  MySQL DDL; write Django models from `egoola-document/database/Egolola DB Re-Design.docx`
  and let `migrate` build Postgres.
- API versioned under `/api/v1/`; docs via drf-spectacular at `/api/docs/`.
- You are the first mover on every phase — nothing else in the team starts a phase's
  work until you've shipped that phase's API.

## App directory structure

Default: flat files per role inside the app (`buyer_views.py`, `seller_serializers.py`,
`admin_order_views.py`, `public_urls.py`, etc.) — this is fine and expected for a
smaller app.

**Threshold:** once an app's non-migration `.py` file count (excluding `__init__.py`)
passes **12**, restructure it into role folders in the same change that pushes it over
— don't wait to be asked:

```
apps/<app>/
  models.py, admin.py, apps.py, services.py, migrations/   # common, stays at root
  common_serializers.py        # only if 2+ roles reuse the same serializer shapes
  admin_api/{urls,views,serializers,filters}.py
  buyer/{urls,views,serializers,filters}.py
  seller/{urls,views,serializers,filters}.py
  public/{urls,views,serializers}.py
```

Only create the role folders that app actually has (no `seller/` if it has no
seller-facing endpoints, etc.), and only the files a role actually needs (no
`filters.py` if that role has no filterable list).

**Never name the admin folder `admin`** — it shadows the app's own `admin.py`
(Django's admin-site autodiscovery imports a module literally named `admin` per
app), which silently stops registering that app's models on `/admin/` with no
error. Use `admin_api/`.

After restructuring: update every `config/urls.py` include() that pointed at the
old flat module, run `manage.py check`, and diff the full resolved URL list
(`django.urls.get_resolver()`, not just a visual read) before vs. after — on both
`/api/v1/...` and `/admin/...` — to prove no path changed and the admin site
still registers everything. `manage.py check` and the API smoke tests alone will
NOT catch an `admin.py` shadowing bug.
