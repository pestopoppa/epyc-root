"""SC86 write-side hook: producer-authored belief rows for HS-4 OpenCode-shell runs.

HS-4 (``harness-selection-and-integration.md``) chose OpenCode as the agentic shell over the
orchestrator's ``/v1`` seam. P0.5 of ``docs/design/hs4-shell-and-orchestrator-features-20260916.md``
§4 requires this hook to exist before the first measured shell run (P0.4 acceptance, HS-14
bake-off).

Two files, two roles:

* **Run sidecar** (``opencode_shell_run.json``, schema :data:`RUN_SCHEMA`). The shell-run driver
  (HS-4 P0.4) writes it at run end, beside the per-attempt records file. It is this writer's INPUT
  and the complete list of what a driver must record. :data:`RUN_SIDECAR_FIELDS` pins its field
  names::

      schema                 "epyc.hs4.opencode_shell_run.v1"
      run_id                 non-empty string
      started_at/finished_at UTC timestamps; started_at >= HOOK_SINCE
      arm_role               "BASELINE" | "CANDIDATE"
      harness                {"name": "opencode", "pin": <40-hex commit>}
      plugin                 {"name": str, "sha256": <64-hex over the plugin source>}
      config_sha256          <64-hex over the OpenCode config actually used>
      harness_card_version   non-empty string (the HS-7 Harness Card this config publishes)
      request_keys           {"x_memory": "on"|"off", "x_tool_mode": "internal"|"client"}
      serving                {"endpoint": str, "model_role": str, "build_info": str,
                              "enable_thinking": bool}
      task_suite             {"name": str, "fingerprint": <64-hex>}
      counts                 {"tasks", "trials_per_task", "attempts", "passed_attempts",
                              "input_tokens", "cached_prompt_tokens"}  (integers)
      records_file           bare file name inside the run dir (per-attempt records)

* **Belief sidecar** (``opencode_shell_run.beliefs.jsonl``, schema :data:`CAPTURE_SCHEMA`). This
  writer emits it. It has one row per HS-14 column (``handoffs/active/harness-selection-and-integration.md``
  HS-14, "Local bake-off requirement"):

  ==========================================  ===========================  ==============
  metric                                      value                        reps
  ==========================================  ===========================  ==============
  ``shell_pass_at_1``                         passed_attempts / attempts   attempts
  ``shell_input_tokens_per_attempt``          input_tokens / attempts      attempts
  ``shell_prefix_cache_hit_share``            cached / input_tokens        attempts
  ``shell_prefill_tokens_per_solved_task``    (input - cached) / passed    passed_attempts
  ==========================================  ===========================  ==============

  The last column is undefined when nothing passed. It is then omitted and named in
  ``extra.columns_absent``, never filled with zero or infinity.

The writer is a PROJECTION. Each value is a fixed ratio of two recorded counts, and
:func:`validate_row` re-derives it, so the writer and the reader share one definition. The writer
never opens a transcript and never guesses an identity.

Refusals (:class:`CaptureError`, nothing written):

* **No harness pin, plugin hash or config hash.** A shell run whose harness cannot be named cannot
  be compared with any other shell run.
* **Pre-hook runs.** A run dir without a run sidecar has no hook to call. A run that started before
  :data:`HOOK_SINCE` predates this contract. A call made more than :data:`MAX_EMIT_LAG_S` after
  ``finished_at`` is a backfill, not a report-time capture (the DF2-4 precedent).
* **Inconsistent counts.** attempts must equal tasks x trials, passed <= attempts, and
  cached <= input tokens.
* **No protocol is claimed that does not exist.** No shell-run protocol is codified under
  ``measurement/protocols/`` (SC86b), so ``protocol_id`` defaults to empty and
  ``claim_tuple.grade()`` caps every row at ``Judged``, an OBSERVATION.

**The locator is the RUN.** Every row of a run shares it, and the metric separates the claims.
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

RUN_SCHEMA = "epyc.hs4.opencode_shell_run.v1"
RUN_SIDECAR_NAME = "opencode_shell_run.json"
CAPTURE_SCHEMA = "epyc.vidya.opencode_shell_run_capture.v1"
SIDECAR_NAME = "opencode_shell_run.beliefs.jsonl"

#: The hook landed 2026-09-16, before any measured shell run. Earlier runs are pre-hook.
HOOK_SINCE = "2026-09-16T00:00:00Z"
#: A capture made later than this after the run finished is a backfill.
MAX_EMIT_LAG_S = 24 * 3600

RUN_SIDECAR_FIELDS: dict[str, tuple[str, ...]] = {
    "": ("schema", "run_id", "started_at", "finished_at", "arm_role", "harness", "plugin",
         "config_sha256", "harness_card_version", "request_keys", "serving", "task_suite",
         "counts", "records_file"),
    "harness": ("name", "pin"),
    "plugin": ("name", "sha256"),
    "request_keys": ("x_memory", "x_tool_mode"),
    "serving": ("endpoint", "model_role", "build_info", "enable_thinking"),
    "task_suite": ("name", "fingerprint"),
    "counts": ("tasks", "trials_per_task", "attempts", "passed_attempts", "input_tokens",
               "cached_prompt_tokens"),
}

HARNESS_NAME = "opencode"
X_MEMORY_ARMS = frozenset({"on", "off"})
X_TOOL_MODES = frozenset({"internal", "client"})
ARM_ROLES = frozenset({"BASELINE", "CANDIDATE"})

METRIC_PASS = "shell_pass_at_1"
METRIC_INPUT = "shell_input_tokens_per_attempt"
METRIC_CACHE = "shell_prefix_cache_hit_share"
METRIC_PREFILL = "shell_prefill_tokens_per_solved_task"

#: metric -> (unit, direction, reps basis). Dict order is the emission order.
METRICS: dict[str, tuple[str, str, str]] = {
    METRIC_PASS: ("fraction_passed", "higher_better", "scored:attempts"),
    METRIC_INPUT: ("input_tokens_per_attempt", "lower_better", "scored:attempts"),
    METRIC_CACHE: ("fraction_prompt_tokens_cached", "higher_better", "scored:attempts"),
    METRIC_PREFILL: ("prefill_tokens_per_passed_attempt", "lower_better",
                     "scored:passed_attempts"),
}

#: The run-identity keys every row's ``extra`` carries (pinned by the tests).
EXTRA_FIELDS = (
    "harness_name", "harness_pin", "plugin_name", "plugin_sha256", "config_sha256",
    "harness_card_version", "x_memory", "x_tool_mode", "serving", "task_suite", "counts",
    "hs14_columns", "columns_absent", "run_sidecar_sha256", "started_at", "finished_at",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_BARE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class CaptureError(ValueError):
    """The driver asked for a sidecar the run cannot honestly support."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def content_hash(value: Any) -> str:
    try:
        return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as exc:
        raise CaptureError(f"value is not canonical JSON: {exc}") from exc


