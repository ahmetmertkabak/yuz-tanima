# 🏗️ 02 - Sistem Mimarisi (Multi-Tenant SaaS)

## 🎯 Ana Mimari Kararı

Proje **3 ana katman** üzerine kurulur:

1. **VPS (Merkezi Sunucu)** — tüm okulların beyni, tek sunucu
2. **Pi Edge Node (Okul Tarafı)** — her kapıya 1 Pi, lokal tanıma + turnike
3. **Web Paneller** — 3 farklı seviyede kullanıcı arayüzü

---

## 🌐 KUŞ BAKIŞI MİMARİ

```
                  ┌────────────────────────────────────────────┐
                  │        MERKEZİ VPS (yuztanima.com)         │
                  │                                            │
                  │  ┌──────────────────────────────────────┐  │
                  │  │  Flask App (Gunicorn + Nginx)        │  │
                  │  │                                      │  │
                  │  │  - Super Admin Panel                 │  │
                  │  │  - School Admin Panel (subdomain)    │  │
                  │  │  - REST API (/api/v1/*)              │  │
                  │  │  - WebSocket (canlı izleme)          │  │
                  │  │  - Tenant Middleware                 │  │
                  │  └──────────────────────────────────────┘  │
                  │                                            │
                  │  ┌──────────────────────────────────────┐  │
                  │  │  PostgreSQL (Multi-tenant DB)        │  │
                  │  │  - schools, users, persons,          │  │
                  │  │  - devices, access_logs, snapshots   │  │
                  │  └──────────────────────────────────────┘  │
                  │                                            │
                  │  ┌──────────────────────────────────────┐  │
                  │  │  Redis (Cache + Queue)               │  │
                  │  │  - Session, WS pub/sub               │  │
                  │  │  - Celery task queue                 │  │
                  │  └──────────────────────────────────────┘  │
                  │                                            │
                  │  ┌──────────────────────────────────────┐  │
                  │  │  Object Storage (S3 benzeri)         │  │
                  │  │  - Yüz fotoğrafları                  │  │
                  │  │  - Snapshot kayıtları (tanımayan)    │  │
                  │  └──────────────────────────────────────┘  │
                  └──────────┬─────────────────────────────────┘
                             │ HTTPS (REST + WebSocket)
                             │ Her Pi'nin kendi API key'i
          ┌──────────────────┼──────────────────────┬─────────────┐
          │                  │                      │             │
     ┌────▼─────┐       ┌────▼─────┐          ┌────▼─────┐  ┌────▼─────┐
     │  OKUL A  │       │  OKUL B  │          │  OKUL C  │  │  OKUL N  │
     │          │       │          │          │          │  │          │
     │ Pi#1 ────│       │ Pi#1 ────│          │ Pi#1 ────│  │ Pi#1 ────│
     │  └Kamera │       │  └Kamera │          │  └Kamera │  │  └Kamera │
     │  └Röle ──│──► T  │  └Röle ──│──► T     │  └Röle ──│  │  └Röle ──│
     │ Pi#2 ... │       │          │          │ Pi#2 ... │  │          │
     └──────────┘       └──────────┘          └──────────┘  └──────────┘
```

**T = Turnike**

---

## 🖥️ KATMAN 1: MERKEZİ VPS

### Sunucu Gereksinimleri (İlk Aşama)
| Özellik | Minimum | Tavsiye | Not |
|---|---|---|---|
| CPU | 2 vCPU | 4 vCPU | Python + PostgreSQL için |
| RAM | 4 GB | 8 GB | Tanıma yapmıyor sadece API |
| Disk | 80 GB SSD | 160 GB SSD | Fotoğraf/snapshot için |
| Bandwidth | 2 TB/ay | 5 TB/ay | Sync trafiği için |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS | |

### VPS Sağlayıcıları (Türkiye için)
| Sağlayıcı | Aylık Fiyat | Notlar |
|---|---|---|
| **Hetzner** (Almanya) | €8-20 (~300-700 TL) | En iyi fiyat/performans, KVKK uygun |
| **DigitalOcean** (EU) | $12-40 (~400-1400 TL) | Kolay yönetim, iyi dokümantasyon |
| **Contabo** (Almanya) | €6-15 (~220-520 TL) | Ucuz ama destek yavaş |
| **Natro/Yedekoleji** (TR) | 200-600 TL | Yerli, Türkçe destek, KVKK 100% uyumlu |
| **AWS Lightsail** | $10-40 | Profesyonel ama pahalı |

**Tavsiye:** İlk aşamada **Hetzner CPX21** (~400 TL/ay). 10-20 okula kadar yeter. Sonra yukarı çıkılır.

