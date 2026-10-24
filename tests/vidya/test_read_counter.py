"""VB-REFOCUS-READ-COUNTER: the per-prepare read log and the empty/non-empty report."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))
sys.path.insert(0, str(REPO / "tests" / "vidya"))

import loop_beliefs as lb  # noqa: E402
import read_counter as rc  # noqa: E402
from test_loop_beliefs import (AS_OF, DS41_CPU, FakeSync,  # noqa: E402,F401
                               alarm)


def _answer(nonempty, status="ready", claims=("c1",)):
    ev = {"nonempty_target": nonempty, "claim_ids": list(claims) if nonempty else [],
          "tiers": {"target": 2 if nonempty else 0, "sibling": 0, "host": 1}}
    return {"consumer": "t.c", "as_of": AS_OF, "status": status, "ledger_path": "x/ledger.jsonl",
            "targets": [{"model_file": "M.gguf"}], "evidence": ev if status == "ready" else None}


def test_record_shape_and_default_path_beside_ledger(tmp_path):
    led = tmp_path / "ledger.jsonl"
    assert rc.record_read(_answer(True), ledger=led) is None
    row = json.loads((tmp_path / "reads.jsonl").read_text())
    assert row["schema"] == rc.SCHEMA and row["consumer"] == "t.c" and row["target_key"] == "M.gguf"
    assert row["nonempty_target"] is True and row["usable_count"] == 1
    assert row["tier_counts"] == {"target": 2, "sibling": 0, "host": 1} and row["as_of"] == AS_OF


def test_env_and_explicit_override(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDYA_READ_LOG", str(tmp_path / "env.jsonl"))
    rc.record_read(_answer(False), ledger=tmp_path / "l.jsonl")
    assert (tmp_path / "env.jsonl").exists()
    rc.record_read(_answer(False), ledger=tmp_path / "l.jsonl", read_log=tmp_path / "x.jsonl")
    assert (tmp_path / "x.jsonl").exists()


def test_write_failure_is_reported_never_raised(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    err = rc.record_read(_answer(True), read_log=blocker / "sub" / "r.jsonl")
    assert err and "Error" in err


def test_prepare_appends_one_record_per_call_and_survives_log_failure(tmp_path, alarm):
    log = tmp_path / "reads.jsonl"
    kw = dict(ledger=tmp_path / "missing.jsonl", index_path=tmp_path / "i.yaml", as_of=AS_OF,
              sync_module=FakeSync(), known_good=tmp_path / "kg.json", **alarm)
    a = lb.prepare("t.c", [{"model_path": DS41_CPU["model_path"], "backend": "cpu"}],
                   read_log=log, **kw)
    rows = [json.loads(x) for x in log.read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["consumer"] == "t.c"
    assert rows[0]["status"] == a["status"] and "read_log_error" not in a
    blocker = tmp_path / "f"
    blocker.write_text("x")
    b = lb.prepare("t.c", [{"model_path": DS41_CPU["model_path"], "backend": "cpu"}],
                   read_log=blocker / "r.jsonl", **kw)
    assert b["status"] == a["status"] and b["read_log_error"]


def _receipts(root):
    d = root / "camp" / "workers" / "actor-replies"
    d.mkdir(parents=True)
    tgt = {"model_path": "/m/DS.gguf"}
    rows = [{"schema": "x.v1", "consumer": "autokernel.planner", "target": tgt, "claim_ids": [],
             "as_of": "2026-10-01T00:00:00+00:00", "ts": "2026-10-01T00:00:01Z"},
            {"schema": "x.v2", "consumer": "autokernel.planner", "target": tgt, "status": "ready",
             "claim_ids": ["a"], "evidence_v2": {"nonempty_target": True},
             "as_of": "2026-10-20T00:00:00+00:00", "ts": "2026-10-20T00:00:01Z"},
            {"schema": "x.v2", "consumer": "autokernel.planner", "target": tgt, "status": "refused",
             "as_of": "2026-10-21T00:00:00+00:00", "ts": "2026-10-21T00:00:01Z"}]
    (d / "belief-receipts.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_report_counts_receipts_readlog_dedup_and_window(tmp_path):
    _receipts(tmp_path / "ak")
    arch = tmp_path / "archive.jsonl"
    arch.write_text(json.dumps({"ts": 1792800000, "vidya_loop_beliefs":
                                {"status": "ready", "nonempty_target": False,
                                 "consumer": "autopilot.planner"}}) + "\n"
                    + json.dumps({"ts": 1792800001, "vidya_loop_beliefs":
                                  {"status": "absent"}}) + "\n" + "not json\n")
    log = tmp_path / "reads.jsonl"
    # duplicates the 10-20 receipt (same consumer + as_of): counted once
    rc.record_read({**_answer(True), "consumer": "autokernel.planner",
                    "as_of": "2026-10-20T00:00:00+00:00"}, read_log=log)
    rc.record_read(_answer(False), read_log=log)
    rep = rc.build_report(read_log=log, autokernel_root=tmp_path / "ak", autopilot_archive=arch)
    ak = rep["by_consumer"]["autokernel.planner"]
    assert (ak["nonempty"], ak["empty"], ak["refused"]) == (1, 1, 1) and rep["deduplicated"] == 1
    assert rep["by_consumer"]["autopilot.planner"]["empty"] == 1
    assert rep["by_consumer"]["autopilot.planner"]["nonempty_rate"] == 0.0
    assert rep["by_consumer"]["t.c"]["empty"] == 1
    assert rep["by_consumer_target"]["autokernel.planner | DS.gguf"]["total"] == 2
    win = rc.build_report(autokernel_root=tmp_path / "ak", since=rc._ts("2026-10-10T00:00:00Z"))
    assert win["total"] == 2


def test_cli_json(tmp_path):
    _receipts(tmp_path / "ak")
    out = subprocess.run([sys.executable, str(REPO / "scripts/vidya/loop_beliefs.py"), "read-counter",
                          "--json", "--read-log", str(tmp_path / "none.jsonl"),
                          "--autokernel-root", str(tmp_path / "ak"),
                          "--autopilot-archive", str(tmp_path / "none2")],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["total"] == 3
