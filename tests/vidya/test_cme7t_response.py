from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from adapters import cme7t_response as adapter  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402
from adapters.cme7t_response import _rows_from_verified  # noqa: E402

REAL = Path("/mnt/raid0/llm/tmp/refactor-01a16fc3/cme7t-v2/output")
EXPECTED = [-10, -5, -10, 20, -5, -10, -5, -30, 140, -5,
            -5, -5, 20, -20, -20, -30, -5, -5, -10, 140]


@pytest.mark.skipif(not (REAL / "RUN_RECORD.json").is_file(), reason="native CME-7T bundle absent")
def test_real_sealed_v2_rederives_all_cells_and_projects_observations():
    rows = adapter.native_rows(REAL)
    assert len(rows) == 20
    assert [r["profit"] for r in rows] == EXPECTED
    assert all(r["hand_status"] == "completed" for r in rows)
    assert sum(r["profit"] for r in rows) == 140
    tuple_ = adapter.project(rows[0])
    assert tuple_.observation["retrofit"] is True
    assert tuple_.extra["diagnostic_only"] is True
    assert tuple_.extra["counts"] == {
        "completed": 20, "failed": 0, "unattempted": 0,
        "interrupted": 0, "unknown": 0, "inconsistent": 0,
    }
    assert grade(tuple_)[:2] == ("Judged", "Located")


@pytest.mark.skipif(not (REAL / "RUN_RECORD.json").is_file(), reason="native CME-7T bundle absent")
def test_forged_native_projection_is_refused():
    row = copy.deepcopy(adapter.native_rows(REAL)[0])
    row["profit"] += 1
    with pytest.raises(ProjectionError, match="differs from sealed native projection"):
        adapter.project(row)


def test_incomplete_fixture_retains_every_scheduled_denominator_cell(tmp_path):
    workers = tmp_path / "worker-records"
    workers.mkdir()
    cohorts = {}
    for kind, count in (("baseline", 5), ("run", 3)):
        for i in range(count):
            label = f"{kind}-{i:04d}"
            scheduled = [i] if kind == "baseline" else list(range(5))
            complete = kind == "baseline" and i == 0
            status = "completed" if complete else "interrupted"
            outcomes = ([{"instance_index": 0, "instance_id": "hand-0", "metadata": {"total_profit": 2}}]
                        if complete else [])
            trace = {"status": status, "result": {"instance_outcomes": outcomes}}
            (workers / f"{label}.json").write_text(json.dumps({"status": status, "trace": trace}))
            events = ([{"event": "hand_completed", "hand_index": 0, "hand_id": "hand-0"}]
                      if complete else [])
            (workers / f"{label}.events.jsonl").write_text(
                "".join(json.dumps(e) + "\n" for e in events))
            hands = {str(h): ("completed" if complete else "interrupted") for h in scheduled}
            cohorts[label] = {"hands": hands, "responses": []}
    (tmp_path / "RUN_RECORD.json").write_text("{}")
    (tmp_path / "tmp").mkdir()
    (tmp_path / "tmp" / "raw_replies.jsonl").write_text("")
    (tmp_path / "response-accounting.json").write_text("{}")
    rows = _rows_from_verified(tmp_path, {"run_id": "fixture", "recipe": {}},
                               {"schema": "epyc.cme7t.v2.accounting.v1", "cohorts": cohorts, "native_complete": False,
                                "accounting_complete": False, "expected_hands": 20,
                                "counts": {"completed": 1}})
    assert len(rows) == 20
    assert sum(r["hand_status"] == "completed" for r in rows) == 1
    assert sum(r["hand_status"] == "interrupted" for r in rows) == 19
    assert all(r["profit"] is None for r in rows if r["hand_status"] != "completed")
