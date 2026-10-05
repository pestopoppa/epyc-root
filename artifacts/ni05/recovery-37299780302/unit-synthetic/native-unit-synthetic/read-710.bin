"""A5: --skip-bad-rows tolerance for the RLVR environment export.

Default behavior stays strict (all-or-nothing, rc 2 on a bad line). With
--skip-bad-rows the malformed line is skipped, counted, and sampled in the
summary while the good row still exports. Fixtures reuse the row shape from
test_rlvr_environment_export.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.autopilot.export_rlvr_environment import main


_GOOD_ROW = {
    "trial_id": 42,
    "action_type": "deep_eval",
    "tier": 2,
    "quality": 2.4,
    "reliability": 0.9,
    "eval_details": {
        "ece": 0.05,
        "auroc": 0.8,
        "question_results": [
            {"qid": "q1", "suite": "math", "correct": True, "answer_hash": "sha256:abc"}
        ],
    },
}


def _write_journal(tmp_path: Path) -> Path:
    # Line 1: valid eval row. Line 2: garbage (invalid JSON).
    source = tmp_path / "journal.jsonl"
    source.write_text(
        json.dumps(_GOOD_ROW) + "\n" + "this is not json {\n",
        encoding="utf-8",
    )
    return source


def test_default_run_fails_on_bad_row(tmp_path: Path) -> None:
    source = _write_journal(tmp_path)
    output = tmp_path / "rlvr.jsonl"

    assert main([str(source), "--output-jsonl", str(output)]) == 2


def test_skip_bad_rows_exports_good_row_and_records_skip(tmp_path: Path) -> None:
    source = _write_journal(tmp_path)
    output = tmp_path / "rlvr.jsonl"
    summary_path = tmp_path / "summary.json"

    rc = main(
        [
            str(source),
            "--output-jsonl",
            str(output),
            "--summary-json",
            str(summary_path),
            "--skip-bad-rows",
        ]
    )

    assert rc == 0
    exported = [json.loads(ln) for ln in output.read_text(encoding="utf-8").splitlines()]
    assert len(exported) == 1
    assert exported[0]["trial_id"] == 42

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["rows"] == 1
    assert summary["skipped_bad_rows"] == 1
    samples = summary["skipped_bad_row_samples"]
    assert len(samples) == 1
    assert samples[0]["line"] == 2
    assert samples[0]["path"].endswith("journal.jsonl")
    assert "invalid JSON" in samples[0]["error"]
