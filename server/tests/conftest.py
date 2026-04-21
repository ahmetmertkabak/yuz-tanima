"""
Pytest fixtures shared across unit and integration tests.
"""
import os

import pytest

os.environ.setdefault("FLASK_ENV", "testing")

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402


@pytest.fixture(scope="session")
def app():
    """Create a Flask application configured for testing."""
    application = create_app("testing")

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def db(app):
    """Fresh database session per test (rolls back at end)."""
    connection = _db.engine.connect()
    transaction = connection.begin()
    session = _db.session
    session.bind = connection

    yield _db

    transaction.rollback()
    connection.close()
    session.remove()