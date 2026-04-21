# Server — Merkezi SaaS Backend

Multi-tenant yüz tanıma SaaS'in merkezi sunucu uygulaması.
Flask 3 + SQLAlchemy + PostgreSQL + Redis + Celery + Socket.IO.

## 🏗️ Mimari

```
server/
├── app/
│   ├── __init__.py        # Flask app factory
│   ├── config.py          # Ortam bazlı config
│   ├── extensions.py      # db, login_manager, socketio, ...
│   ├── models/            # SQLAlchemy modelleri (School, Person, ...)
│   ├── middleware/        # Tenant, auth, rate-limit
│   ├── routes/
│   │   ├── super_admin/   # admin.yuztanima.com
│   │   ├── school_admin/  # <okul>.yuztanima.com
│   │   └── api/v1/        # Cihaz REST API
│   ├── services/          # Business logic
│   ├── templates/
│   └── static/
├── migrations/            # Flask-Migrate (Alembic)
├── tests/
├── requirements.txt
└── run.py
```

## 🚀 Kurulum (Local Dev)

### 1. Python + bağımlılıklar
```bash
cd server
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Servisler (Docker)
PostgreSQL + Redis için proje kök dizinindeki [`docker-compose.yml`](../docker-compose.yml:1)'i kullan:
```bash
cd ..
docker compose up -d postgres redis
```

### 3. Environment
```bash
cp .env.example .env
# SECRET_KEY ve FACE_ENCRYPTION_KEY üret:
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Veritabanı
```bash
export FLASK_APP=app
flask db upgrade   # T1.8'den sonra aktif
```

### 5. Çalıştır
```bash
python run.py
# http://localhost:5000/health  →  {"status":"ok", ...}
```

## 🧪 Test

```bash
pytest                              # tüm testler
pytest -m unit                      # sadece unit testler
pytest --cov=app --cov-report=html  # coverage raporu
```

## 📘 Komutlar

```bash
flask routes-list             # tüm route'ları listele
flask create-super-admin      # platform yöneticisi oluştur (T2.1)
flask db migrate -m "msg"     # yeni migration
flask db upgrade              # migration'ları uygula
```

## 🔐 Güvenlik Notları

- `SECRET_KEY` ve `FACE_ENCRYPTION_KEY` **asla** repo'ya commit'lenmez
- Yüz encoding'leri DB'de Fernet ile şifrelenir
- Device API **HMAC-SHA256** imza ile korunur (CSRF muaf)
- SuperAdmin için 2FA zorunlu (T8.4)

## 📋 TODO

Devam eden görevler için [`../plan/10_TODO_YOL_HARITASI.md`](../plan/10_TODO_YOL_HARITASI.md:1).