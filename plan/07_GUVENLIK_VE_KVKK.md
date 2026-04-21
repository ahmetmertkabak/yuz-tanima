# 🔐 07 - Güvenlik ve KVKK Uyumluluğu

## ⚠️ EN KRİTİK DOKÜMAN

Yüz tanıma = **biyometrik veri** = KVKK Özel Nitelikli Kişisel Veri. Çocukların verisi ise daha da hassas. **Bu doküman eksik yapılırsa yasal ciddi yaptırım riski var.** Para cezası milyonlarla ifade edilir.

---

## ⚖️ YASAL ÇERÇEVE (Türkiye)

### 1. **KVKK (Kişisel Verilerin Korunması Kanunu — 6698 Sayılı)**
- Yüz biyometrik veri → **Özel Nitelikli Kişisel Veri** (Madde 6)
- İşlenmesi için **açık rıza** şart
- Reşit olmayanlarda **velinin açık rızası** şart
- VERBİS (Veri Sorumluları Sicili) kayıt zorunlu

### 2. **MEB Yönetmeliği**
- 2024-2025 döneminde çıkması beklenen yüz tanıma zorunluluğu
- MEB uygulama kılavuzu çıktığında ona göre güncelleme gerekir
- Okul Milli Eğitim Müdürlüğü onayı gerekebilir

### 3. **ILO Çocuk Hakları**
- 18 yaş altı için ek koruma
- BM Çocuk Hakları Sözleşmesi (Türkiye taraf)

