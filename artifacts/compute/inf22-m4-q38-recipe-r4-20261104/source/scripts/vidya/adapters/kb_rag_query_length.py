"""Project KB-RAG query-length telemetry (internal-kb-rag.md H2) into ``ClaimTuple``.

Producer (write side): epyc-orchestrator ``src/retrieval/kb_rag_query_telemetry.py``.
``kb_rag.query()`` appends one UNTRUNCATED query token count per live query, and
``scripts/kb_rag/query_length_report.py --out <report.json>`` aggregates them. The
report carries producer-authored ``belief_measurements`` rows, one per
(encoder, cap, convention) group and metric: over-cap rate, p50, p95 and max.

This adapter only PROJECTS those rows. Nothing is invented on read:

* The rows cite no protocol, and no codified protocol covers traffic telemetry, so
  every tuple is an OBSERVATION. The shared ladder grades it that way, and no
  protocol is supplied here to lift it.
* ``metric_direction`` is the producer's own label (``lower_better`` = more
  headroom under the truncation cap). The adapter checks it and never infers it.
* The attestation is the log path plus the exact byte prefix the report read.
  The prefix sha256 rides in ``extra``, not in ``attestation_sha256``, because the
  live log keeps growing and a whole-file digest claim would be false after the
  next query.
* A report with no observations yields no rows: absence of traffic is not a
  0 % over-cap rate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.kb_rag_query_length/v1"
#: Frame authority scope: traffic telemetry is a measurement-class OBSERVATION (no protocol).
AUTHORITY = "measurement"
PROJECTION_NAME = "kb_rag_query_length"
REPORT_SCHEMA = "epyc.kb_rag.query_length_report.v1"
BELIEF_SCHEMA = "epyc.kb_rag.query_length_belief.v1"
METRICS = frozenset({
    "kb_rag.query_over_cap_rate",
    "kb_rag.query_tokens_p50",
    "kb_rag.query_tokens_p95",
    "kb_rag.query_tokens_max",
})
_FIELDS = frozenset(ClaimTuple.__dataclass_fields__)


def native_rows(report: str | Path | Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Read the producer-authored rows of one persisted report. Refuses a foreign document."""
    if isinstance(report, Mapping):
        doc = dict(report)
    else:
        try:
            doc = json.loads(Path(report).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ProjectionError(f"KB-RAG query-length report unreadable: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != REPORT_SCHEMA:
        raise ProjectionError(f"not a {REPORT_SCHEMA} document")
    rows = doc.get("belief_measurements")
    if not isinstance(rows, list):
        raise ProjectionError("report carries no belief_measurements list")
    if doc.get("observations", 0) == 0 and rows:
        raise ProjectionError("report claims rows over zero observations")
    return tuple(dict(r) for r in rows)


@register(PROJECTION_NAME)
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one producer row. Grading stays in ``claim_tuple.grade()``."""
    if not isinstance(native, Mapping):
        raise ProjectionError("KB-RAG query-length row must be a mapping")
    extra = native.get("extra")
    if not isinstance(extra, Mapping) or extra.get("belief_schema") != BELIEF_SCHEMA:
        raise ProjectionError(f"row is not a {BELIEF_SCHEMA} row")
    if native.get("metric") not in METRICS:
        raise ProjectionError(f"unknown KB-RAG query-length metric {native.get('metric')!r}")
    if native.get("metric_direction") != "lower_better":
        raise ProjectionError("metric_direction must be the producer-recorded lower_better")
    if str(native.get("protocol_id") or "").strip():
        raise ProjectionError(
            "no codified protocol covers KB-RAG traffic telemetry; a row citing one was not "
            "written by this producer")
    if native.get("attestation_sha256"):
        raise ProjectionError(
            "the live log grows, so a whole-file attestation digest cannot be true; the "
            "prefix digest belongs in extra.log_prefix_sha256")
    prefix = str(extra.get("log_prefix_sha256") or "")
    if len(prefix) != 64:
        raise ProjectionError("extra.log_prefix_sha256 must be a 64-hex digest of the bytes read")
    unknown = set(native) - _FIELDS
    if unknown:
        raise ProjectionError(f"row carries non-ClaimTuple fields: {sorted(unknown)}")
    try:
        return ClaimTuple(**dict(native))
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"KB-RAG query-length ClaimTuple grammar mismatch: {exc}") from exc


__all__ = ["ADAPTER_ID", "AUTHORITY", "BELIEF_SCHEMA", "METRICS", "REPORT_SCHEMA", "native_rows", "project"]
