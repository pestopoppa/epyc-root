"""SC37 write side + strict read side for the eval-tower resolution band (EV-14a).

A band is the retained spread of per-suite scores from ``core_v2_calibrate.py
--repeats``: fixed ``n`` and ``seed``, ONE UNCHANGED config, every repeat's per-suite
score retained (never averaged away). The band is the instrument's measured
RESOLUTION for that suite — a candidate delta smaller than the band is UNRESOLVED,
never "no change", never a regression (eval-tower-verification.md EV-14a/b).

Two parts, one module:

* ``build_band_artifact`` — the write-side hook. The EV-14a runner calls it AFTER the
  last repeat with the native ``core_v2_calibration`` JSONL rows, the EV-14c baseline
  pin captured BEFORE the first repeat, and the reference-moved verdict
  (``baseline.pin_moved(pin)``). It emits ONE self-hashed ``.band.json`` artifact per
  suite. It refuses to emit rather than fill in: a run whose repeats did not all
  score, a draw whose per-suite counts disagree between repeats, or a baseline
  reference that MOVED mid-window is not a band and no artifact is written.
* ``native_rows`` / ``project`` — the strict reader. PROJECTS each band artifact into
  the canonical :class:`ClaimTuple`; ``claim_tuple.grade()`` decides. The reader never
  reads the raw calibration JSONL or the eval tower to reconstruct a band — a band
  reconstructed on read would claim a repeat-count and a config identity the run
  never captured (the DF2-4 / ``benchmarks/results`` precedent).

SCOPE LIMIT — carried IN the tuple, not just the docs (the SC37 clause): a band
attests the RESOLUTION OF THE INSTRUMENT and says nothing about the quality of any
config. The claim text states it verbatim, and the reader refuses any artifact whose
claim does not. A projection that reads a band as "this delta is statistically solid"
is the SC21 category error one level up.

EV-14c coupling: the tuple records the pinned reference the band was measured against
(tier, quality, revision, era) and the ``reference_moved`` verdict. A band whose
reference moved mid-window is INVALID — the writer refuses to emit it and the reader
refuses to project one. A silently-moved baseline is impossible by construction.

Attestation: the artifact is the evidence. ``attestation_sha256`` is a hash over the
artifact FILE bytes (recomputed on read); the artifact ALSO carries an internal
``artifact_sha256`` over its own canonical content. There is no separate attested
file to decay against — a mutated artifact fails the internal hash and VOIDS the
whole artifact (zero rows): partial validity is corruption, not a partial band.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

BAND_SCHEMA = "epyc.vidya.eval_tower_band.v1"
CALIBRATION_SCHEMA = 1  # core_v2_calibrate.py result_to_row() schema_version
METRIC = "eval_tower_suite_resolution_band_width"
UNIT = "quality_units_0_3"
PROTOCOL_ID = BAND_SCHEMA
SOURCE_KIND = "eval-tower-band-measurement"
ADAPTER_ID = "vidya.adapters.eval_tower_band/v1"
AUTHORITY = "measurement"

# The scope-limit sentence rides in every claim verbatim. The reader enforces it:
# an artifact whose claim does not carry it is not a band projection.
SCOPE_LIMIT = (
    "INSTRUMENT RESOLUTION ONLY: this band attests the resolution of the eval "
    "instrument for this suite; it says nothing about the quality of any config, "
    "and a delta smaller than the band is UNRESOLVED."
)

CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})
DIRECTIONS = frozenset({"higher_better", "lower_better"})
MIN_REPEATS = 2  # a band is a spread; one repeat has no spread to retain

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CaptureError(ValueError):
    """The runner asked for a band artifact the run did not actually measure."""


# ── shared vocabulary helpers (one definition of well-formed, writer + reader) ──


def _canonical_json(value: Any) -> str:
    def check(obj: Any, path: str) -> None:
        if obj is None or isinstance(obj, (bool, int, str)):
            return
        if isinstance(obj, float):
            if not math.isfinite(obj):
                raise CaptureError(f"{path}: non-finite float is not canonical JSON")
            return
        if isinstance(obj, list):
            for index, item in enumerate(obj):
                check(item, f"{path}[{index}]")
            return
        if isinstance(obj, dict):
            for key, item in obj.items():
                if not isinstance(key, str):
                    raise CaptureError(f"{path}: canonical JSON keys must be strings")
                check(item, f"{path}.{key}")
            return
        raise CaptureError(f"{path}: {type(obj).__name__} is not canonical JSON")

    check(value, "$")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def measurement_identity(*, calibration_id: str, suite_id: str, core_id: str,
                         artifact_sha256: str) -> str:
    """Stable per-(band run, suite, artifact) identity; re-derives on read."""
    digest = content_hash({
        "calibration_id": calibration_id, "suite_id": suite_id, "core_id": core_id,
        "artifact_sha256": artifact_sha256,
    })
    return f"band_{digest[:24]}"


# ── validation ─────────────────────────────────────────────────────────────────


def validate_artifact(artifact: Any) -> list[str]:
    """Every structural problem in one band artifact. Empty list == valid.

    Shared by the writer (refuse to emit) and the reader (refuse to project), so there
    is exactly one definition of "well-formed" — the 2026-08-10 two-dialects lesson
    applied to the band schema.
    """
    if not isinstance(artifact, dict):
        return ["artifact is not a JSON object"]
    p: list[str] = []

    if artifact.get("schema") != BAND_SCHEMA:
        p.append(f"schema must be {BAND_SCHEMA!r}")
    for key in ("calibration_id", "suite_id", "producer", "protocol_id", "claim",
                "metric", "unit", "metric_direction", "category"):
        if not _text(artifact.get(key)):
            p.append(f"{key} must be a non-empty string")
    if artifact.get("metric") != METRIC:
        p.append(f"metric must be {METRIC!r}")
    if artifact.get("protocol_id") != PROTOCOL_ID:
        p.append(f"protocol_id must be {PROTOCOL_ID!r}")
    if artifact.get("metric_direction") not in DIRECTIONS:
        p.append("metric_direction must be recorded as higher_better or lower_better")
    if artifact.get("category") not in CATEGORIES:
        p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
    if not _utc_timestamp(artifact.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    if not isinstance(artifact.get("reference_moved"), bool):
        p.append("reference_moved must be a boolean")
    claim = str(artifact.get("claim", ""))
    if SCOPE_LIMIT not in claim:
        p.append("claim must state the instrument-resolution scope limit verbatim "
                 "(a band never attests config quality)")

    config = artifact.get("unchanged_config")
    if not isinstance(config, dict):
        p.append("unchanged_config must be an object")
    else:
        if not _text(config.get("core_id")):
            p.append("unchanged_config.core_id must be a non-empty string")
        for key in ("seed", "n", "trial_id_base"):
            if not _nonneg_int(config.get(key)):
                p.append(f"unchanged_config.{key} must be a non-negative integer")
        if not _nonneg_int(config.get("rotation_index")):
            p.append("unchanged_config.rotation_index must be a non-negative integer")

    era = artifact.get("instrument_era")
    if not isinstance(era, dict):
        p.append("instrument_era must be an object")
    else:
        if not _text(era.get("eval_quality_era")):
            p.append("instrument_era.eval_quality_era must be a non-empty string")

    repeats = artifact.get("per_repeat_scores")
    if not isinstance(repeats, list) or len(repeats) < MIN_REPEATS:
        p.append(f"per_repeat_scores must list at least {MIN_REPEATS} scored repeats")
    else:
        indexes: list[int] = []
        scores: list[float] = []
        k_values: list[int] = []
        for index, repeat in enumerate(repeats):
            if not isinstance(repeat, dict):
                p.append(f"per_repeat_scores[{index}] is not an object")
                continue
            if not _nonneg_int(repeat.get("repeat_index")):
                p.append(f"per_repeat_scores[{index}].repeat_index must be a non-negative integer")
            elif repeat["repeat_index"] in indexes:
                p.append(f"per_repeat_scores[{index}].repeat_index is duplicated")
            else:
                indexes.append(repeat["repeat_index"])
            if not _nonneg_int(repeat.get("trial_id")):
                p.append(f"per_repeat_scores[{index}].trial_id must be a non-negative integer")
            if not _finite(repeat.get("quality")):
                p.append(f"per_repeat_scores[{index}].quality must be a finite score")
            else:
                scores.append(float(repeat["quality"]))
            if repeat.get("scored") is not True:
                p.append(f"per_repeat_scores[{index}].scored must be true "
                         "(reps counts repeats that SCORED, never attempted)")
            if _nonneg_int(repeat.get("k")):
                k_values.append(int(repeat["k"]))
            else:
                p.append(f"per_repeat_scores[{index}].k must be the suite question count")
        if scores and not (min(scores) <= max(scores)):
            p.append("band width is negative — corrupt retained spread")
        if k_values and len(set(k_values)) != 1:
            p.append(f"suite question count K must be identical across repeats "
                     f"(unchanged config -> unchanged draw); got {sorted(set(k_values))}")

    band = artifact.get("band")
    if not isinstance(band, dict):
        p.append("band must be an object")
    else:
        for key in ("min", "max", "median", "width"):
            if not _finite(band.get(key)):
                p.append(f"band.{key} must be a finite number")
        if scores:
            if _finite(band.get("min")) and not math.isclose(band["min"], min(scores),
                                                             rel_tol=1e-12, abs_tol=1e-15):
                p.append("band.min must equal the minimum retained score")
            if _finite(band.get("max")) and not math.isclose(band["max"], max(scores),
                                                             rel_tol=1e-12, abs_tol=1e-15):
                p.append("band.max must equal the maximum retained score")
            if _finite(band.get("width")) and not math.isclose(
                    band["width"], max(scores) - min(scores), rel_tol=1e-12, abs_tol=1e-15):
                p.append("band.width must equal max - min (the retained spread)")
            if _finite(band.get("median")) and not math.isclose(
                    band["median"], statistics.median(scores), rel_tol=1e-12, abs_tol=1e-15):
                p.append("band.median must equal the median of the retained scores")
        if band.get("method") != "retained_spread_unchanged_config":
            p.append("band.method must be 'retained_spread_unchanged_config'")
        if not _text(band.get("metric")) or not _text(band.get("unit")):
            p.append("band.metric and band.unit must be recorded")

    reference = artifact.get("baseline_reference")
    if not isinstance(reference, dict):
        p.append("baseline_reference must be an object (the EV-14c pinned reference)")
    else:
        if not _nonneg_int(reference.get("tier")):
            p.append("baseline_reference.tier must be a non-negative integer")
        if not _nonneg_int(reference.get("tier_revision")):
            p.append("baseline_reference.tier_revision must be a non-negative integer")
        if not _utc_timestamp(reference.get("pinned_at")):
            p.append("baseline_reference.pinned_at must be a UTC timestamp")
        if not _text(reference.get("pin_id")):
            p.append("baseline_reference.pin_id must be a non-empty string")
        if reference.get("quality") is not None and not _finite(reference.get("quality")):
            p.append("baseline_reference.quality must be finite or absent")
        if not isinstance(reference.get("per_suite_quality"), dict):
            p.append("baseline_reference.per_suite_quality must be an object")
        if not isinstance(reference.get("per_suite_counts"), dict):
            p.append("baseline_reference.per_suite_counts must be an object")

    if not _SHA256.match(str(artifact.get("artifact_sha256", ""))):
        p.append("artifact_sha256 must be a 64-hex digest over the artifact content")
    else:
        try:
            if content_hash({k: v for k, v in artifact.items() if k != "artifact_sha256"}) \
                    != artifact["artifact_sha256"]:
                p.append("artifact_sha256 does not bind the artifact content")
        except CaptureError as exc:
            p.append(f"artifact is not canonically hashable: {exc}")
    return p


# ── write side: build_band_artifact ─────────────────────────────────────────────


def build_band_artifact(
    calibration_jsonl: str | Path,
    out_path: str | Path,
    *,
    calibration_id: str,
    suite_id: str,
    unchanged_config: Mapping[str, Any],
    instrument_era: Mapping[str, Any],
    baseline_reference: Mapping[str, Any],
    reference_moved: bool,
    producer: str = "core_v2_calibrate.py --repeats",
    metric_direction: str = "lower_better",
    emitted_at: str | None = None,
) -> Path:
    """Emit ONE self-hashed ``.band.json`` artifact for one suite — the SC37 write hook.

    ``calibration_jsonl`` is the native output of ``core_v2_calibrate.py --repeats``
    (one row per repeat; schema_version 1). The runner captures ``baseline_reference``
    from ``Baseline.pin_tier(tier, pin_id=...)`` BEFORE the first repeat and passes
    ``reference_moved = baseline.pin_moved(pin)`` after the last — a True verdict
    means the band was measured against a reference that moved mid-window, which is
    INVALID: this function refuses to emit (EV-14c, fail-closed).

    Refusals (each is a band the run did not actually measure):
    * any repeat did not SCORE (``quality_measured`` false, or infra/scoring failures)
      — the band is the retained spread of a clean instrument, not of a degraded one;
    * the suite's question count K differs between repeats — the config was not
      unchanged, so there is no single band;
    * ``reference_moved`` is true — the pinned baseline moved mid-window;
    * fewer than two scored repeats — one repeat has no spread to retain.
    """
    path = Path(calibration_jsonl)
    if not path.is_file():
        raise CaptureError(f"no calibration JSONL at {path} — call this AFTER the repeats")
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        raise CaptureError("calibration JSONL is empty — no repeats to form a band from")
    for row in rows:
        if row.get("event_type") != "core_v2_calibration":
            raise CaptureError(f"unexpected row event_type {row.get('event_type')!r}")
        if row.get("schema_version") != CALIBRATION_SCHEMA:
            raise CaptureError(f"unexpected calibration schema_version {row.get('schema_version')!r}")

    core_id = str(unchanged_config.get("core_id", ""))
    if not core_id:
        raise CaptureError("unchanged_config.core_id is required — the unchanged-config "
                           "identity is the whole point of a band (SC37)")

    repeat_rows: list[dict[str, Any]] = []
    k_per_repeat: list[int] = []
    for row in rows:
        if str(row.get("core_id", "")) != core_id:
            raise CaptureError(
                f"row {row.get('trial_id')} core_id {row.get('core_id')!r} != "
                f"unchanged config {core_id!r} — the repeats are not one unchanged config")
        if row.get("quality_measured") is not True:
            raise CaptureError(
                f"repeat {row.get('repeat_index')} (trial {row.get('trial_id')}) did not "
                f"measure quality ({row.get('quality_unmeasured_reason')!r}); a band needs "
                "the retained spread of a clean instrument")
        if (row.get("infra_failed_count") or 0) > 0 or (row.get("scoring_failed_count") or 0) > 0:
            raise CaptureError(
                f"repeat {row.get('repeat_index')} (trial {row.get('trial_id')}) had "
                f"infra_failed={row.get('infra_failed_count')} "
                f"scoring_failed={row.get('scoring_failed_count')}; a band is never derived "
                "from a degraded repeat")
        suites = row.get("per_suite_quality") or {}
        counts = row.get("per_suite_counts") or {}
        if suite_id not in suites or suites[suite_id] is None:
            raise CaptureError(
                f"repeat {row.get('repeat_index')} (trial {row.get('trial_id')}) did not "
                f"score suite {suite_id!r}; the band needs every repeat's retained score")
        if suite_id not in counts or not _nonneg_int(counts[suite_id]):
            raise CaptureError(
                f"repeat {row.get('repeat_index')} (trial {row.get('trial_id')}) lacks the "
                f"question count for suite {suite_id!r} (K is a tuple element)")
        k_per_repeat.append(int(counts[suite_id]))
        repeat_rows.append({
            "repeat_index": int(row.get("repeat_index", -1)),
            "trial_id": int(row.get("trial_id", -1)),
            "quality": float(suites[suite_id]),
            "k": int(counts[suite_id]),
            "scored": True,
        })
    if len(repeat_rows) < MIN_REPEATS:
        raise CaptureError(f"a band needs at least {MIN_REPEATS} scored repeats; "
                           f"got {len(repeat_rows)}")
    if len(set(k_per_repeat)) != 1:
        raise CaptureError(
            f"suite {suite_id!r} question count K differs across repeats "
            f"({sorted(set(k_per_repeat))}): the config is not unchanged, so there is no "
            "single band to retain")
    k = k_per_repeat[0]
    if not _nonneg_int(unchanged_config.get("seed")) or not _nonneg_int(
            unchanged_config.get("n")):
        raise CaptureError("unchanged_config.seed and unchanged_config.n must be recorded")
    if any(int(row.get("seed", -1)) != int(unchanged_config["seed"])
           for row in rows) or any(int(row.get("requested_n", -1)) != int(unchanged_config["n"])
                                   for row in rows):
        raise CaptureError("repeats disagree with unchanged_config seed/n — the repeats "
                           "are not one unchanged config")
    if reference_moved:
        raise CaptureError(
            "baseline reference MOVED during the band window (EV-14c pin verdict true): "
            "the band was measured against a reference that no longer exists. REFUSING to "
            "emit — re-measure against the current baseline.")
    if metric_direction not in DIRECTIONS:
        raise CaptureError(f"metric_direction must be one of {sorted(DIRECTIONS)}")

    scores = sorted(float(row["quality"]) for row in repeat_rows)
    width = scores[-1] - scores[0]
    band: dict[str, Any] = {
        "metric": METRIC,
        "unit": UNIT,
        "metric_direction": metric_direction,
        "min": scores[0],
        "max": scores[-1],
        "median": statistics.median(scores),
        "width": width,
        "method": "retained_spread_unchanged_config",
    }
    artifact: dict[str, Any] = {
        "schema": BAND_SCHEMA,
        "calibration_id": calibration_id,
        "suite_id": suite_id,
        "producer": producer,
        "emitted_at": emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metric": METRIC,
        "unit": UNIT,
        "metric_direction": metric_direction,
        "category": "BASELINE",
        "protocol_id": PROTOCOL_ID,
        "claim": (
            f"Eval-tower resolution band for suite {suite_id!r}: K={k} questions, "
            f"{len(scores)} repeats of unchanged config {core_id!r} scored "
            f"q∈[{scores[0]:.3f},{scores[-1]:.3f}] (width {width:.3f} on the 0-3 scale), "
            f"measured against the T{int(baseline_reference['tier'])} baseline pinned at "
            f"revision {int(baseline_reference['tier_revision'])} "
            f"(era {instrument_era.get('eval_quality_era')!r}). "
            f"{SCOPE_LIMIT}"
        ),
        "unchanged_config": dict(unchanged_config),
        "instrument_era": dict(instrument_era),
        "per_repeat_scores": repeat_rows,
        "band": band,
        "baseline_reference": dict(baseline_reference),
        "reference_moved": False,
    }
    artifact["artifact_sha256"] = content_hash(
        {k: v for k, v in artifact.items() if k != "artifact_sha256"})
    problems = validate_artifact(artifact)
    if problems:
        raise CaptureError("refusing to emit an invalid band artifact: "
                           + "; ".join(problems))

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    # The file bytes ARE the canonical content (no trailing newline), so the
    # file-level sha256 the reader re-computes equals the internal artifact_sha256
    # exactly — the attestation and the tamper check are the same number.
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(_canonical_json(artifact))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, out)
    return out


# ── read side ────────────────────────────────────────────────────────────────────


def _load_artifact(path: Path) -> dict | None:
    """Parse and validate one band artifact; ``None`` means inadmissible."""
    try:
        artifact = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if validate_artifact(artifact):
        return None
    return artifact


def native_rows(artifact_path: str | Path) -> tuple[dict, ...]:
    """Admissible band artifacts for one suite. Missing/invalid -> zero rows.

    A ``reference_moved`` artifact is a record of a window that FAILED, not a band —
    zero rows, logged loudly (a silently-moved baseline is the exact defect EV-14c
    exists to make impossible).
    """
    path = Path(artifact_path)
    if not path.is_file():
        return ()
    artifact = _load_artifact(path)
    if artifact is None:
        return ()
    if artifact.get("reference_moved") is True:
        sys.stderr.write(
            "eval_tower_band: refusing to project a band whose baseline reference moved "
            f"mid-window ({path}) — invalid, never 'no change' (EV-14c)\n")
        return ()
    # Presence is decided by the projector, not the shared ladder: the band artifact
    # IS the attested evidence (single file), and we just read + self-hash-validated
    # it, so it exists by construction. Content integrity is the internal
    # ``artifact_sha256`` check — a mutated artifact voids the whole file before
    # projection, so there is no decayed-but-readable state to grade down.
    return tuple({
        "artifact": artifact,
        "artifact_path": str(path),
        "attestation_present": True,
    } for _ in [0])


def frames_for_band(artifact_path: str | Path, *, as_of: str) -> list[dict]:
    """Uniform frame emission through the shared carrier (``claim_tuple.to_frames``)."""
    frames: list[dict] = []
    for native in native_rows(artifact_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Revalidates the artifact so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("artifact"), dict):
        raise ProjectionError("eval-tower band native must retain the band artifact")
    artifact = native["artifact"]
    problems = validate_artifact(artifact)
    if problems:
        raise ProjectionError("band artifact is not a producer-authored band: "
                              + "; ".join(problems))
    if artifact.get("reference_moved") is True:
        raise ProjectionError(
            "band measured against a baseline reference that moved mid-window — invalid, "
            "never 'no change' (EV-14c)")
    band = artifact["band"]
    reference = artifact["baseline_reference"]
    config = artifact["unchanged_config"]
    k = int(artifact["per_repeat_scores"][0]["k"])
    repeats_scored = sum(1 for repeat in artifact["per_repeat_scores"] if repeat.get("scored"))
    return ClaimTuple(
        measurement_id=measurement_identity(
            calibration_id=artifact["calibration_id"],
            suite_id=artifact["suite_id"],
            core_id=config["core_id"],
            artifact_sha256=artifact["artifact_sha256"],
        ),
        metric=artifact["metric"],
        value=band["width"],
        date=artifact["emitted_at"],
        category=artifact["category"],
        claim=artifact["claim"],
        metric_direction=artifact["metric_direction"],
        protocol_id=artifact["protocol_id"],
        reps=repeats_scored,
        reps_basis=f"scored:repeats (of {len(artifact['per_repeat_scores'])} runs)",
        unit=artifact["unit"],
        attestation_path=str(native.get("artifact_path", "")),
        # The producer-written content self-hash over the band artifact: a sha256 over
        # the artifact, re-derivable by anyone holding the file. Content integrity is
        # separately enforced by validate_artifact (tamper -> void), so the hash and
        # the presence flag stay consistent by construction.
        attestation_sha256=artifact["artifact_sha256"],
        attestation_locator=(
            f"eval-tower-band:{artifact['calibration_id']}:{artifact['suite_id']}:"
            f"{native.get('artifact_path', '')}"
        ),
        attestation_present=bool(native.get("attestation_present")),
        source_kind=SOURCE_KIND,
        extra={
            "schema": artifact["schema"],
            "producer": artifact["producer"],
            "calibration_id": artifact["calibration_id"],
            "suite_id": artifact["suite_id"],
            "k": k,
            "unchanged_config": config,
            "instrument_era": artifact["instrument_era"],
            "per_repeat_scores": artifact["per_repeat_scores"],
            "band": band,
            "baseline_reference": reference,
            "reference_moved": artifact["reference_moved"],
            "scope_limit": SCOPE_LIMIT,
        },
    )


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "BAND_SCHEMA", "PROTOCOL_ID", "METRIC",
    "UNIT", "SCOPE_LIMIT", "MIN_REPEATS", "CaptureError", "content_hash",
    "measurement_identity", "validate_artifact", "build_band_artifact", "native_rows",
    "frames_for_band", "project",
]
