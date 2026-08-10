"""SC6: read the autopilot journal's write-time measurement tuple.

This is the read half of the SC6 hook. The write half lives in the orchestrator
(`scripts/autopilot/experiment_journal.py` → `measurement_tuple()`), which captures the
constitution's claim tuple at `record()` time so a trial is *born* attested. Nothing is
reconstructed here: this adapter reads the tuple the trial recorded about itself and grades it
with the same function every other measurement goes through.

**The grading logic deliberately lives in this repo, not in the orchestrator.** `MEASUREMENT.md`
and its digest are here, they are human-amendment-only, and a second implementation of the claim
rule sitting next to the autopilot would drift from them the first time either changed. So the
orchestrator records provenance and stays ignorant of grades; `measurement_record.grade()` remains
the single place that decides what warrant a number carries.

Two properties matter and are pinned by tests:

* **A row with no tuple is skipped, not back-filled.** Every trial before 2026-08-12 predates the
  hook. Inventing a protocol id for them would manufacture exactly the warrant this program exists
  to detect the absence of.
* **One claim per trial, keyed by shard and trial id.** Trial ids restart per shard file, so the
  bare id is not unique across a rotated journal — the same basename-collision shape that merged
  three A/B arms into one belief in the sealed-manifest adapter.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frames import make_frame  # noqa: E402
from measurement_record import grade  # noqa: E402

ADAPTER_ID = "vidya.adapters.autopilot_journal/v1"
AUTHORITY = "measurement"
REPO_ROOT = Path(__file__).resolve().parents[3]
ORCH_REL = "repos/epyc-orchestrator"
JOURNAL_GLOB = "orchestration/autopilot_journal*.jsonl"

FT_SOURCE = "epyc.vidya/frame/source_observed/v1"
FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"
FT_SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"


def shards(root: Path | None = None) -> list[Path]:
    base = (root or REPO_ROOT) / ORCH_REL
    return sorted(base.glob(JOURNAL_GLOB))


def iter_measured_rows(root: Path | None = None) -> Iterator[tuple[Path, dict]]:
    """Yield (shard, row) for trial rows that recorded a measurement tuple."""
    for shard in shards(root):
        with open(shard, errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict) or "trial_id" not in row:
                    continue
                meas = row.get("measurement")
                if isinstance(meas, dict) and meas and not meas.get("capture_error"):
                    yield shard, row


def as_record(shard: Path, row: dict) -> dict:
    """Shape a journal row into the record `measurement_record.grade()` consumes."""
    meas = row["measurement"]
    att = meas.get("attestation") or {}
    ident = f"{shard.stem}_{row['trial_id']}"
    basis = meas.get("reps_basis") or ""
    return {
        "measurement_id": ident,
        "date": meas.get("date") or "",
        "metric": "autopilot_trial_objectives",
        "value": row.get("quality", 0.0),
        "unit": "quality",
        # An autopilot trial is a CANDIDATE by construction: it is a proposed change being
        # measured, not a ratified optimum and not the standing baseline. Recording it as anything
        # else is the conflation MEASUREMENT_POLICY.md names as the costliest recurring defect here.
        "category": "CANDIDATE",
        "claim": (f"autopilot trial {row['trial_id']} ({row.get('action_type') or 'trial'}, "
                  f"species={row.get('species') or '?'}): quality={row.get('quality')}, "
                  f"speed={row.get('speed')}, cost={row.get('cost')}"),
        "protocol_id": meas.get("protocol_id") or "",
        "reps": meas.get("reps"),
        "reps_basis": basis,
        "attestation": {
            "path": f"{ORCH_REL}/orchestration/{shard.name}",
            "sha256": att.get("sha256"),
            "locator": att.get("locator") or "",
            "git_tag": att.get("git_tag") or "",
        },
    }


def frames_for_row(shard: Path, row: dict, *, as_of: str) -> list[dict]:
    rec = as_record(shard, row)
    q, t, reasons = grade(rec)
    ident = rec["measurement_id"]
    source_id = f"src_ap_{ident}"
    claim_id = f"clm_ap_{ident}"
    if rec.get("reps_basis", "").startswith("attempted"):
        # n counted what was attempted, not what scored. Stated so the number is not read as a
        # scored denominator later.
        reasons = [*reasons, f"n is the ATTEMPTED count ({rec['reps_basis']}), not the scored one"]
    return [
        make_frame(
            frame_type=FT_SOURCE,
            assertion={"source_id": source_id,
                       "locator": rec["attestation"]["locator"] or rec["attestation"]["path"],
                       "source_kind": "autopilot-trial",
                       "title": f"autopilot trial {row['trial_id']}",
                       "revision_observed": rec["date"]},
            provenance={"method": ADAPTER_ID, "about": ident, "retrofit": False},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
        ),
        make_frame(
            frame_type=FT_CLAIM,
            assertion={"claim_id": claim_id, "display_text": rec["claim"],
                       "source_id": source_id},
            provenance={"method": ADAPTER_ID, "derived_from": source_id, "about": ident},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
        ),
        make_frame(
            frame_type=FT_SUPPORT,
            assertion={"claim_id": claim_id, "evidence_id": f"evd_ap_{ident}",
                       "grade": {"Q": q, "T": t}, "source_id": source_id,
                       "protocol_id": rec["protocol_id"], "reps": rec["reps"],
                       "category": rec["category"]},
            provenance={"evidence": f"evd_ap_{ident}", "about": claim_id, "method": ADAPTER_ID,
                        "grade_reasons": reasons, "reps_basis": rec["reps_basis"]},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
        ),
    ]


def summarize(root: Path | None = None) -> dict:
    """Grade every measured row without emitting frames — the pricing view."""
    import collections

    grades = collections.Counter()
    basis = collections.Counter()
    total = 0
    for shard, row in iter_measured_rows(root):
        rec = as_record(shard, row)
        q, t, _ = grade(rec)
        grades[f"{q}/{t}"] += 1
        basis[rec["reps_basis"] or "none"] += 1
        total += 1
    return {"measured_rows": total, "grades": dict(grades.most_common()),
            "reps_basis": dict(basis.most_common())}


def emit(root: Path | None = None, *, as_of: str, limit: int | None = None) -> Iterable[dict]:
    for i, (shard, row) in enumerate(iter_measured_rows(root)):
        if limit is not None and i >= limit:
            return
        yield from frames_for_row(shard, row, as_of=as_of)


if __name__ == "__main__":
    print(json.dumps(summarize(), indent=2))
