#!/usr/bin/env python3
"""Offline, nonpromotable line-level diagnostics for a sealed programs.jsonl export.

The exporter must bind each program to the original AutoKernel proposal/candidate
journal events and immutable code bytes. This tool does not read a live journal,
run a candidate, call an LLM, or decide an edit label.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import difflib
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re


LABELS = frozenset({
    "bug_fix", "external_dependency", "architectural_change", "composition",
    "local_refinement", "pruning", "refactor", "efficiency",
    "hyperparameter_tuning",
})
SCHEMA = "epyc.autokernel.lineage_diagnostic.v1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_NUMBER = re.compile(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b")


def _source(row: dict, root: Path) -> str:
    """Resolve only a content-addressed blob; never trust inline source alone."""
    digest = row.get("solution_sha256")
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError("solution_sha256 is required")
    blob = root / "blobs" / digest[:2] / f"{digest}.txt"
    if blob.is_symlink() or not blob.is_file():
        raise ValueError(f"missing or unsafe solution blob: {digest}")
    raw = blob.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"solution digest mismatch: {digest}")
    return raw.decode("utf-8")


def _capture(row: dict, root: Path) -> None:
    """Historical patch paths/tree hashes are not original-attempt captures."""
    ref = row.get("source_capture")
    if not isinstance(ref, dict) or set(ref) != {"capture_id", "receipt_sha256"}:
        raise ValueError("prospective source_capture receipt required; historical unbound records refused")
    capture_id, digest = ref["capture_id"], ref["receipt_sha256"]
    if not isinstance(capture_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", capture_id):
        raise ValueError("invalid capture identity")
    if capture_id != row["id"]:
        raise ValueError("program id must be the original capture identity")
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError("invalid capture receipt digest")
    receipt_path = root / "captures" / f"{capture_id}.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError(f"missing original source capture: {capture_id}")
    raw = receipt_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"capture receipt digest mismatch: {capture_id}")
    receipt = json.loads(raw)
    if (not isinstance(receipt, dict)
            or receipt.get("schema") != "epyc.autokernel.lineage_source_capture.v1"
            or receipt.get("capture_id") != capture_id
            or receipt.get("parent_id") != row.get("parent_id")
            or receipt.get("solution_sha256") != row.get("solution_sha256")):
        raise ValueError(f"source capture does not bind program: {capture_id}")
    patch_sha = receipt.get("patch_sha256")
    if row.get("parent_id") is not None:
        if not isinstance(patch_sha, str) or not _SHA.fullmatch(patch_sha):
            raise ValueError("child source capture has no authored patch")
        patch = root / "blobs" / patch_sha[:2] / f"{patch_sha}.patch"
        if patch.is_symlink() or not patch.is_file() or hashlib.sha256(patch.read_bytes()).hexdigest() != patch_sha:
            raise ValueError("authored patch blob missing or corrupt")
    elif patch_sha is not None:
        raise ValueError("root capture must not carry a patch")


def _outcome(row: dict, root: Path) -> None:
    """A score is usable only if the producer authored it with the attempt."""
    metrics = row.get("metrics") or {}
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be a mapping")
    score = metrics.get("score")
    if score is None:
        return
    ref = row.get("outcome_capture")
    if not isinstance(ref, dict) or set(ref) != {"capture_id", "receipt_sha256"}:
        raise ValueError("scored program requires prospective outcome_capture receipt")
    capture_id, digest = ref["capture_id"], ref["receipt_sha256"]
    if (capture_id != row["source_capture"]["capture_id"]
            or not isinstance(digest, str) or not _SHA.fullmatch(digest)):
        raise ValueError("invalid outcome capture identity")
    path = root / "outcomes" / f"{capture_id}.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing original outcome capture")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("outcome capture digest mismatch")
    receipt = json.loads(raw)
    if (not isinstance(receipt, dict)
            or receipt.get("schema") != "epyc.autokernel.lineage_outcome_capture.v1"
            or receipt.get("capture_id") != capture_id
            or receipt.get("score") != score
            or receipt.get("metric_direction") not in {"higher_better", "lower_better"}):
        raise ValueError("outcome capture does not bind score")
    metrics["direction"] = receipt["metric_direction"]


def load_programs(root: Path) -> tuple[list[dict], str]:
    path = root / "programs.jsonl"
    if path.is_symlink() or not path.is_file():
        raise ValueError("programs.jsonl must be a regular file")
    raw = path.read_bytes()
    rows = []
    ids = set()
    for number, line in enumerate(raw.split(b"\n"), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError(f"invalid program at line {number}")
        if row["id"] in ids:
            raise ValueError(f"duplicate program id: {row['id']}")
        ids.add(row["id"])
        if not isinstance(row.get("iteration_found"), int) or row["iteration_found"] < 0:
            raise ValueError(f"invalid iteration: {row['id']}")
        if row.get("parent_id") is not None and not isinstance(row["parent_id"], str):
            raise ValueError(f"invalid parent: {row['id']}")
        _capture(row, root)
        row["solution"] = _source(row, root)
        _outcome(row, root)
        rows.append(row)
    if not rows:
        raise ValueError("empty program export")
    return rows, hashlib.sha256(raw).hexdigest()


def _normal(line: str, *, collapse_numbers: bool = False) -> str:
    line = re.sub(r"//.*$|/\*.*?\*/", "", line).strip()
    return _NUMBER.sub("#", line) if collapse_numbers else line


def _meaningful(line: str) -> bool:
    return len(line) >= 5 and line not in {"else {", "return;"} and not line.startswith("#include")


def _diff(parent: str, child: str) -> tuple[list[str], list[str]]:
    removed, added = [], []
    for line in difflib.unified_diff(parent.splitlines(), child.splitlines(), n=0):
        if line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith(("-", "+")):
            normal = _normal(line[1:])
            if _meaningful(normal):
                (removed if line[0] == "-" else added).append(normal)
    return removed, added


def analyze(rows: list[dict], *, direction: str) -> dict:
    if direction not in {"higher_better", "lower_better"}:
        raise ValueError("metric direction must be explicit")
    by_id = {r["id"]: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate program id")
    ordered = sorted(rows, key=lambda r: (r["iteration_found"], r["id"]))
    for row in ordered:
        metric_direction = (row.get("metrics") or {}).get("direction")
        if metric_direction is not None and metric_direction != direction:
            raise ValueError(f"scored program direction mismatch: {row['id']}")
    removed_history: dict[str, list[tuple[int, str]]] = defaultdict(list)
    cycles = []
    edits = []
    total_added = 0
    recycled_added = 0
    labels_count = Counter()
    labels_scored = Counter()
    labels_improved = Counter()
    for row in ordered:
        parent_id = row.get("parent_id")
        if parent_id is None:
            continue
        if parent_id not in by_id:
            raise ValueError(f"missing parent {parent_id} for {row['id']}")
        parent = by_id[parent_id]
        if parent["iteration_found"] >= row["iteration_found"]:
            raise ValueError(f"non-causal parent for {row['id']}")
        removed, added = _diff(parent["solution"], row["solution"])
        # A removal in this edit cannot cycle into an addition in the same edit.
        edge_cycles = []
        for line in added:
            prior = removed_history.get(line)
            nearest = next((event for event in reversed(prior or [])
                            if event[0] < row["iteration_found"]), None)
            if nearest is not None:
                iteration, removed_by = nearest
                edge_cycles.append({"line_sha256": hashlib.sha256(line.encode()).hexdigest(),
                                    "removed_iteration": iteration, "removed_by": removed_by,
                                    "added_iteration": row["iteration_found"], "added_by": row["id"]})
        for line in removed:
            removed_history[line].append((row["iteration_found"], row["id"]))
        total_added += len(added)
        recycled_added += len(edge_cycles)
        cycles.extend(edge_cycles)
        labels = row.get("edit_labels")
        label_source = row.get("edit_label_source")
        if (not isinstance(labels, list) or any(not isinstance(label, str) for label in labels)
                or len(labels) != len(set(labels)) or not set(labels) <= LABELS):
            raise ValueError(f"nine-label multi-label annotation required for {row['id']}")
        if not isinstance(label_source, dict) or not label_source.get("annotator") or not label_source.get("rubric_revision"):
            raise ValueError(f"label provenance required for {row['id']}")
        metrics = row.get("metrics") or {}
        parent_metrics = parent.get("metrics") or {}
        if not isinstance(metrics, dict) or not isinstance(parent_metrics, dict):
            raise ValueError("metrics must be a mapping")
        score = metrics.get("score")
        parent_score = parent_metrics.get("score")
        if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score)):
            raise ValueError(f"invalid score for {row['id']}")
        if parent_score is not None and (isinstance(parent_score, bool) or not isinstance(parent_score, (int, float)) or not math.isfinite(parent_score)):
            raise ValueError(f"invalid parent score for {row['id']}")
        scored = score is not None and parent_score is not None
        improved = scored and ((score > parent_score) if direction == "higher_better" else (score < parent_score))
        for label in labels:
            labels_count[label] += 1
            labels_scored[label] += int(scored)
            labels_improved[label] += int(improved)
        edits.append({"id": row["id"], "parent_id": parent_id, "added_lines": len(added),
                      "removed_lines": len(removed), "recycled_added_lines": len(edge_cycles),
                      "labels": labels, "scored": scored, "improved": improved if scored else None})
    taxonomy = {label: {"frequency": labels_count[label], "scored": labels_scored[label],
                        "improved": labels_improved[label],
                        "yield": (labels_improved[label] / labels_scored[label]
                                  if labels_scored[label] else None)} for label in sorted(LABELS)}
    return {"schema": SCHEMA, "authority": "offline_observation_only",
            "metric_direction": direction, "program_count": len(rows), "edit_count": len(edits),
            "cycling": {"recycled_added_lines": recycled_added, "added_lines": total_added,
                        "rate": recycled_added / total_added if total_added else None,
                        "events": cycles}, "taxonomy": taxonomy, "edits": edits}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="sealed programs.jsonl + blobs/ export")
    parser.add_argument("--metric-direction", required=True,
                        choices=("higher_better", "lower_better"))
    args = parser.parse_args()
    rows, export_sha256 = load_programs(args.run_dir)
    result = analyze(rows, direction=args.metric_direction)
    result["source"] = {"programs_jsonl_sha256": export_sha256,
                        "solution_sha256": {r["id"]: r["solution_sha256"] for r in rows},
                        "capture_receipt_sha256": {
                            r["id"]: r["source_capture"]["receipt_sha256"] for r in rows},
                        "outcome_receipt_sha256": {
                            r["id"]: r["outcome_capture"]["receipt_sha256"]
                            for r in rows if "outcome_capture" in r}}
    # Authored at measurement time. A future Vidya read adapter must project
    # this record, not reconstruct these values from historical reports.
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    # Lines and edits are correlated observations, not independent repetitions.
    # Leave protocol/n empty so the canonical ladder cannot promote this report.
    measurements = []
    def observe(suffix: str, metric: str, value: float, direction: str, claim: str) -> None:
        measurements.append({"measurement_id": f"ak-lineage-{export_sha256[:16]}-{suffix}",
                             "metric": metric, "value": value, "date": result["generated_at"],
                             "metric_direction": direction, "category": "CANDIDATE",
                             "protocol_id": "", "reps": None, "reps_basis": "",
                             "source_class": "measurement", "claim": claim,
                             "attestation_sha256": export_sha256})
    if result["cycling"]["rate"] is not None:
        observe("cycling", "recycled_added_line_fraction", result["cycling"]["rate"],
                "lower_better", "Line-level cycling in this sealed offline proposal export")
    for label, counts in result["taxonomy"].items():
        if counts["yield"] is not None:
            observe(f"{label}-yield", "edit_label_improvement_fraction", counts["yield"],
                    "higher_better", f"Conditional improvement fraction for {label} edits in this offline export")
    result["belief_measurements"] = measurements
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
