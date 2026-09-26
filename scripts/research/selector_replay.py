"""Offline, fail-closed selector replay over a frozen candidate graph.

This is a diagnostic screen. It never generates candidates, changes a policy, or
assigns a counterfactual outcome to a parent without recorded paired evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vidya"))
from adapters import research_screen

ARMS = ("current", "score_only", "shinka", "dgm", "hgm")
STATUSES = ("scored", "failure", "invalid", "abstention")
IDENTITIES = (
    "policy_revision",
    "scorer_revision",
    "selector_id",
    "scheduler_id",
    "archive_id",
    "endpoint_id",
    "model_id",
    "decoding_id",
)
BUDGETS = ("evaluator_calls", "proposer_tokens", "proposer_cost", "wall_seconds")
FORMULAS = {
    "current": "recorded incumbent parent; no recomputation",
    "score_only": "maximum predecision score, then lexical candidate id",
    "shinka_rank": "seeded categorical draw; P(i) proportional to rank(i)^(-alpha)",
    "shinka_weighted": "seeded categorical draw; sigmoid(lambda*(score-median)/max(MAD,1e-6))/(1+offspring)",
    "dgm": "fixture/source-profile parameterization: seeded draw with supplied g_D values and configured (1+valid_children)^(-kappa_D); no canonical-DGM claim",
    "hgm": "seeded Beta Thompson draw from pooled predecision descendant outcomes",
}
SHINKA_VARIANTS = ("rank", "weighted")


class ReplayRefusal(ValueError):
    """The supplied record cannot support the requested replay."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_once(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ReplayRefusal(f"immutable output changed: {path}")
        return
    with path.open("xb") as stream:
        stream.write(raw)


def json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise ReplayRefusal(f"unreadable JSON: {path}") from exc


def rows_file(path: Path) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    except (OSError, ValueError) as exc:
        raise ReplayRefusal(f"unreadable JSONL: {path}") from exc
    if not all(isinstance(row, dict) for row in rows):
        raise ReplayRefusal(f"JSONL must contain objects: {path}")
    return rows


def required(obj: dict[str, Any], key: str, context: str) -> Any:
    if not isinstance(obj, dict):
        raise ReplayRefusal(f"{context} must be an object")
    if key not in obj or obj[key] is None or obj[key] == "":
        raise ReplayRefusal(f"missing {context}.{key}")
    return obj[key]


