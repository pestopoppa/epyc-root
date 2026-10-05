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

* **A row with no tuple is skipped, not back-filled.** Every trial before 2026-08-10 predates the
  hook. Inventing a protocol id for them would manufacture exactly the warrant this program exists
  to detect the absence of.
* **One claim per trial, keyed by shard and trial id.** Trial ids restart per shard file, so the
  bare id is not unique across a rotated journal — the same basename-collision shape that merged
  three A/B arms into one belief in the sealed-manifest adapter.
"""

from __future__ import annotations

import functools
import hashlib
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

# VB-AP-PROMO-RULE: decision fields the archive stage stamps into ``eval_details`` (orchestrator
# `scripts/autopilot/autopilot.py`, gate-frontier (b)+(c), on main since `a1a0251a`). Values are
# the writer's vocabulary, carried verbatim and never re-decided here:
#   promotion_rule     frontier | empty_frontier_repro | seed | archive_unavailable_no_baseline |
#                      refused_guard_unavailable  (safety_gate.py `_select_promotion_rule`)
#   promotion_status   pending_commit | refused   (present only when a promotion was decided)
#   frontier_admission representative            (absent unless the trial is a clean frontier point)
PROMOTION_FIELDS = ("promotion_rule", "promotion_status", "frontier_admission")
PROMOTION_PENDING = "pending_commit"
BASELINE_PROMOTION_EVENT = "baseline_promotion"
# AP-57 (orchestrator `01906607`): the `speed_axis_reseed` ledger event is deliberately NOT
# projected. It is a baseline_state receipt (the speed axis re-anchored on a refused promotion),
# not a measurement: the trial row it cites is already projected with its speed. It is never a
# promotion commit, and it is appended AFTER the row, so carrying it on the frame would need its
# own settle rule for every refused newest-trial row. The index below ignores it on purpose.


def shards(root: Path | None = None) -> list[Path]:
    base = (root or REPO_ROOT) / ORCH_REL
    return sorted(base.glob(JOURNAL_GLOB))


def iter_measured_rows(root: Path | None = None) -> Iterator[tuple[Path, dict]]:
    """Yield (shard, row) for trial rows that recorded a measurement tuple."""
    for shard in shards(root):
        yield from iter_shard_rows(shard)


def iter_shard_rows(shard: Path) -> Iterator[tuple[Path, dict]]:
    """The same filter as `iter_measured_rows`, over ONE journal shard file."""
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


def _attestation_verified(row: dict) -> bool:
    """SC69: re-derive the digest the trial writer computed over the entry's own content.

    The writer hashes ``entry minus measurement`` — a digest that covered the block it lives in
    could never be recomputed, so it would attest to nothing (experiment_journal.py). The row on
    disk is that entry after a JSON round trip, so the same canonical serialization re-derives
    the digest here; a row whose digest does not re-derive has been mutated since emit.
    """
    recorded = (row.get("measurement") or {}).get("attestation") or {}
    claimed = str(recorded.get("sha256") or "")
    if not claimed:
        return False
    payload = {k: v for k, v in row.items() if k != "measurement"}
    recomputed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return recomputed == claimed


def committed_promotions(shard: Path) -> frozenset[int]:
    """Source trial ids of the ``baseline_promotion`` ledger events in ONE shard.

    The writer journals a promoting trial as ``promotion_status="pending_commit"`` BEFORE the
    promotion commits; the commit record is the ledger event with that ``source_trial_id``,
    appended to the same shard with the final state save. A pending row without it must be read
    as NOT promoted (autopilot.py, re-review B3). Joined within the shard, because trial ids are
    only unique per shard.
    """
    return _shard_index(shard)[0]


def last_trial_id(shard: Path) -> int:
    """Highest trial id journaled in ONE shard (-1 when it holds none)."""
    return _shard_index(shard)[1]


def _shard_index(shard: Path) -> tuple[frozenset[int], int]:
    st = shard.stat()
    return _index_shard(str(shard), st.st_mtime_ns, st.st_size)


@functools.lru_cache(maxsize=16)
def _index_shard(path: str, _mtime_ns: int, _size: int) -> tuple[frozenset[int], int]:
    ids: set[int] = set()
    last = -1
    with open(path, errors="ignore") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(ev, dict):
                continue
            if "trial_id" in ev:
                try:
                    last = max(last, int(ev["trial_id"]))
                except (TypeError, ValueError):
                    pass
            elif ev.get("type") == BASELINE_PROMOTION_EVENT:
                try:
                    ids.add(int(ev.get("source_trial_id")))
                except (TypeError, ValueError):
                    continue
    return frozenset(ids), last


def promotion_unsettled(shard: Path, row: dict, decision: dict) -> bool:
    """A pending promotion on the shard's newest trial whose commit event may still be coming.

    The commit event is appended AFTER the row, so reading between the two would persist
    ``promotion_committed=False`` into an append-only ledger for a promotion that then commits.
    Such a row is not projected yet; once a later trial is journaled the state is final.
    """
    return (decision.get("promotion_status") == PROMOTION_PENDING
            and not decision["promotion_committed"]
            and int(row["trial_id"]) >= last_trial_id(shard))


def promotion_decision(shard: Path, row: dict) -> dict:
    """The promotion/frontier decision the trial row recorded, plus its commit state.

    Only keys the row actually carries are returned, so a row written before the fields existed
    projects byte-identical frames (never back-filled). ``promotion_committed`` is added only for
    a decided promotion: True when a ``pending_commit`` row has its ledger commit event, False
    otherwise (a ``refused`` row, or a pending row whose commit never landed).
    """
    ed = row.get("eval_details")
    if not isinstance(ed, dict):
        return {}
    out = {k: str(ed[k]) for k in PROMOTION_FIELDS if isinstance(ed.get(k), str) and ed[k]}
    if "promotion_status" in out:
        out["promotion_committed"] = (
            out["promotion_status"] == PROMOTION_PENDING
            and int(row["trial_id"]) in committed_promotions(shard))
    return out


#: AP-55-ARM (orchestrator ``cd79b80e``): what each BINDING mode would have held on the same legs,
#: recorded at write time in ``eval_details.ap55_promotion_gate`` (``gate_summary``).
AP55_COUNTERFACTUAL_FIELDS = (("would_hold_enforce", bool),
                              ("would_hold_enforce_reasons", list),
                              ("would_hold_strict", bool))


def _ap55_gate(raw, eval_details=None) -> dict:
    """The writer's AP-55 gate block, copied field by field; ``{}`` when absent.

    The shadow-mode counterfactual keys are copied verbatim from ``eval_details.ap55_promotion_gate``
    only when the row recorded them. They are never re-derived here: a row written before the
    counterfactual existed carries no such key, and ``ap55_shadow_review`` owns the reconstruction.
    """
    if not isinstance(raw, dict) or not raw:
        return {}
    out = {"mode": str(raw.get("mode") or ""),
           "seed_rerun": str(raw.get("seed_rerun") or ""),
           "batch_homogeneity": str(raw.get("batch_homogeneity") or ""),
           "hold": bool(raw.get("hold"))}
    summary = (eval_details or {}).get("ap55_promotion_gate") if isinstance(eval_details, dict) else None
    if isinstance(summary, dict):
        for key, typ in AP55_COUNTERFACTUAL_FIELDS:
            if isinstance(summary.get(key), typ):
                out[key] = list(summary[key]) if typ is list else summary[key]
    return out


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
        # Read from the tuple the trial recorded, not decided here — the writer owns the category,
        # and re-deciding it downstream is how two sources of truth start. Falls back to CANDIDATE
        # for rows written before the writer carried the field, which is what an autopilot trial
        # always is: a proposed change being measured, never the baseline and never a ratified
        # optimum. MEASUREMENT_POLICY.md names conflating those the costliest recurring defect here.
        "category": meas.get("category") or "CANDIDATE",
        "metric_direction": (meas.get("metric_directions") or {}).get("quality", "higher_better"),
        "claim": (f"autopilot trial {row['trial_id']} ({row.get('action_type') or 'trial'}, "
                  f"species={row.get('species') or '?'}): quality={row.get('quality')}, "
                  f"speed={row.get('speed')}, cost={row.get('cost')}"),
        "protocol_id": meas.get("protocol_id") or "",
        "reps": meas.get("reps"),
        "reps_basis": basis,
        # AP-55: the infra regime the trial ran in and its comparability with the baseline
        # reference, as RECORDED by the writer. Carried, never graded here: a NON_COMPARABLE
        # trial is annotated in the reasons, and the ladder in claim_tuple stays the one rule.
        # Empty on rows written before 2026-09-16 (never back-filled).
        "infra_fingerprint": str(meas.get("infra_fingerprint") or ""),
        "comparability": str(meas.get("comparability") or ""),
        # AP-55 (b)+(c): the promotion-gate legs as RECORDED by the writer — the same-regime
        # seed re-run verdict, the candidate-batch homogeneity verdict, the gate mode and
        # whether it held the promotion, plus the AP-55-ARM would_hold_* counterfactual when the
        # row recorded it. Carried, never graded. Empty on rows written before the gate existed
        # (never back-filled).
        "ap55_gate": _ap55_gate(meas.get("ap55_gate"), row.get("eval_details")),
        # AP-54: whether the eval rollouts ran behind the knowledge fence ("active" | "absent" |
        # "mixed"), as RECORDED by the writer from the API echo. Carried, never graded. Empty on
        # rows written before the fence existed, which must be read as unfenced.
        "eval_fence": str(meas.get("eval_fence") or ""),
        # AP-54 kernel enforcement level behind an active fence: landlock | mountns | hook-only.
        # Carried, never graded. Empty when the fence was not active or the row predates it.
        "eval_fence_enforcement": str(meas.get("eval_fence_enforcement") or ""),
        # AP-63(a): the AP-1510 run-manifest digest the trial was dispatched under, as RECORDED
        # by the writer (sources + task + evaluator). Carried, never graded. Empty on rows written
        # before 2026-09-17 and on rows that never dispatched (never back-filled).
        "run_manifest": str(meas.get("run_manifest") or ""),
        "attestation": {
            "path": f"{ORCH_REL}/orchestration/{shard.name}",
            "sha256": att.get("sha256"),
            "locator": att.get("locator") or "",
            "git_tag": att.get("git_tag") or "",
            # SC69: this reader re-derived the recorded digest over the entry's own content
            # (the writer's attestation semantics — not the shard bytes, which an append-only
            # journal can never pin). The verification result is carried in the record the
            # measurement ladder grades.
            "verified": True if _attestation_verified(row) else None,
        },
    }


def frames_for_row(shard: Path, row: dict, *, as_of: str) -> list[dict]:
    rec = as_record(shard, row)
    q, t, reasons = grade(rec)
    ident = rec["measurement_id"]
    decision = promotion_decision(shard, row)
    if promotion_unsettled(shard, row, decision):
        return []
    if decision.get("promotion_status") == PROMOTION_PENDING and not decision["promotion_committed"]:
        # Stated, not graded: the row claims a pending promotion that no ledger event commits.
        reasons = [*reasons, "promotion pending_commit has no baseline_promotion commit event: "
                             "read as NOT promoted"]
    source_id = f"src_ap_{ident}"
    claim_id = f"clm_ap_{ident}"
    if rec.get("reps_basis", "").startswith("attempted"):
        # n counted what was attempted, not what scored. Stated so the number is not read as a
        # scored denominator later.
        reasons = [*reasons, f"n is the ATTEMPTED count ({rec['reps_basis']}), not the scored one"]
    if rec["comparability"] and rec["comparability"] != "COMPARABLE":
        # Stated, not graded: the delta was measured against a baseline from a different (or
        # unverified) infra regime (AP-55).
        reasons = [*reasons, f"infra comparability vs baseline: {rec['comparability']}"]
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
                       "category": rec["category"],
                       "metric_direction": rec["metric_direction"],
                       "infra_fingerprint": rec["infra_fingerprint"],
                       "comparability": rec["comparability"],
                       "ap55_gate": rec["ap55_gate"],
                       "eval_fence": rec["eval_fence"],
                       "eval_fence_enforcement": rec["eval_fence_enforcement"],
                       "run_manifest": rec["run_manifest"],
                       # VB-AP-PROMO-RULE: carried verbatim, never graded; absent keys stay absent.
                       **decision},
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
    """Frames for every measured row. `root` is an epyc-root checkout, or one shard file."""
    rows = (iter_shard_rows(root) if root is not None and Path(root).is_file()
            else iter_measured_rows(root))
    for i, (shard, row) in enumerate(rows):
        if limit is not None and i >= limit:
            return
        yield from frames_for_row(shard, row, as_of=as_of)


if __name__ == "__main__":
    print(json.dumps(summarize(), indent=2))
