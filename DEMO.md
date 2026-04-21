# 🎬 Demo — Local'de 5 Dakikada Ayağa Kaldır

Bu rehber, sistemi **Pi veya VPS olmadan** kendi laptop'unda canlı çalışır
hale getirir. Sonunda:

- 👑 Super Admin paneli (dark theme) — 1 okul + 2 cihaz + 30 öğrenci görebilir
- 🏫 School Admin paneli (okula özgü) — kişi listesi, yoklama, raporlar
- 📡 "Sahte Pi" script'i her 3-6 saniyede bir HMAC-imzalı geçiş olayı gönderir
- 🔴 Dashboard Socket.IO üzerinden canlı olarak yeni geçişleri gösterir

Tüm bu akış gerçekten denendi — `docs/demo-screenshots/` altında ekran görüntüleri var.

---

## ✅ Önkoşullar

- macOS veya Linux
- Python 3.11 (macOS'te `brew install python@3.11`)
- 2 terminal penceresi

Docker, Postgres, Redis, MinIO **gerekmiyor** — dev mode SQLite + in-process
Socket.IO kullanıyor.

---

## 1. Kurulum (tek seferlik, ~2 dakika)

```bash
cd /Users/ahmetmert/Desktop/Projects/yuz-tanima

# Virtualenv
cd server
python3.11 -m venv .venv
source .venv/bin/activate

# Lite bağımlılık seti (Postgres/face_recognition yok)
pip install -r requirements-demo.txt
```

## 2. Environment + Schema + Seed

```bash
# .env oluştur (server/ içindeyken)
cat > .env <<EOF
FLASK_ENV=development
FLASK_APP=app
SECRET_KEY=demo-secret-key
BASE_DOMAIN=localhost
SUPER_ADMIN_SUBDOMAIN=admin
LOG_LEVEL=INFO
EOF
python -c "from cryptography.fernet import Fernet; print('FACE_ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env

# Schema + demo data
mkdir -p instance
python -c "
from app import create_app
from app.extensions import db
app = create_app('development')
with app.app_context():
    db.create_all()
    print('✓ Schema created')
"
python -m scripts.demo_seed
```

Seed sonunda kredensiyaller + cihaz UUID + API key ekrana yazılır. Bunlara
demo boyunca ihtiyacın olacak.

## 3. Sunucuyu çalıştır (Terminal 1)

```bash
cd server
source .venv/bin/activate
PORT=5001 python run.py
```

(AirPlay 5000'i kullanıyorsa 5001 seç. `Ctrl+C` ile durdurulur.)

Hızlı sağlık kontrolü:
```bash
curl http://localhost:5001/health
# {"app":"Yüz Tanıma SaaS","status":"ok","version":"0.1.0"}
```

## 4. Sahte Pi simülatörünü başlat (Terminal 2)

Seed'in yazdırdığı UUID ve API key'i aşağıya kopyala:

```bash
cd server
source .venv/bin/activate

# Eğer macOS'te proxy varsa
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
export NO_PROXY="127.0.0.1,localhost"
export no_proxy="127.0.0.1,localhost"

export SERVER_URL=http://localhost:5001
export DEVICE_UUID=<seed'den gelen UUID>
export API_KEY=<seed'den gelen API_KEY>

python -m scripts.demo_fake_device live
```

Çıktı şöyle olmalı:
```
[16:03:12] ♥  heartbeat → ok, pending_commands=0, tolerance=0.55
[16:03:15] → access_log granted (person=42) accepted=1
[16:03:19] → access_log granted (person=18) accepted=1
[16:03:24] → access_log denied_unknown (unknown) accepted=1
...
```

Her satır sunucuya tam **HMAC-SHA256 imzalı** gerçek API çağrısı. Nonce
replay guard, timestamp window, hepsi doğrulanıyor.

---

## 5. Browser Demoları

### 👑 Super Admin (biz — tüm okullar)

URL: **http://localhost:5001/auth/login**

- Kullanıcı: `super`
- Şifre: `demo1234`

→ `/super/dashboard` — tüm okullar, online/offline cihazlar, audit feed
→ `/super/schools` — okul listesi + arama + "Yeni Okul" formu
→ `/super/devices` — global cihaz listesi + durum
→ `/super/devices/1` — cihaz detay + **canlı telemetry** (fake device heartbeat'leri sayesinde)
→ Cihaz detayında "Reboot / Reload Encodings / ..." komutu queue'a ekleyebilirsin; fake-device `python -m scripts.demo_fake_device commands` çalıştırınca ack eder.

### 🏫 School Admin (Demo Lisesi)

URL: **http://localhost:5001/auth/login?tenant=demo**

- Kullanıcı: `admin`
- Şifre: `demo1234`

Menü:
- **Dashboard** — öğrenci/personel sayısı + bugün kim geldi + son 15 geçiş +
  **Socket.IO canlı feed** (fake-device her yeni olay → dashboard anlık günceller)
- **Kişiler** — 32 kişi (30 öğrenci + 2 öğretmen), filtre + arama + pagination
  + toplu aktif/pasif/sil + "Yeni Kişi" → webcam ile yüz kaydı modal'ı
  (Mac'te izin verip test edebilirsin — gerçek yüz encoding çıkarmak için
  `face_recognition` gerekiyor, lite paket onu kurmuyor; panel görünümü
  çalışır ama encoding oluşturma hata verir. Tam çalıştırmak için
  `pip install face-recognition` ekle.)
- **Geçişler** — tarih aralığı + kapı + sonuç filtresi, Excel export
- **Raporlar → Günlük** — bugün gelenler + geç kalanlar
- **Raporlar → Gelmeyenler** — veli telefonu ile tıklanabilir
- **Raporlar → Aylık** — kişi başına devam gün sayısı

### 📡 Device REST API (curl ile)

`docs/api.md` içinde tüm endpoint'ler + örnekler. En basit test:

```bash
curl http://localhost:5001/api/v1/ping
# {"api_version":"v1","status":"ok"}
```

Authenticated istek için `scripts/demo_fake_device.py` kaynağına bak — HMAC
signer fonksiyonu tamamıyla `edge/app/hmac_signer.py` ile uyumlu.

---

## 6. Kapatma

```bash
# Her iki terminal'de Ctrl+C
# Veya fake-device'ı kill:
pkill -f "demo_fake_device live"
pkill -f "python run.py"
```

Tam temizlik:
```bash
rm server/instance/dev.db   # DB'yi sıfırla
rm server/.env               # env'i temizle
```

---

## 🎯 Ne Gerçekten Çalıştı (Gerçek Demo'dan)

Bu checklist, yukarıdaki adımlar denendikten sonraki çıkan durumu özetler:

| Bileşen | Durum |
|---|---|
| `/health` + `/api/v1/ping` | ✅ 200 |
| Super admin login + dashboard | ✅ Ekran görüntüsü `demo-02-super-dashboard.png` |
| Schools list (1 okul görünür) | ✅ `demo-03-schools-list.png` |
| Devices list (2 cihaz, canlı online statüsü) | ✅ `demo-04-devices.png` |
| School admin login (`?tenant=demo`) | ✅ `demo-05-school-dashboard.png` |
| 32 kişi listesi (filtre + pagination) | ✅ `demo-06-persons.png` |
| Access logs (240+ kayıt) | ✅ `demo-07-access-logs.png` |
| Raporlar indeksi | ✅ `demo-08-reports-index.png` |
| Günlük rapor | ✅ `demo-09-reports-daily.png` |
| Gelmeyenler raporu | ✅ `demo-10-reports-absent.png` |
| Fake device → heartbeat HMAC imzalama | ✅ `200 OK` |
| Fake device → access_log (granted + unknown) | ✅ Dashboard canlı günceller |
| Nonce replay guard (aynı header 2× gönder → 401) | ✅ Integration testlerinde |
| Tenant izolasyon (School A School B'yi görmez) | ✅ Integration testinde |

---

## ⚠️ Bilinen Sınırlamalar (Pi/VPS gelmeden)

1. **Yüz tanıma server-side enroll:** `face-recognition` kütüphanesi `requirements-demo.txt`'e dahil değil (dlib derlemesi uzun sürüyor). Webcam modal'ı açılır ama "Kaydet" 500 döner. Tam test için `pip install face-recognition dlib` ekle.

2. **Socket.IO polling fallback:** Demo mode threading async'inde çalışır. Production'da Redis + eventlet kullanılır (bkz [`docs/deployment.md`](docs/deployment.md:1)).

3. **Rate limit kapalı:** Dev'de rahat test için `RATELIMIT_ENABLED=False`.

4. **Pi yazılımı iskelet:** `edge/` altında config/camera/turnstile/HMAC var ama recognition döngüsü boş. Gerçek Pi'da çalışması için T6.3-T6.14 yapılacak.

---

## 📂 Demo Artefaktları

- [`docs/demo-screenshots/demo-01-login.png`](docs/demo-screenshots/demo-01-login.png) → login sayfası
- [`docs/demo-screenshots/demo-02-super-dashboard.png`](docs/demo-screenshots/demo-02-super-dashboard.png) → super admin dashboard
- [`docs/demo-screenshots/demo-03-schools-list.png`](docs/demo-screenshots/demo-03-schools-list.png) → okul listesi
- [`docs/demo-screenshots/demo-04-devices.png`](docs/demo-screenshots/demo-04-devices.png) → cihaz listesi
- [`docs/demo-screenshots/demo-05-school-dashboard.png`](docs/demo-screenshots/demo-05-school-dashboard.png) → school admin dashboard + son geçişler
- [`docs/demo-screenshots/demo-06-persons.png`](docs/demo-screenshots/demo-06-persons.png) → 32 kişi listesi
- [`docs/demo-screenshots/demo-07-access-logs.png`](docs/demo-screenshots/demo-07-access-logs.png) → geçiş logları (240+)
- [`docs/demo-screenshots/demo-08-reports-index.png`](docs/demo-screenshots/demo-08-reports-index.png) → rapor kartları indeksi
- [`docs/demo-screenshots/demo-09-reports-daily.png`](docs/demo-screenshots/demo-09-reports-daily.png) → günlük yoklama
- [`docs/demo-screenshots/demo-10-reports-absent.png`](docs/demo-screenshots/demo-10-reports-absent.png) → gelmeyenler listesi

---

## 🚀 Sıradaki Adımlar

- **Pi yazılımını tamamla** (tahminen 40-60 saat) — `edge/app/recognition/dlib_recognizer.py` + `sync_client.py` gerçek impl
- **VPS kurulumu** — `docs/deployment.md` adım adım
- **KVKK + avukat** — gizlilik politikası + DPA + VERBİS kaydı
- **Pilot okul** — ilk kurulum + 2 hafta izleme

Detaylı TODO için [`plan/10_TODO_YOL_HARITASI.md`](plan/10_TODO_YOL_HARITASI.md:210).