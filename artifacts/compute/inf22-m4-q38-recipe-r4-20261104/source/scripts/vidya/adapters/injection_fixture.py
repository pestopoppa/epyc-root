"""VB-IBENCH-WRITE: CT-18 injection-fixture results as a prospective measurement source.

The ONLY claim this source can carry is *static-attack ASR on fixture set X*: the fraction of the
fixture set's attacks that succeeded against one arm under one thinking setting on one served pin.
It is not a robustness claim and cannot be read back as one -- the claim string is generated here
with that fixed form, and the validator refuses any other wording (CT-20 wording rule).

One self-hashed row per run x arm. Write side (:func:`write_belief_measurements`) is called by the
CT-18 runner at finalize; the strict reader re-derives ASR from the per-attack records and projects
to the existing measurement ``ClaimTuple``; ``claim_tuple.grade()`` decides. No retrospective tuple:
a run with no sidecar emits zero rows. No ladder.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.injection_fixture_capture.v1"
SIDECAR_NAME = "injection_fixture.beliefs.jsonl"
METRIC = "injection_static_attack_asr"
UNIT = "fraction_attacks_succeeded"
ADAPTER_ID = "vidya.adapters.injection_fixture/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "injection-fixture-asr"
THINKING = frozenset({"on", "off", "not_applicable"})
PIN_KEYS = ("role", "model", "kernel_ref")
CLAIM_PREFIX = "static-attack ASR on fixture set "


def claim_text(fixture_set_id: str, fixture_sha256: str, arm: str, thinking: str, hits: int, n: int) -> str:
    return (f"{CLAIM_PREFIX}{fixture_set_id} [{fixture_sha256[:12]}], arm {arm}, thinking={thinking}: "
            f"{hits}/{n} attacks succeeded (static fixtures only; not a robustness claim)")


def _attack_problems(attacks: Any) -> list[str]:
    if not isinstance(attacks, list) or not attacks:
        return ["extra.attacks must be a non-empty list of per-attack records"]
    p, seen = [], set()
    for i, a in enumerate(attacks):
        if not isinstance(a, dict):
            p.append(f"attacks[{i}] is not an object")
            continue
        if not ns.text(a.get("fixture_id")) or a["fixture_id"] in seen:
            p.append(f"attacks[{i}].fixture_id must be a unique non-empty string")
        seen.add(str(a.get("fixture_id")))
        if not isinstance(a.get("attack_success"), bool):
            p.append(f"attacks[{i}].attack_success must be a boolean")
    return p


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA)
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("metric") != METRIC:
        p.append(f"metric must be {METRIC!r}")
    if row.get("metric_direction") != "lower_better":
        p.append("metric_direction must be lower_better (ASR)")
    for key in ("fixture_set_id", "arm_label"):
        if not ns.text(e.get(key)):
            p.append(f"extra.{key} must be a non-empty string")
    if not ns.SHA256.match(str(e.get("fixture_sha256", ""))):
        p.append("extra.fixture_sha256 must be the 64-hex hash of the fixture set")
    if e.get("thinking_setting") not in THINKING:
        p.append(f"extra.thinking_setting must be one of {sorted(THINKING)}")
    pin = e.get("served_pin")
    if not isinstance(pin, dict) or not all(ns.text(pin.get(k)) for k in PIN_KEYS):
        p.append(f"extra.served_pin must name {list(PIN_KEYS)}")
    if not isinstance(e.get("is_control"), bool):
        p.append("extra.is_control must be a boolean")
    elif row.get("category") != ("BASELINE" if e["is_control"] else "CANDIDATE"):
        p.append("category must follow extra.is_control (BASELINE/CANDIDATE)")
    ap = _attack_problems(e.get("attacks"))
    p += ap
    if not ap:
        n, hits = len(e["attacks"]), sum(a["attack_success"] for a in e["attacks"])
        if e.get("n_attacks") != n or e.get("n_succeeded") != hits:
            p.append("extra.n_attacks / extra.n_succeeded do not match the per-attack records")
        if ns.finite(row.get("value")) and abs(row["value"] - hits / n) > 1e-12:
            p.append("value must equal n_succeeded / n_attacks")
        if row.get("reps") != n or row.get("reps_basis") != "scored:fixtures":
            p.append("reps must equal the number of fixtures with reps_basis 'scored:fixtures'")
        if ns.text(e.get("fixture_set_id")) and ns.SHA256.match(str(e.get("fixture_sha256", ""))) \
                and row.get("claim") != claim_text(e["fixture_set_id"], e["fixture_sha256"],
                                                   e["arm_label"], e["thinking_setting"], hits, n):
            p.append("claim must be the fixed 'static-attack ASR on fixture set X' wording")
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "set": e["fixture_set_id"], "fx": e["fixture_sha256"],
            "arm": e["arm_label"], "think": e["thinking_setting"], "pin": e["served_pin"],
            "results": row["results_sha256"]}, "injfx")
    return p + ns.self_hash_problems(row) if isinstance(row, dict) else p


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    fixture_set_id: str, fixture_sha256: str, arms: Mapping[str, Mapping[str, Any]],
    protocol_id: str = CAPTURE_SCHEMA, emitted_at: str | None = None,
) -> Path:
    """``arms``: label -> ``{thinking_setting, served_pin{role,model,kernel_ref}, is_control,
    attacks:[{fixture_id, attack_success}]}``. ``results_path`` is the run's results artifact
    (re-hashed on read). Any problem raises :class:`CaptureError`; nothing is written."""
    results = Path(results_path)
    if not results.is_file():
        raise CaptureError(f"results artifact missing: {results}")
    if not arms:
        raise CaptureError("at least one arm is required")
    digest = ns.file_sha256(results)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for label, a in arms.items():
        attacks = [dict(x) for x in a.get("attacks", [])]
        bad = _attack_problems(attacks)
        if bad:
            raise CaptureError(f"arm {label!r}: " + "; ".join(bad))
        n, hits = len(attacks), sum(x["attack_success"] for x in attacks)
        thinking = a.get("thinking_setting")
        extra = {"fixture_set_id": fixture_set_id, "fixture_sha256": fixture_sha256,
                 "arm_label": label, "thinking_setting": thinking,
                 "served_pin": dict(a.get("served_pin") or {}), "is_control": a.get("is_control"),
                 "n_attacks": n, "n_succeeded": hits, "attacks": attacks}
        row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
               "emitted_at": when, "date": when[:10], "metric": METRIC, "value": hits / n,
               "unit": UNIT, "metric_direction": "lower_better",
               "category": "BASELINE" if a.get("is_control") else "CANDIDATE",
               "claim": claim_text(str(fixture_set_id), str(fixture_sha256), label, str(thinking), hits, n),
               "protocol_id": protocol_id, "reps": n, "reps_basis": "scored:fixtures",
               "results_path": str(results), "results_sha256": digest, "extra": extra}
        if isinstance(a.get("is_control"), bool) and ns.SHA256.match(str(fixture_sha256)):
            row["measurement_id"] = "injfx_" + ns.content_hash({
                "run_id": run_id, "set": fixture_set_id, "fx": fixture_sha256, "arm": label,
                "think": thinking, "pin": extra["served_pin"], "results": digest})[:24]
        ns.seal(row)
        problems = validate_row(row)
        if problems:
            raise CaptureError(f"arm {label!r}: refusing to emit an invalid row: " + "; ".join(problems))
        rows.append(row)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("injection-fixture native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("injection-fixture row is not a producer-authored capture: "
                              + "; ".join(problems))
    locator = f"injection-fixture:{row['run_id']}:{row['extra']['arm_label']}:{row['results_path']}"
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
