"""VB-DRIPREVIEW-WRITE: write side and strict reader for the D-RI-PREVIEW-1 comparator result.

Emitted at write time by ``epyc-orchestrator`` ``scripts/benchmark/run_repl_preview.py`` as
``repl_preview.beliefs.jsonl`` next to ``--out``. One self-hashed row per role x rendering cell:
the correct-rate with the class counts (correct / blind_rule_fit / retyping_loss / other /
no_answer, summing to n), ``reps`` = samples STARTED (no_answer stays in the denominator, as the
frozen spec requires). Locator = GGUF x rendering x fixture sha256.

REFUSES a ``mock`` result and a partial one (``complete`` false, or a cell short of ``n_per_cell``).
The result file names roles but not their GGUF, and does not hash the fixture: the caller passes
``role_pins`` (role -> ``{"gguf_path": ...}``) and ``fixture_sha256`` (:func:`fixture_sha256` over
the driver's fixture dict); a missing one refuses the write, nothing is guessed. Rows are a report,
not an adopt/reject verdict (PREDECLARED.md). No ladder: ``claim_tuple.grade()`` decides.
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

CAPTURE_SCHEMA = "epyc.vidya.repl_preview_capture.v1"
RESULT_SCHEMA = "epyc.repl_preview_result.v1"
SIDECAR_NAME = "repl_preview.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.repl_preview/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "repl-preview-comparator-measurement"
NO_PROTOCOL = "observation:none"
METRIC = "repl_preview_correct_rate"
CLASSES = ("correct", "blind_rule_fit", "retyping_loss", "other", "no_answer")
CONTROL_RENDERING = "current"


def fixture_sha256(fixture: Mapping[str, Any]) -> str:
    """Digest of the driver's ``build_fixture()`` dict (canonical JSON)."""
    return ns.content_hash(dict(fixture))


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA)
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    for key in ("role", "rendering", "gguf_path", "predeclared"):
        if not ns.text(e.get(key)):
            p.append(f"extra.{key} must be a non-empty string")
    if not ns.SHA256.match(str(e.get("fixture_sha256", ""))):
        p.append("extra.fixture_sha256 must be a 64-hex digest")
    if e.get("mock") is not False or e.get("complete") is not True:
        p.append("extra.mock must be false and extra.complete true")
    counts = e.get("counts")
    n = e.get("n")
    if not (isinstance(counts, dict) and set(counts) == set(CLASSES)
            and all(ns.nonneg_int(v) for v in counts.values())) or not (ns.nonneg_int(n) and n > 0):
        p.append(f"extra.counts must hold non-negative integers for {list(CLASSES)} and extra.n > 0")
    else:
        if sum(counts.values()) != n:
            p.append("class counts must sum to extra.n")
        if ns.finite(row.get("value")) and abs(row["value"] - counts["correct"] / n) > 1e-9:
            p.append("value does not re-derive from correct / n")
        if row.get("reps") != n or row.get("reps_basis") != "started:samples":
            p.append("reps must equal extra.n with reps_basis 'started:samples'")
    if (row.get("metric"), row.get("unit"), row.get("metric_direction")) != (
            METRIC, "fraction", "higher_better"):
        p.append(f"metric/unit/direction are fixed to {METRIC!r}/'fraction'/'higher_better'")
    if ns.text(e.get("rendering")) and row.get("category") != (
            "BASELINE" if e["rendering"] == CONTROL_RENDERING else "CANDIDATE"):
        p.append("category must be BASELINE for the 'current' rendering, else CANDIDATE")
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "role": e["role"],
                                     "rendering": e["rendering"], "gguf": e["gguf_path"],
                                     "fixture": e["fixture_sha256"], "results": row["results_sha256"]},
                               "dripv")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, result_path: str | Path,
    role_pins: Mapping[str, Mapping[str, Any]], fixture_sha256: str,
    emitted_at: str | None = None,
) -> Path:
    """Emit ``repl_preview.beliefs.jsonl`` from a COMPLETE, non-mock driver result. Raises CaptureError."""
    path = Path(result_path)
    if not path.is_file():
        raise CaptureError(f"result file missing: {path}")
    res = json.loads(path.read_text())
    if res.get("schema") != RESULT_SCHEMA:
        raise CaptureError(f"result schema must be {RESULT_SCHEMA!r}")
    if res.get("mock") is not False:
        raise CaptureError("refusing: mock result (plumbing only, never a finding)")
    if res.get("complete") is not True:
        raise CaptureError("refusing: partial result (complete is not true); rerun resumes from --cell-dir")
    if not ns.SHA256.match(str(fixture_sha256)):
        raise CaptureError("fixture_sha256 must be a 64-hex digest")
    counts_all = res.get("counts") or {}
    if not counts_all:
        raise CaptureError("result has no counts")
    digest = ns.file_sha256(path)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for key, c in counts_all.items():
        role, _, rendering = key.partition("|")
        pin = role_pins.get(role) or {}
        if not ns.text(pin.get("gguf_path")):
            raise CaptureError(f"role_pins[{role!r}].gguf_path missing: the result does not name the GGUF")
        n = c.get("n")
        if n != res.get("n_per_cell"):
            raise CaptureError(f"cell {key}: n={n} != n_per_cell={res.get('n_per_cell')}")
        extra = {"role": role, "rendering": rendering, "gguf_path": pin["gguf_path"],
                 "fixture_sha256": fixture_sha256, "n": n,
                 "counts": {k: c.get(k) for k in CLASSES}, "mock": False, "complete": True,
                 "temperature": res.get("temperature"), "predeclared": res.get("predeclared")}
        value = c.get("correct", 0) / n if ns.nonneg_int(n) and n > 0 else None
        row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when,
               "date": when[:10], "metric": METRIC, "value": value, "unit": "fraction",
               "metric_direction": "higher_better",
               "category": "BASELINE" if rendering == CONTROL_RENDERING else "CANDIDATE",
               "claim": f"D-RI-PREVIEW-1 {run_id}: role {role} rendering {rendering} correct-rate "
                        f"{value} on n={n} samples (fixture {fixture_sha256[:12]})",
               "protocol_id": NO_PROTOCOL, "reps": n, "reps_basis": "started:samples",
               "results_path": str(path), "results_sha256": digest, "extra": extra}
        row["measurement_id"] = "dripv_" + ns.content_hash({
            "run_id": run_id, "role": role, "rendering": rendering, "gguf": pin["gguf_path"],
            "fixture": fixture_sha256, "results": digest})[:24]
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError(f"{key}: refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("REPL-preview native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("REPL-preview row is not a producer-authored capture: " + "; ".join(problems))
    x = row["extra"]
    locator = (f"repl-preview:{x['gguf_path']}:{x['rendering']}:{x['fixture_sha256']}:"
               f"{row['results_path']}")
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
