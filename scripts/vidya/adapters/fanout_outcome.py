"""SC62 — project FM-5 fan-out outcome accounting into the belief kernel.

FM-5 (`scripts/coordination/fanout_timing.py`, landed 2026-09-07 at `5f1c4ba4`) walks
Claude and Codex session transcripts and assigns every subagent an outcome bucket, an
`outcome_basis` naming the signal that decided it, and a token block. The corpus
(`data/fanout_timing/merged.v2.jsonl`, 14,004 workflows / 4,278 classified subagents) is
committed. This module is the READ side only: it never invokes and never modifies the
collector (D9-gated), it re-derives the aggregate from the committed corpus bytes, and it
PROJECTS — `claim_tuple.grade()` decides (spec §4.7). No ladder is registered.

WHY THIS FILE IS MOSTLY ABOUT BOUNDS
------------------------------------
The headline a reader takes from the FM-5 report is "86.5% of fan-out tokens went to work
that was never used". That number is real and it is also, on its own, a **stronger claim
than the measurement made**. Four separate reasons, each of which the projection has to
carry or it is lying:

1. **`produced-and-used` is an UPPER bound on usefulness.** 2,094 of its 2,265 verdicts
   rest on `parent-reference` — a substring of the child's output appearing in the parent
   transcript after the child finished. That is evidence the parent *saw* the output, not
   that it *used* it. The proven floor is `git-landed` = 171 subagents whose own mutated
   paths were committed. So "waste" is a BAND: at least 40.0% and at most 95.5% of known
   subagents, and the two ends rest on different evidence, not on different confidence.

2. **`blocked = 0` is a FLOOR, not a finding.** The collector's own docstring says so:
   neither transcript format carries a general "I was blocked" marker, so a subagent that
   wrote a blocked report in prose lands in `produced-and-discarded`. Zero observed
   blockers bounds the true count from below and not at all from above.

3. **Token totals are provider-cumulative and violently skewed.** Both backends re-charge
   the resent prefix every turn, so a long thread inflates; measured on this corpus the
   Codex median subagent is ~1.27M tokens and the p90 is ~1.68B — three orders of
   magnitude. A token share and a head-count share are therefore **different claims about
   different things**, and they are projected as different claims with different ids.

4. **501 `unknown` subagents stay UNFOLDED.** Their used/discarded split is not observable
   (the parent transcript is missing, or the parent mention index hit its byte cap before
   the child's window). They are held out of every denominator, reported as their own
   census claim, and never merged into a bucket. Folding an unknown into a bucket is
   precisely the failure FM-5 was built to prevent, and it would be perverse for its
   belief-kernel adapter to commit it.

THE DESIGN DECISION — separate claims, each of which IS a band
--------------------------------------------------------------
Two questions, answered separately:

*Why separate tuples per quantity, rather than one tuple?* Because they are separate
CLAIMS. `to_frames` derives `claim_id` from `measurement_id`, so one tuple is one citable,
retractable belief; bundling head-count and token waste into one would make it impossible
to cite the one you meant, impossible to retract one without the other, and would force a
single `metric` and `metric_direction` onto quantities that share neither.

*Why is the band IN the tuple's fields, rather than a companion "bounds" tuple beside a
"point estimate" tuple?* Because a companion tuple can be dropped on the floor. A consumer
that reads the point tuple and never the bound tuple reproduces exactly the lie above, and
nothing in the carrier would stop it. Coupling them makes the bound non-optional:

  * `ClaimTuple.value` is a :class:`Bound`, never a scalar. It has no `__float__`, no
    `__index__`, no `__iter__` and no `.point` — the attribute exists solely to RAISE, so
    the obvious attempt fails loudly instead of silently returning `low`. Getting a number
    out requires naming `.low` or `.high`, which is naming which end of the band you mean.
  * `claim` text is GENERATED from the bound (`Bound.render()`), never hand-written, and
    `_require_bounded` refuses any tuple whose claim text does not contain the rendered
    bound. `to_frames` puts `claim` into `display_text` and does NOT emit `value`, so the
    claim text is the only path the number takes into the ledger — which is why the guard
    is on the text and the test asserts against the emitted FRAME, not just the tuple.
  * `extra` carries `bound_low` / `bound_high` / `bound_kind` / the two bases, checked
    against the same object, for machine consumers.

CAN THIS SOURCE REACH `Witnessed`? NO — and that is the honest answer, not a gap.
--------------------------------------------------------------------------------
The constitution's claim rule wants a protocol id, n/reps, a date and durable attestation.
This source has three of the four, genuinely:

  n/reps        4,278 subagents classified from 14,004 workflows — a real scored n.
  date          the corpus's own latest observed event (`collected_at`), a corpus
                property rather than a wall clock, by the collector's design.
  attestation   `data/fanout_timing/merged.v2.jsonl` is committed and on disk; the
                projection hashes the file bytes and additionally pins `collector_sha256`,
                the digest of the classifier source that produced every verdict.

It does not have a protocol id, and none is invented here. `measurement/protocols/` holds
six codified protocols and none covers transcript forensics; `fanout_timing.v2` is the
SCHEMA VERSION OF THE OUTPUT RECORD, not a replayable measurement procedure. The
distinction is load-bearing rather than pedantic: the collector is deterministic over a
FIXED corpus, but its inputs are live session transcripts outside any git tree that grow,
rotate and disappear, so the measurement is not re-derivable by a third party — which is
what a protocol citation is supposed to promise. The SC19 precedent (native schema version
as protocol id) applies to producers whose runs execute under a codified capture protocol;
there is no such protocol here to name.

So `protocol_id` is left empty, the shared ladder returns `Judged/Located` for every tuple
this adapter emits, and these are recorded as OBSERVATIONS — never decision-gating. That
is the correct grade for a forensic walk over ephemeral transcripts, and it is what stops
"86.5% of fan-out tokens are wasted" being cited later as though it had gated something.
The attestation hash is carried anyway, so if a fan-out forensics protocol is ever
codified the same corpus lifts without re-projection.

DELIBERATELY NOT PROJECTED, named rather than silently skipped (the README convention):
the FM-6 orphan rate (35.0%). It is a real measurement in the same corpus and carries its
own documented bound direction — Codex `written_paths` is a lower bound because shell
redirects and heredocs are not parsed, making the Codex orphan rate an UPPER bound — but it
is a different phenomenon (output linkage) from outcome accounting, and SC62 scopes the
latter. File it before projecting it.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.fanout_outcome/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "fanout-outcome-accounting"

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORPUS = REPO_ROOT / "data" / "fanout_timing" / "merged.v2.jsonl"

#: The collector's own schema tag. Recorded as provenance in `extra`; NEVER promoted to
#: `protocol_id` — see the module docstring. A schema version says what shape the output
#: has, not what procedure produced it.
CORPUS_SCHEMA = "fanout_timing.v2"

#: Mirrors `fanout_timing.OUTCOME_BUCKETS` in ladder order. Mirrored rather than imported:
#: `scripts/coordination` is D9-gated and this module must not import from it, and a
#: silent drift in the bucket set would change every denominator here. So drift is made
#: LOUD instead — an unrecognised bucket refuses the whole corpus (`_bucket_counts`).
OUTCOME_BUCKETS = (
    "produced-and-used",
    "produced-and-discarded",
    "no-output",
    "blocked",
    "aborted",
    "unknown",
)

#: The only basis on which "this subagent's work was used" is PROVEN: a path the subagent
#: itself mutated was touched by a commit at or after it finished. Everything else in the
#: `produced-and-used` bucket rests on a substring hit in the parent transcript.
PROVEN_USED_BASIS = "git-landed"

#: The bucket whose used/discarded split is not observable. Held out of every denominator
#: and never folded.
UNKNOWN_BUCKET = "unknown"

#: The scope sentence that rides verbatim in every claim this adapter emits. `_require_bounded`
#: refuses a tuple whose claim omits it, so it cannot be lost in an edit.
SCOPE_LIMIT = (
    "SCOPE: a forensic walk over session transcripts, with NO codified protocol — an "
    "OBSERVATION, never decision-gating. Every figure is a BOUND, never a point estimate."
)

_QUANTITIES = (
    "headcount_waste",
    "token_waste_total",
    "token_waste_new",
    "blocked_floor",
    "unknown_census",
)

_INTERVAL, _FLOOR, _CENSUS = "interval", "floor", "census"
_BOUND_KINDS = frozenset({_INTERVAL, _FLOOR, _CENSUS})


class BoundReadError(ProjectionError):
    """Someone tried to read a point estimate out of a bounded quantity."""


@dataclass(frozen=True)
class Bound:
    """A measured quantity together with what bounds it. There is no unbounded reading.

    Three kinds, and the kind is part of the assertion:

      ``interval``  both ends are known and rest on DIFFERENT EVIDENCE. `low_basis` and
                    `high_basis` say which, because "40% to 95%" is not a confidence
                    interval — it is the gap between what was proven and what was merely
                    observed, and a reader who mistakes it for noise will average it.
      ``floor``     `high is None`. The quantity is bounded from below and NOT from above,
                    and `high_basis` states why no upper bound exists.
      ``census``    `low == high`. An exact count, where the exactness IS the claim.

    The class deliberately offers no way to collapse itself. `float()`, `int()`, iteration
    and `.point` all raise; only `.low` and `.high` return numbers, and naming one of them
    is naming which end of the band you are quoting.
    """

    low: float
    high: float | None
    kind: str
    unit: str
    low_basis: str
    high_basis: str

    def __post_init__(self) -> None:
        if self.kind not in _BOUND_KINDS:
            raise ProjectionError(
                f"bound kind must be one of {sorted(_BOUND_KINDS)} (got {self.kind!r})")
        if not str(self.unit or "").strip():
            raise ProjectionError("a bound without a unit is not a measurement")
        for name in ("low_basis", "high_basis"):
            if not str(getattr(self, name) or "").strip():
                raise ProjectionError(
                    f"{name} is required — a bound whose ends rest on unnamed evidence "
                    "reads as a confidence interval, which is a different claim")
        if self.kind == _FLOOR:
            if self.high is not None:
                raise ProjectionError("a floor has no upper bound; pass high=None")
        else:
            if self.high is None:
                raise ProjectionError(f"kind={self.kind!r} requires an upper bound")
            if self.high < self.low:
                raise ProjectionError(f"upper bound {self.high} is below lower {self.low}")
            if self.kind == _CENSUS and self.high != self.low:
                raise ProjectionError(
                    "a census is exact: low and high must be equal, or it is an interval")

    # --- the refusals. Present so the obvious attempts fail LOUDLY rather than quietly
    # returning `low` and reintroducing the point estimate this class exists to prevent.

    @property
    def point(self) -> float:
        raise BoundReadError(
            f"{self.render()} — this quantity has no point estimate. Read `.low` or "
            "`.high` and say which bound you are quoting (SC62)")

    def __float__(self) -> float:
        raise BoundReadError(
            f"{self.render()} — refusing to collapse a bound to one number; read `.low` "
            "or `.high` (SC62)")

    __index__ = __float__

    def __iter__(self):
        raise BoundReadError(
            f"{self.render()} — refusing to unpack a bound into a bare pair; read `.low` "
            "and `.high` by name so the reader sees which is which (SC62)")

    # --- rendering. Every claim text is built from this, never written by hand.

    def _fmt(self, value: float) -> str:
        if self.unit.startswith("share_"):
            return f"{value * 100:.1f}%"
        return f"{value:,.0f}"

    def render(self) -> str:
        """The human form. Both ends, with the evidence each rests on, always."""
        if self.kind == _FLOOR:
            return (f"AT LEAST {self._fmt(self.low)} ({self.low_basis}); NO UPPER BOUND "
                    f"({self.high_basis})")
        if self.kind == _CENSUS:
            return f"EXACTLY {self._fmt(self.low)} ({self.low_basis})"
        return (f"BAND {self._fmt(self.low)} to {self._fmt(self.high)} — "
                f"lower end: {self.low_basis}; upper end: {self.high_basis}")

    def as_extra(self) -> dict[str, Any]:
        return {
            "bound_kind": self.kind,
            "bound_low": self.low,
            "bound_high": self.high,
            "bound_unit": self.unit,
            "bound_low_basis": self.low_basis,
            "bound_high_basis": self.high_basis,
        }


# --- reading the corpus -----------------------------------------------------------------


def _iter_subagents(records: Sequence[Mapping[str, Any]]) -> Iterator[Mapping[str, Any]]:
    for record in records:
        subs = record.get("subagents")
        if isinstance(subs, list):
            for sub in subs:
                if isinstance(sub, Mapping):
                    yield sub


def _bucket_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Re-derive the aggregate from the corpus bytes. Absence is recorded, never filled.

    A subagent with no `outcome` is SKIPPED and counted in `skipped_no_outcome` — that is
    every schema-v1 row, which predates FM-5 and carries no verdict at all. Back-filling
    one would claim a classification the walk never made (§4.7), and quietly dropping it
    would make the skip invisible in the denominators it changed.

    An UNRECOGNISED bucket is a different failure and gets a different answer: it means
    the collector's ladder grew a bucket this mirror does not know, so every share
    computed here is silently wrong. That refuses the whole corpus rather than degrading.
    """
    counts = {bucket: 0 for bucket in OUTCOME_BUCKETS}
    tokens_total = {bucket: 0 for bucket in OUTCOME_BUCKETS}
    tokens_new = {bucket: 0 for bucket in OUTCOME_BUCKETS}
    proven_used = {"count": 0, "total": 0, "new": 0}
    skipped = 0
    per_subagent_total: list[int] = []

    for sub in _iter_subagents(records):
        bucket = sub.get("outcome")
        if bucket is None or not str(bucket).strip():
            skipped += 1
            continue
        if bucket not in counts:
            raise ProjectionError(
                f"unrecognised outcome bucket {bucket!r} — this adapter mirrors "
                f"{CORPUS_SCHEMA}'s bucket set {list(OUTCOME_BUCKETS)}; a bucket it does "
                "not know silently changes every denominator it computes, so the corpus "
                "is refused rather than projected against a stale mirror")
        tok = sub.get("tokens") if isinstance(sub.get("tokens"), Mapping) else {}
        total = int(tok.get("total") or 0)
        fresh = int(tok.get("new") or 0)
        counts[bucket] += 1
        tokens_total[bucket] += total
        tokens_new[bucket] += fresh
        per_subagent_total.append(total)
        if sub.get("outcome_basis") == PROVEN_USED_BASIS:
            proven_used["count"] += 1
            proven_used["total"] += total
            proven_used["new"] += fresh

    return {
        "counts": counts,
        "tokens_total": tokens_total,
        "tokens_new": tokens_new,
        "proven_used": proven_used,
        "skipped_no_outcome": skipped,
        "per_subagent_total": per_subagent_total,
    }


