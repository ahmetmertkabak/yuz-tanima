# ⏱️ 09 - Süre ve Maliyet Tahmini

## 🎯 Özet Tablo

| Metrik | Değer |
|---|---|
| **Toplam geliştirme süresi** | 4-6 ay (full-time), 8-12 ay (part-time) |
| **MVP (ilk okul pilot)** | 2-3 ay (full-time) |
| **İlk yatırım (Stok + Geliştirme)** | ~150-250 bin TL |
| **Aylık işletme maliyeti** | ~5.000-10.000 TL (10 okula kadar) |
| **Okul başı satış fiyatı** | 18.000-28.000 TL (kurulum + 1 yıl) |
| **Yıllık yenileme** | 3.000-5.000 TL (abonelik) |
| **Break-even (başa baş)** | ~15-20 okul satışında |

---

## 📅 GELİŞTİRME SÜRESİ (FAZ FAZ)

### Full-Time Senaryosu (Tek Geliştirici)

| Faz | İş | Süre | Kümülatif |
|---|---|---|---|
| **0. Hazırlık** | Git, klasör, CI/CD, VPS seçimi | 1 hafta | 1 hf |
| **1. Veri Katmanı** | Yeni modeller, PostgreSQL migration, tenant middleware | 2 hafta | 3 hf |
| **2. Super Admin** | Okul yönetimi, cihaz listesi, subdomain/SSL | 2 hafta | 5 hf |
| **3. School Admin** | Dashboard, person CRUD, raporlar, WebSocket feed | 3 hafta | 8 hf |
| **4. Yüz Kayıt UI** | Webcam capture, encoding üretimi, kalite kontrol | 1 hafta | 9 hf |
| **5. API Katmanı** | Device auth, sync endpoint'leri | 2 hafta | 11 hf |
| **6. Pi Edge Node** | Kamera, yüz tanıma, röle, sync client | 3 hafta | 14 hf |
| **7. OTA Update** | Update manager, script'ler | 1 hafta | 15 hf |
| **8. Güvenlik + KVKK** | Encryption, audit log, 2FA, rate limit | 2 hafta | 17 hf |
| **9. Test + Bugfix** | Unit/integration testler, pen-test | 2 hafta | 19 hf |
| **10. Pilot Kurulum** | İlk okul sahada | 2 hafta | 21 hf |
| **11. Pilot İzleme** | Canlı kullanım, iyileştirmeler | 2 hafta | 23 hf |

**Toplam: ~23 hafta ≈ 5.5 ay (full-time)**

### Part-Time Senaryosu (Haftada 20 saat)
Yukarıdaki süreyi **2 ile çarp** → **~11 ay**

### Hızlandırma Senaryosu (2 Geliştirici)
- Biri server tarafı (faz 1-4, 8)
- Diğeri Pi tarafı (faz 6, 7)
- Paralel çalışırsa **~3-4 ay** full-time

### MVP Odaklı (Güvenlik/KVKK Azaltılmış, Tek Okul)

Sadece 1 okulda deneme amaçlı minimal sürüm:

| Faz | Süre |
|---|---|
| Veri katmanı (tenant ama tek okul) | 1 hf |
| School admin paneli | 2 hf |
| Yüz kayıt + tanıma | 2 hf |
| Pi + röle | 2 hf |
| Saha testi | 1 hf |

**MVP: ~8 hafta ≈ 2 ay (full-time)** — Super admin sonra eklenir, multi-tenant sonra aktif olur.

---

## 💰 BAŞLANGIÇ YATIRIMI (Sıfırdan Başlarken)

### Yazılım Geliştirme
| Kalem | Maliyet |
|---|---|
| Geliştirici maaşı/fırsat maliyeti (kendi emeğin) | Fırsat maliyeti |
| Freelance geliştirici (eğer sen yapmayacaksan) | 200.000-400.000 TL |
| Tasarımcı (UI/UX — opsiyonel) | 20.000-40.000 TL |
| KVKK avukat danışmanlığı | 10.000-25.000 TL |
| Pen-test (pilot öncesi) | 15.000-30.000 TL |

### Donanım Stoku (5 Okul İçin Başlangıç)
| Kalem | Maliyet |
|---|---|
| 5 okul için Pi paketleri (5 + 1 yedek) | ~55.000 TL |
| Test ekipmanı (turnike simülatörü, multimetre) | 3.000 TL |
| Kurulum kiti (tornavidalar, lehim, kablolar) | 2.000 TL |

