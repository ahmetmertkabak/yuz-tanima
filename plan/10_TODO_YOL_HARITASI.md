# 🗺️ 10 - TODO Yol Haritası (Adım Adım)

## 🎯 Bu Dosyanın Amacı

Proje başından pilot sonuna kadar **yapılacakların somut listesi**. Kod moduna geçtiğinde bu liste üzerinden ilerlenir. Her görev:
- ✅ Açıkça tanımlı
- ⏱️ Süre tahmini var
- 📋 Kabul kriteri var

---

## 📅 HAFTALAR HALİNDE YOL HARITASI

---

## 📆 HAFTA 0 — HAZIRLIK (1 Hafta)

### İş Tarafı
- [ ] **T0.1** Firma kuruluş süreci başlat (LTD veya şahıs)
  - Süre: 5-10 gün (paralel devam eder)
- [ ] **T0.2** KVKK avukatı ile ilk görüşme, DPA ve onay formu şablonu siparişi
  - Süre: 2 saat görüşme
- [ ] **T0.3** VPS satın al (Hetzner CPX21 veya benzeri)
  - Süre: 1 saat
- [ ] **T0.4** Domain al (`yuztanima.com` veya benzeri)
  - Cloudflare'e transfer et (wildcard DNS için)
  - Süre: 1 saat
- [ ] **T0.5** GitHub organizasyon + private repo kur
  - 2 repo: `face-recognition-server` + `face-recognition-edge`
  - Süre: 30 dakika

### Teknik Tarafı
- [ ] **T0.6** Mevcut projeyi `v2-multitenant` branch'ine fork et
  - Eski kodu `legacy/` altına taşı
  - Yeni klasör yapısını oluştur (bkz [`08_GECIS_STRATEJISI.md`](08_GECIS_STRATEJISI.md))
- [ ] **T0.7** VPS'e Ubuntu 22.04 kur, temel paketler (nginx, docker, certbot)
  - Süre: 4 saat
- [ ] **T0.8** GitHub Actions CI/CD pipeline
  - Push → lint + test → deploy
  - Süre: 1 gün
- [ ] **T0.9** Development environment setup (Dev container veya Docker Compose)
  - Süre: 1 gün

### Kabul Kriteri
- [ ] Firma kuruldu, vergi dairesi kaydı hazır
- [ ] KVKK sözleşme şablonları hukuk onaylı
- [ ] VPS SSH ile erişilebilir, Python 3.11 + PostgreSQL kurulu
- [ ] `https://dev.yuztanima.com` temel bir "Hello World" gösteriyor
- [ ] Git repo hazır, ilk commit atılmış

---

## 📆 HAFTA 1-2 — VERİ KATMANI

### Modeller
- [ ] **T1.1** `server/app/models/school.py` yaz
  - School modeli + index'ler
  - Unit test: CRUD
- [ ] **T1.2** `server/app/models/user.py` güncelle
  - Role + school_id kolonları ekle
  - Uniqueconstraint: (school_id, username)
