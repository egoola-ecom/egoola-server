# egoola-server

Django + DRF backend for the Egoola marketplace rebuild. Serves egoola-web,
egoola-app, and egoola-seller from one shared, versioned API — see
`Egoola Rebuild Guideline.docx` (Section 4) in `egoola-document` for the
full architecture, and `Egoola Rebuild Phase Tracker.docx` for the task
list this is being built against.

## Local setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/) — install it
once per machine (see uv's docs for your OS), then:

```bash
uv sync                       # creates .venv and installs the locked dependencies
cp .env.example .env          # then fill in your local Postgres password
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

`uv sync` reads `pyproject.toml` and `uv.lock` and pins the interpreter to
the version in `.python-version` (3.12) — no manual `venv`/`pip` steps
needed. Every management command runs through `uv run` so it always uses
that same environment; activating `.venv` by hand (`.venv\Scripts\activate`)
works too if you prefer running `python manage.py ...` directly.

Requires a local PostgreSQL 16+ database (see `.env.example` for the
connection settings) — created by hand once, then owned by Django's
migrations from that point on.

## API documentation

Once `runserver` is up, the API docs are available at:

- `http://127.0.0.1:8000/api/docs/` — Swagger UI, browsable and interactive
- `http://127.0.0.1:8000/api/schema/` — the raw OpenAPI 3 schema (YAML) that Swagger UI is generated from

## App layout

One Django app per module of the Database Redesign document
(`egoola-document/database/Egolola DB Re-Design.docx`, Section 3), plus
`core` for the shared audit-trail base model every other app builds on:

`core`, `geography`, `accounts`, `catalog`, `bidding`, `orders`,
`inquiries`, `messaging`, `engagement`, `notifications`, `cms`.

Every endpoint is versioned: `/api/v1/<app>/...`.