def _percentile(values: Sequence[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * pct))))
    return ordered[idx]


def read_corpus(corpus_path: str | Path = DEFAULT_CORPUS) -> dict[str, Any] | None:
    """Load and aggregate one FM-5 corpus file. Returns None when there is nothing to project.

    Two identity refusals, both of the fake-identity class this substrate exists to catch:

    * a corpus carrying more than one `collector_sha256` merges verdicts from two DIFFERENT
      classifiers into one claim, and the resulting share belongs to neither;
    * a corpus carrying a schema other than `fanout_timing.v2` in a v2 row is not the record
      this projection was written against.

    A corpus in which NO subagent carries an outcome projects zero rows — the pre-hook
    precedent (DF2-4, CT-1): never reconstructed on read.
    """
    path = Path(corpus_path).resolve()
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    records: list[Mapping[str, Any]] = []
    for line in raw.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, Mapping):
            records.append(record)
    if not records:
        return None

    collectors = {str(r.get("collector_sha256") or "") for r in records}
    collectors.discard("")
    if len(collectors) > 1:
        raise ProjectionError(
            f"corpus {path} carries {len(collectors)} distinct collector_sha256 values — "
            "the verdicts were produced by different classifiers and a share computed "
            "across them belongs to neither. Project each collector's corpus separately")

    agg = _bucket_counts(records)
    counts = agg["counts"]
    classified = sum(counts.values())
    if classified == 0:
        return None

    known = classified - counts[UNKNOWN_BUCKET]
    if known == 0:
        return None

    dates = sorted(str(r.get("collected_at") or "") for r in records)
    dates = [d for d in dates if d]
    per_sub = agg["per_subagent_total"]

    # In-tree corpora carry a REPO-RELATIVE path, so the shared ladder's `artifact_present`
    # can resolve it (and so the locator stays stable across working trees); an out-of-tree
    # corpus keeps its absolute path and the ladder will correctly refuse to find it.
    try:
        corpus_ref = str(path.relative_to(REPO_ROOT))
    except ValueError:
        corpus_ref = str(path)

    return {
        "corpus_path": corpus_ref,
        "corpus_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_present": path.is_file(),
        "collector_sha256": next(iter(collectors), ""),
        "schemas": sorted({str(r.get("schema") or "") for r in records}),
        "workflows": len(records),
        "classified": classified,
        "known": known,
        "counts": counts,
        "tokens_total": agg["tokens_total"],
        "tokens_new": agg["tokens_new"],
        "proven_used": agg["proven_used"],
        "skipped_no_outcome": agg["skipped_no_outcome"],
        "date": (dates[-1][:10] if dates else ""),
        "token_p50": _percentile(per_sub, 0.50),
        "token_p90": _percentile(per_sub, 0.90),
    }


