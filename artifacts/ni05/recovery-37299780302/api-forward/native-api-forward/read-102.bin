from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "autopilot" / "autopilot_supervisor.py"
spec = importlib.util.spec_from_file_location("autopilot_supervisor", SCRIPT)
assert spec is not None and spec.loader is not None
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)


def test_supervisor_records_death_and_restarts_once(tmp_path: Path) -> None:
    ledger = tmp_path / "death.jsonl"
    marker = tmp_path / "failed_once"
    code = (
        "from pathlib import Path\n"
        "import sys\n"
        f"marker = Path({str(marker)!r})\n"
        "if not marker.exists():\n"
        "    marker.write_text('1')\n"
        "    sys.exit(7)\n"
        "sys.exit(0)\n"
    )

    rc = supervisor.supervise(
        [sys.executable, "-c", code],
        max_restarts=1,
        restart_delay_s=0.0,
        death_ledger_path=ledger,
    )

    assert rc == 0
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert [row["returncode"] for row in rows] == [7, 0]
    assert rows[0]["cause"] == "nonzero_exit"
    assert rows[0]["restart_scheduled"] is True
    assert rows[1]["cause"] == "clean_exit"
    assert rows[1]["restart_scheduled"] is False
