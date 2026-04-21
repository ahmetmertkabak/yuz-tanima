"""Unit tests for the Person model + face encoding encryption."""
from datetime import datetime, time

import numpy as np
import pytest

from app.models import ConsentStatus, Person, PersonRole


class TestPersonBasics:
    def test_create(self, db, make_person):
        person = make_person(full_name="Ali Veli")
        assert person.id is not None
        assert person.full_name == "Ali Veli"
        assert person.role == PersonRole.STUDENT.value

    def test_person_no_required(self, db, make_school):
        with pytest.raises(ValueError):
            Person(
                school_id=make_school().id,
                person_no="",
                full_name="X",
                role=PersonRole.STUDENT.value,
            )

    def test_person_no_unique_per_school(self, db, make_person, make_school):
        school = make_school()
        make_person(school=school, person_no="STU001")
        db.session.commit()
        with pytest.raises(Exception):
            make_person(school=school, person_no="STU001")
            db.session.commit()
        db.session.rollback()

    def test_invalid_role(self, db, make_school):
        with pytest.raises(ValueError):
            Person(
                school_id=make_school().id,
                person_no="X1",
                full_name="X",
                role="invalid_role",
            )


class TestFaceEncoding:
    def test_encrypt_decrypt_round_trip(self, db, make_person):
        person = make_person()
        encoding = np.random.rand(128).astype(np.float32)
        person.set_face_encoding(encoding)
        db.session.commit()

        decrypted = person.get_face_encoding()
        assert decrypted is not None
        np.testing.assert_allclose(decrypted, encoding, rtol=1e-6)

    def test_ciphertext_changes_on_re_encrypt(self, db, make_person):
        person = make_person()
        encoding = np.random.rand(128).astype(np.float32)
        person.set_face_encoding(encoding)
        ct1 = person.face_encoding_encrypted
        person.set_face_encoding(encoding)
        ct2 = person.face_encoding_encrypted
        # Fernet uses random IV → ciphertexts differ even for same input
        assert ct1 != ct2

    def test_has_face_flag(self, db, make_person):
        person = make_person()
        assert not person.has_face
        person.set_face_encoding(np.zeros(128, dtype=np.float32))
        assert person.has_face

    def test_clear_face_encoding(self, db, make_person):
        person = make_person()
        person.set_face_encoding(np.zeros(128, dtype=np.float32))
        person.face_photo_path = "s3://bucket/xxx.jpg"
        person.clear_face_encoding()
        assert not person.has_face
        assert person.face_photo_path is None


class TestConsent:
    def test_grant_consent(self, db, make_person):
        person = make_person(consent_status=ConsentStatus.PENDING.value)
        person.grant_consent(document_path="consent/xxx.pdf")
        assert person.consent_status == ConsentStatus.GRANTED.value
        assert person.consent_granted_at is not None
        assert person.consent_document_path == "consent/xxx.pdf"

    def test_revoke_wipes_face(self, db, make_person):
        person = make_person()
        person.set_face_encoding(np.zeros(128, dtype=np.float32))
        person.face_photo_path = "s3://bucket/xxx.jpg"
        db.session.commit()

        person.revoke_consent()
        assert person.consent_status == ConsentStatus.REVOKED.value
        assert not person.has_face
        assert person.face_photo_path is None


class TestAccessSchedule:
    def test_access_allowed_no_schedule(self, db, make_person):
        person = make_person(access_schedule=None)
        assert person.is_access_allowed_now()

    def test_access_denied_when_inactive(self, db, make_person):
        person = make_person(is_active=False)
        assert not person.is_access_allowed_now()

    def test_access_denied_no_consent(self, db, make_person):
        person = make_person(consent_status=ConsentStatus.PENDING.value)
        assert not person.is_access_allowed_now()

    def test_access_denied_outside_window(self, db, make_person):
        # Monday 2026-04-20 at 03:00 UTC → before 07:30
        person = make_person(access_schedule={"mon": ["07:30-18:00"]})
        early = datetime(2026, 4, 20, 3, 0, 0)
        assert not person.is_access_allowed_now(now=early)

    def test_access_allowed_inside_window(self, db, make_person):
        person = make_person(access_schedule={"mon": ["07:30-18:00"]})
        midday = datetime(2026, 4, 20, 12, 0, 0)  # Monday
        assert person.is_access_allowed_now(now=midday)

    def test_empty_day_forbids(self, db, make_person):
        person = make_person(access_schedule={"sat": []})
        saturday = datetime(2026, 4, 25, 12, 0, 0)
        assert not person.is_access_allowed_now(now=saturday)