"""Project prospective MF-VBS-1 receipts as observations via the shared grader only."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402
from adapters._analysis_report_provenance import validate_provenance  # noqa: E402

ADAPTER_ID = "vidya.adapters.verify_before_stop/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "verify-before-stop-measurement"
REPORT_SCHEMA = "mf_vbs1_verify_before_stop_report.v2"
PRODUCER = "scripts/analysis/mf_vbs1_verify_before_stop.py"
ORCHESTRATOR = Path("/workspace/repos/epyc-orchestrator")
_TOP = frozenset({
    "prior_reference", "corpus", "classification", "rates", "delegates_to_user_variant",
    "execution_tool_availability", "auto_finalize_caveat", "breakdown_by_arm",
    "breakdown_by_task", "breakdown_by_source_dir", "breakdown_by_role",
    "examples_class_c", "examples_class_d", "prior_comparison", "native_provenance",
})
_RATES = {
    "failure_over_all_voluntary_stops": ("mf_vbs1.failure_rate.all_voluntary", "lower_better"),
    "failure_over_edited_voluntary_stops": ("mf_vbs1.failure_rate.edited_voluntary", "lower_better"),
    "no_execution_after_edit_corpuswide_forced_and_voluntary":
        ("mf_vbs1.no_execution_after_edit", "lower_better"),
}


def _document(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise ProjectionError(f"MF-VBS-1 report unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectionError("MF-VBS-1 report must be a JSON object")
    if set(value) != _TOP:
        raise ProjectionError("MF-VBS-1 report has missing or unknown top-level fields")
    if not isinstance(value.get("corpus"), dict) or not isinstance(value.get("rates"), dict):
        raise ProjectionError("MF-VBS-1 report has no corpus/rates object")
    return value, raw


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    report_path = Path(path)
    if not report_path.is_file():
        return ()
    document, raw = _document(report_path)
    if set(document["rates"]) != set(_RATES):
        raise ProjectionError("MF-VBS-1 report must carry every declared rate exactly once")
    provenance, report_digest = validate_provenance(
        document, report_path=report_path, report_bytes=raw, schema=REPORT_SCHEMA,
        producer_root=ORCHESTRATOR, producer_path=PRODUCER)
    trajectory_count = document["corpus"].get("n_total_real_trajectories")
    if type(trajectory_count) is not int or trajectory_count < 0:
        raise ProjectionError("MF-VBS-1 corpus trajectory count must be a nonnegative integer")
    if trajectory_count == 0:
        return ()
    return tuple({"document": document, "provenance": provenance,
                  "report_path": str(report_path), "report_sha256": report_digest,
                  "metric_key": key} for key in _RATES if key in document["rates"])


def _finite_number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ProjectionError(f"{label} must be a finite number")
    return float(value)


@register(SOURCE_KIND)
def project(native: dict[str, Any]) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("document"), dict):
        raise ProjectionError("MF-VBS-1 native report is malformed")
    doc = native["document"]
    path = Path(native.get("report_path", ""))
    # Revalidate at projection time so callers cannot fabricate a native envelope.
    disk_doc, raw = _document(path)
    if disk_doc != doc:
        raise ProjectionError("MF-VBS-1 native document differs from the parsed report file")
    provenance, digest = validate_provenance(
        doc, report_path=path, report_bytes=raw, schema=REPORT_SCHEMA,
        producer_root=ORCHESTRATOR, producer_path=PRODUCER)
    if digest != native.get("report_sha256") or provenance != native.get("provenance"):
        raise ProjectionError("MF-VBS-1 report changed after discovery")
    key = native.get("metric_key")
    if key not in _RATES:
        raise ProjectionError("unknown MF-VBS-1 metric key")
    metric, direction = _RATES[key]
    rate = doc["rates"].get(key)
    if not isinstance(rate, dict):
        raise ProjectionError("MF-VBS-1 rate entry must be an object")
    numerator, denominator = rate.get("numerator"), rate.get("denominator")
    if type(numerator) is not int or numerator < 0 or type(denominator) is not int or denominator <= 0:
        raise ProjectionError("MF-VBS-1 rate requires a positive integer denominator")
    if numerator > denominator:
        raise ProjectionError("MF-VBS-1 numerator exceeds denominator")
    if key == "no_execution_after_edit_corpuswide_forced_and_voluntary":
        call_bearing = rate.get("call_bearing_edited_trajectories")
        if (type(call_bearing) is not int or call_bearing < 0 or call_bearing > denominator
                or numerator != denominator - call_bearing):
            raise ProjectionError("MF-VBS-1 edited/call-bearing intersection is inconsistent")
    point = _finite_number(rate.get("point"), "rate.point")
    if not math.isclose(point, numerator / denominator, rel_tol=0, abs_tol=1e-12):
        raise ProjectionError("MF-VBS-1 point estimate does not match numerator/denominator")
    ci_lo_key, ci_hi_key = ("wilson_95ci_lo_of_never_executed",
                            "wilson_95ci_hi_of_never_executed") if key == (
                                "no_execution_after_edit_corpuswide_forced_and_voluntary"
                            ) else ("wilson_95ci_lo", "wilson_95ci_hi")
    ci_lo = _finite_number(rate.get(ci_lo_key), f"rate.{ci_lo_key}")
    ci_hi = _finite_number(rate.get(ci_hi_key), f"rate.{ci_hi_key}")
    if not 0 <= ci_lo <= point <= ci_hi <= 1:
        raise ProjectionError("MF-VBS-1 Wilson interval does not contain the point estimate")
    corpus = doc["corpus"]
    # Dates and role/model are unknown unless the native parsed rows bind them.
    date_text = corpus.get("date_range")
    date = date_text if isinstance(date_text, str) else ""
    scope = {
        "date_range": date_text if isinstance(date_text, str) else None,
        "role_model": corpus.get("role_model") if isinstance(corpus.get("role_model"), str) else None,
        "n_total_real_trajectories": corpus.get("n_total_real_trajectories"),
        "denominator_definition": rate.get("description", ""),
        "numerator": numerator,
        "denominator": denominator,
        "wilson_95ci_lo": ci_lo,
        "wilson_95ci_hi": ci_hi,
        "record_id": provenance["record_id"],
    }
    return ClaimTuple(
        measurement_id=f"mf-vbs1:{provenance['record_id']}:{metric}",
        metric=metric, value=point, date=date, category="BASELINE",
        claim=(f"Observed verify-before-stop rate for the named BEP/REPL corpus: {metric}; "
               "the denominator and task/role/date scope are in extra."),
        metric_direction=direction, protocol_id="", reps=denominator,
        reps_basis="native report denominator; see extra.denominator_definition",
        attestation_path=str(path), attestation_sha256=digest,
        attestation_locator=f"mf-vbs1:{provenance['record_id']}:{metric}",
        attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND, extra=scope,
    )


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project"]
