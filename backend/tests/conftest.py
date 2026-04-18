"""
Pytest shared fixtures.

Every test runs from the backend/ working directory so that relative
imports (`from services import …`) resolve the same way the uvicorn
process does.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
# Ensure `from services import …` works when pytest is invoked from
# either backend/ or the repo root.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def _chdir_to_backend(monkeypatch):
    """Make the CWD stable so relative file paths behave."""
    monkeypatch.chdir(BACKEND_DIR)


@pytest.fixture
def reset_aggregator():
    """
    Reset the in-memory dashboard aggregator before AND after each test
    that asks for it — prevents cross-test state leakage without
    polluting the shared state for tests that don't care.
    """
    from services import aggregator
    aggregator.reset()
    yield
    aggregator.reset()


@pytest.fixture(scope="session")
def test_client():
    """FastAPI TestClient shared across the session.

    Yielded lazily so tests that don't hit HTTP (validator, aggregator
    unit tests) don't pay the import cost.
    """
    from fastapi.testclient import TestClient

    from main import app
    with TestClient(app) as client:
        yield client
