# 🔄 08 - Geçiş Stratejisi (Mevcut Koddan Yeni Sisteme)

## 🎯 Felsefe: Sıfırdan Yazmıyoruz

Mevcut kod **çöpe gitmeyecek**. Yaklaşık **%40'ı direkt kullanılacak**, **%30'u dönüştürülecek**, **%30'u silinecek**. Rewrite yerine **aşamalı refactoring** yaklaşımını öneriyorum.

---

## 📁 YENİ PROJE YAPISI

Multi-tenant SaaS için yeniden organize edilmiş klasör yapısı:

```
kart-okuma-sistemi/  (eski isim, sonra "yuz-tanima-sistemi" olur)
│
├── server/                        # 🆕 Merkezi VPS uygulaması
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── school.py          # 🆕 Tenant
│   │   │   ├── user.py            # 🔄 Genişletildi (multi-role)
│   │   │   ├── person.py          # 🔄 Student'tan dönüştü
│   │   │   ├── device.py          # 🆕 Pi cihazları
│   │   │   ├── access_log.py      # 🔄 Attendance'tan dönüştü
│   │   │   ├── snapshot.py        # 🆕
│   │   │   └── audit_log.py       # 🆕
│   │   │
│   │   ├── middleware/
│   │   │   ├── tenant.py          # 🆕 Otomatik school_id filter
│   │   │   ├── auth.py            # 🔄 Genişletildi (role-based)
│   │   │   └── rate_limit.py      # 🆕
│   │   │
│   │   ├── routes/
│   │   │   ├── super_admin/       # 🆕 admin.yuztanima.com
│   │   │   │   ├── schools.py
│   │   │   │   ├── devices.py
│   │   │   │   ├── billing.py
│   │   │   │   └── updates.py
│   │   │   │
│   │   │   ├── school_admin/      # 🆕 okul subdomain
│   │   │   │   ├── dashboard.py   # 🔄 Mevcuttan uyarlanacak
│   │   │   │   ├── persons.py     # 🔄 Student routes'tan dönüşüm
│   │   │   │   ├── access_logs.py # 🆕
│   │   │   │   ├── reports.py     # 🔄 Mevcut raporlar
│   │   │   │   └── devices.py     # 🆕 Salt okunur
│   │   │   │
│   │   │   ├── api/               # 🆕 Pi'lar için
│   │   │   │   ├── v1/
│   │   │   │   │   ├── device.py     # heartbeat, sync
│   │   │   │   │   ├── encodings.py  # encoding sync
│   │   │   │   │   └── access_log.py # log gönderme
│   │   │   │
│   │   │   └── auth.py            # 🔄 Mevcut login
│   │   │
│   │   ├── services/              # 🆕 Business logic ayrı
│   │   │   ├── face_service.py
│   │   │   ├── sync_service.py
│   │   │   ├── report_service.py
│   │   │   └── notification_service.py
│   │   │
│   │   ├── templates/
│   │   │   ├── super_admin/       # 🆕
│   │   │   ├── school_admin/      # 🔄 Mevcut template'ler uyarlanacak
│   │   │   ├── emails/            # 🆕 Email şablonları
│   │   │   └── shared/
│   │   │
│   │   └── static/
│   │
│   ├── migrations/                # 🔄 Flask-Migrate (genişletilecek)
│   ├── tests/                     # 🆕 Pytest
│   ├── celery_app.py              # 🆕 Background tasks
│   ├── requirements.txt
│   └── run.py
│
├── edge/                          # 🆕 Pi yazılımı (ayrı repo olabilir)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py              # device_id, api_key, vpsurl
│   │   ├── hardware.py            # 🔄 Mevcut hardware.py'den dönüştürüldü
│   │   ├── camera.py              # 🆕 USB webcam wrapper
│   │   ├── recognition/
│   │   │   ├── base.py            # 🆕 Abstract
│   │   │   ├── dlib_recognizer.py # 🆕 Faz 1
│   │   │   └── insightface_recognizer.py  # 🆕 Faz 2
│   │   │
│   │   ├── turnstile.py           # 🆕 Röle kontrolü
│   │   ├── display.py             # 🔄 LCD mesajları
│   │   ├── buzzer.py              # 🔄 Ses
│   │   ├── local_db.py            # 🆕 SQLite cache
│   │   ├── sync_client.py         # 🆕 VPS iletişim
│   │   ├── update_manager.py      # 🆕 OTA updates
│   │   └── main.py                # Orchestration
│   │
│   ├── scripts/
│   │   ├── install.sh             # 🆕 İlk kurulum script
│   │   ├── provision.sh           # 🆕 Device registration
│   │   └── update.sh              # 🆕 OTA update executor
│   │
│   ├── systemd/
│   │   └── face-recognition.service  # 🆕 Systemd service
│   │
│   ├── requirements.txt
│   └── main.py                    # Entry point
│
├── docs/                          # 🆕 Dokümantasyon
│   ├── deployment.md
│   ├── api.md
│   └── troubleshooting.md
│
├── plan/                          # 🆕 (ZATEN MEVCUT) Bu planlama dokümanları
│
├── legacy/                        # 🗑️ Eski kod (geçiş süresi için)
│   ├── app/
│   ├── migrations/
│   └── ...
│
├── docker-compose.yml             # 🔄 Güncelleniyor (VPS için)
├── Dockerfile.server              # 🆕
├── Dockerfile.edge                # 🆕 Pi image
├── nginx.conf                     # 🔄 Subdomain routing
└── README.md                      # 🔄
```

