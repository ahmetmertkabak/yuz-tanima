# 🌐 06 - Web Panel Güncellemeleri

## 🎯 3 Farklı Panel Seviyesi

Multi-tenant SaaS modelinde farklı kullanıcılar farklı arayüzler görür:

| Panel | URL | Kullanıcı | Yetki |
|---|---|---|---|
| **Super Admin** | `admin.yuztanima.com` | Biz (firma) | Tüm sistem |
| **School Admin** | `[okul].yuztanima.com` | Okul müdür/IT | Kendi okulu |
| **School Staff** | Aynı URL, farklı role | Öğretmen/sekreter | Okuma |

---

## 👑 1. SUPER ADMIN PANELİ

### Amaç
Tüm okulları merkezi olarak yönetmek, yeni okul eklemek, cihaz durumlarını izlemek, destek vermek.

### Sayfalar

#### `/` — Dashboard
- Toplam okul sayısı, aktif cihaz sayısı, son 24 saat toplam geçiş
- Online/offline cihaz listesi (kırmızı alarmlı)
- Son 10 sistem olayı (yeni okul, cihaz offline vb.)
- Abonelik süresi dolmak üzere olan okullar

#### `/schools` — Okul Yönetimi
**Liste görünümü:**
- Okul adı, subdomain, kayıt tarihi, kişi sayısı, cihaz sayısı, abonelik durumu
- Arama, filtreleme, sıralama
- Durum filtresi: aktif / trial / süresi dolmuş / askıya alınmış

**Detay sayfası (`/schools/<id>`):**
- Bilgiler düzenleme
- Cihaz listesi + durum
- Kullanıcı listesi
- Abonelik yönetimi (uzat, iptal, plan değiştir)
- "Bu okula giriş yap" (impersonation — destek için)
- Audit log

**Yeni okul oluşturma (`/schools/new`):**
- Okul bilgileri
- Subdomain seçimi (benzersizlik kontrolü)
- Abonelik planı
- İlk admin kullanıcı oluşturma (email + şifre kurma linki)
- Otomatik: DNS kayıt, SSL, ilk device API key

#### `/devices` — Tüm Cihazlar (Global)
**Liste görünümü:**
- Okul adı, cihaz adı, lokasyon, son heartbeat, online/offline
- Filtreler: okul, durum, versiyon
- "90+ saniye offline" uyarıları

**Detay sayfası (`/devices/<id>`):**
- Cihaz bilgileri (IP, versiyon, CPU, RAM, disk)
- Son 24 saat geçiş grafiği
- Son loglar (canlı stream)
- **Uzaktan komutlar:**
  - Reboot
  - Force sync
  - Update firmware
  - Reload encodings
  - Disable (api_key iptal)
- Kurulum fotoğrafları
- Uzak terminal (sadece ileride, VPN üzerinden)

#### `/updates` — OTA Yazılım Güncelleme
- Mevcut versiyonlar listesi
- Yeni versiyon upload (zip)
- Hangi okullara push edilecek (hepsine / belirli / beta grup)
- Rollout zamanlama (gece 03:00 vb.)
- Güncelleme sonrası başarı/hata raporu

#### `/billing` — Abonelik & Fatura
- Aktif abonelikler
- Gelir raporu (aylık/yıllık)
- Fatura oluşturma
- Ödeme hatırlatmaları (7 gün önce otomatik email)

#### `/support` — Destek Sistemi
- Gelen destek talepleri
- Okul adına sisteme girip inceleme
- Çözüm notları

#### `/settings` — Sistem Ayarları
- Super admin kullanıcıları
- Global config
- Email şablonları
- Loglar, sistem durumu

### Ekran Tasarımı Felsefesi
- **Dark theme** (admin olduğu belli olsun)
- **Yoğun veri, tablo bazlı**
- **Hızlı erişim menüsü**
- Bootstrap 5 veya Tabler.io benzeri admin şablonu

---

## 🏫 2. SCHOOL ADMIN PANELİ

### Amaç
Okul müdürü/IT sorumlusu günlük işleri halleder: öğrenci ekle/sil, rapor al, geçişleri izle.

### Sayfalar

#### `/` — Dashboard
**Bugünün anlık durumu:**
- Toplam kayıtlı kişi
- Bugün giriş yapan kişi sayısı
- Bugün gelmeyen (aktif olanlardan)
- Son 10 geçiş (canlı)
- Cihaz durumu (1 kapı için: "Ana Giriş - Online")

