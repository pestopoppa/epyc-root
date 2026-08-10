"""SC3: record a measurement at write time, in the grammar the constitution already defines.

WHY THIS EXISTS. Measured 2026-08-11: across 4,224 beliefs the Q axis holds **zero** claims at
`Q4 Witnessed`. The only adapter reads `intake_index.yaml`, and an intake entry is a literature
record, so the top of the carrier is unreachable no matter how much is ingested. Meanwhile our own
progress logs carry 4,687 stated results of which **105 (2.2%)** cite anything durable, and most of
those name a source file rather than a measurement artifact. The substrate models what we read and
never what we measured.

**Nothing here invents a schema.** `MEASUREMENT_POLICY.md` already states the rule:

    A decision-gating number = (metric, protocol-id, n/reps, date, attestation ref).
    A number without a protocol citation is an OBSERVATION: usable for hypotheses, never for
    keep/revert/deploy/promote/buy/close decisions.

That is precisely a Q-axis grading rule, so this module implements it rather than paraphrasing it.
The constitution is the authority; `MEASUREMENT.md` and the policy digest are read-only to
autonomous processes and this module does not touch them — it records claims that comply with them.

The grading falls straight out of the constitution's own words:

  * full tuple, artifact present and hashed  -> `Witnessed/Attested`  (decision-gating)
  * full tuple, artifact named but unhashed  -> `Witnessed/Anchored`  (re-derivable, not pinned)
  * protocol cited, no attestation ref       -> `Verified/Located`    (a result, not decision-gating)
  * no protocol citation                     -> `Judged/Located`      (the constitution's OBSERVATION)

The last row is the load-bearing one. An observation is still worth recording — it is what
hypotheses are made of — and recording it honestly at `Judged` is what stops it being cited later
as though it had gated something.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_DIR = REPO_ROOT / "measurements"

# Exactly one, always (MEASUREMENT_POLICY.md § Category). Conflating these is named there as the
# single most expensive recurring measurement defect in this project.
CATEGORIES = {"OPTIMUM", "BASELINE", "CANDIDATE"}

REQUIRED = ("measurement_id", "date", "metric", "value", "unit", "category", "claim")


class MeasurementError(ValueError):
    """A measurement record does not satisfy the constitution's claim grammar."""


def _fail(msg: str) -> None:
    raise MeasurementError(msg)


def validate(record: dict) -> None:
    """Refuse a record that cannot be graded honestly.

    Deliberately strict about `category` and lenient about `protocol_id`: a missing category is a
    defect, while a missing protocol is a legitimate and common state (an observation) that the
    grade must reflect rather than the validator reject.
    """
    if not isinstance(record, dict):
        _fail("measurement record must be a mapping")
    for key in REQUIRED:
        if key not in record:
            _fail(f"missing required field {key!r}")
        if isinstance(record[key], str) and not record[key].strip():
            _fail(f"required field {key!r} is present but empty")

    if record["category"] not in CATEGORIES:
        _fail(f"category must be exactly one of {sorted(CATEGORIES)} "
              f"(got {record['category']!r}) — see MEASUREMENT_POLICY.md § Category")

    if not isinstance(record["value"], (int, float, str)):
        _fail("value must be a number or a string carrying its own units")

    reps = record.get("reps")
    if reps is not None and (not isinstance(reps, int) or reps < 1):
        _fail("reps must be a positive integer when present")

    art = record.get("attestation")
    if art is not None:
        if not isinstance(art, dict) or not art.get("path"):
            _fail("attestation must be a mapping with at least a 'path'")
        digest = art.get("sha256")
        if digest is not None and not (isinstance(digest, str) and len(digest) == 64):
            _fail("attestation.sha256 must be a 64-character hex digest when present")


def artifact_exists(record: dict) -> bool:
    """True when the attestation names a file that is actually on disk.

    A hash over an artifact that no longer exists proves nothing — the constitution's own reason
    for making T3 require the artifact to be present and cited, not merely referenced.
    """
    art = record.get("attestation") or {}
    path = art.get("path")
    if not path:
        return False
    rel = PurePosixPath(str(path))
    # Containment is checked on the UNRESOLVED path: reject absolute paths and any `..` component.
    # Resolving first would follow `repos/epyc-orchestrator` out to its real location under
    # /mnt/raid0 (the working-tree symlink every repo here uses) and reject a legitimate sibling-repo
    # artifact as an escape, while `../../etc/passwd` is still caught by the `..` test.
    if rel.is_absolute() or ".." in rel.parts:
        return False
    return (REPO_ROOT / rel).is_file()