# --- the native rows: one per QUANTITY, because these are different claims ---------------


def _identity(corpus: Mapping[str, Any], quantity: str) -> str:
    return f"fanout_{quantity}_{corpus['corpus_sha256'][:12]}"


def _skip_note(corpus: Mapping[str, Any]) -> str:
    skipped = corpus["skipped_no_outcome"]
    if not skipped:
        return ""
    return (f" {skipped} subagent(s) carry no outcome at all (pre-FM-5 schema) and are "
            "SKIPPED, never back-filled.")


def _unknown_note(corpus: Mapping[str, Any]) -> str:
    unknown = corpus["counts"][UNKNOWN_BUCKET]
    return (f" {unknown} of {corpus['classified']} classified subagents are `unknown` "
            "(the used/discarded split is not observable) and are held OUT of this "
            "denominator, never folded into a bucket.")


def native_rows(corpus_path: str | Path = DEFAULT_CORPUS) -> tuple[dict[str, Any], ...]:
    """One native row per bounded quantity. Zero rows when the corpus projects nothing."""
    corpus = read_corpus(corpus_path)
    if corpus is None:
        return ()
    return tuple({"corpus": corpus, "quantity": quantity} for quantity in _QUANTITIES)


def _headcount_waste(corpus: Mapping[str, Any]) -> tuple[Bound, str, int, str, str]:
    known = corpus["known"]
    used_observed = corpus["counts"]["produced-and-used"]
    used_proven = corpus["proven_used"]["count"]
    bound = Bound(
        low=(known - used_observed) / known,
        high=(known - used_proven) / known,
        kind=_INTERVAL,
        unit="share_of_known_subagents",
        low_basis=(f"{used_observed} of {known} known subagents landed in "
                   "`produced-and-used`, which is an UPPER bound on usefulness — "
                   f"{used_observed - used_proven} of them rest on `parent-reference`, a "
                   "substring of the child's output appearing in the parent transcript, "
                   "which is evidence the parent SAW the output, not that it USED it"),
        high_basis=(f"only {used_proven} subagents are proven used by `{PROVEN_USED_BASIS}` "
                    "— a path the subagent itself MUTATED was committed at or after it "
                    "finished. That is the floor under usefulness, hence the ceiling on "
                    "waste"),
    )
    return (
        bound,
        "fanout_subagent_waste_share",
        known,
        (f"scored:known_subagents ({corpus['classified']} classified - "
         f"{corpus['counts'][UNKNOWN_BUCKET]} unknown, held out and never folded)"),
        ("This is a claim about SUBAGENT COUNTS. The token share is a different claim "
         "about a different thing and must not be quoted for this one." + _unknown_note(corpus)
         + _skip_note(corpus)),
    )


