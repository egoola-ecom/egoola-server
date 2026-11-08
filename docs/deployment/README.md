# Deployment

How to run egoola-server (Django) and egoola-web (Next.js) on a Linux VPS behind Nginx, with PostgreSQL and HTTPS.
Written from the `dev.egoola.com` setup on a Hostinger KVM 1 (Ubuntu 26.04).

| Document | Use it when |
|---|---|
| [`vps-setup-guide.md`](vps-setup-guide.md) | You have a **new, empty server** and want the whole stack running: user, firewall, swap, SSH, Postgres, GitHub deploy keys, uv, Gunicorn, pm2, Nginx, Cloudflare DNS, Certbot. |
| [`update-guide.md`](update-guide.md) | The server is **already running** and you want to ship new code, change settings, roll back, restore a backup, or do routine maintenance. |

The setup in one picture:

```
browser -> Cloudflare DNS -> Nginx (80/443, HTTPS)
                               |-- /api/ /admin/ /static/ -> Gunicorn :8000 -> Django -> PostgreSQL :5432
                               |-- /media/                -> files on disk (backend/media)
                               '-- everything else        -> Next.js :3000 (pm2)
```

No secrets belong in these documents. Passwords, keys and tokens live only in the server's `.env` files and in your
password manager.
