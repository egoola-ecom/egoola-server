# egoola-server

Django + Django REST Framework + PostgreSQL. This is the ONE shared backend for the
Egoola rebuild — owns all data, business logic, auth, and the API. No other repo
touches the database directly; they all call this repo's API.

You are (or work alongside) the "Egoola Backend" session — see `../CLAUDE.md` for the
shared team rules and `../egoola-document/Egoola_Knowledge_Brief.md` for full project
context before making architecture decisions.

Conventions specific to this repo:
- Models are the schema source of truth for the redesign — don't hand-port the old
  MySQL DDL; write Django models from `egoola-document/database/Egolola DB Re-Design.docx`
  and let `migrate` build Postgres.
- API versioned under `/api/v1/`; docs via drf-spectacular at `/api/docs/`.
- You are the first mover on every phase — nothing else in the team starts a phase's
  work until you've shipped that phase's API.
