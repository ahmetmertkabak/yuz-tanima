# 📘 00 - Genel Bakış (Multi-Tenant SaaS)

## 🎯 Proje Vizyonu

Mevcut **RFID kartlı yemekhane bakiye sistemi**, MEB'in okullara getirdiği **yüz tanıma + turnike** zorunluluğuna uyumlu hale getirilecek ve **çok-okullu (multi-tenant) bir SaaS ürünü**ne dönüştürülecek.

Yani:
- Tek bir okul için değil, **birçok okula satılacak** bir sistem
- **Merkezi VPS sunucu** üzerinden tüm okullar yönetilecek
- Her okul kendi donanım paketini alacak (biz sağlıyoruz ve kuruyoruz)
- Her okulun kendi admin paneli olacak, verileri diğer okullardan **tamamen izole**

---

## 📋 Senaryo Özeti

| Parametre | Değer |
|---|---|
| **Ürün Tipi** | Multi-tenant SaaS (okullara satılan hazır paket) |
| **Hosting** | Merkezi VPS (tek sunucu, tüm okulları yönetir) |
| **Donanım Sağlayıcı** | **Biz** (hazır paket olarak montajlayıp göndereceğiz) |
| **Kurulum** | **Biz yapıyoruz** (sahada veya uzaktan destek) |
| **Pilot** | Tek okul, tek kapı (ana giriş) |
| **Kapı Başı Donanım** | Pi 4 + USB Webcam + Röle + Kablolama |
| **Kişi Sayısı (Okul başı)** | 300-1500 (öğrenci + öğretmen) |
| **Bakiye/Para İşlemi** | ❌ Kaldırılıyor |
| **Yoklama/Geçiş Kaydı** | ✅ Ana işlev |
| **Offline Çalışma** | ✅ İnternet kesilse bile tanıma + turnike çalışır, sonra sync olur |

---

## 👥 Kullanıcı Rolleri

### 1. Super Admin (Biz — Firma Sahibi)
- **Platform:** VPS üzerindeki özel panel
- **Yetkiler:**
  - Yeni okul (tenant) ekleme, düzenleme, deaktif etme
  - Her okula admin kullanıcı atama
  - Tüm okulların cihaz (Pi) durumunu izleme
  - Lisans/abonelik yönetimi
  - Uzaktan Pi güncelleme (OTA — Over The Air update)
  - Teknik destek için log/snapshot görüntüleme (KVKK uyumlu şekilde)
  - Faturalandırma / ödeme takibi

### 2. School Admin (Okul Müdürü / IT Sorumlusu)
- **Platform:** Okul subdomaini (ör. `okuladı.yuztanima.com`)
- **Yetkiler:**
  - Kendi okulunun öğrenci/öğretmenlerini yönetme
  - Yüz kayıt/güncelleme
  - Canlı geçiş izleme (dashboard)
  - Raporlar (günlük yoklama, gelmeyenler, geç kalanlar)
  - Kendi okulunun cihazlarının durumunu izleme
  - Kullanıcı (personel) yetkilendirme

### 3. Okul Personeli (Öğretmen / Sekreter)
- **Platform:** Aynı panel, kısıtlı yetki
- **Yetkiler:** Sadece raporları görüntüleme, öğrenci bilgilerini okuma (yazma yok)

---

## 🔄 Mevcut Sistemden Farklar

### ❌ Çıkarılacak Özellikler
- Bakiye yükleme/düşürme
- Para işlem geçmişi (Transaction)
- Aylık bakiye sıfırlama
- Yemek fiyatı / öğretmen özel fiyatı
- Toplu bakiye işlemleri
- Borç/ödeme takibi
- RFID kart okuyucu (MFRC522)

