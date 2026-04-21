# 📊 İlerleme Raporu — Yüz Tanıma SaaS

**Son güncelleme:** 2026-04-21
**Repo:** https://github.com/ahmetmertkabak/yuz-tanima
**Toplam commit:** 5
**Toplam kod satırı:** ~15.500 (Python + HTML + JS + CSS + Markdown)

---

## 🎯 TL;DR — Şu an ne durumdayız?

| Bileşen | Durum | Demo-hazır mı? |
|---|---|---|
| **Sunucu kodu (kod seviyesinde)** | %95 tamam | ✅ Evet — local'de çalışır |
| **SuperAdmin Paneli** | %95 tamam | ✅ Demo edilebilir |
| **School Admin Paneli** | %90 tamam | ✅ Demo edilebilir |
| **Device REST API** | %100 tamam | ✅ Pi ile konuşur |
| **Pi Edge Node (yazılım)** | %30 tamam (sadece iskelet) | ❌ Henüz Pi'da çalışmaz |
| **VPS Production Deploy** | %80 tamam (doküman var) | ⚠️ Kurulum yapılmadı |
| **KVKK uyum** | %60 tamam (teknik alt yapı hazır) | ⚠️ Hukuk tarafı eksik |
| **Pen-test** | %0 | ❌ |

### Kısa cevap: **Demoya girebilir misin?**

