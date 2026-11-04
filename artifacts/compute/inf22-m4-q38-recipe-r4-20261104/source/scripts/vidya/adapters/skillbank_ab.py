"""VB-SKILLBANK-AB-WRITE: M-23 SkillBank A/B per-cell readout as a prospective measurement source.

One self-hashed row per (role, model pin) cell: skill-on and skill-off ``correct`` / ``scored`` /
``attempted`` counts, the task-level bootstrap CI, adoption, the detector digest and the declared
minimum detectable difference. Negative cells stay rows. A pooled mean is NEVER emitted and a
pooled cell is refused. The strict reader re-derives the per-protocol and intention-to-treat
deltas from the counts, reopens the per-request log hash, and projects to the existing
measurement ``ClaimTuple``; ``claim_tuple.grade()`` decides. No retrospective tuple, no ladder.

Spec: ``episodic-memory-integrity.md`` M-23. The producer (the M-23 A/B runner) does not exist yet;
this carrier is written against the M-23 text. The bootstrap itself is the producer's; the reader
checks shape and the arithmetic it can re-derive, and takes the CI as authored.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.skillbank_ab_capture.v1"
SIDECAR_NAME = "skillbank_ab.beliefs.jsonl"
METRIC = "skillbank_on_minus_off_accuracy"
UNIT = "accuracy_difference"
ADAPTER_ID = "vidya.adapters.skillbank_ab/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "skillbank-ab-measurement"
POOLED_ROLES = frozenset({"pooled", "all", "*", "overall", "mean"})
ARMS = ("skill_on", "skill_off")


def _arm_problems(name: str, arm: Any) -> list[str]:
    if not isinstance(arm, dict):
        return [f"extra.{name} must be an object"]
    p = []
    for k in ("correct", "scored", "attempted"):
        if not ns.nonneg_int(arm.get(k)):
            p.append(f"extra.{name}.{k} must be a non-negative integer")
    if not p:
        if arm["scored"] < 1:
            p.append(f"extra.{name}.scored must be positive")
        if arm["correct"] > arm["scored"] or arm["scored"] > arm["attempted"]:
            p.append(f"extra.{name} must satisfy correct <= scored <= attempted")
    return p


def _deltas(extra: Mapping[str, Any]) -> tuple[float, float]:
    on, off = extra["skill_on"], extra["skill_off"]
    pp = on["correct"] / on["scored"] - off["correct"] / off["scored"]
    itt = on["correct"] / on["attempted"] - off["correct"] / off["attempted"]
    return pp, itt


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("metric") != METRIC:
        p.append(f"metric must be {METRIC!r}")
    if row.get("category") != "CANDIDATE":
        p.append("category must be CANDIDATE (skill-on is the candidate arm)")
    if not ns.text(e.get("role")) or str(e["role"]).lower() in POOLED_ROLES:
        p.append("extra.role must name one served role; a pooled cell is refused")
    if not ns.text(e.get("model_pin")):
        p.append("extra.model_pin must name the model as served")
    arm_p: list[str] = []
    for name in ARMS:
        arm_p += _arm_problems(name, e.get(name))
    p += arm_p
    ci = e.get("bootstrap_ci95")
    if not (isinstance(ci, list) and len(ci) == 2 and all(ns.finite(x) for x in ci)
            and ci[0] <= ci[1]):
        p.append("extra.bootstrap_ci95 must be [lo, hi] with lo <= hi (task-level bootstrap)")
    if not ns.nonneg_int(e.get("bootstrap_resamples")) or e.get("bootstrap_resamples") == 0:
        p.append("extra.bootstrap_resamples must be a positive integer")
    if not ns.finite(e.get("min_detectable_difference")) or e.get("min_detectable_difference", 0) <= 0:
        p.append("extra.min_detectable_difference must be declared (positive) before the run")
    if not ns.SHA256.match(str(e.get("detector_digest", ""))):
        p.append("extra.detector_digest must be the 64-hex digest of the adoption detector")
    ad = e.get("adoption")
    if not isinstance(ad, dict) or not ns.nonneg_int(ad.get("injected")) \
            or not ns.nonneg_int(ad.get("applied")) or ad.get("applied", 0) > ad.get("injected", 0):
        p.append("extra.adoption must carry integer injected >= applied >= 0")
    if not arm_p:
        pp, itt = _deltas(e)
        if abs(row["value"] - pp) > 1e-12:
            p.append("value must equal the per-protocol delta (correct/scored, on minus off)")
        if not ns.finite(e.get("itt_delta")) or abs(e["itt_delta"] - itt) > 1e-12:
            p.append("extra.itt_delta must equal the intention-to-treat delta (correct/attempted)")
        if e.get("negative_cell") is not (pp < 0):
            p.append("extra.negative_cell must be true exactly when the per-protocol delta < 0")
        reps = min(e["skill_on"]["scored"], e["skill_off"]["scored"])
        if row.get("reps") != reps:
            p.append("reps must be min(scored) over the two arms")
        want = (f"scored:tasks (min over arms; attempted on/off="
                f"{e['skill_on']['attempted']}/{e['skill_off']['attempted']})")
        if row.get("reps_basis") != want:
            p.append(f"reps_basis must be {want!r}")
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "role": e["role"], "pin": e["model_pin"],
            "results": row["results_sha256"]}, "skbab")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, request_log_path: str | Path,
    cells: Sequence[Mapping[str, Any]], protocol_id: str = "",
    emitted_at: str | None = None,
) -> Path:
    """Emit ``skillbank_ab.beliefs.jsonl``: one row per cell, negative cells included.

    Each cell: ``{role, model_pin, skill_on:{correct,scored,attempted}, skill_off:{...},
    bootstrap_ci95:[lo,hi], bootstrap_resamples, min_detectable_difference, detector_digest,
    adoption:{injected,applied}}``. ``request_log_path`` is the per-request log (skill_ids joined
    to role and pin) that every row attests. Raises :class:`CaptureError`; nothing is written.
    """
    log = Path(request_log_path)
    if not log.is_file():
        raise CaptureError(f"per-request skill log missing: {log}")
    if not cells:
        raise CaptureError("at least one cell is required")
    digest = ns.file_sha256(log)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for cell in cells:
        e = {k: cell.get(k) for k in (
            "role", "model_pin", "skill_on", "skill_off", "bootstrap_ci95", "bootstrap_resamples",
            "min_detectable_difference", "detector_digest", "adoption")}
        arm_p = [x for n in ARMS for x in _arm_problems(n, e.get(n))]
        if arm_p:
            raise CaptureError(f"cell {e['role']!r}/{e['model_pin']!r}: " + "; ".join(arm_p))
        pp, itt = _deltas(e)
        e["itt_delta"], e["negative_cell"] = itt, pp < 0
        reps = min(e["skill_on"]["scored"], e["skill_off"]["scored"])
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
            "emitted_at": when, "date": when[:10], "metric": METRIC, "value": pp, "unit": UNIT,
            "metric_direction": "higher_better", "category": "CANDIDATE",
            "claim": (f"SkillBank A/B {run_id}: {e['role']} on {e['model_pin']} skill-on minus "
                      f"skill-off = {pp:+.4f} (per-protocol)"),
            "protocol_id": protocol_id, "reps": reps,
            "reps_basis": (f"scored:tasks (min over arms; attempted on/off="
                           f"{e['skill_on']['attempted']}/{e['skill_off']['attempted']})"),
            "results_path": str(log), "results_sha256": digest, "extra": e,
        }
        if ns.text(e["role"]) and ns.text(e["model_pin"]):
            row["measurement_id"] = "skbab_" + ns.content_hash({
                "run_id": run_id, "role": e["role"], "pin": e["model_pin"],
                "results": digest})[:24]
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError(f"cell {e['role']!r}/{e['model_pin']!r}: refusing to emit an "
                               "invalid row: " + "; ".join(bad))
        rows.append(row)
    ids = [r["measurement_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise CaptureError("duplicate (role, model_pin) cell")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("SkillBank A/B native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("SkillBank A/B row is not a producer-authored capture: "
                              + "; ".join(problems))
    x = row["extra"]
    locator = f"skillbank-ab:{row['run_id']}:{x['role']}:{x['model_pin']}:{row['results_path']}"
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""),
                             no_protocol_ids=("observation:none",), legacy_schema_protocol=True)


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
