"""SC75 / VB-INF70-ARMS write-side hook: producer-authored belief rows for INF-70 serving arms.

The INF-70 serving harness (``arm_cold.sh`` / ``arm_hot.sh``, HARNESS-1 onward) runs one
measurement ARM against a live ``llama-server``, writes ``<label>.rows.jsonl`` (one row per
prompt) and, since 2026-09-07, samples co-residency DURING the arm into
``<label>.coresidency``. This module is what the arm script calls AT ARM END to emit
``<label>.belief_measurements.jsonl`` beside those files:

    python3 scripts/vidya/adapters/inf70_serving_arm_capture.py \\
        --run-dir "$OUT" --label "$lbl" --launch-json "$OUT/$SESS.launch.json" \\
        --arm-started-at "$(date -u -d @$A0 +%FT%TZ)"

The row vocabulary is the established producer contract (see
``tulving_episodic_capture.py``): ``measurement_id / metric / value / unit /
metric_direction / category / claim / protocol_id / reps / reps_basis / extra`` plus a
self-hash. The strict read side is ``inf70_serving_arm.py``, which imports this vocabulary so
writer and reader cannot drift into two dialects of one schema.

**The field this hook exists for is the per-arm CONTENTION VERDICT.** It describes the host
*during* the arm and cannot be recovered afterwards; a verdict made up at read time
claims a warrant the run never captured. Therefore:

* **No verdict, no row.** A missing or empty ``.coresidency`` file makes the writer refuse, and
  so does a sampler line it cannot classify.
* **Pre-2026-09-07 arms are worse than absent.** Until 2026-09-07 the sampler tested logical CPU
  ids, so it reported cpus 184-191 (the SMT siblings of bench cores 88-95), and in fact the whole
  96-191 half, as ``disjoint-from-0-95``. Those labels are WRONG, not merely missing. Such an
  arm can never produce a row, for three reasons:
  (a) an arm that started before ``SAMPLER_FIX_DATE`` is refused;
  (b) a coresidency file that uses the legacy vocabulary (``OVERLAPS-0-95`` /
  ``disjoint-from-0-95``) is refused;
  (c) the writer refuses when the capture happens more than ``MAX_CAPTURE_LAG_S`` after the
  arm's rows were last written. A hook called at arm end passes; a backfill run days later
  does not.
* **DIRECT and SMT-SIBLING stay separate.** Collapsing them is what produced the wrong label.
* **Locator = the ARM/launch, never the per-prompt row.** The twenty per-prompt rows of one arm
  are samples of one launch, and one quiet moment lifts all of them. ``reps`` therefore counts
  launches (1), and the per-prompt count rides in ``extra``.
* **Nothing is guessed.** The following must be supplied by the producer or the writer refuses:
  model + GGUF digest, kernel commit + binary version, the launch recipe (including the
  ``GGML_NOHUGEPAGE_PROCESS`` state, which is part of the artifact's identity), pinning, and
  bench CPUs. The between-launch sd is recorded only when the producer supplies it together
  with its replicate group; otherwise it is recorded as absent, never computed from one launch.

The metric is the harness's own definition (``harness1/analyze.py``): token-weighted decode
rate ``sum(pred_n) / sum(pred_ms)`` over rows with ``pred_n >= 16``. Coherence is counted by
REASON (the per-row ``verdict``), never collapsed to pass/fail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

CAPTURE_SCHEMA = "epyc.vidya.inf70_serving_arm_capture.v1"
SIDECAR_SUFFIX = ".belief_measurements.jsonl"

METRIC = "inf70_serving_decode_tps_tw"
METRICS = (METRIC,)
UNIT = "tokens/s"
PRED_N_FLOOR = 16

#: The corrected, three-valued sampler (HARNESS-1 ``tools/cpuoverlap.py``) is version 2.
#: Version 1 is the legacy two-valued predicate that read cpus 96-191 as disjoint.
SAMPLER_VERSION = 2
MIN_SAMPLER_VERSION = 2
#: The first day the corrected sampler existed. Arms before it cannot emit rows.
SAMPLER_FIX_DATE = "2026-09-07"
#: A hook is called at arm end. A capture this long after the arm's rows were written is a
#: backfill, and a backfill would attach a verdict to an arm after the fact.
MAX_CAPTURE_LAG_S = 3600

VERDICT_CONTENDED = "CONTENDED"
VERDICT_CLEAN = "CLEAN"
VERDICTS = frozenset({VERDICT_CONTENDED, VERDICT_CLEAN})

_V2_TOKENS = ("DIRECT-OVERLAP", "SMT-SIBLING-CONTENTION", "DISJOINT-FROM-BENCH-CORES")
_LEGACY_TOKENS = ("OVERLAPS-0-95", "disjoint-from-0-95")
_THP_KNOB = "GGML_NOHUGEPAGE_PROCESS"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
_CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})
_LABEL = re.compile(r"^[A-Za-z0-9_.-]+$")


class CaptureError(ValueError):
    """The arm asked for a sidecar it did not capture the identity or verdict for."""


# --- canonical hashing (same discipline as every other producer contract) -----------------

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
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def row_digest(row: Mapping[str, Any]) -> str:
    unsigned = {k: v for k, v in row.items() if k != "row_sha256"}
    return content_hash(unsigned)


def measurement_identity(*, launch_id: str, label: str, arm_started_at: str, metric: str,
                         contention_verdict: str, rows_sha256: str) -> str:
    """The verdict is part of the identity: the same numbers under a different verdict are a
    different claim, never a re-labelling of this one."""
    digest = content_hash({
        "launch_id": launch_id, "label": label, "arm_started_at": arm_started_at,
        "metric": metric, "contention_verdict": contention_verdict,
        "rows_sha256": rows_sha256,
    })
    return f"inf70arm_{digest[:24]}"


# --- small predicates -------------------------------------------------------------------------

def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fix_instant() -> datetime:
    return datetime.fromisoformat(SAMPLER_FIX_DATE + "T00:00:00+00:00")


def _thp_state_ok(value: Any) -> bool:
    return value == "unset" or (isinstance(value, str) and value.startswith("set:")
                                and len(value) > len("set:"))


# --- the native parsers (used ONLY at write time) --------------------------------------------

def summarize_contention(text: str) -> dict[str, Any]:
    """Per-arm contention verdict from a corrected-sampler ``.coresidency`` file.

    ``foreign_cpu_*`` are in units of one fully busy core (100 = one core), summed across
    foreign processes per sample, as in ``harness1/analyze.py::contention``. DIRECT and
    SMT-SIBLING line counts are kept separate. Raises :class:`CaptureError` when the file
    cannot yield a verdict.
    """
    samples: list[float] = []
    current: float | None = None
    counts = {"direct_overlap": 0, "smt_sibling": 0, "disjoint": 0, "gone": 0}
    for line in text.splitlines():
        if line.startswith("==="):
            if current is not None:
                samples.append(current)
            current = 0.0
            continue
        if "FOREIGN" not in line:
            continue
        if any(token in line for token in _LEGACY_TOKENS):
            raise CaptureError(
                "coresidency uses the legacy sampler vocabulary (OVERLAPS-0-95 / "
                "disjoint-from-0-95): that sampler read cpus 96-191 as disjoint, so its labels "
                "are wrong, not missing — no row")
        if current is None:
            raise CaptureError("coresidency FOREIGN line before any sample header")
        if "CLASSIFY-ERROR" in line:
            raise CaptureError("coresidency carries a CLASSIFY-ERROR line: the verdict for this "
                               "arm is unknown, and an unknown verdict is not a clean one")
        if line.rstrip().endswith("GONE"):
            counts["gone"] += 1
        elif "SMT-SIBLING-CONTENTION" in line:
            counts["smt_sibling"] += 1
        elif "DIRECT-OVERLAP" in line:
            counts["direct_overlap"] += 1
        elif "DISJOINT-FROM-BENCH-CORES" in line:
            counts["disjoint"] += 1
        else:
            raise CaptureError(f"coresidency line carries no recognised verdict: {line.strip()!r}")
        match = re.search(r"cpu=([0-9.]+)", line)
        if not match:
            raise CaptureError(f"coresidency FOREIGN line without cpu=: {line.strip()!r}")
        current += float(match.group(1))
    if current is not None:
        samples.append(current)
    if not samples:
        raise CaptureError("coresidency has no samples: no verdict, no row")
    ordered = sorted(samples)
    contended = counts["direct_overlap"] + counts["smt_sibling"] > 0
    return {
        "contention_verdict": VERDICT_CONTENDED if contended else VERDICT_CLEAN,
        "samples": len(samples),
        "foreign_cpu_p50": round(ordered[len(ordered) // 2], 1),
        "foreign_cpu_mean": round(sum(samples) / len(samples), 1),
        "foreign_cpu_max": round(ordered[-1], 1),
        "direct_overlap_lines": counts["direct_overlap"],
        "smt_sibling_lines": counts["smt_sibling"],
        "disjoint_lines": counts["disjoint"],
        "gone_lines": counts["gone"],
        "sampler_version": SAMPLER_VERSION,
    }


def summarize_rows(text: str) -> dict[str, Any]:
    """Token-weighted decode rate (pred_n >= 16 floor) and coherence counts by reason."""
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise CaptureError(f"rows.jsonl is not JSONL: {exc}") from None
    if not rows:
        raise CaptureError("rows.jsonl is empty: nothing was measured")
    decode = [r for r in rows
              if _finite(r.get("pred_n")) and r["pred_n"] >= PRED_N_FLOOR
              and _finite(r.get("pred_ms")) and r["pred_ms"] > 0]
    if not decode:
        raise CaptureError(f"no row clears the pred_n >= {PRED_N_FLOOR} floor")
    tokens = sum(r["pred_n"] for r in decode)
    seconds = sum(r["pred_ms"] for r in decode) / 1000.0
    reasons: dict[str, int] = {}
    for row in rows:
        key = str(row.get("verdict") or "UNCLASSIFIED")
        reasons[key] = reasons.get(key, 0) + 1
    return {
        "value": round(tokens / seconds, 4),
        "n_rows": len(rows),
        "n_decode_rows": len(decode),
        "decode_tokens": int(tokens),
        "coherence_by_reason": dict(sorted(reasons.items())),
    }


# --- the shared validator -------------------------------------------------------------------

_LAUNCH_TEXT = ("launch_id", "model_path", "binary_version", "pinning", "bench_cpus")


def validate_row(row: Any) -> list[str]:
    """Every structural problem in one producer-authored row. Empty list == valid.

    Shared by the writer (refuse to emit) and the reader (refuse to project).
    """
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for key in ("producer", "measurement_id", "metric", "unit", "claim", "protocol_id",
                "reps_basis", "rows_path", "date", "label"):
        if not _text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if _text(row.get("label")) and not _LABEL.match(row["label"]):
        p.append("label must be a plain arm label")
    emitted = _parse_utc(row.get("emitted_at"))
    if emitted is None:
        p.append("emitted_at must be a UTC timestamp")
    if row.get("metric") not in METRICS:
        p.append(f"metric must be one of {list(METRICS)}")
    if row.get("unit") != UNIT:
        p.append(f"unit must be {UNIT!r}")
    if row.get("metric_direction") != "higher_better":
        p.append("metric_direction must be recorded as higher_better (decode rate)")
    if row.get("category") not in _CATEGORIES:
        p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
    if not _SHA256.match(str(row.get("rows_sha256", ""))):
        p.append("rows_sha256 must be a 64-hex digest over the arm's rows.jsonl")
    if not _finite(row.get("value")) or (_finite(row.get("value")) and row["value"] <= 0):
        p.append("value must be a positive finite decode rate")
    if row.get("reps") != 1 or not str(row.get("reps_basis", "")).startswith("scored:launch"):
        p.append("reps must be 1 with a scored:launch basis — per-prompt rows of one launch "
                 "are samples of one witness, not independent ones (SC6-HAZARD)")

    extra = row.get("extra")
    if not isinstance(extra, dict):
        return p + ["extra must be an object carrying the arm identity and verdict"]

    # -- the contention verdict: the field the hook exists for --------------------------------
    contention = extra.get("contention")
    if not isinstance(contention, dict):
        p.append("extra.contention is required — no verdict, no row")
        contention = {}
    verdict = contention.get("contention_verdict")
    if verdict not in VERDICTS:
        p.append(f"extra.contention.contention_verdict must be one of {sorted(VERDICTS)}")
    sampler_version = contention.get("sampler_version")
    if not _nonneg_int(sampler_version) or sampler_version < MIN_SAMPLER_VERSION:
        p.append(f"extra.contention.sampler_version must be >= {MIN_SAMPLER_VERSION}: the "
                 "legacy sampler read cpus 96-191 as disjoint, so its verdicts are wrong")
    for key in ("samples", "direct_overlap_lines", "smt_sibling_lines", "disjoint_lines",
                "gone_lines"):
        if not _nonneg_int(contention.get(key)):
            p.append(f"extra.contention.{key} must be a non-negative integer")
    if _nonneg_int(contention.get("samples")) and contention["samples"] == 0:
        p.append("extra.contention.samples must be positive — a verdict over zero samples is "
                 "not a verdict")
    for key in ("foreign_cpu_p50", "foreign_cpu_mean", "foreign_cpu_max"):
        if not _finite(contention.get(key)):
            p.append(f"extra.contention.{key} must be a finite number")
    if (verdict in VERDICTS and _nonneg_int(contention.get("direct_overlap_lines"))
            and _nonneg_int(contention.get("smt_sibling_lines"))):
        contended = contention["direct_overlap_lines"] + contention["smt_sibling_lines"] > 0
        if contended != (verdict == VERDICT_CONTENDED):
            p.append("extra.contention.contention_verdict does not follow from the DIRECT / "
                     "SMT-SIBLING line counts")
    if not _SHA256.match(str(extra.get("coresidency_sha256", ""))):
        p.append("extra.coresidency_sha256 must hash the sampler file the verdict came from")

    # -- the date gate: pre-fix arms are worse than absent ------------------------------------
    started = _parse_utc(extra.get("arm_started_at"))
    ended = _parse_utc(extra.get("arm_ended_at"))
    if started is None:
        p.append("extra.arm_started_at must be a UTC timestamp — an undated arm cannot be "
                 "placed after the sampler fix, so it fails closed")
    elif started < _fix_instant():
        p.append(f"arm started {started.isoformat()} before {SAMPLER_FIX_DATE}: its contention "
                 "label came from the sampler that read cpus 184-191 as disjoint — zero rows")
    if ended is None:
        p.append("extra.arm_ended_at must be a UTC timestamp")
    elif started is not None and ended < started:
        p.append("extra.arm_ended_at precedes extra.arm_started_at")
    if ended is not None and emitted is not None:
        lag = (emitted - ended).total_seconds()
        if lag > MAX_CAPTURE_LAG_S:
            p.append(f"captured {int(lag)}s after the arm ended (limit {MAX_CAPTURE_LAG_S}s): "
                     "a verdict attached after the fact is a backfill, not a write-side hook")
        if lag < -60:
            p.append("emitted_at precedes the arm's end")
    if started is not None and row.get("date") != started.strftime("%Y-%m-%d"):
        p.append("date must be the arm's UTC start date")

    # -- launch identity: nothing guessed -----------------------------------------------------
    for key in _LAUNCH_TEXT:
        if not _text(extra.get(key)):
            p.append(f"extra.{key} must be recorded")
    if not _SHA256.match(str(extra.get("gguf_sha256", ""))):
        p.append("extra.gguf_sha256 must be the 64-hex model digest")
    if not _COMMIT.match(str(extra.get("kernel_commit", ""))):
        p.append("extra.kernel_commit must be a hex commit id")
    recipe = extra.get("launch_recipe")
    if not isinstance(recipe, dict) or not isinstance(recipe.get("env"), dict) \
            or not isinstance(recipe.get("args"), list):
        p.append("extra.launch_recipe must carry env (object) and args (list)")
    if not _thp_state_ok(extra.get("thp_knob_state")):
        p.append(f"extra.thp_knob_state must be 'unset' or 'set:<value>' — the {_THP_KNOB} "
                 "state is part of the artifact's identity")
    elif isinstance(recipe, dict) and isinstance(recipe.get("env"), dict):
        env_val = recipe["env"].get(_THP_KNOB)
        expected = "unset" if env_val is None else f"set:{env_val}"
        if extra["thp_knob_state"] != expected:
            p.append(f"extra.thp_knob_state disagrees with launch_recipe.env[{_THP_KNOB}]")

    # -- sample accounting --------------------------------------------------------------------
    for key in ("n_rows", "n_decode_rows", "decode_tokens"):
        if not _nonneg_int(extra.get(key)):
            p.append(f"extra.{key} must be a non-negative integer")
    if extra.get("pred_n_floor") != PRED_N_FLOOR:
        p.append(f"extra.pred_n_floor must be {PRED_N_FLOOR}")
    if not isinstance(extra.get("coherence_by_reason"), dict) or not extra["coherence_by_reason"]:
        p.append("extra.coherence_by_reason must count coherence by REASON")
    sd = extra.get("between_launch_sd")
    group = extra.get("replicate_group")
    if sd is None:
        if group is not None:
            p.append("extra.replicate_group without between_launch_sd")
    elif not _finite(sd) or sd < 0 or not _text(group) \
            or not _nonneg_int(extra.get("replicate_launches")) \
            or extra["replicate_launches"] < 2:
        p.append("extra.between_launch_sd needs a replicate_group and replicate_launches >= 2 "
                 "— an sd over one launch is not a between-launch sd")

    expected_id = None
    if (_text(extra.get("launch_id")) and _text(row.get("label"))
            and _text(extra.get("arm_started_at")) and row.get("metric") in METRICS
            and verdict in VERDICTS and _SHA256.match(str(row.get("rows_sha256", "")))):
        expected_id = measurement_identity(
            launch_id=extra["launch_id"], label=row["label"],
            arm_started_at=extra["arm_started_at"], metric=row["metric"],
            contention_verdict=verdict, rows_sha256=row["rows_sha256"])
    if expected_id is not None and row.get("measurement_id") != expected_id:
        p.append("measurement_id does not re-derive from (launch_id, label, arm_started_at, "
                 "metric, contention_verdict, rows_sha256)")
    if not _SHA256.match(str(row.get("row_sha256", ""))):
        p.append("row_sha256 must be a 64-hex self-hash")
    else:
        try:
            if row_digest(row) != row["row_sha256"]:
                p.append("row_sha256 does not bind the row content")
        except CaptureError as exc:
            p.append(f"row is not canonically hashable: {exc}")
    return p


# --- the writer -------------------------------------------------------------------------------

def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_str(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sidecar_path_for(run_dir: str | Path, label: str) -> Path:
    return Path(run_dir) / f"{label}{SIDECAR_SUFFIX}"


def write_arm_measurement(
    run_dir: str | Path,
    label: str,
    *,
    launch: Mapping[str, Any],
    arm_started_at: str,
    producer: str,
    category: str = "CANDIDATE",
    emitted_at: str | None = None,
    arm_ended_at: str | None = None,
) -> Path:
    """Emit ``<label>.belief_measurements.jsonl`` for one finished arm — the SC75 hook.

    ``launch`` carries the producer's launch identity: ``launch_id``, ``model_path``,
    ``gguf_sha256``, ``kernel_commit``, ``binary_version``, ``launch_recipe`` ({env, args}),
    ``pinning``, ``bench_cpus`` and optionally ``replicate_group`` / ``replicate_launches`` /
    ``between_launch_sd``. ``arm_ended_at`` defaults to the rows file's mtime, which is
    when the harness finished writing it. Any problem raises :class:`CaptureError` and
    nothing is written.
    """
    if not _text(label) or not _LABEL.match(label):
        raise CaptureError(f"label {label!r} is not a plain arm label")
    run = Path(run_dir)
    rows_path = run / f"{label}.rows.jsonl"
    cores_path = run / f"{label}.coresidency"
    if not rows_path.is_file():
        raise CaptureError(f"arm rows missing: {rows_path} — call this at arm end")
    if not cores_path.is_file():
        raise CaptureError(f"coresidency missing: {cores_path} — no verdict, no row")
    if not isinstance(launch, Mapping):
        raise CaptureError("launch must be the producer's launch identity mapping")

    contention = summarize_contention(cores_path.read_text(errors="replace"))
    measured = summarize_rows(rows_path.read_text())
    ended = arm_ended_at or _utc_str(
        datetime.fromtimestamp(rows_path.stat().st_mtime, tz=timezone.utc))
    when = emitted_at or _utc_str(datetime.now(timezone.utc))
    started = _parse_utc(arm_started_at)
    if started is None:
        raise CaptureError("arm_started_at must be a UTC timestamp")
    rows_sha256 = _file_sha256(rows_path)

    recipe = launch.get("launch_recipe")
    env = recipe.get("env") if isinstance(recipe, Mapping) else None
    thp_state = None
    if isinstance(env, Mapping):
        thp_state = "unset" if env.get(_THP_KNOB) is None else f"set:{env[_THP_KNOB]}"

    extra: dict[str, Any] = {
        **{key: launch.get(key) for key in _LAUNCH_TEXT},
        "gguf_sha256": launch.get("gguf_sha256"),
        "kernel_commit": launch.get("kernel_commit"),
        "launch_recipe": dict(recipe) if isinstance(recipe, Mapping) else recipe,
        "thp_knob_state": thp_state,
        "arm_started_at": _utc_str(started),
        "arm_ended_at": ended,
        "contention": contention,
        "coresidency_path": str(cores_path),
        "coresidency_sha256": _file_sha256(cores_path),
        "n_rows": measured["n_rows"],
        "n_decode_rows": measured["n_decode_rows"],
        "decode_tokens": measured["decode_tokens"],
        "pred_n_floor": PRED_N_FLOOR,
        "coherence_by_reason": measured["coherence_by_reason"],
        "replicate_group": launch.get("replicate_group"),
        "replicate_launches": launch.get("replicate_launches"),
        "between_launch_sd": launch.get("between_launch_sd"),
    }
    if extra["between_launch_sd"] is None:
        extra.pop("replicate_launches")
        extra["between_launch_sd_basis"] = "absent: not supplied by the producer for this launch"

    verdict = contention["contention_verdict"]
    row: dict[str, Any] = {
        "schema": CAPTURE_SCHEMA,
        "producer": producer,
        "label": label,
        "emitted_at": when,
        "date": started.strftime("%Y-%m-%d"),
        "measurement_id": measurement_identity(
            launch_id=str(launch.get("launch_id") or ""), label=label,
            arm_started_at=extra["arm_started_at"], metric=METRIC,
            contention_verdict=verdict, rows_sha256=rows_sha256),
        "metric": METRIC,
        "value": measured["value"],
        "unit": UNIT,
        "metric_direction": "higher_better",
        "category": category,
        "claim": (f"INF-70 serving arm {label} (launch {launch.get('launch_id')}): "
                  f"token-weighted decode {measured['value']:.4f} tokens/s over "
                  f"{measured['n_decode_rows']} rows (pred_n>={PRED_N_FLOOR}) of ONE launch; "
                  f"contention {verdict} (direct={contention['direct_overlap_lines']}, "
                  f"smt_sibling={contention['smt_sibling_lines']}, "
                  f"foreign_cpu_max={contention['foreign_cpu_max']}), "
                  f"{_THP_KNOB} {thp_state}"),
        "protocol_id": CAPTURE_SCHEMA,
        "reps": 1,
        "reps_basis": (f"scored:launch (the {measured['n_rows']} per-prompt rows are samples "
                       "of this one launch)"),
        "rows_path": str(rows_path),
        "rows_sha256": rows_sha256,
        "extra": extra,
    }
    row["row_sha256"] = row_digest(row)
    problems = validate_row(row)
    if problems:
        raise CaptureError(f"{label}: refusing to emit an invalid row: " + "; ".join(problems))

    sidecar = sidecar_path_for(run, label)
    tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
    with open(tmp, "w") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, sidecar)
    return sidecar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SC75: emit the INF-70 serving-arm belief sidecar at arm end.")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--launch-json", required=True, type=Path,
                        help="producer launch identity (see write_arm_measurement)")
    parser.add_argument("--arm-started-at", required=True, help="UTC ISO-8601")
    parser.add_argument("--producer", default="inf70-serving-harness")
    parser.add_argument("--category", default="CANDIDATE", choices=sorted(_CATEGORIES))
    args = parser.parse_args(argv)
    try:
        launch = json.loads(args.launch_json.read_text())
        sidecar = write_arm_measurement(
            args.run_dir, args.label, launch=launch, arm_started_at=args.arm_started_at,
            producer=args.producer, category=args.category)
    except (CaptureError, OSError, json.JSONDecodeError) as exc:
        print(f"SC75 capture refused: {exc}", file=sys.stderr)
        return 2
    print(f"belief sidecar: {sidecar}")
    return 0


__all__ = [
    "CAPTURE_SCHEMA", "SIDECAR_SUFFIX", "METRIC", "METRICS", "UNIT", "PRED_N_FLOOR",
    "SAMPLER_VERSION", "MIN_SAMPLER_VERSION", "SAMPLER_FIX_DATE", "MAX_CAPTURE_LAG_S",
    "VERDICT_CONTENDED", "VERDICT_CLEAN", "VERDICTS", "CaptureError", "content_hash",
    "row_digest", "measurement_identity", "summarize_contention", "summarize_rows",
    "validate_row", "sidecar_path_for", "write_arm_measurement", "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
