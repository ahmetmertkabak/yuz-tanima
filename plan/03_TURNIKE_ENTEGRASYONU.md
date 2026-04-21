# 🚪 03 - Turnike Entegrasyonu

## 🎯 Özet
Raspberry Pi, GPIO pini üzerinden **röle modülünü** tetikler. Röle modülü, turnikenin "dry contact" (kuru kontak) girişini kısa süreli kapatır. Turnike bunu "geçiş izni" olarak algılar ve açılır.

**Önemli:** Pi, turnike üzerinde **direkt yüksek gerilim kontrolü** yapmaz. Röle araya girerek hem **elektriksel izolasyon** hem **voltaj uyumu** sağlar.

---

## 📚 TURNİKE TİPLERİ VE KONTROL ARAYÜZLERİ

### 1. Dry Contact / NO (Normally Open) — En Yaygın ✅
- Turnike kontrol kartında "input" terminalleri var
- Bu 2 terminali kısa süreli birleştirirsen turnike açılır
- Voltaj genelde 12V veya 24V DC
- Pi'den röle ile kontrol edilir
- **En güvenli, en basit, standart seçim**

### 2. Wiegand Protokolü (26/34-bit)
- Turnike kart okuyucu ile haberleşme protokolü
- Pi, turnikeye "Kart ID: 12345" şeklinde dijital sinyal gönderir
- Eski sistemlerde yaygın
- Biraz daha karmaşık entegrasyon

### 3. RS-485 / Modbus
- Endüstriyel turnikelerde
- Daha karmaşık, genelde gerek yok

### 4. TTL / Serial
- Bazı Çin markası turnikelerde
- Dökümantasyon kalitesi değişken