def row_digest(row: Mapping[str, Any]) -> str:
    """Self-hash over everything but the hash field itself."""
    return content_hash({k: v for k, v in row.items() if k != "row_sha256"})


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def measurement_identity(*, run_id: str, metric: str, harness_pin: str, config_sha256: str,
                         x_memory: str, records_sha256: str) -> str:
    digest = content_hash({
        "run_id": run_id, "metric": metric, "harness_pin": harness_pin,
        "config_sha256": config_sha256, "x_memory": x_memory, "records_sha256": records_sha256,
    })
    return f"ocshell_{digest[:24]}"


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _int(value: Any, minimum: int) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= minimum


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def columns(counts: Mapping[str, Any]) -> dict[str, float | None]:
    """The HS-14 column set, as fixed ratios of recorded counts. ``None`` = undefined."""
    attempts = counts["attempts"]
    passed = counts["passed_attempts"]
    inp = counts["input_tokens"]
    cached = counts["cached_prompt_tokens"]
    return {
        METRIC_PASS: passed / attempts,
        METRIC_INPUT: inp / attempts,
        METRIC_CACHE: cached / inp,
        METRIC_PREFILL: (inp - cached) / passed if passed > 0 else None,
    }


def _reps(metric: str, counts: Mapping[str, Any]) -> int:
    return counts["passed_attempts"] if metric == METRIC_PREFILL else counts["attempts"]


