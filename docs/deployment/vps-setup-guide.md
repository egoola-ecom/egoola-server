# Egoola VPS Setup Guide (from an empty server to a live site)

This guide sets up the whole Egoola stack on one fresh Linux server (a VPS):

- **egoola-server** — the Django backend (API + admin), run by **Gunicorn**
- **egoola-web** — the Next.js frontend, run by **pm2**
- **PostgreSQL** — the database
- **Nginx** — the "front door" that receives every visitor and sends them to the right app
- **Certbot** — gives the site a free HTTPS certificate
- **Cloudflare DNS** — makes the domain name point to the server

It was written while setting up `dev.egoola.com` on a Hostinger KVM 1 VPS (1 vCPU, 4 GB RAM, Ubuntu 26.04).
Follow it top to bottom on a new VPS and you get the same result. Every step says **what** to do, **why** you do
it, and **how to check** that it worked. Do not skip the checks — a problem is much easier to fix at the step
where it starts.

To update a server that is already running, use [`update-guide.md`](update-guide.md) instead.

---

## Table of contents

- [0. Before you start](#0-before-you-start)
- [1. Create the VPS and add your SSH key](#1-create-the-vps-and-add-your-ssh-key)
- [2. First login and system update](#2-first-login-and-system-update)
- [3. Create your own user (stop using root)](#3-create-your-own-user-stop-using-root)
- [4. Turn on the firewall](#4-turn-on-the-firewall)
- [5. Add swap memory](#5-add-swap-memory)
- [6. Lock down SSH](#6-lock-down-ssh)
- [7. Install the software](#7-install-the-software)
- [8. Create the PostgreSQL database](#8-create-the-postgresql-database)
- [9. Give the server access to GitHub (deploy keys)](#9-give-the-server-access-to-github-deploy-keys)
- [10. Download the code](#10-download-the-code)
- [11. Set up the backend (egoola-server)](#11-set-up-the-backend-egoola-server)
- [12. Run the backend forever with Gunicorn + systemd](#12-run-the-backend-forever-with-gunicorn--systemd)
- [13. Set up the frontend (egoola-web)](#13-set-up-the-frontend-egoola-web)
- [14. Configure Nginx](#14-configure-nginx)
- [15. Point the domain to the server (Cloudflare DNS)](#15-point-the-domain-to-the-server-cloudflare-dns)
- [16. Get the HTTPS certificate (Certbot)](#16-get-the-https-certificate-certbot)
- [17. Final checks](#17-final-checks)
- [18. Optional extras](#18-optional-extras)
- [19. Troubleshooting](#19-troubleshooting)
- [20. Mistakes we actually made (learn from them)](#20-mistakes-we-actually-made-learn-from-them)
- [21. Quick reference](#21-quick-reference)

---

## 0. Before you start

### 0.1 How the pieces fit together

```
                    Visitor's browser
                           |
                https://dev.egoola.com
                           |
              Cloudflare DNS (name -> server IP)
                           |
                 +---------v----------+
                 |       Nginx        |  ports 80 / 443, holds the HTTPS certificate
                 +---------+----------+
        /api/ /admin/ /static/    |   /media/          everything else (/)
                 |              |                         |
      +----------v---------+    v                +--------v---------+
      | Gunicorn :8000     |  files on disk      | Next.js :3000    |
      | Django (egoola-    |  backend/media/     | (egoola-web,     |
      | server)            |                     |  run by pm2)     |
      +----------+---------+                     +------------------+
                 |
      +----------v---------+
      | PostgreSQL :5432   |  only reachable from inside the server
      +--------------------+
```

In plain words:

- The visitor only ever talks to **Nginx**.
- Nginx looks at the address. If it starts with `/api/`, `/admin/` or `/static/` it passes the request to
  Django. If it starts with `/media/` it sends the uploaded file straight from the disk. Everything else goes to
  the Next.js website.
- Django and Next.js listen only on `127.0.0.1` (the server itself), so nobody on the internet can reach them
  directly — only through Nginx.
- The database also listens only on the server itself.

Because the frontend and the API share **one domain**, the browser never needs CORS, and you need only **one**
DNS record and **one** certificate.

### 0.2 What you need

| Thing | Notes |
|---|---|
| A VPS | Ubuntu 24.04 or newer. 4 GB RAM is enough. |
| A Mac/PC with a terminal | All `ssh` commands start here. |
| Access to the egoola-ecom GitHub organization | To add deploy keys to both repos. |
| Access to the Cloudflare account that hosts egoola.com's DNS | The domain was **bought at Namecheap**, but its DNS is **managed in Cloudflare**. See [15](#15-point-the-domain-to-the-server-cloudflare-dns). |

### 0.3 Values used in this guide

Write your own values down before you begin. Every time you see one of the names on the left, type your value.

| Name in this guide | Value we used for dev | What it is |
|---|---|---|
| `VPS_IP` | `201.18.207.36` | The server's public IP (from the Hostinger panel) |
| `DOMAIN` | `dev.egoola.com` | The address people will open |
| Linux user | `egoola` | Your everyday user on the server |
| `APP_DIR` | `/home/egoola/var/www` | Parent folder for all the code |
| `BACKEND_DIR` | `/home/egoola/var/www/backend/egoola-server` | The Django project (where `manage.py` is) |
| `MEDIA_DIR` | `/home/egoola/var/www/backend/media` | Uploaded files (kept **outside** the git folder) |
| `FRONTEND_DIR` | `/home/egoola/var/www/frontend/egoola-web` | The Next.js project (where `package.json` is) |
| Database name / user | `egoola_dev` / `egoola_dev` | The Postgres database and its login |

> If you choose different paths, change them **everywhere**: the `.env`, the Gunicorn service file, and the Nginx
> config. A path that is right in one place and wrong in another is the most common cause of a broken setup.

### 0.4 The golden rule: where am I typing?

Some commands run on **your Mac**, most run **on the server**. Look at your terminal prompt before you press Enter:

| Prompt looks like | You are on |
|---|---|
| `emrulhasan@Emruls-MacBook-Pro ~ %` | Your Mac |
| `root@srv2117256:~#` | The server, as root |
| `egoola@srv2117256:~$` | The server, as the `egoola` user |

If a server command says `command not found` (for example `certbot`), you probably typed it on your Mac.

---

## 1. Create the VPS and add your SSH key

**What:** Install a clean Ubuntu on the VPS and give it your Mac's public SSH key.

**Why:** An SSH key is like a very long password stored in a file on your Mac. With it you can log in without
typing a password, and it is practically impossible to guess.

### 1.1 Choose the operating system

1. Hostinger hPanel → **VPS** → your server → **OS & Panel** → **Operating System**.
2. Choose plain **Ubuntu** (24.04 or newer — we used 26.04). Do **not** choose a version "with control panel".
3. Note the server's **IP address** (this is `VPS_IP`).

### 1.2 Find or create your SSH key (on your Mac)

```bash
ls ~/.ssh/*.pub
```

- If you see a file like `id_ed25519.pub`, you already have a key. Skip to 1.3.
- If you see "no matches found", create one (press Enter at every question):

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

The key has two parts:

| File | What it is | Share it? |
|---|---|---|
| `~/.ssh/id_ed25519.pub` | **Public** key — the "lock" | Yes, safe to paste anywhere |
| `~/.ssh/id_ed25519` | **Private** key — the "key" | **Never.** Never paste, upload or send it |

### 1.3 Add the public key to the VPS

Copy the public key to the clipboard (on your Mac):

```bash
pbcopy < ~/.ssh/id_ed25519.pub
```

`pbcopy` prints nothing when it works — that is normal.

Then in hPanel → **VPS** → **Settings** → **SSH keys** → **Add SSH key**, give it a name (e.g. `emrul-mac`),
paste, save.

### ✅ Check

```bash
ssh root@VPS_IP
```

The first time it asks "Are you sure you want to continue connecting?" — type `yes`. You should get a
`root@...:~#` prompt **without** being asked for a password.

---

## 2. First login and system update

**What:** Update every installed program and set the clock to your timezone.

**Why:** A fresh image is often weeks old. Updating gets the latest security fixes before the server is exposed
to the internet for long.

Run as root on the server:

```bash
apt update && apt upgrade -y
timedatectl set-timezone Asia/Dhaka
```

- `apt update` downloads the list of the newest versions.
- `apt upgrade -y` installs them (`-y` answers "yes" for you).
- If a pink/purple screen asks about a config file, press **Enter** to keep the default.

> **"Waiting for lock" / "Could not get lock"?** A brand-new VPS runs an automatic update in the background for
> the first few minutes. Wait 2–5 minutes and try again. Do **not** kill `apt`, `dpkg` or `unattended-upgrade` —
> stopping them halfway can break packages.

### ✅ Check

```bash
timedatectl
```

`Time zone:` should show `Asia/Dhaka`.

---

## 3. Create your own user (stop using root)

**What:** Create a normal user called `egoola` that can become admin with `sudo`.

**Why:** `root` can do anything with no questions asked — one typo can destroy the server. Working as a normal
user and typing `sudo` only when needed is safer, and it leaves a record of who ran what.

Run as root:

```bash
adduser egoola
```

- Choose a password and **save it in your password manager**. You will need it every time you use `sudo`, and
  for the emergency console in hPanel.
- Name, room number, phone, etc.: just press Enter.

Give the user admin rights:

```bash
usermod -aG sudo egoola
```

Copy your SSH key to the new user, so you can log in as `egoola` with the same key:

```bash
rsync -a --chown=egoola:egoola ~/.ssh /home/egoola/
```

> **`adduser` keeps printing "Waiting for lock to become available..."?** Another `adduser`/`passwd` is still
> open somewhere (maybe in another terminal tab, waiting for a password), or the first-boot update is running.
> Press Ctrl+C, then look:
>
> ```bash
> ps aux | grep -E 'adduser|useradd|passwd|apt|dpkg|unattended' | grep -v grep
> ```
>
> Finish or close the other `adduser`. If it is `apt`/`dpkg`, just wait.

### ✅ Check (keep the root window open!)

Open a **new** terminal tab on your Mac:

```bash
ssh egoola@VPS_IP
sudo whoami
```

`sudo` asks for the `egoola` password, then prints `root`. Only continue when this works.

---

## 4. Turn on the firewall

**What:** Block every incoming connection except SSH (22), HTTP (80) and HTTPS (443).

**Why:** Many programs open network ports. The firewall makes sure only the three doors we actually use are open.
Postgres (5432), Gunicorn (8000) and Next.js (3000) stay closed to the internet.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Type `y` when asked.

> **Order matters.** Always run `ufw allow OpenSSH` **before** `ufw enable`, or you lock yourself out.

### ✅ Check

```bash
sudo ufw status
```

You should see `OpenSSH`, `80/tcp` and `443/tcp` as `ALLOW`, and `Status: active`.

---

## 5. Add swap memory

**What:** Create a 2 GB file on disk that Linux can use as extra memory when the real memory (RAM) is full.

**Why:** The server has 4 GB of RAM. Gunicorn + Next.js + Postgres + Nginx use about 1–1.5 GB. But
`npm run build` (building the Next.js site) can use another 1.5–3 GB for a few minutes. Without swap, Linux kills
a program when memory runs out — usually the build, or worse, your running site. With swap, the build just gets
a bit slower and finishes.

First check if swap already exists:

```bash
free -h
```

If the `Swap:` line shows `0B`, add it:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

| Command | What it does |
|---|---|
| `fallocate -l 2G /swapfile` | Creates an empty 2 GB file |
| `chmod 600` | Only root can read it (it can contain pieces of memory) |
| `mkswap` | Formats the file as swap |
| `swapon` | Starts using it now |
| `... >> /etc/fstab` | Starts using it again after every reboot |

Tell Linux to prefer real RAM and use swap only when RAM is almost full:

```bash
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf
sudo sysctl -p /etc/sysctl.d/99-swap.conf
```

### ✅ Check

```bash
free -h
```

The `Swap:` line now shows `2.0Gi` total.

> Swap is a safety net, not extra RAM. If you see swap **always** heavily used, the server needs more RAM.

---

## 6. Lock down SSH

**What:** Forbid logging in as `root`, and forbid logging in with a password (keys only).

**Why:**

- Robots on the internet try to log in as `root` on every server, all day long, because every Linux server has a
  `root` user. If root login is off, they also have to guess the user name.
- Passwords can be guessed. An SSH key cannot, in practice.

> **Do this only after the check in step 3 worked** (`ssh egoola@VPS_IP` + `sudo whoami`). Otherwise you can lock
> yourself out.

```bash
sudo tee /etc/ssh/sshd_config.d/00-hardening.conf > /dev/null <<'EOF'
PermitRootLogin no
PasswordAuthentication no
EOF
sudo sshd -t && sudo systemctl restart ssh
```

Why a separate file in `sshd_config.d/` instead of editing the main config? Hostinger's image ships its own small
config files in that folder. SSH uses the **first** value it reads, and files are read in name order, so our
`00-...` file wins over theirs.

`sshd -t` tests the config first; SSH only restarts if the test passes.

### ✅ Check (from your Mac, in a new tab)

```bash
ssh root@VPS_IP
```

→ must be **refused** (`Permission denied`).

```bash
ssh egoola@VPS_IP
```

→ must **work**.

**From now on, always log in as `egoola`.** Use `sudo` in front of commands that need admin rights, or
`sudo -i` for a root shell.

### If you ever lock yourself out

hPanel → VPS → **Browser terminal** (or VNC console). That console does not use SSH, so the rules above do not
apply. Log in as `egoola` with its password and fix the file.

### Giving a teammate access

They cannot use a password (password login is off). Ask for their **public** key and add it:

```bash
echo 'ssh-ed25519 AAAA...their-key... their-name' >> /home/egoola/.ssh/authorized_keys
```

---

## 7. Install the software

**What:** Install Nginx, PostgreSQL, Git, Certbot, `uv` (Python) and Node.js + pm2.

You do **not** need to be in any particular folder for `apt` — it installs programs into system folders, wherever
you run it.

### 7.1 System packages

```bash
sudo apt update
sudo apt install -y nginx postgresql postgresql-contrib git certbot python3-certbot-nginx
```

| Package | Why we need it |
|---|---|
| `nginx` | The front door web server |
| `postgresql`, `postgresql-contrib` | The database (egoola-server needs version **16 or newer**) |
| `git` | To download (clone) and update (pull) the code |
| `certbot`, `python3-certbot-nginx` | Free HTTPS certificates that install themselves into Nginx |

We do **not** install `python3-venv`, `python3-dev`, `libpq-dev` or `build-essential`: `uv` brings its own Python,
and the project's packages (`psycopg2-binary`, `pillow`, `bcrypt`) come as ready-made binaries.

### 7.2 uv (Python and Python packages)

**Why uv and not pip?** egoola-server is managed with [uv](https://docs.astral.sh/uv/):

- `.python-version` says the project uses **Python 3.12**.
- `uv.lock` lists the **exact** version of every package that was tested.

The Ubuntu Python may be a different version (Ubuntu 26.04 ships 3.14). `uv` ignores it: it downloads Python 3.12
by itself and installs exactly the locked packages. With plain `pip` you would get untested versions.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

### 7.3 Node.js and pm2

egoola-web uses Next.js 16, which needs Node.js 20.9 or newer. We use Node 22 (LTS).

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm i -g pm2
```

If the NodeSource script says your Ubuntu version is not supported, use `nvm` instead:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install 22
npm i -g pm2
```

`pm2` is a "process manager" for Node: it keeps the Next.js site running, restarts it if it crashes, and starts it
again after a reboot.

### ✅ Check

```bash
uv --version
node -v
npm -v
pm2 -v
psql --version
nginx -v
certbot --version
```

Every command prints a version number. `node -v` shows `v22.x`, `psql` shows 16 or higher.

---

## 8. Create the PostgreSQL database

**What:** Create a database called `egoola_dev` and a login (role) called `egoola_dev` that owns it.

**Why:** Django needs an empty database it is allowed to create tables in. Each environment (dev, staging,
production) gets its **own** database and its **own** password. Never point dev at the production database.

### 8.1 Make a strong password

```bash
openssl rand -base64 24 | tr -d '/+='
```

This prints a random password. `tr -d '/+='` removes characters that can cause trouble in `.env` files. Save it
in your password manager — you will put it in the backend `.env` in step 11.

> Never paste a real password into a chat, a ticket or a git commit. If you do by mistake, change it.

### 8.2 Create the role and the database

Open the Postgres console as the `postgres` admin:

```bash
sudo -u postgres psql
```

The prompt changes to `postgres=#`. Type (replace the password):

```sql
CREATE USER egoola_dev WITH PASSWORD 'PASTE_PASSWORD_HERE';
CREATE DATABASE egoola_dev OWNER egoola_dev ENCODING 'UTF8';
\du
\q
```

- Each SQL line **must end with `;`**. You should see `CREATE ROLE` and then `CREATE DATABASE`.
- Keep the single quotes `'...'` around the password.
- `\du` lists users — `egoola_dev` must be there.
- `\q` quits.

> **Prompt changed to `postgres-#` (with a dash)?** That means Postgres is still waiting for the end of your
> command — you forgot the `;`. Press **Ctrl+C** to throw away the half-typed command, then type it again with
> `;`. If you just type the command again without Ctrl+C, the two lines join together and you get
> `syntax error at or near "CREATE"` — and **nothing** is created.

The project does not need any Postgres extensions (its GIN indexes on JSON/array fields are built in).

### 8.3 Fixing a wrong password later

```bash
sudo -u postgres psql
```

```sql
\password egoola_dev
\q
```

It asks for the new password twice (nothing shows while you type). If it says
`role "egoola_dev" does not exist`, the `CREATE USER` never ran — go back to 8.2.

### ✅ Check

```bash
psql -h localhost -U egoola_dev -d egoola_dev -c "select current_user, version();"
```

Type the password. You should see `egoola_dev` and `PostgreSQL 18.x ...`.

If the screen fills with `~` lines, that is just the page viewer — press **q** to get your prompt back.

`password authentication failed for user "egoola_dev"` means the password you typed is not the one Postgres has.
Use 8.3.

> Postgres only accepts connections from the server itself. Keep it that way: do **not** open port 5432 in the
> firewall and do **not** change `listen_addresses`. To look at the database from your Mac, use an SSH tunnel:
> `ssh -L 5432:localhost:5432 egoola@VPS_IP`, then connect your database tool to `localhost:5432`.

---

## 9. Give the server access to GitHub (deploy keys)

**What:** Create two SSH keys **on the server**, one for each private repo, and register each key in its repo on
GitHub as a read-only **deploy key**.

**Why:**

- The repos are private, so the server must prove it is allowed to read them.
- A deploy key gives access to **one repo only**. If the server is ever hacked, the attacker gets read access to
  those two repos and nothing else — not your whole GitHub account.
- GitHub refuses to use the same deploy key on two repos (`Key is already in use`), so we need **two** keys, and a
  small SSH config that tells Git which key belongs to which repo.

> Deploy keys must be **allowed by the egoola-ecom organization**. If the repo's **Settings → Deploy keys** page
> says "Disabled by egoola-ecom", an organization owner must turn it on (organization **Settings → Member
> privileges → Deploy keys**). The alternative is a fine-grained personal access token — see 9.6.

### 9.1 Create the two keys (on the server, as `egoola`)

```bash
ssh-keygen -t ed25519 -C "egoola-dev-server" -f ~/.ssh/egoola_server -N ""
ssh-keygen -t ed25519 -C "egoola-dev-web" -f ~/.ssh/egoola_web -N ""
```

- `-f` sets the file name; `-N ""` means no passphrase (the server must be able to use it unattended).
- This creates `~/.ssh/egoola_server` + `egoola_server.pub` and `~/.ssh/egoola_web` + `egoola_web.pub`.

> These files must be created **on the server**. If `cat ~/.ssh/egoola_web.pub` says "No such file" and the path
> starts with `/Users/...`, you ran it on your Mac.

### 9.2 Tell SSH which key to use for which repo

```bash
cat >> ~/.ssh/config <<'EOF'
Host github-server
    HostName github.com
    User git
    IdentityFile ~/.ssh/egoola_server
    IdentitiesOnly yes

Host github-web
    HostName github.com
    User git
    IdentityFile ~/.ssh/egoola_web
    IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

This creates two nicknames: `github-server` and `github-web`. Both really go to `github.com`, but each one uses its
own key. `IdentitiesOnly yes` stops SSH from trying other keys first.

### 9.3 Add each public key to its repo on GitHub

Print the first key and copy it:

```bash
cat ~/.ssh/egoola_server.pub
```

GitHub → **egoola-ecom/egoola-server** → **Settings** → **Deploy keys** → **Add deploy key**:

- Title: `egoola-dev-vps`
- Key: paste
- **Allow write access: leave it OFF.** The server only needs to download code (`clone`, `pull`). If the server
  were hacked, a write key would let the attacker push code into your repo.

Then the second key:

```bash
cat ~/.ssh/egoola_web.pub
```

→ add it the same way to **egoola-ecom/egoola-web**.

### 9.4 ✅ Check

```bash
ssh -T github-server
ssh -T github-web
```

The first time, type `yes` to trust GitHub. Each should answer:
`Hi egoola-ecom/egoola-server! You've successfully authenticated...` (or `egoola-web`).

### 9.5 Remember the clone address

Because of the nicknames, clone with `github-server:` / `github-web:` instead of `github.com:`:

| Repo | Clone address |
|---|---|
| egoola-server | `git@github-server:egoola-ecom/egoola-server.git` |
| egoola-web | `git@github-web:egoola-ecom/egoola-web.git` |

If you clone with `github.com` instead, SSH offers the wrong key and you get `Repository not found`.

### 9.6 Alternative when deploy keys are not allowed: fine-grained token

1. GitHub → your avatar → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained
   tokens** → **Generate new token**.
2. Resource owner: `egoola-ecom`. Repository access: only `egoola-server` and `egoola-web`.
   Permissions → Repository → **Contents: Read-only**. Pick an expiry (e.g. 90 days).
3. If the organization requires approval, an owner approves it under organization **Settings → Personal access
   tokens → Pending requests**.
4. On the server:

```bash
git config --global credential.helper store
git clone https://github.com/egoola-ecom/egoola-server.git
chmod 600 ~/.git-credentials
```

Username = your GitHub user name, password = the token. It is saved in `~/.git-credentials` (as plain text — that
is why `chmod 600`). Never put the token inside the clone URL; it would stay in `.git/config` and your shell
history.

---

## 10. Download the code

**What:** Create the folders and clone both repos into them.

**Why this layout:** The uploaded files folder (`media`) lives **next to** the backend git folder, not inside it.
That way `git` never touches uploaded files, and you can delete and re-clone the code without losing uploads.

```
/home/egoola/var/www/
├── backend/
│   ├── egoola-server/     <- git repo (BACKEND_DIR)
│   └── media/             <- uploaded files (MEDIA_DIR)
└── frontend/
    └── egoola-web/        <- git repo (FRONTEND_DIR)
```

> `~/var/www` means `/home/egoola/var/www` — a folder inside your home, **not** the system `/var/www`. Either
> works; just use the same full path everywhere. The home folder is simpler because `egoola` already owns it.

```bash
mkdir -p ~/var/www/backend/media ~/var/www/frontend

cd ~/var/www/backend
git clone git@github-server:egoola-ecom/egoola-server.git

cd ~/var/www/frontend
git clone git@github-web:egoola-ecom/egoola-web.git
```

If you deploy a branch other than `main`:

```bash
cd ~/var/www/backend/egoola-server && git checkout <branch>
cd ~/var/www/frontend/egoola-web && git checkout <branch>
```

### ✅ Check

```bash
ls ~/var/www/backend/egoola-server/manage.py
ls ~/var/www/frontend/egoola-web/package.json
```

Both files exist.

---

## 11. Set up the backend (egoola-server)

All commands in this section run inside `BACKEND_DIR`:

```bash
cd ~/var/www/backend/egoola-server
```

### 11.1 Install Python and the packages

```bash
uv sync --locked --no-dev
```

- Reads `.python-version` (3.12) and downloads that Python if needed.
- Creates a private environment in `.venv/` and installs **exactly** what `uv.lock` lists.
- `--locked` refuses to run if `uv.lock` and `pyproject.toml` disagree, instead of quietly changing versions.
- `--no-dev` skips developer-only tools.

Every Django command is then run as `uv run python manage.py ...` so it always uses that environment.

### 11.2 Create the `.env` file

`config/settings.py` reads all its settings from a file called `.env` next to `manage.py` (it uses
`python-dotenv`). `.env` is in `.gitignore` — it holds secrets and must never be committed.

```bash
cp .env.example .env
chmod 600 .env
```

`chmod 600` means only the `egoola` user can read it.

Make a secret key for this server:

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Open the file:

```bash
nano .env
```

Set these values (keep the comments from `.env.example` if you like):

```env
DJANGO_SECRET_KEY=<the key you just generated>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=dev.egoola.com
CSRF_TRUSTED_ORIGINS=https://dev.egoola.com
CORS_ALLOWED_ORIGINS=https://dev.egoola.com,http://localhost:3000,http://127.0.0.1:3000
DJANGO_TIME_ZONE=Asia/Dhaka

DJANGO_ENV=local

DB_NAME=egoola_dev
DB_USER=egoola_dev
DB_PASSWORD=<the Postgres password from step 8>
DB_HOST=localhost
DB_PORT=5432

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=

MEDIA_ROOT=/home/egoola/var/www/backend/media
```

Save in nano: **Ctrl+O**, **Enter**, then exit: **Ctrl+X**.

What each value means:

| Key | Value | Why |
|---|---|---|
| `DJANGO_SECRET_KEY` | random | Signs logins, sessions and every JWT token. Unique per server, never shared, never the placeholder. Changing it logs everybody out. |
| `DJANGO_DEBUG` | `false` | **Must** be set — the code's default is `true`. Debug mode shows secret details to anyone when an error happens. |
| `DJANGO_ALLOWED_HOSTS` | `dev.egoola.com` | Django only answers requests for this name. Anything else gets `400 Bad Request`. |
| `CSRF_TRUSTED_ORIGINS` | `https://dev.egoola.com` | Needed so the `/admin/` login form works over HTTPS. Include `https://`. |
| `CORS_ALLOWED_ORIGINS` | dev site + localhost | The site itself does not need CORS (same domain). The `localhost` entries let developers run the frontend on their laptop against the dev API. Comma-separated, no spaces, no trailing `/`. **Write this key only once** — if it appears twice, the last line silently wins. |
| `DJANGO_ENV` | `local` | Tells `config/storage.py` to save uploads to a folder on this server instead of Amazon S3. Any other value means S3 and needs the `AWS_*` keys. |
| `DB_*` | from step 8 | How Django logs into Postgres. |
| `AWS_*` | empty | Ignored while `DJANGO_ENV=local`. |
| `MEDIA_ROOT` | **full** path | Where uploads are saved. Always use a full path starting with `/home/...`. A relative path like `../media` depends on which folder a command happens to run from, so files could end up in different places. Do **not** write `/backend/media` — a path starting with `/` means the top of the disk. |

Find the exact full path for `MEDIA_ROOT` with:

```bash
cd ~/var/www/backend/media && pwd && cd -
```

Leave `CORS_ALLOW_ALL_ORIGINS` out of the file (it is an emergency switch that accepts any website).

### 11.3 Run Django's setup commands

```bash
uv run python manage.py check --deploy
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
uv run python manage.py createsuperuser
```

| Command | What it does |
|---|---|
| `check --deploy` | Looks for mistakes in the settings. **Warnings** (W) about `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, etc. are fine for dev. Only an **error** that stops the command matters. |
| `migrate` | Creates every table in the empty database, from the project's migration files. |
| `collectstatic` | Copies the CSS/JS for the admin site and the API docs into `staticfiles/`. WhiteNoise (already in the project) serves them from there. |
| `createsuperuser` | Creates your first login for `/admin/`. |

> If `migrate` fails with `password authentication failed`, the `DB_PASSWORD` in `.env` and the password in
> Postgres are different. Fix it with step 8.3 so Postgres uses exactly the value in `.env`. Watch out for
> spaces or quotes around the value in `.env`.

### ✅ Check

`migrate` ends with a list of `Applying ... OK` lines and no red error.

---

## 12. Run the backend forever with Gunicorn + systemd

**What:** Create a "service" so the backend starts at boot and restarts by itself if it crashes.

**Why:**

- `manage.py runserver` is only for development — it is slow and not safe.
- **Gunicorn** is the real server for Django. It is already in the project's packages, so it is in `.venv/`.
- **systemd** is Linux's service manager. It starts Gunicorn at boot, restarts it on crash, and keeps its logs.

### 12.1 Create the service file

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Paste:

```ini
[Unit]
Description=Gunicorn for egoola-server (dev)
After=network.target postgresql.service

[Service]
User=egoola
WorkingDirectory=/home/egoola/var/www/backend/egoola-server
ExecStart=/home/egoola/var/www/backend/egoola-server/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

Save (Ctrl+O, Enter) and exit (Ctrl+X).

Line by line:

| Line | Meaning |
|---|---|
| `After=... postgresql.service` | Start after the network and the database are up |
| `User=egoola` | Run as `egoola`, not root. It can then write uploads into `MEDIA_ROOT`. |
| `WorkingDirectory=` | The folder with `manage.py`. Settings find `.env` from here. |
| `ExecStart=` | The command to run: Gunicorn from the project's `.venv`. |
| `config.wsgi:application` | The Django entry point (`config/wsgi.py`). |
| `--bind 127.0.0.1:8000` | Listen only inside the server. Nginx forwards to it. |
| `--workers 3` | 3 copies to handle requests in parallel (rule of thumb: 2 × CPU cores + 1). |
| `--timeout 60` | Kill a request that takes longer than 60 seconds. |
| `Restart=always` | Start again if it ever stops. |
| `WantedBy=multi-user.target` | Start at boot. |

There is no `EnvironmentFile=` line: the project loads `.env` by itself.

### 12.2 Start it

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn
sudo systemctl status gunicorn --no-pager
```

- `daemon-reload` makes systemd read the new file.
- `enable --now` = start now **and** at every boot.

### ✅ Check

`status` shows `active (running)`. Then:

```bash
curl -I -H "Host: dev.egoola.com" http://127.0.0.1:8000/api/docs/
```

You should see `HTTP/1.1 200 OK` and `Server: gunicorn`.

Why `-H "Host: dev.egoola.com"`? `ALLOWED_HOSTS` only accepts `dev.egoola.com`. Without the header, curl asks for
`127.0.0.1` and Django answers `400 Bad Request` — that is Django protecting itself, not a bug.

If it fails:

```bash
journalctl -u gunicorn -n 50 --no-pager
```

---

## 13. Set up the frontend (egoola-web)

```bash
cd ~/var/www/frontend/egoola-web
```

### 13.1 Tell the frontend where the API is

egoola-web reads one setting, `NEXT_PUBLIC_API_URL` (see `src/lib/env.ts`). Its default is
`http://localhost:8000/api/v1`, so on the server it **must** be set:

```bash
echo 'NEXT_PUBLIC_API_URL=https://dev.egoola.com/api/v1' > .env.production
```

- It ends in `/api/v1` — the frontend adds the rest of each path itself.
- `NEXT_PUBLIC_...` values are **baked into the site at build time**. If you change this value later, you must
  run `npm run build` again — restarting is not enough.

### 13.2 Install and build

```bash
npm ci
npm run build
```

- `npm ci` installs exactly what `package-lock.json` lists (a clean, repeatable install).
- `npm run build` creates the optimized production site in `.next/`. This is the memory-hungry part (that is why
  we added swap). It can take a few minutes.

### 13.3 Start it with pm2

```bash
pm2 start npm --name frontend -- start -- -p 3000
pm2 save
pm2 startup systemd -u egoola --hp /home/egoola
```

- `pm2 start npm --name frontend -- start -- -p 3000` runs `npm start -p 3000` under pm2, with the name
  `frontend`.
- `pm2 save` remembers the list of running apps.
- `pm2 startup ...` **prints a command starting with `sudo`**. Copy that printed line and run it. This makes pm2
  (and so the frontend) start at boot.

### ✅ Check

```bash
pm2 status
curl -I http://127.0.0.1:3000
```

`pm2 status` shows `frontend` as `online`, and curl shows `200 OK`.

If not: `pm2 logs frontend`.

---

## 14. Configure Nginx

**What:** Tell Nginx which requests go to Django, which go to Next.js, and where the uploaded files are.

### 14.1 Create the site config

```bash
sudo nano /etc/nginx/sites-available/egoola-dev
```

Paste:

```nginx
server {
    listen 80;
    server_name dev.egoola.com;

    # Biggest upload the project allows is 30 MB (documents) - see config/storage.py
    client_max_body_size 30M;

    # Ask search engines not to index the dev site
    add_header X-Robots-Tag "noindex, nofollow" always;

    # Uploaded files: served straight from disk
    location /media/ {
        alias /home/egoola/var/www/backend/media/;
    }

    # Django: API, admin site, API docs, and Django's static files
    location ~ ^/(api|admin|static)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Everything else: the Next.js website
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

What each part does:

| Part | Meaning |
|---|---|
| `server_name dev.egoola.com` | This block is for this domain only |
| `client_max_body_size 30M` | Allow uploads up to 30 MB (Nginx's default is only 1 MB) |
| `location /media/` + `alias` | For `/media/...` addresses, send the file from `MEDIA_DIR`. Both paths end with `/`. Must match `MEDIA_ROOT` in `.env`. Django does not serve these files itself when `DEBUG` is off. |
| `location ~ ^/(api\|admin\|static)/` | Addresses starting with `/api/`, `/admin/` or `/static/` go to Gunicorn. This covers `/api/v1/...`, `/api/docs/`, `/api/schema/`, the admin site and its CSS. |
| `proxy_set_header Host $host` | Pass the real domain name to Django, so `ALLOWED_HOSTS` matches |
| `X-Forwarded-Proto $scheme` | Tells Django whether the visitor used HTTPS. `settings.py` trusts this header (`SECURE_PROXY_SSL_HEADER`), so **keep this line exactly** — it makes CSRF and secure cookies work. |
| `location /` | Everything else goes to Next.js |
| `Upgrade` / `Connection "upgrade"` | Lets Next.js use WebSockets |

Why `/static/` goes to Django and not straight to disk: the project uses WhiteNoise, which already serves Django's
static files efficiently. egoola-web has no `public/static/` folder, so there is no clash with the frontend. Next.js
serves its own files from `/_next/...`, which falls into `location /`.

### 14.2 Turn the site on

```bash
sudo ln -s /etc/nginx/sites-available/egoola-dev /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

- Nginx reads configs from `sites-enabled/`. The `ln -s` makes a shortcut there to our file.
- Removing `default` stops Nginx's "Welcome to nginx" page from answering instead of our site.

### 14.3 Let Nginx reach the media folder

Nginx runs as the user `www-data`. Ubuntu home folders are private, so `www-data` cannot walk into
`/home/egoola/...` and media files would return `403 Forbidden`. Give "pass through" (`x`) permission on each
folder along the path:

```bash
chmod o+x /home/egoola /home/egoola/var /home/egoola/var/www /home/egoola/var/www/backend
namei -l /home/egoola/var/www/backend/media
```

`namei -l` shows every folder on the path. The last group of letters for each folder must contain `x`
(e.g. `drwxr-x--x`). `o+x` lets others pass through a folder, but **not** list or read it.

### 14.4 Test and reload

```bash
sudo nginx -t
sudo systemctl reload nginx
```

`nginx -t` checks the config for mistakes **before** applying it. Never skip it — a broken config can take the
site down on reload.

### ✅ Check

`nginx -t` says `syntax is ok` and `test is successful`. Then, still on the server:

```bash
curl -I -H "Host: dev.egoola.com" http://127.0.0.1/
curl -I -H "Host: dev.egoola.com" http://127.0.0.1/api/docs/
```

Both show `200 OK`.

---

## 15. Point the domain to the server (Cloudflare DNS)

**What:** Add a DNS record so `dev.egoola.com` leads to `VPS_IP`.

### 15.1 Where is the DNS? (important)

egoola.com was **bought at Namecheap**, but its **nameservers are Cloudflare's** (`joel.ns.cloudflare.com`,
`paige.ns.cloudflare.com`). The nameservers decide where DNS records are read from. So:

- Records added in Namecheap's "Advanced DNS" tab are **ignored** by the whole internet.
- Records must be added in **Cloudflare**.

Check it yourself any time (on your Mac):

```bash
dig egoola.com NS +short
```

If it shows `...ns.cloudflare.com`, use Cloudflare. If it shows `...registrar-servers.com`, use Namecheap.

> Do **not** switch the nameservers back to Namecheap "just to add one record". Production's records live in
> Cloudflare; switching would take egoola.com offline.

### 15.2 Add the record

`dev.egoola.com` is a **subdomain** — it is free, you do not buy anything. It is just one more line in the existing
DNS zone.

Cloudflare → **egoola.com** → **DNS** → **Records** → **Add record**:

| Field | Value |
|---|---|
| Type | `A` |
| Name | `dev` |
| IPv4 address | `VPS_IP` |
| Proxy status | **DNS only** (grey cloud) — for now |
| TTL | Auto |

Save. **Do not touch** any other record (`@`, `www`, etc.) — production uses them.

Why grey cloud for now: Certbot (next step) must reach your server directly to prove you own the domain.

### ✅ Check (on your Mac)

```bash
dig dev.egoola.com +short
```

It prints `VPS_IP`. It can take a few minutes. If it prints a Cloudflare IP (`104.x`, `172.67.x`), the record is
still proxied (orange) — switch it to grey.

To confirm the IP really is your server, run on the server:

```bash
curl -4 ifconfig.me
```

The two IPs must be the same.

---

## 16. Get the HTTPS certificate (Certbot)

**What:** Get a free certificate from Let's Encrypt and switch the site to HTTPS.

**Why:** Without HTTPS, passwords and tokens travel as plain text, browsers show "Not secure", and the Django admin
login refuses to work (CSRF needs `https://`).

**Run on the server** (the prompt must say `egoola@srv...`):

```bash
sudo certbot --nginx -d dev.egoola.com
```

- Enter your email (for expiry warnings) and agree to the terms.
- If asked, choose to **redirect** HTTP to HTTPS.

Certbot proves you own the domain, gets the certificate, and **edits the Nginx config by itself** (adds
`listen 443 ssl` and the certificate paths, plus an HTTP→HTTPS redirect).

The certificate lasts 90 days, and Certbot renews it automatically. Test that renewal will work:

```bash
sudo certbot renew --dry-run
```

It ends with `Congratulations, all simulated renewals succeeded`.

### 16.1 Optional: turn the Cloudflare proxy on

After HTTPS works you may switch the `dev` record to **Proxied** (orange cloud) for Cloudflare's protection.
Before you do, look at Cloudflare → **SSL/TLS** → **Overview**:

- **Full (strict)** or **Full** → safe to proxy.
- **Flexible** → leave `dev` on grey. This setting is shared by the **whole** egoola.com zone, including
  production, so do not change it just for dev.

---

## 17. Final checks

Open in your browser:

| Address | Expected |
|---|---|
| `https://dev.egoola.com` | The Egoola website, with a padlock |
| `https://dev.egoola.com/api/docs/` | Swagger API documentation |
| `https://dev.egoola.com/admin/` | Django admin login (log in with the superuser from 11.3) |
| `http://dev.egoola.com` | Redirects to `https://` |

Upload an image somewhere in the app, then:

```bash
ls ~/var/www/backend/media
```

The file is there, and its `https://dev.egoola.com/media/...` link opens in the browser.

Reboot test (proves everything starts by itself):

```bash
sudo reboot
```

Wait one minute, log in again, and open the site. Then:

```bash
sudo systemctl status gunicorn nginx postgresql --no-pager
pm2 status
```

Everything is `active (running)` / `online`.

🎉 The server is ready.

---

## 18. Optional extras

### 18.1 Password-protect the dev website

Keeps strangers and search engines out of the dev site.

```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd egoola
```

Then in `/etc/nginx/sites-available/egoola-dev`, add two lines inside `location / { ... }` **only**:

```nginx
        auth_basic "Dev";
        auth_basic_user_file /etc/nginx/.htpasswd;
```

Do **not** add them to the `/api/` block — the frontend's API calls would fail. Then
`sudo nginx -t && sudo systemctl reload nginx`.

### 18.2 Daily database backup

```bash
mkdir -p ~/backups
echo "localhost:5432:egoola_dev:egoola_dev:PASTE_DB_PASSWORD" > ~/.pgpass && chmod 600 ~/.pgpass
(crontab -l 2>/dev/null; echo '0 3 * * * pg_dump -U egoola_dev -h localhost egoola_dev | gzip > ~/backups/egoola_dev_$(date +\%F).sql.gz') | crontab -
(crontab -l 2>/dev/null; echo '30 3 * * * find ~/backups -name "*.gz" -mtime +14 -delete') | crontab -
```

- `~/.pgpass` lets `pg_dump` log in without asking for the password.
- The first cron line saves a compressed backup every day at 03:00.
- The second deletes backups older than 14 days, so the disk does not fill up.

### 18.3 Media backup

The `media` folder is not in git. Back it up too:

```bash
tar czf ~/backups/media_$(date +%F).tar.gz -C ~/var/www/backend media
```

---

## 19. Troubleshooting

### Where to look

| What | Command |
|---|---|
| Backend (Django/Gunicorn) | `journalctl -u gunicorn -n 100 --no-pager` (live: `journalctl -u gunicorn -f`) |
| Frontend (Next.js) | `pm2 logs frontend` |
| Nginx errors | `sudo tail -n 50 /var/log/nginx/error.log` |
| Status of everything | `sudo systemctl status gunicorn nginx postgresql --no-pager` and `pm2 status` |

### Common errors

| You see | Most likely cause | Fix |
|---|---|---|
| `502 Bad Gateway` | Gunicorn or Next.js is not running | Check the logs above; `sudo systemctl restart gunicorn` / `pm2 restart frontend` |
| `400 Bad Request` from Django | Domain not in `DJANGO_ALLOWED_HOSTS` | Fix `.env`, `sudo systemctl restart gunicorn` |
| `403 CSRF verification failed` on `/admin/` login | `CSRF_TRUSTED_ORIGINS` wrong, or `X-Forwarded-Proto` missing in Nginx | Fix `.env` / Nginx, restart |
| `403 Forbidden` on `/media/...` | Nginx cannot enter the home folders | Step 14.3 (`chmod o+x ...`) |
| `404` on `/media/...` | `alias` path ≠ `MEDIA_ROOT` | Make both the same full path |
| `413 Request Entity Too Large` | Upload bigger than `client_max_body_size` | Raise it in Nginx |
| Browser CORS error | Frontend origin not in `CORS_ALLOWED_ORIGINS` | Add it, restart Gunicorn |
| Frontend calls `localhost:8000` | `.env.production` missing or not rebuilt | Step 13.1, then `npm run build` and `pm2 restart frontend` |
| `password authentication failed for user "egoola_dev"` | `.env` password ≠ Postgres password | Step 8.3 |
| `DNS_PROBE_FINISHED_NXDOMAIN` in the browser | Record missing, or your computer cached an old "not found" answer | `dig` from 15.2; on a Mac flush the cache: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`, and in Chrome `chrome://net-internals/#dns` → Clear host cache |
| `npm run build` killed / "JavaScript heap out of memory" | Not enough memory | Check swap (step 5) |
| `certbot: command not found` | You ran it on your Mac | Run it on the server |

---

## 20. Mistakes we actually made (learn from them)

1. **Ran server commands on the Mac.** `certbot` and `cat ~/.ssh/egoola_web.pub` failed because they were typed in
   a Mac terminal. Always check the prompt (section 0.4).
2. **Added the DNS record in the wrong place.** The domain is registered at Namecheap but the DNS is in Cloudflare.
   Check with `dig egoola.com NS +short` first.
3. **Forgot `;` in `psql`.** The prompt became `postgres-#`, the next line joined it, and the result was a syntax
   error with nothing created. Press Ctrl+C and retype.
4. **`.env` password ≠ Postgres password.** Reset the Postgres password to exactly what `.env` has.
5. **`adduser` "Waiting for lock".** Another `adduser` was still open. Close it, or wait for the first-boot update.
6. **Relative `MEDIA_ROOT` (`../media`).** Works by luck depending on the current folder. Use the full path.
7. **`CORS_ALLOWED_ORIGINS` written twice in `.env`.** Only the last one counts. Keep one line.
8. **Deploy keys were disabled by the organization.** Either an org owner enables them, or use a fine-grained token.
9. **Pasted a real password in a chat.** Change any secret that was shared.

---

## 21. Quick reference

```bash
# Log in
ssh egoola@VPS_IP

# Restart things
sudo systemctl restart gunicorn
pm2 restart frontend
sudo nginx -t && sudo systemctl reload nginx

# Logs
journalctl -u gunicorn -f
pm2 logs frontend
sudo tail -f /var/log/nginx/error.log

# Django commands (in BACKEND_DIR)
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py shell

# Database console
psql -h localhost -U egoola_dev -d egoola_dev

# Disk and memory
df -h
free -h
```

| File | Purpose |
|---|---|
| `BACKEND_DIR/.env` | Backend settings and secrets |
| `FRONTEND_DIR/.env.production` | Frontend API address (needs a rebuild after changes) |
| `/etc/systemd/system/gunicorn.service` | How the backend is started |
| `/etc/nginx/sites-available/egoola-dev` | Domain → app routing, HTTPS (edited by Certbot) |
| `/etc/ssh/sshd_config.d/00-hardening.conf` | No root login, no password login |
| `~/.ssh/config` | Which GitHub key goes with which repo |

Next: to ship new code to this server, follow [`update-guide.md`](update-guide.md).