**Canlı feed (WebSocket):**
- "10:23 Ahmet Yılmaz girdi (Ana Giriş) ✅"
- "10:24 Tanınmayan kişi (Ana Giriş) ⚠️" → tıklayınca snapshot

**Grafikler:**
- Saatlik giriş dağılımı (bugün)
- Haftalık giriş trendi
- Sınıflara göre devam oranı

#### `/persons` — Kişi Yönetimi
**Liste:**
- Öğrenci, öğretmen, personel tümü (filtrelenebilir)
- Kolonlar: ad, no, rol, sınıf, yüz kayıtlı mı, son giriş, aktif mi
- Arama (isim, no)
- Toplu işlemler: aktif/pasif, sil

**Detay (`/persons/<id>`):**
- Kişi bilgileri
- Yüz fotoğrafı gösterimi
- "Yüzü yeniden kaydet" butonu
- Erişim takvimi (hangi saatlerde girebilir)
- Son 30 gün giriş geçmişi (grafik)
- Veli bilgileri
- KVKK onay durumu
- İşlem logları (kim eklemiş, ne zaman)

**Yeni kişi (`/persons/new`):**
Form alanları:
- Ad soyad, no, rol
- Sınıf
- Email, telefon
- Veli telefonu
- **"Yüzü Şimdi Kaydet" butonu:**
  - Modal açılır → webcam izni
  - 3-5 frame otomatik yakalanır
  - Kalite kontrolü gösterilir
  - Kaydet → encoding üretilir
- KVKK onay belgesi yükleme (PDF)

**Toplu import:**
- Excel yükleme (mevcut özellik — korunacak)
- Her öğrenci için sonra yüz kaydı yapılır

#### `/access-logs` — Geçiş Logları
- Tarih aralığı seçici
- Kişiye göre filtreleme
- Yöne göre filtre (in/out)
- "Sadece reddedilenler" checkbox
- Her satırda: zaman, kişi, kapı, yön, onay, güven, snapshot (varsa)
- Excel export

