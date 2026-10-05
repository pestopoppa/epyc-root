"""Suite-wide hermetic seams.

THE CURRENT-SERIAL-RUN POINTER (2026-09-16). ``dashboard.loop_status`` prefers
the host's ``current-serial-run.json`` over ``AUTOKERNEL_LOOP_STORE_ROOT``
(a1cb667f). On a host where a serial run is live, every test that injects a
fixture store through that env var — or that reads the hub's own payload —
silently read the live serial run instead, and went red the moment the
autokernel session started one. Point the pointer at a path that never exists
for every test. Tests that exercise the pointer set the variable themselves
(``monkeypatch.setenv`` / ``os.environ``), which overrides this default.
"""
from __future__ import annotations

import pytest

CURRENT_SERIAL_RUN_ENV = "AUTOKERNEL_CURRENT_SERIAL_RUN_POINTER"


@pytest.fixture(autouse=True)
def _no_host_current_serial_run_pointer(tmp_path_factory, monkeypatch):
    missing = tmp_path_factory.getbasetemp() / "no-current-serial-run.json"
    monkeypatch.setenv(CURRENT_SERIAL_RUN_ENV, str(missing))