def validate_counts(counts: Any) -> list[str]:
    if not isinstance(counts, Mapping):
        return ["counts must be an object"]
    p: list[str] = []
    for key in RUN_SIDECAR_FIELDS["counts"]:
        minimum = 0 if key in ("passed_attempts", "cached_prompt_tokens") else 1
        if not _int(counts.get(key), minimum):
            p.append(f"counts.{key} must be an integer >= {minimum}")
    if p:
        return p
    if counts["attempts"] != counts["tasks"] * counts["trials_per_task"]:
        p.append("counts.attempts must equal tasks x trials_per_task")
    if counts["passed_attempts"] > counts["attempts"]:
        p.append("counts.passed_attempts exceeds attempts")
    if counts["cached_prompt_tokens"] > counts["input_tokens"]:
        p.append("counts.cached_prompt_tokens exceeds input_tokens")
    return p


def validate_run_sidecar(run: Any) -> list[str]:
    """Every problem with a driver-written run sidecar. Empty list == acceptable input."""
    if not isinstance(run, Mapping):
        return ["run sidecar is not a JSON object"]
    p: list[str] = []
    if run.get("schema") != RUN_SCHEMA:
        p.append(f"schema must be {RUN_SCHEMA!r} (a run without it is pre-hook)")
    missing = [k for k in RUN_SIDECAR_FIELDS[""] if k not in run]
    if missing:
        p.append("missing fields: " + ", ".join(missing))
    unknown = sorted(set(run) - set(RUN_SIDECAR_FIELDS[""]))
    if unknown:
        p.append("unknown fields (the schema is closed): " + ", ".join(unknown))
    if not _text(run.get("run_id")):
        p.append("run_id must be a non-empty string")

    started, finished = _parse_utc(run.get("started_at")), _parse_utc(run.get("finished_at"))
    if started is None or finished is None:
        p.append("started_at and finished_at must be UTC timestamps")
    else:
        if finished < started:
            p.append("finished_at precedes started_at")
        if started < _parse_utc(HOOK_SINCE):
            p.append(f"run started {run['started_at']}, before the SC86 hook ({HOOK_SINCE}); "
                     "a pre-hook run stays pre-hook")
    if run.get("arm_role") not in ARM_ROLES:
        p.append(f"arm_role must be one of {sorted(ARM_ROLES)}")

    harness = run.get("harness")
    if not isinstance(harness, Mapping) or not _GIT_SHA.match(str(harness.get("pin", ""))):
        p.append("harness.pin must be the 40-hex OpenCode commit the run used (no pin, no row)")
    elif harness.get("name") != HARNESS_NAME:
        p.append(f"harness.name must be {HARNESS_NAME!r}")
    plugin = run.get("plugin")
    if not isinstance(plugin, Mapping) or not _SHA256.match(str(plugin.get("sha256", ""))):
        p.append("plugin.sha256 must be the 64-hex digest of the plugin source")
    elif not _text(plugin.get("name")):
        p.append("plugin.name must be a non-empty string")
    if not _SHA256.match(str(run.get("config_sha256", ""))):
        p.append("config_sha256 must be the 64-hex digest of the OpenCode config used")
    if not _text(run.get("harness_card_version")):
        p.append("harness_card_version must name the published Harness Card")

    keys = run.get("request_keys")
    if not isinstance(keys, Mapping):
        p.append("request_keys must be an object")
    else:
        if keys.get("x_memory") not in X_MEMORY_ARMS:
            p.append("request_keys.x_memory must be 'on' or 'off'")
        if keys.get("x_tool_mode") not in X_TOOL_MODES:
            p.append("request_keys.x_tool_mode must be 'internal' or 'client'")

    serving = run.get("serving")
    if not isinstance(serving, Mapping):
        p.append("serving must be an object")
    else:
        for key in ("endpoint", "model_role", "build_info"):
            if not _text(serving.get(key)):
                p.append(f"serving.{key} must be recorded, never guessed")
        if not isinstance(serving.get("enable_thinking"), bool):
            p.append("serving.enable_thinking must be recorded as a boolean (HS-14)")

    suite = run.get("task_suite")
    if not isinstance(suite, Mapping) or not _SHA256.match(str(suite.get("fingerprint", ""))):
        p.append("task_suite.fingerprint must be a 64-hex digest")
    elif not _text(suite.get("name")):
        p.append("task_suite.name must be a non-empty string")

    p.extend(validate_counts(run.get("counts")))
    records = run.get("records_file")
    if not isinstance(records, str) or not _BARE_NAME.match(records) or records in (".", ".."):
        p.append("records_file must be a bare file name inside the run directory")
    return p


