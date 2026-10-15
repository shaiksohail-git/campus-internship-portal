"""Vercel serverless entrypoint — exposes the Flask WSGI app.

The Flask package lives in backend/ (imported as `app`); templates and static
assets live in frontend/, which the app factory resolves relative to this
repository layout. Every request (including /static) is routed here.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402 — path setup must run first

app = create_app()
