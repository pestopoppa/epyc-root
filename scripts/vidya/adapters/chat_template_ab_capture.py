"""CT-8 / SC46 write-side hook: producer-authored belief rows for chat-template A/B runs.

A chat-template A/B runner (CT-1 family: CT-1, CT-1b, CT-5(c)+16K, E-7 recalibration) calls
:func:`write_belief_measurements` at summarize-time to emit a ``belief_measurements.jsonl``
sidecar next to its ``summary.json`` — one claim-tuple-shaped row per (arm, suite) cell.

The row vocabulary is the established producer contract (``hip_authoring_arm.py``,
``arena_cell_runner.py``: ``measurement_id / metric / value / unit / metric_direction / category /
claim / protocol_id / reps / reps_basis / extra`` plus a self-hash), not a new dialect. The
domain-specific identity — model, quant, template_sha256, kernel/binary stamp, sampling, serving
path, paired flips — rides in ``extra``.

Two refusals are the point of the hook:

* **Nothing is guessed.** The kernel identity comes from the run's recorded stamp (the runner
  captures ``llama-server --version`` / the verify script's output at launch); the template digests
  are the actual bytes served. The writer validates shape and refuses to emit rather than fill in
  what the run did not capture — a tuple invented at write time is as fake as one invented on read.
* **Pre-hook runs stay pre-hook.** This module writes sidecars only when a runner calls it at
  summarize-time. It is never invoked over a finished run directory to backfill one (the DF2-4
  precedent): the completed CT-1/CT-1b/CT-5/16K runs and any run already in flight when the hook
  landed emit zero rows, permanently.

The strict read side is ``chat_template_ab.py``; it imports the vocabulary from here so the writer
and reader cannot drift into two dialects of one schema.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

CAPTURE_SCHEMA = "epyc.vidya.chat_template_ab_capture.v1"
SIDECAR_NAME = "belief_measurements.jsonl"
METRIC = "chat_template_suite_accuracy"
UNIT = "fraction_correct"
SERVING_MODES = frozenset({"test_port", "live_production"})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")

_CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})
_DIRECTIONS = frozenset({"higher_better", "lower_better"})


class CaptureError(ValueError):
    """The runner asked for a sidecar it did not capture the identity for."""


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
    """Self-hash over everything but the hash field itself."""
    unsigned = {k: v for k, v in row.items() if k != "row_sha256"}
    return content_hash(unsigned)


def measurement_identity(*, run_id: str, arm: int, suite: str,
                         template_sha256: str, results_sha256: str) -> str:
    digest = content_hash({
        "run_id": run_id, "arm": arm, "suite": suite,
        "template_sha256": template_sha256, "results_sha256": results_sha256,
    })
    return f"ctab_{digest[:24]}"


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


def validate_row(row: Any) -> list[str]:
    """Every structural problem in one producer-authored row. Empty list == valid.

    Shared by the writer (refuse to emit) and the reader (refuse to project), so there is exactly
    one definition of "well-formed" — the 2026-08-10 two-dialects lesson applied to a schema.
    """
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []

    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for key in ("run_id", "producer", "measurement_id", "metric", "unit", "claim",
                "protocol_id", "reps_basis", "results_path", "date"):
        if not _text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not _utc_timestamp(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    if row.get("metric_direction") not in _DIRECTIONS:
        p.append("metric_direction must be recorded as higher_better or lower_better")
    if row.get("category") not in _CATEGORIES:
        p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
    if not _SHA256.match(str(row.get("results_sha256", ""))):
        p.append("results_sha256 must be a 64-hex digest over the per-question results file")

    extra = row.get("extra")
    if not isinstance(extra, dict):
        return p + ["extra must be an object carrying the run identity"]

    if not _text(extra.get("suite")):
        p.append("extra.suite must be a non-empty string")
    if not _nonneg_int(extra.get("arm")):
        p.append("extra.arm must be a non-negative integer")
    if not _nonneg_int(extra.get("baseline_arm")):
        p.append("extra.baseline_arm must be a non-negative integer")
    if not _text(extra.get("arm_label")):
        p.append("extra.arm_label must be a non-empty string")
    if not _SHA256.match(str(extra.get("template_sha256", ""))):
        p.append("extra.template_sha256 must be a 64-hex digest — the template axis is the "
                 "whole point of this family (SC46)")
    for key in ("model_path", "model_name", "quant"):
        if not _text(extra.get(key)):
            p.append(f"extra.{key} must be a non-empty string")

    kernel = extra.get("kernel")
    if not isinstance(kernel, dict):
        p.append("extra.kernel must be an object (the run's recorded stamp)")
    else:
        if not _COMMIT.match(str(kernel.get("source_commit", ""))):
            p.append("extra.kernel.source_commit must be the 40-hex commit from the run's "
                     "recorded stamp, never a guess")
        if not _text(kernel.get("binary_version")):
            p.append("extra.kernel.binary_version must be recorded")

    serving = extra.get("serving")
    if not isinstance(serving, dict) or serving.get("mode") not in SERVING_MODES:
        p.append(f"extra.serving.mode must be one of {sorted(SERVING_MODES)}")

    sampling = extra.get("sampling")
    if not isinstance(sampling, dict):
        p.append("extra.sampling must be an object")
    else:
        if not _finite(sampling.get("temperature")):
            p.append("extra.sampling.temperature must be recorded (sampling-sensitive suites)")
        if not _nonneg_int(sampling.get("seed")):
            p.append("extra.sampling.seed must be recorded (pinned-seed protocol)")

    n = extra.get("n")
    if not _nonneg_int(n) or n == 0:
        p.append("extra.n must be a positive integer")
    else:
        for key in ("correct", "errors", "truncated"):
            v = extra.get(key)
            if not _nonneg_int(v) or v > n:
                p.append(f"extra.{key} must be an integer in [0, n]")
        if _nonneg_int(extra.get("correct")) and extra["correct"] <= n:
            if not _finite(row.get("value")) or not math.isclose(
                    row["value"], extra["correct"] / n, rel_tol=1e-12, abs_tol=1e-15):
                p.append("value must equal extra.correct / extra.n")
        if row.get("reps") != n:
            p.append("reps must equal extra.n (per-question cells; the question is the rep)")
        errors = extra.get("errors")
        basis = str(row.get("reps_basis", ""))
        if _nonneg_int(errors):
            if errors == 0 and basis != "scored:questions":
                p.append("reps_basis must be 'scored:questions' when every question scored")
            if errors > 0 and not basis.startswith("attempted"):
                p.append("reps_basis must state ATTEMPTED when errored questions were counted "
                         "as incorrect — n would otherwise overstate the sample")
    if "mean_tokens" in extra and extra["mean_tokens"] is not None \
            and not _finite(extra["mean_tokens"]):
        p.append("extra.mean_tokens must be finite when present")

    arm, baseline = extra.get("arm"), extra.get("baseline_arm")
    if _nonneg_int(arm) and _nonneg_int(baseline):
        if arm == baseline:
            if row.get("category") != "BASELINE":
                p.append("the baseline arm's row must carry category BASELINE")
            if any(key in extra for key in ("flips_01", "flips_10", "paired_against_arm")):
                p.append("the baseline arm carries no paired-flip counts")
        else:
            if row.get("category") == "BASELINE":
                p.append("a non-baseline arm must not claim category BASELINE")
            if "flips_01" in extra or "flips_10" in extra or "paired_against_arm" in extra:
                if (not _nonneg_int(extra.get("flips_01"))
                        or not _nonneg_int(extra.get("flips_10"))
                        or extra.get("paired_against_arm") != baseline):
                    p.append("paired flips must carry flips_01, flips_10 and "
                             "paired_against_arm == baseline_arm, or be absent entirely")

    expected_id = None
    if (_text(row.get("run_id")) and _nonneg_int(extra.get("arm")) and _text(extra.get("suite"))
            and _SHA256.match(str(extra.get("template_sha256", "")))
            and _SHA256.match(str(row.get("results_sha256", "")))):
        expected_id = measurement_identity(
            run_id=row["run_id"], arm=extra["arm"], suite=extra["suite"],
            template_sha256=extra["template_sha256"], results_sha256=row["results_sha256"])
    if expected_id is not None and row.get("measurement_id") != expected_id:
        p.append("measurement_id does not re-derive from (run_id, arm, suite, "
                 "template_sha256, results_sha256)")
    if not _SHA256.match(str(row.get("row_sha256", ""))):
        p.append("row_sha256 must be a 64-hex self-hash")
    else:
        try:
            if row_digest(row) != row["row_sha256"]:
                p.append("row_sha256 does not bind the row content")
        except CaptureError as exc:
            p.append(f"row is not canonically hashable: {exc}")
    return p


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_belief_measurements(
    run_dir: str | Path, *,
    run_id: str,
    producer: str,
    model_path: str,
    model_name: str,
    quant: str,
    kernel: Mapping[str, Any],
    serving: Mapping[str, Any],
    sampling: Mapping[str, Any],
    arms: Mapping[int, Mapping[str, Any]],
    baseline_arm: int = 0,
    summary: Mapping[str, Any] | None = None,
    emitted_at: str | None = None,
) -> Path:
    """Emit ``belief_measurements.jsonl`` next to ``summary.json`` — the CT-8 write-side hook.

    ``arms`` maps arm index -> ``{"label": str, "template_sha256": 64-hex,
    "results_path": optional str}`` (default ``<run_dir>/results_arm<i>.jsonl``). ``kernel`` is the
    run's RECORDED stamp — at minimum ``source_commit`` (40-hex) and ``binary_version`` — captured
    by the runner at launch, never typed from memory. Everything is validated through
    :func:`validate_row`; any problem raises :class:`CaptureError` and nothing is written.

    Per-suite paired flips (``flips_01`` / ``flips_10``, the summary's own vocabulary, carried
    verbatim) attach to the non-baseline arm only, and only in two-arm runs where the summary
    recorded them — where the run has them, in the task's words.
    """
    root = Path(run_dir)
    if summary is None:
        summary_path = root / "summary.json"
        if not summary_path.is_file():
            raise CaptureError(f"no summary.json in {root} — call this at summarize-time")
        summary = json.loads(summary_path.read_text())
    if not isinstance(summary, Mapping) or not summary:
        raise CaptureError("summary must be a non-empty per-suite mapping")
    if not arms:
        raise CaptureError("at least one arm is required")
    if baseline_arm not in arms:
        raise CaptureError("baseline_arm must be one of the declared arms")
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    per_arm: dict[int, dict[str, Any]] = {}
    for arm, spec in arms.items():
        if not _nonneg_int(arm):
            raise CaptureError("arm indices must be non-negative integers")
        results_path = Path(spec.get("results_path") or root / f"results_arm{arm}.jsonl")
        if not results_path.is_file():
            raise CaptureError(f"arm {arm}: per-question results file missing: {results_path}")
        per_arm[arm] = {
            "label": spec.get("label"),
            "template_sha256": str(spec.get("template_sha256", "")),
            "results_path": str(results_path),
            "results_sha256": _file_sha256(results_path),
        }

    rows: list[dict[str, Any]] = []
    for suite, cells in summary.items():
        if not isinstance(cells, Mapping):
            raise CaptureError(f"suite {suite!r}: summary entry is not an object")
        for arm in sorted(per_arm):
            cell = cells.get(f"arm{arm}")
            if not isinstance(cell, Mapping):
                raise CaptureError(f"suite {suite!r}: no summary cell for arm{arm}")
            for key in ("n", "correct", "truncated", "errors"):
                if not _nonneg_int(cell.get(key)):
                    raise CaptureError(f"suite {suite!r} arm{arm}: summary cell lacks {key}")
            n, correct, errors = cell["n"], cell["correct"], cell["errors"]
            if n < 1:
                raise CaptureError(f"suite {suite!r} arm{arm}: empty cell is not a measurement")
            info = per_arm[arm]
            extra: dict[str, Any] = {
                "suite": suite,
                "arm": arm,
                "baseline_arm": baseline_arm,
                "arm_label": info["label"],
                "template_sha256": info["template_sha256"],
                "model_path": model_path,
                "model_name": model_name,
                "quant": quant,
                "kernel": dict(kernel),
                "serving": dict(serving),
                "sampling": dict(sampling),
                "n": n,
                "correct": correct,
                "errors": errors,
                "truncated": cell["truncated"],
                "mean_tokens": cell.get("mean_tokens"),
            }
            if arm != baseline_arm and len(per_arm) == 2 \
                    and _nonneg_int(cells.get("flips_01")) and _nonneg_int(cells.get("flips_10")):
                extra["flips_01"] = cells["flips_01"]
                extra["flips_10"] = cells["flips_10"]
                extra["paired_against_arm"] = baseline_arm
            row: dict[str, Any] = {
                "schema": CAPTURE_SCHEMA,
                "run_id": run_id,
                "producer": producer,
                "emitted_at": when,
                "date": when[:10],
                "measurement_id": measurement_identity(
                    run_id=run_id, arm=arm, suite=suite,
                    template_sha256=info["template_sha256"],
                    results_sha256=info["results_sha256"]),
                "metric": METRIC,
                "value": correct / n,
                "unit": UNIT,
                "metric_direction": "higher_better",
                "category": "BASELINE" if arm == baseline_arm else "CANDIDATE",
                "claim": (f"Chat-template A/B {run_id}: arm{arm} ({info['label']}, template "
                          f"{info['template_sha256'][:12]}…) scored {correct}/{n} on {suite}"),
                "protocol_id": CAPTURE_SCHEMA,
                "reps": n,
                "reps_basis": ("scored:questions" if errors == 0 else
                               f"attempted:questions ({errors} errored, counted incorrect)"),
                "results_path": info["results_path"],
                "results_sha256": info["results_sha256"],
                "extra": extra,
            }
            row["row_sha256"] = row_digest(row)
            problems = validate_row(row)
            if problems:
                raise CaptureError(
                    f"suite {suite!r} arm{arm}: refusing to emit an invalid row: "
                    + "; ".join(problems))
            rows.append(row)

    sidecar = root / SIDECAR_NAME
    tmp = sidecar.with_suffix(".jsonl.tmp")
    with open(tmp, "w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, sidecar)
    return sidecar


__all__ = [
    "CAPTURE_SCHEMA", "SIDECAR_NAME", "METRIC", "UNIT", "SERVING_MODES", "CaptureError",
    "content_hash", "row_digest", "measurement_identity", "validate_row",
    "write_belief_measurements",
]
