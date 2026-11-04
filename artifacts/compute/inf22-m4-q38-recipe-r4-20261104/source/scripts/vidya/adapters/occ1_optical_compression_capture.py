"""SC85 write-side hook: producer-authored belief rows for OCC-1 optical-compression runs.

``epyc-inference-research/scripts/benchmark/occ1/run_occ1.py report`` calls
:func:`write_belief_measurements` right after it writes ``summary.json``. The call emits a
``belief_measurements.jsonl`` sidecar in the same run directory. OCC-1 compares bitmap frames
against raw text on a served vision reader (``optical-context-compression.md``).

Rows per arm:

* ``occ1_squad_f1`` and ``occ1_squad_em`` for every arm. The text arm is the BASELINE, and every
  image arm is a CANDIDATE.
* ``occ1_squad_f1_delta_vs_text`` for each image arm. This is the paired F1 delta against the text
  arm, and it carries the chunk-clustered 95% CI, the exact McNemar p on EM and the pre-registered
  verdict.
* ``occ1_prompt_token_ratio_vs_text`` for each image arm. This is the billed-token cost ratio, and
  lower is better.

The row vocabulary is the established producer contract (``chat_template_ab_capture.py`` and
``tulving_episodic_capture.py``). The domain identity rides in ``extra``: arm, suite fingerprint,
serving identity, the pre-registration digest and the run's overall verdict. The strict read side
is ``occ1_optical_compression.py``. It imports this vocabulary, so the writer and the reader cannot
drift into two dialects of one schema.

The hook refuses five things:

* **The locator is the RUN, never a question.** One OCC-1 run is one harness execution over one
  fixed suite, so its 1,165 questions per arm are samples, not independent witnesses. Every row of
  a run shares the run locator (run id, suite fingerprint, records file). Arm and metric are what
  separate the claims.
* **A VOID run emits nothing.** A run that ``report`` marked VOID is an instrument failure, not a
  measurement. Examples: text-arm F1 below 0.60, an unrepaired transport error, a prompt-cache hit,
  an incomplete suite, or a server identity problem. The writer refuses such a run and writes no
  file.
* **Nothing is guessed.** The serving identity is the ``/props`` stamp that ``run`` recorded
  (``server_identity.json``). The suite fingerprint is the one ``plan`` sealed. Every value is copied
  verbatim from ``summary.json``; nothing is recomputed. If any of these is absent, the writer
  refuses.
* **No protocol is claimed that does not exist.** There is no codified OCC protocol under
  ``measurement/protocols/``, so ``protocol_id`` defaults to empty. ``claim_tuple.grade()`` then caps
  every tuple at ``Judged`` (an OBSERVATION). The harness pre-registration is bound by digest in
  ``extra.prereg_sha256``, but a harness-local pre-registration is not a ratified protocol.
* **Pre-hook runs stay pre-hook.** This writer is called at report time and never over a finished
  run directory to backfill one (the DF2-4 precedent).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAPTURE_SCHEMA = "epyc.vidya.occ1_optical_compression_capture.v1"
SIDECAR_NAME = "belief_measurements.jsonl"
RECORDS_NAME = "records.jsonl"
BASELINE_ARM = "text"

METRIC_F1 = "occ1_squad_f1"
METRIC_EM = "occ1_squad_em"
METRIC_F1_DELTA = "occ1_squad_f1_delta_vs_text"
METRIC_TOKEN_RATIO = "occ1_prompt_token_ratio_vs_text"

#: metric -> (unit, direction, which arms carry it)
METRICS: dict[str, tuple[str, str, str]] = {
    METRIC_F1: ("squad_f1_mean", "higher_better", "all"),
    METRIC_EM: ("fraction_exact_match", "higher_better", "all"),
    METRIC_F1_DELTA: ("squad_f1_delta", "higher_better", "image"),
    METRIC_TOKEN_RATIO: ("prompt_tokens_ratio", "lower_better", "image"),
}
ARM_VERDICTS = frozenset({"POSITIVE", "NOT_NONINFERIOR", "NEGATIVE_COST"})
OVERALL_VERDICTS = frozenset({"POSITIVE", "NEGATIVE"})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARM = re.compile(r"^(text|img-[0-9a-z]+-(bw|color))$")
_CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})


class CaptureError(ValueError):
    """The runner asked for a sidecar the run cannot honestly support."""


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


def measurement_identity(*, run_id: str, arm: str, metric: str,
                         suite_fingerprint: str, records_sha256: str) -> str:
    digest = content_hash({
        "run_id": run_id, "arm": arm, "metric": metric,
        "suite_fingerprint": suite_fingerprint, "records_sha256": records_sha256,
    })
    return f"occ1_{digest[:24]}"


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _pos_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 1


def _nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _close(a: Any, b: Any) -> bool:
    return _finite(a) and _finite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15)


def validate_row(row: Any) -> list[str]:
    """Every structural problem in one producer-authored row. Empty list == valid.

    The writer uses it to refuse to emit, and the reader uses it to refuse to project, so
    "well-formed" has exactly one definition.
    """
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []

    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for key in ("run_id", "producer", "measurement_id", "claim", "reps_basis",
                "records_path", "date"):
        if not _text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not isinstance(row.get("protocol_id"), str):
        p.append("protocol_id must be a string (empty when no codified protocol exists)")
    if not _utc_timestamp(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    metric = row.get("metric")
    if metric not in METRICS:
        p.append(f"metric must be one of {sorted(METRICS)}")
    else:
        unit, direction, _scope = METRICS[metric]
        if row.get("unit") != unit:
            p.append(f"unit for {metric} must be {unit!r}")
        if row.get("metric_direction") != direction:
            p.append(f"metric_direction for {metric} is recorded as {direction!r}")
    if row.get("category") not in _CATEGORIES:
        p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
    if not _SHA256.match(str(row.get("records_sha256", ""))):
        p.append("records_sha256 must be a 64-hex digest over the per-request records file")
    if not _finite(row.get("value")):
        p.append("value must be a finite number")
    if not _pos_int(row.get("reps")):
        p.append("reps must be a positive integer")

    extra = row.get("extra")
    if not isinstance(extra, dict):
        return p + ["extra must be an object carrying the run identity"]

    arm = extra.get("arm")
    if not isinstance(arm, str) or not _ARM.match(arm):
        p.append("extra.arm must be 'text' or 'img-<font>-<bw|color>'")
        arm = None
    if extra.get("baseline_arm") != BASELINE_ARM:
        p.append("extra.baseline_arm must be 'text' (the paired baseline)")
    if not _SHA256.match(str(extra.get("suite_fingerprint", ""))):
        p.append("extra.suite_fingerprint must be the 64-hex suite digest sealed by `plan`")
    if not _SHA256.match(str(extra.get("prereg_sha256", ""))):
        p.append("extra.prereg_sha256 must bind the pre-registered decision parameters")
    if extra.get("overall_verdict") not in OVERALL_VERDICTS:
        p.append("extra.overall_verdict must be POSITIVE or NEGATIVE (a VOID run emits no rows)")

    serving = extra.get("serving")
    if not isinstance(serving, dict):
        p.append("extra.serving must be the run's recorded /props identity")
    else:
        for key in ("build_info", "model_path"):
            if not _text(serving.get(key)):
                p.append(f"extra.serving.{key} must be recorded, never guessed")
        if not _pos_int(serving.get("n_ctx")):
            p.append("extra.serving.n_ctx must be recorded")

    n = extra.get("n")
    if not _pos_int(n):
        p.append("extra.n must be a positive integer (questions scored)")
    requests = extra.get("requests")
    if not _pos_int(requests):
        p.append("extra.requests must be a positive integer")
    for key in ("unreadable", "missing", "truncated"):
        if not _nonneg_int(extra.get(key)):
            p.append(f"extra.{key} must be a non-negative integer")
    for key in ("f1", "em"):
        if not _finite(extra.get(key)):
            p.append(f"extra.{key} must be recorded")

    if arm is not None:
        is_text = arm == BASELINE_ARM
        if is_text and row.get("category") != "BASELINE":
            p.append("the text arm's rows must carry category BASELINE")
        if not is_text and row.get("category") == "BASELINE":
            p.append("an image arm must not claim category BASELINE")
        if metric in METRICS and METRICS[metric][2] == "image" and is_text:
            p.append(f"{metric} is an image-arm metric; the text arm is its reference")
        if not is_text:
            if not _pos_int(extra.get("n_paired")):
                p.append("extra.n_paired must be a positive integer for an image arm")
            ci = extra.get("f1_delta_ci95")
            if not (isinstance(ci, list) and len(ci) == 2 and all(_finite(x) for x in ci)
                    and ci[0] <= ci[1]):
                p.append("extra.f1_delta_ci95 must be [lo, hi] with lo <= hi")
            elif _finite(extra.get("f1_delta")) and not ci[0] <= extra["f1_delta"] <= ci[1]:
                p.append("extra.f1_delta must lie inside its own CI")
            for key in ("f1_delta", "token_ratio_vs_text", "em_mcnemar_p"):
                if not _finite(extra.get(key)):
                    p.append(f"extra.{key} must be recorded for an image arm")
            if _finite(extra.get("token_ratio_vs_text")) and extra["token_ratio_vs_text"] <= 0:
                p.append("extra.token_ratio_vs_text must be positive")
            if extra.get("verdict") not in ARM_VERDICTS:
                p.append(f"extra.verdict must be one of {sorted(ARM_VERDICTS)}")
        elif any(key in extra for key in ("f1_delta", "f1_delta_ci95", "verdict", "n_paired")):
            p.append("the baseline arm carries no paired statistics")

    # The value is the summary's own figure, copied, and reps is the count that figure is over.
    source = {METRIC_F1: ("f1", "n"), METRIC_EM: ("em", "n"),
              METRIC_F1_DELTA: ("f1_delta", "n_paired"),
              METRIC_TOKEN_RATIO: ("token_ratio_vs_text", "requests")}.get(metric)
    if source is not None:
        vkey, nkey = source
        if vkey in extra and not _close(row.get("value"), extra.get(vkey)):
            p.append(f"value must equal extra.{vkey} (copied from summary.json, never recomputed)")
        if nkey in extra and row.get("reps") != extra.get(nkey):
            p.append(f"reps must equal extra.{nkey}")
        basis = "scored:chunk_requests" if metric == METRIC_TOKEN_RATIO else (
            "scored:paired_questions" if metric == METRIC_F1_DELTA else "scored:questions")
        if row.get("reps_basis") != basis:
            p.append(f"reps_basis for {metric} must be {basis!r}")

    if (_text(row.get("run_id")) and arm is not None and metric in METRICS
            and _SHA256.match(str(extra.get("suite_fingerprint", "")))
            and _SHA256.match(str(row.get("records_sha256", "")))):
        expected = measurement_identity(
            run_id=row["run_id"], arm=arm, metric=metric,
            suite_fingerprint=extra["suite_fingerprint"], records_sha256=row["records_sha256"])
        if row.get("measurement_id") != expected:
            p.append("measurement_id does not re-derive from (run_id, arm, metric, "
                     "suite_fingerprint, records_sha256)")
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


def _claim(metric: str, run_id: str, arm: str, extra: Mapping[str, Any], value: float) -> str:
    suite = extra["suite_fingerprint"][:12]
    if metric == METRIC_F1:
        return f"OCC-1 {run_id}: arm {arm} scored SQuAD F1 {value:.4f} over {extra['n']} questions (suite {suite})"
    if metric == METRIC_EM:
        return f"OCC-1 {run_id}: arm {arm} scored SQuAD EM {value:.4f} over {extra['n']} questions (suite {suite})"
    if metric == METRIC_F1_DELTA:
        lo, hi = extra["f1_delta_ci95"]
        return (f"OCC-1 {run_id}: arm {arm} vs text paired F1 delta {value:+.4f} "
                f"[95% CI {lo:+.4f}, {hi:+.4f}] over {extra['n_paired']} questions, "
                f"verdict {extra['verdict']} (suite {suite})")
    return (f"OCC-1 {run_id}: arm {arm} billed {value:.4f}x the text arm's prompt tokens "
            f"over {extra['requests']} chunks, verdict {extra['verdict']} (suite {suite})")


def _safe_claim(metric: str, run_id: str, arm: str, extra: Mapping[str, Any], value: float) -> str:
    """The claim text, or a bare label when the row is malformed.

    A malformed row never reaches the file: validate_row names the real problem and the writer
    refuses to emit it.
    """
    try:
        return _claim(metric, run_id, arm, extra, value)
    except (KeyError, TypeError, ValueError):
        return f"OCC-1 {run_id}: arm {arm} {metric}"


def write_belief_measurements(
    run_dir: str | Path, *,
    run_id: str,
    producer: str,
    summary: Mapping[str, Any] | None = None,
    protocol_id: str = "",
    emitted_at: str | None = None,
) -> Path:
    """Emit ``belief_measurements.jsonl`` beside ``summary.json``. This is the SC85 write-side hook.

    ``summary`` is the dict ``run_occ1.py report`` just wrote. If it is omitted, the writer reads
    ``<run_dir>/summary.json``. The attested artifact is ``<run_dir>/records.jsonl``. Every row is
    checked by :func:`validate_row`. On any problem the writer raises :class:`CaptureError` and
    writes nothing.
    """
    root = Path(run_dir)
    if summary is None:
        path = root / "summary.json"
        if not path.is_file():
            raise CaptureError(f"no summary.json in {root}; call this at report time")
        summary = json.loads(path.read_text())
    if not isinstance(summary, Mapping) or not summary:
        raise CaptureError("summary must be a non-empty object")
    overall = summary.get("overall")
    if overall == "VOID" or summary.get("void_reasons"):
        raise CaptureError("run is VOID (" + "; ".join(summary.get("void_reasons") or ["VOID"])
                           + "); a VOID run is an instrument failure, not a measurement")
    if overall not in OVERALL_VERDICTS:
        raise CaptureError(f"summary.overall {overall!r} is not a recorded verdict")
    ident = summary.get("server_identity")
    if not isinstance(ident, Mapping):
        raise CaptureError("summary carries no server_identity; `run` records it at launch")
    if ident.get("problems"):
        raise CaptureError("server identity problems: " + "; ".join(ident["problems"]))
    prereg = summary.get("prereg")
    if not isinstance(prereg, Mapping) or not prereg:
        raise CaptureError("summary carries no pre-registration block")
    records = root / RECORDS_NAME
    if not records.is_file():
        raise CaptureError(f"per-request records missing: {records}")
    records_sha = _file_sha256(records)
    rows_in = summary.get("rows")
    if not isinstance(rows_in, list) or not rows_in:
        raise CaptureError("summary has no per-arm rows")
    if not any(isinstance(r, Mapping) and r.get("arm") == BASELINE_ARM for r in rows_in):
        raise CaptureError("summary has no text (baseline) arm")
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    serving = {k: ident.get(k) for k in ("build_info", "model_path", "n_ctx", "total_slots", "url")
               if ident.get(k) is not None}

    out: list[dict[str, Any]] = []
    for src in rows_in:
        if not isinstance(src, Mapping) or not isinstance(src.get("arm"), str):
            raise CaptureError("summary row lacks an arm")
        arm = src["arm"]
        is_text = arm == BASELINE_ARM
        extra: dict[str, Any] = {
            "arm": arm,
            "baseline_arm": BASELINE_ARM,
            "suite_fingerprint": summary.get("suite_fingerprint"),
            "prereg_sha256": content_hash(dict(prereg)),
            "overall_verdict": overall,
            "serving": serving,
            "n": src.get("n"),
            "requests": src.get("requests"),
            "f1": src.get("f1"),
            "f1_se": src.get("f1_se"),
            "em": src.get("em"),
            "unreadable": src.get("unreadable"),
            "missing": src.get("missing"),
            "truncated": src.get("truncated"),
            "prompt_tokens_mean": src.get("prompt_tokens_mean"),
        }
        metrics = [METRIC_F1, METRIC_EM]
        if not is_text:
            for key in ("n_paired", "f1_delta", "f1_delta_ci95", "em_mcnemar_p",
                        "em_discordant_arm_only", "em_discordant_text_only",
                        "token_ratio_vs_text", "verdict"):
                extra[key] = src.get(key)
            if isinstance(extra["f1_delta_ci95"], (list, tuple)):
                extra["f1_delta_ci95"] = list(extra["f1_delta_ci95"])
            metrics += [METRIC_F1_DELTA, METRIC_TOKEN_RATIO]
        value_key = {METRIC_F1: "f1", METRIC_EM: "em", METRIC_F1_DELTA: "f1_delta",
                     METRIC_TOKEN_RATIO: "token_ratio_vs_text"}
        reps_key = {METRIC_F1: "n", METRIC_EM: "n", METRIC_F1_DELTA: "n_paired",
                    METRIC_TOKEN_RATIO: "requests"}
        basis = {METRIC_F1: "scored:questions", METRIC_EM: "scored:questions",
                 METRIC_F1_DELTA: "scored:paired_questions",
                 METRIC_TOKEN_RATIO: "scored:chunk_requests"}
        for metric in metrics:
            value = extra.get(value_key[metric])
            if not _finite(value):
                raise CaptureError(f"arm {arm}: summary lacks {value_key[metric]}")
            unit, direction, _scope = METRICS[metric]
            row: dict[str, Any] = {
                "schema": CAPTURE_SCHEMA,
                "run_id": run_id,
                "producer": producer,
                "emitted_at": when,
                "date": when[:10],
                "measurement_id": "",
                "metric": metric,
                "value": value,
                "unit": unit,
                "metric_direction": direction,
                "category": "BASELINE" if is_text else "CANDIDATE",
                "claim": _safe_claim(metric, run_id, arm, extra, value),
                "protocol_id": protocol_id,
                "reps": extra.get(reps_key[metric]),
                "reps_basis": basis[metric],
                "records_path": str(records),
                "records_sha256": records_sha,
                "extra": dict(extra),
            }
            if _SHA256.match(str(extra.get("suite_fingerprint", ""))):
                row["measurement_id"] = measurement_identity(
                    run_id=run_id, arm=arm, metric=metric,
                    suite_fingerprint=extra["suite_fingerprint"], records_sha256=records_sha)
            row["row_sha256"] = row_digest(row)
            problems = validate_row(row)
            if problems:
                raise CaptureError(f"arm {arm} {metric}: refusing to emit an invalid row: "
                                   + "; ".join(problems))
            out.append(row)

    sidecar = root / SIDECAR_NAME
    tmp = sidecar.with_suffix(".jsonl.tmp")
    with open(tmp, "w") as handle:
        for row in out:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, sidecar)
    return sidecar


__all__ = [
    "BASELINE_ARM",
    "CAPTURE_SCHEMA",
    "METRICS",
    "METRIC_EM",
    "METRIC_F1",
    "METRIC_F1_DELTA",
    "METRIC_TOKEN_RATIO",
    "RECORDS_NAME",
    "SIDECAR_NAME",
    "CaptureError",
    "content_hash",
    "measurement_identity",
    "row_digest",
    "validate_row",
    "write_belief_measurements",
]