### 4. **GDPR (AB Vatandaşı Okulu Varsa)**
- Uluslararası okullarda AB vatandaşı öğrenciler varsa GDPR da geçerli
- Benzer kurallar, daha ağır yaptırım (global cironun %4'ü)

---

## 🔑 ROL DAĞILIMI (Veri Sorumlusu / İşleyen)

Bu **çok önemli**, sözleşmelerde netleştirilmeli:

| Rol | Kim? | Sorumluluk |
|---|---|---|
| **Veri Sorumlusu (Data Controller)** | **OKUL** | Verilerin toplanması, amaç, rıza alınması |
| **Veri İşleyen (Data Processor)** | **BİZ (firma)** | Verilerin güvenli işlenmesi, depolanması |

Yani:
- Okul, öğrenciden rıza alır
- Okul verileri amaca uygun kullanır
- Biz, altyapıyı güvenli sağlarız, veri bütünlüğünü koruyalım
- Arasında **Veri İşleyen Sözleşmesi (DPA)** imzalanır

### DPA (Data Processing Agreement) İçeriği
- Verilerin işlenme amacı
- İşlenecek veri kategorileri
- Güvenlik önlemleri
- Alt işleyen kullanımı (Hetzner VPS vs.)
- Sözleşme süresi
- Veri silme prosedürü
- İhlal bildirimi süreleri (72 saat içinde KVKK'ya bildirim)

---

## 📝 AÇIK RIZA MEKANİZMASI

### Veli Onay Formu (Zorunlu)

Her öğrenci için fiziksel veya dijital imzalı bir form:

```
═══════════════════════════════════════════════════════════
    YÜZ TANIMA SİSTEMİ VELİ AÇIK RIZA FORMU
═══════════════════════════════════════════════════════════

Öğrenci: [Ad Soyad]
Sınıf: [9-A]
Okul No: [2025001]

Velinin Adı: [Ad Soyad]
T.C. Kimlik No: [XXXXXXXXXXX]
Yakınlık: [Anne / Baba / Vasi]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Yukarıda bilgileri yazılı çocuğumun/velayetim altındaki 
öğrencinin yüz biyometrik verisinin, [OKUL ADI] tarafından 
işletilen yüz tanımalı giriş-çıkış kontrol sisteminde 
aşağıdaki amaçlarla işlenmesine AÇIK RIZAM vardır:

☐ Okul giriş/çıkış yoklaması
☐ Güvenlik ve erişim kontrolü
☐ Devamsızlık takibi ve raporlaması

Veri sorumlusu: [OKUL ADI]
Veri işleyen: [FİRMA ADI] (altyapı sağlayıcısı)

Verinin saklanma süresi: Öğrencinin okul kaydı aktif olduğu
sürece + 1 yıl. Ayrılış halinde 30 gün içinde silinir.

Haklarınız (KVKK Madde 11):
- Verinizin işlenip işlenmediğini öğrenme
- İşlenmişse bilgi talep etme
- Amaca uygun kullanılıp kullanılmadığını öğrenme
- Düzeltilmesini veya silinmesini isteme
- İşlemeye itiraz etme
- Zararın giderilmesini talep etme

İletişim:
- Okul: [okul iletişim]
- Veri İşleyen: [firma iletişim]
- KVKK Kurumu: www.kvkk.gov.tr

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Tarih: ___/___/______
  
  Veli İmzası: _________________________
  
  Öğrenci İmzası (18+ ise): _________________________

═══════════════════════════════════════════════════════════
```

### Dijital Onay (Opsiyonel)
- Velinin cep telefonuna SMS onay linki
- e-Devlet ile doğrulama (ileride)
- Scanlı PDF olarak sistemde saklanır

### Rızanın Geri Alınması
Veli istediği zaman "verimi sil" diyebilir. Sistem bunu otomatik yapmalı:
- Panel'de "Verilerimi sil" butonu
- Sistem: face_encoding = NULL, photo_path = NULL
- 30 gün soft-delete, sonra hard-delete

---

## 🛡️ TEKNİK GÜVENLİK ÖNLEMLERİ

### 1. Veri Aktarımı (Encryption in Transit)

✅ **Tüm trafik HTTPS (TLS 1.3)**
- Pi ↔ VPS: HTTPS zorunlu
- Panel ↔ VPS: HTTPS zorunlu
- Let's Encrypt sertifika otomatik yenileme

✅ **HSTS (HTTP Strict Transport Security)**
- Browser'a "bu siteyi sadece HTTPS ile aç" der

✅ **Certificate Pinning (Pi için)**
- Pi sadece beklenen sertifikayla VPS'e bağlanır (MitM önler)

### 2. Veri Depolama (Encryption at Rest)

✅ **PostgreSQL Transparent Data Encryption**
- Disk şifreli (Hetzner disk encryption otomatik)

✅ **Biyometrik veri kolonu ekstra şifreli**
```python
# application-level encryption
from cryptography.fernet import Fernet

class Person(db.Model):
    _face_encoding_encrypted = db.Column(db.LargeBinary)
    
    @property
    def face_encoding(self):
        return fernet.decrypt(self._face_encoding_encrypted)
    
    @face_encoding.setter
    def face_encoding(self, value):
        self._face_encoding_encrypted = fernet.encrypt(value)
```

✅ **Yedekler şifreli**
- DB yedekleri GPG ile şifrelenip S3'e yüklenir
- Şifre çözme anahtarı ayrı yerde saklanır

### 3. Erişim Kontrolü

✅ **Role-Based Access Control (RBAC)**
- SuperAdmin, SchoolAdmin, SchoolStaff, Viewer
- Her endpoint için rol kontrolü

✅ **Multi-Factor Authentication (2FA)**
- SuperAdmin ZORUNLU
- SchoolAdmin tavsiye edilir (TOTP — Google Authenticator)

✅ **Session Security**
- Secure cookies (HTTPOnly, SameSite=Strict)
- Session timeout (2 saat inactivity)
- Concurrent session limiti (aynı hesap 3 cihazdan çok açılamaz)

✅ **Rate Limiting**
- Login: 5 deneme/15 dakika (IP başı)
- API: 100 req/dk (device başı)
- Brute force koruması: Fail2ban

### 4. Audit Logging

Her kritik işlem loglanır ve **değiştirilemez** (append-only):

```python
class AuditLog(db.Model):
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer)
    action = db.Column(db.String)
    # 'person.create', 'person.delete', 'face.update', 
    # 'face.delete', 'device.reboot', 'bulk_export', vs.
    resource_type = db.Column(db.String)
    resource_id = db.Column(db.Integer)
    ip_address = db.Column(db.String)
    details = db.Column(db.JSON)
```

Denetim (audit) sırasında "Kim ne zaman hangi veriyi gördü/değiştirdi?" sorusunu cevaplayabilmelisin.

### 5. Tenant İzolasyonu (Kritik!)

```python
# Her sorguda otomatik filter
@event.listens_for(Session, "do_orm_execute")
def filter_by_tenant(execute_state):
    if not execute_state.is_select or g.get('school_id') is None:
        return
    # ... otomatik school_id = g.school_id ekle
```

Testler:
- **Integration test:** Okul A admin, Okul B verisine erişim denemesi → 403 olmalı
- **SQL injection koruması:** SQLAlchemy ORM kullanımı (raw SQL yok)

### 6. Device Authentication

Her Pi unique `api_key` ile bağlanır. API key:
- 64 karakter random
- Panel'den üretilir, Pi'ya bir kere yazılır
- HMAC ile her request imzalanır
- İstenince iptal edilebilir (cihaz çalınmışsa)

```python
@api.before_request
def device_auth():
    api_key = request.headers.get('X-Device-Key')
    timestamp = request.headers.get('X-Timestamp')
    signature = request.headers.get('X-Signature')
    
    # Timestamp 5 dk içinde olmalı (replay attack önleme)
    if abs(time.time() - int(timestamp)) > 300:
        abort(401)
    
    device = Device.query.filter_by(api_key=api_key, is_active=True).first()
    if not device:
        abort(401)
    
    # HMAC doğrulama
    expected = hmac.new(device.secret, 
                        f"{timestamp}:{request.path}:{request.data}".encode(), 
                        'sha256').hexdigest()
    if not hmac.compare_digest(expected, signature):
        abort(401)
    
    g.device = device
    g.school_id = device.school_id
```

---

## 📸 FOTOĞRAF / SNAPSHOT YÖNETİMİ

### Kayıt Fotoğrafları
- Orjinal yüz fotoğrafı S3'te saklanır
- Encoding DB'de saklanır (encoding'den yüze geri dönüş matematik olarak mümkün DEĞİL — tek yönlü)
- Teorik olarak encoding daha güvenli ama yine de hassas veri

### Tanımayan Kişi Snapshot'ları
- Güvenlik için saklanır ama **süresi sınırlı**
- 30 gün sonra otomatik silinir (cron job)
- Admin "bu kişi zararsız" diyebilir → silinir
- Admin "bu kişiyi şüpheli olarak bildir" diyebilir → arşivlenir

### KVKK İçin Veri Saklama Süreleri

| Veri | Süre | Gerekçe |
|---|---|---|
| Yüz encoding (aktif öğrenci) | Kayıt süresi boyunca | Hizmet sunumu için |
| Yüz encoding (ayrılmış) | 30 gün (sonra sil) | Ayrılış sonrası |
| Yüz fotoğrafı | Kayıt süresi | Admin kontrol için |
| Access log | 1 yıl | MEB yönetmelik + raporlama |
| Snapshot (tanımayan) | 30 gün | Güvenlik analizi |
| Audit log | 2 yıl | Yasal gereklilik |
| KVKK onay formları | 10 yıl | Hukuki savunma için |

### Otomatik Silme (Celery Task)
```python
@celery.task
def cleanup_expired_data():
    # 30+ gün snapshot'lar
    Snapshot.query.filter(
        Snapshot.timestamp < datetime.utcnow() - timedelta(days=30)
    ).delete()
    
    # Ayrılmış öğrenci encoding'leri
    Person.query.filter(
        Person.is_active == False,
        Person.updated_at < datetime.utcnow() - timedelta(days=30)
    ).update({Person.face_encoding: None, Person.face_photo_path: None})
    
    db.session.commit()
```

Günlük cron ile çalışır.

---

## 🚨 VERİ İHLALİ YÖNETİMİ

### İhlal Nedir?
- Yetkisiz erişim (hack, sızıntı)
- Veri kaybı (server çökmesi ile DB silinmesi)
- Yanlış taraflara veri gönderimi

### Prosedür (72 saat kuralı!)
1. **Tespit:** Monitoring + alarm sistemi
2. **İzolasyon:** Etkilenen sistemi offline al
3. **Analiz:** Hangi veri, kaç kişi, ne zaman?
4. **Bildirim (72 saat içinde!):**
   - KVKK Kurumu (https://www.kvkk.gov.tr)
   - Etkilenen veri sahipleri (veliler)
   - Okul yönetimi
5. **Azaltma:** Şifre sıfırlama, sertifika yenileme vb.
6. **Dokümantasyon:** Tüm süreç yazılı kayıt
7. **Önleme:** Kök neden analizi, düzeltici aksiyon

### Hazır Bulundurulacaklar
- KVKK ihlal bildirim formu şablonu
- Email şablonları (veli, okul, KVKK için ayrı ayrı)
- Basın bildirisi şablonu (büyük ihlal halinde)
- İletişim listesi (avukat, sigorta, basın)

---

## 🧪 GÜVENLİK TESTLERİ

### Penetration Testing
- İlk lansmandan önce **en az bir pen-test** yaptırın
- Yıllık tekrar edilmeli
- OWASP Top 10 kapsamı minimum

### Otomatik Güvenlik Taraması
- **Bandit** (Python kod güvenlik analizi)
- **Safety** (bağımlılık açık kontrolü)
- **OWASP ZAP** (web app scanner)
- Her PR'da çalışır

### Güvenlik Checklist
- [ ] SQL injection korumalı (SQLAlchemy ORM)
- [ ] XSS koruması (Jinja2 auto-escape)
- [ ] CSRF koruması (Flask-WTF)
- [ ] Password hash: bcrypt veya argon2
- [ ] Secrets env variable'da (kod içinde değil)
- [ ] DEBUG=False production'da
- [ ] CORS kısıtlı
- [ ] Security headers (CSP, X-Frame-Options, vb.)
- [ ] Input validation hepsinde
- [ ] File upload validation (sadece image)

---

## 🌐 VERİ LOKASYONU (KVKK Kritik!)

### Veriler NEREDE saklanır?
- PostgreSQL → **Türkiye veya AB** tercih edilir (KVKK'ya uygun)
- AB transferinde KVKK Kurumu izni gerekebilir
- **ABD'li cloud'dan (AWS US, Azure US) kaçın**

### Tavsiye
- **Birincil:** Türkiye (Natro, Yedekoleji, TurkTelekom Cloud)
- **İkincil kabul:** Hetzner (Almanya, AB GDPR)
- **Kaçın:** AWS US, GCP US

---

## 📋 KVKK UYUM CHECKLIST'İ

### İlk Lansman Öncesi Mutlaka:
- [ ] VERBİS kaydı tamamlandı
- [ ] Veri Sorumlusu (Okul) ve Veri İşleyen (Biz) netleştirildi
- [ ] DPA (Veri İşleyen Sözleşmesi) hazır ve imzalı
- [ ] Veli onay formu şablonu hukuk onayı aldı
- [ ] Gizlilik politikası yayınlandı (her subdomain'de footer'da link)
- [ ] Kullanım koşulları yayınlandı
- [ ] Çerez politikası yayınlandı (panel cookie kullanıyor)
- [ ] "Verilerimi sil" mekanizması çalışıyor
- [ ] "Verilerimi indir" mekanizması (data portability)
- [ ] İhlal bildirim planı hazır
- [ ] Güvenlik pen-test yapıldı
- [ ] Yedekleme + restore test edildi
- [ ] Audit log çalışıyor
- [ ] Otomatik silme cron'ları çalışıyor

### Her Okul Kurulum Öncesi:
- [ ] Okul yönetimine KVKK brifingi verildi
- [ ] DPA imzalandı
- [ ] Velilere onay formu gönderildi
- [ ] En az %95 veli onay alındı (yoksa başlama)
- [ ] Onay alınmayan öğrenciler için alternatif (manuel kayıt)
- [ ] KVKK iletişim kişisi belirlendi (okul tarafında)

---

## ⚖️ HUKUKİ DESTEK

### İhtiyaç
- **KVKK uzmanı avukat** — başlangıç sözleşmeleri için
- Yıllık retainer (aylık ~5.000-10.000 TL)
- İhlal durumunda 24/7 destek

### Sigorta
- **Siber sorumluluk sigortası** (cyber liability insurance)
- İhlal durumunda masrafları karşılar
- Yıllık ~15.000-30.000 TL (cironun %1-2'si)

---

## 🎓 ETİK DEĞERLENDİRMELER

Sadece yasal değil, etik olarak da düşünmek gerekir:

1. **Çocuğun mahremiyeti** — Biyometri "takip" hissi verir. Bilinçlendirme şart.
2. **Teknoloji bağımlılığı** — Yüz tanıma olmazsa okul çalışamaz hale gelmemeli
3. **Ayrımcılık riski** — Tanıma zayıf çalışan kişi (engelli, farklı etnik köken) dışlanmamalı
4. **Veri minimizasyonu** — Sadece gerekli veri topla, fazlasını değil
5. **Şeffaflık** — Velilere verilerin nasıl kullanıldığı açık anlatılmalı
6. **Seçim hakkı** — Onay vermeyen öğrenci için alternatif yol (manuel listeye yazılma) olmalı

---

## 📞 KVKK İLETİŞİM VE KAYNAKLAR

- **KVKK Kurumu:** https://www.kvkk.gov.tr
- **VERBİS:** https://verbis.kvkk.gov.tr
- **Rehber Dokümanlar:** https://www.kvkk.gov.tr/Icerik/2036/Rehber-Dokumanlar
- **İhlal Bildirim:** https://www.kvkk.gov.tr/Icerik/6638/Veri-Ihlali-Bildirimi

---

## ✅ ÖZET

KVKK uyumu bir "özellik" değil, **projenin temeli**. Bunu es geçersek:
- 💰 Para cezası (milyonlara çıkabilir)
- 🚫 Sistem durdurma
- 📰 Medyada itibar kaybı
- 🏫 Okullar sözleşmeyi iptal eder
- ⚖️ Bireysel dava riski

Bu nedenle:
1. **İlk aşamada avukat tutun**
2. **Veli onayı olmadan kimseyi kaydetmeyin**
3. **DPA sözleşmeleri imzalanmadan okulla çalışmayın**
4. **Güvenlik pen-test yaptırın**
5. **Siber sigorta alın**

Bu 5 madde olmadan "ilk okul kurulumu" yapılmamalı.