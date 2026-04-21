# 🤖 05 - Yüz Tanıma (Face Recognition)

## 🎯 Amaç
Pi tarafında gerçek zamanlı yüz algılama + tanıma yapılacak. 300-1500 kişilik bir okul havuzundan **<1 saniye içinde** kimliği belirleyip turnike açılmalı.

---

## 📚 YÜZ TANIMA TEMEL KAVRAMLAR

### Süreç 3 Aşamadan Oluşur

1. **Face Detection (Algılama)** — "Bu görüntüde yüz var mı? Nerede?"
2. **Face Encoding (Vektörleştirme)** — "Bu yüzü matematiksel olarak ifade et" (128 veya 512 boyutlu vektör)
3. **Face Matching (Karşılaştırma)** — "Bu encoding hangi kayıtlı kişiye benziyor?" (Euclidean distance)

### Önemli Terimler
- **Encoding / Embedding:** Yüzün sayısal parmak izi (örn: 128 float sayıdan oluşan vektör)
- **Tolerance / Threshold:** Karşılaştırma eşiği. Düşük = daha katı (false negative artar), yüksek = daha gevşek (false positive artar)
- **False Positive (FP):** Başka kişiyi biri olarak tanıma — GÜVENLİK AÇIĞI
- **False Negative (FN):** Kayıtlı kişiyi tanımama — KULLANICI DENEYİMİ SORUNU

---

## 🔬 KÜTÜPHANE SEÇENEKLERİ

