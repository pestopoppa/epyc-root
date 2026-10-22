"""VB-HIL15A-WRITE: write side and strict reader for the HIL-15a flag-on dependency AUC table.

Emitted at write time by ``epyc-orchestrator`` ``scripts/trace/hil15a_flagon_run.py`` as
``<out>/auc_table.beliefs.jsonl`` (opt-in; a table written before the hook exists is never
back-filled). One self-hashed row per FEATURE SET (out-of-fold AUC) and per DELTA (AUC difference
with the producer's task-resampled 95% CI). ``reps`` = runs; tasks and failed-run counts ride in
``extra``; the edge definition is the producer's own ``observed`` (intervention-validated needs the
HIL-16 replay) and is carried verbatim, never upgraded.

The writer REFUSES a manifest that is not explicitly ``"mock": false`` and an ``insufficient``
table (no AUC exists to attest). The AUC producer emits a CI only for deltas; a feature-set row has
``ci95 = null`` (never invented). The CI itself is ``null`` when the producer had too few bootstrap
replicates. No ladder here: ``claim_tuple.grade()`` decides.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.hil15a_auc_capture.v1"
SIDECAR_NAME = "auc_table.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.hil15a_auc/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "hil15a-dependency-auc-measurement"
NO_PROTOCOL = "observation:none"
EDGE_GRADE = "observed"
SET_METRIC, DELTA_METRIC = "hil15a_auc_out_of_fold", "hil15a_delta_auc"
#: the feature set that carries the claim; every other set is a comparison arm
CANDIDATE_SET = "size+composition+observed_dependency"


def _ci_problem(ci: Any) -> str | None:
    if ci is None:
        return None
    if not (isinstance(ci, list) and len(ci) == 2 and all(ns.finite(x) for x in ci) and ci[0] <= ci[1]):
        return "extra.ci95_task_resampled must be null or [lo, hi] with lo <= hi"
    return None


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA)
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    kind = e.get("kind")
    if kind not in ("feature_set", "delta") or not ns.text(e.get("name")):
        return p + ["extra.kind must be feature_set|delta and extra.name non-empty"]
    if e.get("edge_grade") != EDGE_GRADE:
        p.append(f"extra.edge_grade must be {EDGE_GRADE!r}")
    for key in ("n_runs", "n_tasks", "n_failed"):
        if not ns.nonneg_int(e.get(key)):
            p.append(f"extra.{key} must be a non-negative integer")
    else_ok = ns.nonneg_int(e.get("n_runs")) and ns.nonneg_int(e.get("n_failed"))
    if else_ok and not (0 < e["n_failed"] < e["n_runs"]):
        p.append("extra.n_failed must satisfy 0 < n_failed < n_runs (both classes present)")
    if row.get("reps") != e.get("n_runs") or row.get("reps_basis") != "scored:runs":
        p.append("reps must equal extra.n_runs with reps_basis 'scored:runs'")
    if not ns.text(e.get("edge_definition")):
        p.append("extra.edge_definition must be carried verbatim from the producer")
    if kind == "feature_set":
        want = (SET_METRIC, "auc", "higher_better")
        if e.get("ci95_task_resampled") is not None:
            p.append("a feature-set row has no producer CI: extra.ci95_task_resampled must be null")
        if row.get("category") != ("CANDIDATE" if e["name"] == CANDIDATE_SET else "BASELINE"):
            p.append("category must be CANDIDATE for the observed-dependency set, else BASELINE")
    else:
        want = (DELTA_METRIC, "auc_delta", "higher_better")
        bad = _ci_problem(e.get("ci95_task_resampled"))
        if bad:
            p.append(bad)
        a, b = e.get("minuend"), e.get("subtrahend")
        if not (ns.finite(a) and ns.finite(b)) or not ns.text(e.get("minuend_set")) \
                or not ns.text(e.get("subtrahend_set")):
            p.append("a delta row must carry minuend/subtrahend sets and their AUCs")
        elif ns.finite(row.get("value")) and abs(row["value"] - (a - b)) > 1.5e-4:
            p.append("value does not re-derive from the recorded minuend and subtrahend AUCs")
        if row.get("category") != "CANDIDATE":
            p.append("a delta row's category must be CANDIDATE")
    if (row.get("metric"), row.get("unit"), row.get("metric_direction")) != want:
        p.append(f"a {kind} row fixes metric/unit/direction to {want}")
    if not ns.text(e.get("manifest_schema")):
        p.append("extra.manifest_schema must be recorded")
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "kind": kind, "name": e["name"],
                                     "results": row["results_sha256"]}, "hil15a")
    return p + ns.self_hash_problems(row)


def _rows(table: Mapping[str, Any], manifest: Mapping[str, Any]) -> list[dict]:
    if manifest.get("mock") is not False:
        raise CaptureError('refusing: the manifest is not an explicit "mock": false run '
                           "(a mock AUC table is a plumbing artefact, never a finding)")
    if table.get("status") == "insufficient" or "auc_out_of_fold" not in table:
        raise CaptureError(f"refusing: auc_table has no AUCs (status={table.get('status')!r})")
    common = {k: table.get(k) for k in ("n_runs", "n_tasks", "n_failed")}
    common.update(edge_grade=EDGE_GRADE, edge_definition=table.get("edge_definition"),
                  manifest_schema=manifest.get("schema"), hashseed=manifest.get("hashseed"),
                  flags=manifest.get("flags"), label_classes=manifest.get("label_classes"),
                  served_model=manifest.get("served_model"))
    aucs = table["auc_out_of_fold"]
    out = []
    for name, v in aucs.items():
        out.append((SET_METRIC, "auc", v, "BASELINE" if name != CANDIDATE_SET else "CANDIDATE",
                    {"kind": "feature_set", "name": name, "ci95_task_resampled": None, **common}))
    for name, d in (table.get("deltas") or {}).items():
        out.append((DELTA_METRIC, "auc_delta", d.get("delta_auc"), "CANDIDATE",
                    {"kind": "delta", "name": name, "ci95_task_resampled": d.get("ci95_task_resampled"),
                     **common}))
    return out


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, auc_table_path: str | Path,
    manifest: Mapping[str, Any], emitted_at: str | None = None,
) -> Path:
    """Emit ``auc_table.beliefs.jsonl`` from the driver's ``auc_table.json`` + in-memory manifest.

    ``manifest`` is the driver's manifest dict (needs ``"mock": false`` and ``schema``). Delta
    minuend/subtrahend sets come from :data:`DELTA_SETS` (the producer's fixed mapping). A delta
    name not in it is refused by the validator. Raises CaptureError."""
    path = Path(auc_table_path)
    if not path.is_file():
        raise CaptureError(f"auc_table file missing: {path}")
    table = json.loads(path.read_text())
    digest = ns.file_sha256(path)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for metric, unit, value, category, extra in _rows(table, manifest):
        if extra["kind"] == "delta":
            a_set, b_set = DELTA_SETS.get(extra["name"], (None, None))
            aucs = table["auc_out_of_fold"]
            extra.update(minuend_set=a_set, subtrahend_set=b_set,
                         minuend=aucs.get(a_set), subtrahend=aucs.get(b_set))
        row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when,
               "date": when[:10], "metric": metric, "value": value, "unit": unit,
               "metric_direction": "higher_better", "category": category,
               "claim": f"HIL-15a {run_id}: {extra['kind']} {extra['name']} {metric}={value} "
                        f"over {table.get('n_runs')} runs / {table.get('n_tasks')} tasks "
                        f"(edge={EDGE_GRADE})",
               "protocol_id": NO_PROTOCOL, "reps": table.get("n_runs"), "reps_basis": "scored:runs",
               "results_path": str(path), "results_sha256": digest, "extra": extra}
        row["measurement_id"] = "hil15a_" + ns.content_hash({
            "run_id": run_id, "kind": extra["kind"], "name": extra["name"], "results": digest})[:24]
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


#: producer's fixed delta definitions (src/trace/dependency_features.py auc_table ``deltas``)
DELTA_SETS = {
    "observed_dependency_minus_composition": ("size+composition+observed_dependency", "size+composition"),
    "observed_dependency_minus_size": ("size+composition+observed_dependency", "size"),
    "counterfeit_minus_composition": ("size+composition+degree_matched_counterfeit", "size+composition"),
}


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("HIL-15a native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("HIL-15a row is not a producer-authored capture: " + "; ".join(problems))
    x = row["extra"]
    locator = f"hil15a:{row['run_id']}:{x['kind']}:{x['name']}:{row['results_path']}"
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
