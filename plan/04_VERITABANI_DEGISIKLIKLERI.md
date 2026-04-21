# 🗄️ 04 - Veritabanı Değişiklikleri (Multi-Tenant Schema)

## 🎯 Temel Değişiklik

**Eski sistem:** Tek SQLite DB, tek okula özel, bakiye/yemek odaklı.  
**Yeni sistem:** PostgreSQL multi-tenant, her tabloda `school_id` ile izole.

---

## 🔄 DÖNÜŞÜM ÖZET TABLOSU

| Eski Model | Yeni Model | Durum |
|---|---|---|
| [`User`](app/models.py:14) | `User` + `Role` | 🔄 Genişletildi (multi-role) |
| [`Student`](app/models.py:25) | `Person` | 🔄 Dönüştü (öğrenci+öğretmen birleşik) |
| [`Attendance`](app/models.py:78) | `AccessLog` | 🔄 Dönüştü (daha zengin) |
| [`Transaction`](app/models.py:68) | - | ❌ Silindi |
| - | `School` | 🆕 Yeni (tenant tablosu) |
| - | `Device` | 🆕 Yeni (Pi cihazları) |
| - | `Snapshot` | 🆕 Yeni (tanımayan yüzler) |
| - | `SyncQueue` | 🆕 Pi'da lokal |

---

## 🆕 YENİ MODELLER

### 1. `School` (Tenant = Okul)
```python
class School(db.Model):
    __tablename__ = 'schools'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)  
    # örn: "ali-pasa-lisesi" → ali-pasa-lisesi.yuztanima.com
    
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    
    # Abonelik
    subscription_status = db.Column(db.String(20), default='trial')  
    # 'trial', 'active', 'expired', 'suspended'
    subscription_expires_at = db.Column(db.DateTime)
    max_devices = db.Column(db.Integer, default=1)
    max_persons = db.Column(db.Integer, default=500)
    
    # Ayarlar
    timezone = db.Column(db.String(50), default='Europe/Istanbul')
    recognition_tolerance = db.Column(db.Float, default=0.6)  
    # Düşük = daha katı, yüksek = daha gevşek
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    users = db.relationship('User', backref='school', cascade='all, delete-orphan')
    persons = db.relationship('Person', backref='school', cascade='all, delete-orphan')
    devices = db.relationship('Device', backref='school', cascade='all, delete-orphan')
```

### 2. `User` (Güncellendi — Multi-Role)
```python
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256))
    full_name = db.Column(db.String(100))
    
    # 🆕 Role ve tenant
    role = db.Column(db.String(20), nullable=False)  
    # 'super_admin', 'school_admin', 'school_staff', 'viewer'
    
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id', ondelete='CASCADE'), 
                          nullable=True)  # super_admin için NULL
    
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İndeksler
    __table_args__ = (
        db.UniqueConstraint('school_id', 'username', name='uq_school_username'),
        db.UniqueConstraint('school_id', 'email', name='uq_school_email'),
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def can_manage_devices(self):
        return self.role in ('super_admin', 'school_admin')
```

**Not:** Farklı okullardaki iki kullanıcı aynı username'i alabilir ama aynı okul içinde unique.

### 3. `Person` (Student'ın Yerini Aldı)
```python
class Person(db.Model):
    __tablename__ = 'persons'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    
    # Kimlik bilgileri
    person_no = db.Column(db.String(30), nullable=False)  # öğrenci no / sicil no
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  
    # 'student', 'teacher', 'staff', 'manager'
    
    class_name = db.Column(db.String(30), nullable=True)  # "9-A", "Öğretmen" vb.
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    parent_phone = db.Column(db.String(20), nullable=True)  # veli
    
    # Yüz tanıma verileri
    face_encoding = db.Column(db.LargeBinary, nullable=True)  
    # Pickle veya numpy bytes (128 veya 512 dim vektör)
    face_photo_path = db.Column(db.String(255), nullable=True)  
    # S3/MinIO yolu
    face_updated_at = db.Column(db.DateTime, nullable=True)
    
    # Erişim kontrol
    access_granted = db.Column(db.Boolean, default=True)  
    # Bazen disiplin vb. için geçici kapatma
    access_schedule = db.Column(db.JSON, nullable=True)  
    # Örn: {"mon": ["08:00-17:00"], "sat": []}
    
    # KVKK
    consent_given = db.Column(db.Boolean, default=False)
    consent_date = db.Column(db.DateTime, nullable=True)
    consent_document_path = db.Column(db.String(255), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    access_logs = db.relationship('AccessLog', backref='person', 
                                   cascade='all, delete-orphan')
    
    # İndeksler (multi-tenant için kritik!)
    __table_args__ = (
        db.UniqueConstraint('school_id', 'person_no', name='uq_school_person_no'),
        db.Index('ix_persons_school_active', 'school_id', 'is_active'),
    )
```