def validate_row(row: Any) -> list[str]:
    """Every structural problem in one producer-authored row. Empty list == valid.

    The writer uses it to refuse to emit, and the reader uses it to refuse to project.
    """
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for key in ("run_id", "producer", "measurement_id", "claim", "records_path", "date"):
        if not _text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not isinstance(row.get("protocol_id"), str):
        p.append("protocol_id must be a string (empty when no codified protocol exists)")
    emitted = _parse_utc(row.get("emitted_at"))
    if emitted is None:
        p.append("emitted_at must be a UTC timestamp")
    elif row.get("date") != row["emitted_at"][:10]:
        p.append("date must be the emitted_at date")
    metric = row.get("metric")
    if metric not in METRICS:
        p.append(f"metric must be one of {sorted(METRICS)}")
    else:
        unit, direction, basis = METRICS[metric]
        if row.get("unit") != unit:
            p.append(f"unit for {metric} must be {unit!r}")
        if row.get("metric_direction") != direction:
            p.append(f"metric_direction for {metric} is recorded as {direction!r}")
        if row.get("reps_basis") != basis:
            p.append(f"reps_basis for {metric} must be {basis!r}")
    if row.get("category") not in ARM_ROLES:
        p.append(f"category must be one of {sorted(ARM_ROLES)}")
    if not _SHA256.match(str(row.get("records_sha256", ""))):
        p.append("records_sha256 must be a 64-hex digest over the per-attempt records file")
    if not _finite(row.get("value")):
        p.append("value must be a finite number")
    if not _int(row.get("reps"), 1):
        p.append("reps must be a positive integer")

    extra = row.get("extra")
    if not isinstance(extra, dict):
        return p + ["extra must be an object carrying the run identity"]
    if set(extra) != set(EXTRA_FIELDS):
        p.append("extra keys must be exactly " + ", ".join(EXTRA_FIELDS))
        return p
    if extra["harness_name"] != HARNESS_NAME:
        p.append(f"extra.harness_name must be {HARNESS_NAME!r}")
    if not _GIT_SHA.match(str(extra["harness_pin"])):
        p.append("extra.harness_pin must be a 40-hex commit")
    for key in ("plugin_sha256", "config_sha256", "run_sidecar_sha256"):
        if not _SHA256.match(str(extra[key])):
            p.append(f"extra.{key} must be a 64-hex digest")
    for key in ("plugin_name", "harness_card_version"):
        if not _text(extra[key]):
            p.append(f"extra.{key} must be a non-empty string")
    if extra["x_memory"] not in X_MEMORY_ARMS:
        p.append("extra.x_memory must be 'on' or 'off'")
    if extra["x_tool_mode"] not in X_TOOL_MODES:
        p.append("extra.x_tool_mode must be 'internal' or 'client'")
    serving = extra["serving"]
    if not (isinstance(serving, dict) and all(_text(serving.get(k)) for k in
                                              ("endpoint", "model_role", "build_info"))
            and isinstance(serving.get("enable_thinking"), bool)):
        p.append("extra.serving must carry endpoint, model_role, build_info, enable_thinking")
    suite = extra["task_suite"]
    if not (isinstance(suite, dict) and _text(suite.get("name"))
            and _SHA256.match(str(suite.get("fingerprint", "")))):
        p.append("extra.task_suite must carry name and a 64-hex fingerprint")
    for key in ("started_at", "finished_at"):
        if _parse_utc(extra[key]) is None:
            p.append(f"extra.{key} must be a UTC timestamp")

    count_problems = validate_counts(extra["counts"])
    p.extend(f"extra.{x}" for x in count_problems)
    if not count_problems:
        derived = columns(extra["counts"])
        if extra["hs14_columns"] != derived:
            p.append("extra.hs14_columns does not re-derive from extra.counts")
        absent = sorted(k for k, v in derived.items() if v is None)
        if extra["columns_absent"] != absent:
            p.append("extra.columns_absent must name exactly the undefined columns")
        if metric in METRICS:
            if derived[metric] is None:
                p.append(f"{metric} is undefined for this run and must not be emitted")
            elif row.get("value") != derived[metric]:
                p.append(f"value does not re-derive from extra.counts for {metric}")
            if row.get("reps") != _reps(metric, extra["counts"]):
                p.append(f"reps for {metric} does not match extra.counts")

    if (not p and metric in METRICS):
        expected = measurement_identity(
            run_id=row["run_id"], metric=metric, harness_pin=extra["harness_pin"],
            config_sha256=extra["config_sha256"], x_memory=extra["x_memory"],
            records_sha256=row["records_sha256"])
        if row.get("measurement_id") != expected:
            p.append("measurement_id does not re-derive from (run_id, metric, harness_pin, "
                     "config_sha256, x_memory, records_sha256)")
    if not _SHA256.match(str(row.get("row_sha256", ""))):
        p.append("row_sha256 must be a 64-hex self-hash")
    else:
        try:
            if row_digest(row) != row["row_sha256"]:
                p.append("row_sha256 does not bind the row content")
        except CaptureError as exc:
            p.append(f"row is not canonically hashable: {exc}")
    return p


