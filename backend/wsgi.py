"""WSGI entrypoint for Gunicorn and Flask CLI."""

import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.getenv("FLASK_ENV", "production"))