def finite(value: Any, context: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ReplayRefusal(f"{context} must be finite numeric")
    return float(value)


def utc(value: Any, context: str) -> datetime:
    if not isinstance(value, str):
        raise ReplayRefusal(f"{context} requires UTC timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReplayRefusal(f"{context} requires UTC timestamp") from exc
    if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
        raise ReplayRefusal(f"{context} requires UTC timestamp")
    return stamp


def audit_historical(
    journals: list[Path],
    package: Path | None = None,
    inventory: dict | None = None,
    inventory_artifact: dict | None = None,
) -> dict[str, Any]:
    """Inventory the real shards; explicitly refuse inferred menus and outcomes."""
    if not journals:
        raise ReplayRefusal("missing historical.journal")
    entries = []
    missing: set[str] = set()
    all_rows: list[dict] = []
    sequential_rows: list[dict] = []
    expected = inventory.get("sources") if inventory is not None else None
    if expected is not None and len(expected) != len(journals):
        raise ReplayRefusal("historical inventory source count differs")
    for index, path in enumerate(journals):
        raw = path.read_bytes()
        rows = rows_file(path)
        sequential = [
            row for row in rows if isinstance(row.get("seq"), dict) and row["seq"]
        ]
        if expected is not None:
            item = expected[index]
            if (
                path.resolve() != Path(item["path"]).resolve()
                or len(raw) != item["bytes"]
                or len(rows) != item["lines"]
                or digest(raw) != item["sha256"]
            ):
                raise ReplayRefusal(
                    f"historical source[{index}] differs from pinned inventory"
                )
        if package is not None:
            write_once(package / f"journal-{index}.jsonl", raw)
        all_rows.extend(rows)
        sequential_rows.extend(sequential)
        entries.append(
            {
                "path": str(path.resolve()),
                "frozen_path": str((package / f"journal-{index}.jsonl").resolve())
                if package
                else None,
                "sha256": digest(raw),
                "bytes": len(raw),
                "rows": len(rows),
                "sequential_rows": len(sequential),
            }
        )
        for row in sequential:
            if not isinstance(row.get("eligible_candidates"), list):
                missing.add("decision.eligible_candidates")
            if not isinstance(row.get("paired_continuations"), dict):
                missing.add("decision.paired_continuations")
            if not row.get("selector_revision"):
                missing.add("decision.selector_revision")
            if not row.get("model_id"):
                missing.add("decision.model_id")
            if not row.get("decoding_id"):
                missing.add("decision.decoding_id")
            if "explicit_abstention" not in row:
                missing.add("decision.explicit_abstention")
            if "eligibility_tie_break" not in row:
                missing.add("decision.eligibility_tie_break")
    missing.update(
        (
            "candidate_graph.predecision_features",
            "candidate_graph.clade_statistics",
            "candidate_graph.proposal_bytes",
            "continuation_design.same_task_seed_evaluator",
            "holdout.predeclared_chronological_split",
        )
    )
    full_ids = {
        row.get("trial_id") for row in all_rows if row.get("trial_id") is not None
    }
    seq_ids = {row.get("trial_id") for row in sequential_rows}
    parent_outside = [
        row.get("parent_trial")
        for row in sequential_rows
        if row.get("parent_trial") is not None and row["parent_trial"] not in seq_ids
    ]
    questions = [
        q
        for row in sequential_rows
        for q in row.get("eval_details", {}).get("question_results", [])
        if isinstance(q, dict)
    ]
    summary = {
        "sequential_rows": len(sequential_rows),
        "distinct_seq_candidates": len(
            {row["seq"].get("candidate") for row in sequential_rows}
        ),
        "git_tags_present": sum(bool(row.get("git_tag")) for row in sequential_rows),
        "parent_pointers_outside_seq_subset": len(parent_outside),
        "parent_pointers_resolved_in_full_journals": sum(
            parent in full_ids for parent in parent_outside
        ),
        "sequential_question_outcomes": len(questions),
        "distinct_sequential_qids": len({q.get("qid") for q in questions}),
    }
    report = {
        "schema": "epyc.selector_replay.audit.v1",
        "sources": entries,
        "inventory": inventory_artifact,
        "inventory_content_sha256": digest(canonical(inventory)) if inventory else None,
        "summary": summary,
        "capture_commit_reference": inventory.get("capture_commit_reference")
        if inventory
        else None,
        "cross_check": inventory.get("cross_check") if inventory else None,
        "scope": "journal shards only; no separate graph or paired-continuation artifact supplied",
        "replay_ready": False,
        "disposition": "not_evaluable",
        "incumbent_status": "recorded_parent_edges_only; selector menus/config unreconstructed",
        "missing_fields": sorted(missing),
        "reason": "trial outcomes alone do not identify unchosen-parent continuations",
    }
    report["audit_sha256"] = digest(canonical(report))
    return report


def verify_audit(path: Path) -> dict[str, Any]:
    """Check a sealed historical refusal against the copied raw bytes."""
    report = json_file(path)
    if report.get("schema") != "epyc.selector_replay.audit.v1":
        raise ReplayRefusal("historical audit schema mismatch")
    body = {key: value for key, value in report.items() if key != "audit_sha256"}
    if report.get("audit_sha256") != digest(canonical(body)):
        raise ReplayRefusal("historical audit self-hash mismatch")
    for index, source in enumerate(report["sources"]):
        frozen = source.get("frozen_path")
        if not frozen:
            raise ReplayRefusal(f"historical source[{index}] has no frozen copy")
        raw = Path(frozen).read_bytes()
        if len(raw) != source["bytes"] or digest(raw) != source["sha256"]:
            raise ReplayRefusal(f"historical source[{index}] frozen bytes changed")
    artifact = report.get("inventory")
    if artifact:
        raw = Path(artifact["path"]).read_bytes()
        if digest(raw) != artifact["sha256"]:
            raise ReplayRefusal("historical inventory bytes changed")
        if digest(canonical(json.loads(raw))) != report["inventory_content_sha256"]:
            raise ReplayRefusal("historical inventory content changed")
    rechecked = audit_historical(
        [Path(source["frozen_path"]) for source in report["sources"]]
    )
    if (
        rechecked["summary"] != report["summary"]
        or rechecked["missing_fields"] != report["missing_fields"]
    ):
        raise ReplayRefusal(
            "historical summary or missing-field inventory differs from frozen bytes"
        )
    receipt_path = path.parent / "research-screen.json"
    if receipt_path.exists():
        receipt = research_screen.native_rows(receipt_path)[0]["receipt"]
        if (
            receipt["profile"]["kind"] != "deterministic_primitive"
            or receipt["profile"]["conformance_artifact"]["sha256"]
            != digest(path.read_bytes())
            or artifact is None
            or receipt["input_manifest"]["sha256"] != artifact["sha256"]
            or receipt["profile"]["provenance_artifact"]["sha256"] != artifact["sha256"]
            or receipt["counts"]["eligible"] != len(report["missing_fields"])
            or receipt["counts"]["invalid"] != len(report["missing_fields"])
        ):
            raise ReplayRefusal("historical research-screen receipt differs from audit")
        rows = rows_file(path.parent / "missing-fields.jsonl")
        if [row.get("item_id") for row in rows] != report["missing_fields"]:
            raise ReplayRefusal("historical raw missing-field rows differ from audit")
    return report


def seal_historical_audit_receipt(audit_path: Path) -> Path:
    """Prospectively record the deterministic refusal after the audit is sealed."""
    report = verify_audit(audit_path)
    artifact = report.get("inventory")
    if artifact is None:
        raise ReplayRefusal("historical receipt requires pinned inventory artifact")
    inventory_path = Path(artifact["path"])
    if inventory_path.resolve().parent != audit_path.resolve().parent:
        raise ReplayRefusal(
            "historical receipt inventory must be frozen in audit package"
        )
    missing = report["missing_fields"]
    if report["disposition"] != "not_evaluable" or not missing:
        raise ReplayRefusal(
            "historical receipt requires a non-evaluable missing-field audit"
        )
    raw_rows = [
        {
            "item_id": field,
            "status": "invalid",
            "field": field,
            "reason": "required historical selector replay evidence absent",
        }
        for field in missing
    ]
    raw_spec = _emit_jsonl(audit_path.parent / "missing-fields.jsonl", raw_rows)
    receipt_path = audit_path.parent / "research-screen.json"
    timestamp = (
        json_file(receipt_path)["timestamp"]
        if receipt_path.exists()
        else datetime.now(timezone.utc).isoformat()
    )
    receipt_body = {
        "schema": research_screen.SCHEMA,
        "receipt_id": f"selector-audit-{report['audit_sha256'][:16]}",
        "run_id": f"historical-audit-{report['audit_sha256'][:16]}",
        "timestamp": timestamp,
        "source": {
            "kind": "historical_selector_audit",
            "revision": report["audit_sha256"],
        },
        "producer": {
            "name": "epyc-selector-replay-audit",
            "revision": digest(Path(__file__).read_bytes()),
        },
        "input_manifest": _spec(inventory_path),
        "baseline": {
            "id": "recorded_parent_edges_unreconstructed",
            "revision": report["capture_commit_reference"] or "historical-journal-only",
        },
        "raw_outputs": raw_spec,
        "window": {
            "kind": "inapplicable",
            "id": f"inventory-{artifact['sha256'][:16]}",
            "reason": "deterministic conformance and provenance audit of pinned historical journal bytes",
        },
        "counts": {
            "eligible": len(missing),
            "scored": 0,
            "failure": 0,
            "invalid": len(missing),
            "abstention": 0,
        },
        "rule": {
            "id": "selector-replay-evidence-gate",
            "revision": "1",
            "statement": "Refuse historical effect replay when any required observed field is absent.",
        },
        "disposition": {
            "decision": "not_evaluable",
            "reason": "historical replay evidence incomplete; no promotion authority",
        },
        "claim": {
            "class": "mechanism_feasibility",
            "metric": "replay_evidence_completeness",
            "value": 0,
            "unit": "fraction",
            "direction": "higher_better",
            "category": "CANDIDATE",
            "protocol_id": "selector-replay-audit-v1",
            "text": "Pinned historical journals lack required selector replay evidence; no promotion authority",
            "reps_basis": f"{len(missing)} required evidence fields absent in deterministic audit",
        },
        "profile": {
            "kind": "deterministic_primitive",
            "primitive_id": "selector-replay-historical-evidence-audit-v1",
            "conformance_artifact": _spec(audit_path),
            "provenance_artifact": _spec(inventory_path),
        },
    }
    research_screen.write_receipt(receipt_path, receipt_body)
    verify_audit(audit_path)
    return receipt_path


def _validate_source(
    spec: dict[str, Any], root: Path
) -> tuple[list[dict], dict, list[dict], dict]:
    if not isinstance(spec, dict):
        raise ReplayRefusal("source must be a JSON object")
    if spec.get("schema") != "epyc.selector_replay.source.v1":
        raise ReplayRefusal("missing source.schema=epyc.selector_replay.source.v1")
    kind = required(spec, "source_kind", "source")
    if kind not in ("synthetic_fixture", "historical"):
        raise ReplayRefusal(
            "source.source_kind must be synthetic_fixture or historical"
        )
    identities = required(spec, "identities", "source")
    for key in IDENTITIES:
        required(identities, key, "source.identities")
    budgets = required(spec, "budgets", "source")
    for key in BUDGETS:
        if (
            finite(required(budgets, key, "source.budgets"), f"source.budgets.{key}")
            < 0
        ):
            raise ReplayRefusal(f"source.budgets.{key} must be nonnegative")
    design = required(spec, "continuation_design", "source")
    if design != "same_task_seed_evaluator":
        raise ReplayRefusal(
            "source.continuation_design must be same_task_seed_evaluator"
        )
    provenance = required(spec, "provenance", "source")
    if not isinstance(provenance, dict):
        raise ReplayRefusal("source.provenance must be an object")
    for key, value in (
        ("menu", "observed_raw"),
        ("parent", "recorded_edge"),
        ("holdout", "predeclared_chronological"),
        ("outcome", "paired_recorded"),
    ):
        if provenance.get(key) != value:
            raise ReplayRefusal(
                f"source.provenance.{key} requires {value}; derived evidence is not eligible"
            )
    declared_at = utc(
        required(provenance, "holdout_declared_at", "source.provenance"),
        "source.provenance.holdout_declared_at",
    )
    profiles = required(spec, "profiles", "source")
    if not isinstance(profiles, dict):
        raise ReplayRefusal("source.profiles must be an object")
    shinka = required(profiles, "shinka", "source.profiles")
    if (
        finite(required(shinka, "rank_alpha", "source.profiles.shinka"), "rank_alpha")
        <= 0
    ):
        raise ReplayRefusal("source.profiles.shinka.rank_alpha must be positive")
    if (
        finite(
            required(shinka, "weighted_lambda", "source.profiles.shinka"),
            "weighted_lambda",
        )
        <= 0
    ):
        raise ReplayRefusal("source.profiles.shinka.weighted_lambda must be positive")
    required(shinka, "source_profile", "source.profiles.shinka")
    if type(required(shinka, "seed", "source.profiles.shinka")) is not int:
        raise ReplayRefusal("source.profiles.shinka.seed must be an integer")
    dgm = required(profiles, "dgm", "source.profiles")
    if dgm.get("g_D") != "precomputed_per_candidate":
        raise ReplayRefusal(
            "source.profiles.dgm.g_D must supply precomputed_per_candidate values"
        )
    if finite(required(dgm, "kappa_D", "source.profiles.dgm"), "kappa_D") < 0:
        raise ReplayRefusal("source.profiles.dgm.kappa_D must be nonnegative")
    if dgm.get("valid_child_rule") != "observed_valid_children_zero_floor_one":
        raise ReplayRefusal(
            "source.profiles.dgm.valid_child_rule missing or unsupported"
        )
    required(dgm, "source_profile", "source.profiles.dgm")
    if type(required(dgm, "seed", "source.profiles.dgm")) is not int:
        raise ReplayRefusal("source.profiles.dgm.seed must be an integer")
    hgm = required(profiles, "hgm", "source.profiles")
    if hgm.get("outcome_mapping") != "identity_unit_interval":
        raise ReplayRefusal(
            "source.profiles.hgm.outcome_mapping must pin identity_unit_interval"
        )
    if hgm.get("pseudo_descendant_semantics") != "beta_fractional_success_failure":
        raise ReplayRefusal(
            "source.profiles.hgm.pseudo_descendant_semantics missing or unsupported"
        )
    for key in ("prior_alpha", "prior_beta"):
        if finite(required(hgm, key, "source.profiles.hgm"), key) <= 0:
            raise ReplayRefusal(f"source.profiles.hgm.{key} must be positive")
    if type(required(hgm, "seed", "source.profiles.hgm")) is not int:
        raise ReplayRefusal("source.profiles.hgm.seed must be an integer")
    paths = required(spec, "files", "source")
    for name in ("journal", "candidate_graph", "outcomes"):
        required(paths, name, "source.files")
    journal = rows_file(root / paths["journal"])
    graph = json_file(root / paths["candidate_graph"])
    outcomes = json_file(root / paths["outcomes"])
    if not isinstance(graph, dict) or not isinstance(graph.get("decisions"), list):
        raise ReplayRefusal("missing candidate_graph.decisions")
    decisions = graph["decisions"]
    if not isinstance(outcomes, dict):
        raise ReplayRefusal("missing outcomes object")
    journal_by_id = {row.get("decision_id"): row for row in journal}
    if len(journal_by_id) != len(journal):
        raise ReplayRefusal("journal has duplicate decision_id")
    seen: set[str] = set()
    previous = None
    holdout_started = False
    holdout_blocks: list[str] = []
    holdout_clusters: set[str] = set()
    first_holdout_time: datetime | None = None
    for d in decisions:
        ident = required(d, "decision_id", "candidate_graph.decision")
        if ident in seen:
            raise ReplayRefusal(f"duplicate decision_id {ident}")
        seen.add(ident)
        stamp = utc(
            required(d, "timestamp", f"decision[{ident}]"),
            f"decision[{ident}].timestamp",
        )
        if previous is not None and stamp <= previous:
            raise ReplayRefusal(
                "candidate_graph decisions must be strictly time ordered"
            )
        previous = stamp
        split = required(d, "split", f"decision[{ident}]")
        if split not in ("development", "holdout") or (
            holdout_started and split != "holdout"
        ):
            raise ReplayRefusal("holdout must be a later contiguous time window")
        holdout_started |= split == "holdout"
        if split == "holdout":
            if first_holdout_time is None:
                first_holdout_time = stamp
            block = required(d, "holdout_block", f"decision[{ident}]")
            if not holdout_blocks or block != holdout_blocks[-1]:
                if block in holdout_blocks:
                    raise ReplayRefusal(
                        "holdout blocks must be chronological and contiguous"
                    )
                holdout_blocks.append(block)
            holdout_clusters.add(required(d, "parent_cluster_id", f"decision[{ident}]"))
        for key in ("task_id", "current_parent", "seed", "evaluator_id"):
            required(d, key, f"decision[{ident}]")
        j = journal_by_id.get(ident)
        if (
            j is None
            or j.get("selected_parent") != d["current_parent"]
            or j.get("timestamp") != d["timestamp"]
        ):
            raise ReplayRefusal(
                f"journal choice/timestamp mismatch for decision[{ident}]"
            )
        candidates = required(d, "eligible_candidates", f"decision[{ident}]")
        if not isinstance(candidates, list) or not candidates:
            raise ReplayRefusal(
                f"decision[{ident}].eligible_candidates must be nonempty"
            )
        ids = set()
        for c in candidates:
            cid = required(c, "candidate_id", f"decision[{ident}].candidate")
            if cid in ids:
                raise ReplayRefusal(f"decision[{ident}] has duplicate candidate {cid}")
            ids.add(cid)
            finite(required(c, "score", f"decision[{ident}].candidate[{cid}]"), "score")
            for key in ("valid_children", "offspring", "dgm_g"):
                number = finite(
                    required(c, key, f"decision[{ident}].candidate[{cid}]"), key
                )
                if number < 0:
                    raise ReplayRefusal(
                        f"decision[{ident}].candidate[{cid}].{key} must be nonnegative"
                    )
                if key != "dgm_g" and type(c[key]) is not int:
                    raise ReplayRefusal(
                        f"decision[{ident}].candidate[{cid}].{key} must be integer count"
                    )
            descendants = required(c, "descendant_outcomes", f"candidate[{cid}]")
            if not isinstance(descendants, list):
                raise ReplayRefusal(
                    f"candidate[{cid}].descendant_outcomes must be a list"
                )
            descendant_ids: set[str] = set()
            for observation in descendants:
                descendant_id = required(
                    observation, "descendant_id", f"candidate[{cid}].descendant"
                )
                if descendant_id in descendant_ids:
                    raise ReplayRefusal(
                        f"candidate[{cid}] duplicate descendant outcome"
                    )
                descendant_ids.add(descendant_id)
                value = finite(
                    required(observation, "value", f"candidate[{cid}].descendant"),
                    "descendant.value",
                )
                if not 0 <= value <= 1:
                    raise ReplayRefusal(
                        f"candidate[{cid}] descendant outcome must be mapped to [0,1]"
                    )
                if (
                    utc(
                        required(
                            observation, "observed_at", f"candidate[{cid}].descendant"
                        ),
                        "descendant.observed_at",
                    )
                    > stamp
                ):
                    raise ReplayRefusal(
                        f"candidate[{cid}] leaks future descendant outcome"
                    )
            if (
                utc(
                    required(c, "feature_timestamp", f"candidate[{cid}]"),
                    f"candidate[{cid}].feature_timestamp",
                )
                > stamp
            ):
                raise ReplayRefusal(
                    f"decision[{ident}] leaks future candidate features"
                )
        if d["current_parent"] not in ids:
            raise ReplayRefusal(
                f"decision[{ident}].current_parent absent from eligible menu"
            )
        paired = outcomes.get(ident)
        if not isinstance(paired, dict) or set(paired) != ids:
            raise ReplayRefusal(
                f"decision[{ident}].paired_continuations must cover every eligible parent"
            )
        for cid, outcome in paired.items():
            if outcome.get("status") not in STATUSES:
                raise ReplayRefusal(
                    f"decision[{ident}].continuation[{cid}].status invalid"
                )
            required(outcome, "lineage_id", f"decision[{ident}].continuation[{cid}]")
            for key in ("task_id", "seed", "evaluator_id"):
                if outcome.get(key) != d[key]:
                    raise ReplayRefusal(
                        f"decision[{ident}].continuation[{cid}].{key} differs"
                    )
            if outcome["status"] == "scored":
                finite(
                    required(
                        outcome, "value", f"decision[{ident}].continuation[{cid}]"
                    ),
                    "continuation.value",
                )
                finite(
                    required(
                        outcome,
                        "lineage_value",
                        f"decision[{ident}].continuation[{cid}]",
                    ),
                    "continuation.lineage_value",
                )
            if (
                utc(
                    required(outcome, "observed_at", f"continuation[{cid}]"),
                    "continuation.observed_at",
                )
                <= stamp
            ):
                raise ReplayRefusal(
                    f"decision[{ident}].continuation[{cid}] predates decision"
                )
    if set(journal_by_id) != seen:
        raise ReplayRefusal("journal and candidate graph decision sets differ")
    if not any(d["split"] == "development" for d in decisions) or not holdout_started:
        raise ReplayRefusal("source requires development and later holdout decisions")
    if first_holdout_time is None or declared_at >= first_holdout_time:
        raise ReplayRefusal(
            "holdout declaration must precede the first held-out decision"
        )
    if len(holdout_blocks) < 2 or len(holdout_clusters) < 2:
        raise ReplayRefusal(
            "holdout requires two chronological blocks and two parent clusters"
        )
    return journal, graph, decisions, outcomes


def freeze(source: Path, package: Path) -> Path:
    """Copy the exact source bytes and seal one immutable package manifest."""
    spec = json_file(source)
    journal, _, decisions, _ = _validate_source(spec, source.parent)
    package.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for name, rel in sorted(spec["files"].items()):
        src = source.parent / rel
        raw = src.read_bytes()
        dest = package / f"source-{name}{src.suffix}"
        write_once(dest, raw)
        artifacts[name] = {"path": dest.name, "sha256": digest(raw)}
    raw_source = source.read_bytes()
    write_once(package / "source-spec.json", raw_source)
    order = [
        {
            "decision_id": d["decision_id"],
            "timestamp": d["timestamp"],
            "task_id": d["task_id"],
            "split": d["split"],
        }
        for d in decisions
    ]
    order_bytes = canonical(order) + b"\n"
    write_once(package / "task-order.json", order_bytes)
    manifest = {
        "schema": "epyc.selector_replay.package.v1",
        "source_kind": spec["source_kind"],
        "source_sha256": digest(raw_source),
        "task_order_sha256": digest(order_bytes),
        "task_order_rows": len(order),
        "artifacts": artifacts,
        "runner_sha256": digest(Path(__file__).read_bytes()),
        "python_version": sys.version.split()[0],
        "identities": spec["identities"],
        "budgets": spec["budgets"],
        "profiles": spec["profiles"],
        "provenance": spec["provenance"],
        "continuation_design": spec["continuation_design"],
        "decision_count": len(decisions),
        "journal_rows": len(journal),
        "holdout_id": spec["holdout_id"],
        "holdout_decisions": [
            d["decision_id"] for d in decisions if d["split"] == "holdout"
        ],
        "formulas": FORMULAS,
        "tie_rule": "lexical candidate_id for equal score/rank or equal sampled weight",
        "cold_start": "zero offspring and valid children use denominator one; zero descendants sample frozen Beta prior",
    }
    manifest["manifest_sha256"] = digest(canonical(manifest))
    path = package / "manifest.json"
    write_once(path, canonical(manifest) + b"\n")
    return path


def _draw(weights: list[tuple[str, float]], seed: int) -> str:
    ordered = sorted(weights)
    total = sum(weight for _, weight in ordered)
    if total <= 0 or not math.isfinite(total):
        raise ReplayRefusal("selector has no finite positive sampling mass")
    target = random.Random(seed).random() * total
    for candidate, weight in ordered:
        target -= weight
        if target < 0:
            return candidate
    return ordered[-1][0]


def _seed(profile_seed: Any, decision_id: str, arm: str, variant: str) -> int:
    return int(digest(canonical([profile_seed, decision_id, arm, variant]))[:16], 16)


def _choose(arm: str, decision: dict, profiles: dict, variant: str) -> str:
    candidates = decision["eligible_candidates"]
    if arm == "current":
        return decision["current_parent"]
    ranked = sorted(candidates, key=lambda c: (-c["score"], c["candidate_id"]))
    ranks = {c["candidate_id"]: index + 1 for index, c in enumerate(ranked)}
    if arm == "score_only":
        return ranked[0]["candidate_id"]
    if arm == "shinka":
        profile = profiles["shinka"]
        if variant == "rank":
            weights = [
                (c["candidate_id"], ranks[c["candidate_id"]] ** -profile["rank_alpha"])
                for c in candidates
            ]
        else:
            scores = sorted(float(c["score"]) for c in candidates)
            midpoint = len(scores) // 2
            median = (
                scores[midpoint]
                if len(scores) % 2
                else (scores[midpoint - 1] + scores[midpoint]) / 2
            )
            deviations = sorted(abs(score - median) for score in scores)
            mad = (
                deviations[midpoint]
                if len(deviations) % 2
                else (deviations[midpoint - 1] + deviations[midpoint]) / 2
            )
            scale = max(mad, 1e-6)
            weights = []
            for c in candidates:
                z = profile["weighted_lambda"] * (c["score"] - median) / scale
                sigmoid = 1 / (1 + math.exp(-max(-700, min(700, z))))
                weights.append((c["candidate_id"], sigmoid / (1 + c["offspring"])))
        return _draw(
            weights, _seed(profile["seed"], decision["decision_id"], arm, variant)
        )
    if arm == "dgm":
        profile = profiles["dgm"]
        weights = [
            (
                c["candidate_id"],
                c["dgm_g"] / (1 + c["valid_children"]) ** profile["kappa_D"],
            )
            for c in candidates
        ]
        return _draw(
            weights, _seed(profile["seed"], decision["decision_id"], arm, "fixed")
        )
    if arm == "hgm":
        profile = profiles["hgm"]
        rng = random.Random(
            _seed(profile["seed"], decision["decision_id"], arm, "fixed")
        )
        sampled = []
        for c in sorted(candidates, key=lambda c: c["candidate_id"]):
            values = [row["value"] for row in c["descendant_outcomes"]]
            alpha = profile["prior_alpha"] + sum(values)
            beta = profile["prior_beta"] + sum(1 - value for value in values)
            sampled.append((c["candidate_id"], rng.betavariate(alpha, beta)))
        return min(sampled, key=lambda pair: (-pair[1], pair[0]))[0]
    raise ReplayRefusal(f"unknown arm: {arm}")


def _spec(path: Path, rows: int | None = None) -> dict:
    result = {"path": path.name, "sha256": digest(path.read_bytes())}
    if rows is not None:
        result["row_count"] = rows
    return result


def _emit_jsonl(path: Path, rows: list[dict]) -> dict:
    write_once(path, b"".join(canonical(row) + b"\n" for row in rows))
    return _spec(path, len(rows))


def replay(package: Path, result: Path, variant: str) -> dict:
    if variant not in SHINKA_VARIANTS:
        raise ReplayRefusal("Shinka variant must be explicitly rank or weighted")
    manifest = json_file(package / "manifest.json")
    if manifest.get("schema") != "epyc.selector_replay.package.v1":
        raise ReplayRefusal("invalid package manifest schema")
    manifest_body = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if manifest.get("manifest_sha256") != digest(canonical(manifest_body)):
        raise ReplayRefusal("package manifest self-hash mismatch")
    if manifest.get("runner_sha256") != digest(Path(__file__).read_bytes()):
        raise ReplayRefusal("package runner revision differs from current code")
    if manifest.get("python_version") != sys.version.split()[0]:
        raise ReplayRefusal(
            "package Python version differs from pinned sampling runtime"
        )
    for name, artifact in manifest["artifacts"].items():
        if digest((package / artifact["path"]).read_bytes()) != artifact["sha256"]:
            raise ReplayRefusal(f"package artifact digest mismatch: {name}")
    if digest((package / "source-spec.json").read_bytes()) != manifest["source_sha256"]:
        raise ReplayRefusal("package source spec digest mismatch")
    if (
        digest((package / "task-order.json").read_bytes())
        != manifest["task_order_sha256"]
    ):
        raise ReplayRefusal("package task order digest mismatch")
    if (
        len(json_file(package / "task-order.json")) != manifest["task_order_rows"]
        or manifest["task_order_rows"] != manifest["decision_count"]
    ):
        raise ReplayRefusal("package task order row count mismatch")
    spec = json_file(package / "source-spec.json")
    copied = {**spec, "files": {k: v["path"] for k, v in manifest["artifacts"].items()}}
    _, _, decisions, outcomes = _validate_source(copied, package)
    if manifest["formulas"] != FORMULAS:
        raise ReplayRefusal("package formulas differ from runner revision")
    result.mkdir(parents=True, exist_ok=True)
    raw, parents, continuations = [], [], []
    choices: dict[str, dict[str, str]] = {arm: {} for arm in ARMS}
    counts = {key: 0 for key in STATUSES}
    for d in decisions:
        ident = d["decision_id"]
        for arm in ARMS:
            parent = _choose(arm, d, manifest["profiles"], variant)
            outcome = outcomes[ident][parent]
            status = outcome["status"]
            choices[arm][ident] = parent
            row = {
                "item_id": ident,
                "arm": arm,
                "status": status,
                "parent": parent,
                "split": d["split"],
                "task_id": d["task_id"],
                "lineage_id": outcome["lineage_id"],
                "shinka_variant": variant,
            }
            if status == "scored":
                row["result"] = outcome["value"]
                row["lineage_value"] = outcome["lineage_value"]
                continuations.append(
                    {
                        "item_id": ident,
                        "arm": arm,
                        "result": outcome["value"],
                        "parent": parent,
                        "lineage_id": outcome["lineage_id"],
                        "lineage_value": outcome["lineage_value"],
                        "source_outcome_sha256": digest(canonical(outcome)),
                    }
                )
            else:
                row["reason"] = outcome.get("reason", "recorded non-score")
            raw.append(row)
            parents.append({"item_id": ident, "arm": arm, "parent": parent})
            counts[status] += 1
    raw_spec = _emit_jsonl(result / "raw-outputs.jsonl", raw)
    parent_spec = _emit_jsonl(result / "parent-choices.jsonl", parents)
    continuation_spec = _emit_jsonl(
        result / "paired-continuations.jsonl", continuations
    )
    holdout = [d for d in decisions if d["split"] == "holdout"]
    current = choices["current"]
    diagnostics = {
        "schema": "epyc.selector_replay.result.v1",
        "source_kind": manifest["source_kind"],
        "holdout_id": manifest["holdout_id"],
        "holdout_decisions": len(holdout),
        "shinka_variant": variant,
        "arms": {},
        "budgets": manifest["budgets"],
        "profiles": manifest["profiles"],
        "formulas": FORMULAS,
    }

    def heldout_values(arm: str) -> list[float] | None:
        selected = [
            outcomes[d["decision_id"]][choices[arm][d["decision_id"]]] for d in holdout
        ]
        return (
            [float(o["value"]) for o in selected]
            if all(o["status"] == "scored" for o in selected)
            else None
        )

    def heldout_lineage_values(arm: str) -> list[float] | None:
        selected = [
            outcomes[d["decision_id"]][choices[arm][d["decision_id"]]] for d in holdout
        ]
        return (
            [float(o["lineage_value"]) for o in selected]
            if all(o["status"] == "scored" for o in selected)
            else None
        )

    baseline_values = heldout_values("current")
    score_values = heldout_values("score_only")
    baseline = (
        sum(baseline_values) / len(holdout) if baseline_values is not None else None
    )
    score_mean = sum(score_values) / len(holdout) if score_values is not None else None
    diagnostics["incumbent_holdout_mean"] = baseline
    diagnostics["score_only_holdout_mean"] = score_mean
    for arm in ARMS:
        agreement = sum(
            choices[arm][d["decision_id"]] == current[d["decision_id"]]
            for d in decisions
        )
        vals = heldout_values(arm)
        lineage_vals = heldout_lineage_values(arm)
        arm_mean = sum(vals) / len(holdout) if vals is not None else None
        gain = (
            arm_mean - baseline
            if arm_mean is not None and baseline is not None
            else None
        )
        paired_deltas = (
            [a - b for a, b in zip(vals, baseline_values)]
            if vals is not None and baseline_values is not None
            else []
        )
        by_block: dict[str, list[float]] = {}
        by_cluster: dict[str, list[float]] = {}
        for decision, delta in zip(holdout, paired_deltas):
            by_block.setdefault(decision["holdout_block"], []).append(delta)
            by_cluster.setdefault(decision["parent_cluster_id"], []).append(delta)
        time_split = [sum(values) / len(values) for values in by_block.values()]
        rng = random.Random(
            _seed(
                manifest["holdout_id"],
                arm,
                variant if arm == "shinka" else "fixed",
                "cluster-bootstrap",
            )
        )
        clusters = sorted(by_cluster)
        boot = []
        if len(clusters) >= 2:
            for _ in range(1000):
                sampled = [
                    value
                    for _ in clusters
                    for value in by_cluster[rng.choice(clusters)]
                ]
                boot.append(sum(sampled) / len(sampled))
        bootstrap_positive = (
            sum(value > 0 for value in boot) / len(boot) if boot else None
        )
        if arm == "current":
            stop = "baseline"
        elif agreement / len(decisions) >= 0.95:
            stop = "choice_agreement_at_least_95pct"
        elif gain is None:
            stop = "missing_scored_paired_continuation"
        elif arm not in ("current", "score_only") and score_mean is None:
            stop = "missing_score_only_control"
        elif gain <= 0 or (
            arm not in ("current", "score_only")
            and score_mean is not None
            and arm_mean <= score_mean
        ):
            stop = "no_heldout_improvement"
        elif len(time_split) < 2 or min(time_split) < 0:
            stop = "holdout_reversal"
        elif bootstrap_positive is None or bootstrap_positive < 0.95:
            stop = "unstable_bootstrap"
        else:
            stop = "bounded_followup_eligible"
        diagnostics["arms"][arm] = {
            "agreement_n": agreement,
            "agreement_denominator": len(decisions),
            "agreement_fraction": agreement / len(decisions),
            "holdout_mean": arm_mean,
            "heldout_gain_vs_current": gain,
            "time_split_blocks": list(by_block),
            "time_split_paired_deltas": time_split,
            "heldout_lineage_mean": sum(lineage_vals) / len(lineage_vals)
            if lineage_vals is not None
            else None,
            "bootstrap_cluster_count": len(clusters),
            "bootstrap_replicates": len(boot),
            "bootstrap_positive_fraction": bootstrap_positive,
            "stop_rule": stop,
        }
    write_once(result / "diagnostics.json", canonical(diagnostics) + b"\n")
    write_once(result / "input-manifest.json", (package / "manifest.json").read_bytes())
    for source_name, result_name in (
        ("journal", "journal.jsonl"),
        ("candidate_graph", "candidate-graph.json"),
    ):
        data = (package / manifest["artifacts"][source_name]["path"]).read_bytes()
        write_once(result / result_name, data)
    write_once(result / "task-order.json", (package / "task-order.json").read_bytes())
    terminal = (
        "fixture_only" if manifest["source_kind"] == "synthetic_fixture" else "stop"
    )
    reason = (
        "synthetic conformance only"
        if terminal == "fixture_only"
        else "stop rules evaluated on held-out recorded continuations"
    )
    old_receipt = result / "research-screen.json"
    timestamp = (
        json_file(old_receipt)["timestamp"]
        if old_receipt.exists()
        else datetime.now(timezone.utc).isoformat()
    )
    receipt_body = {
        "schema": research_screen.SCHEMA,
        "receipt_id": f"selector-{variant}-{digest((package / 'manifest.json').read_bytes())[:16]}",
        "run_id": f"replay-{variant}-{digest((package / 'manifest.json').read_bytes())[:16]}",
        "timestamp": timestamp,
        "source": {"kind": "selector_replay", "revision": manifest["source_sha256"]},
        "producer": {
            "name": "epyc-selector-replay",
            "revision": manifest["runner_sha256"],
        },
        "input_manifest": _spec(result / "input-manifest.json"),
        "baseline": {
            "id": "current",
            "revision": manifest["identities"]["policy_revision"],
        },
        "raw_outputs": raw_spec,
        "window": {"kind": "holdout", "id": manifest["holdout_id"], "reason": ""},
        "counts": {"eligible": len(raw), **counts},
        "rule": {
            "id": "selector-stop-v1",
            "revision": "1",
            "statement": "Stop at >=95% agreement, no gain over incumbent and score-only, holdout reversal, or unstable cluster bootstrap.",
        },
        "disposition": {"decision": terminal, "reason": reason},
        "claim": {
            "class": "mechanism_feasibility"
            if terminal == "fixture_only"
            else "selector_causality",
            "metric": "paired_replay_coverage",
            "value": len(continuations) / len(raw),
            "unit": "fraction",
            "direction": "higher_better",
            "category": "CANDIDATE",
            "protocol_id": "selector-replay-v1",
            "text": "Proportion of selected arms with recorded scored paired continuation",
            "reps_basis": f"{len(decisions)} decisions x {len(ARMS)} arms",
        },
        "profile": {
            "kind": "selector_replay",
            "journal": _spec(result / "journal.jsonl"),
            "candidate_graph": _spec(result / "candidate-graph.json"),
            "task_order": _spec(result / "task-order.json"),
            **{
                key: manifest["identities"][key]
                for key in (
                    "policy_revision",
                    "scorer_revision",
                    "selector_id",
                    "scheduler_id",
                    "archive_id",
                    "endpoint_id",
                )
            },
            "eligibility_denominator": len(raw),
            "parent_choices": parent_spec,
            "paired_continuations": continuation_spec,
            "arms": list(ARMS),
            "shinka_variant": variant,
            "profiles": manifest["profiles"],
            "model_id": manifest["identities"]["model_id"],
            "decoding_id": manifest["identities"]["decoding_id"],
            "holdout_id": manifest["holdout_id"],
            "tokens": manifest["budgets"]["proposer_tokens"],
            "cost": manifest["budgets"]["proposer_cost"],
        },
    }
    research_screen.write_receipt(result / "research-screen.json", receipt_body)
    return diagnostics


def replay_both(package: Path, result: Path) -> Path:
    """Run both Shinka treatments and seal one index over their five-arm receipts."""
    result.mkdir(parents=True, exist_ok=True)
    variants = {}
    for variant in SHINKA_VARIANTS:
        output = result / variant
        replay(package, output, variant)
        receipt = output / "research-screen.json"
        research_screen.native_rows(receipt)
        variants[variant] = {
            name: {
                "path": f"{variant}/{filename}",
                "sha256": digest((output / filename).read_bytes()),
            }
            for name, filename in (
                ("receipt", "research-screen.json"),
                ("diagnostics", "diagnostics.json"),
                ("raw_outputs", "raw-outputs.jsonl"),
            )
        }
    manifest = package / "manifest.json"
    body = {
        "schema": "epyc.selector_replay.aggregate.v1",
        "package_manifest": {
            "path": str(manifest.resolve()),
            "sha256": digest(manifest.read_bytes()),
        },
        "variants": variants,
        "meaning": "two distinct Shinka screens; each receipt contains current, score_only, shinka, dgm, hgm",
    }
    body["aggregate_sha256"] = digest(canonical(body))
    path = result / "aggregate-index.json"
    write_once(path, canonical(body) + b"\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    audit = subs.add_parser("audit-historical")
    audit.add_argument("journals", nargs="+", type=Path)
    audit.add_argument("--output", required=True, type=Path)
    audit.add_argument("--package", type=Path)
    audit.add_argument("--expected-inventory", type=Path)
    check = subs.add_parser("verify-audit")
    check.add_argument("audit", type=Path)
    pack = subs.add_parser("freeze")
    pack.add_argument("source", type=Path)
    pack.add_argument("package", type=Path)
    run = subs.add_parser("replay")
    run.add_argument("package", type=Path)
    run.add_argument("result", type=Path)
    run.add_argument("--shinka-variant", choices=SHINKA_VARIANTS, required=True)
    both = subs.add_parser("replay-both")
    both.add_argument("package", type=Path)
    both.add_argument("result", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "audit-historical":
            if args.expected_inventory is None or args.package is None:
                raise ReplayRefusal(
                    "audit-historical requires --expected-inventory and --package"
                )
            raw_inventory = args.expected_inventory.read_bytes()
            inventory = json.loads(raw_inventory)
            frozen_inventory = args.package / "inventory.json"
            write_once(frozen_inventory, raw_inventory)
            report = audit_historical(
                args.journals,
                args.package,
                inventory,
                {
                    "path": str(frozen_inventory.resolve()),
                    "sha256": digest(raw_inventory),
                },
            )
            write_once(args.output, canonical(report) + b"\n")
            verify_audit(args.output)
            receipt_path = seal_historical_audit_receipt(args.output)
            print(
                json.dumps(
                    {
                        "audit": str(args.output),
                        "receipt": str(receipt_path),
                        "disposition": report["disposition"],
                        "missing_fields": report["missing_fields"],
                    },
                    indent=2,
                )
            )
            return 2
        if args.command == "verify-audit":
            print(json.dumps(verify_audit(args.audit), indent=2))
            return 0
        if args.command == "freeze":
            print(freeze(args.source, args.package))
        elif args.command == "replay-both":
            print(replay_both(args.package, args.result))
        else:
            print(
                json.dumps(
                    replay(args.package, args.result, args.shinka_variant), indent=2
                )
            )
        return 0
    except (ReplayRefusal, OSError, research_screen.ProjectionError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
