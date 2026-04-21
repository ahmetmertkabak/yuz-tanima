"""
Tenant isolation — the single most important security test in this codebase.

Verifies that the SQLAlchemy `do_orm_execute` listener injects a
`school_id == g.tenant_context.school_id` predicate on every SELECT against
tenant-scoped models.
"""
import pytest
from flask import g

from app.middleware.tenant import TenantContext
from app.models import AccessLog, AccessOutcome, Device, Person


def _set_tenant(school):
    """Simulate the request-time tenant middleware."""
    g.tenant_context = TenantContext(
        subdomain=school.subdomain,
        school=school,
        is_super_admin_host=False,
        is_api_host=False,
    )
    g.bypass_tenant_filter = False


def _clear_tenant():
    for attr in ("tenant_context", "bypass_tenant_filter"):
        if attr in g:
            g.pop(attr)


@pytest.fixture(autouse=True)
def _clean_tenant_state(app):
    """Ensure no leakage between tests."""
    yield
    with app.app_context():
        _clear_tenant()


class TestPersonIsolation:
    def test_school_a_sees_only_own_persons(
        self, app, db, make_school, make_person
    ):
        school_a = make_school(subdomain="a")
        school_b = make_school(subdomain="b")
        make_person(school=school_a, person_no="A001")
        make_person(school=school_a, person_no="A002")
        make_person(school=school_b, person_no="B001")
        db.session.commit()

        with app.test_request_context("/"):
            _set_tenant(school_a)
            rows = db.session.query(Person).all()
            assert len(rows) == 2
            assert {p.person_no for p in rows} == {"A001", "A002"}

        with app.test_request_context("/"):
            _set_tenant(school_b)
            rows = db.session.query(Person).all()
            assert len(rows) == 1
            assert rows[0].person_no == "B001"

    def test_cross_tenant_lookup_returns_none(
        self, app, db, make_school, make_person
    ):
        school_a = make_school(subdomain="a2")
        school_b = make_school(subdomain="b2")
        alien = make_person(school=school_b, person_no="X999")
        db.session.commit()

        with app.test_request_context("/"):
            _set_tenant(school_a)
            found = db.session.query(Person).filter_by(id=alien.id).first()
            assert found is None  # filtered out by tenant middleware

    def test_super_admin_bypass(self, app, db, make_school, make_person):
        school_a = make_school(subdomain="a3")
        school_b = make_school(subdomain="b3")
        make_person(school=school_a, person_no="A1")
        make_person(school=school_b, person_no="B1")
        db.session.commit()

        with app.test_request_context("/"):
            _set_tenant(school_a)
            g.bypass_tenant_filter = True
            rows = db.session.query(Person).all()
            # Bypass => sees everyone
            assert len(rows) == 2


class TestDeviceIsolation:
    def test_device_filtered(self, app, db, make_school, make_device):
        school_a = make_school(subdomain="ad")
        school_b = make_school(subdomain="bd")
        make_device(school=school_a, device_name="A-Gate")
        make_device(school=school_b, device_name="B-Gate")
        db.session.commit()

        with app.test_request_context("/"):
            _set_tenant(school_a)
            rows = db.session.query(Device).all()
            assert {d.device_name for d in rows} == {"A-Gate"}


class TestAccessLogIsolation:
    def test_access_logs_filtered(
        self, app, db, make_school, make_person
    ):
        school_a = make_school(subdomain="al")
        school_b = make_school(subdomain="bl")
        pa = make_person(school=school_a)
        pb = make_person(school=school_b)
        db.session.add_all(
            [
                AccessLog(
                    school_id=school_a.id,
                    person_id=pa.id,
                    direction="in",
                    outcome=AccessOutcome.GRANTED.value,
                ),
                AccessLog(
                    school_id=school_b.id,
                    person_id=pb.id,
                    direction="in",
                    outcome=AccessOutcome.GRANTED.value,
                )]
        )
        db.session.commit()

        with app.test_request_context("/"):
            _set_tenant(school_a)
            rows = db.session.query(AccessLog).all()
            assert len(rows) == 1
            assert rows[0].school_id == school_a.id