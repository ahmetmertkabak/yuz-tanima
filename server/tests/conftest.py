"""
Pytest fixtures shared across unit and integration tests.

Tests use an in-memory SQLite database by default (no external services
required). Override with `TEST_DATABASE_URL=<postgres-url>` for CI-integration
runs that exercise Postgres-specific behaviour.
"""
from __future__ import annotations

import os
from typing import Generator

import pytest
from cryptography.fernet import Fernet

# --- MUST be set before app.config is imported ---
os.environ.setdefault("FLASK_ENV", "testing")
if not os.environ.get("FACE_ENCRYPTION_KEY"):
    os.environ["FACE_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from flask import Flask  # noqa: E402
from flask.testing import FlaskClient  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402


# ---------------------------------------------------------------------------
# Application / database fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Session-wide Flask app configured for testing."""
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture()
def db(app: Flask):
    """Clean DB session per test — rolls back all changes at teardown."""
    yield _db
    _db.session.rollback()
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def make_school(db):
    """Factory for School instances."""
    from app.models import School, SubscriptionStatus

    counter = {"n": 0}

    def _factory(**overrides):
        counter["n"] += 1
        defaults = {
            "name": f"Test Okulu {counter['n']}",
            "subdomain": f"test-{counter['n']}",
            "subscription_status": SubscriptionStatus.ACTIVE.value,
            "is_active": True,
            "max_devices": 5,
            "max_persons": 500}
        defaults.update(overrides)
        school = School(**defaults)
        db.session.add(school)
        db.session.flush()
        return school

    return _factory


@pytest.fixture()
def make_user(db, make_school):
    """Factory for User instances — creates a school if not given."""
    from app.models import User, UserRole

    counter = {"n": 0}

    def _factory(**overrides):
        counter["n"] += 1
        school = overrides.pop("school", None)
        role = overrides.pop("role", UserRole.SCHOOL_ADMIN.value)
        if role != UserRole.SUPER_ADMIN.value and school is None:
            school = make_school()
        password = overrides.pop("password", "testpass1234")
        defaults = {
            "username": f"user{counter['n']}",
            "email": f"user{counter['n']}@example.com",
            "full_name": f"Test User {counter['n']}",
            "role": role,
            "school_id": school.id if school else None,
            "is_active": True}
        defaults.update(overrides)
        user = User(**defaults)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        return user

    return _factory


@pytest.fixture()
def make_person(db, make_school):
    """Factory for Person instances."""
    from app.models import ConsentStatus, Person, PersonRole

    counter = {"n": 0}

    def _factory(**overrides):
        counter["n"] += 1
        school = overrides.pop("school", None) or make_school()
        defaults = {
            "school_id": school.id,
            "person_no": f"STU{counter['n']:04d}",
            "full_name": f"Test Student {counter['n']}",
            "role": PersonRole.STUDENT.value,
            "class_name": "9-A",
            "is_active": True,
            "access_granted": True,
            "consent_status": ConsentStatus.GRANTED.value}
        defaults.update(overrides)
        person = Person(**defaults)
        db.session.add(person)
        db.session.flush()
        return person

    return _factory


@pytest.fixture()
def make_device(db, make_school):
    """Factory for Device instances. Returns (device, plaintext_api_key)."""
    from app.models import Device, DeviceDirectionMode

    counter = {"n": 0}

    def _factory(**overrides):
        counter["n"] += 1
        school = overrides.pop("school", None) or make_school()
        defaults = {
            "school_id": school.id,
            "device_name": f"Gate {counter['n']}",
            "direction_mode": DeviceDirectionMode.BIDIRECTIONAL.value,
            "is_active": True}
        defaults.update(overrides)
        device = Device(**defaults)
        plain_key = device.set_api_key()
        db.session.add(device)
        db.session.flush()
        return device, plain_key

    return _factory