### Altyapı (İlk 12 Ay)
| Kalem | Tutar |
|---|---|
| VPS (Hetzner CPX21) | 400 TL/ay × 12 = 4.800 TL |
| Domain + DNS (Cloudflare) | 300 TL/yıl |
| S3 Storage (self-host MinIO veya AWS) | 0 - 2.000 TL/yıl |
| SSL (Let's Encrypt) | 0 TL |
| Backup storage (Hetzner StorageBox) | 1.200 TL/yıl |

### Hukuki + İşletme
| Kalem | Maliyet |
|---|---|
| Firma kurulum (LTD veya şahıs) | 2.000-5.000 TL |
| VERBİS kaydı | 0 TL |
| KVKK politika dokümantasyonu | Avukat dahil |
| Siber sorumluluk sigortası (yıllık) | 15.000-30.000 TL |

### Toplam İlk Yatırım Senaryoları

| Senaryo | Toplam |
|---|---|
| **Sen kendin yazarsan** (sadece donanım + altyapı + hukuk + sigorta) | **60.000 - 110.000 TL** |
| **Freelance geliştirici** (yukarı + geliştirme) | **250.000 - 450.000 TL** |
| **Minimal MVP (1 okul)** | **20.000 - 35.000 TL** (kendin yazarsan) |

---

## 💵 AYLIK İŞLETME MALİYETİ

### Teknik Altyapı
| Kalem | 1-10 Okul | 10-50 Okul | 50-200 Okul |
|---|---|---|---|
| VPS | 400 TL | 1.500 TL | 5.000 TL |
| Bandwidth | Dahil | 500 TL | 2.000 TL |
| Backup | 100 TL | 300 TL | 1.000 TL |
| Email servis (SendGrid, Mailgun) | 100 TL | 200 TL | 500 TL |
| Monitoring (Sentry, UptimeRobot) | 200 TL | 500 TL | 1.500 TL |

### Destek + Operasyon
| Kalem | 1-10 Okul | 10-50 Okul | 50-200 Okul |
|---|---|---|---|
| Destek personeli | 0 (sen) | 20.000 TL (1 kişi) | 60.000 TL (3 kişi) |
| Saha teknisyen ziyareti | Gerektiğinde | Yılda 2x/okul | Düzenli |
| Telefon/internet | 300 TL | 800 TL | 2.000 TL |

### Yasal + Sigorta
| Kalem | Aylık |
|---|---|
| Muhasebeci | 1.500-3.000 TL |
| Avukat retainer | 2.000-5.000 TL |
| Sigorta (yıllık / 12) | 1.500-2.500 TL |

### Toplam
- **1-10 okul:** ~5.000-10.000 TL/ay
- **10-50 okul:** ~30.000-45.000 TL/ay
- **50-200 okul:** ~100.000-150.000 TL/ay

---

## 💸 OKUL BAŞI DETAYLI MALIYET VE KAR

### Bir Satış (1 Okul, 1 Kapı)

**Maliyet tarafı:**
| Kalem | Tutar |
|---|---|
| Donanım (standart paket) | 9.000 TL |
| Kurulum işçiliği (1 gün, teknisyen) | 2.000 TL |
| Yol + konaklama (okul uzaksa) | 0-3.000 TL |
| Amortize yazılım geliştirme payı | 500 TL |
| Amortize pazarlama/satış maliyeti | 1.000 TL |
| **Toplam Maliyet** | **~12.500-15.500 TL** |

**Gelir tarafı:**
| Paket | Satış Fiyatı |
|---|---|
| Ekonomik (C270 + basit kutu) | 15.000-18.000 TL |
| Standart (C920 + UPS) | 20.000-22.000 TL |
| Premium (+ 3.5" ekran) | 25.000-28.000 TL |

**Kar marjı:**
- Ekonomik: ~3.000-5.000 TL (%20-30)
- Standart: ~6.500-9.500 TL (%40-45)
- Premium: ~10.000-15.000 TL (%50-55)

### Ek Kapı Aynı Okulda
- Kurulum işçiliği: 500 TL (aynı gün, kısa)
- Donanım: ~9.000 TL
- Satış: ~14.000-18.000 TL
- Kar: ~4.500-8.000 TL

### Yıllık Yenileme (Abonelik)
- Gider tarafı (okul başı): ~300-500 TL/yıl (VPS payı, destek)
- Satış: 3.000-5.000 TL/yıl
- **Kar: ~2.500-4.500 TL/yıl (saf kar, çok yüksek marj!)**

Bu, uzun vadede en önemli gelir kalemi — sürekli cash flow.

---

## 📊 BREAK-EVEN (BAŞA BAŞ) ANALİZİ

### Senaryo 1: Kendin Yazıyorsun, Minimum Yatırım (~80.000 TL)

| Satış | Kümülatif Kar | Durum |
|---|---|---|
| 1 okul | 8.000 TL | -72.000 TL |
| 5 okul | 40.000 TL | -40.000 TL |
| 10 okul | 80.000 TL | **0 TL ✅ BREAK-EVEN** |
| 20 okul | 160.000 TL | +80.000 TL |
| 50 okul | 400.000 TL | +320.000 TL |

**İlk 10 okul = yatırımı kurtarır.**

### Senaryo 2: Freelance Geliştirici (~350.000 TL)

| Satış | Kümülatif Kar | Durum |
|---|---|---|
| 10 okul | 80.000 TL | -270.000 TL |
| 30 okul | 240.000 TL | -110.000 TL |
| 45 okul | 360.000 TL | **0 TL ✅ BREAK-EVEN** |
| 100 okul | 800.000 TL | +450.000 TL |

Daha uzun vadeli, daha büyük ölçek gerekir.

### 2. Yıldan İtibaren Recurring Revenue (Sürekli Gelir)
- 50 okul × 4.000 TL (yenileme) = **200.000 TL/yıl pasif gelir**
- 100 okul × 4.000 TL = **400.000 TL/yıl**
- 200 okul × 4.000 TL = **800.000 TL/yıl**

Yenileme geliri yıllara yayılınca **işletme maliyetini karşılar + kar bırakır**.

---

## 🎯 REALİST HEDEF SCENARIOSU

### 1. Yıl: Pilot + Kuruluş
- Ay 0-6: Geliştirme
- Ay 6-9: Pilot + iyileştirme (1-2 okul)
- Ay 9-12: İlk satışlar (3-5 okul)

**1. yıl sonunda:** 5-8 okul, ~100.000-160.000 TL gelir, break-even yaklaşıyor veya geçti

### 2. Yıl: Büyüme
- Pazarlama + referans satışı
- Her ay 2-4 okul ekle
- Yıl sonu: 25-40 okul

**2. yıl sonunda:** Kümülatif gelir 500.000-800.000 TL, sürekli gelir başladı

### 3. Yıl: Ölçekleme
- Personel al (destek + satış)
- 80-150 okul hedefi

**3. yıl sonunda:** Yıllık 1.5-3 milyon TL gelir

---

## 📈 GİZLİ MALIYETLER (DİKKAT!)

Bunlar kolayca gözden kaçar, bütçeye eklenmeli:

### 1. Teknik Borç / Bug'lar
- Canlıda bir sorun çıkar → acil düzeltme gerekir
- **Bütçe:** ~%10-15 ek süre/maliyet

### 2. Donanım Arızası
- Pi'lar 3-5 yıl dayanır ama arıza olur
- **Bütçe:** Okul başı yılda 500-1.000 TL rezerv

### 3. Müşteri Destek Saatleri
- "Bizim Pi offline", "Öğrenci tanımıyor" gibi
- **İlk yıl:** Saatlerce telefon desteği
- **Bütçe:** Haftalık 5-10 saat

### 4. Saha Ziyaretleri
- Kameralı kurulum uzaktan çalışmaz
- Kurulum + bakım + sorun giderme
- **Bütçe:** Yol + konaklama + gün (2.000-5.000 TL/ziyaret)

### 5. Pazarlama
- Okullara ulaşmak kolay değil
- Referans + demo + sunum gerekir
- **Bütçe:** İlk yıl 20.000-50.000 TL (web site, broşür, fuar)

### 6. Yasal + İhtilaf
- Yanlış tanıma → veli şikayet → KVKK başvurusu
- Savunma masrafları olabilir
- **Sigorta + avukat retainer önemli**

### 7. Rakipler
- Hikvision, ZKTeco gibi Çin markaları rekabet getirir
- Fiyatları düşük olabilir
- **Bizim farkımız:** Türkçe destek, yerinde kurulum, eğitim sistemine özel

---

## 🎲 SENARYO KARŞILAŞTIRMA

### Senaryo A: Solo Entrepreneur (Sen Yazıyorsun)
- Yatırım: 80.000 TL
- Süre: 6 ay geliştirme
- Risk: Orta (teknik risk sende)
- Ölçek: 1 yılda 5-10 okul

### Senaryo B: Freelance + Sen Yönetim
- Yatırım: 350.000 TL
- Süre: 4 ay geliştirme
- Risk: Yüksek (para batabilir)
- Ölçek: 1 yılda 10-20 okul

### Senaryo C: MVP Lansmanı (Minimal)
- Yatırım: 25.000 TL
- Süre: 2 ay MVP
- Risk: Düşük
- Ölçek: 1 okulla başla, kazanç olursa geliştir

**Önerim: Senaryo C ile başla, 1 okul pilot ile PMF (product-market fit) kanıtla, sonra Senaryo A'ya geçiş.**

---

## 💡 AĞIRLIK MALİYET OPTİMİZASYONLARI

### 1. Pi 4 Yerine Pi 5 (İleride)
- Pi 5 stoklar dolunca 3.500 TL'ye düşer
- %30 daha hızlı, aynı fiyata

### 2. Toptan Alım Indirimi
- 10 adet Pi = %15 indirim
- 50 adet = %25 indirim

### 3. Kamera Alternatifi
- C270 yerine Çin marka (risk var ama ~%50 ucuz)
- Güvenilirlik kötüyse saha desteği maliyeti fiyat farkını siler → C270/C920 kalsın

### 4. VPS Optimizasyonu
- Hetzner auction server (%30-50 ucuz, 1 vCPU az)
- 20 okul ile test edilebilir

### 5. Self-Hosted vs SaaS Tool'lar
- Monitoring: Grafana self-host (ücretsiz) vs Datadog (pahalı)
- Email: Postal self-host vs SendGrid
- **Self-host iyi tercih** (uzaktan bilgi gerekir ama öğrenilir)

---

## 📌 KRİTİK KARAR NOKTALARI

### Şimdi Karar Vermen Gerekenler
1. **Geliştirmeyi sen mi yapacaksın yoksa freelance mı?** (80k vs 350k fark)
2. **İlk yıl kaç okul hedefliyorsun?** (tutkun ölçeği belirler)
3. **Tam zamanlı mı çalışacaksın?** (tam zamanlı = 2x hızlı)
4. **Hukuki süreç için bütçen var mı?** (KVKK avukat = olmazsa olmaz)
5. **Pazarlama yeteneğin var mı?** (yazılım + satış ayrı işler)

### İlk 90 Günde Mutlaka
- Firma kur (LTD veya şahıs şirketi)
- KVKK avukat ile görüş
- VERBİS kaydı başlat
- Siber sigorta teklifi al
- Hosting + domain satın al
- GitHub private repo kur
- Mimari dokümanlarını sonlandır (bu klasör!)

### İlk 180 Günde
- MVP'yi bitir
- 1 okul pilot için tarafları tamam et
- Kurulum kılavuzu yaz
- Fiyatlandırma netleştir
- Sözleşme şablonları hazırla

---

## 📋 ÖZET

| Soru | Cevap |
|---|---|
| Ne kadar sürer? | MVP: 2 ay, tam sistem: 5-6 ay (full-time) |
| Ne kadar para? | MVP: 25k TL, tam sistem: 80-110k TL (sen yazıyorsan) |
| Ne zaman kar? | MVP: 3 okul sonra, tam: 10-15 okul sonra |
| Yıllık gelir potansiyeli? | 50 okul = 250k yenileme + 800k yeni satış = 1 milyon+ |
| Büyük risk? | KVKK ihlali, donanım arızası, müşteri desteği yoğunluğu |
| En iyi strateji? | Önce 1 okulda MVP kanıtla, sonra ölçekle |

Sonraki: [`10_TODO_YOL_HARITASI.md`](10_TODO_YOL_HARITASI.md) — Adım adım yapılacaklar listesi.
