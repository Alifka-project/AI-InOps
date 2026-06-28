"""ASGI entrypoint for hosting platforms (Vercel FastAPI service, etc.).

Vercel's FastAPI framework looks for an ``app`` ASGI callable in the service's
entrypoint at the service root. The real application lives in ``app/main.py``;
this thin module re-exports it so the entrypoint convention is satisfied while
keeping the package layout intact.
"""
from __future__ import annotations

from app.main import app  # noqa: F401  (re-exported ASGI application)

__all__ = ["app"]
