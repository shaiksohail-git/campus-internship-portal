"""Production entrypoint — runs migrations, then serves the Flask app on $PORT.

Importing this module builds the WSGI app (so `gunicorn main:app` works too).
Running it directly starts a server bound to the port the platform assigns.

The Flask package lives in backend/ (imported as `app`); templates and static
assets live in frontend/, which the app factory resolves relative to this
repository layout.
"""

import logging
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402 — path setup must run first
from app.extensions import db  # noqa: E402

logger = logging.getLogger("uvicorn.error")

app = create_app()


def run_migrations():
    """Apply Alembic migrations before the first request.

    A fresh database has no tables, and there is no separate migration step
    here — it runs from the app itself on boot. Skipped when no DATABASE_URL
    is configured, so a serverless entrypoint pointed at SQLite is untouched.
    """
    if not os.environ.get("DATABASE_URL"):
        return
    from flask_migrate import upgrade

    with app.app_context():
        upgrade()
        # Migrations open a connection in this process, and the server forks its
        # workers afterwards. An inherited socket then fails in whichever worker
        # picks it up, so close the pool before the fork.
        db.engine.dispose()


if os.environ.get("DATABASE_URL"):
    run_migrations()


def _serve():
    """Serve on 0.0.0.0:$PORT with gunicorn, falling back to Werkzeug."""
    port = int(os.environ.get("PORT", "5000"))
    try:
        from gunicorn.app.base import BaseApplication
    except ImportError:
        app.run(host="0.0.0.0", port=port, debug=False)
        return

    class Server(BaseApplication):
        def __init__(self):
            self.options = {
                "bind": f"0.0.0.0:{port}",
                "workers": int(os.environ.get("WEB_CONCURRENCY", "2")),
                "accesslog": "-",
                "errorlog": "-",
            }
            super().__init__()

        def load_config(self):
            for key, value in self.options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key.lower(), value)

        def load(self):
            return app

    Server().run()


if __name__ == "__main__":
    _serve()