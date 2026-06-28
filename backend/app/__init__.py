"""FastAPI application package for the Digital Twin backend.

Ensures the repository root (which contains the verified ``core`` engine) is on
``sys.path`` so ``import core`` works whether the app is launched from the
``backend`` directory locally or from the project root inside Docker.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

__all__: list[str] = []
