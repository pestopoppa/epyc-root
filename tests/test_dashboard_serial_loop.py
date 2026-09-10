"""Serial routing/child joins through original writers; no inference or new measurements."""
from __future__ import annotations

import importlib
import json
import os
import time
from pathlib import Path

import pytest

from dashboard import campaign_status, loop_status
from tests.test_dashboard_champion_headline import (
    champion_bundle,
    make_production_repo,
    recorded_loop,
)
from tests.test_dashboard_knowledge_card import build_fixture
from tests.test_dashboard_runtime_js import _page_js, _run


@pytest.fixture
def producer(monkeypatch):
    value = os.environ.get("EPYC_INFERENCE_RESEARCH_ROOT") or os.environ.get("EPYC_RESEARCH_ROOT")
    if not value:
        pytest.skip("set explicit EPYC_INFERENCE_RESEARCH_ROOT to the tested research checkout")
    root = Path(value).resolve()
    monkeypatch.syspath_prepend(str(root / "scripts/kernel_rnd"))
    module = importlib.import_module("autokernel.loop.status")
    assert Path(module.__file__).resolve().is_relative_to(root)
    assert "batch" in __import__("inspect").signature(module.write).parameters
    return module


@pytest.fixture
def sources(tmp_path, monkeypatch, producer):
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    original = recorded_loop()
    (canonical / "loop-status.json").write_text(json.dumps(original))
    prod_tree = tmp_path / "frozen-fixture"
    prod_sha = make_production_repo(prod_tree)
    (canonical / "champion-vs-production.json").write_text(json.dumps(champion_bundle(
        baseline_commit=prod_sha, champion_commit=original["champion_head"])))
    rows = build_fixture(canonical / "experiments.db")
    assert rows  # Copied original rows, not a zero-history fixture.
    monkeypatch.setattr(loop_status, "DEFAULT_STORE_ROOT", canonical)
    monkeypatch.setenv(loop_status.FROZEN_TREE_ENV, str(prod_tree))
    monkeypatch.setenv(loop_status.CHAMPION_TREE_ENV, str(tmp_path / "no-champion-tree"))
    for name in (campaign_status.STORE_ROOT_ENV, campaign_status.CAMPAIGN_ID_ENV,
                 campaign_status.CONFIG_GENERATION_ENV, campaign_status.CONFIG_DIGEST_ENV):
        monkeypatch.delenv(name, raising=False)
    router, child = tmp_path / "router", tmp_path / "target"
    active = {"target_index": 0, "selected_id": "fixture-cpu", "store": str(child),
              "batch_dir": str(router / "batches/batch-000000"),
              "pid": os.getpid(), "input_argv_sha256": "a" * 64}
    routing = {"target_count": 2, "rounds": 2, "batch_iterations": 3, "next_batch": 0,
               "stop_requested": False, "failed_targets": {}}
    producer.write(router, state="running", epoch="r", campaign_id="legacy-serial",
                   anchor_commit="", surface="serial_targets", pairs=0, noise_floor_pct=None,
                   target=active, routing=routing, stale_after_s=180)
    producer.write(child, state="running", epoch="child", campaign_id="ak-loop",
                   anchor_commit="b" * 40, surface="serving:fixture", pairs=5, noise_floor_pct=7.8,
                   iterations_planned=3, outcomes=[{"status": "measured_null",
                                                   "mechanism_id": "fixture-only"}],
                   target={"selected_id": active["selected_id"]},
                   batch={"output_dir": active["batch_dir"], "pid": active["pid"]},
                   baseline_scope="experimental_candidate_not_champion", stale_after_s=180)
    monkeypatch.setenv(loop_status.STORE_ROOT_ENV, str(router))
    return canonical, router, child, active, routing


def _rewrite(path, change):
    body = json.loads(path.read_text())
    change(body)
    path.write_text(json.dumps(body))


