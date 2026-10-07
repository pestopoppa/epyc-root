"""Observe the real root conftest teardown without replacing or copying it."""
from __future__ import annotations

import os


_PROGRESS_LOG_DIR_ENV = "ORCHESTRATOR_PROGRESS_LOG_DIR"


def pytest_unconfigure(config):
    """Observe restoration after pytest has finalized session fixtures."""
    restored = _PROGRESS_LOG_DIR_ENV not in os.environ
    os.write(1, ("SCG_LOGDIR_CONFTST_TEARDOWN=" + ("PASS" if restored else "FAIL") + "\n").encode())
