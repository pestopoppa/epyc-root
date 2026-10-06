"""Project source-bound eval-suite discriminability reports as observations."""
from __future__ import annotations

import json
import hashlib
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402
from adapters._analysis_report_provenance import validate_provenance  # noqa: E402

ADAPTER_ID = "vidya.adapters.eval_suite_discriminability/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "eval-suite-discriminability"
REPORT_SCHEMA = "eval_suite_discriminability_report.v2"
PRODUCER = "scripts/analysis/eval_suite_discriminability.py"
ORCHESTRATOR = Path("/workspace/repos/epyc-orchestrator")
_TOP = frozenset({"schema_version", "generated_at", "measurement_class", "config", "inputs",
                  "warnings", "summary", "suites", "task_classes", "native_provenance"})
_METRICS = (
    ("pass_rate", "higher_better"),
    ("mde", "lower_better"),
    ("run_spread", "lower_better"),
    ("flip_rate", "lower_better"),
)
_CONFIG_FIELDS = frozenset({"alpha", "power", "target_effect", "saturation_high",
                            "saturation_low", "min_n", "quantum_gate", "run_spread_gate",
                            "error_dominated_gate"})
_SUMMARY_FIELDS = frozenset({"n_rows", "n_suites", "n_task_classes", "n_saturated_suites",
                             "n_floored_suites", "n_underpowered_suites",
                             "n_run_unstable_suites", "n_underpowered_task_classes"})
_GROUP_FIELDS = frozenset({
    "group", "n", "n_unique_qids", "n_runs", "correct", "errors", "error_rate",
    "pass_rate", "pass_rate_excl_errors", "wilson_ci", "wilson_width", "effective_quantum",
    "mde", "mde_target_effect", "n_per_arm", "run_spread", "error_dominated_runs",
    "run_stability_unmeasurable", "brittleness", "per_run", "saturated", "floored", "tiny_n",
    "underpowered", "run_unstable", "discriminability_index", "flags",
})
_BRITTLENESS_FIELDS = frozenset({"measured", "n_multirun_qids", "flip_rate",
                                "mean_qid_variance", "max_qid_variance", "n_error_excluded"})


