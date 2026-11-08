# Egoola Update Guide (ship new code to a running server)

Use this guide when the server is **already set up** (see [`vps-setup-guide.md`](vps-setup-guide.md)) and you want
it to run the newest code from GitHub — for example after a teammate merged a pull request.

It covers:

- updating the **backend** (egoola-server) and the **frontend** (egoola-web), step by step, with what each command
  does and why
- a one-command **deploy script**
- changing settings (`.env`), switching branches, going **back** to an older version, restoring a backup
- regular server maintenance

Everything here is typed **on the server** as the `egoola` user. Log in from your Mac first:

```bash
ssh egoola@VPS_IP
```

Your prompt must look like `egoola@srv...:~$`. If it shows your Mac's name, you are not on the server.

---

## Table of contents

- [0. The paths used in this guide](#0-the-paths-used-in-this-guide)
- [1. What needs to happen after a change?](#1-what-needs-to-happen-after-a-change)
- [2. Before every update](#2-before-every-update)
- [3. Update the backend, step by step](#3-update-the-backend-step-by-step)
- [4. Update the frontend, step by step](#4-update-the-frontend-step-by-step)
- [5. Check the update worked](#5-check-the-update-worked)
- [6. One-command deploy script](#6-one-command-deploy-script)
- [7. Changing settings (.env)](#7-changing-settings-env)
- [8. Deploying a different branch](#8-deploying-a-different-branch)
- [9. Something broke: going back (rollback)](#9-something-broke-going-back-rollback)
- [10. Restore the database from a backup](#10-restore-the-database-from-a-backup)
- [11. Changing server config files](#11-changing-server-config-files)
- [12. Regular server maintenance](#12-regular-server-maintenance)
- [13. Troubleshooting after an update](#13-troubleshooting-after-an-update)
- [14. Cheat sheet](#14-cheat-sheet)

---

## 0. The paths used in this guide

| Name | Path on the dev server |
|---|---|
| `BACKEND_DIR` | `/home/egoola/var/www/backend/egoola-server` |
| `MEDIA_DIR` | `/home/egoola/var/www/backend/media` |
| `FRONTEND_DIR` | `/home/egoola/var/www/frontend/egoola-web` |

If your server uses other folders, replace them everywhere below.

---

## 1. What needs to happen after a change?

Not every change needs every step. This table tells you which steps a change needs. When you are not sure, just
run **all** the steps — every one of them is safe to repeat.

### Backend (egoola-server)

| What changed in the code | `git pull` | `uv sync` | `migrate` | `collectstatic` | restart Gunicorn |
|---|:-:|:-:|:-:|:-:|:-:|
| Python code only (views, serializers, services...) | ✅ | | | | ✅ |
| `pyproject.toml` / `uv.lock` (new or upgraded package) | ✅ | ✅ | | | ✅ |
| `models.py` → a new file in some `migrations/` folder | ✅ | | ✅ | | ✅ |
| Admin look, or a new package with its own CSS/JS | ✅ | | | ✅ | ✅ |
| `.env` on the server (no code change) | | | | | ✅ |

**Why Gunicorn must restart:** Gunicorn loads the Python code into memory when it starts. Until it restarts, it
keeps running the **old** code, even though the files on disk are new.

### Frontend (egoola-web)

| What changed | `git pull` | `npm ci` | `npm run build` | restart pm2 |
|---|:-:|:-:|:-:|:-:|
| Pages, components, styles | ✅ | | ✅ | ✅ |
| `package.json` / `package-lock.json` | ✅ | ✅ | ✅ | ✅ |
| `.env.production` (`NEXT_PUBLIC_API_URL`) | | | ✅ | ✅ |

**Why the frontend needs a build every time:** The live site does not run your source files. It runs the
optimized copy that `npm run build` creates in `.next/`. New source code does nothing until you build again.

### Order: backend first, then frontend

The frontend calls the backend's API. If a new frontend expects a new API field, the backend must already have it.
So the safe order is always: **backend → check → frontend → check.**

---

## 2. Before every update

### 2.1 See what is about to change

```bash
cd /home/egoola/var/www/backend/egoola-server
git fetch
git status
git log --oneline HEAD..origin/main
```

- `git fetch` downloads the news from GitHub but does **not** change your files yet.
- `git status` must say `nothing to commit, working tree clean`. If it lists changed files, someone edited code
  directly on the server — see [13](#13-troubleshooting-after-an-update) before going on.
- `git log HEAD..origin/main` lists the new commits you are about to get. Replace `main` with your branch name if
  you deploy another branch.

See if any of them contain database changes:

```bash
git diff --stat HEAD origin/main -- '*/migrations/*'
```

If this prints anything, the update changes the database — **take a backup first** (2.2).

### 2.2 Back up the database

Always do this before an update with migrations. It takes seconds and makes a bad update reversible.

```bash
mkdir -p ~/backups
pg_dump -h localhost -U egoola_dev -Fc egoola_dev > ~/backups/before_update_$(date +%F_%H%M).dump
ls -lh ~/backups | tail -3
```

- `-Fc` is Postgres's compact "custom" format, which `pg_restore` can read (see [10](#10-restore-the-database-from-a-backup)).
- It asks for the database password, unless you set up `~/.pgpass` (setup guide 18.2).
- `ls` should show the new file with a size bigger than 0.

### 2.3 Remember the current version

Write down where you are now, so you can come back if needed:

```bash
cd /home/egoola/var/www/backend/egoola-server && git log -1 --oneline
cd /home/egoola/var/www/frontend/egoola-web && git log -1 --oneline
```

Each prints something like `26747b4 docs(accounts): ...`. The first word (`26747b4`) is the commit id.

---

## 3. Update the backend, step by step

```bash
cd /home/egoola/var/www/backend/egoola-server
```

### 3.1 Download the new code

```bash
git pull
```

**What it does:** gets the newest commits of the current branch from GitHub and updates the files.

**Expected:** `Fast-forward` and a list of changed files, or `Already up to date.`

If it says `Your local changes would be overwritten` → see [13](#13-troubleshooting-after-an-update).

### 3.2 Install packages

```bash
uv sync --locked --no-dev
```

**What it does:** makes `.venv/` match `uv.lock` exactly — installs new packages, upgrades changed ones, removes
deleted ones. If nothing changed, it finishes in a second.

**Why `--locked`:** if someone changed `pyproject.toml` but forgot to commit the updated `uv.lock`, this stops with
an error instead of quietly installing untested versions. The fix then belongs in the repo (run `uv lock` on a
developer machine and commit it), not on the server.

### 3.3 Update the database

```bash
uv run python manage.py migrate
```

**What it does:** applies every new migration file to the database (new tables, new columns, etc.). Migrations
already applied are skipped, so it is always safe to run.

**Expected:** `Applying <app>.<number>_<name>... OK` lines, or `No migrations to apply.`

You can see what is pending before applying:

```bash
uv run python manage.py showmigrations | grep '\[ \]'
```

Lines with `[ ]` are not applied yet.

### 3.4 Update static files

```bash
uv run python manage.py collectstatic --noinput
```

**What it does:** copies the CSS/JS/images of Django's admin and the API docs into `staticfiles/`. Fast when
nothing changed.

### 3.5 Check for configuration problems

```bash
uv run python manage.py check
```

**Expected:** `System check identified no issues (0 silenced).`

### 3.6 Restart the backend

```bash
sudo systemctl restart gunicorn
sudo systemctl status gunicorn --no-pager
```

**What it does:** stops the old Gunicorn and starts it again with the new code. The API is unavailable for about
1–2 seconds.

**Expected:** `active (running)`.

### 3.7 Check it answers

```bash
curl -I -H "Host: dev.egoola.com" http://127.0.0.1:8000/api/docs/
```

**Expected:** `HTTP/1.1 200 OK`. If not, read the log:

```bash
journalctl -u gunicorn -n 50 --no-pager
```

---

## 4. Update the frontend, step by step

```bash
cd /home/egoola/var/www/frontend/egoola-web
```

### 4.1 Download the new code

```bash
git pull
```

Same as 3.1.

### 4.2 Install packages

```bash
npm ci
```

**What it does:** deletes `node_modules/` and installs exactly what `package-lock.json` lists. Clean and
repeatable. Takes a minute.

**Why `npm ci` and not `npm install`:** `npm install` can change `package-lock.json` on the server, which makes
the server different from the repo and blocks the next `git pull`.

You can skip `npm ci` when `package.json` and `package-lock.json` did not change — but running it is always safe.

### 4.3 Build

```bash
npm run build
```

**What it does:** creates the new optimized site in `.next/`. This takes a few minutes and uses a lot of memory.

**The old site keeps running while it builds**, so visitors see no downtime yet.

If the build **fails**, stop here: do not restart pm2. The old version keeps running. Read the error, fix it in
the repo, and pull again. (A build that fails in the middle can leave `.next/` half-written; the old process keeps
serving what it already loaded, but do not restart it until a build succeeds.)

### 4.4 Restart the frontend

```bash
pm2 restart frontend
pm2 status
```

**What it does:** restarts Next.js so it serves the new build. Downtime: about 1–3 seconds.

**Expected:** `frontend` is `online`, and its `↺` (restart) counter went up by one.

### 4.5 Check it answers

```bash
curl -I http://127.0.0.1:3000
```

**Expected:** `200 OK`. If not: `pm2 logs frontend --lines 50`.

---

## 5. Check the update worked

In your browser (use a private window or hard reload — **Cmd+Shift+R** — to skip the browser cache):

| Address | Expected |
|---|---|
| `https://dev.egoola.com` | Website shows the new changes |
| `https://dev.egoola.com/api/docs/` | API docs load and show any new endpoints |
| `https://dev.egoola.com/admin/` | Admin login works |

Then test the feature that was changed (log in, open the page, submit the form...).

Quick health check from the server:

```bash
sudo systemctl is-active gunicorn nginx postgresql
pm2 status
```

All three print `active`; `frontend` is `online`.

---

## 6. One-command deploy script

Typing every step by hand is fine for learning. For daily use, save them in a script.

### 6.1 Create the script (once)

```bash
nano ~/deploy.sh
```

Paste:

```bash
#!/usr/bin/env bash
# Deploys the newest code of the current branch for egoola-server and egoola-web.
# Usage:  ~/deploy.sh            -> backend + frontend
#         ~/deploy.sh backend    -> backend only
#         ~/deploy.sh frontend   -> frontend only
set -euo pipefail

BACKEND_DIR=/home/egoola/var/www/backend/egoola-server
FRONTEND_DIR=/home/egoola/var/www/frontend/egoola-web
TARGET="${1:-all}"

deploy_backend() {
  echo "==> Backend: $BACKEND_DIR"
  cd "$BACKEND_DIR"
  git pull --ff-only
  uv sync --locked --no-dev
  uv run python manage.py migrate --noinput
  uv run python manage.py collectstatic --noinput
  uv run python manage.py check
  sudo systemctl restart gunicorn
  sleep 2
  curl -fsS -o /dev/null -H "Host: dev.egoola.com" http://127.0.0.1:8000/api/docs/
  echo "==> Backend OK: $(git log -1 --oneline)"
}

deploy_frontend() {
  echo "==> Frontend: $FRONTEND_DIR"
  cd "$FRONTEND_DIR"
  git pull --ff-only
  npm ci
  npm run build
  pm2 restart frontend
  sleep 3
  curl -fsS -o /dev/null http://127.0.0.1:3000
  echo "==> Frontend OK: $(git log -1 --oneline)"
}

case "$TARGET" in
  backend)  deploy_backend ;;
  frontend) deploy_frontend ;;
  all)      deploy_backend; deploy_frontend ;;
  *) echo "Usage: $0 [backend|frontend|all]"; exit 1 ;;
esac

echo "==> Deploy finished."
```

Save (Ctrl+O, Enter), exit (Ctrl+X), and make it runnable:

```bash
chmod +x ~/deploy.sh
```

What makes this script safe:

| Part | Why |
|---|---|
| `set -euo pipefail` | **Stop at the first error.** For example, if the build fails, pm2 is **not** restarted, so the old site keeps running. |
| `git pull --ff-only` | Only accept a clean "move forward". If the server's copy has local edits or a different history, it stops instead of creating a merge. |
| Backend before frontend | The new frontend may need the new API. |
| `curl -f ...` at the end of each part | Fails the script if the app does not answer after the restart, so you notice immediately. |

### 6.2 Use it

Back up the database first if there are migrations (section 2.2), then:

```bash
~/deploy.sh
```

Or only one side:

```bash
~/deploy.sh backend
~/deploy.sh frontend
```

**Expected last line:** `==> Deploy finished.` If the script stops early, the last lines show which command
failed. Fix the cause, then run it again — every step is safe to repeat.

---

## 7. Changing settings (.env)

### 7.1 Backend `.env`

```bash
cd /home/egoola/var/www/backend/egoola-server
nano .env
sudo systemctl restart gunicorn
```

Settings are read only when Gunicorn starts, so **always restart** after editing.

Rules for `.env`:

- One `KEY=value` per line. No spaces around `=`. No quotes needed.
- Each key **once**. If a key appears twice, the last one wins silently.
- Lists (`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`) are comma-separated, no spaces.
- Never commit `.env`; never paste its contents into a chat.

If a new version of the code needs a **new** setting, it is added to `.env.example` in the repo. Compare after each
pull:

```bash
diff <(grep -oE '^[A-Z_]+=' .env.example | sort) <(grep -oE '^[A-Z_]+=' .env | sort)
```

Lines starting with `<` are keys in `.env.example` that your `.env` is missing.

### 7.2 Changing the database password

1. Make a new password: `openssl rand -base64 24 | tr -d '/+='`
2. Set it in Postgres:
   ```bash
   sudo -u postgres psql -c "\password egoola_dev"
   ```
3. Put the same value in `.env` → `DB_PASSWORD=...`
4. `sudo systemctl restart gunicorn`
5. Update `~/.pgpass` if you use the backup cron job.

### 7.3 Changing `DJANGO_SECRET_KEY`

Generate a new one (setup guide 11.2), put it in `.env`, restart Gunicorn. **Everyone is logged out** (all JWT
tokens and admin sessions become invalid). Do this if the key ever leaked.

### 7.4 Frontend `.env.production`

```bash
cd /home/egoola/var/www/frontend/egoola-web
nano .env.production
npm run build
pm2 restart frontend
```

`NEXT_PUBLIC_*` values are written into the site during the **build**, so restart alone is not enough — you must
build again.

---

## 8. Deploying a different branch

To test a feature branch on dev:

```bash
cd /home/egoola/var/www/backend/egoola-server
git fetch
git checkout feature/my-branch
```

Then run the normal steps (3.2 → 3.7). From now on `git pull` and `~/deploy.sh` follow this branch.

Same for the frontend in `FRONTEND_DIR` (then steps 4.2 → 4.5).

To go back to `main`:

```bash
git checkout main
git pull
```

> **Careful with migrations on branches.** If the feature branch added migrations and you ran `migrate`, the
> database now has those changes. Going back to `main` does **not** undo them. Either undo them first (see 9.3)
> or restore the backup from before (section 10).

To see which branch is deployed:

```bash
git -C /home/egoola/var/www/backend/egoola-server branch --show-current
git -C /home/egoola/var/www/frontend/egoola-web branch --show-current
```

---

## 9. Something broke: going back (rollback)

Stay calm. Find the cause first (section 13); often it is a small `.env` or config fix. If you need the old version
back right now:

### 9.1 Find the last good commit

```bash
cd /home/egoola/var/www/backend/egoola-server     # or FRONTEND_DIR
git log --oneline -10
```

Pick the commit that was running before (you wrote it down in 2.3).

### 9.2 Roll back the frontend

```bash
cd /home/egoola/var/www/frontend/egoola-web
git checkout <good-commit-id>
npm ci
npm run build
pm2 restart frontend
```

### 9.3 Roll back the backend

**Without migrations in between** (the bad update did not change the database):

```bash
cd /home/egoola/var/www/backend/egoola-server
git checkout <good-commit-id>
uv sync --locked --no-dev
uv run python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

**With migrations in between**, the database must go back too. Two ways:

- **Undo the migrations** (while you are still on the new code — the new migration files are needed to undo
  them). For each app that got a new migration, migrate back to the number before it:
  ```bash
  uv run python manage.py showmigrations catalog
  uv run python manage.py migrate catalog 0012
  ```
  (`catalog` and `0012` are examples — use the app name and the last **good** migration number.) Then do the
  `git checkout <good-commit-id>` steps above.
- **Or restore the backup** from 2.2 (section 10). Simpler and always works, but any data written after the
  backup is lost.

### 9.4 Get back on the branch afterwards

`git checkout <commit>` leaves you in a "detached HEAD" state: `git pull` will not work. After the problem is fixed
in the repo:

```bash
git checkout main
git pull
```

Then deploy normally.

---

## 10. Restore the database from a backup

> **This replaces the whole database with the backup.** Every change made after the backup was taken is lost.
> Be sure you have the right file before you start.

```bash
ls -lh ~/backups
```

Stop the backend so nothing writes during the restore:

```bash
sudo systemctl stop gunicorn
```

**For a `.dump` file** (made with `pg_dump -Fc`, as in 2.2):

```bash
pg_restore -h localhost -U egoola_dev -d egoola_dev --clean --if-exists --no-owner ~/backups/before_update_YYYY-MM-DD_HHMM.dump
```

**For a `.sql.gz` file** (the daily cron backup):

```bash
sudo -u postgres psql -c "DROP DATABASE egoola_dev WITH (FORCE);"
sudo -u postgres psql -c "CREATE DATABASE egoola_dev OWNER egoola_dev ENCODING 'UTF8';"
gunzip -c ~/backups/egoola_dev_YYYY-MM-DD.sql.gz | psql -h localhost -U egoola_dev -d egoola_dev
```

Start the backend again:

```bash
sudo systemctl start gunicorn
```

Make sure the code matches the restored database: the checked-out commit should be the one that was running when
the backup was taken. Check with:

```bash
uv run python manage.py showmigrations | grep '\[ \]'
```

No output means code and database agree.

---

## 11. Changing server config files

### 11.1 Nginx

```bash
sudo nano /etc/nginx/sites-available/egoola-dev
sudo nginx -t
sudo systemctl reload nginx
```

**Always** run `nginx -t` before reloading. `reload` (not `restart`) applies the change without dropping open
connections. Note: Certbot added the HTTPS lines to this file — keep them.

### 11.2 Gunicorn service

```bash
sudo nano /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

`daemon-reload` is required after editing any service file; otherwise systemd keeps using the old one.

### 11.3 pm2

If you change how the frontend is started (e.g. the port), delete and recreate it, then save:

```bash
cd /home/egoola/var/www/frontend/egoola-web
pm2 delete frontend
pm2 start npm --name frontend -- start -- -p 3000
pm2 save
```

---

## 12. Regular server maintenance

### Every week or two

**Install security updates:**

```bash
sudo apt update && sudo apt upgrade -y
```

If it says a restart is required (or `/var/run/reboot-required` exists), reboot at a quiet time:

```bash
[ -f /var/run/reboot-required ] && echo "Reboot needed"
sudo reboot
```

Everything starts again by itself (Gunicorn via systemd, the frontend via pm2). Check after one minute with
section 5.

**Check disk space:**

```bash
df -h /
du -sh ~/backups ~/var/www/backend/media
```

Keep `Use%` for `/` under about 80%. Old backups and big uploads are the usual reasons it fills up.

**Check memory:**

```bash
free -h
```

### Every month

**Check the certificate renewal still works:**

```bash
sudo certbot renew --dry-run
sudo certbot certificates
```

`certificates` shows the expiry date. Certbot renews automatically about 30 days before expiry.

**Clean old logs** (keeps the last 2 weeks):

```bash
sudo journalctl --vacuum-time=14d
pm2 flush
```

### When the dependencies of the tools change

- **uv:** `uv self update`
- **pm2:** `sudo npm i -g pm2@latest && pm2 update`
- **Node.js major version** (e.g. 22 → 24): only when egoola-web requires it. Repeat the NodeSource step from the
  setup guide with the new number, then `npm ci && npm run build && pm2 restart frontend`.
- **Python version:** nothing to do on the server. When the repo's `.python-version` changes, `uv sync` downloads
  the new Python by itself.

---

## 13. Troubleshooting after an update

### `git pull` says "Your local changes would be overwritten"

Someone edited files directly on the server. See what:

```bash
git status
git diff
```

- If the edits are not needed: `git restore .` throws them away (**permanent** — check the diff first), then
  `git pull`.
- If they are needed: copy the diff, make the same change in the repo through a normal pull request, then
  `git restore .` and `git pull`.

Never fix code on the server directly — the next pull will conflict with it, and the fix will be lost or block the
deploy.

### `git pull` says "Not possible to fast-forward" / "divergent branches"

The server's copy has commits that are not on GitHub (or GitHub's history was rewritten). If the server should
simply match GitHub:

```bash
git fetch
git status
git reset --hard origin/main
```

`reset --hard` **permanently** throws away anything on the server that is not on GitHub. Look at `git status`
and `git log origin/main..HEAD` first.

### `git pull` says "Permission denied (publickey)" or "Repository not found"

The deploy key does not work any more (removed on GitHub, or the remote address changed). Check:

```bash
ssh -T github-server
ssh -T github-web
git remote -v
```

The remote must use `github-server:` / `github-web:`, not `github.com:`. See setup guide section 9.

### `uv sync --locked` fails: "The lockfile needs to be updated"

`pyproject.toml` changed but the new `uv.lock` was not committed. Fix it in the repo (a developer runs `uv lock`
and commits `uv.lock`), then pull again. Do not run `uv lock` on the server.

### `migrate` fails

Read the error. Common ones:

- `password authentication failed` → `.env` `DB_PASSWORD` does not match Postgres (section 7.2).
- `relation ... already exists` / `column ... does not exist` → the database and migration files disagree,
  often because a branch with migrations was deployed and left. Restore the backup (section 10) or ask the
  backend developer.

The old Gunicorn keeps running the old code until you restart it, so a failed migrate does not immediately break
the site — but **do not restart** until migrate succeeds.

### `npm run build` fails

- `JavaScript heap out of memory` / the process is "Killed" → not enough memory. Check `free -h` (swap must
  exist). Stop other heavy work and retry.
- Type or lint errors → a code problem. Fix in the repo, pull, build again. The old site keeps running meanwhile.

### Site shows `502 Bad Gateway` after the update

The app behind Nginx is not running.

```bash
sudo systemctl status gunicorn --no-pager
journalctl -u gunicorn -n 50 --no-pager
pm2 status
pm2 logs frontend --lines 50
```

A Python import error after `git pull` usually means `uv sync` was skipped. Run 3.2, then restart.

### New change not visible in the browser

1. Hard reload (**Cmd+Shift+R**) or open a private window.
2. Frontend change: did you run `npm run build` **and** `pm2 restart frontend`?
3. Backend change: did you restart Gunicorn?
4. Are you on the right branch and commit? `git log -1 --oneline` in each folder.

---

## 14. Cheat sheet

```bash
# Log in
ssh egoola@VPS_IP

# Full deploy (back up first if there are migrations)
pg_dump -h localhost -U egoola_dev -Fc egoola_dev > ~/backups/before_update_$(date +%F_%H%M).dump
~/deploy.sh

# Backend by hand
cd /home/egoola/var/www/backend/egoola-server
git pull
uv sync --locked --no-dev
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

# Frontend by hand
cd /home/egoola/var/www/frontend/egoola-web
git pull
npm ci
npm run build
pm2 restart frontend

# What is deployed?
git -C /home/egoola/var/www/backend/egoola-server log -1 --oneline
git -C /home/egoola/var/www/frontend/egoola-web log -1 --oneline

# Logs
journalctl -u gunicorn -f
pm2 logs frontend
sudo tail -f /var/log/nginx/error.log
```
