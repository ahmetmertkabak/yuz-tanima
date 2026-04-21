# 📚 Planlama Dokümanları — İndeks

Bu klasör, **yemekhane kart okuma sistemini** MEB'in okullara getirdiği **yüz tanıma + turnike zorunluluğuna** uyumlu, **çok-okullu (multi-tenant SaaS) bir ürüne** dönüştürme planını içerir.

Kod yazılmadan önce tüm tasarım kararları, mimari seçimler, iş modeli ve yol haritası bu dokümanlarda netleştirilmiştir.

---

## 🎯 Proje Vizyonu (Çok Kısa)

**Ne yapıyoruz?**  
Okullara yüz tanıma + turnike kontrolü sağlayan bir SaaS ürünü geliştiriyoruz.

**Kime?**  
Türkiye'deki özel okullar, kolejler ve ileride devlet okulları.

**Nasıl?**  
Her okula hazır bir donanım paketi (Raspberry Pi + USB webcam + röle) satıyoruz ve merkezi VPS panelden yönetiyoruz. Okullar kendi subdomain'lerinde kendi verilerini görüyor, biz super admin panelden tümünü yönetiyoruz.

**Mevcut kod ne olacak?**  
Yemekhane sistemindeki RFID ve bakiye mantığı kaldırılacak. Yoklama + raporlama altyapısı korunup geliştirilecek. Yüz tanıma + multi-tenant katmanlar eklenecek.

---

## 📖 Doküman Listesi

Okuma sırası ile:

| # | Dosya | Ne Anlatır? |
|---|---|---|
| 00 | [`00_GENEL_BAKIS.md`](00_GENEL_BAKIS.md) | Proje vizyonu, roller, temel kararlar, ne değişiyor |
| 01 | [`01_DONANIM_SECIMI.md`](01_DONANIM_SECIMI.md) | Pi, kamera, röle, kablolar, paket içeriği ve fiyatları |
| 02 | [`02_MIMARI.md`](02_MIMARI.md) | VPS + Pi + panel mimarisi, offline-first, tenant izolasyonu |
| 03 | [`03_TURNIKE_ENTEGRASYONU.md`](03_TURNIKE_ENTEGRASYONU.md) | Dry contact kablolama, fail-safe, kurulum süreci |
| 04 | [`04_VERITABANI_DEGISIKLIKLERI.md`](04_VERITABANI_DEGISIKLIKLERI.md) | Yeni/silinen/dönüşen modeller, multi-tenant schema |
| 05 | [`05_YUZ_TANIMA.md`](05_YUZ_TANIMA.md) | Kütüphane seçimi, performans, liveness, hybrid mod |
| 06 | [`06_WEB_PANEL_GUNCELLEMELERI.md`](06_WEB_PANEL_GUNCELLEMELERI.md) | Super Admin + School Admin + Staff panelleri |
| 07 | [`07_GUVENLIK_VE_KVKK.md`](07_GUVENLIK_VE_KVKK.md) | KVKK uyum, veli onay, encryption, audit log |
| 08 | [`08_GECIS_STRATEJISI.md`](08_GECIS_STRATEJISI.md) | Mevcut koddan yeni mimariye aşamalı geçiş |
| 09 | [`09_SURE_VE_MALIYET.md`](09_SURE_VE_MALIYET.md) | Faz faz süre, bütçe, break-even analizi |
| 10 | [`10_TODO_YOL_HARITASI.md`](10_TODO_YOL_HARITASI.md) | Hafta hafta somut görevler (T0-T12) |
| 11 | [`11_IS_MODELI.md`](11_IS_MODELI.md) | Paket yapısı, fiyatlar, satış süreci, destek modeli |

---

## ⚡ HIZLI ÖZET (30 Saniye)

| Başlık | Cevap |
|---|---|
| **Mevcut sistemden farkı** | Bakiye/yemek çıkıyor, yüz tanıma + turnike giriyor, multi-tenant oluyor |
| **Donanım** | Pi 4 (4GB) + USB webcam + 2 kanal röle + kasa ≈ 9.000 TL/kapı |
| **Tek okul mu, çok okul mu?** | Çok okul — SaaS modeli, her okul kendi subdomain |
| **Pilot süre** | 2-3 ay (full-time, MVP) |
| **Tam sistem süre** | 5-6 ay (full-time) |
| **İlk yatırım** | ~80-110k TL (sen yazıyorsan) |
| **Okul başı satış** | 15.000-28.000 TL (paket bağlı) |
| **Yıllık yenileme** | 2.500-6.000 TL (pasif gelir) |
| **Break-even** | ~10-15 okul |
| **Offline çalışır mı?** | Evet — Pi lokalde tanıma yapar, internet gelince sync |
| **KVKK?** | Kritik — veli onay formu, DPA, encryption, audit log şart |

