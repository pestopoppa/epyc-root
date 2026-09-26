"""Small paired fixture and provenance refusals for the offline selector screen."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "research"))
import selector_replay as replay

FIXTURE = ROOT / "tests" / "fixtures" / "selector_replay_v1"


def source_copy(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    for path in FIXTURE.iterdir():
        (root / path.name).write_bytes(path.read_bytes())
    return root / "source.json"


def test_fixture_freeze_replay_receipt_and_idempotence(tmp_path: Path) -> None:
    source = source_copy(tmp_path)
    package, result = tmp_path / "package", tmp_path / "result"
    first = replay.freeze(source, package)
    assert first == replay.freeze(source, package)
    index = replay.replay_both(package, result)
    assert index == replay.replay_both(package, result)
    aggregate = json.loads(index.read_text())
    assert aggregate["aggregate_sha256"] == replay.digest(
        replay.canonical(
            {k: v for k, v in aggregate.items() if k != "aggregate_sha256"}
        )
    )
    assert set(aggregate["variants"]) == {"rank", "weighted"}
    for variant in ("rank", "weighted"):
        for artifact in aggregate["variants"][variant].values():
            assert (
                replay.digest((result / artifact["path"]).read_bytes())
                == artifact["sha256"]
            )
    diagnostics = json.loads((result / "rank" / "diagnostics.json").read_text())
    assert diagnostics["arms"]["score_only"]["stop_rule"] == "no_heldout_improvement"
    assert diagnostics["arms"]["score_only"]["agreement_denominator"] == 4
    assert len(diagnostics["arms"]["hgm"]["time_split_paired_deltas"]) == 2
    weighted = json.loads((result / "weighted" / "diagnostics.json").read_text())
    assert weighted["shinka_variant"] == "weighted"
    assert diagnostics["shinka_variant"] == "rank"
    assert (result / "weighted" / "research-screen.json").exists()
    for arm in ("current", "score_only", "dgm", "hgm"):
        assert diagnostics["arms"][arm] == weighted["arms"][arm]
    native = replay.research_screen.native_rows(
        result / "rank" / "research-screen.json"
    )[0]["receipt"]
    assert native["counts"] == {
        "eligible": 20,
        "scored": 18,
        "failure": 2,
        "invalid": 0,
        "abstention": 0,
    }
    assert native["disposition"]["decision"] == "fixture_only"
    assert native["claim"]["class"] == "mechanism_feasibility"
    assert len((result / "rank" / "raw-outputs.jsonl").read_text().splitlines()) == 20


def test_missing_counterfactual_and_identity_fail_closed(tmp_path: Path) -> None:
    source = source_copy(tmp_path)
    spec = json.loads(source.read_text())
    del spec["identities"]["model_id"]
    source.write_text(json.dumps(spec))
    with pytest.raises(replay.ReplayRefusal, match="source.identities.model_id"):
        replay.freeze(source, tmp_path / "package")
    spec["identities"]["model_id"] = "fixture-no-model"
    source.write_text(json.dumps(spec))
    outcome_path = source.parent / "outcomes.json"
    outcomes = json.loads(outcome_path.read_text())
    del outcomes["d3"]["b"]
    outcome_path.write_text(json.dumps(outcomes))
    with pytest.raises(
        replay.ReplayRefusal, match=r"decision\[d3\].paired_continuations"
    ):
        replay.freeze(source, tmp_path / "package")


def test_future_feature_and_tampered_package_refused(tmp_path: Path) -> None:
    source = source_copy(tmp_path)
    graph_path = source.parent / "candidate-graph.json"
    graph = json.loads(graph_path.read_text())
    graph["decisions"][0]["eligible_candidates"][0]["feature_timestamp"] = (
        "2026-09-02T00:00:00Z"
    )
    graph_path.write_text(json.dumps(graph))
    with pytest.raises(replay.ReplayRefusal, match="leaks future"):
        replay.freeze(source, tmp_path / "package")
    graph_path.write_bytes((FIXTURE / "candidate-graph.json").read_bytes())
    replay.freeze(source, tmp_path / "package")
    copied_graph = tmp_path / "package" / "source-candidate_graph.json"
    copied_graph.write_bytes(copied_graph.read_bytes() + b" ")
    with pytest.raises(replay.ReplayRefusal, match="artifact digest mismatch"):
        replay.replay(tmp_path / "package", tmp_path / "result", "rank")


def test_tie_and_cold_start_are_explicit() -> None:
    decision = {
        "decision_id": "tie",
        "current_parent": "b",
        "eligible_candidates": [
            {
                "candidate_id": "b",
                "score": 0.5,
                "valid_children": 0,
                "offspring": 0,
                "dgm_g": 0.5,
                "descendant_outcomes": [],
            },
            {
                "candidate_id": "a",
                "score": 0.5,
                "valid_children": 0,
                "offspring": 0,
                "dgm_g": 0.5,
                "descendant_outcomes": [],
            },
        ],
    }
    profiles = json.loads((FIXTURE / "source.json").read_text())["profiles"]
    assert (
        replay._choose("score_only", copy.deepcopy(decision), profiles, "rank") == "a"
    )
    for arm in ("shinka", "dgm", "hgm"):
        assert replay._choose(arm, copy.deepcopy(decision), profiles, "rank") in (
            "a",
            "b",
        )
        assert replay._choose(
            arm, copy.deepcopy(decision), profiles, "rank"
        ) == replay._choose(arm, copy.deepcopy(decision), profiles, "rank")
    assert replay._choose("current", decision, profiles, "rank") == "b"


def test_failure_invalid_abstention_remain_in_denominator(tmp_path: Path) -> None:
    source = source_copy(tmp_path)
    outcome_path = source.parent / "outcomes.json"
    outcomes = json.loads(outcome_path.read_text())
    for did, cid, status in (("d1", "c", "invalid"), ("d2", "b", "abstention")):
        outcomes[did][cid]["status"] = status
        outcomes[did][cid].pop("value", None)
        outcomes[did][cid].pop("lineage_value", None)
        outcomes[did][cid]["reason"] = f"synthetic {status}"
    outcome_path.write_text(json.dumps(outcomes))
    replay.freeze(source, tmp_path / "package")
    replay.replay(tmp_path / "package", tmp_path / "result", "rank")
    receipt = replay.research_screen.native_rows(
        tmp_path / "result" / "research-screen.json"
    )[0]["receipt"]
    assert receipt["counts"]["eligible"] == 20
    assert receipt["counts"]["failure"] >= 1
    assert receipt["counts"]["invalid"] >= 1
    assert receipt["counts"]["abstention"] >= 1
    assert receipt["counts"]["eligible"] == sum(
        receipt["counts"][key] for key in replay.STATUSES
    )


def test_historical_audit_rejects_trial_only_rows(tmp_path: Path) -> None:
    journal = tmp_path / "historical.jsonl"
    journal.write_text(
        json.dumps({"decision_id": "x", "seq": {"candidate": "c", "k": 1}}) + "\n"
    )
    report = replay.audit_historical([journal], tmp_path / "frozen")
    assert report["replay_ready"] is False
    assert "decision.eligible_candidates" in report["missing_fields"]
    assert "decision.paired_continuations" in report["missing_fields"]
    assert report["disposition"] == "not_evaluable"
    assert report["audit_sha256"] == replay.digest(
        replay.canonical({k: v for k, v in report.items() if k != "audit_sha256"})
    )
    audit_path = tmp_path / "frozen" / "audit.json"
    audit_path.write_bytes(replay.canonical(report) + b"\n")
    assert replay.verify_audit(audit_path) == report
    (tmp_path / "frozen" / "journal-0.jsonl").write_text("changed")
    with pytest.raises(replay.ReplayRefusal, match="frozen bytes changed"):
        replay.verify_audit(audit_path)


def test_task_order_tamper_refused(tmp_path: Path) -> None:
    source = source_copy(tmp_path)
    replay.freeze(source, tmp_path / "package")
    order = tmp_path / "package" / "task-order.json"
    order.write_bytes(order.read_bytes() + b" ")
    with pytest.raises(replay.ReplayRefusal, match="task order digest mismatch"):
        replay.replay_both(tmp_path / "package", tmp_path / "result")


def test_historical_inventory_rejects_byte_mismatch(tmp_path: Path) -> None:
    journal = tmp_path / "journal.jsonl"
    journal.write_text('{"seq":{"candidate":"c"}}\n')
    pinned = {
        "sources": [
            {
                "path": str(journal),
                "bytes": len(journal.read_bytes()),
                "lines": 1,
                "sha256": "0" * 64,
            }
        ]
    }
    with pytest.raises(replay.ReplayRefusal, match="differs from pinned inventory"):
        replay.audit_historical([journal], tmp_path / "frozen", pinned)
    assert not (tmp_path / "frozen" / "journal-0.jsonl").exists()


def test_formula_config_and_cluster_provenance_are_required(tmp_path: Path) -> None:
    source = source_copy(tmp_path)
    spec = json.loads(source.read_text())
    del spec["profiles"]["dgm"]["g_D"]
    source.write_text(json.dumps(spec))
    with pytest.raises(replay.ReplayRefusal, match="dgm.g_D"):
        replay.freeze(source, tmp_path / "package")
    spec["profiles"]["dgm"]["g_D"] = "precomputed_per_candidate"
    source.write_text(json.dumps(spec))
    graph_path = source.parent / "candidate-graph.json"
    graph = json.loads(graph_path.read_text())
    graph["decisions"][3]["parent_cluster_id"] = graph["decisions"][2][
        "parent_cluster_id"
    ]
    graph_path.write_text(json.dumps(graph))
    with pytest.raises(replay.ReplayRefusal, match="two parent clusters"):
        replay.freeze(source, tmp_path / "package")


def test_no_future_descendant_or_derived_menu(tmp_path: Path) -> None:
    source = source_copy(tmp_path)
    spec = json.loads(source.read_text())
    spec["provenance"]["menu"] = "derived_from_parent_edges"
    source.write_text(json.dumps(spec))
    with pytest.raises(replay.ReplayRefusal, match="derived evidence"):
        replay.freeze(source, tmp_path / "package")
    spec["provenance"]["menu"] = "observed_raw"
    source.write_text(json.dumps(spec))
    graph_path = source.parent / "candidate-graph.json"
    graph = json.loads(graph_path.read_text())
    graph["decisions"][0]["eligible_candidates"][0]["descendant_outcomes"][0][
        "observed_at"
    ] = "2026-09-27T00:00:00Z"
    graph_path.write_text(json.dumps(graph))
    with pytest.raises(replay.ReplayRefusal, match="future descendant outcome"):
        replay.freeze(source, tmp_path / "package")
