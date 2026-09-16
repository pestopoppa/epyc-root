"""SC68 write-side hook: producer-authored belief rows for BEAM conversational-memory runs.

``epyc-inference-research/scripts/benchmark/score_beam_run.py`` calls
:func:`write_belief_measurements` at score-time (``--belief-measurements --arm …``) to emit a
``belief_measurements.jsonl`` sidecar next to the folded artifact — ONE claim-tuple-shaped row
per run arm. Wired at adapter-authoring time (CME-1), before any BEAM run exists.

The row vocabulary is the established producer contract (``tulving_episodic_capture.py``,
``chat_template_ab_capture.py``): ``measurement_id / metric / value / unit / metric_direction /
category / claim / protocol_id / reps / reps_basis / extra`` plus a self-hash. The strict read side
is ``beam_memory.py``, which imports this vocabulary so writer and reader cannot drift.

What the hook exists to pin (``intake-1337#record``):

* **The BEAM-fold headline is the claim; the other fold rides as recorded context.** The value is
  the unweighted mean of the ten ability columns (per question = mean of 0/0.5/1 nugget verdicts,
  ``tau_norm`` for event ordering when present). The rubric-item micro-average and the binarised
  (``>= 0.5``) pass count ride in ``extra`` of the SAME tuple, never as claims. A tuple that does
  not say which fold produced its number cannot be compared to any external BEAM figure — the
  MemPalace #125 run reads 49.0 on the binarised micro fold and 55.7 on BEAM's.
* **The fold is re-derived, not trusted.** ``value`` must equal the mean of the recorded
  per-ability scores, so a micro-average or a binarised rate cannot be written under this metric.
* **Ten columns or no claim.** A headline over fewer ability columns is a different quantity
  under the same name, and is refused.
* **The judge is identity.** Four judges have put BEAM on four axes, so the judge model, the judge
  prompt version and whether the judge saw the probing question are mandatory and part of the id.
* **Nothing is guessed.** ``arm`` must be one of the three M-12b arms (M-12 B2): ``full`` (BEAM's
  Vanilla column, memory-off), ``rag`` (``pair_chunk`` x BM25, the naive-memory control) or
  ``trace`` (the same chunks through the orchestrator trace store, the arm under test). The
  scorer's summary must record that every judged row was produced under exactly that arm
  (``context_mode_by_row``, from the harness's per-row provenance); pre-hook runs and runs
  whose rows never recorded their arm emit zero rows.
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

CAPTURE_SCHEMA = "epyc.vidya.beam_memory_capture.v1"
SIDECAR_NAME = "belief_measurements.jsonl"

METRIC = "beam_fold_headline"
METRICS = (METRIC,)
UNIT = "score"
FOLD_NAME = "beam_macro"
BINARISATION_THRESHOLD = 0.5

#: The ten BEAM ability columns (``probing_questions`` keys). Mirrors
#: ``epyc-inference-research:scripts/benchmark/beam_scoring.BEAM_ABILITIES``.
BEAM_ABILITIES = (
    "abstention", "contradiction_resolution", "event_ordering", "information_extraction",
    "instruction_following", "knowledge_update", "multi_session_reasoning",
    "preference_following", "summarization", "temporal_reasoning",
)
SPLITS = frozenset({"100K", "500K", "1M", "10M"})
ARMS = frozenset({"full", "rag", "trace"})


def _single_arm(by_row: Any) -> str | None:
    """The one arm a ``context_mode_by_row`` count map names, else None."""
    if not isinstance(by_row, Mapping):
        return None
    present = [k for k, v in by_row.items() if _nonneg_int(v) and v > 0]
    return present[0] if len(present) == 1 else None

#: beam_scoring.FOLD_VERSION 1 is the first fold with a tested contract (CME-2).
MIN_SCORER_VERSION = 1

#: CME-3: carried wherever a BEAM number is quoted.
HARNESS_NOTE = (
    "BEAM's released harness never passes the probing question to the judge (all ten evaluate_* "
    "functions discard it), and every abstention rubric is a single-nugget refusal template, so "
    "a blanket refusal scores 1.0 on that column. extra.question_in_judge_prompt records whether "
    "THIS run's judge saw the question.")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})
_DIRECTIONS = frozenset({"higher_better", "lower_better"})
_FOLD_TOLERANCE = 1e-9


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
    return content_hash({k: v for k, v in row.items() if k != "row_sha256"})


def measurement_identity(*, run_id: str, arm: str, split: str, judge_model: str,
                         metric: str, scored_sha256: str) -> str:
    digest = content_hash({
        "run_id": run_id, "arm": arm, "split": split, "judge_model": judge_model,
        "metric": metric, "scored_sha256": scored_sha256,
    })
    return f"beam_{digest[:24]}"


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _pos_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _unit_interval(value: Any) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and 0.0 <= value <= 1.0)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_row(row: Any) -> list[str]:
    """Every structural problem in one producer-authored row. Empty list == valid.

    Shared by the writer (refuse to emit) and the reader (refuse to project).
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
        p.append(f"metric must be {METRIC!r} — the BEAM-fold headline is the only claim")
    if row.get("metric_direction") not in _DIRECTIONS:
        p.append("metric_direction must be recorded as higher_better or lower_better")
    if row.get("category") not in _CATEGORIES:
        p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
    if not _SHA256.match(str(row.get("scored_sha256", ""))):
        p.append("scored_sha256 must be a 64-hex digest over the scored artifact")
    if not _unit_interval(row.get("value")):
        p.append("value must be a finite score in [0, 1]")

    extra = row.get("extra")
    if not isinstance(extra, dict):
        return p + ["extra must be an object carrying the run identity"]

    if extra.get("arm") not in ARMS:
        p.append(f"extra.arm must be one of {sorted(ARMS)} — never inferred on read")
    elif _single_arm(extra.get("context_mode_by_row")) != extra.get("arm"):
        p.append("extra.context_mode_by_row must show every judged row produced under "
                 "extra.arm (the harness-recorded arm, M-12 B2)")
    if extra.get("split") not in SPLITS:
        p.append(f"extra.split must be one of {sorted(SPLITS)}")
    if not _nonneg_int(extra.get("scorer_version")):
        p.append("extra.scorer_version must be recorded")
    elif extra["scorer_version"] < MIN_SCORER_VERSION:
        p.append(f"extra.scorer_version must be >= {MIN_SCORER_VERSION} (the tested CME-2 fold)")
    if extra.get("fold") != FOLD_NAME:
        p.append(f"extra.fold must be {FOLD_NAME!r} — the tuple must say WHICH fold produced "
                 "its number")
    for key in ("model_role", "judge_model", "judge_prompt_version", "event_ordering_basis",
                "harness_note"):
        if not _text(extra.get(key)):
            p.append(f"extra.{key} must be recorded")
    for key in ("question_in_judge_prompt", "checked_against_dataset"):
        if not isinstance(extra.get(key), bool):
            p.append(f"extra.{key} must be a boolean")

    if extra.get("abilities_reported") != sorted(BEAM_ABILITIES):
        p.append("extra.abilities_reported must be all ten BEAM ability columns — a headline "
                 "over fewer columns is a different quantity under the same name")
    per_ability = extra.get("per_ability")
    ability_scores: list[float] = []
    if not isinstance(per_ability, dict) or sorted(per_ability) != sorted(BEAM_ABILITIES):
        p.append("extra.per_ability must carry exactly the ten ability columns")
    else:
        for ability, cell in sorted(per_ability.items()):
            if (not isinstance(cell, dict) or not _pos_int(cell.get("questions"))
                    or not _unit_interval(cell.get("score"))):
                p.append(f"extra.per_ability.{ability} must carry questions > 0 and a score "
                         "in [0, 1]")
            else:
                ability_scores.append(float(cell["score"]))
    if (len(ability_scores) == len(BEAM_ABILITIES) and _unit_interval(row.get("value"))
            and abs(sum(ability_scores) / len(ability_scores) - row["value"]) > _FOLD_TOLERANCE):
        p.append("value does not re-derive as the unweighted mean of extra.per_ability — only "
                 "the BEAM fold may be written under this metric (a micro-average or binarised "
                 "rate is recorded context, never the claim)")

    n_questions = extra.get("n_questions")
    if not _pos_int(n_questions):
        p.append("extra.n_questions must be a positive integer")
    elif isinstance(per_ability, dict) and len(ability_scores) == len(BEAM_ABILITIES) and \
            sum(per_ability[a]["questions"] for a in BEAM_ABILITIES) != n_questions:
        p.append("extra.n_questions must equal the per-ability question counts summed")
    if not _pos_int(extra.get("n_nuggets")):
        p.append("extra.n_nuggets must be a positive integer")

    # The second fold, recorded as context in the same tuple.
    if not _unit_interval(extra.get("rubric_item_micro_average")):
        p.append("extra.rubric_item_micro_average must be recorded in [0, 1]")
    if extra.get("binarised_threshold") != BINARISATION_THRESHOLD:
        p.append(f"extra.binarised_threshold must be {BINARISATION_THRESHOLD}")
    passed, total = extra.get("binarised_pass_count"), extra.get("binarised_total_checks")
    if not _nonneg_int(passed) or not _pos_int(total):
        p.append("extra.binarised_pass_count / binarised_total_checks must be recorded")
    else:
        if passed > total:
            p.append("extra.binarised_pass_count cannot exceed binarised_total_checks")
        if _pos_int(extra.get("n_nuggets")) and total != extra["n_nuggets"]:
            p.append("extra.binarised_total_checks must equal extra.n_nuggets")

    if row.get("reps") != n_questions or not _pos_int(row.get("reps")):
        p.append("reps must equal extra.n_questions — the questions that were judged and folded")
    if row.get("reps_basis") != "scored:questions":
        p.append("reps_basis must be 'scored:questions'")

    expected_id = None
    if (_text(row.get("run_id")) and extra.get("arm") in ARMS and extra.get("split") in SPLITS
            and _text(extra.get("judge_model")) and row.get("metric") in METRICS
            and _SHA256.match(str(row.get("scored_sha256", "")))):
        expected_id = measurement_identity(
            run_id=row["run_id"], arm=extra["arm"], split=extra["split"],
            judge_model=extra["judge_model"], metric=row["metric"],
            scored_sha256=row["scored_sha256"])
    if expected_id is not None and row.get("measurement_id") != expected_id:
        p.append("measurement_id does not re-derive from (run_id, arm, split, judge_model, "
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


def _claim_text(*, run_id: str, arm: str, extra: Mapping[str, Any], value: float,
                reps: int) -> str:
    return (f"BEAM {extra['split']} run {run_id} arm '{arm}': BEAM-fold headline {value:.4f} "
            f"(unweighted mean of 10 ability columns over {reps} questions, judge "
            f"{extra['judge_model']}, event ordering on {extra['event_ordering_basis']}); "
            f"recorded context, NOT the claim: rubric-item micro-average "
            f"{extra['rubric_item_micro_average']:.4f}, binarised pass "
            f"{extra['binarised_pass_count']}/{extra['binarised_total_checks']} at >= "
            f"{BINARISATION_THRESHOLD}")


def write_belief_measurements(
    scored_path: str | Path, *,
    summary: Mapping[str, Any],
    run_id: str,
    producer: str,
    arm: str,
    category: str = "CANDIDATE",
    sidecar_path: str | Path | None = None,
    emitted_at: str | None = None,
) -> Path:
    """Emit ``belief_measurements.jsonl`` beside the folded artifact — the SC68 hook.

    ``summary`` is ``score_beam_run.score_judged_payload(...)["summary"]``, read verbatim: this
    writer never recomputes the fold (the validator only re-derives it to refuse a mismatch).
    Any problem raises :class:`CaptureError` and nothing is written.
    """
    scored = Path(scored_path)
    if not scored.is_file():
        raise CaptureError(f"scored artifact missing: {scored} — call this at score-time")
    if not isinstance(summary, Mapping) or not summary:
        raise CaptureError("summary must be the scorer's non-empty summary block")
    if arm not in ARMS:
        raise CaptureError(f"arm must be one of {sorted(ARMS)}; the judged artifact does not "
                           "record it and this writer will not guess it")
    scorer_version = summary.get("scorer_version")
    if not _nonneg_int(scorer_version) or scorer_version < MIN_SCORER_VERSION:
        raise CaptureError(f"summary.scorer_version must be >= {MIN_SCORER_VERSION}; got "
                           f"{scorer_version!r}")
    by_row = summary.get("context_mode_by_row")
    if _single_arm(by_row) != arm:
        raise CaptureError(
            f"arm={arm!r} is not what the result rows record ({by_row!r}); the harness writes "
            "each row's arm, and a claim may only restate it")
    diag = summary.get("secondary_diagnostics")
    if not isinstance(diag, Mapping):
        raise CaptureError("summary.secondary_diagnostics is missing — BOTH folds must be "
                           "recorded, the second as context")

    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scored_sha256 = _file_sha256(scored)
    split = str(summary.get("split") or "")
    judge_model = str(summary.get("judge_model") or "")
    extra: dict[str, Any] = {
        "arm": arm,
        "context_mode_by_row": {str(k): v for k, v in by_row.items()},
        "split": split,
        "scorer_version": scorer_version,
        "fold": summary.get("fold"),
        "model_role": str(summary.get("model_role") or ""),
        "judge_model": judge_model,
        "judge_prompt_version": str(summary.get("judge_prompt_version") or ""),
        "question_in_judge_prompt": summary.get("question_in_judge_prompt"),
        "checked_against_dataset": summary.get("checked_against_dataset"),
        "event_ordering_basis": str(summary.get("event_ordering_basis") or ""),
        "abilities_reported": list(summary.get("abilities_reported") or []),
        "per_ability": summary.get("per_ability"),
        "n_questions": summary.get("n_questions"),
        "n_nuggets": summary.get("n_nuggets"),
        "rubric_item_micro_average": diag.get("rubric_item_micro_average"),
        "binarised_threshold": diag.get("binarised_threshold"),
        "binarised_pass_count": diag.get("binarised_pass_count"),
        "binarised_total_checks": diag.get("binarised_total_checks"),
        "binarised_pass_rate": diag.get("binarised_pass_rate"),
        "harness_note": HARNESS_NOTE,
    }
    value = summary.get("headline")
    reps = summary.get("n_questions")
    row: dict[str, Any] = {
        "schema": CAPTURE_SCHEMA,
        "run_id": run_id,
        "producer": producer,
        "emitted_at": when,
        "date": when[:10],
        "measurement_id": measurement_identity(
            run_id=run_id, arm=arm, split=split, judge_model=judge_model, metric=METRIC,
            scored_sha256=scored_sha256),
        "metric": METRIC,
        "value": value,
        "unit": UNIT,
        "metric_direction": "higher_better",
        "category": category,
        "claim": "",
        "protocol_id": CAPTURE_SCHEMA,
        "reps": reps,
        "reps_basis": "scored:questions",
        "scored_path": str(scored),
        "scored_sha256": scored_sha256,
        "extra": extra,
    }
    if (_unit_interval(value) and _pos_int(reps) and split and judge_model
            and _unit_interval(extra["rubric_item_micro_average"])
            and _nonneg_int(extra["binarised_pass_count"])
            and _pos_int(extra["binarised_total_checks"]) and extra["event_ordering_basis"]):
        row["claim"] = _claim_text(run_id=run_id, arm=arm, extra=extra, value=float(value),
                                   reps=reps)
    row["row_sha256"] = row_digest(row)
    problems = validate_row(row)
    if problems:
        raise CaptureError("refusing to emit an invalid BEAM row: " + "; ".join(problems))

    sidecar = Path(sidecar_path) if sidecar_path else scored.parent / SIDECAR_NAME
    tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
    with open(tmp, "w") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, sidecar)
    return sidecar


__all__ = [
    "CAPTURE_SCHEMA", "SIDECAR_NAME", "METRIC", "METRICS", "UNIT", "FOLD_NAME",
    "BINARISATION_THRESHOLD", "BEAM_ABILITIES", "SPLITS", "ARMS", "MIN_SCORER_VERSION",
    "HARNESS_NOTE", "CaptureError", "content_hash", "row_digest", "measurement_identity",
    "validate_row", "write_belief_measurements",
]
