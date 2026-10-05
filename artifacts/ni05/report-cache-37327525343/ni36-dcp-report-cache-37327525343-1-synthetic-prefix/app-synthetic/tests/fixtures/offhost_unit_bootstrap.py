#!/usr/bin/env python3
"""Explicit off-host pytest entrypoint with a declared synthetic RAM fact.

The entire pytest invocation uses this fact. It is not evidence that the actual
runner can serve the production lineup. Run the actual-host subprocess capacity
fixture separately, without this entrypoint. No production module enables it.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from unittest.mock import patch


SYNTHETIC_HOST_RAM_GIB = 1024.0
MANIFEST_MODULE = "scripts.server.stack_manifest"


def _synthetic_host_memtotal_gib() -> float:
    """Declared host fact for this explicit test process only."""
    return SYNTHETIC_HOST_RAM_GIB


def main(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("Specify the pytest scope explicitly.")
    if MANIFEST_MODULE in sys.modules:
        raise SystemExit("The bootstrap requires a fresh process before manifest import.")

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    original_read_text = Path.read_text

    def initial_import_read_text(path: Path, *args, **kwargs):
        if path == Path("/proc/meminfo"):
            return "MemTotal: 1073741824 kB\n"
        return original_read_text(path, *args, **kwargs)

    # The real initial validator still runs, using only this declared host fact.
    # Restore the filesystem method immediately, before pytest imports anything.
    with patch.object(Path, "read_text", initial_import_read_text):
        manifest = importlib.import_module(MANIFEST_MODULE)

    original_host_provider = manifest._host_memtotal_gib
    manifest._host_memtotal_gib = _synthetic_host_memtotal_gib
    print(
        json.dumps(
            {
                "fixture": "offhost_synthetic_host_ram",
                "host_ram_gib": SYNTHETIC_HOST_RAM_GIB,
                "scope": "entire pytest invocation in this process",
                "pytest_argv": argv,
                "production_capacity_validator": "unchanged",
                "gpu_capacity_provider": "unchanged",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        import pytest

        return int(pytest.main(argv))
    finally:
        manifest._host_memtotal_gib = original_host_provider


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
