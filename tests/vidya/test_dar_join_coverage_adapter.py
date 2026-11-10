"""VB-DAR-JOIN-COVERAGE-WIRE: receipts written by the real producer, strict projection.

The fixture runs scripts/analysis/dar_join_coverage.py itself (synthetic inputs, no real DAR data), so
the reader is pinned to the producer's actual receipt shape. No real audit has run yet.
"""
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import dar_join_coverage as adapter  # noqa: E402

PRODUCER = ROOT / "scripts" / "analysis" / "dar_join_coverage.py"


def fixture(tmp_path) -> Path:
    prog = [{"event_type": "task_started", "task_id": t, "timestamp": "2026-09-25T00:00:00Z",
             "data": {"objective": "o", "task_type": "x"}} for t in ("t1", "t2")]
    prog += [{"event_type": "task_completed", "task_id": "t1", "timestamp": "2026-09-25T00:00:10Z",
              "data": {"role": "r"}}]
    rew = [{"task_id": "t1", "timestamp": "2026-09-25T00:00:10Z", "producer_role": "r", "wall_clock_s": 10,
            "reward_post_fix": 0.5, "outcome": "success"}]
    files = {"p.jsonl": prog, "r.jsonl": rew}
    for name, rows in files.items():
        (tmp_path / name).write_text("\n".join(json.dumps(x) for x in rows) + "\n")
    (tmp_path / "b.json").write_text('["r"]')
    (tmp_path / "c.json").write_text('{"scorer": "synthetic"}')
    out = tmp_path / "receipt.json"
    subprocess.run([sys.executable, str(PRODUCER), "--progress", str(tmp_path / "p.jsonl"), "--rewards",
                    str(tmp_path / "r.jsonl"), "--baseline-roles", str(tmp_path / "b.json"), "--scorer-config",
                    str(tmp_path / "c.json"), "--receipt-out", str(out)], check=True, capture_output=True)
    return out


def test_producer_receipt_projects_two_observations(tmp_path):
    natives = adapter.native_rows(fixture(tmp_path))
    tuples = {t.metric: t for t in map(adapter.project, natives)}
    assert tuples["dar_join.feature_reward_coverage"].value == 0.5   # 1 joined / 2 progress ids
    assert tuples["dar_join.duration_input_coverage"].value == 0.5
    for t in tuples.values():
        assert t.protocol_id == "" and t.reps == 2
        assert ct.grade(t)[0] != "Witnessed"
        assert '"t1"' not in json.dumps(t.extra) and "objective" not in json.dumps(t.extra)


def test_producer_default_stdout_unchanged_without_receipt(tmp_path):
    fixture(tmp_path)
    out = subprocess.run([sys.executable, str(PRODUCER), "--progress", str(tmp_path / "p.jsonl"), "--rewards",
                          str(tmp_path / "r.jsonl"), "--baseline-roles", str(tmp_path / "b.json")],
                         check=True, capture_output=True, text=True).stdout
    assert json.loads(out)["schema"] == "dar-join-audit.v1"


def test_producer_refuses_half_receipt_flags(tmp_path):
    fixture(tmp_path)
    r = subprocess.run([sys.executable, str(PRODUCER), "--progress", str(tmp_path / "p.jsonl"), "--rewards",
                        str(tmp_path / "r.jsonl"), "--baseline-roles", str(tmp_path / "b.json"),
                        "--receipt-out", str(tmp_path / "x.json")], capture_output=True)
    assert r.returncode == 2 and not (tmp_path / "x.json").exists()


def _tamper(tmp_path, fn, reseal=False):
    path = fixture(tmp_path)
    doc = json.loads(path.read_text())
    fn(doc)
    if reseal:
        doc["receipt_sha256"] = adapter._digest(doc)
    path.write_text(json.dumps(doc))
    return adapter.native_rows(path)[0]


@pytest.mark.parametrize("fn,reseal,match", [
    (lambda d: d["result"]["counts"].update(joined_unique_feature_reward=2), False, "does not bind"),
    (lambda d: d["result"]["counts"].update(joined_unique_feature_reward=9), True, "invariant"),
    (lambda d: d.update(status="failed"), True, "not completed"),
    (lambda d: d["inputs"].pop("scorer_config_sha256"), True, "scorer_config"),
    (lambda d: d["producer"].update(git_revision=None), True, "git revision"),
    (lambda d: d["inputs"].update(progress=[]), True, "progress"),
    (lambda d: d["result"]["counts"].update(progress_task_ids=0, joined_unique_feature_reward=0,
                                            joined_duration_inputs_available=0), True, "no progress"),
])
def test_tampered_or_partial_receipts_are_refused(tmp_path, fn, reseal, match):
    with pytest.raises(ct.ProjectionError, match=match):
        adapter.project(_tamper(tmp_path, fn, reseal))


def test_foreign_and_stdout_only_documents_are_refused(tmp_path):
    p = tmp_path / "audit.json"
    p.write_text(json.dumps({"schema": "dar-join-audit.v1", "counts": {}}))
    with pytest.raises(ct.ProjectionError, match="no receipt"):
        adapter.native_rows(p)


def test_unknown_metric_and_changed_bytes(tmp_path):
    path = fixture(tmp_path)
    native = adapter.native_rows(path)[0]
    with pytest.raises(ct.ProjectionError, match="unknown"):
        adapter.project({**native, "metric": "dar_join.reward_quality"})
    path.write_text(path.read_text() + " ")
    with pytest.raises(ct.ProjectionError, match="hashed bytes"):
        adapter.project(native)