---

## 🗑️ SİLİNECEK KOD (Açıkça)

### Dosyalar
- [`app/route.py`](app/route.py) — duplicate dosya
- [`app/templates/hardware.py`](app/templates/hardware.py) — yanlış yerdeki dosya
- [`create_admin.py`](create_admin.py) — SuperAdmin paneli üzerinden yapılacak

### [`app/models.py`](app/models.py)'den silinecek
- `Transaction` modeli tamamen
- `MEAL_PRICE`, `TEACHER_MEAL_PRICE` sabitleri
- `Student.balance` kolonu
- `Student.add_balance()`, `deduct_balance()`, `get_total_unpaid()` metodları
- `Attendance.mark_as_paid()` ve `paid`, `payment_date` kolonları

### [`app/routes.py`](app/routes.py)'den silinecek
- Bakiye yükleme/düşürme route'ları
- Toplu bakiye işlem route'ları
- Fiyat bilgisi gösteren route'lar
- Öğretmen özel fiyatlandırma mantığı

### [`app/hardware.py`](app/hardware.py)'den silinecek
- MFRC522 kart okuma mantığı (`_rfid_reader_loop`)
- `SimpleMFRC522` import ve kullanımları
- RFID-spesifik error handling

### Tüm Bakiye Logic'i
- Aylık bakiye sıfırlama scheduler
- Borç hesaplama
- Transaction ile ilgili her şey

---

## 🔄 DÖNÜŞTÜRÜLECEK KOD

### [`app/__init__.py`](app/__init__.py)
**Mevcut:** Basit Flask app factory  
**Yeni:** 
- Subdomain routing middleware
- Multi-tenant context
- Super admin + school admin ayrımı
- Socket.IO entegrasyonu
- Celery background task setup

```python
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    celery.init_app(app)
    
    # Middleware
    app.before_request(set_tenant_context)
    
    # Blueprints
    from app.routes.super_admin import bp as super_admin_bp
    from app.routes.school_admin import bp as school_admin_bp
    from app.routes.api.v1 import bp as api_v1_bp
    
    app.register_blueprint(super_admin_bp, url_prefix='/super')
    app.register_blueprint(school_admin_bp)
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    
    return app
```

### [`app/models.py`](app/models.py)
**Mevcut:** Tek dosya, 4 model  
**Yeni:** `models/` klasörü, 7+ model, her biri kendi dosyasında

Dönüşüm:
- `Student` → `Person` (adın yanı sıra rol, sınıf, face_encoding eklenir)
- `Attendance` → `AccessLog` (daha zengin alanlar)
- `User` genişletildi (role, school_id)
- `Transaction` silinir
- Yeni: `School`, `Device`, `Snapshot`, `AuditLog`

### [`app/hardware.py`](app/hardware.py)
**Mevcut:** 448 satır, RFID + threading + LCD + buzzer + DB  
**Yeni:** `edge/` klasörüne taşınır ve parçalanır:

| Eski (hardware.py bölümü) | Yeni dosya |
|---|---|
| `_rfid_reader_loop` (silinir) | - |
| `_card_processor_loop` | `edge/app/recognition/` |
| `_db_processor_loop` | `edge/app/main.py` orchestration |
| LCD methodları | `edge/app/display.py` |
| Buzzer methodları | `edge/app/buzzer.py` |
| GPIO setup | `edge/app/turnstile.py` |

