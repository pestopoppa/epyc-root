"""Stage P5 path controls through the actual PII hook, including mixed leaks."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "scripts/hooks/pii_precommit.sh"
ROWS = [json.loads(line) for line in
        (ROOT / "research/fixtures/pii_p5_generated_paths.jsonl").read_text().splitlines()]
# Keep the source fixture small; the hook still scans an actual large staged line.
ROWS.append({**next(row for row in ROWS if row["id"] == "additional-bare-number"),
             "id": "large-line-additional-bare-number",
             "text": next(row["text"] for row in ROWS
                          if row["id"] == "additional-bare-number") + " " + "x" * (128 * 1024)})


@pytest.mark.parametrize("row", ROWS, ids=[row["id"] for row in ROWS])
def test_p5_generated_path_control(tmp_path, row):
    def run(*args):
        return subprocess.run(args, cwd=tmp_path, text=True, capture_output=True, timeout=30)

    assert run("git", "init", "-q").returncode == 0
    evidence = tmp_path / row["path"]
    evidence.parent.mkdir(parents=True)
    evidence.write_text(row["text"] + "\n")
    assert run("git", "add", "--", row["path"]).returncode == 0
    result = run("bash", str(HOOK))
    assert result.returncode in (0, 1), result.stderr
    blocked = bool(re.search(r"^BLOCKED: .*: \[(secret|account_number)\]", result.stderr, re.M))
    assert blocked == (result.returncode == 1), result.stderr
    assert blocked == row["expected_match"], result.stderr
    if blocked:
        assert f'[{row["label"]}]' in result.stderr
