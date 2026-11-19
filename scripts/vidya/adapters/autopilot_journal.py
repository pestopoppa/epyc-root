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

from claim_tuple import ClaimTuple, ProjectionError  # noqa: E402
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
BELIEF_SCOPE_SCHEMA = "epyc.autopilot.belief_scope.v1"
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


def _w6_generalization(eval_details) -> dict | None:
    """Return the optional authored W6 diagnostic block, without interpreting it.

    The writer stores this under ``eval_details.details.w6_generalization``.  An absent or
    malformed outer shape stays absent; a producer-authored block is copied verbatim, including
    nullable measurements and its reason.  This support metadata is informational and never
    participates in ``grade()`` or promotion decisions.
    """
    if not isinstance(eval_details, dict):
        return None
    details = eval_details.get("details")
    if not isinstance(details, dict):
        return None
    report = details.get("w6_generalization")
    return dict(report) if isinstance(report, dict) else None


#: VB-AP-JOURNAL-CARRY: optional producer-authored fields, informational only. A missing, legacy
#: or malformed field stays ABSENT (read as UNKNOWN); nothing here reaches ``grade()``.
NON_LEARNING_REQUEST_SOURCES = frozenset({"smoke", "probe", "health"})
REWARD_EVENT_TYPES = frozenset({"memory_stored", "q_value_updated"})


