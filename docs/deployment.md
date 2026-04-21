# Deployment — VPS (Production)

This document covers the one-time provisioning of the production VPS and
recurring operations (SSL renewal, backups, deploys).

## 🖥️ Target Environment

- **Host:** Hetzner CPX21 (or equivalent: 3 vCPU, 4 GB RAM, 80 GB NVMe)
- **OS:** Ubuntu 22.04 LTS
- **Domain:** `yuztanima.com` (example) with **wildcard DNS** on Cloudflare
  - `*.yuztanima.com`  → VPS IP
  - `admin.yuztanima.com` → VPS IP
  - `api.yuztanima.com`   → VPS IP

## 📦 Components

| Service | Purpose | Port |
|---|---|---|
| nginx | TLS termination + reverse proxy | 80/443 |
| gunicorn (server) | Flask + Socket.IO | 5000 (internal) |
| celery worker | Background jobs | — |
| celery beat | Scheduled jobs | — |
| PostgreSQL 16 | Primary DB | 5432 (internal) |
| Redis 7 | Cache / Celery broker / Socket.IO bus | 6379 (internal) |
| MinIO | Snapshot + face-image storage | 9000 (internal) |

---

## 🚀 Initial Setup

### 1. VPS hardening

```bash
# SSH key-only access
sudo passwd -l root
sudo nano /etc/ssh/sshd_config  # PasswordAuthentication no
sudo systemctl restart ssh

# Firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Unattended security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# fail2ban
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
```

### 2. Dependencies

```bash
sudo apt update && sudo apt install -y \
  python3.11 python3.11-venv python3.11-dev \
  build-essential cmake pkg-config \
  libpq-dev libjpeg-dev libopenblas-dev \
  nginx certbot python3-certbot-dns-cloudflare \
  postgresql-16 redis-server \
  git curl jq
```

### 3. PostgreSQL

```bash
sudo -u postgres psql <<'SQL'
CREATE USER yuztanima WITH PASSWORD 'CHANGE-ME';
CREATE DATABASE yuz_tanima_prod OWNER yuztanima;
GRANT ALL PRIVILEGES ON DATABASE yuz_tanima_prod TO yuztanima;
SQL
```

Edit [`pg_hba.conf`](/etc/postgresql/16/main/pg_hba.conf) to allow `yuztanima`
local connections via MD5/SCRAM.

### 4. Application user & directory

```bash
sudo useradd --system --create-home --shell /bin/bash --home /opt/yuztanima yuztanima
sudo -u yuztanima git clone https://github.com/ahmetmertkabak/yuz-tanima.git /opt/yuztanima/app
cd /opt/yuztanima/app/server
sudo -u yuztanima python3.11 -m venv .venv
sudo -u yuztanima .venv/bin/pip install -r requirements.txt
```

### 5. Environment file

```bash
sudo mkdir -p /etc/yuz-tanima
sudo cp /opt/yuztanima/app/server/.env.example /etc/yuz-tanima/server.env
sudo chmod 600 /etc/yuz-tanima/server.env
sudo chown yuztanima:yuztanima /etc/yuz-tanima/server.env
# Fill in real secrets. Generate SECRET_KEY and FACE_ENCRYPTION_KEY:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 6. systemd units

```ini
# /etc/systemd/system/yuztanima-web.service
[Unit]
Description=Yüz Tanıma web (gunicorn + eventlet)
After=network-online.target postgresql.service redis-server.service

[Service]
Type=simple
User=yuztanima
Group=yuztanima
WorkingDirectory=/opt/yuztanima/app/server
EnvironmentFile=/etc/yuz-tanima/server.env
ExecStart=/opt/yuztanima/app/server/.venv/bin/gunicorn \
  -k eventlet -w 1 -b 127.0.0.1:5000 "app:create_app()"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/yuztanima-worker.service
[Unit]
Description=Yüz Tanıma Celery worker
After=redis-server.service

[Service]
Type=simple
User=yuztanima
Group=yuztanima
WorkingDirectory=/opt/yuztanima/app/server
EnvironmentFile=/etc/yuz-tanima/server.env
ExecStart=/opt/yuztanima/app/server/.venv/bin/celery -A celery_app worker -l INFO
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/yuztanima-beat.service
[Unit]
Description=Yüz Tanıma Celery beat
After=redis-server.service