### ✅ Eklenecek Özellikler
- **Multi-tenant mimari** (okul = tenant)
- **Yüz tanıma ile giriş** (kamera + encoding)
- **Turnike kontrolü** (röle ile)
- **Giriş/çıkış yönü takibi** (in/out)
- **Cihaz yönetimi** (Pi'ları merkezden izle/kontrol et)
- **Canlı izleme paneli** (kim ne zaman girdi)
- **Snapshot kayıt** (tanınamayan yüzler için)
- **Offline-first sync** (Pi bağımsız çalışır, internet gelince sync olur)
- **Super Admin paneli** (tüm okulları yönet)
- **Subdomain sistemi** (her okula özel URL)
- **Lisans/abonelik** (ay/yıllık ücretlendirme)

### 🔄 Korunacak Özellikler
- Flask web paneli yapısı
- Öğrenci CRUD işlemleri (Person modeline dönüşüyor)
- Login/auth sistemi (multi-role eklenerek)
- Raporlama iskelet yapısı (Excel export vb.)
- Threading + queue mimarisi felsefesi (Pi tarafında)
- Flask-Migrate veri tabanı yönetimi

---

## 🏗️ Mimari Özeti (Detay için [`02_MIMARI.md`](02_MIMARI.md))

```
                  ┌──────────────────────────────────────┐
                  │   MERKEZİ VPS SUNUCU                 │
                  │   (yuztanima.com gibi)               │
                  │                                      │
                  │   - Super Admin Paneli               │
                  │   - Multi-tenant DB (PostgreSQL)     │
                  │   - REST API + WebSocket             │
                  │   - Okul subdomainleri yönetimi      │
                  │   - OTA update sunucusu              │
                  └───────────┬──────────────────────────┘
                              │ HTTPS
                              │
           ┌──────────────────┼──────────────────┬─────────────────┐
           │                  │                  │                 │
       ┌───▼────┐         ┌───▼────┐         ┌───▼────┐       ┌───▼────┐
       │ OKUL A │         │ OKUL B │         │ OKUL C │       │ OKUL N │
       │ Pi #1  │         │ Pi #1  │         │ Pi #1  │       │ Pi #1  │
       │ (giriş)│         │ (giriş)│         │ (giriş)│       │ (giriş)│
       └────────┘         └────────┘         │ Pi #2  │       └────────┘
                                             │ (arka) │
                                             └────────┘
```

---

## 🏗️ Temel Kararlar

### Karar 1: Merkezi VPS + Okul Başı Pi'lar
- **VPS:** Hetzner / DigitalOcean / Contabo (ilk etap ~200-400 TL/ay)
- Her okulun her kapısı için 1 Pi
- Pi'lar VPS'e `api_key` ile HTTPS üzerinden bağlanır
- Offline çalışabilir, internet gelince sync olur

### Karar 2: Donanım Paketi Hazır Satılacak
Okullar ne Pi bilgisi ne kamera kurulumu uğraşmayacak. Biz:
1. Paketi montajlıyoruz (Pi + kamera + röle + kablolar + kutu)
2. Yazılımı önceden flash'lıyoruz (plug-and-play)
3. Yerinde kuruluma gidiyoruz veya uzaktan kılavuzluk ediyoruz

### Karar 3: Tenant İzolasyonu = DB Seviyesinde
- PostgreSQL tek DB, her tabloda `school_id` kolonu (row-level izolasyon)
- Her query otomatik olarak `WHERE school_id = current_user.school_id` ile filtrelenir
- SuperAdmin hariç kimse cross-tenant veriye erişemez

### Karar 4: Pi Pi'dan Bağımsız = Offline-First
- Pi'da lokal SQLite cache var
- Yüz encoding'leri Pi'ya senkronize ediliyor
- İnternet kesilse bile Pi tanıma + turnike açma devam eder
- Geçiş logları lokalde birikir, bağlantı gelince VPS'e push edilir

### Karar 5: Subdomain Tabanlı Tenant
- Her okul: `okuladi.yuztanima.com` gibi özel URL
- Wildcard SSL (`*.yuztanima.com`) ile tek sertifika
- Flask middleware subdomain'e göre tenant'ı belirliyor

### Karar 6: OTA Güncelleme (Uzaktan Yazılım Güncelleme)
- Pi'lar gece belirli saatte VPS'e "güncelleme var mı?" diye sorar
- Yeni versiyon varsa indirir, kendini günceller
- **Okula fiziksel gitmeden** tüm Pi'lar güncellenebilir
- Bu OLMADAN 10+ okul yönetilemez!

---

## 🚦 Kullanıcı Deneyimi Akışı

### Öğrenci Perspektifinden
```
1. Öğrenci kapıya yaklaşır
2. Kamera yüzü yakalar (otomatik, dokunma yok)
3. Pi tanımayı yapar (okul encoding'leri içinden)
4. ✅ Tanıma başarılı → Röle → Turnike açılır → Log kaydı
5. ❌ Tanıma başarısız → Ekranda uyarı + snapshot
```

### Okul Admin Perspektifinden
```
1. Tarayıcıdan okuladi.yuztanima.com'a girer
2. Kullanıcı adı / şifre ile login
3. Dashboard'da bugün kim geldi kim gelmedi görür
4. Yeni öğrenci eklerken "Yüz Kaydet" butonuna basar
5. Webcam açılır → Fotoğraf çekilir → Encoding üretilir → Pi'lara sync olur
6. Aylık rapor almak için Raporlar > Excel Export
```

### Super Admin Perspektifinden (Biz)
```
1. admin.yuztanima.com panelinden giriş
2. Tüm okulları listele: Ali Paşa Lisesi, Mehmet Akif OO, ...
3. Yeni okul ekle: "Türk Telekom Lisesi" → Admin kullanıcısı ata
4. Cihaz durumu: "Ali Paşa Lisesi > Ana Giriş Pi — OFFLINE!" → müdahale
5. Tüm okullar için genel yazılım güncellemesi tetikle
```

---

## 📊 Başarı Kriterleri

| Metrik | Hedef |
|---|---|
| Tanıma süresi | < 1 saniye (yüz algılamadan turnike açılana kadar) |
| Tanıma doğruluğu | > %98 (doğru ışık koşullarında) |
| False positive oranı | < %0.5 (başkasının yerine geçme) |
| Sistem uptime (VPS) | > %99.5 |
| Pi uptime (okul saatlerinde) | > %99 |
| Offline çalışma süresi | 72+ saat kesintisiz |
| Okul kurulum süresi | < 2 saat (sahada) |
| Yeni okul ekleme süresi (yazılım) | < 5 dakika (panelden) |

---

## 📦 Satış Paketi (Özet — Detay [`11_IS_MODELI.md`](11_IS_MODELI.md))

### Bir Okul İçin Minimum Paket (1 Kapı)
- 1x Raspberry Pi 4 (4GB veya 8GB) + kasa + SD kart
- 1x USB Webcam (Logitech C270 veya C920)
- 1x 2 kanal röle modülü
- Kablolama + adaptör
- Ön-yüklü yazılım (plug-and-play)
- Yerinde kurulum + eğitim
- 1 yıl destek + yazılım güncellemesi

**Donanım maliyeti:** ~7000-10000 TL (kar hariç)  
**Satış fiyatı:** ~18000-25000 TL (1 kapı, 1 yıl destek dahil)  
**Yıllık yenileme (abonelik):** ~3000-5000 TL (VPS + destek + güncelleme)

### Ek Kapı (Aynı Okul)
- Kapı başı: ~5000-7000 TL ek

---

## 📚 Doküman Haritası

Bu `plan/` klasöründeki diğer dokümanlar:

- [`01_DONANIM_SECIMI.md`](01_DONANIM_SECIMI.md) — Donanım paketi içeriği, fiyatlar, toptan alım
- [`02_MIMARI.md`](02_MIMARI.md) — Multi-tenant mimari, VPS + Pi ilişkisi
- [`03_TURNIKE_ENTEGRASYONU.md`](03_TURNIKE_ENTEGRASYONU.md) — Kablolama, röle, fail-safe
- [`04_VERITABANI_DEGISIKLIKLERI.md`](04_VERITABANI_DEGISIKLIKLERI.md) — Multi-tenant schema
- [`05_YUZ_TANIMA.md`](05_YUZ_TANIMA.md) — Kütüphane, algoritma, encoding
- [`06_WEB_PANEL_GUNCELLEMELERI.md`](06_WEB_PANEL_GUNCELLEMELERI.md) — 3 tip panel (super/okul/personel)
- [`07_GUVENLIK_VE_KVKK.md`](07_GUVENLIK_VE_KVKK.md) — Multi-tenant izolasyon, KVKK
- [`08_GECIS_STRATEJISI.md`](08_GECIS_STRATEJISI.md) — Mevcut koddan yeni koda
- [`09_SURE_VE_MALIYET.md`](09_SURE_VE_MALIYET.md) — Geliştirme süresi + işletme maliyeti
- [`10_TODO_YOL_HARITASI.md`](10_TODO_YOL_HARITASI.md) — Adım adım yapılacaklar
- [`11_IS_MODELI.md`](11_IS_MODELI.md) — Paket, fiyat, destek, satış modeli