# 🔖 DEVAM NOTU — Yeni Task İçin Bağlam

> **Bu dosya, yeni VS Code workspace'inde (`/Users/ahmetmert/Desktop/Projects/yuz-tanima`) yeni bir task başlattığında ilk okunacak dosyadır.**

---

## 📍 NEREDE KALDIK?

### Yapılan:
1. ✅ Eski RFID yemekhane sistemi analiz edildi
2. ✅ Çok-okullu (multi-tenant SaaS) yüz tanıma + turnike sistemine dönüşüm planlandı
3. ✅ `plan/` klasörüne **13 detaylı doküman** yazıldı (bkz. [`plan/README.md`](README.md))
4. ✅ Yeni klasör oluşturuldu: `/Users/ahmetmert/Desktop/Projects/yuz-tanima`
5. ✅ Git init yapıldı, remote `https://github.com/ahmetmertkabak/yuz-tanima.git` eklendi
6. ✅ plan/ klasörü eski projeden kopyalandı

### Yapılacak (sıradaki adımlar):
1. 🔜 **T0.6.3:** Yeni klasör yapısını oluştur (server/, edge/, docs/, legacy/)
2. 🔜 **T0.6.4:** server/ için temel iskelet (Flask app factory, config, requirements)
3. 🔜 **T0.6.5:** edge/ için temel iskelet (Pi yazılımı)
4. 🔜 **T0.6.6:** .gitignore ve README.md
5. 🔜 İlk commit + push to GitHub
6. 🔜 T1.1-T1.6 — Yeni modelleri yaz (School, User, Person, Device, AccessLog, Snapshot, AuditLog)
7. 🔜 T1.7 — Tenant middleware
8. 🔜 T1.8-T1.9 — PostgreSQL config + migration script

---

## 🎯 PROJE ÖZETİ (30 saniye)

**Ne yapıyoruz?**  
MEB'in okullara getirdiği yüz tanıma + turnike zorunluluğuna uyumlu **çok-okullu SaaS ürünü** geliştiriyoruz.

**Mimari:**
- **Merkezi VPS** (Flask + PostgreSQL + multi-tenant)
- **Her okul için Pi** (kamera + röle + turnike kontrolü)
- **Offline-first:** Pi internet olmadan da çalışır
- **3 panel:** Super Admin (biz), School Admin (okul), Staff (öğretmen)

**Temel Kararlar:**
- Donanım paketi: Pi 4 (4GB) + Logitech C920 + 2ch röle ≈ 9.000 TL/kapı
- Satış: 15-28k TL (3 paket), yıllık yenileme 2.5-6k TL
- Süre: MVP 2 ay, tam sistem 5-6 ay (full-time)
- Yatırım: 80-110k TL (kendin yazarsan)
- **Bakiye sistemi tamamen kaldırıldı** — sadece yoklama/erişim kontrolü
- **RFID çıktı, yüz tanıma girdi**

---

## 📚 KRİTİK DOKÜMANLARI OKU

Yeni task başlatıldığında şu sırayla oku:

1. [`plan/README.md`](README.md) — İndeks
2. [`plan/00_GENEL_BAKIS.md`](00_GENEL_BAKIS.md) — Proje vizyonu
3. [`plan/02_MIMARI.md`](02_MIMARI.md) — Sistem mimarisi
4. [`plan/04_VERITABANI_DEGISIKLIKLERI.md`](04_VERITABANI_DEGISIKLIKLERI.md) — Modeller
5. [`plan/08_GECIS_STRATEJISI.md`](08_GECIS_STRATEJISI.md) — Yeni klasör yapısı
6. [`plan/10_TODO_YOL_HARITASI.md`](10_TODO_YOL_HARITASI.md) — TODO listesi

---

## 🚀 YENİ TASK'TA İLK PROMPT

Yeni VS Code workspace'inde bu prompt ile task başlat:

```
plan/DEVAM_NOTU.md dosyasını oku, ardından plan/10_TODO_YOL_HARITASI.md 
dosyasındaki T0.6.3'ten (yeni klasör yapısı) başlayarak devam et.
```

---

## 📁 BEKLENEN KLASÖR YAPISI (Oluşturulacak)

```
yuz-tanima/
├── plan/                    ✅ Kopyalandı
├── server/                  🔜 Merkezi VPS uygulaması
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── middleware/
│   │   ├── routes/
│   │   │   ├── super_admin/
│   │   │   ├── school_admin/
│   │   │   └── api/
│   │   ├── services/
│   │   ├── templates/
│   │   └── static/
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   └── run.py
│
├── edge/                    🔜 Pi yazılımı (ayrı cihaz, kurulum SD kartına)
│   ├── app/
│   │   ├── config.py
│   │   ├── camera.py
│   │   ├── recognition/
│   │   ├── turnstile.py
│   │   ├── sync_client.py
│   │   └── main.py
│   ├── scripts/
│   ├── systemd/
│   └── requirements.txt
│
├── docs/                    🔜 Teknik dokümantasyon
├── .gitignore               🔜
├── README.md                🔜
└── docker-compose.yml       🔜
```

Detaylı yapı [`08_GECIS_STRATEJISI.md`](08_GECIS_STRATEJISI.md)'de.

---

## 🔗 REFERANS: ESKİ PROJE

Eski kod `~/Desktop/Projects/kart-okuma-sistemi` klasöründe duruyor. Referans olarak kullanılacak dosyalar:

- `app/hardware.py` → yeni `edge/app/` için referans (threading, queue mimarisi)
- `app/models.py` → yeni `server/app/models/` için referans
- `app/routes.py` → yeni `server/app/routes/` için referans (raporlar, auth)
- `app/templates/` → yeni `server/app/templates/` için referans

**UNUTMA:** Eski koddan kopyalama yapacağın zaman o klasörden `cat` veya manuel oku, direkt kopyalamak yerine yeni projenin standartlarına göre yaz.

---

## ✅ KONTROL LİSTESİ (Yeni Task Başlatınca)

- [ ] `pwd` ile klasör doğru mu kontrol et (`.../yuz-tanima` olmalı)
- [ ] `ls` ile plan/ klasörünün olduğunu gör
- [ ] `git remote -v` ile remote'un `yuz-tanima.git` olduğunu doğrula
- [ ] Bu `DEVAM_NOTU.md` dosyasını oku
- [ ] `plan/README.md`'yi oku
- [ ] `plan/10_TODO_YOL_HARITASI.md`'yi oku
- [ ] T0.6.3'ten başla

---

**Son güncelleme:** 2026-04-21  
**Durum:** Planlama tamamlandı, kod yazımına geçiş hazır  
**Aktif TODO:** T0.6.3 (klasör yapısı oluşturma)