- [ ] **T1.3** `server/app/models/person.py` yaz (Student'tan dönüşüm)
  - face_encoding, class_name, role, consent_given
- [ ] **T1.4** `server/app/models/device.py` yaz
  - api_key, heartbeat, firmware_version
- [ ] **T1.5** `server/app/models/access_log.py` yaz
  - direction, confidence, snapshot_path
- [ ] **T1.6** `server/app/models/snapshot.py` ve `audit_log.py` yaz

### Middleware ve Altyapı
- [ ] **T1.7** Tenant middleware yaz
  - `g.school_id` set etme
  - SQLAlchemy event listener ile auto-filter
  - Unit test: Farklı okul verisi erişim engeli
- [ ] **T1.8** PostgreSQL bağlantısı + Flask-Migrate kur
- [ ] **T1.9** Mevcut SQLite verilerini migrate eden script yaz
  - Legacy school oluştur
  - Student → Person, Attendance → AccessLog

### Kabul Kriteri
- [ ] Tüm modeller PostgreSQL'e migrate edildi
- [ ] Tenant middleware testleri %100 geçiyor
- [ ] Mevcut RFID verileri kaybetmeden yeni sisteme taşındı
- [ ] Model unit testleri %80+ coverage

---

## 📆 HAFTA 3-4 — SUPER ADMIN PANELİ

### Auth + Dashboard
- [ ] **T2.1** SuperAdmin login sayfası + 2FA
- [ ] **T2.2** SuperAdmin dashboard
  - Toplam okul, cihaz, geçiş sayıları
  - Online/offline cihaz listesi
- [ ] **T2.3** Subdomain middleware
  - `admin.yuztanima.com` → super admin panel
  - `[okul].yuztanima.com` → school admin panel

### Okul Yönetimi
- [ ] **T2.4** Okul listesi sayfası (tablo, filtre, arama)
- [ ] **T2.5** Yeni okul oluşturma formu
- [ ] **T2.6** Okul detay + düzenleme sayfası
- [ ] **T2.7** Okul oluşturulunca otomatik:
  - Subdomain DNS kaydı (Cloudflare API)
  - İlk school_admin kullanıcısı
  - Default ayarlar

### Cihaz Yönetimi
- [ ] **T2.8** Cihaz listesi (tüm okullar)
- [ ] **T2.9** Cihaz detay sayfası (heartbeat, son geçişler, komutlar)
- [ ] **T2.10** Uzaktan komut API'si (reboot, reload)

### SSL
- [ ] **T2.11** Let's Encrypt wildcard sertifika setup
  - DNS-01 challenge
  - Cron ile otomatik yenileme

### Kabul Kriteri
- [ ] Yeni okul ekleme 5 dakikanın altında tamamlanıyor
- [ ] SuperAdmin 2FA çalışıyor
- [ ] `*.yuztanima.com` wildcard SSL aktif
- [ ] Cihaz listesi canlı heartbeat gösteriyor

---

## 📆 HAFTA 5-7 — SCHOOL ADMIN PANELİ

### Dashboard + Canlı Feed
- [ ] **T3.1** School admin login (okul subdomain'inde)
- [ ] **T3.2** Dashboard (bugünkü giriş, gelmeyen, grafik)
- [ ] **T3.3** Socket.IO entegrasyonu
  - Geçiş olunca real-time ekranda görünür
  - Room: `school_{id}`

### Person (Öğrenci/Öğretmen) Yönetimi
- [ ] **T3.4** Kişi listesi (filtre, arama, sıralama)
- [ ] **T3.5** Kişi detay sayfası
- [ ] **T3.6** Yeni kişi oluşturma formu
- [ ] **T3.7** Excel toplu import (mevcut kodu uyarla)
- [ ] **T3.8** Toplu işlemler (aktif/pasif, sil)

### Raporlar
- [ ] **T3.9** Günlük yoklama raporu
- [ ] **T3.10** Gelmeyenler listesi (veli telefon içerir)
- [ ] **T3.11** Aylık özet rapor
- [ ] **T3.12** Geç kalanlar raporu (örn. 08:30 sonrası)
- [ ] **T3.13** Excel ve PDF export

### Kabul Kriteri
- [ ] 500 kişi sorunsuz listelenir (pagination)
- [ ] Excel import 500 öğrenciyi < 30 saniyede alır
- [ ] Raporlar Excel export sorunsuz
- [ ] Dashboard WebSocket canlı veri gösteriyor

---

## 📆 HAFTA 8 — YÜZ KAYDETME UI

- [ ] **T4.1** Yüz kayıt modal (JS + webcam)
  - getUserMedia API ile kamera erişimi
  - 3-5 frame otomatik capture
- [ ] **T4.2** Frame kalite kontrolü (frontend)
  - Yüz algılama (face-api.js ile client-side)
  - Bulanıklık, yüz sayısı, kadraj kontrolü
- [ ] **T4.3** Backend encoding endpoint
  - Frame'leri al
  - `face_recognition` ile encoding üret
  - Ortalama encoding DB'ye yaz
- [ ] **T4.4** "Yeniden çek" ve "Sil" işlevleri
- [ ] **T4.5** Yüz fotoğrafı S3/MinIO depolama

### Kabul Kriteri
- [ ] 1 öğrencinin yüzü 30 saniyede kaydediliyor
- [ ] Kalitesiz frame'ler reddediliyor (bulanık, 2 yüz vb.)
- [ ] Encoding DB'ye doğru formatta yazılıyor

---

## 📆 HAFTA 9-10 — API KATMANI

### Device API
- [ ] **T5.1** Device authentication (HMAC + timestamp)
- [ ] **T5.2** `POST /api/v1/device/heartbeat`
  - Son heartbeat, IP, CPU/RAM bilgisi
- [ ] **T5.3** `GET /api/v1/device/encodings?since=X`
  - Incremental sync (sadece değişenler)
- [ ] **T5.4** `POST /api/v1/device/access_log`
  - Tekli ve batch
- [ ] **T5.5** `POST /api/v1/device/snapshot` (multipart upload)
- [ ] **T5.6** `GET /api/v1/device/config`
  - Tolerance, pulse_ms vb.

### API Güvenlik
- [ ] **T5.7** Rate limiting (device başı 100 req/dk)
- [ ] **T5.8** Request signature doğrulama
- [ ] **T5.9** API versiyon desteği (v1, v2 hazırlık)

### Dokümantasyon
- [ ] **T5.10** Swagger/OpenAPI dokümanı
- [ ] **T5.11** Test client (Postman collection)

### Kabul Kriteri
- [ ] Yetkisiz istek 401 dönüyor
- [ ] Replay attack engelleniyor (timestamp expire)
- [ ] Sync endpoint 500 encoding'i 2 saniyede gönderiyor
- [ ] Swagger UI'dan tüm endpoint'ler test edilebiliyor

---

## 📆 HAFTA 11-13 — PI EDGE NODE

### Kamera + Yüz Tanıma
- [ ] **T6.1** USB webcam açma (OpenCV VideoCapture)
- [ ] **T6.2** Frame okuma thread'i (`_camera_loop`)
- [ ] **T6.3** `face_recognition` entegrasyonu
  - Haar cascade ile yüz algılama
  - Encoding üretme
- [ ] **T6.4** Lokal cache ile karşılaştırma
  - Numpy vectorized compare
  - Tolerance kontrolü

### Turnike + Çevre Birimleri
- [ ] **T6.5** Röle kontrolü (`turnstile.py`)
- [ ] **T6.6** LCD mesajları (mevcut kodu al)
- [ ] **T6.7** Buzzer sinyalleri (mevcut kodu al)

### Veri Tabanı + Sync
- [ ] **T6.8** Lokal SQLite şema + init
- [ ] **T6.9** Sync client (`sync_client.py`)
  - Heartbeat loop
  - Encoding sync loop
  - Log sync loop
- [ ] **T6.10** Retry mantığı (network hatası durumunda)
- [ ] **T6.11** Snapshot upload

### Sistem
- [ ] **T6.12** systemd service (boot'ta otomatik başlat)
- [ ] **T6.13** Logging (file + remote)
- [ ] **T6.14** Watchdog (çökerse auto-restart)

### Kabul Kriteri
- [ ] Pi boot'ta sistem otomatik başlıyor
- [ ] Kayıtlı yüz 1 saniyede tanınıyor
- [ ] Tanınmayan yüz için snapshot alınıyor
- [ ] İnternet kesilse bile çalışmaya devam ediyor
- [ ] İnternet gelince pending loglar senkronize oluyor

---

## 📆 HAFTA 14 — OTA UPDATE

- [ ] **T7.1** `update_manager.py` yaz
- [ ] **T7.2** Versiyon kontrol endpoint'i (server)
- [ ] **T7.3** Zip indirme + imza doğrulama
- [ ] **T7.4** Güvenli güncelleme (A/B partition gibi)
- [ ] **T7.5** Başarı/başarısızlık raporlama
- [ ] **T7.6** SuperAdmin panelden push kontrolü

### Kabul Kriteri
- [ ] Test okulda uzaktan güncelleme başarıyla yapıldı
- [ ] Güncellemeden önce yedek alınıyor
- [ ] Başarısız güncelleme sonrası rollback çalışıyor

---

## 📆 HAFTA 15-16 — GÜVENLİK + KVKK

### Teknik Güvenlik
- [ ] **T8.1** Biyometrik veri encryption at rest
- [ ] **T8.2** Audit log tüm kritik işlemlerde
- [ ] **T8.3** Rate limiting (tüm endpoint'ler)
- [ ] **T8.4** 2FA (SuperAdmin zorunlu, SchoolAdmin opsiyonel)
- [ ] **T8.5** Security headers (CSP, HSTS, X-Frame-Options)
- [ ] **T8.6** Fail2ban kurulum

### KVKK
- [ ] **T8.7** Gizlilik politikası sayfası
- [ ] **T8.8** Çerez politikası
- [ ] **T8.9** Kullanım koşulları
- [ ] **T8.10** "Verilerimi sil" endpoint (GDPR right to erasure)
- [ ] **T8.11** "Verilerimi indir" endpoint (data portability)
- [ ] **T8.12** Veli onay formu dijital upload
- [ ] **T8.13** Otomatik silme cron (30 gün snapshot'lar)
- [ ] **T8.14** VERBİS kaydı

### Kabul Kriteri
- [ ] Pen-test kritik bulgu yok
- [ ] KVKK avukatı tüm sayfaları onayladı
- [ ] DPA sözleşme şablonu hazır
- [ ] VERBİS kaydı tamamlandı

---

## 📆 HAFTA 17-18 — TEST + BUGFIX

### Otomatik Testler
- [ ] **T9.1** Unit test coverage > %70
- [ ] **T9.2** Integration test (tenant izolasyonu)
- [ ] **T9.3** E2E test (Selenium/Playwright)
- [ ] **T9.4** Load test (100 eşzamanlı kullanıcı)

### Manuel Testler
- [ ] **T9.5** 20+ farklı senaryo manuel test
- [ ] **T9.6** Mobile tarayıcı testi
- [ ] **T9.7** Hata mesajları + kullanıcı deneyimi

### Pen-Test
- [ ] **T9.8** Profesyonel pen-test firma ile anlaşma
- [ ] **T9.9** Bulgular için fix
- [ ] **T9.10** Re-test

### Kabul Kriteri
- [ ] Unit test CI'da her push'ta geçiyor
- [ ] Kritik bug yok
- [ ] Pen-test raporu "orta" ve üzeri bulgu yok

---

## 📆 HAFTA 19-20 — PİLOT KURULUM

### Okul Seçimi + Hazırlık
- [ ] **T10.1** Pilot okulu belirle (tercihen referans)
  - İdeal: Tanıdığın bir okul veya önceki yemekhane müşterisi
- [ ] **T10.2** Okul yönetimi ile sözleşme (DPA dahil)
- [ ] **T10.3** Velilere onay formu gönderimi
- [ ] **T10.4** %95+ onay beklenmesi

### Donanım
- [ ] **T10.5** Standart paket hazırla
- [ ] **T10.6** Pi'ya API key flash
- [ ] **T10.7** 24 saat tezgah testi

### Saha Kurulum (1 gün)
- [ ] **T10.8** Turnike kontrol kartı inceleme
- [ ] **T10.9** Pi + kamera + röle montaj
- [ ] **T10.10** Kablolama (kablo kanalı dahil)
- [ ] **T10.11** Yazılım test (10 kayıtlı kişi ile deneme)
- [ ] **T10.12** Kurulum fotoğrafları + dokümantasyon

### Yüz Kayıt
- [ ] **T10.13** Okul yönetimine eğitim (1 saat)
- [ ] **T10.14** İlk 50 öğrenci ile yüz kayıt pilotu
- [ ] **T10.15** 2-3 gün canlı test

### Kabul Kriteri
- [ ] Kurulum tek günde tamamlandı
- [ ] İlk 50 öğrenci sorunsuz kaydedildi
- [ ] Canlı test %95+ doğru tanıma
- [ ] Okul yönetimi paneli kullanmaya başladı

---

## 📆 HAFTA 21-22 — PİLOT İZLEME + İYİLEŞTİRME

### Canlı İzleme
- [ ] **T11.1** Günlük kontrol (ilk hafta)
- [ ] **T11.2** Haftalık check-in (okul admini ile)
- [ ] **T11.3** Sorun loglarını analiz
- [ ] **T11.4** Performans metrikleri kayıt

### İyileştirme
- [ ] **T11.5** Karşılaşılan bug'ları düzelt
- [ ] **T11.6** Tolerance ayarını iyileştir (ışık, mesafe)
- [ ] **T11.7** Ek 200-400 öğrenciyi sisteme ekle (aşamalı)
- [ ] **T11.8** UX feedback'leri uygula

### Ölçme
- [ ] **T11.9** Başarı metrikleri raporla:
  - Tanıma doğruluğu
  - False positive/negative
  - Ortalama tanıma süresi
  - Sistem uptime
  - Kullanıcı memnuniyeti

### Kabul Kriteri
- [ ] Pilot okul 2 hafta %99+ uptime ile çalıştı
- [ ] Tüm öğrenciler sisteme dahil edildi
- [ ] Okul yönetimi "satın alma" kararı verdi
- [ ] Referans verebilecek durum

---

## 📆 HAFTA 23+ — ROLLOUT AŞAMASI

### Satış Altyapısı
- [ ] **T12.1** Pazarlama web sitesi (landing page)
- [ ] **T12.2** Demo video (pilot okuldan görüntüler)
- [ ] **T12.3** Referans mektubu (pilot okuldan)
- [ ] **T12.4** Fiyat listesi + paket karşılaştırma
- [ ] **T12.5** Satış süreç dokümanı

### Operasyon Altyapısı
- [ ] **T12.6** Destek sistemi (helpdesk, ticket)
- [ ] **T12.7** Kurulum kılavuzu PDF
- [ ] **T12.8** Eğitim videoları
- [ ] **T12.9** SSS + bilgi tabanı

### Ölçeklendirme
- [ ] **T12.10** 2-3 okul daha kurulum (yavaş tempo)
- [ ] **T12.11** Süreç sorunlarını tespit et
- [ ] **T12.12** Akıcılaştır (donanım hazırlama, kurulum, eğitim)
- [ ] **T12.13** Hedef: 6. ayda 10 okul

---

## 🎯 ÖNCELİK ANAHTARI

Her görev yanındaki etiket:
- 🔴 **Kritik:** Bu olmadan bir sonraki yapılamaz
- 🟡 **Önemli:** Proje için gerekli ama paralel yapılabilir
- 🟢 **İyi Olur:** Sonraya bırakılabilir

**Öneri sırası:**

```
Hafta 0     → Hazırlık (Kritik)
Hafta 1-2   → Veri katmanı (Kritik)
Hafta 3-4   → Super admin (Kritik)
Hafta 5-7   → School admin (Kritik)
Hafta 8     → Yüz kayıt UI (Kritik)
Hafta 9-10  → API (Kritik)
Hafta 11-13 → Pi edge node (Kritik)
Hafta 14    → OTA (Önemli)
Hafta 15-16 → Güvenlik/KVKK (Kritik)
Hafta 17-18 → Test/pen-test (Kritik)
Hafta 19-20 → Pilot kurulum (Kritik)
Hafta 21-22 → Pilot izleme (Kritik)
```

---

## 📋 HIZLI BAŞLANGIÇ (İlk 5 Görev)

Code moduna geçince ilk yapılacaklar:

1. 🔴 **T0.6** — Yeni klasör yapısını oluştur, mevcut kodu `legacy/` altına taşı
2. 🔴 **T1.1-T1.6** — Tüm yeni modelleri yaz
3. 🔴 **T1.7** — Tenant middleware yaz + test et
4. 🔴 **T1.8-T1.9** — PostgreSQL bağlantısı + migration script
5. 🔴 **T2.1** — SuperAdmin login sayfası

Bu 5 görev ~2-3 haftada biter, sonra sırayla devam.

---

## 🔄 HAFTALIK RİTİM

Her hafta:
- **Pazartesi:** Bu haftanın görevlerini planla
- **Çarşamba:** Ara değerlendirme, engel kontrolü
- **Cuma:** Haftalık demo (kendine veya ekibe)
- **Cuma sonu:** Gelecek haftanın planı

Her 2 haftada bir **retrospektif** (ne iyi gitti, ne kötü, ne öğrendim).

---

## ✅ TAMAM OLUNCA SIRADAKİ DOKÜMAN

Son bir doküman kaldı: [`11_IS_MODELI.md`](11_IS_MODELI.md) — Paket içeriği, fiyatlandırma, satış stratejisi. Sonra Code moduna geçip kod yazmaya başlayabilirsin.