### Yazılım Stack
```
Ubuntu 22.04 LTS
├── Nginx (reverse proxy, SSL terminasyon)
├── Gunicorn (WSGI, 4-8 worker)
│   └── Flask App
│       ├── Flask-SQLAlchemy
│       ├── Flask-Login (role-based)
│       ├── Flask-Migrate
│       ├── Flask-SocketIO (canlı güncellemeler)
│       └── Flask-Limiter (rate limiting)
├── PostgreSQL 15
├── Redis 7 (cache + Celery broker)
├── Celery (background tasks — rapor üretimi, sync vb.)
├── MinIO veya Amazon S3 (dosya depolama)
├── Certbot (Let's Encrypt SSL)
└── Fail2ban (brute force koruması)
```

### URL Yapısı
```
https://yuztanima.com              → Pazarlama/Landing
https://admin.yuztanima.com        → Super Admin Paneli (sadece biz)
https://[okul].yuztanima.com       → Okul Admin Paneli (subdomain)
https://api.yuztanima.com/v1/*     → REST API (Pi'lar buraya bağlanır)
```

### Wildcard SSL
```
*.yuztanima.com    Let's Encrypt + DNS-01 challenge
```
Tek sertifika tüm okulları kapsar.

---

## 🤖 KATMAN 2: PI EDGE NODE (Okul Tarafı)