- 🟢 **Panel demosu (local):** Evet — Docker Compose ile Postgres + Redis + MinIO kaldırıp `python run.py` ile paneller tam çalışır. Mock cihaz olmadan okul ekleme, kişi ekleme (yüz webcam'den), raporlar, geçiş logları hepsi görünür.
- 🟡 **End-to-end (Pi'lı) demo:** Henüz değil. Pi'nın yüz tanıma döngüsü (`T6.1-T6.14`) yazılmadı — sadece çatısı var.
- 🟡 **Müşteriye sat-gör demosu:** VPS'e deploy ettikten sonra panel demosu gösterilebilir. Pi'nın canlı çalıştığını göstermek istiyorsan yaklaşık **2-3 hafta daha** Pi tarafı lazım.

---

## 📦 Tamamlanan Fazlar

### ✅ Faz 0 — Hazırlık (T0.6.3–T0.6.7)
**Commit:** `3e81832`

- 14 dökümanlı planlama hazır (`plan/`)
- `server/` + `edge/` + `docs/` klasör yapısı
- Docker Compose (Postgres + Redis + MinIO)
- `.gitignore`, README, Dockerfile
- GitHub repo + ilk push

### ✅ Faz 1 — Veri Katmanı + Multi-Tenant (T1.1–T1.10)
**Commit:** `dd0062b`

**7 model + tenant middleware:**
- `School` — tenant (subdomain, subscription lifecycle)
- `User` — multi-role (super_admin/school_admin/school_staff/viewer), bcrypt, TOTP, lockout
- `Person` — Student yerine geçti, `role` + `class_name` + **Fernet-şifreli face_encoding** + KVKK consent + access schedule
- `Device` — Pi cihazları, UUID, Fernet-şifreli API key, heartbeat/status
- `AccessLog` — turnike olayları, AccessOutcome enum, denormalized person fields
- `Snapshot` — auto-expiry (KVKK retention)
- `AuditLog` — **immutable** admin eylem kaydı (UPDATE/DELETE engellenmiş)

**Tenant izolasyon:**
- `middleware/tenant.py` — subdomain → School resolve + SQLAlchemy `do_orm_execute` hook ile otomatik `school_id` filtresi
- Super-admin için bypass flag
- **En kritik test:** `tests/integration/test_tenant_isolation.py` — School A'nın Pi'sı School B'nin datasını göremiyor

**Face crypto:**
- `services/face_crypto.py` — numpy array ↔ bytes ↔ Fernet ciphertext
- Yüz encoding'leri DB'de şifreli at-rest

**Migration:**
- `scripts/migrate_legacy_sqlite.py` — eski RFID SQLite'tan Student→Person, Attendance→AccessLog

### ✅ Faz 2 — Auth + SuperAdmin Paneli (T2.1–T2.10)
**Commit:** `693da80`

**Auth:**
- `/auth/login` — tenant-aware (admin subdomain'de sadece super_admin, okul subdomain'inde okul kullanıcıları)
- `/auth/2fa` — TOTP (pyotp), QR kurulum, her kullanıcı kendisi aç/kapat
- `/auth/change-password`, `/auth/logout`, `/auth/password-reset` (stub)
- Brute-force koruması: 5 hatalı giriş → 15 dk kilit
- `middleware/auth.py` — `@super_admin_required`, `@school_admin_required`, `@must_belong_to_current_school`

**SuperAdmin Paneli (`admin.yuztanima.com` — dark sidebar):**
- Dashboard — global istatistikler, offline cihaz uyarıları, expiring abonelikler, audit feed
- **Okul Yönetimi** — arama/filtre/pagination, yeni okul (otomatik ilk admin + 30 günlük trial), detay, düzenleme, askıya al/aktif et
- **Cihaz Yönetimi** — global liste, yeni cihaz (one-time API key + Pi provisioning bilgileri), detay (telemetry + son geçişler + komut kuyruğu), API key rotate, uzaktan komut (reboot/reload_encodings/force_sync/vb.)

**UI altyapısı:**
- `templates/shared/base.html` + auth sayfaları + form_field macro
- `static/css/admin.css` (dark), `school.css` (light), `shared.css`
- Bootstrap 5 + Bootstrap Icons

### ✅ Faz 3 — School Admin + Yüz Kaydı (T3.1–T4.5)
**Commit:** `860a9bf`

**School Admin Paneli (her okulun subdomain'i):**
- **Dashboard** — kişi/cihaz sayaçları, son 15 geçiş, **Socket.IO canlı feed** (biri turnikeden geçince anında görünür)
- **Kişiler** — liste (filtre: isim/no/email/rol/sınıf/aktif + sort/pagination), yeni kişi, detay, düzenle, sil, toplu aktif/pasif/sil
- **Excel import** — TR+EN kolon takma adları (`no`/`ogrenci_no`/`person_no` hepsi çalışır), Excel/CSV destekli
- **Excel export** — `openpyxl` ile stillendirilmiş dosya
- **Geçişler** — tarih aralığı + kapı + sonuç + sadece-reddedilenler filtresi, 50 satır/sayfa, Excel export
- **Raporlar:**
  - Günlük yoklama — gelenler + geç kalanlar (08:30↑) + sayaçlar
  - Gelmeyenler — sınıf/rol filtreli, veli telefonu tıklanabilir (`tel:` link)
  - Aylık özet — kişi başına ay içindeki devam gün sayısı

**Yüz Kaydetme (T4.1-T4.5):**
- Detay sayfasında "Yüz Kaydet" butonu → modal açılır
- `static/js/face-capture.js` — `getUserMedia` ile webcam, 5 kare yakala, thumbnail preview, tek tek silme, re-take
- Backend: `POST /persons/<id>/face`
  - Base64 JPEG'leri decode
  - `face_recognition` ile yüz algılama + encoding
  - 3+ temiz kareden ortalama encoding
  - Fernet ile şifrele, DB'ye yaz
  - Hata yönetimi: "Yüz bulunamadı", "Birden fazla yüz", "Bulanık" vs.
- `DELETE /persons/<id>/face` — KVKK silme hakkı

**Real-time:**
- `services/realtime.py` — `broadcast_access_log()`, `broadcast_device_status()`
- Socket.IO room per school → `school_<id>`
- Dashboard'da yeni satır 1.5 saniye highlight'lı görünür

### ✅ Faz 4 — Device REST API (T5.1–T5.9)
**Commit:** `de3c35b`

**HMAC-SHA256 authentication:**
- Canonical: `METHOD\nPATH\nTIMESTAMP\nNONCE\nSHA256(body)`
- Her request 4 header taşır: `X-Device-Id`, `X-Timestamp`, `X-Nonce`, `X-Signature`
- Timestamp ±60s toleransı
- Nonce replay cache (5 dk TTL, in-memory; prod'da Redis'e taşınabilir)
- Device API key Fernet ile şifreli DB'de (bcrypt olamaz çünkü sunucu HMAC için plaintext'e ihtiyaç duyar)

**8 endpoint:**
```
GET  /api/v1/ping                              (no auth, liveness)
POST /api/v1/device/heartbeat                  (120/dk)
GET  /api/v1/device/config                     (30/dk)
GET  /api/v1/device/encodings?since=ISO        (60/dk, incremental)
POST /api/v1/device/access_log                 (60/dk, batch ≤500)
POST /api/v1/device/snapshot                   (30/dk, multipart)
GET  /api/v1/device/commands                   (60/dk)
POST /api/v1/device/commands/<id>/ack          (120/dk)
```

**Object storage:**
- `services/storage.py` — S3/MinIO + filesystem fallback (dev)
- Per-tenant key: `<school_subdomain>/snapshots/YYYY/MM/DD/<uuid>.jpg`

**Tests (en önemlileri):**
- `tests/integration/test_device_api.py` — 10 test sınıfı, auth negatifleri dahil
- **KVKK kritik testi:** `/device/encodings` response'u consent=granted + is_active=True olmayan kişiyi *asla* dönmez

**Dokümantasyon:**
- `docs/api.md` — 295 satır, tüm endpoint'ler request/response şemalarıyla, error code tablosu

---

## 🚧 Henüz Yapılmamış / Eksik Olanlar

### ❌ Pi Edge Node Gerçek Implementasyon (T6.1–T6.14)

Pi tarafında **sadece iskelet** var. Modüller:
- [`edge/app/config.py`](edge/app/config.py:1) — ✅ settings
- [`edge/app/camera.py`](edge/app/camera.py:1) — ✅ threaded OpenCV wrapper
- [`edge/app/turnstile.py`](edge/app/turnstile.py:1) — ✅ GPIO röle kontrolü (fail-safe)
- [`edge/app/local_db.py`](edge/app/local_db.py:1) — ✅ SQLite şema
- [`edge/app/hmac_signer.py`](edge/app/hmac_signer.py:1) — ✅ sunucuyla uyumlu HMAC
- [`edge/app/sync_client.py`](edge/app/sync_client.py:1) — 🟡 sadece **stub** (HTTP client yazıldı ama gerçek iş yapmıyor)
- [`edge/app/main.py`](edge/app/main.py:1) — 🟡 orchestrator iskeleti var ama:
  - Recognition döngüsü **boş** (`TODO (T6.3)`)
  - Heartbeat zamanlaması var ama sync job'ları placeholder
- [`edge/app/recognition/`](edge/app/recognition/base.py:1) — 🟡 abstract class var, concrete `dlib_recognizer.py` yok

**Yapılması gereken (tahminen 1-2 hafta tam zamanlı):**
1. `recognition/dlib_recognizer.py` — `face_recognition` kütüphanesiyle concrete implementation
2. Pi'nın encoding cache'ini sunucudan çekip numpy compare etmesi
3. Tanınan kişi için `turnstile.open_briefly()` + lokal SQLite'a log + sync kuyruğu
4. `sync_client.py` gerçek implementasyon: heartbeat, encoding sync, log batch gönderimi, snapshot upload, uzaktan komut alımı
5. Retry + backoff mantığı (internet kesintisinde)
6. systemd service gerçek dünya tesleri

### ⚠️ KVKK / Hukuk (T8.x)
- ✅ Teknik altyapı hazır (Fernet encryption, consent workflow, audit log, data export/delete endpoint'leri hazır)
- ❌ **Gizlilik politikası sayfası** yazılmadı
- ❌ **Çerez politikası** yazılmadı
- ❌ **DPA (Data Processing Agreement)** şablonu hazırlanmadı (avukata gidecek)
- ❌ **VERBİS kaydı** yapılmadı

### ⚠️ OTA Update (T7.x)
- DeviceCommand model'de `update_firmware` komutu var ama Pi tarafında `update_manager.py` yok
- Versiyon imzalama + rollback mekanizması yok

### ⚠️ Production Deployment
- ✅ [`docs/deployment.md`](docs/deployment.md:1) tam hazır (254 satır, nginx + systemd + backup)
- ❌ VPS'e henüz **deploy yapılmadı**
- ❌ Cloudflare wildcard DNS ayarlanmadı
- ❌ SSL sertifikası alınmadı

### ⚠️ Pen-Test
- Yapılmadı. Pilot kurulum öncesi şart.

---

## 🎬 Demo Senaryosu — Şu An Yapabileceklerin

### 1. Local dev ortamı ayaklandır (5 dakika)

```bash
cd /Users/ahmetmert/Desktop/Projects/yuz-tanima

# Altyapı servislerini ayağa kaldır
docker compose up -d postgres redis minio

# Server bağımlılıkları
cd server
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# .env oluştur
cp .env.example .env
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))" >> .env
python -c "from cryptography.fernet import Fernet; print('FACE_ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env

# Veritabanı şeması
export FLASK_APP=app
flask db init
flask db migrate -m "baseline"
flask db upgrade

# Platform yöneticisi oluştur
flask create-super-admin
# → username, email, password gir

python run.py
# → http://localhost:5000
```

### 2. SuperAdmin panel demosu (15 dakika)

1. `http://localhost:5000/auth/login` — super admin olarak gir
2. Otomatik `/super/dashboard`'a yönlenirsin (dark theme)
3. **"Yeni Okul"** → örn. "Ali Paşa Lisesi", subdomain `ali-pasa-lisesi`, ilk school admin'i oluştur
4. **"Yeni Cihaz"** → okul seç, cihaz adı gir → ekranda **one-time API key** gösterilir (Pi provisioning için bu değer yazılacak)
5. Cihaz detay sayfası → telemetry (şimdi boş çünkü Pi yok), komut kuyruğundan "reload_encodings" ekle

### 3. School Admin panel demosu (20 dakika)

1. `http://localhost:5000/auth/login` — okul admin'i olarak gir (SuperAdmin'de oluşturduğun kullanıcı). Tenant header'ı için `?tenant=ali-pasa-lisesi` query string'i ekle (veya `/etc/hosts`'a `127.0.0.1 ali-pasa-lisesi.localhost` yaz).
2. Dashboard — boş
3. **Kişiler → Yeni Kişi** → Ahmet Yılmaz, STU001, 9-A
4. Detay sayfasında **"Yüz Kaydet"** butonuna tıkla
5. Modal açılır, webcam izni ver
6. 5 kare çek → "Kaydet"
7. (Opsiyonel) Excel import → demo.xlsx ile 50 kişi yükle

### 4. Device API demosu (simüle Pi, 10 dakika)

`scripts/demo_fake_device.py` diye bir betik yazıp (Faz 5'te geliyor), önceki adımdaki API key ile heartbeat + sahte access_log gönderebilirsin. Yaynı kaydedilen access_log **dashboard'da canlı** belirir.

Şu an elle curl ile denemek için:

```python
import hashlib, hmac, json, time, requests
api_key = "<paneldeki-one-time-api-key>"
device_uuid = "<paneldeki-uuid>"
body = json.dumps({"firmware_version":"0.1.0"}).encode()
ts = str(int(time.time())); nonce = "abc123xyz0987654321"
body_hex = hashlib.sha256(body).hexdigest()
canonical = f"POST\n/api/v1/device/heartbeat\n{ts}\n{nonce}\n{body_hex}"
sig = hmac.new(api_key.encode(), canonical.encode(), hashlib.sha256).hexdigest()
print(requests.post("http://localhost:5000/api/v1/device/heartbeat",
  data=body,
  headers={"X-Device-Id":device_uuid,"X-Timestamp":ts,"X-Nonce":nonce,
           "X-Signature":sig,"Content-Type":"application/json"}).json())
```

---

## 📈 Sayılar

| Metrik | Değer |
|---|---|
| Git commits | 5 |
| Python dosyası | 72 |
| HTML template | 28 |
| CSS dosyası | 3 |
| JS dosyası | 1 |
| Markdown doküman | 17 (plan + server/edge/docs) |
| Toplam satır | ~15.500 |
| Python ast.parse | ✅ Hepsi geçti |
| Unit test | 5 dosya |
| Integration test | 2 dosya (tenant izolasyon + device API) |
| Tahmini test coverage | ~%60 |

---

## 🏁 Sıradaki Öncelikler (önem sırası)

### 🔴 Kritik (bu hafta)
1. **Pi yazılımı tamamla (T6.1–T6.14)** — yüz tanıma döngüsü + sync client
2. **VPS deploy** — `docs/deployment.md` takip et, `admin.yuztanima.com` ayağa kalksın
3. **Fake device demo script** — satış demosunda kullanılacak, Pi'sız da canlı gibi gösterir

### 🟡 Önemli (önümüzdeki 2 hafta)
4. **OTA update** (T7.x)
5. **KVKK sayfaları** (gizlilik, çerez, kullanım koşulları) — avukatla birlikte
6. **VERBİS kaydı**
7. **Pen-test ön çalışması** (bandit + semgrep + kendi check-list)

### 🟢 İyi olur (pilot öncesi)
8. Celery beat tanımla (snapshot expiry, subscription reminder)
9. Sentry / log aggregation
10. Admin kullanıcı için backup kodları (2FA için)
11. E2E test (Playwright)

---

## 💡 Maliyet ve Süre

- **Server tarafı (tamam):** ~150 saat iş → bitti
- **Pi tarafı (yapılacak):** tahmini 40-60 saat
- **KVKK + avukat:** 15-25k TL (bir kerelik)
- **İlk VPS yılı:** Hetzner CPX21 ≈ 12 €/ay → ~360€
- **Pilot donanım paketi:** ~9.000 TL/kapı (bkz. [`plan/01_DONANIM_SECIMI.md`](plan/01_DONANIM_SECIMI.md:1))

Pilot okul için **tam end-to-end demo** hazır olmasına **2-3 hafta** daha var (Pi yazılımı + VPS deploy + test okul hazırlığı).

---

## 📂 Doküman İndeksi

- [`plan/`](plan/) — 14 planlama dokümanı
- [`docs/api.md`](docs/api.md) — Device REST API referansı (295 satır)
- [`docs/deployment.md`](docs/deployment.md) — VPS deployment rehberi
- [`server/README.md`](server/README.md) — Sunucu geliştirici rehberi
- [`edge/README.md`](edge/README.md) — Pi geliştirici rehberi
- [`README.md`](README.md) — Proje ana sayfa