### [`app/routes.py`](app/routes.py) (1400+ satır!)
**Mevcut:** Tek dosya, her şey karışık  
**Yeni:** Blueprint'lere bölünür

Route grupları:
- Auth routes → `routes/auth.py`
- Student (Person) routes → `routes/school_admin/persons.py`
- Report routes → `routes/school_admin/reports.py`
- Dashboard → `routes/school_admin/dashboard.py`
- (Bakiye route'ları silinir)

### Template Dosyaları
| Eski | Yeni |
|---|---|
| [`base.html`](app/templates/base.html) | `shared/base.html` + `school_admin/base.html` + `super_admin/base.html` |
| [`dashboard.html`](app/templates/dashboard.html) | `school_admin/dashboard.html` (bakiye bölümü çıkar, canlı feed girer) |
| [`student_detail.html`](app/templates/student_detail.html) | `school_admin/person_detail.html` |
| [`reports.html`](app/templates/reports.html) | `school_admin/reports/index.html` |
| [`daily_report.html`](app/templates/daily_report.html) | `school_admin/reports/daily.html` |
| [`monthly_report.html`](app/templates/monthly_report.html) | `school_admin/reports/monthly.html` |
| [`login.html`](app/templates/login.html) | `shared/auth/login.html` (aynen) |

---

## 📅 GEÇİŞ AŞAMALARI (Adım Adım)

### Aşama 0: Hazırlık (1 hafta)
- [x] Bu planlama dokümanları ✅
- [ ] Git branch stratejisi: `main` = eski sistem, `v2-multitenant` = yeni
- [ ] Yeni klasör yapısı oluşturma
- [ ] Eski kodu `legacy/` altına taşıma
- [ ] `requirements.txt` güncelleme
- [ ] CI/CD pipeline (GitHub Actions) kurma

### Aşama 1: Veri Katmanı (1-2 hafta)
- [ ] Yeni modelleri yaz (`server/app/models/`)
- [ ] PostgreSQL'e geç (SQLite yerine)
- [ ] Migration scriptleri
- [ ] Tenant middleware
- [ ] Model unit test'leri

**Kritik:** Mevcut veri kaybolmasın. Migration script'i mevcut SQLite'tan okuyup PostgreSQL'e aktaracak.

### Aşama 2: Super Admin Paneli (2 hafta)
- [ ] Super admin auth + login
- [ ] Okul listesi + ekleme formu
- [ ] Cihaz listesi + heartbeat izleme
- [ ] Subdomain wildcard DNS setup (Cloudflare API)
- [ ] SSL (Let's Encrypt wildcard)
- [ ] Dashboard + istatistikler

### Aşama 3: School Admin Paneli (2-3 hafta)
- [ ] Person CRUD (Student'tan uyarlama)
- [ ] Dashboard canlı feed (WebSocket)
- [ ] Access log sayfası
- [ ] Raporlar (günlük, aylık, gelmeyenler)
- [ ] Yüz kaydetme modal (webcam + encoding üretimi)
- [ ] Excel export
- [ ] Kullanıcı yönetimi (okul içi)

### Aşama 4: API (1-2 hafta)
- [ ] Device auth (api_key + HMAC)
- [ ] Heartbeat endpoint
- [ ] Encoding sync endpoint
- [ ] Access log submit endpoint
- [ ] Snapshot upload
- [ ] API dokümantasyonu (Swagger)

### Aşama 5: Pi Edge Node (2-3 hafta)
- [ ] Kamera entegrasyonu (OpenCV)
- [ ] Yüz algılama + tanıma (`face_recognition`)
- [ ] Röle kontrolü + turnike
- [ ] Lokal SQLite cache
- [ ] Sync client
- [ ] OTA update manager
- [ ] Systemd service
- [ ] Provisioning script
- [ ] Master SD image hazırlama

### Aşama 6: Güvenlik + KVKK (1-2 hafta)
- [ ] Encryption at rest (biyometrik veri)
- [ ] Audit log
- [ ] Veli onay modülü
- [ ] Verilerimi sil / indir endpoint'leri
- [ ] KVKK gizlilik politikası sayfaları
- [ ] DPA şablonu (hukuk onayı)
- [ ] Rate limiting
- [ ] 2FA (SuperAdmin için)
- [ ] Pen-test hazırlığı

### Aşama 7: Pilot Kurulum (1-2 hafta)
- [ ] İlk okul seçimi
- [ ] Donanım hazırlığı (1 Pi paketi)
- [ ] Sahada kurulum + turnike entegrasyonu
- [ ] Velilere onay formu gönderimi
- [ ] 50-100 kişi ile başlangıç
- [ ] 2 hafta canlı test
- [ ] Sorunları düzeltme

### Aşama 8: Rollout (sürekli)
- [ ] 2. okul
- [ ] 5. okul
- [ ] Pazarlama materyalleri
- [ ] Satış süreci dokümantasyonu
- [ ] Destek sistemi kurma

---

## 🔀 PARALEL ÇALIŞMA STRATEJİSİ

Mevcut sistem (yemekhane RFID) pilot müşterinizde çalışmaya devam edebilir. Yeni sistem ayrı olarak geliştirilir:

```
mert@rpi:~ $ git branch
  main                      # Mevcut RFID sistem, production
* v2-multitenant            # Yeni sistem, development
  feature/face-recognition
  feature/super-admin-panel
```

Yeni okullara satış yaparken `v2-multitenant` kullanılır, eski müşteri `main`'de kalır.

Sonunda eski sistem sonlandırılır (EOL) — 6 ay önceden duyurulur.

---

## 📊 KOD BAZINDA ÖZET

### Mevcut kod satır sayısı (yaklaşık)
- `models.py`: 96 satır
- `hardware.py`: 448 satır
- `routes.py`: 1400+ satır
- Templates: ~2000 satır HTML
- **Toplam:** ~4000 satır

### Tahmini yeni kod satır sayısı
- Server (models + routes + services): ~5000 satır
- Edge (Pi yazılımı): ~2000 satır
- Templates: ~3500 satır HTML
- Tests: ~2000 satır
- **Toplam:** ~12.500 satır (3x artış)

**Neden 3 kat?**
- Multi-tenant middleware + güvenlik
- 3 ayrı panel (super admin, school admin, staff)
- API katmanı
- Yüz tanıma entegrasyonu
- Sync mekanizmaları
- Testler

---

## 🧪 TEST STRATEJİSİ

### Mevcut: Test yok ❌
### Yeni: Otomatik test zorunlu ✅

- **Unit tests:** Model, service fonksiyonları
- **Integration tests:** API endpoint'leri
- **Tenant isolation tests:** Okul A'nın verisine Okul B erişemiyor doğrulama
- **E2E tests:** Selenium/Playwright ile panel testi
- **Hardware tests:** Pi üzerinde mock ile

CI/CD her push'ta çalıştırır, hata varsa merge engellenir.

---

## 🔒 RISK YÖNETİMİ

| Risk | Olasılık | Etki | Azaltma |
|---|---|---|---|
| Veri kaybı (migration) | Düşük | Yüksek | Her adımdan önce yedek, staging env'de test |
| Tenant sızıntısı (kod hatası) | Orta | Çok Yüksek | Otomatik izolasyon testleri |
| KVKK ihlali | Düşük | Çok Yüksek | Avukat danışmanlığı, pen-test |
| Pi çalınması | Düşük | Orta | api_key iptal, şifreli disk |
| VPS çökmesi | Düşük | Yüksek | Yedekler, failover planı |
| Yanlış tanıma (güvenlik) | Orta | Yüksek | Tolerance ayarı, hybrid mod |

---

## 🎯 BAŞARI METRİKLERİ (Geçiş Sonrası)

- [ ] Mevcut tüm öğrenci verisi yeni sisteme aktarıldı (kayıp yok)
- [ ] Eski sistem ile yeni sistem 2 hafta paralel çalışabildi
- [ ] İlk pilot okul 1 ay sorunsuz kullandı
- [ ] Tenant izolasyon testleri %100 geçti
- [ ] KVKK uyum checklist %100
- [ ] Kod coverage > %70
- [ ] Pen-test kritik bulgu yok

---

## 🏁 SONUÇ

Mevcut kod **çok değerli** çünkü:
- İş mantığı (raporlama, öğrenci yönetimi) test edilmiş
- UI/UX zaten kullanıcı tarafından onaylanmış
- Threading mimarisi sağlam

Yaklaşımımız:
1. **Silinecekleri sil** (temizlik)
2. **Genişletilecekleri genişlet** (multi-tenant)
3. **Eksikleri ekle** (yüz tanıma, API, sync)
4. **Bir kerede değil, aşamalı geç**
5. **Her aşamada çalışan sistem bırak**

Tahmini toplam süre: [`09_SURE_VE_MALIYET.md`](09_SURE_VE_MALIYET.md)'de.