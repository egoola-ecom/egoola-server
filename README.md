# egoola-server

Django + DRF backend for the Egoola marketplace rebuild. Serves egoola-web,
egoola-app, and egoola-seller from one shared, versioned API — see
`Egoola Rebuild Guideline.docx` (Section 4) in `egoola-document` for the
full architecture, and `Egoola Rebuild Phase Tracker.docx` for the task
list this is being built against.

## Local setup

```bash
python -m venv venv
./venv/Scripts/activate       # venv\Scripts\activate on native Windows shells
pip install -r requirements.txt
cp .env.example .env          # then fill in your local Postgres password
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Requires a local PostgreSQL 16+ database (see `.env.example` for the
connection settings) — created by hand once, then owned by Django's
migrations from that point on. API docs are served at `/api/docs/` once
the server is running.

## App layout

One Django app per module of the Database Redesign document
(`egoola-document/database/Egolola DB Re-Design.docx`, Section 3), plus
`core` for the shared audit-trail base model every other app builds on:

`core`, `geography`, `accounts`, `catalog`, `bidding`, `orders`,
`inquiries`, `messaging`, `engagement`, `notifications`, `cms`.

Every endpoint is versioned: `/api/v1/<app>/...`.