### Seçenek 1: `face_recognition` (dlib tabanlı) 🥇 Başlangıç için
**GitHub:** [ageitgey/face_recognition](https://github.com/ageitgey/face_recognition)

- **Kullanım kolaylığı:** ⭐⭐⭐⭐⭐
- **Doğruluk:** %99.38 (LFW benchmark)
- **Pi performansı:** Orta (frame başına ~300-500ms)
- **Encoding boyutu:** 128 dim
- **Kurulum:** Biraz uğraştırıcı (dlib'in compile edilmesi gerekir, Pi'da 30-60 dk)

**Örnek kod:**
```python
import face_recognition

# Fotoğrafı yükle
image = face_recognition.load_image_file("person.jpg")

# Yüzleri bul
face_locations = face_recognition.face_locations(image)

# Encoding üret (128 float)
face_encodings = face_recognition.face_encodings(image, face_locations)

# Karşılaştır
matches = face_recognition.compare_faces(
    known_encodings,  # DB'den gelen tüm encoding'ler
    face_encodings[0],
    tolerance=0.6
)
```

**Artı:**
- Çok kolay API
- Türkçe dokümantasyon bol
- Örnek proje çok

**Eksi:**
- Pi'da yavaş (frame başına 300ms+)
- 500+ kişide lineer arama yavaşlar
- 5+ yıllık, yeni model güncellemeleri yok

### Seçenek 2: `InsightFace` (Modern, Production) 🥇🥇 Tavsiye
**GitHub:** [deepinsight/insightface](https://github.com/deepinsight/insightface)

- **Kullanım kolaylığı:** ⭐⭐⭐
- **Doğruluk:** %99.8+ (state-of-the-art)
- **Pi performansı:** Hızlı (~100-200ms) — ONNX runtime ile
- **Encoding boyutu:** 512 dim (daha diskriminatif)
- **Kurulum:** pip install basit, model dosyası indirilir

**Örnek kod:**
```python
import insightface
from insightface.app import FaceAnalysis

app = FaceAnalysis(providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

# Yüzleri tespit + encoding çıkar
faces = app.get(image)

for face in faces:
    embedding = face.normed_embedding  # 512 dim
    bbox = face.bbox                   # x1, y1, x2, y2
```

**Artı:**
- State-of-the-art doğruluk
- Modern mimari (ResNet50, ArcFace loss)
- ONNX → CPU optimizasyon iyi
- Maske + güneş gözlüğü bile destekler
- Aktif geliştiriliyor

**Eksi:**
- Biraz daha fazla bellek
- Model dosyası (~250MB) indirilmeli

### Seçenek 3: `OpenCV DNN + ArcFace` (En Minimal)
- Sadece OpenCV ile çalışır, başka bağımlılık yok
- Kurulum en kolay
- Doğruluk orta (%96-98)
- Özellikle çok düşük kaynaklı cihazlar için

### Seçenek 4: `DeepFace`
- Çok model destekler (VGG-Face, Facenet, ArcFace, Dlib)
- Esnek ama daha yavaş
- Önce denemek için iyi, production için overkill

---

## 🏆 KARAR: Aşamalı Yaklaşım

### Faz 1 (MVP / Pilot): `face_recognition` 
**Neden:** Hızlı başlamak için. API basit, dokümantasyon yaygın. 500 kişiye kadar Pi 4'te yeterli performans verir.

### Faz 2 (Ölçeklendikçe): `InsightFace`
**Neden:** 500+ kişi veya multi-face detection gerekince geçiş. Daha iyi doğruluk + daha hızlı.

**Kod modüler olacak** — kütüphane swap kolay olacak şekilde yazılacak:

```python
# app/recognition/base.py
class FaceRecognizer(ABC):
    @abstractmethod
    def detect_faces(self, frame) -> List[FaceLocation]: ...
    @abstractmethod
    def encode_face(self, frame, location) -> np.ndarray: ...
    @abstractmethod
    def compare(self, encoding1, encoding2) -> float: ...

# app/recognition/dlib_recognizer.py
class DlibFaceRecognizer(FaceRecognizer): ...

# app/recognition/insightface_recognizer.py
class InsightFaceRecognizer(FaceRecognizer): ...
```

Config dosyasından kütüphane seçilebilir. Kütüphane değişirse kod değişmez.

---

## ⚡ PERFORMANS OPTİMİZASYONU

### Sorun: Lineer Arama Yavaş
500 kişilik encoding setinde her karşılaştırma 500 iterasyon demek.

### Çözüm 1: Numpy Vectorization
```python
# Yavaş
matches = [compare(enc, known) for known in all_encodings]

# Hızlı (tüm encoding'ler tek matris)
distances = np.linalg.norm(known_matrix - new_encoding, axis=1)
best_idx = np.argmin(distances)
```
500 kişi için 500ms → 5ms (100x hızlanma).

### Çözüm 2: FAISS (Facebook AI Similarity Search)
Binlerce encoding için vektör arama kütüphanesi.
```python
import faiss

# Index oluştur
index = faiss.IndexFlatL2(128)
index.add(encoding_matrix)  # 10000 kişilik matris

# Arama (milisaniyeler)
distances, indices = index.search(query_encoding, k=1)
```
10.000 kişi için <10ms arama. Okullar için overkill ama ileride iyi olabilir.

### Çözüm 3: Frame Downscaling
Tam çözünürlükte tanıma çok yavaş. Frame'i 1/4 küçült → tanıma 4x hızlanır.
```python
small_frame = cv2.resize(frame, (0,0), fx=0.25, fy=0.25)
```
Sonra konum bulunca orijinal frame'de büyük version'a döndür.

### Çözüm 4: Frame Skip
Her frame'i işlemeye gerek yok. 30fps'de her 5. frame = 6 fps tanıma → yine hızlı, CPU rahat.

### Çözüm 5: Detection Model Değiştirme
`face_recognition` default'ta HOG kullanır (hızlı ama %96). CNN daha doğru (%99.9) ama yavaş. Pi'da HOG kalsın.

---

## 🎯 HEDEF PERFORMANS

### Pi 4 (8GB) 'da Beklenen Değerler

| Metrik | 500 Kişi | 1000 Kişi | 2000 Kişi |
|---|---|---|---|
| Encoding çıkarma | 150-250ms | aynı | aynı |
| Karşılaştırma (numpy) | 2-5ms | 5-10ms | 10-20ms |
| Toplam tanıma süresi | ~250ms | ~300ms | ~350ms |
| + Turnike açma | +50ms | +50ms | +50ms |
| **Kullanıcı bekler** | **~300ms** | **~350ms** | **~400ms** |

Hedef: <1 saniye → kolayca karşılanır.

---

## 🔐 GÜVENLİK: LIVENESS DETECTION

### Sorun: Fotoğraf ile Geçiş
Birisi sınıf arkadaşının telefondaki fotoğrafını kameraya gösterirse sistem kabul edebilir. **Bu ciddi bir güvenlik açığı!**

### Çözümler

#### 1. Blink Detection (Göz Kırpma)
Kısa sürede iki frame: gözler açık → kapalı → açık. Fotoğrafta olmaz.
**Artı:** Basit, hızlı  
**Eksi:** Video kopyası bypass eder

#### 2. Head Pose / Motion
Kullanıcıdan başını hafif sağa/sola döndürmesi istenir. 3D hareket fotoğrafta olmaz.
**Artı:** İyi koruma  
**Eksi:** UX biraz yavaşlar

#### 3. Depth Camera (Intel RealSense, vb.)
3D derinlik bilgisi → fotoğraf düz, gerçek yüz derin.
**Artı:** En güçlü  
**Eksi:** Kamera pahalı (2000+ TL)

#### 4. Texture Analysis
AI modeli "gerçek yüz mü, LCD ekran mı?" ayırt eder.
**Artı:** Otomatik, kullanıcı dokunmaz  
**Eksi:** Model eğitimi gerekir

### Karar
- **Faz 1 (MVP):** Liveness detection yok, sadece yüz tanıma
- **Faz 2 (Pilot tamamlandıktan sonra):** **Blink detection + motion** eklenir
- **Faz 3 (Yüksek güvenlikli okullar):** Depth kamera opsiyonu

---

## 🎨 HYBRID MOD (2FA Benzeri Seçenek)

**Öğrenci no + yüz** kombinasyonu:
1. Ekranda tuş takımı (veya öğrenci numara okuyucu)
2. Öğrenci numarayı girer → o kişinin encoding'i aktif olur
3. Yüz gösterilir → o spesifik encoding ile karşılaştırılır (1:1 match)

**Avantaj:** False positive sıfıra yakın (500 içinden 1 değil, 1 içinden 1)  
**Dezavantaj:** Kullanıcı deneyimi biraz daha yavaş  
**Kullanım:** Opsiyonel, "yüksek güvenlik modu" olarak sunulur

---

## 🎓 EĞİTİM / KAYIT SÜRECİ

### Yüz Kaydetme
Okul admini öğrenci eklerken webcam ile yüz kaydı yapar.

**Önerilen akış:**
1. Öğrenci kameraya bakar
2. Sistem otomatik 3-5 frame yakalar (farklı açılardan)
3. Her frame için encoding üretir
4. **Ortalama encoding** DB'ye kaydedilir (daha tutarlı tanıma)
5. Kalite kontrolü:
   - Yüz net mi? (bulanıklık testi)
   - Sadece 1 yüz mi? (başkası varsa reddet)
   - Gözlük/maske yoksa ideal
   - Yüz merkezi mi?

### Çoklu Fotoğraf ile Robustluk
Farklı açılardan 3-5 fotoğraf → 3-5 encoding. Karşılaştırma sırasında **en yakın mesafe** kullanılır. Bu gözlük, saç kesimi değişikliği gibi durumlara dayanıklılık sağlar.

```python
class Person:
    face_encoding = db.Column(db.LargeBinary)  # Primary (ortalama)
    face_encodings_extra = db.Column(db.JSON)  # Ek encoding'ler
```

---

## 📸 KAMERA KALİTE KRİTERLERİ

Tanıma doğruluğu için frame kalitesi kritik:

| Faktör | Öneri |
|---|---|
| Çözünürlük | 720p minimum, 1080p tercih |
| FPS | 15-30 |
| Işık | Yüze dengeli, karşıdan güneş YOK |
| Mesafe | Yüz kameraya 50-120cm |
| Yüz boyutu (frame içinde) | En az 80x80 pixel |
| Blur | Hareket bulanıklığı yok → 30fps+ gerekli |
| Beyaz dengesi | Doğal ten rengi algılanmalı |

---

## 🧪 TEST KÜTÜPHANESİ

Pilot öncesi test için:
- **LFW (Labeled Faces in the Wild):** 13.000+ ünlü yüzü, benchmark için
- **Kendi test seti:** 20-30 gönüllü, 5 farklı koşul:
  - Normal
  - Gözlüklü
  - Maskeli (ağız+burun)
  - Sakallı/sakalsız
  - Makyajlı (farklı gün)
  - Saç kesimi değişikliği

Her koşulda %95+ doğruluk hedefi.

---

## 🌍 ETİK / BIAS

**Sorun:** Birçok yüz tanıma modeli **belirli ırklar / ten renkleri için daha zayıf** (özellikle koyu tenli kişilerde).

**Türkiye için:** Çoğu öğrenci açık ten — en kötü bias senaryosunda bile iyi çalışır. Ama ideal olan:
- Eğitim setinde çeşitli ten rengi olan model seç
- InsightFace (Asya odaklı ama genel iyi) veya açık model seç
- Bias testi yap (5-10 farklı ten rengi ile)

---

## 🔄 ENCODING SYNC MEKANİZMASI

### VPS → Pi Sync Protokolü

```http
GET /api/v1/device/encodings?since=2025-10-15T10:00:00
X-Device-Key: abc123...

Response:
{
  "updated": [
    {"id": 123, "person_no": "2025001", "name": "Ahmet Y.", 
     "encoding": "base64_encoded_bytes"},
    ...
  ],
  "deleted": [456, 789],  // Silinen person.id listesi
  "last_sync": "2025-10-15T10:30:00"
}
```

Pi her 1 dakikada bir sorar. Sadece değişiklik gelir (incremental sync).

### İlk Senkronizasyon
Yeni Pi kurulduğunda tüm encoding'leri indirir (~500 kişi × 128 float = ~250KB). Birkaç saniye sürer.

### Delta Sync
Sonraki senkronizasyonlarda sadece `updated_at > last_sync` olan kayıtlar gelir. Çok verimli.

---

## 💾 ENCODING DEPOLAMA FORMATI

### PostgreSQL'de
```python
face_encoding = db.Column(db.LargeBinary)  # numpy → bytes

# Yazma
person.face_encoding = encoding_array.tobytes()

# Okuma
encoding_array = np.frombuffer(person.face_encoding, dtype=np.float64).reshape(128)
```

### Pi SQLite'ta
Aynı BLOB formatı, lokalde saklanır. Pi boot'ta RAM'e yükler (hız için).

---

## 📊 MEMORY KULLANIMI

Pi 4 (8GB RAM) için hesap:
- 500 kişi × 128 float × 8 byte = 500KB (ihmal edilebilir)
- 500 kişi × 512 float × 4 byte = 1MB
- face_recognition model: ~400MB RAM
- OpenCV buffer: ~200MB
- Python + Flask: ~100MB
- **Toplam: ~700MB** → 8GB RAM çok çok yeterli

---

## 🔍 SONUÇLAR / ÇIKTILAR

Her tanıma işlemi şunları üretir ve loglar:
```python
{
    "recognized": True,
    "person_id": 123,
    "confidence": 0.89,    # 1.0'a yakın = daha kesin
    "distance": 0.34,       # tolerance altında mı?
    "frame_snapshot": "bytes" if not recognized else None,
    "processing_time_ms": 285}
```

Bu, ileride **tanıma kalitesini monitör etmek** için altın değerinde.

---

## ✅ ÖZET

- **Faz 1:** `face_recognition` (kolay başlangıç)
- **Faz 2:** `InsightFace` (performans/doğruluk için)
- **Pi 4 yeterli:** 500 kişide ~300ms tanıma
- **Numpy vectorization:** karşılaştırma 100x hızlanır
- **Multi-photo enrollment:** farklı açılar için encoding
- **Liveness:** Faz 2'de blink + motion
- **Hybrid mod:** Öğrenci no + yüz opsiyonel
- **KVKK için:** `07_GUVENLIK_VE_KVKK.md`