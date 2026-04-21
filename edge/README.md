# Edge — Raspberry Pi Yüz Tanıma Node

Her okula yerleştirilen **turnike yanı cihaz**. Kamera + yüz tanıma + röle
kontrolü + offline cache + VPS senkronizasyonu.

## 🎯 Ne Yapar?

1. USB kameradan sürekli frame alır
2. Tanıdığı yüz için turnike rölesine kısa bir pulse gönderir
3. Tüm geçişleri lokal SQLite'a yazar
4. Arka planda VPS ile senkronize olur (heartbeat, encoding sync, log sync)
5. İnternet kesilirse **çalışmaya devam eder** — bağlantı gelince birikmiş logları yükler

## 🧱 Mimari

```
edge/
├── app/
│   ├── main.py              # Orchestrator (systemd entrypoint)
│   ├── config.py            # Pydantic settings (/etc/yuz-tanima/edge.env)
│   ├── camera.py            # Threaded USB webcam wrapper
│   ├── recognition/
│   │   ├── base.py              # Abstract Recognizer
│   │   ├── dlib_recognizer.py   # (T6.3) face_recognition
│   │   └── insightface_recognizer.py  # (Faz 2)
│   ├── turnstile.py         # Röle kontrolü (gpiozero, fail-safe)
│   ├── display.py           # (T6.6) LCD mesajları
│   ├── buzzer.py            # (T6.7) Sesli geri bildirim
│   ├── local_db.py          # SQLite cache
│   ├── hmac_signer.py       # API istekleri için HMAC-SHA256 imza
│   ├── sync_client.py       # VPS REST API client
│   ├── update_manager.py    # (T7) OTA
│   └── logging_setup.py     # JSON yapılandırılmış log
├── scripts/
│   ├── install.sh           # Pi'ya ilk kurulum
│   └── provision.sh         # Okulla eşleştirme
├── systemd/
│   └── yuz-tanima-edge.service
└── requirements.txt
```

## 🔧 Pi Üzerinde Kurulum

```bash
# SSH'lanmış Pi üzerinde:
curl -fsSL https://raw.githubusercontent.com/ahmetmertkabak/yuz-tanima/main/edge/scripts/install.sh | sudo bash
sudo bash /opt/yuz-tanima/edge/scripts/provision.sh
# → DEVICE_ID, SCHOOL_ID, API_KEY girilir
# Servis otomatik start olur; logları izle:
sudo journalctl -u yuz-tanima-edge -f
```

## 💻 Local Dev (macOS / Linux)

```bash
cd edge
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt    # RPi.GPIO/gpiozero otomatik skip edilir
cp .env.example .env
python -m app.main                 # simülasyon modu (GPIO yok)
```

## 🔐 Güvenlik

- `API_KEY` ve `DEVICE_ID` sadece `/etc/yuz-tanima/edge.env` içinde, mod `600`
- Tüm API çağrıları **HMAC-SHA256** ile imzalanır (bkz. [`app/hmac_signer.py`](app/hmac_signer.py:1))
- Fail-safe GPIO: hata durumunda turnike **kilitli kalır**
- Systemd unit sistem koruma bayraklarıyla çalışır (`NoNewPrivileges`, `ProtectSystem=strict`)

## 🗺️ Yol Haritası

Detaylı görevler için kök dizindeki [`../plan/10_TODO_YOL_HARITASI.md`](../plan/10_TODO_YOL_HARITASI.md:210) (Hafta 11–13).