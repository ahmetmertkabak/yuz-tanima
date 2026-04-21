"""
Seed the local dev database with a realistic demo tenant.

Creates:
  - 1 Super Admin      (admin@demo.local / demo1234)
  - 1 School           (Demo Lisesi, subdomain: demo)
  - 1 School Admin     (admin@demo.local / demo1234 under the Demo school)
  - 30 Students split across 3 classes (9-A, 9-B, 10-A) with consent granted
  - 2 Teachers
  - 2 Devices (Ana Giriş, Arka Giriş) with plaintext API keys printed at end
  - 120 AccessLog rows spanning the last 7 days

Usage:
    cd server
    source .venv/bin/activate
    python -m scripts.demo_seed

Reruns are idempotent — re-seeds only if the tenant doesn't exist.
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    AccessDirection,
    AccessLog,
    AccessOutcome,
    ConsentStatus,
    Device,
    DeviceDirectionMode,
    Person,
    PersonRole,
    School,
    SubscriptionStatus,
    User,
    UserRole,
)


FIRST_NAMES = [
    "Ahmet", "Ayşe", "Mehmet", "Fatma", "Ali", "Zeynep", "Mustafa",
    "Elif", "Hasan", "Hatice", "İbrahim", "Meryem", "Emre", "Büşra",
    "Yusuf", "Esra", "Kerem", "Selin", "Can", "Deniz", "Arda", "Nisa",
    "Oğuz", "Beren", "Eren", "Melisa", "Berkay", "Ecrin", "Tarık", "Ela"]

LAST_NAMES = [
    "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım",
    "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan",
    "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek", "Taş", "Polat"]


def _random_name(seed: int) -> str:
    rng = random.Random(seed)
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _random_encoding(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(loc=0, scale=0.05, size=128).astype(np.float32)


def seed() -> dict:
    app = create_app("development")
    with app.app_context():
        # ---- Super admin ----
        super_user = (
            db.session.query(User)
            .filter(User.role == UserRole.SUPER_ADMIN.value)
            .first()
        )
        if super_user is None:
            super_user = User(
                username="super",
                email="super@demo.local",
                full_name="Platform Yöneticisi",
                role=UserRole.SUPER_ADMIN.value,
                school_id=None,
                is_active=True,
            )
            super_user.set_password("demo1234")
            db.session.add(super_user)
            print("✓ Super admin created: super@demo.local / demo1234")
        else:
            print("↺ Super admin exists")

        # ---- School ----
        school = db.session.query(School).filter_by(subdomain="demo").first()
        if school is None:
            school = School(
                name="Demo Lisesi",
                subdomain="demo",
                contact_name="Okul Müdürü",
                contact_email="mudur@demolisesi.k12.tr",
                phone="0212 555 00 00",
                max_devices=5,
                max_persons=500,
                subscription_status=SubscriptionStatus.ACTIVE.value,
                timezone="Europe/Istanbul",
                recognition_tolerance=0.55,
                is_active=True,
            )
            db.session.add(school)
            db.session.flush()
            print(f"✓ School created: {school.name} (id={school.id}, subdomain={school.subdomain})")
        else:
            print(f"↺ School exists (id={school.id})")

        # ---- School admin ----
        school_admin = (
            db.session.query(User)
            .filter(User.school_id == school.id, User.role == UserRole.SCHOOL_ADMIN.value)
            .first()
        )
        if school_admin is None:
            school_admin = User(
                username="admin",
                email="admin@demo.local",
                full_name="Okul Yöneticisi",
                role=UserRole.SCHOOL_ADMIN.value,
                school_id=school.id,
                is_active=True,
            )
            school_admin.set_password("demo1234")
            db.session.add(school_admin)
            print("✓ School admin created: admin@demo.local / demo1234")

        # ---- Persons (students + teachers) ----
        existing_count = (
            db.session.query(Person).filter_by(school_id=school.id).count()
        )
        persons: list[Person] = []
        if existing_count < 30:
            classes = ["9-A", "9-B", "10-A"]
            for i in range(1, 31):
                p = Person(
                    school_id=school.id,
                    person_no=f"STU{i:04d}",
                    full_name=_random_name(i),
                    role=PersonRole.STUDENT.value,
                    class_name=classes[(i - 1) % 3],
                    parent_phone=f"0555 000 {i:04d}",
                    parent_name=f"{_random_name(i + 100)} (veli)",
                    is_active=True,
                    access_granted=True,
                    consent_status=ConsentStatus.GRANTED.value,
                    consent_granted_at=datetime.utcnow() - timedelta(days=30),
                )
                p.set_face_encoding(_random_encoding(i))
                db.session.add(p)
                persons.append(p)

            # Teachers
            for j, name in enumerate(["Ayşe Öğretmen", "Mehmet Öğretmen"], start=1):
                teacher = Person(
                    school_id=school.id,
                    person_no=f"TCH{j:04d}",
                    full_name=name,
                    role=PersonRole.TEACHER.value,
                    class_name=None,
                    is_active=True,
                    access_granted=True,
                    consent_status=ConsentStatus.GRANTED.value,
                    consent_granted_at=datetime.utcnow() - timedelta(days=60),
                )
                teacher.set_face_encoding(_random_encoding(1000 + j))
                db.session.add(teacher)
                persons.append(teacher)

            db.session.flush()
            print(f"✓ {len(persons)} persons created (30 students + 2 teachers)")
        else:
            persons = db.session.query(Person).filter_by(school_id=school.id).all()
            print(f"↺ {existing_count} persons already exist")

        # ---- Devices ----
        device_keys = {}
        for name, loc in [("Ana Giriş", "A Blok Zemin"), ("Arka Giriş", "Bahçe Kapısı")]:
            existing = (
                db.session.query(Device)
                .filter_by(school_id=school.id, device_name=name)
                .first()
            )
            if existing is None:
                device = Device(
                    school_id=school.id,
                    device_name=name,
                    location=loc,
                    direction_mode=DeviceDirectionMode.BIDIRECTIONAL.value,
                    turnstile_pulse_ms=500,
                    is_active=True,
                )
                plain = device.set_api_key()
                db.session.add(device)
                db.session.flush()
                device_keys[name] = {
                    "uuid": device.device_uuid,
                    "api_key": plain,
                    "id": device.id}
                print(f"✓ Device created: {name} (uuid={device.device_uuid})")
            else:
                # Rotate key for demo purposes so the seed always prints a usable one
                plain = existing.set_api_key()
                device_keys[name] = {
                    "uuid": existing.device_uuid,
                    "api_key": plain,
                    "id": existing.id}
                print(f"↺ Device exists, rotated API key: {name}")

        # ---- Access logs (last 7 days) ----
        existing_logs = (
            db.session.query(AccessLog).filter_by(school_id=school.id).count()
        )
        if existing_logs < 50:
            devices = db.session.query(Device).filter_by(school_id=school.id).all()
            rng = random.Random(42)
            now = datetime.utcnow()
            for day in range(7):
                day_start = now - timedelta(days=day)
                for _ in range(rng.randint(15, 25)):
                    person = rng.choice(persons)
                    device = rng.choice(devices)
                    event = day_start.replace(
                        hour=rng.randint(7, 17),
                        minute=rng.randint(0, 59),
                        second=rng.randint(0, 59),
                    )
                    outcome = (
                        AccessOutcome.GRANTED.value
                        if rng.random() > 0.05
                        else AccessOutcome.DENIED_UNKNOWN.value
                    )
                    log = AccessLog(
                        school_id=school.id,
                        person_id=(
                            person.id if outcome == AccessOutcome.GRANTED.value else None
                        ),
                        device_id=device.id,
                        event_at=event,
                        direction=AccessDirection.IN.value,
                        outcome=outcome,
                        confidence=round(rng.uniform(0.82, 0.97), 2)
                        if outcome == AccessOutcome.GRANTED.value
                        else None,
                        recognizer_backend="dlib",
                    )
                    db.session.add(log)
            db.session.flush()
            print("✓ ~120 access logs created (last 7 days)")

        db.session.commit()

        return {
            "super_admin": {"email": "super@demo.local", "password": "demo1234"},
            "school_admin": {"email": "admin@demo.local", "password": "demo1234"},
            "school": {"subdomain": "demo", "id": school.id},
            "devices": device_keys}


if __name__ == "__main__":
    info = seed()
    print("\n" + "=" * 70)
    print("🎉 DEMO SEED COMPLETE")
    print("=" * 70)
    print("\n🌐 URLs (with `X-Tenant-Subdomain: demo` or `?tenant=demo`):")
    print("   http://localhost:5000/auth/login")
    print()
    print("👑 Super Admin:")
    print(f"   email:    {info['super_admin']['email']}")
    print(f"   password: {info['super_admin']['password']}")
    print("   url:      http://localhost:5000/auth/login (no tenant header needed)")
    print()
    print("🏫 School Admin (Demo Lisesi):")
    print(f"   email:    {info['school_admin']['email']}")
    print(f"   password: {info['school_admin']['password']}")
    print("   url:      http://localhost:5000/auth/login?tenant=demo")
    print()
    print("🖥️  Device API Keys (save these — can't be retrieved later):")
    for name, d in info["devices"].items():
        print(f"\n   Device: {name}")
        print(f"     DEVICE_ID:  {d['uuid']}")
        print(f"     API_KEY:    {d['api_key']}")
        print(f"     SCHOOL_ID:  {info['school']['id']}")
    print("\n" + "=" * 70)