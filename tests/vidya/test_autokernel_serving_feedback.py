"""Real compare/archive/query bridge with only the measurement boundary synthetic."""
import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters.autokernel_legacy_serving import PlannerFeedback
from fold import fold
from gate import UsePolicy, evaluate
from lattice import parse_grade


@pytest.fixture
def source(tmp_path, monkeypatch):
    research = os.environ["EPYC_RESEARCH_ROOT"]
    monkeypatch.syspath_prepend(str(Path(research) / "scripts/kernel_rnd"))
    from autokernel.loop import archive, serving_beliefs
    from autokernel.loop.test_serving_beliefs import comparison
    row, calls = comparison(monkeypatch, floor_pct=100.0)
    assert row["decisive"] is False  # Original reducer, not an injected verdict.
    bridge = serving_beliefs.PlannerFeedback(tmp_path, ROOT)
    attempt = {"status": "measured_null", "mechanism_id": "remember-this-null", "comparison": row}
    assert archive.record(tmp_path, attempt, epoch="original-epoch",
                          recorded_at=datetime.now(timezone.utc).isoformat(), campaign_id="original-campaign",
                          on_serving_export=bridge.exported)
    inputs = row["belief_capture"]["inputs"]
    scope = {"epoch": "original-epoch", "model": inputs["resolved_arms"]["anchor"]["model"],
             "recipe_hash": row["recipe_hash"], "request_digest": row["request_digest"],
             "anchor_execution_digest": inputs["resolved_arms"]["anchor"]["execution_digest"],
             "anchor_build": inputs["build_paths"]["anchor"]}
    return bridge, scope, row, calls


def test_actual_archive_incremental_ingest_query_render_and_restart(source, tmp_path):
    from autokernel.loop import actors, archive, serving_beliefs
    bridge, scope, _, calls = source
    result = bridge.context(scope)
    assert result["status"] == "observations_only" and not result["errors"]
    row, = result["rows"]
    assert row["mechanism_id"] == "remember-this-null"
    assert row["native_decisive"] is False and row["anchor_tok_s"] == 11.0
    assert all(status["result"] == "allow" for status in row["belief_status"])
    original = bridge._reader.ledger.path.read_bytes()
    for _ in range(3):
        assert bridge.context(scope)["rows"][0]["capture_id"] == row["capture_id"]
    assert bridge._reader.ledger.path.read_bytes() == original
    resumed = serving_beliefs.PlannerFeedback(tmp_path, ROOT)
    assert resumed.context(scope)["rows"][0]["capture_id"] == row["capture_id"]
    assert resumed._reader.ledger.path.read_bytes() == original
    prior = archive.recall(tmp_path, epoch="original-epoch")
    assert prior[0]["status"] == "measured_null"
    text = actors.render_context({"prior_experiments": prior, "serving_observations": result})
    assert "measured_null" in text and "recall, not qualified gains" in text
    folded = fold([record.frame for record in bridge._reader.ledger.read_all()], as_of=result["as_of"])
    assert evaluate(row["belief_status"][0]["claim_id"], folded,
                    UsePolicy(use="qualified", floor=parse_grade("Witnessed/Attested"))).outcome != "allow"
    assert len(calls) == 4


@pytest.mark.parametrize("key", ["model", "recipe_hash", "request_digest", "epoch", "anchor_execution_digest", "anchor_build"])
def test_original_scope_mismatch_never_transfers_numbers(source, key):
    bridge, scope, _, _ = source
    other = copy.deepcopy(scope)
    other[key] = {**other[key], "sha256": "f" * 64} if key == "model" else "different"
    assert bridge.context(other)["rows"] == []
    assert bridge.context(None)["status"] == "scope_unavailable"


def test_moved_source_is_not_replaced_by_cached_numbers(source):
    bridge, scope, _, _ = source
    row = bridge.context(scope)["rows"][0]
    path = Path(row["source"])
    source = path.parent / json.loads(path.read_text())["native_reference"]["path"]
    source.rename(source.with_suffix(".moved"))
    result = bridge.context(scope)
    assert result["rows"] == [] and result["errors"]


def test_incremental_export_does_not_rescan_receipt_directory(source, monkeypatch):
    bridge, scope, _, _ = source
    path = Path(bridge.context(scope)["rows"][0]["source"])
    monkeypatch.setattr(os, "scandir", lambda *_: pytest.fail("not a startup scan"))
    before = bridge._reader.ledger.path.read_bytes()
    bridge.exported(path)
    assert bridge._reader.ledger.path.read_bytes() == before
    assert bridge.context(scope)["rows"]


def test_query_and_export_fault_do_not_erase_archive(source, tmp_path, monkeypatch, capsys):
    from autokernel.loop import archive
    bridge, scope, _, _ = source
    monkeypatch.setattr(bridge._reader, "context", lambda *_a, **_kw: (_ for _ in ()).throw(OSError("query fault")))
    assert bridge.context(scope)["status"] == "unavailable"
    assert "query fault" in capsys.readouterr().err
    assert archive.recall(tmp_path, epoch="original-epoch")[0]["status"] == "measured_null"


def test_source_and_context_bounds_are_explicit(source, monkeypatch):
    bridge, scope, _, _ = source
    monkeypatch.setattr(PlannerFeedback, "MAX_READ_BYTES", 1)
    result = bridge.context(scope)
    assert result["rows"] == [] and "query source byte bound reached" in result["errors"]


def test_actual_run_installs_feedback_and_rebinds_scope_after_keep(monkeypatch):
    research = Path(os.environ["EPYC_RESEARCH_ROOT"])
    monkeypatch.syspath_prepend(str(research / "scripts/kernel_rnd"))
    from autokernel.loop.test_existing_cpu_run import (
        test_existing_main_cpu_five_iterations_preserves_canonical_champion,
    )
    test_existing_main_cpu_five_iterations_preserves_canonical_champion(False, feedback_root=ROOT)


def test_first_export_recovers_transient_initialization_failure(source, tmp_path, monkeypatch, capsys):
    from autokernel.loop import serving_beliefs
    original, scope, _, _ = source
    receipt = Path(original.context(scope)["rows"][0]["source"])
    bridge = serving_beliefs.PlannerFeedback(tmp_path, ROOT)
    load = bridge._load
    def transient():
        raise OSError("temporary reader I/O")
    monkeypatch.setattr(bridge, "_load", transient)
    assert bridge.context(scope)["status"] == "unavailable"
    assert "temporary reader I/O" in capsys.readouterr().err
    monkeypatch.setattr(bridge, "_load", load)
    bridge.exported(receipt)
    result = bridge.context(scope)
    assert result["rows"] and not result["errors"]
