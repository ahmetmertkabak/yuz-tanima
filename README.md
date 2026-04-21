# 🎯 Yüz Tanıma — Okullar İçin Çok-Kiracılı SaaS

RFID yemekhane bakiye sisteminden evrimleşmiş, **okullar için yüz tanıma +
turnike kontrol** SaaS ürünü. MEB'in getirdiği yüz tanıma + turnike zorunluluğuna
uyumlu olarak geliştirilmektedir.

**Mimari:** Merkezi VPS (Flask + PostgreSQL + multi-tenant) + her okul için
Raspberry Pi (kamera + röle + turnike). Offline-first, KVKK-uyumlu.

---

## 📂 Proje Yapısı

```
yuz-tanima/
├── plan/                   📋 14 doküman — planlama / tasarım kararları
├── server/                 🌐 Merkezi VPS uygulaması (Flask 3)
├── edge/                   📸 Raspberry Pi yazılımı (kamera + yüz tanıma + GPIO)
├── docs/                   📘 Teknik dokümantasyon (deployment, API, troubleshoot)
├── docker-compose.yml      🐳 Lokal dev stack (Postgres + Redis + MinIO + server)
├── .gitignore
└── README.md
```

## 🚀 Hızlı Başlangıç (Local Dev)

### Sadece altyapı (Postgres + Redis + MinIO):
```bash
docker compose up -d postgres redis minio
```

### Server'ı lokal Python ile çalıştır:
```bash
cd server
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # SECRET_KEY ve FACE_ENCRYPTION_KEY üret
python run.py
# → http://localhost:5000/health
```

### Tam stack Docker'da (server dahil):
```bash
docker compose --profile full up -d
```

### Pi edge node local simülasyonu (macOS/Linux):
```bash
cd edge
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main    # GPIO simulation mode
```

## 🧪 Test

```bash
cd server && pytest
```

## 📚 Dokümantasyon

- [`plan/README.md`](plan/README.md:1) — Planlama dokümanları indeksi
- [`plan/00_GENEL_BAKIS.md`](plan/00_GENEL_BAKIS.md:1) — Vizyon ve kararlar
- [`plan/02_MIMARI.md`](plan/02_MIMARI.md:1) — Sistem mimarisi
- [`plan/04_VERITABANI_DEGISIKLIKLERI.md`](plan/04_VERITABANI_DEGISIKLIKLERI.md:1) — Modeller
- [`plan/10_TODO_YOL_HARITASI.md`](plan/10_TODO_YOL_HARITASI.md:1) — Haftalık TODO
- [`server/README.md`](server/README.md:1) — Sunucu detayları
- [`edge/README.md`](edge/README.md:1) — Pi detayları

## 🔐 Güvenlik Notları

- `.env` dosyaları ve her türlü anahtar **asla** repo'ya girmez (bkz. [`.gitignore`](.gitignore:1))
- Biyometrik veriler (yüz encoding'leri) Fernet ile şifrelenir (at-rest)
- Device ↔ VPS iletişimi **HMAC-SHA256** ile imzalanır
- SuperAdmin için 2FA zorunludur
- Full detaylar [`plan/07_GUVENLIK_VE_KVKK.md`](plan/07_GUVENLIK_VE_KVKK.md:1)

## 📜 Lisans

Özel, tüm hakları saklıdır. Ticari kullanım için iletişime geçin.

## 👤 Geliştirici

Ahmet Mert Kabak — [@ahmetmertkabak](https://github.com/ahmetmertkabak)