#### `/reports` — Raporlar
**Günlük rapor:**
- Bugün kimler geldi, kimler gelmedi
- Gelenler: ilk giriş saati, çıkış saati (varsa)
- Gelmeyenler: liste + veli telefonları (toplu SMS linki?)
- Geç kalanlar (örn. 08:30'dan sonra girenler)

**Aylık rapor:**
- Kişi bazlı devam günü sayısı
- Sınıf bazlı özet
- En çok gelmeyenler listesi

**Özel filtre:**
- Tarih aralığı
- Kişi grubu (sınıf, rol)
- Excel/PDF export

#### `/unknown-visitors` — Tanınmayan Kişiler
- Snapshot galerisi (son 30 gün)
- "Bu kim?" — admin "ekle" veya "görmezden gel" diyebilir
- Eşleşme önerisi (AI, mevcut kişilere benzer)

#### `/devices` — Cihazlar (Salt Okunur)
- Okulun cihazları (pilot için 1 tane)
- Son heartbeat, online/offline
- Son 24 saat geçiş sayısı
- "Ping test" butonu (cihaza test isteği at)
- Uzaktan reboot YOK (SuperAdmin'de)

#### `/users` — Kullanıcı Yönetimi
- Okulun personel listesi
- Rol: school_admin / school_staff / viewer
- Yeni kullanıcı ekleme (email + rol)
- Şifre sıfırlama

#### `/settings` — Okul Ayarları
- Okul bilgileri (ad, adres, telefon)
- Logo yükleme
- Recognition tolerance (ince ayar)
- Bildirim tercihleri (kim offline olunca kime mail)
- Email / SMS gateway ayarları (opsiyonel)

---

## 👁️ 3. SCHOOL STAFF (VIEWER) PANELİ

Aynı URL, ama rol kısıtlamalı. Sayfa görünümleri:
- ✅ Dashboard (salt okunur)
- ✅ Persons listesi (salt okunur, arama)
- ✅ Access logs (salt okunur)
- ✅ Reports (okuma + export)
- ❌ Yeni kişi ekleme yok
- ❌ Kullanıcı yönetimi yok
- ❌ Cihaz/ayar yok

Flask-Login + Role-based access control (RBAC) ile yönetilir:

```python
from functools import wraps

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/persons/new')
@login_required
@role_required('school_admin', 'super_admin')
def new_person():
    ...
```

---

## 🎨 UI/UX TASARIM

### Renk Şeması
- **Super Admin:** Koyu tema (dark gray/blue), profesyonel
- **School Admin:** Açık tema, okul logosu üstte, kurumsal
- **Marka rengi:** Her okul kendi rengini seçebilir (buton, accent için)

### Responsive
- Desktop öncelikli (admin çalışması için)
- Tablet uyumlu (müdür iPad ile bakar)
- Mobile özet (sadece dashboard + son geçişler)

### Framework Önerileri
| Framework | Notlar |
|---|---|
| **Bootstrap 5** | Hızlı, mevcut kod Bootstrap kullanıyor, tanıdık |
| **Tabler.io** | Bootstrap tabanlı admin template, şık |
| **AdminLTE** | Klasik admin dashboard |
| **Tailwind CSS** | Modern ama öğrenme eğrisi var |

**Tavsiye:** Mevcut Bootstrap 5'i korumak. Tabler.io şablonundan parçalar alınabilir. Sonradan Tailwind'e geçiş düşünülebilir.

### JavaScript
- **Alpine.js** — basit interaktiflik için (Vue kadar güçlü değil ama çok hafif)
- **HTMX** — sayfa yenilemeden Flask ile iletişim için MÜKEMMEL
- **Chart.js** — grafikler için
- **Socket.IO Client** — canlı güncelleme için

**HTMX öneriyorum:** Flask uygulamalarında SPA yazmak yerine HTMX ile server-side render + dinamik içerik. Daha az JS, daha az bug.

---

## 🔴 CANLI ÖZELLIK: WebSocket Dashboard

School Admin dashboard açıkken, biri turnikelerden geçtiğinde anında görünür:

### Backend (Flask-SocketIO)
```python
from flask_socketio import SocketIO, emit, join_room

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'school_{current_user.school_id}')

# Access log geldiğinde
def on_access_log_created(log):
    socketio.emit('access_log', {
        'person_name': log.person.full_name,
        'timestamp': log.timestamp.isoformat(),
        'device': log.device.device_name,
        'granted': log.granted
    }, room=f'school_{log.school_id}')
```

### Frontend
```html
<script>
  const socket = io();
  socket.on('access_log', (data) => {
    addLogToFeed(data);  // Animasyonlu üstte ekle
    playSound('chime');  // Opsiyonel
    updateCounter();
  });
</script>
```

---

## 📊 DASHBOARD GRAFİKLERİ

Chart.js ile:

1. **Saatlik Giriş Grafiği (Bugün)**
   - Bar chart, 06:00 - 18:00 arası saatlik
   
2. **Haftalık Trend**
   - Line chart, son 7 gün toplam giriş

3. **Sınıf Bazlı Devam**
   - Horizontal bar, sınıf/yoklama %

4. **Cihaz Durumu Timeline**
   - Online/offline switch (renk değişimli)

---

## 📥 EXCEL EXPORT

Mevcut özellik korunacak, sadece veri yapısı değişecek:

```python
# Yeni format
@app.route('/reports/daily/export')
def export_daily():
    df = pd.DataFrame([
        {
            'Ad Soyad': log.person.full_name,
            'Sınıf': log.person.class_name,
            'Giriş Saati': log.timestamp,
            'Kapı': log.device.device_name,
            'Durum': 'Giriş' if log.granted else 'Reddedildi'}
        for log in access_logs
    ])
    return send_excel(df, 'gunluk_yoklama.xlsx')
```

---

## 📸 YÜZ KAYDETME MODAL'I

En kritik UX parçası bu. Detaylı akış:

```
[Yeni Öğrenci Ekle] formunu doldurdu
   ↓
[Yüzü Şimdi Kaydet] butonuna basıyor
   ↓
Modal açılıyor:
  ┌─────────────────────────────────────┐
  │ Yüz Kaydet - Ahmet Yılmaz           │
  ├─────────────────────────────────────┤
  │                                     │
  │        [ WEBCAM FEED ]              │
  │         (canlı yayın)               │
  │                                     │
  │  Yüz konumu: ✅ İyi / ⚠️ Uzak       │
  │  Işık: ✅ İyi                       │
  │  Yüz sayısı: 1 ✅                   │
  │                                     │
  │  [Fotoğraf 1/5]                     │
  │  [Fotoğraf 2/5]                     │
  │  ...                                │
  │                                     │
  │  [Yeniden Çek] [Kaydet]             │
  └─────────────────────────────────────┘
   ↓
Frontend 5 frame yakalar, backend'e yollar
   ↓
Backend her frame için encoding üretir
   ↓
Ortalama encoding DB'ye yazılır
   ↓
"Kaydedildi, Pi'lara 1-2 dakika içinde senkronize olacak"
```

### Kalite Kontrolü (İleri Özellik)
- Yüz kadraj dışında → uyarı
- Bulanık → uyarı
- Birden fazla yüz → uyarı
- Çok uzak/yakın → uyarı

Kullanıcı her kontrol geçtiğinde fotoğraf çekebilir.

---

## 🔄 GERİYE UYUMLULUK (Mevcut Kodu Korumak)

Mevcut koddan korunanlar:
- [`app/forms.py`](app/forms.py) — temel form yapısı
- [`app/templates/base.html`](app/templates/base.html) — şablon base
- [`app/templates/login.html`](app/templates/login.html) — giriş sayfası
- [`app/templates/dashboard.html`](app/templates/dashboard.html) — iskelet
- Pandas + openpyxl rapor export mantığı
- Flask-Login auth flow

Yeniden yazılacak:
- [`app/templates/student_detail.html`](app/templates/student_detail.html) → `person_detail.html`
- Dashboard içerik (bakiye kaldırılacak, yoklama eklenecek)
- Menü yapısı (yeni sayfalar için)

---

## 📦 STATIK DOSYALAR

```
app/static/
├── css/
│   ├── admin.css       (super admin tema)
│   ├── school.css      (school admin tema)
│   └── shared.css
├── js/
│   ├── webcam-capture.js    (yüz kayıt modal)
│   ├── live-feed.js         (socketio dashboard)
│   ├── charts.js
│   └── app.js
├── img/
│   ├── logo.png
│   └── avatars/
└── vendor/             (bootstrap, chart.js vs.)
```

---

## 🧪 KULLANIM SENARYOLARI (User Stories)

### Senaryo 1: Yeni Dönem Başlangıcı
Okul admini 500 öğrenciyi Excel ile toplu yükler. Sonra her öğrenci okula geldikçe "yüz kaydet" diye ekler.

### Senaryo 2: Öğrenci Gelmedi — Veliyi Ara
Sabah 09:30. Admin dashboardunda "Bugün gelmeyenler" sekmesine bakar. Ayşe Kaya'nın yanında veli telefon numarası var. Tıklar → telefon açılır.

### Senaryo 3: Tanınmayan Giriş Alarmı
Snapshot galerisinde bilinmeyen yüz var. Admin kim olduğuna bakar. Yeni gelen öğretmen → profil oluşturur, yüzünü kaydeder.

### Senaryo 4: Cihaz Offline
Super admin panelde "Ali Paşa Lisesi - Ana Giriş Pi — 5 dakikadır offline" uyarısı. Admin okul müdürünü arar, "Pi'nin power kablosu düşmüş" gibi çıkar.

---

## 🌐 ÇOK DİLLİ DESTEK (İleride)

Başlangıçta Türkçe. Sonradan:
- Flask-Babel ile çeviri
- Okul admin paneli Türkçe
- Super admin İngilizce + Türkçe

---

## ✅ ÖZET

| Özellik | Mevcut | Yeni |
|---|---|---|
| Panel seviyeleri | 1 (admin) | 3 (super + school admin + staff) |
| Dashboard | Bakiye + yoklama | Canlı yoklama + WebSocket |
| Öğrenci ekleme | Form | Form + yüz kayıt modal |
| Raporlar | Aylık bakiye | Günlük yoklama + gelmeyenler |
| Cihaz yönetimi | Yok | Var (SuperAdmin) |
| Canlı feed | Yok | WebSocket ile anında |
| Subdomain routing | Yok | Tenant middleware |

Sonraki doküman: [`07_GUVENLIK_VE_KVKK.md`](07_GUVENLIK_VE_KVKK.md)