def _document(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise ProjectionError(f"eval discriminability report unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectionError("eval discriminability report must be an object")
    if set(value) != _TOP:
        raise ProjectionError("eval discriminability report has missing or unknown top-level fields")
    if value.get("schema_version") != REPORT_SCHEMA:
        raise ProjectionError("legacy/version-mismatched report has no admissible ClaimTuple provenance")
    if not isinstance(value.get("generated_at"), str) or not isinstance(value.get("inputs"), list):
        raise ProjectionError("report generation time/inputs have invalid types")
    if (any(not isinstance(path, str) for path in value["inputs"])
            or not isinstance(value.get("warnings"), list)
            or any(not isinstance(item, str) for item in value["warnings"])):
        raise ProjectionError("report inputs/warnings contain malformed entries")
    if value.get("measurement_class") != "OBSERVATION":
        raise ProjectionError("report measurement_class must remain OBSERVATION")
    if (not isinstance(value.get("config"), dict)
            or set(value["config"]) != _CONFIG_FIELDS
            or not isinstance(value.get("summary"), dict)
            or set(value["summary"]) != _SUMMARY_FIELDS
            or not isinstance(value.get("suites"), list)
            or not isinstance(value.get("task_classes"), list)):
        raise ProjectionError("report config/suites have invalid types")
    if value.get("warnings"):
        raise ProjectionError("report has malformed/unreadable input warnings and is incomplete")
    return value, raw


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    report_path = Path(path)
    if not report_path.is_file():
        return ()
    document, raw = _document(report_path)
    provenance, report_digest = validate_provenance(
        document, report_path=report_path, report_bytes=raw, schema=REPORT_SCHEMA,
        producer_root=ORCHESTRATOR, producer_path=PRODUCER)
    if not provenance["inputs"]:
        return ()
    rows: list[dict[str, Any]] = []
    for groups_key in ("suites", "task_classes"):
        group_names: set[str] = set()
        for suite in document[groups_key]:
            if (not isinstance(suite, dict) or set(suite) != _GROUP_FIELDS
                    or not isinstance(suite.get("group"), str)):
                raise ProjectionError(f"{groups_key} row has missing or unknown fields")
            if (not isinstance(suite.get("brittleness"), dict)
                    or set(suite["brittleness"]) != _BRITTLENESS_FIELDS):
                raise ProjectionError("suite brittleness has missing or unknown fields")
            if suite["group"] in group_names:
                raise ProjectionError(f"report contains duplicate {groups_key} identities")
            group_names.add(suite["group"])
    for suite in document["suites"]:
        suite_name = suite["group"]
        for metric, _direction in _METRICS:
            value: Any
            if metric == "pass_rate":
                value = suite.get("pass_rate")
            elif metric == "mde":
                value = suite.get("mde")
            elif metric == "run_spread":
                value = suite.get("run_spread")
            else:
                brittleness = suite.get("brittleness")
                value = (brittleness.get("flip_rate") if isinstance(brittleness, dict)
                         and brittleness.get("measured") else None)
            if value is None and metric in {"pass_rate", "run_spread"}:
                raise ProjectionError(f"suite is missing required metric {metric}")
            if (value is None and metric == "flip_rate"
                    and suite["brittleness"].get("measured")):
                raise ProjectionError("measured brittleness is missing its flip_rate")
            if value is None:
                continue
            suite_id = hashlib.sha256(suite_name.encode("utf-8")).hexdigest()
            rows.append({"document": document, "provenance": provenance,
                         "report_path": str(report_path), "report_sha256": report_digest,
                         "suite": suite, "suite_name": suite_name, "metric": metric,
                         "suite_id": suite_id, "value": value})
    return tuple(rows)


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ProjectionError(f"{label} must be finite numeric data")
    return float(value)


@register(SOURCE_KIND)
def project(native: dict[str, Any]) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("suite"), dict):
        raise ProjectionError("eval discriminability native row is malformed")
    path = Path(native.get("report_path", ""))
    disk_doc, raw = _document(path)
    document = native.get("document")
    if disk_doc != document:
        raise ProjectionError("eval discriminability native document differs from parsed report")
    provenance, digest = validate_provenance(
        document, report_path=path, report_bytes=raw, schema=REPORT_SCHEMA,
        producer_root=ORCHESTRATOR, producer_path=PRODUCER)
    if digest != native.get("report_sha256") or provenance != native.get("provenance"):
        raise ProjectionError("eval discriminability report changed after discovery")
    suite_name = native.get("suite_name")
    suite_id = hashlib.sha256(str(suite_name).encode("utf-8")).hexdigest()
    if suite_id != native.get("suite_id"):
        raise ProjectionError("suite identity digest does not rederive")
    metric = native.get("metric")
    direction_by_metric = dict(_METRICS)
    if metric not in direction_by_metric:
        raise ProjectionError("unknown eval discriminability metric")
    suite = native["suite"]
    if set(suite) != _GROUP_FIELDS or set(suite.get("brittleness", {})) != _BRITTLENESS_FIELDS:
        raise ProjectionError("suite native schema has missing or unknown fields")
    if suite.get("group") != suite_name:
        raise ProjectionError("suite identity differs from report row")
    value = _finite(native.get("value"), metric)
    if not 0 <= value <= 1 and metric in {"pass_rate", "flip_rate"}:
        raise ProjectionError(f"{metric} must lie between 0 and 1")
    if metric == "run_spread" and not 0 <= value <= 1:
        raise ProjectionError("run_spread must lie between 0 and 1")
    n = suite.get("n_unique_qids")
    if type(n) is not int or n <= 0:
        raise ProjectionError("suite n_unique_qids must be positive")
    extra = {
        "record_id": provenance["record_id"],
        "suite": suite_name,
        "suite_id": suite_id,
        "n_unique_qids": n,
        "n_rows": suite.get("n_rows"),
        "error_rate": suite.get("error_rate"),
        "wilson_ci": suite.get("wilson_ci"),
        "error_dominated_runs": suite.get("error_dominated_runs", []),
        "flags": suite.get("flags", []),
        "measurement_class": document["measurement_class"],
        "config": document["config"],
        "run_instability_scope": (
            "current producer excludes error-dominated runs from run_spread/flip_rate; "
            "historical v1 reports are refused because they lack source/input provenance"
        ),
    }
    return ClaimTuple(
        measurement_id=f"eval-discriminability:{provenance['record_id']}:{suite_id}:{metric}",
        metric=f"eval_suite_discriminability.{metric}", value=value,
        date=str(document.get("generated_at", ""))[:10], category="BASELINE",
        claim=(f"Observed {metric} for eval suite {suite_name!r}; this diagnostic describes "
               "suite discriminability and is not an eval-quality or promotion verdict."),
        metric_direction=direction_by_metric[metric], protocol_id="", reps=n,
        reps_basis="unique question IDs in this report suite", unit="fraction" if metric in {
            "pass_rate", "flip_rate"} else "report-native",
        attestation_path=str(path), attestation_sha256=digest,
        attestation_locator=f"eval-discriminability:{provenance['record_id']}:{suite_id}:{metric}",
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        extra=extra,
    )


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project"]