### 4. `Device` (Pi Cihazları)
```python
class Device(db.Model):
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    
    # Cihaz kimliği
    device_name = db.Column(db.String(100), nullable=False)  # "Ana Giriş"
    location = db.Column(db.String(200))  # "A Blok Zemin Kat"
    description = db.Column(db.Text)
    
    # Auth
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    # Pi bu key ile authentike olur
    
    # Yapılandırma
    direction_mode = db.Column(db.String(10), default='bidirectional')  
    # 'in_only', 'out_only', 'bidirectional'
    turnstile_pulse_ms = db.Column(db.Integer, default=1000)
    
    # Durum
    is_active = db.Column(db.Boolean, default=True)
    last_heartbeat = db.Column(db.DateTime, nullable=True)
    last_ip = db.Column(db.String(45), nullable=True)
    firmware_version = db.Column(db.String(20), nullable=True)
    
    # İstatistik
    cpu_percent = db.Column(db.Float, nullable=True)
    memory_percent = db.Column(db.Float, nullable=True)
    disk_percent = db.Column(db.Float, nullable=True)
    uptime_seconds = db.Column(db.Integer, nullable=True)
    
    # Kurulum
    installed_at = db.Column(db.DateTime, nullable=True)
    installed_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    access_logs = db.relationship('AccessLog', backref='device')
    
    __table_args__ = (
        db.UniqueConstraint('school_id', 'device_name', name='uq_school_device_name'),
    )
    
    @property
    def is_online(self):
        if not self.last_heartbeat:
            return False
        return (datetime.utcnow() - self.last_heartbeat).total_seconds() < 90
```

### 5. `AccessLog` (Attendance'ın Yerini Aldı)
```python
class AccessLog(db.Model):
    __tablename__ = 'access_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id', ondelete='SET NULL'),
                          nullable=True, index=True)
    # NULL olabilir: tanınamayan kişi durumu
    
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='SET NULL'),
                          nullable=True)
    
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, 
                          index=True)
    direction = db.Column(db.String(10))  # 'in', 'out', 'unknown'
    
    # Tanıma detayları
    recognition_confidence = db.Column(db.Float, nullable=True)  # 0.0-1.0
    granted = db.Column(db.Boolean, default=False)
    # True: turnike açıldı, False: reddedildi
    
    denial_reason = db.Column(db.String(100), nullable=True)
    # 'unknown_person', 'access_restricted', 'out_of_schedule', 'system_error'
    
    snapshot_path = db.Column(db.String(255), nullable=True)
    # Tanımayan veya şüpheli durumlar için
    
    # Meta
    note = db.Column(db.String(500))
    
    __table_args__ = (
        db.Index('ix_access_logs_school_timestamp', 'school_id', 'timestamp'),
        db.Index('ix_access_logs_school_person', 'school_id', 'person_id', 'timestamp'),
    )
```

### 6. `Snapshot` (Tanınmayan Yüzler)
```python
class Snapshot(db.Model):
    __tablename__ = 'snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))
    access_log_id = db.Column(db.Integer, db.ForeignKey('access_logs.id'), nullable=True)
    
    image_path = db.Column(db.String(255), nullable=False)  # S3 yolu
    face_encoding = db.Column(db.LargeBinary, nullable=True)  # karşılaştırma için
    best_match_person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), 
                                      nullable=True)
    best_match_confidence = db.Column(db.Float, nullable=True)
    
    reviewed = db.Column(db.Boolean, default=False)
    review_note = db.Column(db.Text)
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # KVKK: belirli süre sonra otomatik silinmeli
    expires_at = db.Column(db.DateTime, nullable=True)
```