[Service]
Type=simple
User=yuztanima
Group=yuztanima
WorkingDirectory=/opt/yuztanima/app/server
EnvironmentFile=/etc/yuz-tanima/server.env
ExecStart=/opt/yuztanima/app/server/.venv/bin/celery -A celery_app beat -l INFO

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now yuztanima-web yuztanima-worker yuztanima-beat
```

### 7. nginx + wildcard SSL

```bash
# Cloudflare API token for DNS-01 challenge
sudo mkdir -p /etc/letsencrypt/credentials
cat | sudo tee /etc/letsencrypt/credentials/cloudflare.ini <<EOF
dns_cloudflare_api_token = YOUR_CLOUDFLARE_TOKEN
EOF
sudo chmod 600 /etc/letsencrypt/credentials/cloudflare.ini

# First-time cert
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/credentials/cloudflare.ini \
  -d yuztanima.com -d '*.yuztanima.com' \
  -m ops@yuztanima.com --agree-tos --non-interactive

# Auto-renewal is already in /etc/cron.d/certbot (tested by Certbot's systemd timer)
```

Create [`/etc/nginx/sites-available/yuztanima`](/etc/nginx/sites-available/yuztanima):

```nginx
server {
    listen 80;
    server_name yuztanima.com *.yuztanima.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yuztanima.com *.yuztanima.com;

    ssl_certificate     /etc/letsencrypt/live/yuztanima.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yuztanima.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 16m;

    # Socket.IO
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Static assets
    location /static/ {
        alias /opt/yuztanima/app/server/app/static/;
        expires 7d;
    }

    # Main
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "same-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/yuztanima /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 8. First-time DB migration + super-admin

```bash
cd /opt/yuztanima/app/server
sudo -u yuztanima .venv/bin/flask db upgrade
sudo -u yuztanima .venv/bin/flask create-super-admin
```

### 9. Verify

```bash
curl https://admin.yuztanima.com/health
# {"status":"ok","app":"Yüz Tanıma SaaS","version":"0.1.0"}

# Browser
open https://admin.yuztanima.com/auth/login
```

---

## 🔁 Deploying a new version

```bash
ssh yuztanima@yuztanima.com
cd /opt/yuztanima/app && git pull
cd server
./.venv/bin/pip install -r requirements.txt
./.venv/bin/flask db upgrade
exit

# Back on root
sudo systemctl restart yuztanima-web yuztanima-worker yuztanima-beat
```

Preferred: use a CI/CD pipeline (GitHub Actions) that SSHs into the VPS and
runs the above as a deploy step.

---

## 🗄️ Backups

### PostgreSQL (nightly)

```bash
# /etc/cron.daily/yuztanima-pgbackup
#!/usr/bin/env bash
set -euo pipefail
OUT=/var/backups/yuztanima/pg-$(date +%Y%m%d).sql.gz
mkdir -p "$(dirname "$OUT")"
sudo -u postgres pg_dump yuz_tanima_prod | gzip > "$OUT"
find /var/backups/yuztanima -name 'pg-*.sql.gz' -mtime +30 -delete
# Optionally: rsync to a remote S3-compatible bucket
```

### Application env + letsencrypt certs

Weekly `rsync` to an off-site location.

---

## 📊 Monitoring

- `systemctl status yuztanima-*` — service health
- `journalctl -u yuztanima-web -f` — live logs
- Sentry — exception tracking (DSN in `.env`)
- Uptime Kuma — external uptime monitoring of `/health` endpoint
- Prometheus node-exporter — CPU/RAM/disk metrics (optional)

---

## 🚨 Incident Runbook (Minimal)

| Symptom | Check | Remedy |
|---|---|---|
| Site down | `systemctl status yuztanima-web` | `systemctl restart yuztanima-web` |
| Login fails for everyone | PostgreSQL running? | `systemctl restart postgresql` |
| Socket.IO not updating | Redis running? | `systemctl restart redis-server` |
| Pi's not syncing | nginx / gunicorn healthy? | Check `/api/v1/ping` + firewall |
| Cert expired | `certbot certificates` | `certbot renew && systemctl reload nginx` |