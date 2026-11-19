"""VB-HILLB1-WRITE: HIL-LB1 loop-detector scores on the Who&When Pro labelled loop set, as OBSERVATIONS.

Source: orchestrator ``scripts/trace/hil_lb1_loop_score.py`` writes one aggregate JSON
(``artifacts/hil/hil-lb1/hil_lb1_loop_score.json``). Only ``whowhen_pro.populations`` is projected:
per population x detector the confusion counts (tp/fp/fn/tn) and the four rates derived from them.

Doctrine, in the order it bites:

* PROJECTION ONLY. Every number is copied from the file and RE-DERIVED from the counts on both the
  write and the read side (precision tp/(tp+fp), recall tp/(tp+fn), F1 2tp/(2tp+fp+fn), FP rate
  fp/(fp+tn), each rounded to 4 places as the scorer does); a value that does not re-derive is
  refused. ``claim_tuple.grade()`` decides. No new ladder.
* ``protocol_id`` is ALWAYS the empty string. No ratified protocol applies and ``"observation:none"``
  is a known bug pattern. The tuple is an OBSERVATION.
* The label is INJECTED loop behaviour (Who&When Pro mode A.4, all positives in one framework), not
  natural frequency; the scorer's own ``scope`` string rides in every row, with the tokenizer sha256.
* The unlabelled sections (recorded tap replies, coding-session census, constrained-output fixtures)
  are firing counts, never accuracy, and are NOT projected. A rate whose denominator is zero is
  ``None`` at source and yields no row.
* The labelled-set digest and the code commit are absent from the source JSON. The caller may pass
  ``labelled_set_path`` (hashed at write time) and ``code_ref``; otherwise the row records them as
  absent (``extra.absent_at_source``), never invents them.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.hil_lb1_loop_score_capture.v1"
SIDECAR_NAME = "hil_lb1_loop_score.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.hil_lb1_loop_score/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "hil-lb1-loop-score"
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")

COUNT_FIELDS = ("n", "n_pos", "n_neg", "tp", "fp", "fn", "tn")
#: metric -> (source field, direction, n basis field-expression, human unit)
METRICS = {
    "hil_lb1_precision": ("precision", "higher_better", "tp+fp", "TP/(TP+FP)"),
    "hil_lb1_recall": ("recall", "higher_better", "n_pos", "TP/(TP+FN)"),
    "hil_lb1_f1": ("f1", "higher_better", "n", "2TP/(2TP+FP+FN)"),
    "hil_lb1_fp_rate_on_negatives": ("fp_rate_on_negatives", "lower_better", "n_neg", "FP/(FP+TN)"),
}
BASELINE_DETECTORS = ("prevalence_baseline", "l2_loop_existing")


def derive(cell: dict, field: str) -> float | None:
    tp, fp, fn, tn = (cell[k] for k in ("tp", "fp", "fn", "tn"))
    if field == "precision":
        v = tp / (tp + fp) if tp + fp else None
    elif field == "recall":
        v = tp / (tp + fn) if tp + fn else None
    elif field == "f1":
        v = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    else:
        v = fp / (fp + tn) if fp + tn else None
    return None if v is None else round(v, 4)


def n_of(cell: dict, expr: str) -> int:
    return cell["tp"] + cell["fp"] if expr == "tp+fp" else cell[expr]


def category_for(detector: str) -> str:
    return "BASELINE" if detector.split(" ")[0] in BASELINE_DETECTORS or \
        detector.split(" ")[0].removesuffix("_exempt") in BASELINE_DETECTORS else "CANDIDATE"


def cell_problems(cell: Any, where: str = "extra.cell") -> list[str]:
    if not isinstance(cell, dict):
        return [f"{where} must be an object"]
    if not all(ns.nonneg_int(cell.get(k)) for k in COUNT_FIELDS):
        return [f"{where} must carry integer counts {COUNT_FIELDS}"]
    p = []
    if cell["tp"] + cell["fn"] != cell["n_pos"] or cell["fp"] + cell["tn"] != cell["n_neg"] \
            or cell["n_pos"] + cell["n_neg"] != cell["n"]:
        p.append(f"{where} confusion counts are inconsistent")
    for m, (field, *_rest) in METRICS.items():
        if cell.get(field) != derive(cell, field):
            p.append(f"{where}.{field} does not re-derive from the counts")
    return p


def _load(path: Path) -> dict:
    try:
        res = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"HIL-LB1 result unreadable: {exc}") from exc
    w = res.get("whowhen_pro") if isinstance(res, dict) else None
    if not (isinstance(w, dict) and isinstance(w.get("populations"), dict) and w["populations"]):
        raise CaptureError("HIL-LB1 result has no whowhen_pro.populations (labelled scoring absent)")
    for key in ("scope",):
        if not ns.text(w.get(key)):
            raise CaptureError(f"HIL-LB1 whowhen_pro lacks {key!r}")
    tok = res.get("tokenizer")
    if not (isinstance(tok, dict) and ns.SHA256.match(str(tok.get("sha256", "")))):
        raise CaptureError("HIL-LB1 result lacks the tokenizer sha256 (use the real tokenizer, not 'regex')")
    if not isinstance(res.get("profiles"), dict):
        raise CaptureError("HIL-LB1 result lacks detector profiles")
    return res


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: no ratified protocol applies, the tuple is an "
                 "OBSERVATION (\"observation:none\" is a known bug pattern)")
    for key in ("population", "detector", "scope"):
        if not ns.text(e.get(key)):
            p.append(f"extra.{key} must be a non-empty string")
    if row.get("metric") not in METRICS:
        return p + [f"metric must be one of {sorted(METRICS)}"] + ns.self_hash_problems(row)
    field, direction, nexpr, _ = METRICS[row["metric"]]
    p += cell_problems(e.get("cell"))
    cell = e.get("cell")
    if isinstance(cell, dict) and not cell_problems(cell):
        if cell[field] is None or row.get("value") != cell[field]:
            p.append(f"value must equal extra.cell.{field} (non-null)")
        if row.get("reps") != n_of(cell, nexpr) or not row.get("reps"):
            p.append(f"reps must equal {nexpr} (> 0)")
    if row.get("metric_direction") != direction:
        p.append(f"metric_direction must be {direction}")
    if row.get("category") != category_for(str(e.get("detector"))):
        p.append("category does not match the detector")
    if not ns.SHA256.match(str(e.get("tokenizer_sha256", ""))):
        p.append("extra.tokenizer_sha256 must be a 64-hex digest")
    if e.get("labelled_set_sha256") is not None and not ns.SHA256.match(str(e["labelled_set_sha256"])):
        p.append("extra.labelled_set_sha256 must be null or a 64-hex digest")
    if e.get("code_ref") is not None and not GIT_SHA.match(str(e["code_ref"])):
        p.append("extra.code_ref must be null or a 40-hex commit")
    absent = sorted(k for k in ("labelled_set_sha256", "code_ref") if e.get(k) is None)
    if e.get("absent_at_source") != absent:
        p.append("extra.absent_at_source must list exactly the null identity fields")
    if not isinstance(e.get("profiles"), dict):
        p.append("extra.profiles must be the scorer's detector profile object")
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "population": e["population"], "detector": e["detector"],
            "metric": row["metric"], "results": row["results_sha256"]}, "hillb1")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    labelled_set_path: str | Path | None = None, code_ref: str | None = None,
    emitted_at: str | None = None,
) -> Path:
    """Emit ``hil_lb1_loop_score.beliefs.jsonl`` from a finished ``hil_lb1_loop_score.json``."""
    raw = Path(results_path)
    res = _load(raw)
    digest = ns.file_sha256(raw)
    labelled = None
    if labelled_set_path is not None:
        lp = Path(labelled_set_path)
        if not lp.is_file():
            raise CaptureError(f"labelled set missing: {lp}")
        labelled = ns.file_sha256(lp)
    if code_ref is not None and not GIT_SHA.match(code_ref):
        raise CaptureError("code_ref must be a 40-hex commit")
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    w = res["whowhen_pro"]
    rows = []
    for pop in sorted(w["populations"]):
        for det in sorted(w["populations"][pop]):
            cell = {k: v for k, v in w["populations"][pop][det].items()}
            bad = cell_problems(cell)
            if bad:
                raise CaptureError("result cell malformed: " + "; ".join(bad))
            for metric, (field, direction, nexpr, unit) in METRICS.items():
                if cell[field] is None or not n_of(cell, nexpr):
                    continue
                row = {
                    "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
                    "emitted_at": when, "date": when[:10], "metric": metric, "value": cell[field],
                    "unit": unit, "metric_direction": direction, "category": category_for(det),
                    "claim": (f"HIL-LB1 {run_id}: detector {det} on Who&When Pro population {pop} "
                              f"{metric}={cell[field]} (INJECTED loop behaviour, not natural "
                              f"frequency; {w['scope']})"),
                    "protocol_id": "", "reps": n_of(cell, nexpr),
                    "reps_basis": f"scored:Who&When Pro traces ({nexpr})",
                    "results_path": str(raw), "results_sha256": digest,
                    "extra": {
                        "population": pop, "detector": det, "scope": w["scope"],
                        "descriptive_sweep": "(descriptive sweep)" in det,
                        "cell": {k: cell[k] for k in (*COUNT_FIELDS, "precision", "recall", "f1",
                                                       "fp_rate_on_negatives")},
                        "profiles": res["profiles"], "tokenizer_sha256": res["tokenizer"]["sha256"],
                        "tokenizer_path": res["tokenizer"].get("kind"),
                        "labelled_set_sha256": labelled, "code_ref": code_ref,
                        "absent_at_source": sorted(
                            k for k, v in (("labelled_set_sha256", labelled), ("code_ref", code_ref))
                            if v is None),
                        "loop_N": w.get("loop_N"), "source": res.get("source"),
                    },
                }
                row["measurement_id"] = "hillb1_" + ns.content_hash({
                    "run_id": run_id, "population": pop, "detector": det, "metric": metric,
                    "results": digest})[:24]
                ns.seal(row)
                bad = validate_row(row)
                if bad:
                    raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
                rows.append(row)
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate population x detector x metric")
    if not rows:
        raise CaptureError("no population x detector cell met the emission thresholds")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("HIL-LB1 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("HIL-LB1 row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    locator = (f"hil-lb1:{row['run_id']}:{e['population']}:{e['detector']}:{row['metric']}:"
               f"{row['results_path']}")
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
