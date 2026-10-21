"""VB-HIL-WRITE carrier plus VB-HIL-WRITE-FIELDS: HIL feature A/B run evidence as a measurement source.

The module name is the one the adapters README row proposed (``harness_improvement.py``); no
carrier existed in the tree when VB-HIL-WRITE-FIELDS was dispatched, so this builds the carrier
with the HIL-2 item 14 arm pins as REQUIRED fields from the start. Item 14 lists what cannot be
recovered on read: the tool-surface digest (tool names and schemas), the served context window, the
compaction-policy digest, the wall-time and turn budget and the final-result selection rule. They
ride in ``extra.arm_pins`` and :func:`arm_pin_problems` is exported so any other HIL producer (for
example the SC86 shell-run carrier, whose ``RUN_SIDECAR_FIELDS`` records no tool-surface digest
today) can reuse the same check rather than redefine it.

One self-hashed row per run x arm x feature x objective metric, written at the eval runner's native
finalize boundary. The strict reader reopens the raw-result digest and the prompt/parameter digest,
projects authored facts to the existing measurement ``ClaimTuple`` and ``claim_tuple.grade()``
decides. No ladder, no retroactive rows, no policy or promotion authority. A protocol id is carried
only when one already applies; otherwise ``protocol_id`` is the literal ``observation:none``.
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

CAPTURE_SCHEMA = "epyc.vidya.harness_improvement_capture.v1"
SIDECAR_NAME = "harness_improvement.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.harness_improvement/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "harness-improvement-measurement"
NO_PROTOCOL = "observation:none"
ARM_ROLES = frozenset({"BASELINE", "CANDIDATE"})

#: HIL-2 item 14 pins. Closed field set; every one required.
ARM_PIN_FIELDS = ("tool_surface_sha256", "served_context_window", "compaction_policy_sha256",
                  "wall_time_budget_s", "turn_budget", "final_result_selection_rule")


def arm_pin_problems(pins: Any, *, where: str = "extra.arm_pins") -> list[str]:
    """Shared check for the item 14 pins (reusable by other HIL producers)."""
    if not isinstance(pins, dict):
        return [f"{where} must be an object"]
    p = []
    for key in ("tool_surface_sha256", "compaction_policy_sha256"):
        if not ns.SHA256.match(str(pins.get(key, ""))):
            p.append(f"{where}.{key} must be a 64-hex digest")
    for key in ("served_context_window", "turn_budget"):
        if not ns.nonneg_int(pins.get(key)) or pins.get(key) == 0:
            p.append(f"{where}.{key} must be a positive integer")
    if not ns.finite(pins.get("wall_time_budget_s")) or pins.get("wall_time_budget_s", 0) <= 0:
        p.append(f"{where}.wall_time_budget_s must be a positive number")
    if not ns.text(pins.get("final_result_selection_rule")):
        p.append(f"{where}.final_result_selection_rule must be a non-empty string")
    unknown = sorted(set(pins) - set(ARM_PIN_FIELDS))
    if unknown:
        p.append(f"{where} has unknown fields {unknown}")
    return p


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA)
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    for key in ("feature_id", "objective", "suite_id", "suite_version", "split",
                "native_verdict", "prompt_param_path", "harness_pin"):
        if not ns.text(e.get(key)):
            p.append(f"extra.{key} must be a non-empty string")
    if e.get("arm") not in ARM_ROLES:
        p.append("extra.arm must be BASELINE or CANDIDATE")
    elif row.get("category") != e["arm"]:
        p.append("category must equal extra.arm")
    for key in ("prompt_param_sha256", "config_sha256"):
        if not ns.SHA256.match(str(e.get(key, ""))):
            p.append(f"extra.{key} must be a 64-hex digest")
    if not ns.nonneg_int(e.get("scored")) or not ns.nonneg_int(e.get("attempted")) \
            or e.get("scored", 0) > e.get("attempted", 0) or e.get("scored") == 0:
        p.append("extra.scored/attempted must be integers with 0 < scored <= attempted")
    else:
        if row.get("reps") != e["scored"]:
            p.append("reps must equal extra.scored")
        want = ("scored:items" if e["scored"] == e["attempted"]
                else f"scored:items (attempted {e['attempted']})")
        if row.get("reps_basis") != want:
            p.append(f"reps_basis must be {want!r}")
    ids = e.get("identities", {})
    if not isinstance(ids, dict) or not all(ns.text(k) and ns.text(v) for k, v in ids.items()):
        p.append("extra.identities must map names to non-empty strings (only what the suite used)")
    p += arm_pin_problems(e.get("arm_pins"))
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "feature": e["feature_id"], "arm": e["arm"],
            "objective": e["objective"], "prompt": e["prompt_param_sha256"],
            "results": row["results_sha256"]}, "hilw")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    observations: Sequence[Mapping[str, Any]], protocol_id: str | None = None,
    emitted_at: str | None = None,
) -> Path:
    """Emit ``harness_improvement.beliefs.jsonl`` at the eval runner's finalize boundary.

    Each observation: ``{feature_id, arm, objective, metric, value, unit, metric_direction,
    native_verdict, suite_id, suite_version, split, scored, attempted, prompt_param_path,
    prompt_param_sha256, harness_pin, config_sha256, arm_pins:{HIL-2 item 14}, identities?}``.
    ``results_path`` is the durable raw-result file each row attests. Raises :class:`CaptureError`.
    """
    raw = Path(results_path)
    if not raw.is_file():
        raise CaptureError(f"raw result file missing: {raw}")
    if not observations:
        raise CaptureError("at least one observation is required")
    digest = ns.file_sha256(raw)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for o in observations:
        e = {k: o.get(k) for k in (
            "feature_id", "arm", "objective", "suite_id", "suite_version", "split",
            "native_verdict", "prompt_param_path", "prompt_param_sha256", "harness_pin",
            "config_sha256", "scored", "attempted", "arm_pins")}
        e["identities"] = dict(o.get("identities") or {})
        scored, attempted = e["scored"], e["attempted"]
        ok = ns.nonneg_int(scored) and ns.nonneg_int(attempted)
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
            "emitted_at": when, "date": when[:10], "metric": o.get("metric"),
            "value": o.get("value"), "unit": o.get("unit"),
            "metric_direction": o.get("metric_direction"), "category": e["arm"],
            "claim": (f"HIL {run_id}: feature {e['feature_id']} {e['arm']} {o.get('metric')}="
                      f"{o.get('value')} on {e['suite_id']}@{e['suite_version']}/{e['split']}"),
            "protocol_id": protocol_id or NO_PROTOCOL,
            "reps": scored, "reps_basis": (
                "scored:items" if ok and scored == attempted
                else f"scored:items (attempted {attempted})"),
            "results_path": str(raw), "results_sha256": digest, "extra": e,
        }
        if all(ns.text(e.get(k)) for k in ("feature_id", "arm", "objective")):
            row["measurement_id"] = "hilw_" + ns.content_hash({
                "run_id": run_id, "feature": e["feature_id"], "arm": e["arm"],
                "objective": e["objective"], "prompt": e["prompt_param_sha256"],
                "results": digest})[:24]
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate run x arm x feature x objective observation")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("HIL native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("HIL row is not a producer-authored capture: " + "; ".join(problems))
    x = row["extra"]
    locator = (f"hil:{row['run_id']}:{x['feature_id']}:{x['arm']}:{x['objective']}:"
               f"{row['results_path']}")
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
