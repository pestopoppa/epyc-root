"""Run source-pinned candidate modules without writing to the application tree."""

import os
import sys
from pathlib import Path

from candidate import install

sys.dont_write_bytecode = True
scratch = Path("/mnt/raid0/llm/tmp/routing-intelligence/ure2-writer")
scratch.mkdir(parents=True, exist_ok=True)
os.environ["ORCHESTRATOR_PROGRESS_LOG_DIR"] = str(scratch / "progress")
os.environ["ORCHESTRATOR_MOCK_MODE"] = "1"
baseline = "--baseline" in sys.argv
if baseline:
    sys.argv.remove("--baseline")
install(baseline=baseline)

from src.trace import approval_live

approval_live.DEFAULT_DB_PATH = scratch / "regression-events.sqlite"

import pytest

raise SystemExit(
    pytest.main(
        [
            "-q",
            "-o",
            f"cache_dir={scratch / 'pytest-cache'}",
            *(
                [*sys.argv[1:]]
                if sys.argv[1:]
                else [str(Path(__file__).with_name("test_approval_live.py"))]
            ),
        ]
    )
)