def _token_waste(corpus: Mapping[str, Any], basis: str) -> tuple[Bound, str, int, str, str]:
    key = "tokens_total" if basis == "total" else "tokens_new"
    buckets = corpus[key]
    known_tokens = sum(v for b, v in buckets.items() if b != UNKNOWN_BUCKET)
    if known_tokens == 0:
        raise ProjectionError(
            f"corpus records zero {basis} tokens over known subagents — there is no share "
            "to compute, and 0/0 is not 100% waste")
    used_observed = buckets["produced-and-used"]
    used_proven = corpus["proven_used"]["total" if basis == "total" else "new"]
    basis_prose = ("every token processed (input + output + cache_creation + cache_read)"
                   if basis == "total"
                   else "the non-cached part only (input + output + cache_creation)")
    bound = Bound(
        low=(known_tokens - used_observed) / known_tokens,
        high=(known_tokens - used_proven) / known_tokens,
        kind=_INTERVAL,
        unit=f"share_of_known_subagent_tokens[{basis}]",
        low_basis=(f"{used_observed:,} of {known_tokens:,} {basis} tokens sit in "
                   "`produced-and-used`, an UPPER bound on usefulness (mostly "
                   "`parent-reference` substring hits)"),
        high_basis=(f"only {used_proven:,} {basis} tokens belong to subagents proven used "
                    f"by `{PROVEN_USED_BASIS}`"),
    )
    return (
        bound,
        f"fanout_token_waste_share_{basis}",
        corpus["known"],
        (f"scored:known_subagents ({corpus['classified']} classified - "
         f"{corpus['counts'][UNKNOWN_BUCKET]} unknown, held out and never folded)"),
        (f"TOKEN BASIS `{basis}` = {basis_prose}. Provider-cumulative: both backends "
         "re-charge the resent prefix every turn, so a long thread inflates its own share, "
         "and this corpus is violently skewed — corpus-wide median subagent "
         f"{corpus['token_p50']:,} tokens against a p90 of {corpus['token_p90']:,} "
         f"({corpus['token_p90'] / max(corpus['token_p50'], 1):,.0f}x). A handful of very "
         "long threads therefore dominate this number. It is a claim about TOKENS, not "
         "about subagents; the head-count share is a different claim."
         + _unknown_note(corpus) + _skip_note(corpus)),
    )