### Görev Dağılımı
Her Pi şu işleri yapar:
1. **Kamera stream** — USB webcam'den frame yakala
2. **Yüz algılama** — Frame'de yüz var mı? (OpenCV/dlib)
3. **Yüz tanıma** — Encoding çıkar, lokal cache ile karşılaştır
4. **Turnike kontrolü** — Röle tetikle, GPIO sinyali
5. **Sync** — Logları VPS'e gönder, yeni encoding'leri indir
6. **Heartbeat** — "Ben hayattayım" sinyali (30 sn'de bir)

### Yazılım Stack (Pi Tarafı)
```
Raspberry Pi OS (Bookworm, 64-bit)
├── Python 3.11
├── OpenCV 4.x
├── face_recognition (dlib) VEYA insightface
├── SQLite (lokal cache DB)
├── RPi.GPIO (röle kontrolü)
├── Flask (mini-lokal API — debugging için)
├── Requests (VPS ile iletişim)
├── python-socketio (canlı komut almak için)
└── systemd service (otomatik başlatma)
```

### Thread Mimarisi (Mevcut Kodu Baz Alarak)
```
┌──────────────────────────────────────────────────────────────┐
│                        PI EDGE NODE                          │
│                                                              │
│  Thread 1: _camera_loop                                      │
│    ├─ OpenCV VideoCapture frame al                          │
│    ├─ Yüz algıla (Haar Cascade / MTCNN)                     │
│    └─ frame_queue'ya at                                     │
│                                                              │
│  Thread 2: _recognition_loop                                │
│    ├─ frame_queue'dan al                                    │
│    ├─ face_encoding üret                                    │
│    ├─ Lokal cache ile karşılaştır (tolerance check)         │
│    └─ Bulunursa → action_queue'ya at                        │
│       Bulunamazsa → snapshot kaydet + unknown_queue         │
│                                                              │
│  Thread 3: _action_loop                                     │
│    ├─ action_queue'dan al                                   │
│    ├─ Bugün zaten girmiş mi? (duplicate check)             │
│    ├─ Röle tetikle (turnike aç)                             │
│    ├─ LCD/ekran "Hoşgeldin [isim]"                          │
│    ├─ Buzzer beep_success                                   │
│    └─ Lokal SQLite'a access_log kaydet                      │
│                                                              │
│  Thread 4: _sync_loop (15 saniyede bir)                     │
│    ├─ Lokal SQLite'dan 'unsynced' logları al               │
│    ├─ VPS API'ye POST et                                    │
│    ├─ Başarılıysa 'synced=True' işaretle                    │
│    └─ Network hatası → kuyrukta bekle                       │
│                                                              │
│  Thread 5: _encoding_sync_loop (1 dakikada bir)             │
│    ├─ VPS'den "yeni/güncellenen encoding var mı?" sor      │
│    ├─ Varsa lokal cache'i güncelle                          │
│    └─ Silinen kişilerin encoding'ini düş                    │
│                                                              │
│  Thread 6: _heartbeat_loop (30 saniyede bir)                │
│    ├─ VPS'e "ben hayattayım, CPU %X, disk %Y" gönder       │
│    └─ VPS panelde "online" görünür                          │
│                                                              │
│  Thread 7: _command_listener (WebSocket)                    │
│    ├─ VPS'den komut bekle (reboot, update, reload)         │
│    └─ Komut geldiğinde ilgili action'ı çalıştır             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Lokal SQLite Cache Yapısı

Pi'daki SQLite'ta 3 tablo olur:
```sql
-- Yüz tanıma için lokal cache (VPS'den sync edilir)
persons_cache (
  id INTEGER PRIMARY KEY,
  person_id INTEGER,        -- VPS'teki ID
  name TEXT,
  face_encoding BLOB,       -- 128-dim vektör
  is_active BOOLEAN,
  updated_at TIMESTAMP
)

-- VPS'e gönderilecek geçiş logları
access_logs_pending (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id INTEGER,
  direction TEXT,
  confidence REAL,
  timestamp TIMESTAMP,
  synced BOOLEAN DEFAULT 0,
  snapshot_path TEXT
)

-- Cihaz ayarları
device_config (
  key TEXT PRIMARY KEY,
  value TEXT
)
```

### Offline Çalışma Senaryosu

```
t=0:     Pi internet bağlı, normal çalışıyor
t=5dk:   ISP kesinti oldu, Pi VPS'e bağlanamıyor
t=5-70dk: Pi YİNE DE tanıma yapar (lokal cache kullanır)
         Turnike açar, loglar SQLite'a kaydolur (synced=0)
t=70dk:  İnternet geri geldi
t=70dk+5sn: Sync thread devreye girer, tüm loglar VPS'e push olur
t=71dk:  VPS'te tüm eksik loglar göründü ✅
```

**Sonuç:** Okul interneti günlerce kopuk olsa bile sistem çalışmaya devam eder.

---

## 🌐 KATMAN 3: WEB PANELLER

### Panel 1: Super Admin (biz)
**URL:** `admin.yuztanima.com`  
**Kullanıcılar:** Sadece firma sahibi + teknik ekip (~2-5 kişi)  
**Özellikler:**
- Okul listesi (tenant listesi) + ekle/düzenle/deaktif
- Her okulun cihaz durumu (heartbeat izleme)
- Tüm okulların toplu istatistik
- Abonelik/lisans yönetimi
- OTA update push
- Sistem logları, hata takibi
- Destek bileti oluşturma

### Panel 2: School Admin
**URL:** `[okuladı].yuztanima.com`  
**Kullanıcılar:** Okul müdürü, müdür yardımcısı, IT sorumlusu (~3-10 kişi)  
**Özellikler:**
- Öğrenci/öğretmen listesi + CRUD
- Yüz kayıt (webcam ile anında)
- Canlı geçiş izleme (dashboard)
- Günlük/aylık raporlar + Excel export
- Gelmeyen / geç kalan listesi
- Kendi okulunun cihazları (sadece görüntüleme — uzaktan yönetim SuperAdmin'de)
- Kullanıcı (personel) ekleme (kısıtlı yetki)

### Panel 3: Okul Personeli (opsiyonel)
**URL:** Aynı panel, farklı role  
**Yetkiler:** Sadece rapor görüntüleme, öğrenci arama, dokunamaz

---

## 🔄 VERI AKIŞLARı

### Akış 1: Yeni Okul Ekleme
```
SuperAdmin:
  1. admin.yuztanima.com'a giriş
  2. "Yeni Okul" → ad, adres, subdomain, abonelik tipi
  3. Okul admini kullanıcı oluştur (email + geçici şifre)
  4. Sistem otomatik:
     - DB'ye school kaydı
     - Subdomain DNS'e ekleme (Cloudflare API)
     - SSL sertifika (wildcard zaten var)
     - İlk device_id + api_key üret
  5. Donanım paketi hazırla → Pi'ya api_key flash
  6. Okula kargo + kurulum
```

### Akış 2: Öğrenci Ekleme (Okul Admini)
```
SchoolAdmin:
  1. [okul].yuztanima.com → login
  2. "Öğrenciler" → "Yeni"
  3. Ad, sınıf, no, rol girer
  4. "Yüz Kaydet" → webcam açılır
  5. Fotoğraf çeker → backend face_encoding üretir
  6. DB'ye kaydeder (school_id ile)
  7. Okulun Pi'ları bir sonraki sync'de encoding'i indirir
```

### Akış 3: Geçiş Anı (Yüksek Frekans)
```
Pi (lokal):
  1. Kamera frame yakalar
  2. Yüz algılar
  3. Encoding üretir
  4. Lokal cache'de arar (~50-200ms)
  5. BULDU → röle + log (SQLite)
  6. Her 15sn'de bir sync → VPS
  
VPS (async):
  1. Pi'dan batch log alır
  2. DB'ye yazar
  3. WebSocket ile admin dashboardlarına push eder
  4. Canlı dashboard'da "10:23 Ahmet Yılmaz girdi" görünür
```

### Akış 4: OTA Update
```
SuperAdmin:
  1. Yeni yazılım versiyonu hazır (v1.2.0)
  2. admin panelde "Update Push" → seçili okullar
  
Pi (otomatik):
  1. Gece 03:00'te VPS'e sorar "güncel versiyon nedir?"
  2. v1.2.0 var → zip indir
  3. Kendini günceller, restart
  4. Başarı durumunu VPS'e bildirir
```

---

## 🔐 TENANT İZOLASYONU (KRİTİK)

### Strateji: Row-Level Security (Shared DB, Shared Schema)

Tek DB, tüm tablolarda `school_id` kolonu.

**Her sorguda otomatik filtreleme:**
```python
# Flask middleware
@app.before_request
def set_tenant_context():
    if current_user.is_authenticated:
        g.school_id = current_user.school_id

# SQLAlchemy event listener
@event.listens_for(Session, "do_orm_execute")
def filter_by_tenant(execute_state):
    if execute_state.is_select:
        execute_state.statement = execute_state.statement.where(
            ModelClass.school_id == g.school_id
        )
```

**Avantajlar:**
- ✅ Tek DB → yönetim kolay
- ✅ Cross-tenant rapor kolay (SuperAdmin için)
- ✅ Ölçeklenme iyi (10.000 okul bile kaldırır)

**Dezavantajlar:**
- ⚠️ Bir kod hatası tenant sızıntısına sebep olabilir (testler kritik)
- ⚠️ Büyük tablolar tek DB'de → indexleme dikkatli olmalı

**Alternatif:** Okul başına ayrı DB (schema-per-tenant). Daha güvenli ama yönetimi katlanılmaz hale gelir (50 okul = 50 DB migration!). Shared schema + tenant_id kesinlikle doğru seçim.

### Pi İzolasyonu
Her Pi kendi `api_key`'i ile VPS'e bağlanır. VPS her request'te:
```python
@api.before_request
def authenticate_device():
    api_key = request.headers.get('X-Device-Key')
    device = Device.query.filter_by(api_key=api_key, is_active=True).first()
    if not device:
        abort(401)
    g.device = device
    g.school_id = device.school_id  # tenant otomatik
```

Bu sayede bir Pi sadece kendi okulunun verisini görür/gönderir.

---

## 📊 ÖLÇEKLENMe (Scalability)

### İlk Aşama: 1-10 Okul
- Tek VPS (4 vCPU, 8 GB RAM)
- PostgreSQL local
- Redis local
- Maliyet: ~400-600 TL/ay

### Orta Ölçek: 10-50 Okul
- VPS upgrade (8 vCPU, 16 GB RAM)
- PostgreSQL ayrı sunucuda
- CDN for static files
- Maliyet: ~1500-3000 TL/ay

### Büyük Ölçek: 50-500 Okul
- Load balancer + 2-3 app server
- PostgreSQL primary + read replica
- Redis Sentinel cluster
- S3 storage ayrı
- Maliyet: ~8000-20000 TL/ay

Bu aşamalara **aynı kod tabanıyla** geçilir. Baştan iyi mimari kurarsak refactor gerekmez.

---

## 🔗 API YAPISI (Özet)

```
# Device API (Pi'lar kullanır)
POST /api/v1/device/heartbeat
POST /api/v1/device/access_log
POST /api/v1/device/access_log/batch
GET  /api/v1/device/encodings?since=[timestamp]
GET  /api/v1/device/config
POST /api/v1/device/snapshot

# Admin API (panel kullanır)
GET  /api/v1/schools           (SuperAdmin)
POST /api/v1/schools
GET  /api/v1/schools/[id]/devices
POST /api/v1/schools/[id]/devices/[id]/command  (reboot, update)

GET  /api/v1/persons
POST /api/v1/persons
PUT  /api/v1/persons/[id]
POST /api/v1/persons/[id]/face

GET  /api/v1/access_logs?date=X&person_id=Y
GET  /api/v1/reports/daily
GET  /api/v1/reports/absent
```

Detaylar: [`06_WEB_PANEL_GUNCELLEMELERI.md`](06_WEB_PANEL_GUNCELLEMELERI.md)

---

## 🧭 SONUÇ

Bu mimari:
- ✅ **Çok okullu** — baştan multi-tenant tasarım
- ✅ **Offline-first** — internet olmadan da çalışır
- ✅ **Uzaktan yönetim** — fiziksel müdahale minimumda
- ✅ **Ölçeklenebilir** — 1 okuldan 500 okula aynı kod
- ✅ **Güvenli** — tenant izolasyonu + device auth
- ✅ **Maliyet etkin** — ilk aşamada ~400 TL/ay VPS yeterli