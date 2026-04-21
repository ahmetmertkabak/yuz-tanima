"""Unit tests for AccessLog + AuditLog + Snapshot."""
from datetime import datetime, timedelta

import pytest

from app.models import (
    AccessDirection,
    AccessLog,
    AccessOutcome,
    AuditAction,
    AuditLog,
    Snapshot,
)


class TestAccessLog:
    def test_granted_log(self, db, make_person):
        person = make_person()
        log = AccessLog(
            school_id=person.school_id,
            person_id=person.id,
            event_at=datetime.utcnow(),
            direction=AccessDirection.IN.value,
            outcome=AccessOutcome.GRANTED.value,
            confidence=0.92,
        )
        db.session.add(log)
        db.session.commit()
        assert log.id is not None
        assert log.is_granted
        assert not log.is_unknown

    def test_unknown_face_log(self, db, make_school):
        school = make_school()
        log = AccessLog(
            school_id=school.id,
            person_id=None,
            direction=AccessDirection.UNKNOWN.value,
            outcome=AccessOutcome.DENIED_UNKNOWN.value,
        )
        db.session.add(log)
        db.session.commit()
        assert log.is_unknown
        assert not log.is_granted

    def test_invalid_outcome_rejected(self, db, make_school):
        with pytest.raises(ValueError):
            AccessLog(
                school_id=make_school().id,
                direction=AccessDirection.IN.value,
                outcome="made-up",
            )

    def test_confidence_range(self, db, make_school):
        with pytest.raises(ValueError):
            AccessLog(
                school_id=make_school().id,
                outcome=AccessOutcome.GRANTED.value,
                confidence=1.5,
            )

    def test_person_fields_cached(self, db, make_person):
        person = make_person(full_name="Ayşe", person_no="S100", class_name="10-B")
        log = AccessLog(
            school_id=person.school_id,
            person_id=person.id,
            direction=AccessDirection.IN.value,
            outcome=AccessOutcome.GRANTED.value,
        )
        db.session.add(log)
        db.session.commit()
        assert log.person_name_cached == "Ayşe"
        assert log.person_no_cached == "S100"
        assert log.person_class_cached == "10-B"


class TestSnapshot:
    def test_expires_at_auto_set(self, db, make_school):
        school = make_school()
        snap = Snapshot(
            school_id=school.id,
            image_path="s3://x/1.jpg",
            captured_at=datetime.utcnow(),
        )
        db.session.add(snap)
        db.session.commit()
        assert snap.expires_at is not None
        # Default retention is 30 days
        assert snap.expires_at > datetime.utcnow() + timedelta(days=29)

    def test_review_workflow(self, db, make_school, make_user):
        user = make_user()
        snap = Snapshot(
            school_id=user.school_id,
            image_path="s3://x/2.jpg",
            captured_at=datetime.utcnow(),
        )
        db.session.add(snap)
        db.session.commit()
        assert not snap.reviewed
        snap.mark_reviewed(user_id=user.id, note="looks fine")
        assert snap.reviewed
        assert snap.reviewed_by_user_id == user.id
        assert snap.review_note == "looks fine"


class TestAuditLog:
    def test_record_creates_entry(self, db, make_user):
        user = make_user()
        AuditLog.record(
            AuditAction.PERSON_CREATED,
            user=user,
            resource_type="person",
            resource_id=42,
            resource_label="Ali",
            ip="127.0.0.1",
        )
        db.session.commit()
        rows = db.session.query(AuditLog).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.action == "person.created"
        assert row.user_id == user.id
        assert row.user_email_cached == user.email
        assert row.school_id == user.school_id
        assert row.resource_id == "42"

    def test_audit_log_immutable_update(self, db, make_user):
        user = make_user()
        AuditLog.record(AuditAction.LOGIN_SUCCESS, user=user)
        db.session.commit()
        row = db.session.query(AuditLog).first()
        row.action = "tampered"
        with pytest.raises(RuntimeError):
            db.session.commit()
        db.session.rollback()

    def test_audit_log_immutable_delete(self, db, make_user):
        user = make_user()
        AuditLog.record(AuditAction.LOGIN_SUCCESS, user=user)
        db.session.commit()
        row = db.session.query(AuditLog).first()
        db.session.delete(row)
        with pytest.raises(RuntimeError):
            db.session.commit()
        db.session.rollback()