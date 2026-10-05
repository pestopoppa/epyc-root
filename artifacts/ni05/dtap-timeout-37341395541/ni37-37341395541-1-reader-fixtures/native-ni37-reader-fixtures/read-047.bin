"""SC19 / EVL-47 read side: project contention-gate capture rows into measurement ClaimTuples.

The write side is a producer-written JSONL capture — orchestrator
``src/scheduling/contention_gate_capture.py``, envelope schema ``contention_gate_capture.v1``:
one request-keyed envelope per line, appended at the point where
``ChatResponse.contention_gate`` is stamped (opt-in via ``ORCHESTRATOR_CONTENTION_GATE_CAPTURE``,
never raises). This adapter PROJECTS those envelopes into the canonical
:class:`ClaimTuple` and delegates every grading decision to ``claim_tuple.grade()`` — it
holds no ladder and never returns a lattice level of its own.

Doctrine, following the strict-reader family (the chat-template-A/B / DF2-4 precedent):

* **One claim per REQUEST, never per decision.** A request can pass the gate more than once
  (the dispatch path records every candidate tried, not just the winner), so a naive
  per-decision projection would read one request as N independent witnesses. The envelope is
  already request-keyed; the projection keeps it that way.
* **An absent or empty capture is NOT a measurement.** The surface has emitted zero rows so
  far (the orchestrator API is down and the capture is default-OFF), so the honest state is
  ``candidate — ready, unwritten``. Missing/empty file → zero rows, reported as
  "no emissions" — nothing is fabricated from an empty file.
* **A malformed capture is inadmissible as a whole.** The writer appends atomically (one
  JSON line per write), so a non-JSON line or a schema-mismatched envelope means corruption
  or a torn write, not a partial run — same void-the-file rule as the sidecar reader.
* **Attestation is anchored, not attested.** The capture lives OUTSIDE any git tree
  (``/mnt/raid0/llm/bus-runtime/``) and is an append-only log, and the producer pins no
  digest at collect time. A read-time hash of moving bytes cannot pin the artifact, so the
  honest grade is ``Witnessed/Anchored`` — the sha256 of the captured bytes is carried in
  ``extra`` as re-derivation evidence, not as a pin. A producer-authored per-envelope digest
  (a v2 schema) is what would upgrade the grade to ``Witnessed/Attested``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.contention_gate/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "contention-gate-measurement"
CAPTURE_SCHEMA = "contention_gate_capture.v1"
DEFAULT_CAPTURE_PATH = Path("/mnt/raid0/llm/bus-runtime/contention_gate_capture.jsonl")


def _verdict(row: dict) -> str:
    """The request-level verdict the ROUTE-A1 timeout proxy structurally cannot see.

    Derived from the producer's own mirrored top-level fields, using the producer's own
    definition: ``queued_then_admitted`` is exactly ``admitted=True`` with ``waited_s > 0``.
    """
    admitted = bool(row.get("admitted"))
    waited_s = float(row.get("waited_s") or 0.0)
    if not admitted:
        return "blocked"
    if waited_s > 0.0:
        return "queued_then_admitted"
    return "admitted_immediately"


def validate_row(row: Any) -> list[str]:
    """Problems with one envelope line. Empty list = a producer-authored capture row."""
    if not isinstance(row, dict):
        return ["capture row is not a JSON object"]
    problems: list[str] = []
    if row.get("capture_schema") != CAPTURE_SCHEMA:
        problems.append(f"capture_schema must be {CAPTURE_SCHEMA!r}")
    if not isinstance(row.get("request_id"), str) or not row["request_id"].strip():
        problems.append("request_id must be a non-empty string")
    if not isinstance(row.get("ts_utc"), str) or not row["ts_utc"].strip():
        problems.append("ts_utc must be a non-empty string")
    decisions = row.get("gate_decisions")
    if not isinstance(decisions, list) or not decisions:
        problems.append("gate_decisions must be a non-empty list")
    elif row.get("decision_count") != len(decisions):
        problems.append("decision_count does not match gate_decisions length")
    if not isinstance(row.get("admitted"), bool):
        problems.append("admitted must be a boolean")
    if not isinstance(row.get("waited_s"), (int, float)):
        problems.append("waited_s must be a number")
    return problems


def _load_rows(capture_path: Path) -> list[dict] | None:
    """All producer rows from one capture file, or ``None`` when the file is inadmissible."""
    try:
        text = capture_path.read_text()
    except OSError:
        return None
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None
        if validate_row(row):
            return None
        rows.append(row)
    return rows


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refusal_reason(capture_path: str | Path) -> str | None:
    """Why a capture yields zero rows: ``"no emissions"`` / ``"malformed: ..."``, else None.

    An absent or empty capture is not a measurement — the honest state of a producer that
    has not yet emitted — and is reported as "no emissions" rather than as an error.
    """
    path = Path(capture_path)
    if not path.is_file():
        return "no emissions"
    try:
        text = path.read_text()
    except OSError as exc:
        return f"malformed: unreadable capture ({exc})"
    if not text.strip():
        return "no emissions"
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            return f"malformed: non-JSON line ({exc})"
        problems = validate_row(row)
        if problems:
            return "malformed: " + "; ".join(problems)
    return None


def native_rows(capture_path: str | Path) -> tuple[dict, ...]:
    """Admissible native rows from one capture file. Missing/empty/malformed -> zero rows."""
    path = Path(capture_path)
    if not path.is_file():
        return ()
    rows = _load_rows(path)
    if not rows:
        return ()
    request_count = len(rows)
    digest = _file_sha256(path)
    return tuple({
        "row": row,
        "capture_path": str(path),
        "capture_sha256": digest,
        "request_count": request_count,
    } for row in rows)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. One claim per REQUEST, never per decision."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("contention-gate native row must retain the producer envelope")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError(
            "contention-gate capture row is not a producer-authored envelope: "
            + "; ".join(problems))
    if not isinstance(native.get("request_count"), int) or native["request_count"] < 1:
        raise ProjectionError(
            "contention-gate native row must retain the capture's request count "
            "(callers cannot bypass native_rows)")
    decisions = row["gate_decisions"]
    verdict = _verdict(row)
    capture_path = str(native.get("capture_path") or "")
    measurement_id = f"cg_{row['request_id']}"
    return ClaimTuple(
        measurement_id=measurement_id,
        metric="contention_gate_verdict",
        value=verdict,
        date=str(row["ts_utc"])[:10],
        # Current serving-path behaviour, not a proposal under test: the echo measures how
        # the live gate actually decided, so it is the baseline the 503 proxy replaced.
        category="BASELINE",
        claim=(
            f"Request {row['request_id']} {verdict} under {row['capture_schema']}: "
            f"admitted={row['admitted']}, waited_s={row['waited_s']}, "
            f"{len(decisions)} gate decision(s) recorded — the contention verdict is "
            "measured directly, not inferred from a fail-closed 503 timeout"
        ),
        # The per-request verdict is categorical, so direction is nominal at tuple level;
        # the direction that matters (share of requests directly measured) is derivable
        # from reps across the capture, never inferred here.
        metric_direction="higher_better",
        protocol_id=row["capture_schema"],
        reps=native["request_count"],
        reps_basis="requests",
        unit="verdict",
        # Anchored, not Attested: the capture is an off-tree append-only log and the
        # producer pins no digest at collect time. The sha256 of the captured bytes rides
        # in extra as re-derivation evidence; a producer-authored v2 hash would upgrade.
        attestation_sha256="",
        attestation_locator=capture_path,
        source_kind=SOURCE_KIND,
        extra={
            "schema": row["capture_schema"],
            "request_id": row["request_id"],
            "ts_utc": row["ts_utc"],
            "decision_count": row["decision_count"],
            "admitted": row["admitted"],
            "waited_s": row["waited_s"],
            "queued_then_admitted": _verdict(row) == "queued_then_admitted",
            "candidate_topology_idx": row.get("candidate_topology_idx"),
            "gate_decisions": decisions,
            "capture_path": capture_path,
            "capture_sha256": native.get("capture_sha256", ""),
        },
    )


def frames_for_capture(capture_path: str | Path, *, as_of: str) -> list[dict]:
    """Uniform frame emission through the shared carrier (`claim_tuple.to_frames`)."""
    frames: list[dict] = []
    for native in native_rows(capture_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "CAPTURE_SCHEMA", "DEFAULT_CAPTURE_PATH",
    "validate_row", "refusal_reason", "native_rows", "project", "frames_for_capture",
]