def _blocked_floor(corpus: Mapping[str, Any]) -> tuple[Bound, str, int, str, str]:
    blocked = corpus["counts"]["blocked"]
    classified = corpus["classified"]
    bound = Bound(
        low=blocked / classified,
        high=None,
        kind=_FLOOR,
        unit="share_of_classified_subagents",
        low_basis=(f"{blocked} of {classified} classified subagents carry a structural "
                   "blocker marker (Claude: an `isApiErrorMessage` tail; Codex: a terminal "
                   "`error`/`stream_error` payload)"),
        high_basis=("NEITHER transcript format carries a general 'I was blocked' marker, "
                    "and prose is never read as a signal — a subagent that reported being "
                    "blocked in words lands in `produced-and-discarded`. Nothing in this "
                    "corpus bounds the true blocked count from above, so a reader must "
                    "NOT read this as 'nothing was blocked'"),
    )
    return (
        bound,
        "fanout_blocked_share",
        classified,
        f"scored:classified_subagents (all {classified} scanned for a blocker marker)",
        ("A FLOOR on external blocking, not a measurement of it." + _skip_note(corpus)),
    )


def _unknown_census(corpus: Mapping[str, Any]) -> tuple[Bound, str, int, str, str]:
    unknown = corpus["counts"][UNKNOWN_BUCKET]
    classified = corpus["classified"]
    bound = Bound(
        low=float(unknown),
        high=float(unknown),
        kind=_CENSUS,
        unit="subagents",
        low_basis=(f"{unknown} of {classified} classified subagents whose used/discarded "
                   "split is NOT observable — the parent transcript is absent from the "
                   "corpus, or the parent mention index hit its byte cap before the "
                   "child's window. An exact count of what could not be decided"),
        high_basis=("same exact count — a census, not an estimate; it is what is held out "
                    "of every other denominator in this projection"),
    )
    return (
        bound,
        "fanout_unclassifiable_subagents",
        classified,
        f"scored:classified_subagents (all {classified} attempted classification)",
        (f"These {unknown} subagents are NEVER folded into another bucket: an unknown "
         "folded into a bucket is the precise failure FM-5 exists to prevent. Every share "
         "this adapter emits holds them out of its denominator and says so."
         + _skip_note(corpus)),
    )