def test_original_writer_reader_page_keeps_canonical_history(sources, tmp_path):
    canonical, router, child, _active, _routing = sources
    baseline = loop_status.snapshot(canonical)[0]
    wire = loop_status.snapshot()[0]
    assert wire["serial"]["child"]["joined"]
    assert wire["serial"]["child"]["loop"]["iterations_done"] == 1
    assert wire["loop"]["iterations_done"] == 0
    assert wire["canonical_store_root"] == wire["knowledge_store_root"] == str(canonical)
    assert wire["champion_vs_production"]["evidence"] == baseline["champion_vs_production"]["evidence"]
    assert wire["champion_vs_production"]["measured"] == baseline["champion_vs_production"]["measured"]
    assert wire["knowledge"]["attempts"] == baseline["knowledge"]["attempts"] > 0
    rendered = _run(_page_js(), wire, tmp_path, ["render"])
    assert rendered["threw"] == []
    assert "1 / 3" in rendered["by_id"]["tiles"]
    assert "Routing cursor 0" in rendered["by_id"]["serial"]
    assert str(child) in rendered["by_id"]["serial"]
    assert str(canonical) in rendered["by_id"]["ident"]
    assert rendered["by_id"]["champ"] and rendered["by_id"]["know"]
    assert str(router) == wire["store_root"]
    wire["serial"]["routing"]["stop_requested"] = True
    stopping = _run(_page_js(), wire, tmp_path, ["renderSerial"])
    assert "STOP REQUESTED" in stopping["by_id"]["serial"]


@pytest.mark.parametrize("changed", ["missing_batch", "pid", "output_dir", "target_id"])
def test_older_or_foreign_child_is_not_current(sources, tmp_path, changed):
    _canonical, _router, child, _active, _routing = sources
    def change(body):
        if changed == "missing_batch":
            body.pop("batch")
        elif changed == "target_id":
            body["target"]["selected_id"] = "other"
        else:
            body["batch"][changed] = 999999 if changed == "pid" else "/other/batch"
    _rewrite(child / "loop-status.json", change)
    wire = loop_status.snapshot()[0]
    assert not wire["serial"]["child"]["joined"]
    assert wire["serial"]["child"]["loop"] is None
    rendered = _run(_page_js(), wire, tmp_path, ["render"])
    assert rendered["threw"] == []
    assert "No joined current-child details" in rendered["by_id"]["serial"]
    assert "1 / 3" not in rendered["by_id"]["tiles"]


@pytest.mark.parametrize("fault", ["stale", "failed", "malformed", "missing", "fifo", "symlink"])
def test_fresh_router_never_refreshes_child_errors(sources, tmp_path, fault):
    _canonical, _router, child, _active, _routing = sources
    path = child / "loop-status.json"
    if fault == "stale":
        _rewrite(path, lambda b: b.update(generated_at="2000-01-01T00:00:00Z"))
    elif fault == "failed":
        _rewrite(path, lambda b: b.update(state="failed"))
    elif fault == "malformed":
        path.write_text("{broken")
    else:
        path.unlink()
        if fault == "fifo":
            os.mkfifo(path)
        elif fault == "symlink":
            path.symlink_to(tmp_path / "other.json")
            (tmp_path / "other.json").write_text("{}")
    wire = loop_status.snapshot()[0]
    assert wire["freshness_state"] == "fresh"
    child_report = wire["serial"]["child"]
    if fault == "failed":
        assert child_report["notice"]["kind"] == "failed"
    else:
        assert child_report["freshness_state"] == (
            "stale" if fault == "stale" else "absent" if fault == "missing" else "malformed")
    rendered = _run(_page_js(), wire, tmp_path, ["renderSerial"])
    assert rendered["threw"] == []
    assert "does not refresh or qualify" in rendered["by_id"]["serial"]
    assert ("CHILD DECLARED FAILED" if fault == "failed" else child_report["freshness_state"]) in rendered["by_id"]["serial"]


