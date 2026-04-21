# 🔧 01 - Donanım Seçimi ve Paket İçeriği (Multi-Okul SaaS)

## 🎯 Felsefe: Hazır Paket (Plug-and-Play)

Okul müdürü Pi nedir bilmeyecek. Bizim göndereceğimiz **kutu + kablo + kurulum kılavuzu** ile sistem çalışır hale gelecek. Bu nedenle **standart bir donanım paketi** tanımlanmalı.

Neden standart paket?
- Stok yönetimi kolay (10 okul = 10 aynı paket)
- Saha desteği kolay (her Pi aynı, soruna aynı şekilde bakılır)
- Yazılım tek image ile hepsine uyar
- Yedek parça yönetimi kolay

---

## 📦 STANDART "OKUL GİRİŞ PAKETİ" (1 Kapı İçin)

| # | Bileşen | Model | Adet | Birim Maliyet | Durum |
|---|---|---|---|---|---|
| 1 | Raspberry Pi 4 (4GB) | Resmi | 1 | 4500-5500 TL | ✅ Temel |
| 2 | Pi 4 Resmi Kasa + Fan | Argon NEO / Resmi | 1 | 250-400 TL | ✅ Temel |
| 3 | microSD 64GB A2 | SanDisk Extreme | 1 | 350-500 TL | ✅ Temel |
| 4 | Pi 4 Resmi Güç Adaptörü | 5V 3A USB-C | 1 | 250-350 TL | ✅ Temel |
| 5 | USB Webcam | Logitech C920 | 1 | 1300-1800 TL | ✅ Temel |
| 6 | 2 Kanal Röle Modülü | Optocoupler izolasyonlu | 1 | 100-150 TL | ✅ Temel |
| 7 | Jumper Kablo Seti | F-F + M-F 20cm | 1 | 30 TL | ✅ Temel |
| 8 | USB Uzatma Kablosu (2m) | Aktif/pasif | 1 | 80-150 TL | ✅ Temel |
| 9 | Kamera Montaj Bracketı | Duvar/turnike üstü | 1 | 100-200 TL | ✅ Temel |
| 10 | Mini UPS HAT | Waveshare / X728 | 1 | 600-900 TL | ⚙️ Tavsiye |
| 11 | Ethernet kablosu (5m) | Cat6 | 1 | 50-100 TL | ⚙️ Tavsiye |
| 12 | Korumalı özel kutu | Metal/plastik IP54 | 1 | 400-800 TL | ⚙️ Tavsiye |
| 13 | Yedek SD kart (flash'lı) | 64GB A2 | 1 | 350-500 TL | ⚙️ Tavsiye |

### Maliyet Özeti

| Paket Seviyesi | İçerik | Toplam Maliyet | Satış Önerisi |
|---|---|---|---|
| **Ekonomik (Temel)** | Madde 1-9 | **~7000-9000 TL** | ~15.000-18.000 TL |
| **Standart (Tavsiye)** | Temel + 10, 11 | **~7800-10000 TL** | ~18.000-22.000 TL |
| **Premium** | Hepsi | **~9000-11500 TL** | ~25.000-30.000 TL |

> Fiyatlar 2025-2026 için tahminidir. Toptan alımlarda %15-25 indirim mümkün.

---

## 📷 KAMERA SEÇİMİ

### Neden USB Webcam?
- ✋ Pi Camera v3 stok sıkıntılı, tedariki belirsiz
- USB webcam her yerde bulunur
- Uzatma kablosu ile 2-10m mesafe sorunsuz
- Standart driver, uyumluluk problemi yok

### Önerilen: Logitech C920 🏆
- **Fiyat:** 1300-1800 TL (toptan ~1100 TL)
- **Çözünürlük:** 1080p @ 30fps
- **Autofocus:** Var (yakın mesafe önemli)
- **Düşük ışık performansı:** İyi
- **USB 2.0 compatible:** Pi 4'te sorunsuz
- **Neden bu model:** Pazarda en yaygın, kalite/fiyat oranı en iyi, driver stabilite en iyi

### Alternatifler

| Model | Fiyat | Avantaj | Dezavantaj |
|---|---|---|---|
| Logitech C270 | 500-800 TL | Çok ucuz | 720p, düşük ışıkta zayıf |
| Logitech C922 Pro | 2000-2800 TL | Daha iyi düşük ışık | Fazla pahalı, gerekmez |
| Dahua/Hikvision IP Kam | 1500-3000 TL | Uzak mesafe (Ethernet) | Karmaşık kurulum, RTSP parse |
| Çin markası USB webcam | 200-500 TL | Ucuz | ❌ Driver sorunları, güvenilmez |

**Karar:** **Logitech C920** standart paketimizde olacak. Çin marka ile risk almayacağız (saha desteği maliyeti fiyat farkını siler).

### Kamera Montajı
- **Yükseklik:** 150-170 cm (yetişkin göz hizası)
- **Açı:** Yere paralel, hafifçe aşağı (~10°)
- **Mesafe:** Kullanıcı kameradan 50-120 cm
- **Işık:** Arkadan güneş GELMEMELİ (backlight)
- **Kablo:** Pi'den kameraya max 5m (USB 2.0 limit), 5m+ için aktif USB extender

---

## 🔌 RÖLE MODÜLÜ

### Seçim: **2 Kanal 5V Optocoupler İzolasyonlu Röle**

### Özellikleri
- ✅ Optocoupler izolasyonlu (Pi'yi korur)
- ✅ 5V coil (Pi'den direkt beslenebilir)
- ✅ Low-level trigger (GPIO LOW → röle ON)
- ✅ Kontak: 10A 250V AC / 10A 30V DC
- ✅ 2 kanal (1. aç, 2. yedek/alarm)

### Arama Anahtar Kelimeleri
- "2 channel 5V relay module optocoupler"
- "2 kanal röle modülü opto izolasyonlu"

### Nerden Alınır
- **Direnc.net** — güvenilir, teknik spec belirtilir
- **Robotistan.com** — hızlı kargo, eğitim dökümanları var
- **Hepsiburada / Trendyol** — hızlı ama marka kontrol edilmeli

### Fiyat
- Perakende: 100-150 TL
- Toptan (10+ adet): 70-90 TL

---

## 💾 microSD KART

### Seçim: **SanDisk Extreme 64GB A2 Class 10** 🏆

### Neden Marka Önemli?
Pi'de SD kart sürekli okuma/yazma yapar (log, encoding, DB). **Ucuz SD kartlar 3-6 ayda bozulur**, sistem çöker, saha desteği maliyeti büyük. Güvenilir marka ile bu risk çok düşer.

### Neden A2?
- **A1:** Random IOPS 1500/500 (sadece iyi)
- **A2:** Random IOPS 4000/2000 (Pi performansı +%30)

### Fiyat
- Perakende: 350-500 TL
- Toptan (10+ adet): 280-400 TL

### Alternatifler
- Samsung EVO Plus 64GB A2
- Kingston Canvas Go! Plus 64GB A2
- ❌ Kaspersky, XPG gibi az bilinen — tavsiye etmem

---

## ⚡ GÜÇ ADAPTÖRÜ

### Seçim: **Raspberry Pi 4 Resmi Güç Adaptörü (5.1V 3A USB-C)**

### Neden Resmi?
- Pi 4 yetersiz adaptörde "undervoltage warning" verir, sistem yavaşlar
- Ucuz adaptörler voltaj dalgalanması yapar, SD karta zarar verir
- Resmi adaptör Pi 4 için özel optimize edilmiş

### Fiyat: 250-350 TL

### Alternatif
- Anker 30W USB-C Charger (PD destekli) — Pi 4'e uyar
- ❌ Ucuz Çin adaptörü kullanma

---

## 🔋 MİNİ UPS HAT (Tavsiye Edilen)

### Neden UPS?
Okulda elektrik kesintisi yaygın. UPS HAT ile:
- Kesintide sistem 20-60 dakika çalışmaya devam eder
- SD kart bozulma riski ortadan kalkar
- Pi güvenli shutdown yapar (corruption yok)

### Seçenek 1: Waveshare UPS HAT (B)
- **Fiyat:** 700-900 TL
- **Çalışma süresi:** ~30 dakika
- **Pil:** 2x 18650 Li-Ion (değiştirilebilir)

### Seçenek 2: X728 Uninterruptible Power Supply
- **Fiyat:** 600-800 TL
- **Çalışma süresi:** ~40 dakika
- **Ekstra:** Auto power-on, safe shutdown yazılımı

### Seçenek 3: PiSugar 3
- **Fiyat:** 800-1100 TL
- Daha şık, daha profesyonel

### Karar
**Standart paketle satılsın.** Pilot aşamada opsiyonel, sonraki okullarda standart olmalı. Saha destek maliyetini ciddi düşürür.

---

## 📦 KORUMA KUTUSU (Tavsiye Edilen)

Pi turnikenin yanında bir yere monte edilecek. Açık durması:
- Toz, nem toplar
- Vandalizm riski
- Kablo karışıklığı

### Seçenekler
- **IP54 metal kutu** (300-500 TL) — profesyonel görünüm
- **Plastik elektrik kutusu** (150-300 TL) — ekonomik ama yeterli
- **3D printed özel tasarım** — ileride özelleştirme için

### Kutu İçeriği
- Pi + UPS HAT + Röle + kabloları düzenli şekilde
- Yazılım flash'lanmış, kilit takılabilir
- Okulun logosu/numarası etiket

---

## 🔌 KABLOLAMA STANDARTLARI

### Pi → Röle
```
Pi Pin 2 (5V)   ────► Röle VCC
Pi Pin 6 (GND)  ────► Röle GND
Pi GPIO 17      ────► Röle IN1 (Turnike aç)
Pi GPIO 27      ────► Röle IN2 (Yedek)
```

### Röle → Turnike
```
Röle Kanal 1:
    COM   ──┐
             ├──► Turnike "Free Pass" input
    NO    ──┘

(Açıklama: Normal durumda açık, röle tetiklenince COM ve NO 
birleşir → turnike açılır)
```

Detaylı kablolama şeması: [`03_TURNIKE_ENTEGRASYONU.md`](03_TURNIKE_ENTEGRASYONU.md)

---

## 📊 TOPTAN ALIM PLANI

### İlk 5 Okul için Stok (5 kapı varsayımı)

| Kalem | Adet | Birim | Toplam |
|---|---|---|---|
| Raspberry Pi 4 (4GB) | 6 (1 yedek) | 4800 TL | 28.800 TL |
| microSD 64GB A2 | 10 (yedekli) | 400 TL | 4.000 TL |
| Logitech C920 | 6 | 1500 TL | 9.000 TL |
| 2 kanal röle | 10 | 100 TL | 1.000 TL |
| UPS HAT | 5 | 800 TL | 4.000 TL |
| Kasa + fan | 6 | 350 TL | 2.100 TL |
| Güç adaptörü | 6 | 300 TL | 1.800 TL |
| USB extender 2m | 5 | 120 TL | 600 TL |
| Kablo + bracket + kutu | 5 | 800 TL | 4.000 TL |
| **İlk Stok Yatırımı** | | | **~55.000 TL** |

Bu stokla 5 okul rahatça kurulur + ek yedek olur.

---

## 🛒 TEDARIKÇİ ÖNERİLERİ

| Kategori | Kaynak | Notlar |
|---|---|---|
| Pi + resmi aksesuar | **Robotistan.com** | Türkiye resmi Pi distribütörü, fatura verir |
| Pi + aksesuar | **Samm Market** | Alternatif, hızlı kargo |
| Röle + modüller | **Direnc.net** | En güvenilir elektronik |
| Kamera (toptan) | Hepsiburada Kurumsal | Logitech orjinal |
| Kablo, jumper | **Robotistan**, **Çakmaktaş** | Hobbi siteleri |
| Metal kutu | Pazarlama uzmanı elektrik mağazaları | Bölgesel |

---

## 🛠️ ÖN-HAZIRLIK SÜRECI (Her Paket İçin)

Yeni okul satıldığında paketi göndermeden önce:

1. ✅ SD karta **master image** flash'lanır (Pi zaten çalışır halde)
2. ✅ Pi'ya **unique device_id + api_key** atanır (VPS panelinden üretilir)
3. ✅ İlk boot'ta Pi otomatik VPS'e kayıt olur
4. ✅ Test: 1 saat deneme (yüz tanıma + röle + sync)
5. ✅ Kutuya paketleme: Pi + kablo + kamera + kurulum kılavuzu (PDF)
6. ✅ Kargo veya yerinde kurulum

Detaylı provisioning süreci: [`10_TODO_YOL_HARITASI.md`](10_TODO_YOL_HARITASI.md)

---

## 📋 KURULUM KİTİ (Sahada Biz Götüreceğiz)

Sahada kurulum yaparken yanımızda olması gerekenler:
- Dizüstü bilgisayar (test için)
- Multimetre (turnike kontrol kartı voltajları)
- Tornavida seti (turnike panel açma)
- İzole bant, kablo bağı
- Yedek Pi + kamera (sorun çıkarsa)
- Fotoğraflı kurulum kılavuzu (adım adım)

---

## 💰 MALIYET ÖZETI

| Senaryo | Kapı Başı Maliyet | Satış Fiyatı | Brüt Kar |
|---|---|---|---|
| Ekonomik paket | ~7000 TL | ~15.000 TL | ~8.000 TL |
| Standart paket | ~9000 TL | ~20.000 TL | ~11.000 TL |
| Premium paket | ~11.000 TL | ~28.000 TL | ~17.000 TL |

> Yukarıdaki fiyatlara **yerinde kurulum + 1 yıl destek** dahildir.

Yıllık abonelik (yenileme): 3.000-5.000 TL (VPS + destek + güncelleme)

Detaylı iş modeli: [`11_IS_MODELI.md`](11_IS_MODELI.md)