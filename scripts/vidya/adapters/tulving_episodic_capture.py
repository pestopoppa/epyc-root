"""SC67 write-side hook: producer-authored belief rows for Tulving episodic scored runs.

``epyc-inference-research/scripts/benchmark/score_tulving_run.py`` calls
:func:`write_belief_measurements` at score-time (``--belief-measurements``) to emit a
``belief_measurements.jsonl`` sidecar next to the scored artifact — one claim-tuple-shaped
row per headline metric of one run arm.

The row vocabulary is the established producer contract (``chat_template_ab_capture.py``,
``hip_authoring_arm.py``, ``arena_cell_runner.py``): ``measurement_id / metric / value /
unit / metric_direction / category / claim / protocol_id / reps / reps_basis / extra`` plus
a self-hash. The domain identity — run id, variant + chapter count, arm, scorer version,
subset sizes, bin basis — rides in ``extra``. The strict read side is
``tulving_episodic.py``, which imports this vocabulary so writer and reader cannot drift
into two dialects of one schema (the 2026-08-10 lesson).

Four refusals are the point of the hook:

* **Locator = the RUN, never the per-question file** (the SC6-HAZARD class). A Tulving run
  scores hundreds of questions from ONE harness execution; they are samples, not
  independent witnesses. Every row for a run shares the run locator, and the metric name is
  what separates the claims.
* **Scorer version is mandatory and must be post-M-12e.** The pre-M-12e scorer computed
  Simple Recall over EVERY question (including the Chronological Awareness legs), so its
  figures are a different quantity under the same name. A row carrying
  ``scorer_version < 2`` is refused: it would put two incomparable quantities behind one
  metric id.
* **Pre-hook runs stay pre-hook.** This writer is called by the scorer at score-time.
  Run ``20260619_141212`` and every other run scored before this hook emit **zero rows**,
  permanently — a tuple invented on read claims warrant the original run never captured.
  (Re-scoring an old run's stored responses does not change that: the *arm identity* — was
  this memory-off, retrieved, or full-book — was never recorded by that harness, and the
  writer refuses to guess it.)
* **Nothing is guessed.** ``arm`` must be one of the three M-12a arms, the chapter count and
  variant must be the ones the run actually used, and ``n`` is the count of questions that
  SCORED in the subset the metric is about — not the count attempted, and not the whole
  question set.

Metric direction is recorded, never inferred: both headline metrics are higher-better, and
``chronological_awareness_score`` additionally carries its partial-coverage count, because a
CAS figure whose tau leg silently failed closed on most questions is a different number from
one that did not.
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

CAPTURE_SCHEMA = "epyc.vidya.tulving_episodic_capture.v1"
SIDECAR_NAME = "belief_measurements.jsonl"

#: The Simple Recall / Chronological Awareness headline metrics. Separate claim ids because
#: they are computed over DISJOINT question subsets and answer different questions.
SIMPLE_RECALL_METRIC = "tulving_simple_recall_score"
CHRONOLOGICAL_METRIC = "tulving_chronological_awareness_score"
METRICS = (SIMPLE_RECALL_METRIC, CHRONOLOGICAL_METRIC)
UNIT = "score"

#: The three prompt-matched M-12a arms. ``none`` = memory-off, ``retrieved`` = the retrieval
#: surface fills the context, ``full`` = the whole book in context (the ceiling).
ARMS = frozenset({"none", "retrieved", "full"})

#: M-12e landed scorer version 2. Anything below it is a different quantity (see above).
MIN_SCORER_VERSION = 2

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})
_DIRECTIONS = frozenset({"higher_better", "lower_better"})


class CaptureError(ValueError):
    """The scorer asked for a sidecar it did not capture the identity for."""


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


def measurement_identity(*, run_id: str, arm: str, variant: str, chapters: int,
                         metric: str, scored_sha256: str) -> str:
    digest = content_hash({
        "run_id": run_id, "arm": arm, "variant": variant, "chapters": chapters,
        "metric": metric, "scored_sha256": scored_sha256,
    })
    return f"tulv_{digest[:24]}"


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

    Shared by the writer (refuse to emit) and the reader (refuse to project), so there is
    exactly one definition of "well-formed".
    """
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []

    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for key in ("run_id", "producer", "measurement_id", "metric", "unit", "claim",
                "protocol_id", "reps_basis", "scored_path", "date"):
        if not _text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not _utc_timestamp(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    if row.get("metric") not in METRICS:
        p.append(f"metric must be one of {sorted(METRICS)}")
    if row.get("metric_direction") not in _DIRECTIONS:
        p.append("metric_direction must be recorded as higher_better or lower_better")
    if row.get("category") not in _CATEGORIES:
        p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
    if not _SHA256.match(str(row.get("scored_sha256", ""))):
        p.append("scored_sha256 must be a 64-hex digest over the scored artifact")
    if not _finite(row.get("value")):
        p.append("value must be a finite number")

    extra = row.get("extra")
    if not isinstance(extra, dict):
        return p + ["extra must be an object carrying the run identity"]

    if extra.get("arm") not in ARMS:
        p.append(f"extra.arm must be one of {sorted(ARMS)} — the arm is the whole point of "
                 "an A/B and is never inferred on read")
    if not _text(extra.get("variant")):
        p.append("extra.variant must name the dataset variant (e.g. Udefault_Sdefault_seed0)")
    if not _nonneg_int(extra.get("chapters")) or extra.get("chapters") == 0:
        p.append("extra.chapters must be the positive chapter count the run actually used")
    if not _nonneg_int(extra.get("scorer_version")):
        p.append("extra.scorer_version must be recorded")
    elif extra["scorer_version"] < MIN_SCORER_VERSION:
        p.append(f"extra.scorer_version must be >= {MIN_SCORER_VERSION} (post-M-12e); the "
                 "pre-M-12e scorer computed Simple Recall over every question, which is a "
                 "different quantity under the same name")
    if not _text(extra.get("model_role")):
        p.append("extra.model_role must be recorded")
    for key in ("result_questions", "scored_questions", "missing_ground_truth"):
        if not _nonneg_int(extra.get(key)):
            p.append(f"extra.{key} must be a non-negative integer")

    n = row.get("reps")
    if not _nonneg_int(n) or n == 0:
        p.append("reps must be a positive integer — the count of questions that SCORED in "
                 "the subset this metric is about")
    basis = str(row.get("reps_basis", ""))
    if _nonneg_int(extra.get("missing_ground_truth")):
        if extra["missing_ground_truth"] == 0 and not basis.startswith("scored:"):
            p.append("reps_basis must state SCORED when every question resolved its ground truth")
        if extra["missing_ground_truth"] > 0 and not basis.startswith("attempted:"):
            p.append("reps_basis must state ATTEMPTED when questions were dropped for missing "
                     "ground truth — n would otherwise overstate the sample")

    metric = row.get("metric")
    if metric == SIMPLE_RECALL_METRIC:
        if not _nonneg_int(extra.get("simple_recall_questions")):
            p.append("extra.simple_recall_questions must be a non-negative integer")
        elif row.get("reps") != extra["simple_recall_questions"]:
            p.append("reps must equal extra.simple_recall_questions — Simple Recall is scored "
                     "over the get=='all' subset only (M-12e)")
        if not _text(extra.get("simple_recall_bin_basis")):
            p.append("extra.simple_recall_bin_basis must record which basis binned the five "
                     "bins (nb_events, or the nb_gt fallback)")
        bins = extra.get("simple_recall_bins")
        if not isinstance(bins, dict) or not bins:
            p.append("extra.simple_recall_bins must carry the five bins, bin 0 included — the "
                     "hallucination bin is the point")
        elif "0" not in bins:
            p.append("extra.simple_recall_bins must include bin 0")
    elif metric == CHRONOLOGICAL_METRIC:
        for key in ("latest_questions", "chronological_questions",
                    "chronological_partial_coverage"):
            if not _nonneg_int(extra.get(key)):
                p.append(f"extra.{key} must be a non-negative integer")
        if (_nonneg_int(extra.get("latest_questions"))
                and _nonneg_int(extra.get("chronological_questions"))
                and row.get("reps") != extra["latest_questions"]
                + extra["chronological_questions"]):
            p.append("reps must equal extra.latest_questions + extra.chronological_questions "
                     "— the CA score folds both legs")
        if (_nonneg_int(extra.get("chronological_partial_coverage"))
                and _nonneg_int(extra.get("chronological_questions"))
                and extra["chronological_partial_coverage"] > extra["chronological_questions"]):
            p.append("extra.chronological_partial_coverage cannot exceed "
                     "extra.chronological_questions")

    expected_id = None
    if (_text(row.get("run_id")) and extra.get("arm") in ARMS and _text(extra.get("variant"))
            and _nonneg_int(extra.get("chapters")) and row.get("metric") in METRICS
            and _SHA256.match(str(row.get("scored_sha256", "")))):
        expected_id = measurement_identity(
            run_id=row["run_id"], arm=extra["arm"], variant=extra["variant"],
            chapters=extra["chapters"], metric=row["metric"],
            scored_sha256=row["scored_sha256"])
    if expected_id is not None and row.get("measurement_id") != expected_id:
        p.append("measurement_id does not re-derive from (run_id, arm, variant, chapters, "
                 "metric, scored_sha256)")
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


def _claim_text(*, metric: str, run_id: str, arm: str, variant: str, chapters: int,
                value: float, reps: int, extra: Mapping[str, Any]) -> str:
    if metric == SIMPLE_RECALL_METRIC:
        tail = (f"over {reps} get=='all' questions, bins keyed on "
                f"{extra['simple_recall_bin_basis']}, bin 0 included")
        label = "Simple Recall Score"
    else:
        tail = (f"over {extra['latest_questions']} latest + "
                f"{extra['chronological_questions']} chronological questions, "
                f"{extra['chronological_partial_coverage']} tau questions failed closed for "
                "partial coverage")
        label = "Chronological Awareness Score"
    return (f"Tulving episodic {variant} {chapters}ch run {run_id} arm '{arm}': "
            f"{label} {value:.4f} ({tail})")


def write_belief_measurements(
    scored_path: str | Path, *,
    summary: Mapping[str, Any],
    run_id: str,
    producer: str,
    arm: str,
    variant: str,
    chapters: int,
    category: str = "CANDIDATE",
    sidecar_path: str | Path | None = None,
    emitted_at: str | None = None,
) -> Path:
    """Emit ``belief_measurements.jsonl`` beside the scored artifact — the SC67 hook.

    ``summary`` is the ``summary`` block of the scorer's own output, read verbatim: this
    writer never recomputes a metric, so the sidecar cannot disagree with the artifact it
    attests. ``scored_path`` is the scored JSON the scorer just wrote; it is hashed and
    becomes the attestation. Any problem raises :class:`CaptureError` and nothing is
    written.
    """
    scored = Path(scored_path)
    if not scored.is_file():
        raise CaptureError(f"scored artifact missing: {scored} — call this at score-time")
    if not isinstance(summary, Mapping) or not summary:
        raise CaptureError("summary must be the scorer's non-empty summary block")
    if arm not in ARMS:
        raise CaptureError(f"arm must be one of {sorted(ARMS)}; the harness never records it "
                           "implicitly and this writer will not guess it")
    scorer_version = summary.get("scorer_version")
    if not _nonneg_int(scorer_version) or scorer_version < MIN_SCORER_VERSION:
        raise CaptureError(
            f"summary.scorer_version must be >= {MIN_SCORER_VERSION} (post-M-12e); got "
            f"{scorer_version!r}. A pre-M-12e score is a different quantity under the same "
            "name and must never be projected as this metric.")

    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scored_sha256 = _file_sha256(scored)
    missing = summary.get("missing_ground_truth", 0)
    if not _nonneg_int(missing):
        raise CaptureError("summary.missing_ground_truth must be a non-negative integer")
    basis = ("scored:questions" if missing == 0 else
             f"attempted:questions ({missing} dropped for missing ground truth)")

    common: dict[str, Any] = {
        "arm": arm,
        "variant": variant,
        "chapters": int(chapters),
        "scorer_version": int(scorer_version),
        "model_role": str(summary.get("model_role") or ""),
        "config_name": str(summary.get("config_name") or ""),
        "result_questions": summary.get("result_questions", 0),
        "scored_questions": summary.get("scored_questions", 0),
        "missing_ground_truth": missing,
        "avg_f1": summary.get("avg_f1"),
    }

    specs: list[tuple[str, Any, int, dict[str, Any]]] = [
        (
            SIMPLE_RECALL_METRIC,
            summary.get("simple_recall_score"),
            summary.get("simple_recall_questions", -1),
            {
                "simple_recall_questions": summary.get("simple_recall_questions", -1),
                "simple_recall_bin_basis": summary.get("simple_recall_bin_basis", ""),
                "simple_recall_bins": summary.get("simple_recall_bins"),
            },
        ),
        (
            CHRONOLOGICAL_METRIC,
            summary.get("chronological_awareness_score"),
            (summary.get("latest_questions", 0) or 0)
            + (summary.get("chronological_questions", 0) or 0),
            {
                "latest_questions": summary.get("latest_questions", -1),
                "chronological_questions": summary.get("chronological_questions", -1),
                "chronological_partial_coverage":
                    summary.get("chronological_partial_coverage", -1),
            },
        ),
    ]

    rows: list[dict[str, Any]] = []
    for metric, value, reps, specific in specs:
        extra = {**common, **specific}
        row: dict[str, Any] = {
            "schema": CAPTURE_SCHEMA,
            "run_id": run_id,
            "producer": producer,
            "emitted_at": when,
            "date": when[:10],
            "measurement_id": measurement_identity(
                run_id=run_id, arm=arm, variant=variant, chapters=int(chapters),
                metric=metric, scored_sha256=scored_sha256),
            "metric": metric,
            "value": value,
            "unit": UNIT,
            "metric_direction": "higher_better",
            "category": category,
            "claim": "",
            "protocol_id": CAPTURE_SCHEMA,
            "reps": reps,
            "reps_basis": basis,
            "scored_path": str(scored),
            "scored_sha256": scored_sha256,
            "extra": extra,
        }
        if _finite(value) and _nonneg_int(reps) and reps > 0:
            row["claim"] = _claim_text(
                metric=metric, run_id=run_id, arm=arm, variant=variant,
                chapters=int(chapters), value=float(value), reps=reps, extra=extra)
        row["row_sha256"] = row_digest(row)
        problems = validate_row(row)
        if problems:
            raise CaptureError(
                f"{metric}: refusing to emit an invalid row: " + "; ".join(problems))
        rows.append(row)

    sidecar = Path(sidecar_path) if sidecar_path else scored.parent / SIDECAR_NAME
    tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
    with open(tmp, "w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, sidecar)
    return sidecar


__all__ = [
    "CAPTURE_SCHEMA", "SIDECAR_NAME", "SIMPLE_RECALL_METRIC", "CHRONOLOGICAL_METRIC",
    "METRICS", "UNIT", "ARMS", "MIN_SCORER_VERSION", "CaptureError", "content_hash",
    "row_digest", "measurement_identity", "validate_row", "write_belief_measurements",
]