### 7. `AuditLog` (Admin İşlemleri — KVKK için)
```python
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    action = db.Column(db.String(50), nullable=False)  
    # 'person_create', 'person_delete', 'face_update', 'device_reboot', vb.
    resource_type = db.Column(db.String(30))
    resource_id = db.Column(db.Integer)
    
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    details = db.Column(db.JSON)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
```

---

## 📐 ER DİYAGRAMI

```
┌──────────────┐
│   School     │◄──────────────┐
│ (Tenant)     │               │
└──────┬───────┘               │
       │1:N                    │
       ├─────────┐             │
       │         │             │
       ▼         ▼             │
  ┌────────┐  ┌────────┐      │
  │  User  │  │Person  │      │
  └────────┘  └───┬────┘      │
                  │1:N         │
                  ▼            │
              ┌────────┐       │
              │Access  │       │
              │  Log   │◄──┐   │
              └────────┘   │   │
                           │N:1│
                           ▼   │
                      ┌────────┴┐
                      │ Device  │
                      └─────────┘
                           │
                           │1:N
                           ▼
                      ┌─────────┐
                      │Snapshot │
                      └─────────┘
```

---

## 🔒 MIDDLEWARE: TENANT OTOMATİK FİLTRELEME

Her sorguda otomatik `school_id` filtresi eklenir. Böylece kod her yerde `.filter_by(school_id=g.school_id)` yazmak zorunda kalmaz.

```python
from flask import g
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

# Tenant-scoped modellerin listesi
TENANT_MODELS = [Person, Device, AccessLog, Snapshot, AuditLog]

@event.listens_for(Session, "do_orm_execute")
def filter_by_tenant(execute_state):
    # Sadece SELECT'leri filtrele
    if not execute_state.is_select:
        return
    
    # SuperAdmin tüm tenant'ları görebilir
    if g.get('user_role') == 'super_admin' and g.get('bypass_tenant_filter'):
        return
    
    if g.get('school_id') is None:
        return
    
    # Her tenant model için kriter ekle
    for Model in TENANT_MODELS:
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                Model,
                Model.school_id == g.school_id,
                include_aliases=True
            )
        )
```

---

## 🔑 MIGRATION PLANI

### Aşama 1: Yeni Modeller Eklenir (Breaking Change Yok)
```python
# 1. School modelini ekle
# 2. Device, AccessLog, Snapshot, AuditLog ekle
# 3. User'a role + school_id kolonları ekle (nullable)
# 4. Default school oluştur ("Legacy School")
# 5. Var olan tüm User'ları legacy school'a ata
```

### Aşama 2: Veri Taşıma
```python
# Mevcut Student → Person
for student in Student.query.all():
    person = Person(
        school_id=legacy_school.id,
        person_no=student.student_no,
        full_name=student.name,
        role='student',
        # class_name'i ayrı bir alandan al
    )
    db.session.add(person)

# Mevcut Attendance → AccessLog
for attendance in Attendance.query.all():
    log = AccessLog(
        school_id=legacy_school.id,
        person_id=person_mapping[attendance.student_id],
        timestamp=attendance.created_at,
        direction='in',
        granted=True,
    )
    db.session.add(log)
```

### Aşama 3: Eski Modelleri Kaldır
```python
# 1. Transaction tablosunu drop
# 2. Student → eski kalıyor (geçiş süresi için)
# 3. Attendance → eski kalıyor
# 4. Balance, rfid_card kolonlarını Person'da opsiyonel tut (ileride kaldır)
```

### Aşama 4: Temiz Versiyon
```python
# Eski Student, Attendance, Transaction tabloları kaldırılır
# Sadece yeni modeller kalır
```

---

## 📊 ÖRNEK QUERY'LER