**Yaklaşımımız:** **Dry Contact** ile başlayacağız (okul turnikelerinin %95+'ı destekler). Diğer protokoller ihtiyaç çıkarsa eklenir.

---

## 🔌 KABLOLAMA ŞEMASI (DRY CONTACT)

### Genel Şema

```
  ┌─────────────────────┐
  │   Raspberry Pi 4    │
  │                     │
  │  Pin 2  (5V)  ──────┼───────┐
  │  Pin 6  (GND) ──────┼─────┐ │
  │  GPIO 17      ──────┼───┐ │ │
  │  GPIO 27      ──────┼─┐ │ │ │
  └─────────────────────┘ │ │ │ │
                          │ │ │ │
                    ┌─────▼─▼─▼─▼─┐
                    │  2ch Röle   │
                    │  Modülü     │
                    │ IN2 IN1 GND VCC │
                    │             │
                    │  CH1: COM──┐│
                    │  CH1: NO ──┘│──┐
                    │             │  │  ← Turnike kontrol
                    │  CH2: COM──┐│  │    kartına
                    │  CH2: NO ──┘│──┤
                    └─────────────┘  │
                                     │
                    ┌────────────────▼──────┐
                    │ TURNİKE KONTROL KARTI │
                    │                        │
                    │ IN+ ───────────────    │ ← Röle COM
                    │ IN- ───────────────    │ ← Röle NO
                    │                        │
                    │ (Bu iki terminalin     │
                    │  birleşmesi "aç"       │
                    │  komutu anlamına       │
                    │  gelir)                │
                    └────────────────────────┘
```

### Pin Detayları

| Pi Pin | Fiziksel # | Röle Bacağı | Açıklama |
|---|---|---|---|
| 5V Power | 2 | VCC | Röle besleme |
| GND | 6 | GND | Ortak toprak |
| GPIO 17 | 11 | IN1 | Kanal 1 trigger (turnike aç) |
| GPIO 27 | 13 | IN2 | Kanal 2 trigger (yedek/alarm) |

### Röle Kontak Tipleri

```
  [COM] ─────┬─────
             │
             │  Normal durum: COM ↔ NC bağlı, COM ↔ NO açık
  [NC]  ─────┘     Röle aktif: COM ↔ NO bağlı, COM ↔ NC açık
  
  [NO]  ─────
  
  COM = Common (ortak)
  NO  = Normally Open (normalde açık)
  NC  = Normally Closed (normalde kapalı)
```

**Bizim kullanımımız:**  
- Turnike açma sinyali için **COM + NO** kullanılır
- Normalde açık → röle tetiklenince kapanır → turnike açılır → 500ms-2sn sonra röle bırakılır → normalde açık durumuna döner

---

## 💻 YAZILIM TARAFI (Pi'da)

### Röle Kontrol Kodu (Örnek)

```python
import RPi.GPIO as GPIO
import time

RELAY_CH1_PIN = 17  # Turnike aç
RELAY_CH2_PIN = 27  # Yedek/alarm

def setup_relay():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RELAY_CH1_PIN, GPIO.OUT)
    GPIO.setup(RELAY_CH2_PIN, GPIO.OUT)
    # Active-low röle → HIGH = OFF, LOW = ON
    GPIO.output(RELAY_CH1_PIN, GPIO.HIGH)
    GPIO.output(RELAY_CH2_PIN, GPIO.HIGH)

def open_turnstile(duration=1.0):
    """
    Turnike açma pulse'ı.
    duration: Röle aktif kalma süresi (saniye)
    """
    try:
        GPIO.output(RELAY_CH1_PIN, GPIO.LOW)   # Röle ON (turnike aç)
        time.sleep(duration)
        GPIO.output(RELAY_CH1_PIN, GPIO.HIGH)  # Röle OFF
        return True
    except Exception as e:
        print(f"Turnike açma hatası: {e}")
        return False

def cleanup():
    GPIO.cleanup()
```

### Dikkat Edilecek Noktalar

1. **Active-Low vs Active-High:** Röle modülüne göre mantık ters olabilir. Modül data sheet'i kontrol edilmeli.
2. **Pulse süresi:** Genelde 500ms-2sn arası. Turnike üreticisine göre değişir. Başlangıçta 1 saniye dene.
3. **Çakışma kontrolü:** İki kişi üst üste geçerse turnike zaten "busy" olur, ekstra pulse göndermek sorun çıkarmaz.
4. **Thread-safe kullanım:** Birden fazla thread'den çağrılıyorsa `threading.Lock` kullan.

---

## ⚠️ GÜVENLİK VE FAIL-SAFE

### Kural 1: Elektriksel Güvenlik
- ✅ **Optocoupler izolasyonlu röle** kullan (Pi'yi turnike yüksek voltajından izole eder)
- ✅ Pi ile turnike kontrol kartı **farklı güç kaynaklarından** beslenmeli
- ❌ Pi GPIO'sunu direkt turnikeye bağlama (voltaj/akım farkı Pi'yi yakar)

### Kural 2: Yazılım Fail-Safe
Sistem çöker veya Pi kapanırsa turnike ne olur?

**Seçenek A: "Fail-Closed" (Güvenlik modu)**
- Sistem çökerse turnike **kapalı** kalır
- Kimse geçemez
- Güvenlik için iyi ama insanlar içeride mahsur kalabilir

**Seçenek B: "Fail-Open" (Acil durum modu)** 🏆
- Sistem çökerse turnike **açık** kalır
- Herkes geçebilir
- **Yangın/deprem yönetmeliğine uygun** (Türkiye mevzuatı)
- Okullar için **zorunlu**

**Uygulama:**
- Turnike kontrol kartının kendi "emergency release" girişi kullanılmalı
- Yangın alarmı devresi paralel bağlanabilir
- Yanı sıra güvenlik görevlisi elle de açabilmeli

### Kural 3: Yetkisiz Geçiş Önleme
- Her açılış mutlaka `AccessLog`'a yazılmalı
- Snapshot (fotoğraf) alınmalı
- Şüpheli açılışlar (çok sık, tanınmayan kişi) alarm üretmeli

### Kural 4: Watchdog
Pi çökerse veya donarsa, hardware watchdog turnikeyi etkilememeli:
```python
# systemd watchdog (Pi yazılımı)
WatchdogSec=30s

# Pi tamamen çökerse → röle tetiklenmez → turnike kapalı kalır
# Bu OK, çünkü emergency release turnike kontrol kartında ayrı var
```

---

## 🔧 KURULUM SÜRECİ (Sahada)

### Adım 1: Turnike Kontrol Kartını İncele
1. Turnike kontrol paneli açılır (genelde yanda/altta küçük bir kutu)
2. Üretici dökümantasyonuna bak (Perco, Ozak, Türkbo gibi markalar var)
3. "External input" veya "Free pass" veya "Unlock button" terminallerini bul
4. Genelde etiket: `IN1`, `IN2`, `BUT1`, `REL1+`, `REL1-` gibi

### Adım 2: Mevcut Düğme Kontrolü
Çoğu turnikede "güvenlik görevlisi geçir" butonu vardır. Bu buton genelde **iki kablonun kısa devresiyle** çalışır → bizim röle de aynı işi yapacak. Paralel bağlanır.

### Adım 3: Multimetre ile Voltaj Ölçümü
- Terminal üzerindeki **açık devre voltajı** ölç (12V DC bekleniyor)
- Kısa devre akımı (mA) test et
- Bu değerler röle kapasitesine uyumlu mu kontrol et (2ch röle 10A @ 30V DC kaldırır, yeterli)

### Adım 4: Kablo Çekme
- Pi → Röle: 20cm jumper (röle Pi'nin yanında)
- Röle → Turnike: **2 damarlı kablo** (uzunluk = Pi'den turnikeye mesafe)
  - 0.5mm² veya 0.75mm² TTR kablo
  - 5m'ye kadar sorunsuz

### Adım 5: Bağlantı ve Test
```
Röle COM → Turnike IN+
Röle NO  → Turnike IN-
```
Yazılımdan `open_turnstile()` çağır → Turnike açılmalı.

### Adım 6: Feedback Sinyali (Opsiyonel)
Bazı turnikelerde "kişi geçti" sinyali çıkışı vardır. Bu sinyal Pi'ya GPIO input olarak bağlanabilir:
- Turnike OUT+ → Pi GPIO 22 (input, pull-up)
- Turnike OUT- → Pi GND

Yazılımda:
```python
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def detect_person_passed():
    if GPIO.input(22) == GPIO.LOW:
        return True  # Kişi gerçekten geçti
```

Bu sayede `AccessLog.granted = True` daha kesin olur.

---

## 🧪 TEST SENARYOLARI

| Test | Adım | Beklenti |
|---|---|---|
| Temel açma | `open_turnstile(1)` | Turnike 1 sn açılır |
| Hızlı tekrar | 100ms ara ile 5 çağrı | Turnike açık kalır (sorun değil) |
| Güç kesme | Pi'yi fişten çek | Turnike emergency release devresiyle açılır |
| Ağ kopması | Ethernet çıkar | Tanıma + turnike çalışmaya devam eder |
| 10 saat çalışma | Sürekli açma/kapama | Röle kontakları sağlam, Pi stabil |
| Paralel kişi | Aynı anda 2 kişi | İlk kişi girer, ikinci için tekrar tanıma gerekir |

---

## 🚨 HATA SENARYOLARI VE ÇÖZÜMLERİ

| Sorun | Sebep | Çözüm |
|---|---|---|
| Röle tıklıyor ama turnike açılmıyor | Voltaj uyumsuzluğu veya NO/NC karışık | Multimetre ile kontrol, bağlantıyı ters çevir |
| Turnike sürekli açık | Röle kontağı kaynaklanmış | Röle değiştir |
| Pi GPIO yanıt vermiyor | GPIO mode çakışması | `GPIO.cleanup()` → yeniden setup |
| İki kişi aynı anda geçiyor | Turnike aç süresi uzun | `duration=0.5` yap |
| Turnike motor sesi yok | Güç kesilmiş veya emergency modda | Turnike kontrol kartı incele |

---

## 🇹🇷 TÜRKİYE'DE YAYGIN TURNİKE MARKALARI

| Marka | Dry Contact Desteği | Not |
|---|---|---|
| **Perco (Rusya)** | ✅ Var | Yaygın, dokümantasyon iyi |
| **Ozak** | ✅ Var | Türk üretimi |
| **Türkbo** | ✅ Var | Türk üretimi |
| **Mega** | ✅ Var | Yerli marka |
| **ZKTeco** | ✅ Var | Çin, ucuz |
| **Hikvision** | ✅ Var | Çin, IP destekli |

**Okula gitmeden önce:** Turnike markası/modeli sorulsun, teknik döküman indirilsin. Müdahale öncesi kablolama hazır olsun.

---

## 🔐 VANDALIZM / HIRSIZLIK ÖNLEMLERİ

1. **Pi Kasası Kilit:** Pi ve röle, kilitli metal/plastik kutuda olsun
2. **Kablo Kanalı:** Pi → Turnike kablosu görünür yerde olmasın (PVC kanal içinde)
3. **API Key Dönüşümlü:** Pi çalınırsa panelden api_key iptal edilir → o Pi sisteme bir daha giremez
4. **Cihaz Uzaktan Kapatma:** SuperAdmin panelden "Bu cihazı deaktif et" → api isteği ret
5. **Fiziksel Etiket:** "Okul Mülkü - Çalınması Halinde Cihaz Bloke Edilir" uyarısı

---

## 📸 KURULUM BELGELEME

Her okulda kurulum sırasında şunlar fotoğraflanır ve SuperAdmin panele yüklenir:
- Turnike kontrol kartı bağlantıları
- Pi + kamera montaj pozisyonu
- Kamera açısı (örnek tanıma testi)
- Kablolama diyagramı
- Kurulum tarihi, teknisyen adı

Bu, ileride uzaktan destek sırasında kritik.

---

## ✅ KABUL KRİTERLERİ (Kurulum Tamamlandı Sayılması İçin)

- [ ] Pi açılıp kapatıldığında otomatik başlıyor
- [ ] Kayıtlı bir yüz gösterildiğinde turnike 1-2 saniyede açılıyor
- [ ] Tanınmayan yüzde turnike açılmıyor, snapshot kaydediliyor
- [ ] İnternet kesildiğinde sistem çalışmaya devam ediyor
- [ ] İnternet geri geldiğinde loglar VPS'e push oluyor
- [ ] Emergency release devresi fonksiyonel (yangın senaryosu)
- [ ] SuperAdmin panelde Pi "online" görünüyor
- [ ] 30 dakika canlı test sırasında 20 geçiş sorunsuz