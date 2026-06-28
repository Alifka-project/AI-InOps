"""Pytest fixtures: repo root on path, a TestClient, and a sample dataset."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from core import data_generator as dg  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def sample() -> dict:
    """Canonical SAMPLE dataset used as the request payload in endpoint tests."""
    return dg.sample_dataset()


@pytest.fixture(scope="session")
def sample_csvs() -> dict:
    """{kind: csv_text} for the sample dataset (simulates real uploads)."""
    return dg.sample_csv_texts()
