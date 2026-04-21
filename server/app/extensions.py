"""
Flask extension instances.

Initialized here to avoid circular imports between the app factory and modules
that need access to these extensions.
"""
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
socketio = SocketIO()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],
)


# Configure login manager defaults
login_manager.login_view = "auth.login"
login_manager.login_message = "Bu sayfayı görüntülemek için giriş yapmalısınız."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"