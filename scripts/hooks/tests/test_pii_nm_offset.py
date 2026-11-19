"""PII-NM-OFFSET: genuine `nm` rows pass raw; account-number look-alikes still block."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "scripts/hooks/pii_precommit.sh"

ROWS = [json.loads(x) for x in (ROOT / "research/fixtures/pii_nm_offset_rows.jsonl").read_text().splitlines()]
CASES = [(r["id"], r["text"], r["must_block"]) for r in ROWS]


@pytest.mark.parametrize("cid,line,must_block", CASES, ids=[c[0] for c in CASES])
def test_nm_row(tmp_path, cid, line, must_block):
    def run(*a):
        return subprocess.run(a, cwd=tmp_path, text=True, capture_output=True, timeout=30)

    assert run("git", "init", "-q").returncode == 0
    f = tmp_path / "docs" / "symbols.txt"
    f.parent.mkdir()
    raw = line + "\n"
    f.write_text(raw)
    assert run("git", "add", "--", "docs/symbols.txt").returncode == 0
    r = run("bash", str(HOOK))
    assert r.returncode in (0, 1), r.stderr
    blocked = bool(re.search(r"^BLOCKED: .*: \[(secret|account_number)\]", r.stderr, re.M))
    assert blocked == must_block, r.stderr
    assert f.read_text() == raw  # raw bytes untouched