_BUILDERS = {
    "headcount_waste": _headcount_waste,
    "token_waste_total": lambda c: _token_waste(c, "total"),
    "token_waste_new": lambda c: _token_waste(c, "new"),
    "blocked_floor": _blocked_floor,
    "unknown_census": _unknown_census,
}


def _require_bounded(tup: ClaimTuple) -> ClaimTuple:
    """Post-condition: the bound rides in the tuple, and in the text that reaches the ledger.

    `to_frames` emits `claim` as `display_text` and does NOT emit `value`, so the claim
    TEXT is the only path this number takes into the belief kernel. A guard on `value`
    alone would therefore be inert where it matters most.
    """
    bound = tup.value
    if not isinstance(bound, Bound):
        raise ProjectionError(
            f"{tup.measurement_id}: value must be a Bound, not {type(bound).__name__} — a "
            "scalar here is a point estimate, and this measurement has none (SC62)")
    rendered = bound.render()
    if rendered not in tup.claim:
        raise ProjectionError(
            f"{tup.measurement_id}: the claim text does not carry the bound. Claim text is "
            "what reaches the ledger via `display_text`; a claim that states a number "
            f"without its bound is a stronger claim than the measurement made. Expected to "
            f"find: {rendered!r}")
    if SCOPE_LIMIT not in tup.claim:
        raise ProjectionError(
            f"{tup.measurement_id}: the claim text does not carry the scope limit verbatim")
    for key, value in bound.as_extra().items():
        if tup.extra.get(key) != value:
            raise ProjectionError(
                f"{tup.measurement_id}: extra[{key!r}] disagrees with the Bound object")
    return tup


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Project one bounded quantity. Projection only — `claim_tuple.grade()` decides.

    `protocol_id` is deliberately empty: see the module docstring. The ladder therefore
    returns `Judged/Located` for every tuple here, which is the honest grade for a forensic
    walk over transcripts nobody can re-derive. The attestation digest is carried anyway.
    """
    if not isinstance(native, Mapping):
        raise ProjectionError("fanout-outcome native row must be a mapping")
    quantity = native.get("quantity")
    corpus = native.get("corpus")
    if quantity not in _BUILDERS or not isinstance(corpus, Mapping):
        raise ProjectionError(
            f"fanout-outcome native row names no known quantity (got {quantity!r}); "
            f"expected one of {list(_QUANTITIES)}")

    bound, metric, reps, reps_basis, note = _BUILDERS[quantity](corpus)
    claim = (f"FM-5 fan-out outcome accounting over {corpus['workflows']:,} workflows / "
             f"{corpus['classified']:,} classified subagents — {metric}: {bound.render()}. "
             f"{note} {SCOPE_LIMIT}")

    tup = ClaimTuple(
        measurement_id=_identity(corpus, quantity),
        metric=metric,
        value=bound,
        date=corpus["date"],
        # The measured status quo of the fan-out regime, not a proposal under test.
        category="BASELINE",
        claim=claim,
        # Waste, blocking and unclassifiability are all bad; less of each is better.
        metric_direction="lower_better",
        # EMPTY ON PURPOSE. No codified protocol covers transcript forensics, and
        # `fanout_timing.v2` is an output schema version, not a replayable procedure.
        protocol_id="",
        reps=reps,
        reps_basis=reps_basis,
        unit=bound.unit,
        attestation_path=corpus["corpus_path"],
        attestation_sha256=corpus["corpus_sha256"],
        attestation_locator=(f"fanout-corpus:{corpus['corpus_path']}"
                             f"@collector:{corpus['collector_sha256'][:12]}"),
        attestation_present=bool(corpus["corpus_present"]),
        source_kind=SOURCE_KIND,
        extra={
            **bound.as_extra(),
            "quantity": quantity,
            "corpus_schemas": corpus["schemas"],
            "collector_sha256": corpus["collector_sha256"],
            "workflows": corpus["workflows"],
            "classified_subagents": corpus["classified"],
            "known_subagents": corpus["known"],
            "outcome_counts": dict(corpus["counts"]),
            "unknown_unfolded": corpus["counts"][UNKNOWN_BUCKET],
            "proven_used_basis": PROVEN_USED_BASIS,
            "proven_used_count": corpus["proven_used"]["count"],
            "skipped_no_outcome": corpus["skipped_no_outcome"],
            "scope_limit": SCOPE_LIMIT,
        },
    )
    return _require_bounded(tup)


def frames_for_corpus(corpus_path: str | Path = DEFAULT_CORPUS, *, as_of: str) -> list[dict]:
    """Uniform frame emission through the shared carrier (`claim_tuple.to_frames`)."""
    frames: list[dict] = []
    for native in native_rows(corpus_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "CORPUS_SCHEMA", "DEFAULT_CORPUS",
    "OUTCOME_BUCKETS", "PROVEN_USED_BASIS", "UNKNOWN_BUCKET", "SCOPE_LIMIT",
    "Bound", "BoundReadError", "read_corpus", "native_rows", "project",
    "frames_for_corpus",
]