def grade(record: dict) -> tuple[str, str, list[str]]:
    """Return (Q, T, reasons) implementing the constitution's claim rule.

    `reasons` names every element of the tuple that is missing, so a low grade is self-explaining
    and nobody has to reverse-engineer why their measurement did not reach Witnessed.
    """
    reasons: list[str] = []

    has_protocol = bool(str(record.get("protocol_id") or "").strip())
    has_reps = record.get("reps") is not None
    has_date = bool(str(record.get("date") or "").strip())
    art = record.get("attestation") or {}
    has_ref = bool(art.get("path"))
    hashed = bool(art.get("sha256")) and artifact_exists(record)

    if not has_protocol:
        reasons.append("no protocol citation — this is an OBSERVATION, never decision-gating "
                       "(MEASUREMENT_POLICY.md § The claim rule)")
        return "Judged", ("Located" if has_ref else "T0"), reasons

    if not has_reps:
        reasons.append("no n/reps recorded")
    if not has_date:
        reasons.append("no date recorded")
    if not has_ref:
        reasons.append("no attestation reference — a result, but not decision-gating")
    elif not art.get("sha256"):
        reasons.append("attestation named but not hashed")
    elif not artifact_exists(record):
        reasons.append("attestation hashed but the artifact is not on disk — a hash over a file "
                       "that no longer exists proves nothing")

    full_tuple = has_protocol and has_reps and has_date and has_ref
    if not full_tuple:
        return "Verified", ("Located" if has_ref else "Located"), reasons
    if hashed:
        return "Witnessed", "Attested", reasons
    return "Witnessed", "Anchored", reasons


def record_path(date: str) -> Path:
    return LEDGER_DIR / f"{str(date)[:7]}.jsonl"


def append(record: dict, *, dry_run: bool = False) -> dict:
    """Validate, grade and append. Returns the stored record with its grade attached."""
    validate(record)
    q, t, reasons = grade(record)
    stored = dict(record)
    stored["grade"] = {"Q": q, "T": t}
    stored["grade_reasons"] = reasons
    stored["record_sha256"] = hashlib.sha256(
        json.dumps({k: v for k, v in record.items()}, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if not dry_run:
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        path = record_path(record["date"])
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(stored, sort_keys=True, ensure_ascii=False) + "\n")
    return stored


def load_all() -> list[dict]:
    if not LEDGER_DIR.exists():
        return []
    out: list[dict] = []
    for path in sorted(LEDGER_DIR.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def to_frames(record: dict, *, as_of: str) -> list[dict]:
    """Emit claim + supporting-evidence frames for one measurement."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from frames import make_frame  # noqa: PLC0415

    mid = record["measurement_id"]
    claim_id = f"clm_meas_{mid.replace('-', '_')}"
    source_id = f"src_meas_{mid.replace('-', '_')}"
    q, t, reasons = grade(record)
    art = record.get("attestation") or {}

    source = make_frame(
        frame_type="epyc.vidya/frame/source_observed/v1",
        assertion={
            "source_id": source_id,
            "locator": art.get("path") or f"measurement:{mid}",
            "source_kind": "measurement",
            "title": f"{record['metric']} ({record['category']})",
            "revision_observed": record.get("date"),
        },
        provenance={"method": "vidya.measurement_record/v1", "about": mid, "retrofit": False},
        actor="vidya.measurement_record/v1",
        authority_scope="measurement",
        created_at=as_of,
    )
    claim = make_frame(
        frame_type="epyc.vidya/frame/claim_proposed/v1",
        assertion={"claim_id": claim_id, "display_text": record["claim"], "source_id": source_id},
        provenance={"method": "vidya.measurement_record/v1", "derived_from": source_id,
                    "about": mid},
        actor="vidya.measurement_record/v1",
        authority_scope="measurement",
        created_at=as_of,
    )
    support = make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={
            "claim_id": claim_id,
            "evidence_id": f"evd_meas_{mid.replace('-', '_')}",
            "grade": {"Q": q, "T": t},
            "source_id": source_id,
            "protocol_id": record.get("protocol_id"),
            "reps": record.get("reps"),
            "category": record["category"],
        },
        provenance={
            "evidence": f"evd_meas_{mid.replace('-', '_')}",
            "about": claim_id,
            "method": "vidya.measurement_record/v1",
            "grade_reasons": reasons,
        },
        actor="vidya.measurement_record/v1",
        authority_scope="measurement",
        created_at=as_of,
    )
    return [source, claim, support]


def summary() -> dict[str, Any]:
    import collections

    records = load_all()
    grades = collections.Counter(f"{r['grade']['Q']}/{r['grade']['T']}"
                                 for r in records if r.get("grade"))
    cats = collections.Counter(r.get("category") for r in records)
    return {
        "records": len(records),
        "grades": dict(grades.most_common()),
        "categories": dict(cats.most_common()),
        "decision_gating": sum(1 for r in records
                               if (r.get("grade") or {}).get("Q") == "Witnessed"),
    }