---

## 🗺️ MİMARİ (Kuş Bakışı)

```
┌──────────────────────────────────────┐
│   MERKEZİ VPS (yuztanima.com)        │
│   - PostgreSQL (multi-tenant)        │
│   - Super Admin Panel                │
│   - School Admin Panel (subdomains)  │
│   - REST API + WebSocket             │
└────────────┬─────────────────────────┘
             │ HTTPS
             │
    ┌────────┼────────┬────────┐
    │        │        │        │
  Pi #1    Pi #2    Pi #3    Pi #N
  Okul A   Okul B   Okul C   Okul N
```

Her Pi:
- Kamera ile yüz yakalar
- Lokal cache ile eşleştirir
- Turnike açar
- Log'ları VPS'e senkronize eder
- **Offline çalışabilir**

---

## 🚀 CODE MODUNA GEÇMEDEN ÖNCE

Bu planlama dokümanları tamamlandı. Kod yazmaya başlamadan önce:

### İş tarafında kontrol edilmesi gerekenler:
- [ ] Firma kuruluş süreci başlatıldı mı?
- [ ] KVKK avukat görüşmesi yapıldı mı?
- [ ] Pilot okul olmayı kabul edecek okul var mı?
- [ ] Bütçe onaylandı mı? (minimum 80-110k TL)

### Teknik tarafta kontrol edilmesi gerekenler:
- [ ] VPS satın alındı mı?
- [ ] Domain alındı mı? (`yuztanima.com` gibi)
- [ ] Hosting ve DNS setup planı belli mi?
- [ ] GitHub repo açıldı mı?

Bu 8 madde "evet" olduğunda Code moduna geçip kod yazmaya başlanır. [`10_TODO_YOL_HARITASI.md`](10_TODO_YOL_HARITASI.md) ilk görev listesini verir.

---

## 📝 BU DOKÜMANLARI GÜNCEL TUTMA

Planlama dokümanları **yaşayan belgeler**. Geliştirme sırasında:
- Yeni karar alındığında ilgili dosya güncellenir
- Değişen tahminler (süre, fiyat) revize edilir
- Yeni riskler/fırsatlar eklenir
- Deneyimlerden öğrenilenler yazılır

---

## 🎯 HANGİ DOKÜMAN NE ZAMAN OKUNMALI?

| Sen Neredeysen | Şunu Oku |
|---|---|
| İlk defa geliyorsun | 00 + bu README |
| "Ne kadar tutar?" | 01, 09 |
| "Nasıl çalışacak?" | 02, 03, 05 |
| "Kod nereden başlayacak?" | 04, 08 |
| "Panel nasıl görünecek?" | 06 |
| "KVKK'ya uyar mı?" | 07 |
| "Nasıl para kazanırız?" | 11 |
| "Bu hafta ne yapayım?" | 10 |
| Toplam resmi görmek | Sırayla hepsi |

---

## 🔗 İLGİLİ MEVCUT DOKÜMANLAR (Proje Kökünde)

Bu yeni planlamadan önce yazılmış dokümanlar hala değerli:
- [`SISTEM_OZETI.md`](../SISTEM_OZETI.md) — Mevcut RFID sisteminin özeti
- [`KART_OKUMA_AKISI.md`](../KART_OKUMA_AKISI.md) — Mevcut kart okuma akışı (yüz tanımaya uyarlanacak referans)
- [`GELISTIRME_ONERILERI.md`](../GELISTIRME_ONERILERI.md) — Geçmiş geliştirme önerileri

---

## ✅ PLAN TAMAMLANDI

Tüm planlama bölümleri yazıldı. Şimdi yapılacak:

1. **Sen bu dokümanları gözden geçir** (sırayla 00'dan 11'e)
2. **Sorular / düzeltmeler varsa architect modunda tartışırız**
3. **Her şey netleşince Code moduna geçiş yaparız**
4. **[`10_TODO_YOL_HARITASI.md`](10_TODO_YOL_HARITASI.md)'daki T0 görevleriyle başlarız**

Hayırlı olsun! 🚀