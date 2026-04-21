"""Unit tests for the User model."""
import pytest

from app.models import User, UserRole


class TestUserAuth:
    def test_password_hash(self, db, make_user):
        user = make_user(password="secret123456")
        assert user.check_password("secret123456")
        assert not user.check_password("wrong-password")

    def test_short_password_rejected(self, db, make_user):
        with pytest.raises(ValueError):
            make_user(password="short")

    def test_email_normalized(self, db, make_user):
        user = make_user(email="Upper@Example.COM")
        assert user.email == "upper@example.com"


class TestUserRoles:
    def test_super_admin_no_school(self, db):
        u = User(
            username="root",
            email="root@example.com",
            role=UserRole.SUPER_ADMIN.value,
            school_id=None,
        )
        u.set_password("password1234")
        db.session.add(u)
        db.session.commit()
        assert u.is_super_admin()

    def test_super_admin_rejects_school(self, db, make_school):
        school = make_school()
        u = User(
            username="bad",
            email="bad@example.com",
            role=UserRole.SUPER_ADMIN.value,
            school_id=school.id,
        )
        u.set_password("password1234")
        db.session.add(u)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_school_role_requires_school(self, db):
        u = User(
            username="orphan",
            email="orphan@example.com",
            role=UserRole.SCHOOL_ADMIN.value,
            school_id=None,
        )
        u.set_password("password1234")
        db.session.add(u)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_role_permission_helpers(self, db, make_user):
        admin = make_user(role=UserRole.SCHOOL_ADMIN.value)
        viewer = make_user(role=UserRole.VIEWER.value)
        assert admin.can_manage_persons()
        assert not viewer.can_manage_persons()
        assert viewer.can_view_reports()


class TestUserLockout:
    def test_lockout_after_failed_logins(self, db, make_user):
        user = make_user()
        for _ in range(5):
            user.register_failed_login(threshold=5)
        assert user.is_locked
        assert not user.is_active_account

    def test_successful_login_resets(self, db, make_user):
        user = make_user()
        user.register_failed_login()
        user.register_successful_login(ip="127.0.0.1")
        assert user.failed_login_count == 0
        assert not user.is_locked
        assert user.last_login_ip == "127.0.0.1"


class TestPerSchoolUniqueness:
    def test_same_username_different_schools(self, db, make_user, make_school):
        s1 = make_school()
        s2 = make_school()
        make_user(school=s1, username="alice", email="alice@a.com")
        # Should NOT collide because it's a different school
        make_user(school=s2, username="alice", email="alice@b.com")
        db.session.commit()
        assert db.session.query(User).filter_by(username="alice").count() == 2

    def test_duplicate_username_same_school(self, db, make_user, make_school):
        school = make_school()
        make_user(school=school, username="dupe", email="a@x.com")
        db.session.commit()
        with pytest.raises(Exception):
            make_user(school=school, username="dupe", email="b@x.com")
            db.session.commit()
        db.session.rollback()