def _json_text(value) -> str | None:
    """Deterministic JSON text (certified frames forbid floats); None when not serializable."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return None


def _accepted_warrant_telemetry(eval_details) -> dict | None:
    """``eval_details.details.accepted_warrant_telemetry`` (SG-W2), copied verbatim or absent."""
    if not isinstance(eval_details, dict):
        return None
    details = eval_details.get("details")
    if not isinstance(details, dict):
        return None
    block = details.get("accepted_warrant_telemetry")
    return dict(block) if isinstance(block, dict) and block else None


def progress_carry(progress_events: Iterable[dict] | None) -> dict:
    """Optional progress-log fields: TASK_STARTED ``request_source`` and the ``reward_provenance``
    block of MEMORY_STORED / Q_VALUE_UPDATED events (orchestrator ``ProgressEntry`` JSON shape).

    ``request_source`` is carried only for the producer's own non-learning vocabulary
    (smoke/probe/health); any other value is not copied. Returns only the keys that are present.
    """
    sources: list[dict] = []
    rewards: list[dict] = []
    for ev in progress_events or ():
        if not isinstance(ev, dict) or not isinstance(ev.get("data"), dict):
            continue
        kind, data = ev.get("event_type"), ev["data"]
        if kind == "task_started":
            rs = data.get("request_source")
            if isinstance(rs, str) and rs in NON_LEARNING_REQUEST_SOURCES:
                sources.append({"task_id": str(ev.get("task_id") or ""), "request_source": rs})
        elif kind in REWARD_EVENT_TYPES:
            prov = data.get("reward_provenance")
            if isinstance(prov, dict) and prov and _json_text(prov) is not None:
                rewards.append({"event_type": kind, "memory_id": str(ev.get("memory_id") or ""),
                                "reward_provenance": prov})
    out: dict = {}
    if sources:
        out["request_source_json"] = _json_text(sources)
    if rewards:
        out["reward_provenance_json"] = _json_text(rewards)
    return out


def _native_fingerprint_scope(row: dict) -> tuple[dict, str]:
    """P1-PHASE2: scope for a row that carries an AP-55 fingerprint but NO ``belief_scope``.

    Only what the row itself recorded: ``stack_regime`` is ``measurement.infra_fingerprint`` (the
    digest the writer stamps), and ``role_models`` is the role -> model file map of the row's own
    top-level ``infra_fingerprint.components.models.roles`` when that block is there (the same
    derivation the orchestrator's ``trial_belief_scope`` uses). ``config_key`` and
    ``knob_family`` are NOT derivable from a row without ``belief_scope`` (the action params are
    not on the row in the bridge's key shape), so they are absent, explicitly. A row with no
    fingerprint returns ``({}, "")``: no regime is ever invented, and never from the date.
    """
    digest = str((row.get("measurement") or {}).get("infra_fingerprint") or "").strip()
    if not digest:
        return {}, ""
    scope: dict = {"stack_regime": digest}
    fp = row.get("infra_fingerprint")
    roles = (((fp.get("components") or {}).get("models") or {}).get("roles")
             if isinstance(fp, dict) else None)
    if isinstance(roles, dict):
        role_models = {str(slot).split("@", 1)[0]: Path(str(r["model_path"])).name
                       for slot, r in roles.items()
                       if isinstance(r, dict) and r.get("model_path")}
        if role_models:
            scope["role_models"] = dict(sorted(role_models.items()))
    try:
        ClaimTuple(measurement_id="belief-scope-check", metric="belief_scope_check", value=0,
                   date="", category="CANDIDATE", claim="belief_scope check", applicability=scope)
    except ProjectionError as exc:
        return {}, f"fingerprint scope refused by the carrier ({exc}): not scoped"
    return scope, ""


def belief_scope_applicability(row: dict) -> tuple[dict, str]:
    """(applicability, refusal reason) from the row's top-level ``belief_scope`` (P1-M).

    The orchestrator writes ``belief_scope`` on trials from 2026-10-21 on (``trial_belief_scope``):
    the regime (the AP-55 ``infra_fingerprint`` digest), the role -> model_file map, the action's
    ``config_key`` and its knob families. It is carried as the source frame's applicability,
    inert to grading, exactly as recorded.

    NEVER back-filled (DESIGN 12.4): a row with no ``belief_scope`` returns ``({}, "")`` and
    projects the byte-identical frames it always did. A scope that is present but wrong -- another
    schema, no regime, a regime that disagrees with the row's own ``infra_fingerprint``, or one
    ``ClaimTuple`` refuses -- scopes NOTHING and returns the reason, which is stated in the
    evidence frame's grade reasons instead of being silently dropped.
    """
    raw = row.get("belief_scope")
    if not isinstance(raw, dict) or not raw:
        return _native_fingerprint_scope(row)
    if raw.get("schema") != BELIEF_SCOPE_SCHEMA:
        return {}, f"belief_scope schema is not {BELIEF_SCOPE_SCHEMA}: not scoped"
    regime = raw.get("stack_regime")
    if not isinstance(regime, str) or not regime.strip():
        return {}, "belief_scope names no stack_regime: not scoped"
    recorded = str((row.get("measurement") or {}).get("infra_fingerprint") or "")
    if recorded and recorded != regime:
        return {}, "belief_scope.stack_regime differs from the row's infra_fingerprint: not scoped"
    scope: dict = {"stack_regime": regime}
    for src, dst in (("role_models", "role_models"), ("config_key", "config_key"),
                     ("knob_families", "knob_family")):
        value = raw.get(src)
        if value in (None, "", [], {}):
            continue
        scope[dst] = value
    try:
        # The carrier owns the scope rules; validate by constructing, never by a second copy.
        ClaimTuple(measurement_id="belief-scope-check", metric="belief_scope_check", value=0,
                   date="", category="CANDIDATE", claim="belief_scope check", applicability=scope)
    except ProjectionError as exc:
        return {}, f"belief_scope refused by the carrier ({exc}): not scoped"
    return scope, ""


def as_record(shard: Path, row: dict) -> dict:
    """Shape a journal row into the record `measurement_record.grade()` consumes."""
    meas = row["measurement"]
    att = meas.get("attestation") or {}
    ident = f"{shard.stem}_{row['trial_id']}"
    basis = meas.get("reps_basis") or ""
    record = {
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
    warrant = _accepted_warrant_telemetry(row.get("eval_details"))
    if warrant is not None and _json_text(warrant) is not None:
        record["accepted_warrant_telemetry_json"] = _json_text(warrant)
    w6_generalization = _w6_generalization(row.get("eval_details"))
    if w6_generalization is not None:
        # Authored informational support only.  Do not derive a missing block from historical
        # row fields or allow this descriptive comparison to change the existing quality claim.
        record["w6_generalization"] = w6_generalization
    return record


def frames_for_row(shard: Path, row: dict, *, as_of: str,
                   progress_events: Iterable[dict] | None = None) -> list[dict]:
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
    scope, scope_refusal = belief_scope_applicability(row)
    if scope_refusal:
        reasons = [*reasons, scope_refusal]
    return [
        make_frame(
            frame_type=FT_SOURCE,
            assertion={"source_id": source_id,
                       "locator": rec["attestation"]["locator"] or rec["attestation"]["path"],
                       "source_kind": "autopilot-trial",
                       "title": f"autopilot trial {row['trial_id']}",
                       "revision_observed": rec["date"],
                       # P1-M: present only on a row that carried a valid belief_scope, so every
                       # earlier row keeps its byte-identical source frame.
                       **({"applicability": scope} if scope else {})},
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
                       # W6e diagnostic carry: optional, authored, descriptive only.  Missing
                       # legacy blocks stay absent and the shared grade above is unchanged.
                       # Certified frames forbid floats. Preserve the authored diagnostic
                       # as deterministic JSON text, not new numeric certified assertions.
                       **({"w6_generalization_json": json.dumps(
                           rec["w6_generalization"], sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)}
                          if "w6_generalization" in rec else {}),
                       # VB-AP-JOURNAL-CARRY: optional, informational, absent when not authored.
                       **({"accepted_warrant_telemetry_json": rec["accepted_warrant_telemetry_json"]}
                          if "accepted_warrant_telemetry_json" in rec else {}),
                       **progress_carry(progress_events),
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


def emit(root: Path | None = None, *, as_of: str, limit: int | None = None,
         progress_events: Iterable[dict] | None = None) -> Iterable[dict]:
    """Frames for every measured row. `root` is an epyc-root checkout, or one shard file."""
    progress_events = list(progress_events) if progress_events is not None else None
    rows = (iter_shard_rows(root) if root is not None and Path(root).is_file()
            else iter_measured_rows(root))
    for i, (shard, row) in enumerate(rows):
        if limit is not None and i >= limit:
            return
        yield from frames_for_row(shard, row, as_of=as_of, progress_events=progress_events)


# --- VB-AP70-ROTATION-READ ----------------------------------------------------------------------
# Strict reader for the AP-70 core-rotation observation records the orchestrator appends to the
# journal as ledger events (``scripts/autopilot/core_rotation_observation.py``, schema_version 1):
# plan -> boundary pin -> pair -> summary. Observe-only: the claim is projected through the shared
# ``ClaimTuple`` / ``grade()`` and nothing here adds a ladder, threshold, objective, baseline,
# archive, selection or promotion effect. No historical backfill: only records that are bound to a
# predeclared plan, in order, are read, and any drift refuses the whole study (no partial claim).

import math  # noqa: E402,F401  (kept local to this section)
import re  # noqa: E402

ROTATION_PLAN = "autopilot_core_rotation_observation_plan"
ROTATION_PIN = "autopilot_core_rotation_observation_boundary_pin"
ROTATION_PAIR = "autopilot_core_rotation_observation_pair"
ROTATION_SUMMARY = "autopilot_core_rotation_observation_summary"
ROTATION_TYPES = (ROTATION_PLAN, ROTATION_PIN, ROTATION_PAIR, ROTATION_SUMMARY)
ROTATION_SCHEMA_VERSION = 1
ROTATION_PROMPT_ACTIONS = ("prompt_mutation", "gepa_optimize")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_TOL = 1e-9


class RotationRefusal(ValueError):
    """A rotation record set that does not meet the strict contract; the study is not projected."""


def _refuse(msg: str):
    raise RotationRefusal(msg)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _need(cond: bool, msg: str) -> None:
    if not cond:
        _refuse(msg)


def rotation_events(shard: Path) -> list[dict]:
    """Rotation ledger events of ONE shard, in file order (torn lines skipped)."""
    out: list[dict] = []
    with open(shard, errors="ignore") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(ev, dict) and "trial_id" not in ev and ev.get("type") in ROTATION_TYPES:
                out.append(ev)
    return out


def _check_plan(plan: dict) -> tuple[int, int, dict[int, dict]]:
    _need(plan.get("schema_version") == ROTATION_SCHEMA_VERSION, "plan schema_version is not 1")
    _need(plan.get("authority") == "observe_only", "plan authority is not observe_only")
    _need(plan.get("metric") == "eval_result.quality"
          and plan.get("metric_direction") == "higher_is_better"
          and plan.get("drop_definition") == "q_outgoing_rotation - q_incoming_rotation",
          "plan metric/direction/drop definition drifted")
    k, period = plan.get("planned_k"), plan.get("rotation_period_trials")
    _need(_is_int(k) and k >= 1, "planned_k is not a positive integer")
    _need(_is_int(period) and period >= 1, "rotation period is not a positive integer")
    bounds = plan.get("planned_boundaries")
    _need(isinstance(bounds, list) and len(bounds) == k, "planned boundaries do not number K")
    by_id: dict[int, dict] = {}
    for i, b in enumerate(bounds):
        _need(isinstance(b, dict), "planned boundary is not a mapping")
        bid, out_i, in_i = (b.get("boundary_trial_id"), b.get("outgoing_rotation_index"),
                            b.get("incoming_rotation_index"))
        _need(all(_is_int(x) for x in (bid, out_i, in_i)), "planned boundary indices are not integers")
        _need(bid > 0 and bid % period == 0 and in_i == bid // period and out_i == in_i - 1,
              "planned boundary is not an exact rotation boundary")
        _need(i == 0 or bid == bounds[i - 1]["boundary_trial_id"] + period,
              "planned boundaries are not consecutive at the rotation period")
        by_id[bid] = b
    return k, period, by_id


def _check_identity(ident, *, where: str) -> None:
    _need(isinstance(ident, dict) and ident, f"{where}: incumbent identity missing")
    cfg = ident.get("config_snapshot")
    _need(isinstance(cfg, dict) and cfg.get("type") in ROTATION_PROMPT_ACTIONS,
          f"{where}: unsupported nonprompt incumbent")
    for key in ("prompt_tree_sha256", "request_prompt_tree_sha256", "checkpoint_metadata_sha256"):
        _need(isinstance(ident.get(key), str) and _HEX64.match(ident[key]),
              f"{where}: {key} missing or malformed")
    _need(ident["prompt_tree_sha256"] == ident["request_prompt_tree_sha256"],
          f"{where}: request prompt tree differs from the archived incumbent")
    for key in ("config_fingerprint", "checkpoint_target", "infra_digest"):
        _need(isinstance(ident.get(key), str) and ident[key], f"{where}: {key} missing")
    _need(_is_int(ident.get("trial_id")), f"{where}: incumbent trial id missing")
    for key in ("feature_flags", "infra_fingerprint", "evaluation_environment_identity"):
        _need(isinstance(ident.get(key), dict) and ident[key], f"{where}: {key} missing")
    served = ident.get("served_runtime_identity")
    _need(isinstance(served, dict) and served.get("status") == "observed"
          and isinstance(served.get("identity_sha256"), str)
          and _HEX64.match(served["identity_sha256"]),
          f"{where}: served-runtime identity missing or unobserved")


def _check_side(side, rotation: int, *, where: str) -> None:
    _need(isinstance(side, dict), f"{where}: result block missing")
    _need(side.get("rotation_index") == rotation, f"{where}: rotation index differs from plan")
    _need(_is_num(side.get("quality")), f"{where}: quality missing or nonfinite")
    n = side.get("n_questions")
    _need(_is_int(n) and n > 0 and side.get("n_questions_completed") == n
          and side.get("quality_denominator") == n, f"{where}: partial or unmatched denominator")
    sidecar = side.get("question_sidecar_persistence")
    _need(isinstance(sidecar, dict) and sidecar.get("archive_complete") is True,
          f"{where}: question sidecar missing or incomplete")
    for key in ("core_id", "dataset_sha256"):
        _need(isinstance(side.get(key), str) and side[key], f"{where}: {key} missing")
    for key in ("eval_wall_s", "sum_request_elapsed_s"):
        _need(_is_num(side.get(key)), f"{where}: timing {key} missing or nonfinite")


def _recompute_summary(k: int, planned_ids: list[int], pairs: list[dict]) -> dict:
    drops = [p["drop"] for p in pairs if p["status"] == "complete"]
    done = {p["boundary_trial_id"] for p in pairs if p["status"] == "complete"}
    if len(drops) != k or done != set(planned_ids):
        return {"status": "incomplete", "pairs_complete": len(drops), "mean_drop": None,
                "standard_error": None}
    mean = sum(drops) / k
    se = None
    if k >= 2:
        se = math.sqrt(sum((d - mean) ** 2 for d in drops) / (k - 1)) / math.sqrt(k)
    return {"status": "complete", "pairs_complete": k, "mean_drop": mean, "standard_error": se}


def read_rotation_study(events: list[dict], study_id: str) -> dict:
    """Bind one study's plan, boundary pins, pairs and final summary strictly, or raise
    ``RotationRefusal``. Returns ``{"plan", "pins", "pairs", "summary"}``."""
    mine = [(i, e) for i, e in enumerate(events) if e.get("study_id") == study_id]
    plans = [(i, e) for i, e in mine if e["type"] == ROTATION_PLAN]
    _need(len(plans) == 1, "study must have exactly one predeclared plan")
    plan_pos, plan = plans[0]
    k, period, bounds = _check_plan(plan)
    planned_ids = list(bounds)
    plan_ts = str(plan.get("timestamp") or "")

    def after_plan(pos: int, ev: dict, what: str) -> None:
        _need(pos > plan_pos, f"{what} precedes the predeclared plan")
        ts = str(ev.get("timestamp") or "")
        _need(not (ts and plan_ts and ts < plan_ts), f"{what} is older than the plan: historical")

    pins: dict[int, tuple[int, dict]] = {}
    for pos, ev in ((i, e) for i, e in mine if e["type"] == ROTATION_PIN):
        after_plan(pos, ev, "boundary pin")
        bid = ev.get("boundary_trial_id")
        b = bounds.get(bid) if _is_int(bid) else None
        _need(b is not None, "boundary pin names an unplanned boundary")
        _need(bid not in pins, "boundary has more than one pin")
        _need(ev.get("schema_version") == ROTATION_SCHEMA_VERSION, "pin schema_version is not 1")
        _need(ev.get("planned_k") == k and ev.get("rotation_period_trials") == period
              and ev.get("outgoing_rotation_index") == b["outgoing_rotation_index"]
              and ev.get("incoming_rotation_index") == b["incoming_rotation_index"],
              "boundary pin disagrees with the plan")
        status = ev.get("boundary_identity_status")
        if status == "verified":
            _check_identity(ev.get("identity"), where=f"pin {bid}")
        else:
            _need(status == "unavailable", "pin identity status is neither verified nor unavailable")
            _need(isinstance(ev.get("boundary_identity_reason"), str)
                  and ev["boundary_identity_reason"].strip(), "unavailable pin states no reason")
        pins[bid] = (pos, ev)

    pairs: dict[int, tuple[int, dict]] = {}
    for pos, ev in ((i, e) for i, e in mine if e["type"] == ROTATION_PAIR):
        after_plan(pos, ev, "pair")
        bid = ev.get("boundary_trial_id")
        b = bounds.get(bid) if _is_int(bid) else None
        _need(b is not None, "pair names an unplanned boundary: synthetic")
        _need(bid not in pairs, "boundary has more than one pair")
        _need(ev.get("schema_version") == ROTATION_SCHEMA_VERSION, "pair schema_version is not 1")
        _need(ev.get("outgoing_rotation_index") == b["outgoing_rotation_index"]
              and ev.get("incoming_rotation_index") == b["incoming_rotation_index"],
              "pair rotation indices differ from the plan")
        pin = pins.get(bid)
        _need(pin is not None and pin[0] < pos, "pair has no earlier boundary pin")
        pin_ev = pin[1]
        if ev.get("status") == "complete":
            _need(pin_ev.get("boundary_identity_status") == "verified",
                  "complete pair over an unverified pin")
            _check_identity(ev.get("incumbent"), where=f"pair {bid}")
            _need(ev["incumbent"] == pin_ev["identity"], f"pair {bid}: identity drift from its pin")
            _need(ev.get("metric") == "eval_result.quality"
                  and ev.get("metric_direction") == "higher_is_better",
                  "pair metric or direction drifted")
            _check_side(ev.get("outgoing"), b["outgoing_rotation_index"], where=f"pair {bid} outgoing")
            _check_side(ev.get("incoming"), b["incoming_rotation_index"], where=f"pair {bid} incoming")
            o, n_ = ev["outgoing"], ev["incoming"]
            _need(o["n_questions"] == n_["n_questions"], f"pair {bid}: matched denominator differs")
            _need(o["core_id"] != "" and o["dataset_sha256"] == n_["dataset_sha256"],
                  f"pair {bid}: draws are not from one dataset")
            _need(ev.get("q_outgoing") == o["quality"] and ev.get("q_incoming") == n_["quality"],
                  f"pair {bid}: q values differ from the draw results")
            _need(_is_num(ev.get("drop")) and abs(ev["drop"] - (o["quality"] - n_["quality"])) <= _TOL,
                  f"pair {bid}: drop is not q_outgoing - q_incoming")
            arts = ev.get("question_result_artifacts")
            _need(isinstance(arts, list) and len(arts) == 2
                  and all(isinstance(a, str) and a for a in arts), f"pair {bid}: sidecar paths missing")
            tc = ev.get("timing_cost")
            _need(isinstance(tc, dict) and all(_is_num(tc.get(x)) for x in
                  ("outgoing_eval_wall_s", "incoming_eval_wall_s", "sum_request_elapsed_s"))
                  and tc.get("n_questions") == o["n_questions"] + n_["n_questions"],
                  f"pair {bid}: timing/cost missing or inconsistent")
        else:
            _need(ev.get("status") == "incomplete", "pair status is neither complete nor incomplete")
            _need(isinstance(ev.get("reason"), str) and ev["reason"].strip(),
                  "incomplete pair states no reason")
            _need(ev.get("q_outgoing") is None and ev.get("q_incoming") is None
                  and ev.get("drop") is None, "incomplete pair carries a value")
        pairs[bid] = (pos, ev)

    summaries = [(i, e) for i, e in mine if e["type"] == ROTATION_SUMMARY]
    _need(summaries, "study has no summary")
    sum_pos, summary = summaries[-1]
    _need(summary.get("schema_version") == ROTATION_SCHEMA_VERSION, "summary schema_version is not 1")
    _need(all(pos < sum_pos for pos, _ in pairs.values()), "summary precedes a recorded pair: stale")
    _need(summary.get("planned_k") == k and summary.get("planned_boundary_trial_ids") == planned_ids,
          "summary disagrees with the plan")
    plist = [ev for _, ev in pairs.values()]
    exp = _recompute_summary(k, planned_ids, plist)
    _need(summary.get("status") == exp["status"], "summary status does not re-derive from the pairs")
    _need(summary.get("pairs_recorded") == len(plist) and summary.get("pairs_complete") == exp["pairs_complete"],
          "summary pair counts do not re-derive")
    for key in ("mean_drop", "standard_error"):
        got, want = summary.get(key), exp[key]
        if want is None:
            _need(got is None, f"summary {key} must be null (incomplete plan or K=1)")
        else:
            _need(_is_num(got) and abs(got - want) <= _TOL, f"summary {key} does not re-derive")
    return {"plan": plan, "pins": [e for _, e in pins.values()], "pairs": plist,
            "summary": summary}


def rotation_study_ids(events: list[dict]) -> list[str]:
    return sorted({str(e.get("study_id")) for e in events if e.get("type") == ROTATION_PLAN
                   and isinstance(e.get("study_id"), str) and e["study_id"]})


def _study_slug(study_id: str) -> str:
    return hashlib.sha256(study_id.encode("utf-8")).hexdigest()[:12]


def rotation_frames(shard: Path, study: dict, *, as_of: str) -> list[dict]:
    """Source / claim / support frames for ONE validated study's summary claim."""
    plan, summary = study["plan"], study["summary"]
    study_id = plan["study_id"]
    ident = f"{shard.stem}_ap70_{_study_slug(study_id)}"
    complete = summary["status"] == "complete"
    mean, se = summary["mean_drop"], summary["standard_error"]
    summary_sha = hashlib.sha256(json.dumps(summary, sort_keys=True, default=str,
                                            allow_nan=False).encode("utf-8")).hexdigest()
    k = plan["planned_k"]
    claim_text = (
        f"AP-70 core-rotation observation {study_id}: K={k} planned boundaries, "
        + (f"mean drop (q_outgoing - q_incoming) = {mean} over {k} matched boundaries, "
           f"SE={se if se is not None else 'null (K=1)'}; positive means worse quality on the "
           "incoming draw; observation only, no generalization-drop claim"
           if complete else
           f"INCOMPLETE ({summary['pairs_complete']}/{k} matched pairs); no final mean"))
    record = {
        "measurement_id": ident,
        "date": str(summary.get("timestamp") or plan.get("timestamp") or "")[:10],
        "metric": "autopilot_core_rotation_drop",
        "value": mean if complete else "incomplete",
        "unit": "quality",
        "category": "CANDIDATE",
        "metric_direction": "lower_better",
        "claim": claim_text,
        "protocol_id": "",
        "reps": k if complete else None,
        "reps_basis": "scored:matched_boundaries" if complete else "",
        "attestation": {"path": f"{ORCH_REL}/orchestration/{shard.name}", "sha256": summary_sha,
                        "locator": f"{shard.name}#ap70-study-{_study_slug(study_id)}",
                        "git_tag": "", "verified": None},
    }
    q, t, reasons = grade(record)
    study_json = json.dumps(
        {"plan": plan, "boundary_pins": study["pins"], "pairs": study["pairs"], "summary": summary},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    source_id, claim_id = f"src_ap70_{ident}", f"clm_ap70_{ident}"
    return [
        make_frame(
            frame_type=FT_SOURCE,
            assertion={"source_id": source_id, "locator": record["attestation"]["locator"],
                       "source_kind": "autopilot-core-rotation-study",
                       "title": f"AP-70 rotation study {study_id}",
                       "revision_observed": record["date"]},
            provenance={"method": ADAPTER_ID, "about": ident, "retrofit": False},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of),
        make_frame(
            frame_type=FT_CLAIM,
            assertion={"claim_id": claim_id, "display_text": claim_text, "source_id": source_id},
            provenance={"method": ADAPTER_ID, "derived_from": source_id, "about": ident},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of),
        make_frame(
            frame_type=FT_SUPPORT,
            assertion={"claim_id": claim_id, "evidence_id": f"evd_ap70_{ident}",
                       "grade": {"Q": q, "T": t}, "source_id": source_id,
                       "protocol_id": "", "reps": record["reps"], "category": "CANDIDATE",
                       "metric_direction": "lower_better",
                       "rotation_study_status": summary["status"],
                       "rotation_study_json": study_json},
            provenance={"evidence": f"evd_ap70_{ident}", "about": claim_id, "method": ADAPTER_ID,
                        "grade_reasons": reasons, "reps_basis": record["reps_basis"]},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of),
    ]


def emit_rotation(root: Path | None = None, *, as_of: str) -> tuple[list[dict], list[dict]]:
    """(frames, refusals) for every rotation study in the journal shards (opt-in, read-only).

    A study that fails the strict contract yields a refusal record and NO frames. ``emit`` never
    calls this, so default behaviour is unchanged.
    """
    shard_list = [Path(root)] if root is not None and Path(root).is_file() else shards(root)
    frames: list[dict] = []
    refusals: list[dict] = []
    for shard in shard_list:
        events = rotation_events(shard)
        for study_id in rotation_study_ids(events):
            try:
                frames.extend(rotation_frames(shard, read_rotation_study(events, study_id),
                                              as_of=as_of))
            except RotationRefusal as exc:
                refusals.append({"shard": shard.name, "study_id": study_id, "reason": str(exc)})
    return frames, refusals


if __name__ == "__main__":
    print(json.dumps(summarize(), indent=2))
