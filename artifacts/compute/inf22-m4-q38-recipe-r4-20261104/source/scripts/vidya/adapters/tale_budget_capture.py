"""VB-PRB-T4 write-side hook: producer-authored belief rows for TALE-EP budget evaluations.

The PRB-T4 driver calls :func:`write_belief_measurements` at write time (right after
``eval_tale_budget.py`` saved a suite's per-question ``.jsonl`` and its ``.meta.json``), which
emits ``<results>.beliefs.jsonl`` next to them: one claim-tuple-shaped row per
(run, suite, condition, metric).

Metrics per suite x condition (``baseline`` / ``static`` / ``tale``):

* ``tale_suite_accuracy``            fraction_correct   higher_better  reps = scored questions
* ``tale_mean_answer_tokens``        tokens             lower_better   reps = attempted questions
* ``tale_mean_tokens_incl_estimator`` tokens            lower_better   (== answer-only for non-TALE)
* ``tale_mean_latency_s_answer_only``    seconds         lower_better
* ``tale_mean_latency_s_incl_estimator`` seconds        lower_better

Answer-only AND incl-estimator figures are both emitted for tokens and latency, as VB-PRB-T4 requires
(the estimator call is TALE's own cost; answer-only rows stay comparable with pre-PRB-T4 runs). The
formulas are those of ``eval_tale_budget.summarize()`` over the same per-question rows.

The row vocabulary is the established producer contract (``chat_template_ab_capture.py``). The
identity that the handoff requires on every tuple -- budget_unit, temperature + seed, served GGUF
(``meta.serving``) and chat_template_kwargs -- rides in ``extra`` and is REQUIRED: the writer
refuses to emit rather than fill in what the run did not record.

Pre-hook runs stay pre-hook: this is never invoked over a finished run to backfill it.
The strict read side is ``tale_budget.py``; it imports ``validate_row`` from here so writer and
reader share one definition of well-formed.
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

CAPTURE_SCHEMA = "epyc.vidya.tale_budget_capture.v1"
SIDECAR_SUFFIX = ".beliefs.jsonl"
CONDITIONS = ("baseline", "static", "tale")
BUDGET_UNITS = frozenset({"tokens", "words"})
SERVING_MODES = frozenset({"test_port", "live_production"})

#: metric -> (unit, direction)
METRICS: dict[str, tuple[str, str]] = {
    "tale_suite_accuracy": ("fraction_correct", "higher_better"),
    "tale_mean_answer_tokens": ("tokens", "lower_better"),
    "tale_mean_tokens_incl_estimator": ("tokens", "lower_better"),
    "tale_mean_latency_s_answer_only": ("seconds", "lower_better"),
    "tale_mean_latency_s_incl_estimator": ("seconds", "lower_better"),
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
#: The capture schema is a record format, not a measurement protocol (MEASUREMENT.md:13). Until a
#: TALE protocol is codified under ``measurement/protocols/`` every row is an observation, exactly
#: like OCC-1 (SC85). Rows from the pre-port /workspace copy carry CAPTURE_SCHEMA here; the reader
#: accepts them and projects the same empty citation.
NO_PROTOCOL = ""


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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def row_digest(row: Mapping[str, Any]) -> str:
    return content_hash({k: v for k, v in row.items() if k != "row_sha256"})


def measurement_identity(*, run_id: str, suite: str, condition: str, metric: str,
                         results_sha256: str) -> str:
    digest = content_hash({"run_id": run_id, "suite": suite, "condition": condition,
                           "metric": metric, "results_sha256": results_sha256})
    return f"tale_{digest[:24]}"


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _pos_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _utc(value: Any) -> bool:
    if not _text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def validate_row(row: Any) -> list[str]:
    """Every structural problem in one producer-authored row. Empty list == valid."""
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for key in ("run_id", "producer", "measurement_id", "metric", "unit", "claim",
                "reps_basis", "results_path", "meta_path", "date"):
        if not _text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if row.get("protocol_id") not in ("", CAPTURE_SCHEMA):
        p.append("protocol_id must be empty (no TALE protocol is codified under "
                 "measurement/protocols/); the capture schema is accepted only as the pre-port value")
    if not _utc(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    for key in ("results_sha256", "meta_sha256"):
        if not _SHA256.match(str(row.get(key, ""))):
            p.append(f"{key} must be a 64-hex digest")
    metric = row.get("metric")
    if metric not in METRICS:
        p.append(f"metric must be one of {sorted(METRICS)}")
    else:
        unit, direction = METRICS[metric]
        if row.get("unit") != unit:
            p.append(f"unit for {metric} must be {unit!r}")
        if row.get("metric_direction") != direction:
            p.append(f"metric_direction for {metric} must be {direction!r}")
    if not _finite(row.get("value")) or row["value"] < 0:
        p.append("value must be a finite non-negative number")
    if not _pos_int(row.get("reps")):
        p.append("reps must be a positive integer")
    extra = row.get("extra")
    if not isinstance(extra, dict):
        return p + ["extra must be an object carrying the run identity"]
    condition = extra.get("condition")
    if condition not in CONDITIONS:
        p.append(f"extra.condition must be one of {CONDITIONS}")
    elif row.get("category") != ("BASELINE" if condition == "baseline" else "CANDIDATE"):
        p.append("category must be BASELINE for the baseline arm and CANDIDATE otherwise")
    if not _text(extra.get("suite")):
        p.append("extra.suite must be a non-empty string")
    if extra.get("budget_unit") not in BUDGET_UNITS:
        p.append("extra.budget_unit must be recorded (tokens|words)")
    sampling = extra.get("sampling")
    if not isinstance(sampling, dict) or not _finite(sampling.get("temperature")) \
            or not _nonneg_int(sampling.get("seed")):
        p.append("extra.sampling must record temperature and a non-negative seed")
    if not isinstance(extra.get("chat_template_kwargs"), dict):
        p.append("extra.chat_template_kwargs must be recorded (an object, possibly empty)")
    served = extra.get("served")
    if not isinstance(served, dict) or not _text(served.get("gguf_path")) \
            or not _text(served.get("model_id")):
        p.append("extra.served must name the served model_id and gguf_path (from meta.serving)")
    serving = extra.get("serving")
    if not isinstance(serving, dict) or serving.get("mode") not in SERVING_MODES \
            or not _text(serving.get("endpoint")):
        p.append(f"extra.serving must carry endpoint and mode in {sorted(SERVING_MODES)}")
    kernel = extra.get("kernel")
    if not isinstance(kernel, dict) or not _SHA256.match(str(kernel.get("binary_sha256", ""))) \
            or not _text(kernel.get("binary_path")):
        p.append("extra.kernel must carry the served binary_path and its binary_sha256")
    n, n_scored = extra.get("n"), extra.get("n_scored")
    if not _pos_int(n) or not _nonneg_int(n_scored) or n_scored > n:
        p.append("extra.n must be positive and extra.n_scored within [0, n]")
    elif metric == "tale_suite_accuracy":
        correct = extra.get("correct")
        if not _nonneg_int(correct) or n_scored == 0 or correct > n_scored:
            p.append("accuracy rows need extra.correct within [0, n_scored] and n_scored > 0")
        else:
            if not _finite(row.get("value")) or not math.isclose(row["value"], correct / n_scored,
                                                                 rel_tol=1e-12, abs_tol=1e-15):
                p.append("value must equal extra.correct / extra.n_scored")
            if row.get("reps") != n_scored:
                p.append("accuracy reps must equal extra.n_scored")
            want = ("scored:questions" if n_scored == n else
                    f"scored:questions ({n - n_scored} unscorable excluded)")
            if row.get("reps_basis") != want:
                p.append(f"accuracy reps_basis must be {want!r}")
    elif metric in METRICS:
        if row.get("reps") != n:
            p.append("cost rows' reps must equal extra.n (every attempted question costs)")
        if row.get("reps_basis") != "attempted:questions":
            p.append("cost rows' reps_basis must be 'attempted:questions'")
    if all(_text(row.get(k)) for k in ("run_id", "metric")) and _text(extra.get("suite")) \
            and condition in CONDITIONS and _SHA256.match(str(row.get("results_sha256", ""))):
        expected = measurement_identity(run_id=row["run_id"], suite=extra["suite"],
                                        condition=condition, metric=row["metric"],
                                        results_sha256=row["results_sha256"])
        if row.get("measurement_id") != expected:
            p.append("measurement_id does not re-derive from (run_id, suite, condition, metric, "
                     "results_sha256)")
    if not _SHA256.match(str(row.get("row_sha256", ""))):
        p.append("row_sha256 must be a 64-hex self-hash")
    else:
        try:
            if row_digest(row) != row["row_sha256"]:
                p.append("row_sha256 does not bind the row content")
        except CaptureError as exc:
            p.append(f"row is not canonically hashable: {exc}")
    return p


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sidecar_path(results_path: str | Path) -> Path:
    path = Path(results_path)
    return path.with_name(path.stem + SIDECAR_SUFFIX)


def _cells(results_path: Path) -> dict[tuple[str, str], list[dict]]:
    cells: dict[tuple[str, str], list[dict]] = {}
    for line in results_path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if "question_id" not in row:
            continue
        if row.get("condition") not in CONDITIONS or not _text(row.get("suite")):
            raise CaptureError(f"results row without a known condition/suite: {row.get('question_id')}")
        cells.setdefault((row["suite"], row["condition"]), []).append(row)
    if not cells:
        raise CaptureError(f"no per-question rows in {results_path}")
    return cells


def write_belief_measurements(
    results_path: str | Path, *,
    run_id: str,
    producer: str,
    kernel: Mapping[str, Any],
    serving_mode: str = "test_port",
    meta_path: str | Path | None = None,
    emitted_at: str | None = None,
) -> Path:
    """Emit ``<results>.beliefs.jsonl``. ``kernel`` is the served binary's RECORDED identity
    (``binary_path`` + ``binary_sha256``, hashed by the caller at launch). Sampling, budget unit,
    chat_template_kwargs and the served model come from the harness's own ``.meta.json`` and are
    refused if absent. Any invalid row raises :class:`CaptureError` and nothing is written."""
    results = Path(results_path)
    meta_file = Path(meta_path) if meta_path else results.with_suffix(".meta.json")
    if not results.is_file() or not meta_file.is_file():
        raise CaptureError(f"results or meta missing: {results}, {meta_file}")
    meta = json.loads(meta_file.read_text())
    serving = meta.get("serving") if isinstance(meta, dict) else None
    if not isinstance(serving, dict):
        raise CaptureError("meta.serving is missing: the served model identity was not recorded")
    endpoint = serving.get("base_url") or serving.get("endpoint") or ""
    gguf = serving.get("gguf") if isinstance(serving.get("gguf"), dict) else {}
    served = {"model_id": serving.get("model_id"), "model_id_source": serving.get("model_id_source"),
              "gguf_path": serving.get("gguf_path"),
              "gguf_path_source": serving.get("gguf_path_source"),
              "gguf_size_bytes": gguf.get("size_bytes"), "gguf_sha256": gguf.get("sha256"),
              "props_model_path": (serving.get("props") or {}).get("model_path"),
              "props_build_info": (serving.get("props") or {}).get("build_info")}
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results_sha, meta_sha = file_sha256(results), file_sha256(meta_file)
    ctk = meta.get("chat_template_kwargs")
    rows: list[dict[str, Any]] = []
    for (suite, condition), qs in sorted(_cells(results).items()):
        scored = [q for q in qs if q.get("correct") is not None]
        n, n_scored = len(qs), len(scored)
        correct = sum(1 for q in scored if q["correct"])
        values = {
            "tale_suite_accuracy": (correct / n_scored) if n_scored else None,
            "tale_mean_answer_tokens": sum(q["total_tokens"] for q in qs) / n,
            "tale_mean_tokens_incl_estimator": sum(
                q.get("total_tokens_incl_estimator") or q["total_tokens"] for q in qs) / n,
            "tale_mean_latency_s_answer_only": sum(q["elapsed_s"] for q in qs) / n,
            "tale_mean_latency_s_incl_estimator": sum(
                q.get("elapsed_s_incl_estimator") or q["elapsed_s"] for q in qs) / n,
        }
        budgets = sorted(q["tale_budget"] for q in qs if q.get("tale_budget") is not None)
        for metric, value in values.items():
            if value is None:
                continue  # an arm with nothing scorable has no accuracy; absence is recorded by omission
            unit, direction = METRICS[metric]
            is_acc = metric == "tale_suite_accuracy"
            extra = {
                "suite": suite, "condition": condition, "n": n, "n_scored": n_scored,
                "budget_unit": meta.get("budget_unit"),
                "sampling": {"temperature": meta.get("temperature"), "seed": meta.get("seed"),
                             "max_tokens": meta.get("max_tokens"),
                             "estimator_max_tokens": meta.get("estimator_max_tokens")},
                "chat_template_kwargs": ctk if isinstance(ctk, dict) else ({} if ctk is None else ctk),
                "served": served,
                "served_models_seen": meta.get("served_models_seen"),
                "serving": {"mode": serving_mode, "endpoint": endpoint},
                "kernel": dict(kernel),
                "harness_started_at": meta.get("started_at"),
                "harness_finished_at": meta.get("finished_at"),
            }
            if is_acc:
                extra["correct"] = correct
            if condition == "tale":
                extra["mean_estimator_tokens"] = sum(q.get("estimator_tokens") or 0 for q in qs) / n
                if budgets:
                    extra["budget_min_median_max"] = [budgets[0], budgets[len(budgets) // 2], budgets[-1]]
            row: dict[str, Any] = {
                "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
                "emitted_at": when, "date": when[:10],
                "measurement_id": measurement_identity(run_id=run_id, suite=suite, condition=condition,
                                                       metric=metric, results_sha256=results_sha),
                "metric": metric, "value": value, "unit": unit, "metric_direction": direction,
                "category": "BASELINE" if condition == "baseline" else "CANDIDATE",
                "claim": (f"TALE-EP {run_id}: {condition} arm on {suite} -> {metric} = "
                          f"{value:.4f} {unit} (n={n_scored if is_acc else n})"),
                # No TALE protocol is codified under measurement/protocols/: an OBSERVATION.
                "protocol_id": NO_PROTOCOL,
                "reps": n_scored if is_acc else n,
                "reps_basis": (("scored:questions" if n_scored == n else
                                f"scored:questions ({n - n_scored} unscorable excluded)")
                               if is_acc else "attempted:questions"),
                "results_path": str(results), "results_sha256": results_sha,
                "meta_path": str(meta_file), "meta_sha256": meta_sha,
                "extra": extra,
            }
            row["row_sha256"] = row_digest(row)
            problems = validate_row(row)
            if problems:
                raise CaptureError(f"{suite}/{condition}/{metric}: refusing an invalid row: "
                                   + "; ".join(problems))
            rows.append(row)
    out = sidecar_path(results)
    tmp = out.with_suffix(".tmp")
    with open(tmp, "w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, out)
    return out


__all__ = ["CAPTURE_SCHEMA", "NO_PROTOCOL", "SIDECAR_SUFFIX", "METRICS", "CONDITIONS", "CaptureError",
           "content_hash", "row_digest", "measurement_identity", "validate_row", "file_sha256",
           "sidecar_path", "write_belief_measurements"]