def _claim(run: Mapping[str, Any], metric: str, value: float) -> str:
    c = run["counts"]
    head = (f"OpenCode shell run {run['run_id']} (pin {run['harness']['pin'][:12]}, "
            f"cfg {run['config_sha256'][:12]}, x_memory={run['request_keys']['x_memory']}, "
            f"suite {run['task_suite']['name']})")
    if metric == METRIC_PASS:
        return f"{head}: pass@1 {value:.4f} over {c['attempts']} attempts"
    if metric == METRIC_INPUT:
        return f"{head}: {value:.1f} input tokens per attempt over {c['attempts']} attempts"
    if metric == METRIC_CACHE:
        return f"{head}: prefix-cache hit share {value:.4f} of {c['input_tokens']} prompt tokens"
    return (f"{head}: {value:.1f} prefill tokens per solved task over "
            f"{c['passed_attempts']} passed attempts")


def write_belief_measurements(
    run_dir: str | Path, *,
    producer: str,
    run: Mapping[str, Any] | None = None,
    protocol_id: str = "",
    emitted_at: str | None = None,
) -> Path:
    """Emit ``opencode_shell_run.beliefs.jsonl`` into ``run_dir``. This is the SC86 hook.

    ``run`` is the run sidecar the driver just wrote. If omitted, the writer reads
    ``<run_dir>/opencode_shell_run.json``. On any problem it raises :class:`CaptureError` and
    writes nothing.
    """
    root = Path(run_dir)
    run_path = root / RUN_SIDECAR_NAME
    if run is None:
        if not run_path.is_file():
            raise CaptureError(f"no {RUN_SIDECAR_NAME} in {root}: a run without one is pre-hook")
        try:
            run = json.loads(run_path.read_text())
        except json.JSONDecodeError as exc:
            raise CaptureError(f"{run_path} is not JSON: {exc}") from exc
    if not _text(producer):
        raise CaptureError("producer must name the driver")
    problems = validate_run_sidecar(run)
    if problems:
        raise CaptureError("refusing the run sidecar: " + "; ".join(problems))

    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    emitted, finished = _parse_utc(when), _parse_utc(run["finished_at"])
    if emitted is None:
        raise CaptureError("emitted_at must be a UTC timestamp")
    lag = (emitted - finished).total_seconds()
    if lag < 0:
        raise CaptureError("emitted_at precedes the run's finished_at")
    if lag > MAX_EMIT_LAG_S:
        raise CaptureError(f"capture is {lag:.0f}s after the run finished; the hook runs at "
                           "report time and never backfills a finished run")

    records = root / run["records_file"]
    if not records.is_file():
        raise CaptureError(f"per-attempt records missing: {records}")
    records_sha = file_sha256(records)
    counts = dict(run["counts"])
    derived = columns(counts)
    extra = {
        "harness_name": run["harness"]["name"],
        "harness_pin": run["harness"]["pin"],
        "plugin_name": run["plugin"]["name"],
        "plugin_sha256": run["plugin"]["sha256"],
        "config_sha256": run["config_sha256"],
        "harness_card_version": run["harness_card_version"],
        "x_memory": run["request_keys"]["x_memory"],
        "x_tool_mode": run["request_keys"]["x_tool_mode"],
        "serving": {k: run["serving"][k] for k in RUN_SIDECAR_FIELDS["serving"]},
        "task_suite": {k: run["task_suite"][k] for k in RUN_SIDECAR_FIELDS["task_suite"]},
        "counts": counts,
        "hs14_columns": derived,
        "columns_absent": sorted(k for k, v in derived.items() if v is None),
        "run_sidecar_sha256": content_hash(dict(run)),
        "started_at": run["started_at"],
        "finished_at": run["finished_at"],
    }

    out: list[dict[str, Any]] = []
    for metric, (unit, direction, basis) in METRICS.items():
        value = derived[metric]
        if value is None:
            continue
        row: dict[str, Any] = {
            "schema": CAPTURE_SCHEMA,
            "run_id": run["run_id"],
            "producer": producer,
            "emitted_at": when,
            "date": when[:10],
            "measurement_id": measurement_identity(
                run_id=run["run_id"], metric=metric, harness_pin=extra["harness_pin"],
                config_sha256=extra["config_sha256"], x_memory=extra["x_memory"],
                records_sha256=records_sha),
            "metric": metric,
            "value": value,
            "unit": unit,
            "metric_direction": direction,
            "category": run["arm_role"],
            "claim": _claim(run, metric, value),
            "protocol_id": protocol_id,
            "reps": _reps(metric, counts),
            "reps_basis": basis,
            "records_path": str(records),
            "records_sha256": records_sha,
            "extra": json.loads(json.dumps(extra)),
        }
        row["row_sha256"] = row_digest(row)
        problems = validate_row(row)
        if problems:
            raise CaptureError(f"{metric}: refusing to emit an invalid row: " + "; ".join(problems))
        out.append(row)

    sidecar = root / SIDECAR_NAME
    tmp = sidecar.with_suffix(".jsonl.tmp")
    with open(tmp, "w") as handle:
        for row in out:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, sidecar)
    return sidecar


__all__ = [
    "CAPTURE_SCHEMA", "EXTRA_FIELDS", "HOOK_SINCE", "MAX_EMIT_LAG_S", "METRICS",
    "METRIC_CACHE", "METRIC_INPUT", "METRIC_PASS", "METRIC_PREFILL", "RUN_SCHEMA",
    "RUN_SIDECAR_FIELDS", "RUN_SIDECAR_NAME", "SIDECAR_NAME", "CaptureError", "columns",
    "content_hash", "file_sha256", "measurement_identity", "row_digest", "validate_counts",
    "validate_row", "validate_run_sidecar", "write_belief_measurements",
]