### SchoolAdmin Dashboard (Bugün Kim Girdi?)
```python
today = datetime.now().date()
logs = AccessLog.query.filter(
    AccessLog.timestamp >= today,
    AccessLog.granted == True,
).order_by(AccessLog.timestamp.desc()).all()
# school_id otomatik middleware ile filtrelenir
```

### Bugün Gelmeyen Öğrenciler
```python
today = datetime.now().date()
present_person_ids = db.session.query(AccessLog.person_id).filter(
    AccessLog.timestamp >= today,
    AccessLog.granted == True,
).distinct().subquery()

absent = Person.query.filter(
    Person.role == 'student',
    Person.is_active == True,
    ~Person.id.in_(present_person_ids),
).all()
```

### SuperAdmin — Tüm Okullar Özeti
```python
g.bypass_tenant_filter = True  # sadece SuperAdmin için
schools_summary = db.session.query(
    School,
    db.func.count(Person.id).label('person_count'),
    db.func.count(Device.id).label('device_count'),
).outerjoin(Person).outerjoin(Device).group_by(School.id).all()
```

---

## 🗄️ PI TARAFI (Lokal SQLite)

Pi'daki lokal cache ayrı bir şema — basit ve hızlı:

```sql
-- Persons cache (VPS'ten sync edilir)
CREATE TABLE persons_cache (
    id INTEGER PRIMARY KEY,
    server_id INTEGER NOT NULL,  -- VPS'teki Person.id
    person_no TEXT,
    full_name TEXT NOT NULL,
    face_encoding BLOB NOT NULL,
    is_active INTEGER DEFAULT 1,
    access_granted INTEGER DEFAULT 1,
    synced_at TIMESTAMP
);

CREATE INDEX idx_persons_active ON persons_cache(is_active);

-- Pending access logs (VPS'e gönderilecek)
CREATE TABLE access_logs_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_server_id INTEGER,  -- NULL = unknown
    timestamp TIMESTAMP NOT NULL,
    direction TEXT,
    confidence REAL,
    granted INTEGER,
    denial_reason TEXT,
    snapshot_filename TEXT,
    synced INTEGER DEFAULT 0,
    sync_attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pending_synced ON access_logs_pending(synced);

-- Device config
CREATE TABLE device_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP
);

-- Örnek config
INSERT INTO device_config VALUES 
    ('last_encoding_sync', '2025-10-15T10:00:00'),
    ('recognition_tolerance', '0.6'),
    ('turnstile_pulse_ms', '1000');
```

---

## 📦 POSTGRESQL OPTIMIZASYONU

### Partitioning (İleride Büyüdükçe)

`access_logs` tablosu yıllarca büyüyecek. Tarihsel partitioning öneririm:

```sql
CREATE TABLE access_logs (
    id BIGSERIAL,
    school_id INT NOT NULL,
    person_id INT,
    timestamp TIMESTAMP NOT NULL,
    -- ...
) PARTITION BY RANGE (timestamp);

CREATE TABLE access_logs_2025 PARTITION OF access_logs
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE access_logs_2026 PARTITION OF access_logs
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
```

Bu, 500 okul × 500 kişi × 2 geçiş/gün × 200 gün = **100 milyon satır/yıl**. Partitioning şart.

### Indexler (Kritik!)
```sql
CREATE INDEX ix_persons_school_id ON persons(school_id) WHERE is_active = TRUE;
CREATE INDEX ix_access_logs_school_timestamp ON access_logs(school_id, timestamp DESC);
CREATE INDEX ix_devices_last_heartbeat ON devices(last_heartbeat);
```

---

## ✅ ÖZET

- **7 yeni model** (School, User güncellendi, Person, Device, AccessLog, Snapshot, AuditLog)
- **3 model silindi** (Transaction, eski Student, eski Attendance — geçiş sonrası)
- **Her tabloda `school_id`** → tenant izolasyonu
- **Middleware ile otomatik filtreleme** → kod temiz kalır
- **Pi lokal SQLite** → offline çalışma
- **Partitioning ile ölçeklenir** → milyonlarca kayıt

Migration adımları [`08_GECIS_STRATEJISI.md`](08_GECIS_STRATEJISI.md)'nde detaylı anlatılıyor.