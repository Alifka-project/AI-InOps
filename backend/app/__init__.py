"""FastAPI application package for the Digital Twin backend.

Ensures the directory that contains the verified ``core`` engine is on
``sys.path`` so ``import core`` works no matter where the app is launched from
(repo root, the ``backend`` directory, Docker, or a monorepo platform that scopes
the service to ``backend/``). It searches upward from this file for a directory
that contains ``core/__init__.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_core_on_path() -> None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "core" / "__init__.py").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return


_ensure_core_on_path()

__all__: list[str] = []