@pytest.mark.parametrize("phase,stop,failures,label", [
    ("complete", False, {}, "complete"),
    ("complete", True, {}, "stopped"),
    ("complete", False, {"0": "failed"}, "complete_with_failures"),
    ("complete", False, {"0": "failed", "1": "failed"}, "all_failed"),
    ("failed", False, {"0": "failed", "1": "failed"}, "all_failed"),
])
def test_terminal_distinctions_do_not_claim_batch_iterations(sources, tmp_path, phase, stop, failures, label):
    _canonical, router, _child, _active, _routing = sources
    def change(body):
        body["state"] = phase
        body["target"] = {"stop_requested": stop, "failed_targets": failures}
        body["routing"].update(stop_requested=stop, failed_targets=failures, next_batch=4)
    _rewrite(router / "loop-status.json", change)
    wire = loop_status.snapshot()[0]
    assert wire["serial"]["state"] == label
    assert wire["serial"]["child"] is None
    rendered = _run(_page_js(), wire, tmp_path, ["render"])
    assert rendered["threw"] == []
    assert "1 / 3" not in rendered["by_id"]["tiles"]
    assert rendered["by_id"]["champ"] and rendered["by_id"]["know"]


def test_old_router_has_unknown_totals_and_malformed_fields_are_visible(sources):
    _canonical, router, _child, _active, _routing = sources
    _rewrite(router / "loop-status.json", lambda b: b.pop("routing"))
    assert loop_status.snapshot()[0]["serial"]["routing"] is None
    _rewrite(router / "loop-status.json", lambda b: b.update(routing=["not-a-mapping"]))
    wire = loop_status.snapshot()[0]
    assert wire["serial"]["state"] == "malformed"
    assert wire["serial"]["reader_error"]


def test_actual_owned_children_switch_and_preserve_original_history(sources, producer, tmp_path, monkeypatch):
    fixture = importlib.import_module("autokernel.loop.test_serial_run")
    sr = importlib.import_module("autokernel.loop.serial_run")
    child_source = fixture.CHILD.replace("count = 0 if stopped[0]", '''
from scripts.kernel_rnd.autokernel.loop import status
status.write(Path(sr.option(argv, "--store")), state="running", epoch="fixture",
    campaign_id="ak-loop", anchor_commit="a"*40, surface="fixture", pairs=5,
    noise_floor_pct=None, target=identity,
    batch={"output_dir": str(out), "pid": __import__("os").getpid()},
    iterations_planned=1, outcomes=[{"status":"measured_null","mechanism_id":"synthetic-only"}])
(out / "published").touch()
until = time.monotonic() + 5
while not (out / "read-by-hub").exists() and time.monotonic() < until:
    time.sleep(.01)
count = 0 if stopped[0]''')
    invocation_root = tmp_path / "actual"
    invocation_root.mkdir()
    router, argv = fixture._inputs(invocation_root, monkeypatch, rounds=1)
    (invocation_root / "child.py").write_text(child_source)
    monkeypatch.setenv(loop_status.STORE_ROOT_ENV, str(router))
    original_write = producer.write
    seen = []
    def observe(*args, **kwargs):
        result = original_write(*args, **kwargs)
        if kwargs["campaign_id"] == "legacy-serial" and kwargs["state"] == "running":
            directory = Path(kwargs["target"]["batch_dir"])
            until = time.monotonic() + 5
            while not (directory / "published").exists() and time.monotonic() < until:
                time.sleep(.01)
            assert (directory / "published").exists()
            wire, observation = loop_status.snapshot()
            assert wire["serial"]["child"]["joined"]
            assert wire["serial"]["child"]["loop"]["batch"]["pid"] == kwargs["target"]["pid"]
            seen.append((wire, observation.watermark))
            (directory / "read-by-hub").touch()
        return result
    monkeypatch.setattr(producer, "write", observe)
    assert sr.main(argv) == 0
    assert len(seen) == 2 and seen[0][1] != seen[1][1]
    assert seen[0][0]["serial"]["active"]["store"] != seen[1][0]["serial"]["active"]["store"]
    for wire, _mark in seen:
        assert wire["knowledge_store_root"] == str(sources[0])
        assert wire["knowledge"]["attempts"] > 0
        rendered = _run(_page_js(), wire, tmp_path, ["render"])
        assert rendered["threw"] == []
        assert "1 / 1" in rendered["by_id"]["tiles"]
    assert loop_status.snapshot()[0]["serial"]["state"] == "complete"
