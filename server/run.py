"""
Development entry point.

Usage:
    python run.py                       # runs dev server on 0.0.0.0:5000
    FLASK_ENV=production python run.py  # runs under prod config

For production, use gunicorn via Docker or systemd:
    gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 "app:create_app()"
"""
import os

from app import create_app
from app.extensions import socketio

app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    socketio.run(
        app,
        host=host,
        port=port,
        debug=app.config["DEBUG"],
        use_reloader=app.config["DEBUG"],
        allow_unsafe_werkzeug=app.config["DEBUG"],
    )