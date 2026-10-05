"""Tests for the A9 offline pairwise preference-direction audit diagnostic."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_MOD_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "graph_router"
    / "audit_offline_reward_pairwise_preference_directions.py"
)
_spec = importlib.util.spec_from_file_location("a9_pref_dir_audit", _MOD_PATH)
assert _spec and _spec.loader
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _pair_row(
    *,
    pair_id: str,
    group_key: str,
    preferred_action: str,
    rejected_action: str,
    source_family: str = "seeding_eval",
    suite: str = "math",
) -> dict:
    return {
        "schema_version": "offline_reward_pairwise_preference.v1",
        "contract_name": "within_task_pairwise_preference_v1",
        "pair_id": pair_id,
        "group_key": group_key,
        "question_id": group_key,
        "suite": suite,
        "source_path": "/tmp/source.jsonl",
        "source_record_offset": 0,
        "source_family": source_family,
        "prompt_sha256": "p",
        "expected_sha256": "e",
        "preferred_item_id": f"{pair_id}:preferred",
        "rejected_item_id": f"{pair_id}:rejected",
        "preferred_role_key": preferred_action,
        "rejected_role_key": rejected_action,
        "preferred_canonical_action": preferred_action,
        "rejected_canonical_action": rejected_action,
    }


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "pairs.jsonl"
    p.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", encoding="utf-8")
    return p


def test_one_sided_thin_stratum_flagged_with_collection_target(tmp_path: Path) -> None:
    rows: list[dict] = []
    # Healthy stratum: balanced cross-action coverage, plenty of rows.
    for i in range(20):
        a, b = ("frontdoor", "coder_escalation") if i % 2 == 0 else ("coder_escalation", "frontdoor")
        rows.append(
            _pair_row(
                pair_id=f"ok{i}", group_key=f"g_ok{i}", preferred_action=a, rejected_action=b,
                source_family="three_way_eval", suite="livecodebench",
            )
        )
    # Weak stratum: only 3 rows, all one direction (frontdoor always preferred).
    for i in range(3):
        rows.append(
            _pair_row(
                pair_id=f"bad{i}", group_key=f"g_bad{i}",
                preferred_action="frontdoor", rejected_action="architect_general",
                source_family="seeding_eval", suite="thinking",
            )
        )

    summary = mod.audit_pairwise_preference_directions(rows)

    assert summary["schema_version"] == mod.AUDIT_SCHEMA_VERSION
    assert summary["decision"]["status"] == "preference_coverage_gaps_found"
    assert summary["decision"]["runtime_gate_change_allowed"] is False
    assert "source_family:seeding_eval" in summary["decision"]["weak_strata"]
    assert "suite:thinking" in summary["decision"]["weak_strata"]

    # The weak stratum's cross-action pair is one-sided -> a concrete target exists,
    # asking to collect the missing direction.
    targets = [
        t
        for t in summary["collection_targets"]
        if t["stratum_field"] == "source_family" and t["stratum_value"] == "seeding_eval"
    ]
    assert targets, "expected a collection target for the one-sided seeding_eval stratum"
    t0 = targets[0]
    assert t0["action_pair"] == "architect_general>frontdoor"
    assert t0["current_rows"] == 3
    assert t0["current_direction_balance"] == 0.0
    assert t0["needs_direction"] != ["balance both directions"]

    # The healthy stratum is not weak and emits no target.
    assert "suite:livecodebench" not in summary["decision"]["weak_strata"]
    assert not [t for t in summary["collection_targets"] if t["stratum_value"] == "livecodebench"]


def test_cli_writes_json_and_md(tmp_path: Path) -> None:
    rows = [
        _pair_row(
            pair_id=f"r{i}", group_key=f"g{i}",
            preferred_action="frontdoor" if i % 2 else "coder_escalation",
            rejected_action="coder_escalation" if i % 2 else "frontdoor",
        )
        for i in range(12)
    ]
    pairwise = _write(tmp_path, rows)
    aj = tmp_path / "audit.json"
    am = tmp_path / "audit.md"
    ct = tmp_path / "collection_targets.json"
    rc = mod.main(
        [
            "--pairwise-jsonl",
            str(pairwise),
            "--audit-json",
            str(aj),
            "--audit-md",
            str(am),
            "--collection-targets-json",
            str(ct),
        ]
    )
    assert rc == 0
    payload = json.loads(aj.read_text(encoding="utf-8"))
    assert payload["schema_version"] == mod.AUDIT_SCHEMA_VERSION
    assert payload["input"]["pair_rows"] == 12
    assert am.read_text(encoding="utf-8").startswith("# Pairwise preference-direction audit")
    compact = json.loads(ct.read_text(encoding="utf-8"))
    assert compact == mod.collection_targets_payload(payload)
    assert compact["schema_version"] == mod.COLLECTION_TARGETS_SCHEMA_VERSION
    assert compact["source_audit_schema_version"] == mod.AUDIT_SCHEMA_VERSION
    assert compact["decision"]["status"] == payload["decision"]["status"]
    assert compact["thresholds"] == payload["thresholds"]
    assert compact["collection_targets"] == payload["collection_targets"]


def test_bad_schema_version_errors(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"schema_version": "wrong"}) + "\n", encoding="utf-8")
    aj = tmp_path / "a.json"
    am = tmp_path / "a.md"
    rc = mod.main(["--pairwise-jsonl", str(bad), "--audit-json", str(aj), "--audit-md", str(am)])
    assert rc == 2
