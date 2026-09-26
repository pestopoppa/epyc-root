"""Prospective screen contract: refusal, evidence binding, and shared grading."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import research_screen as screen  # noqa: E402


def evidence(root: Path, name: str, content: bytes, *, rows: int | None = None) -> dict:
    path = root / name
    path.write_bytes(content)
    spec = {"path": name, "sha256": hashlib.sha256(content).hexdigest()}
    if rows is not None:
        spec["row_count"] = rows
    return spec


def jsonl(rows: list[dict]) -> bytes:
    return b"".join(json.dumps(row, sort_keys=True).encode() + b"\n" for row in rows)


def body(root: Path, kind: str = "selector_replay") -> dict:
    rows = [
        {
            "item_id": "a",
            "status": "scored",
            "output": "yes",
            "probabilities": {"yes": 0.8, "no": 0.2},
        },
        {"item_id": "b", "status": "abstention"},
    ]
    base = {
        "schema": screen.SCHEMA,
        "receipt_id": f"screen-{kind}-1",
        "run_id": "run-1",
        "timestamp": "2026-09-26T05:00:00Z",
        "source": {"kind": kind, "revision": "abc123"},
        "producer": {"name": "fixture-producer", "revision": "def456"},
        "input_manifest": evidence(root, "manifest.json", b"{}\n"),
        "baseline": {"id": "incumbent", "revision": "base123"},
        "raw_outputs": evidence(root, "rows.jsonl", jsonl(rows), rows=2),
        "window": {"kind": "holdout", "id": "held-1", "reason": ""},
        "counts": {
            "eligible": 2,
            "scored": 1,
            "failure": 0,
            "invalid": 0,
            "abstention": 1,
        },
        "rule": {"id": "stop-1", "revision": "rule123", "statement": "stop if no gain"},
        "disposition": {"decision": "stop", "reason": "gain below threshold"},
        "claim": {
            "class": "selector_causality",
            "metric": "heldout_gain",
            "value": 0.1,
            "unit": "fraction",
            "direction": "higher_better",
            "category": "CANDIDATE",
            "protocol_id": "",
            "text": "Frozen replay gain is 0.1",
            "reps_basis": "one scored held-out item",
        },
    }
    if kind == "selector_replay":
        selector_rows = [
            {"item_id": "a", "arm": arm, "status": "scored", "output": "p1"}
            for arm in sorted(screen.ARMS)
        ]
        base["raw_outputs"] = evidence(root, "rows.jsonl", jsonl(selector_rows), rows=5)
        base["counts"] = {
            "eligible": 5,
            "scored": 5,
            "failure": 0,
            "invalid": 0,
            "abstention": 0,
        }
        base["claim"]["reps_basis"] = "five scored arm decisions over one held-out item"
        base["profile"] = {
            "kind": kind,
            "journal": evidence(root, "journal.json", b"{}\n"),
            "candidate_graph": evidence(root, "graph.json", b"{}\n"),
            "task_order": evidence(root, "order.json", b"{}\n"),
            "policy_revision": "policy-1",
            "scorer_revision": "scorer-1",
            "selector_id": "selector-1",
            "scheduler_id": "scheduler-1",
            "archive_id": "archive-1",
            "endpoint_id": "endpoint-1",
            "eligibility_denominator": 5,
            "parent_choices": evidence(
                root,
                "parents.jsonl",
                jsonl(
                    [
                        {"item_id": "a", "arm": arm, "parent": "p1"}
                        for arm in sorted(screen.ARMS)
                    ]
                ),
                rows=5,
            ),
            "paired_continuations": evidence(
                root,
                "outcomes.jsonl",
                jsonl(
                    [
                        {"item_id": "a", "arm": arm, "result": 1}
                        for arm in sorted(screen.ARMS)
                    ]
                ),
                rows=5,
            ),
            "arms": ["current", "score_only", "shinka", "dgm", "hgm"],
            "holdout_id": "held-1",
            "tokens": None,
            "cost": None,
        }
    else:
        base["claim"]["class"] = "benchmark_performance"
        base["profile"] = {
            "kind": kind,
            "requested_model": "jev-latest",
            "resolved_model": "jev-1.13.0",
            "model_base": "",
            "model_head": "",
            "hosted_revision": "jev-1.13.0",
            "adapter_revision": "adapter-1",
            "config": evidence(root, "config.json", b"{}\n"),
            "dataset_manifest": evidence(root, "dataset.json", b"{}\n"),
            "component_timing": evidence(
                root, "component.json", b'{"samples_ms":[12.0]}\n'
            ),
            "sequential_timing": evidence(
                root, "sequential.json", b'{"samples_ms":[24.0]}\n'
            ),
            "billing": {
                "hosted": True,
                "evidence": evidence(
                    root,
                    "billing.json",
                    b'{"billed_cost":0.002,"currency":"USD","requests":2}\n',
                ),
            },
            "protocol_scope": "bounded hosted shadow; incumbent authoritative",
        }
    return base


def seal(root: Path, payload: dict) -> Path:
    path = root / "run.research-screen.json"
    screen.write_receipt(path, payload)
    return path


@pytest.mark.parametrize("kind", ["selector_replay", "typed_decision_shadow"])
def test_profiles_round_trip_and_shared_grader(tmp_path: Path, kind: str) -> None:
    path = seal(tmp_path, body(tmp_path, kind))
    native = screen.native_rows(path)[0]
    claim = screen.project(native)
    assert claim.extra["claim_class"] == (
        "selector_causality" if kind == "selector_replay" else "benchmark_performance"
    )
    assert claim.extra["counts"]["eligible"] == (5 if kind == "selector_replay" else 2)
    assert claim.reps == (5 if kind == "selector_replay" else 1)
    assert claim.attestation_verified is True
    assert ct.grade(claim)[:2] == ("Judged", "Located")


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda b: b.pop("rule"), "envelope"),
        (lambda b: b["counts"].update(eligible=1), "denominator"),
        (lambda b: b["claim"].update(**{"class": "unknown"}), "claim.class"),
        (lambda b: b["profile"].update(selector_id=""), "selector_id"),
        (
            lambda b: b["window"].update(kind="inapplicable", reason="none"),
            "inapplicable",
        ),
    ],
)
def test_selector_refusals(tmp_path: Path, change, match: str) -> None:
    payload = body(tmp_path)
    change(payload)
    with pytest.raises(ct.ProjectionError, match=match):
        seal(tmp_path, payload)


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda b: b["profile"].update(resolved_model=""), "resolved_model"),
        (lambda b: b["profile"]["billing"].update(evidence=None), "billing.evidence"),
        (lambda b: b["profile"].update(sequential_timing=None), "sequential_timing"),
    ],
)
def test_typed_identity_and_cost_timing_refusals(
    tmp_path: Path, change, match: str
) -> None:
    payload = body(tmp_path, "typed_decision_shadow")
    change(payload)
    with pytest.raises(ct.ProjectionError, match=match):
        seal(tmp_path, payload)


def test_raw_bytes_and_digest_refused(tmp_path: Path) -> None:
    path = seal(tmp_path, body(tmp_path, "typed_decision_shadow"))
    raw = tmp_path / "rows.jsonl"
    raw.write_bytes(raw.read_bytes().replace(b"0.8", b"0.9"))
    with pytest.raises(ct.ProjectionError, match="raw_outputs bytes"):
        screen.native_rows(path)
    payload = json.loads(path.read_text())
    payload["counts"]["scored"] = 2
    path.write_text(json.dumps(payload))
    with pytest.raises(ct.ProjectionError, match="self-hash"):
        screen.native_rows(path)


def test_row_status_and_probabilities_are_bound(tmp_path: Path) -> None:
    payload = body(tmp_path, "typed_decision_shadow")
    rows = [
        {
            "item_id": "a",
            "status": "scored",
            "output": "yes",
            "probabilities": {"yes": 0.7, "no": 0.7},
        },
        {"item_id": "b", "status": "abstention"},
    ]
    payload["raw_outputs"] = evidence(tmp_path, "rows.jsonl", jsonl(rows), rows=2)
    with pytest.raises(ct.ProjectionError, match="normalized"):
        seal(tmp_path, payload)
    rows[0]["probabilities"] = {"yes": 0.8, "no": 0.2}
    rows[1]["status"] = "failure"
    payload["raw_outputs"] = evidence(tmp_path, "rows.jsonl", jsonl(rows), rows=2)
    with pytest.raises(ct.ProjectionError, match="statuses"):
        seal(tmp_path, payload)


def test_deterministic_holdout_rationale(tmp_path: Path) -> None:
    payload = body(tmp_path, "typed_decision_shadow")
    payload["profile"] = {
        "kind": "deterministic_primitive",
        "primitive_id": "evaluator-preflight-v1",
        "conformance_artifact": evidence(tmp_path, "conformance.json", b"{}\n"),
        "provenance_artifact": evidence(tmp_path, "provenance.json", b"{}\n"),
    }
    payload["window"] = {
        "kind": "inapplicable",
        "id": "fixture-v1",
        "reason": "deterministic conformance fixture over pinned row bytes",
    }
    path = seal(tmp_path, payload)
    assert (
        screen.project(screen.native_rows(path)[0])
        .extra["window"]["reason"]
        .startswith("deterministic")
    )


def test_typed_shadow_cannot_skip_holdout(tmp_path: Path) -> None:
    payload = body(tmp_path, "typed_decision_shadow")
    payload["window"] = {
        "kind": "inapplicable",
        "id": "fixture-v1",
        "reason": "deterministic conformance fixture over pinned row bytes",
    }
    with pytest.raises(ct.ProjectionError, match="only deterministic primitives"):
        seal(tmp_path, payload)


def test_timing_and_billing_need_measured_content(tmp_path: Path) -> None:
    payload = body(tmp_path, "typed_decision_shadow")
    payload["profile"]["component_timing"] = evidence(
        tmp_path, "component.json", b"{}\n"
    )
    with pytest.raises(ct.ProjectionError, match="samples_ms"):
        seal(tmp_path, payload)
    payload = body(tmp_path, "typed_decision_shadow")
    payload["profile"]["billing"]["evidence"] = evidence(
        tmp_path, "billing.json", b"{}\n"
    )
    with pytest.raises(ct.ProjectionError, match="billed_cost"):
        seal(tmp_path, payload)


def test_selector_parent_rows_must_match_decisions(tmp_path: Path) -> None:
    payload = body(tmp_path)
    wrong = [
        {"item_id": "other" if arm == "dgm" else "a", "arm": arm, "parent": "p1"}
        for arm in sorted(screen.ARMS)
    ]
    payload["profile"]["parent_choices"] = evidence(
        tmp_path, "parents.jsonl", jsonl(wrong), rows=5
    )
    with pytest.raises(ct.ProjectionError, match="differ from raw item rows"):
        seal(tmp_path, payload)


def test_receipt_path_is_immutable(tmp_path: Path) -> None:
    payload = body(tmp_path)
    path = seal(tmp_path, payload)
    assert screen.write_receipt(path, payload)["receipt_sha256"]
    changed = dict(payload)
    changed["disposition"] = {"decision": "promote", "reason": "different decision"}
    with pytest.raises(ct.ProjectionError, match="already holds different bytes"):
        screen.write_receipt(path, changed)
