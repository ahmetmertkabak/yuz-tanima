"""Unit tests for the School model."""
import pytest

from app.models import School, SubscriptionStatus


class TestSchoolBasics:
    def test_create(self, db):
        school = School(name="Test", subdomain="test")
        db.session.add(school)
        db.session.commit()
        assert school.id is not None
        assert school.created_at is not None

    def test_subdomain_unique(self, db):
        s1 = School(name="A", subdomain="same")
        db.session.add(s1)
        db.session.commit()

        s2 = School(name="B", subdomain="same")
        db.session.add(s2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_normalize_subdomain(self):
        assert School.normalize_subdomain("Ali Paşa") == "ali-paşa"
        assert School.normalize_subdomain("  FOO_BAR ") == "foo-bar"


class TestSubscription:
    def test_trial_lifecycle(self, db, make_school):
        school = make_school(subscription_status=SubscriptionStatus.TRIAL.value)
        school.start_trial(days=7)
        db.session.commit()
        assert school.is_subscription_active
        assert school.trial_expires_at is not None

    def test_suspended_is_inactive(self, db, make_school):
        school = make_school(
            subscription_status=SubscriptionStatus.SUSPENDED.value
        )
        assert not school.is_subscription_active

    def test_inactive_flag_blocks(self, db, make_school):
        school = make_school(is_active=False)
        assert not school.is_subscription_active