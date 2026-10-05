"""VB-TDP-1 — project typed-decision measurement receipts (TD-2 / TD-3) into ``ClaimTuple``.

Producer (write side): epyc-orchestrator ``src/typed_decisions/measure.py``. Each
study run writes ONE JSON receipt named ``<study>-<utc-stamp>.json`` under
``<artifacts_dir or system tmp>/typed_decisions/`` carrying ``study``,
``timestamp``, ``mode``, ``role``, ``counts``, ``results``, and the
``prompt_sha256`` values of every ``DecisionResult`` the run produced. No
producer hook is required: the receipt IS the native record, and this adapter
projects it. ``claim_tuple.grade()`` decides every tuple — no ladder or grade
literal lives here.

The declared metrics, one ClaimTuple per (receipt, metric):

* ``contamination`` (TD-2): ``flip_rate`` — top-answer flips against the
  canonical order, over the question pairs resolved in BOTH orders
  (``counts.comparable_pairs``). An unresolved pair is never a flip.
* ``calibration`` (TD-2): ``ece`` and ``brier`` over the decisions that were
  actually scored, i.e. resolved AND labeled (``counts.scored``). Accuracy and
  mean confidence are diagnostics that ride in the claim text and ``extra``,
  never separate claims; the per-question ``rows`` and reliability bins are
  samples of the one run, never N witnesses.
* ``fanout`` (TD-3): ``agreement_rate`` over the (state, question) pairs
  resolved in BOTH arms; the batched and singleton wall times (reps = the calls
  each arm actually timed); and the producer's own serial-sum and wall-clock
  speedups (reps = the states the pairing covers). Per-call arrays stay samples.
* ``tool_args_pilot`` (TD-2): per arm (``closed_set`` / ``free_form``) the
  ``exact_match_rate`` and ``per_arg_exact_match_rate`` (reps = the arm's cases
  and the argument slots it scored), the arm ``wall_ms`` (reps = the arm's timed
  cases), and the closed-vs-free ``agreement`` rate (reps = the cases resolved in
  both arms). The receipt carries a per-metric ``metric_directions`` map for these
  and it is read verbatim; per-case arrays and token sums stay samples.
* ``parallel_fanout`` (TD-3b): per arm (``batched`` / ``sequential_singleton`` /
  ``concurrent_singleton``) the ``wall_ms`` and ``serial_sum_ms`` (reps = the calls
  each arm actually timed), the producer's two named speedups (reps = the states
  whose paired arms were timed), and the three pairwise agreement rates (reps =
  each comparison's own ``comparable_pairs``; a bare float rate — the other shape
  the producer may write — is projected with the run's (state, question) pair
  universe as a stated basis, never a reconstructed count). The receipt's single
  ``agreement_rate_vs_batched`` direction entry is its label for the agreement
  family and is read verbatim for all three; ``prompt_sha256`` is a per-arm map
  here and the identity payload carries it whole. Per-call arrays and token sums
  stay samples.
* ``routing_replay`` (TD-7, harness continued by TD-9): the frozen-snapshot
  routing diagnostic. ``agreement_rate`` over the decided rows (reps =
  ``aggregates.n_decided``, the rate's own denominator) plus its
  ``agreement_wilson_95_low`` bound (same reps; the high bound rides in the claim
  text and ``extra``); calibration ``ece``, ``brier`` and ``auroc`` over the
  confidence-vs-frozen-label pairs (reps = ``aggregates.calibration.n``, the
  calibration block's own count). The receipt labels directions in its own
  ``higher_is_better`` / ``lower_is_better`` vocabulary, mapped 1:1 onto the
  carrier's two tokens by ``_DIRECTION_VOCABULARY``; the receipt token is carried
  verbatim in ``extra.metric_direction_receipt_token``. TD-7 receipts predate the
  ``study`` field and identify themselves with ``receipt: "td7-routing-replay"``
  (both shapes are accepted and resolve to one study, so they share identities);
  a run is identified by the snapshot ``db_sha256`` + ``config.n`` + ``config.seed``
  + ``timestamp``, never by the per-row state/prompt hashes, which are row samples.
  The frozen label describes the INCUMBENT action's outcome only, and the
  ``calibration_agreeing_only`` sub-block — the caveat block, not a claim, since the
  receipt declares no direction keys for it — is carried whole in ``extra`` and
  named in every claim. A declared field may be present-but-null (a degenerate
  AUROC, the producer's own "not computed"): that metric is omitted, and absence is
  recorded, never filled. The remaining directed diagnostics (``mae``,
  ``top1_accuracy``, ``bottom1_accuracy``, ``spearman_rho``, ``path_split.unresolved``,
  ``wall_ms_total``) ride in ``extra.aggregates`` and the claim text; they are not
  projected as claims.

An unknown ``study``, a missing declared metric field, or a malformed number is
REFUSED by name — a mapping miss is not silently fewer rows (the README's
"extractor does not understate" test). A ``null`` speedup (the producer's own
explicit "could not divide") projects no tuple for that metric: absence is
recorded, never filled.

WRITE-SIDE GAPS (owning session: the epyc-orchestrator typed-decisions branch)
-----------------------------------------------------------------------------
The receipt schema predates VB-TDP-1 and carries no ClaimTuple labels:

1. **No ``protocol_id``.** No codified protocol covers the typed-decision
   studies yet, and none is invented here: the shared ladder grades every tuple
   an OBSERVATION (``Judged/Located``), correctly. If a protocol is codified
   later the same receipts lift without re-projection.
2. **No ``metric_direction`` in the TD-2/TD-3 receipts, per metric or per
   receipt.** The adapter reads a direction ONLY from explicit receipt fields (a
   per-metric ``metrics`` block, a ``metric_directions`` map, or a top-level
   ``metric_direction``) and never infers one from a metric name. The
   ``tool_args_pilot`` and ``parallel_fanout`` receipts DO carry a top-level
   ``metric_directions`` map, whose values are projected verbatim; the earlier
   studies do not, and for them ``ClaimTuple`` has no direction-less path, so when
   the receipt carries none the field is left at the carrier structural default,
   ``extra.metric_direction_present`` is ``False``, and the claim text carries a
   verbatim clause saying the label is NOT a recorded fact and the number must not
   be compared directionally. The producer should record a direction per metric
   (and restate it in the receipt) before any consumer reads these numbers as
   directional.
3. **No ``category``.** The adapter assigns ``BASELINE`` (the studies
   characterize the status-quo plane; no arm of a study is a promotion
   candidate) and flags ``extra.category_source``.
4. **No envelope schema/version tag**, so the reader keys on ``study`` plus
   shape. A versioned receipt schema would make refusals sharper and refusals
   of near-miss documents rarer.
5. **No explicit run id.** Identity is derived from the receipt's own fields
   (study + timestamp + mode + role + metric + prompt hashes): unique per run,
   stable across replay, and distinct metrics of one run stay distinct claims.
   A producer-minted run id would be stronger than the microsecond timestamp.
6. **The default receipt location is ``/tmp/typed_decisions``**, outside any git
   tree, so the durable artifact is the file digest this adapter computes from
   the bytes it reads; the producer should write receipts under a committed
   artifacts directory before these numbers are cited outside the session.
7. **``reps`` / ``reps_basis`` are not receipt fields.** They are extracted from
   the receipt's own counts (the SCORED denominators: ``counts.comparable_pairs``,
   ``counts.scored``, ``counts.batched_calls`` / ``counts.singleton_calls``, the
   tool-args arm ``cases`` / ``per_arg_total`` and ``results.agreement.compared``)
   with the basis stated verbatim; a producer-authored ``reps`` / ``reps_basis``
   pair would remove the mapping.
8. **The ``parallel_fanout`` direction map labels the whole agreement family with
   one ``agreement_rate_vs_batched`` key**, including the concurrent-vs-sequential
   pair the name does not describe, and its ``prompt_sha256`` is a per-arm object
   where the earlier studies wrote a flat list. Per-comparison direction keys and
   a stable hash-field shape would remove both structural aliases; until then the
   aliases are declared here and only the direction VALUE comes from the receipt.
9. **The ``routing_replay`` receipts carry no ``study`` field and label
   directions in a different vocabulary** (``higher_is_better`` /
   ``lower_is_better`` rather than the carrier's ``higher_better`` /
   ``lower_better``). Both are handled declaratively here — the receipt tag
   ``"td7-routing-replay"`` resolves to the study, and the vocabulary map is a
   declared 1:1 translation whose receipt token is preserved verbatim — but a
   producer-written ``study`` and the carrier's own tokens would make the
   adapter's receipt-tag alias and vocabulary map unnecessary. The
   ``calibration_agreeing_only`` block carries no direction entries, which is
   why it stays a carried caveat rather than a declared metric; per-sub-block
   direction keys would let it be projected.

``receipt_path`` is deliberately NOT trusted as an attestation source: the
digest is recomputed from the bytes this adapter reads, and
``attestation_verified`` is set only because that re-read happened here.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.typed_decisions_measurement/v1"
#: Frame authority scope: a measurement-class source, all of it protocol-less for now.
AUTHORITY = "measurement"
PROJECTION_NAME = "typed_decisions_measurement"
SOURCE_KIND = "typed-decisions-measurement"
PRODUCER = "epyc-orchestrator src/typed_decisions/measure.py"
STUDIES = ("contamination", "calibration", "fanout", "tool_args_pilot", "parallel_fanout",
           "routing_replay")
_ID_SCHEME = "vidya.typed-decisions-measurement/v1"

_DIRECTIONS = frozenset({"higher_better", "lower_better"})
_CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})

#: The routing_replay receipts label directions in their own vocabulary; the 1:1 mapping
#: onto the carrier's two tokens is declared here so the receipt token stays verbatim
#: (``extra.metric_direction_receipt_token``) while ``ClaimTuple`` receives a token it can
#: validate. A token outside this map is refused by path, never repaired.
_DIRECTION_VOCABULARY = {
    "higher_is_better": "higher_better",
    "lower_is_better": "lower_better",
}

#: The routing_replay harness identifies itself by receipt tag before it carried a
#: ``study`` field; both tags resolve to the one study so the two shapes share identities.
_RECEIPT_TAG_STUDY = {
    "td7-routing-replay": "routing_replay",
    "td9-routing-replay": "routing_replay",
}

OBSERVATION_CLAUSE = (
    "The producer receipt records no protocol_id, and no codified protocol covers this study "
    "yet, so the shared ladder grades this an OBSERVATION (Judged), never decision-gating."
)
DIRECTION_ABSENT_CLAUSE = (
    "The producer receipt records no metric_direction for this metric: the tuple's direction "
    "label is the ClaimTuple structural default, NOT a recorded fact, and this number must not "
    "be compared directionally until the producer records one (VB-TDP-1 write-side gap)."
)
ROUTING_LABEL_CAVEAT = (
    "CAVEAT: the frozen label is the INCUMBENT action's recorded outcome "
    "(`outcome == 'success'` from the frozen snapshot), NOT ground truth for the action the "
    "model chose, so on a disagreeing row the confidence is not a calibration of that row's "
    "own outcome; `calibration_agreeing_only` covers only the rows where the model chose the "
    "incumbent and is a diagnostic, never a second measurement."
)


@dataclass(frozen=True)
class Metric:
    """One declared measurement of a receipt: value, scored denominator, and labels.

    ``direction_key`` is the key this metric is declared under in the receipt's
    per-metric direction map when it differs from the claim key — the two arms of
    one study share one direction label (``exact_match``, ``wall_ms``) while their
    claims must stay distinct. It is an adapter-declared structural alias; the
    direction VALUE is still read only from the receipt.
    """

    key: str
    metric: str
    label: str
    value: float
    unit: str
    reps: int
    reps_basis: str
    direction_key: str | None = None


# ── receipt loading and validation ───────────────────────────────────────────


def _mapping(value: Any, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ProjectionError(f"{label} must be an object")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value):
        raise ProjectionError(
            f"{label} must be a finite number (absent or malformed in the receipt) — "
            "the adapter refuses rather than reconstructing it")
    return float(value)


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProjectionError(
            f"{label} must be a positive integer (absent or malformed in the receipt)")
    return value


def _int_value(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectionError(
            f"{label} must be an integer (absent or malformed in the receipt)")
    return int(value)


def _declared(block: Mapping, key: str, path: str) -> Any:
    """The field's value, refusing an ABSENT key by path; a present-but-null value passes.

    The two states are different facts: absent means the receipt never captured the field
    (a malformed document, refused); null is the producer's own "not computed" (absence is
    recorded, never filled).
    """
    if key not in block:
        raise ProjectionError(
            f"receipt.{path}.{key} is absent — the adapter refuses a declared field rather "
            "than reconstructing or silently skipping it")
    return block[key]


def _wilson(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ProjectionError(
            f"{label} must be a two-element [low, high] interval (got {value!r})")
    low = _finite(value[0], f"{label}[0]")
    high = _finite(value[1], f"{label}[1]")
    if low > high:
        raise ProjectionError(
            f"{label} low ({low}) exceeds its high ({high}) — refused, never repaired")
    return low, high


def _fmt(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.4f}"
    return str(value)


def _agreement_value(value: Any) -> Any:
    """The rate an agreement block carries: the nested field, or the bare float itself."""
    return value.get("agreement_rate") if isinstance(value, Mapping) else value


def _load_receipt(receipt: str | Path | Mapping[str, Any]) -> tuple[dict, str, str, bool | None]:
    """Return (document, source path, sha256 over the bytes read, artifact present).

    The digest is computed from the FILE the adapter actually read, never trusted
    from a field; a mapping input has no file and therefore no attestation.
    """
    if isinstance(receipt, Mapping):
        return dict(receipt), "", "", None
    path = Path(receipt)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ProjectionError(f"typed-decision receipt unreadable: {exc}") from exc
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"typed-decision receipt is not JSON: {exc}") from exc
    if not isinstance(doc, Mapping):
        raise ProjectionError("typed-decision receipt root must be a JSON object")
    return dict(doc), str(path), hashlib.sha256(raw).hexdigest(), True


def _study_of(receipt: Mapping) -> Any:
    """The study a receipt declares: its ``study`` field, or the producer's receipt tag.

    The TD-7 routing-replay harness predates the ``study`` field and identifies itself
    with ``receipt: "td7-routing-replay"`` (TD-9 continues the harness and may tag the
    same way). The tag family is accepted because the study roster is closed and only
    this study's harness names itself ``*-routing-replay``; a doc carrying neither a
    known study nor a routing-replay tag resolves to ``None`` and is refused by name
    in ``_validate_receipt``, never guessed.
    """
    study = receipt.get("study")
    if study is not None:
        return study
    tag = receipt.get("receipt")
    if isinstance(tag, str):
        known = _RECEIPT_TAG_STUDY.get(tag)
        if known is not None:
            return known
        if "routing-replay" in tag or "routing_replay" in tag:
            return "routing_replay"
    return None


def _validate_receipt(receipt: Mapping) -> str:
    """Refuse anything that is not a typed-decision study receipt; return the study."""
    study = _study_of(receipt)
    if study not in STUDIES:
        raise ProjectionError(
            f"not a typed-decision measurement receipt (study={study!r}; expected one of "
            f"{list(STUDIES)}) — a mapping miss is reported, never skipped silently")
    if study == "routing_replay":
        # The routing harness writes its own envelope (aggregates/config/snapshot +
        # metric_directions), not the measure.py counts/results pair. The identity
        # fields (snapshot sha256 + N + seed + timestamp) are validated here so two
        # distinct runs cannot hash to one id through a malformed field.
        _mapping(receipt.get("aggregates"), "receipt.aggregates")
        config = _mapping(receipt.get("config"), "receipt.config")
        snapshot = _mapping(receipt.get("snapshot"), "receipt.snapshot")
        _mapping(receipt.get("metric_directions"), "receipt.metric_directions")
        _positive_int(config.get("n"), "receipt.config.n")
        _int_value(config.get("seed"), "receipt.config.seed")
        digest = snapshot.get("db_sha256")
        if not isinstance(digest, str) or len(digest) != 64 \
                or any(char not in "0123456789abcdefABCDEF" for char in digest):
            raise ProjectionError(
                "receipt.snapshot.db_sha256 must be a 64-character hex digest (absent or "
                "malformed in the receipt) — the frozen label source is the run's identity")
        timestamp = receipt.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ProjectionError(
                "receipt.timestamp must be non-empty text (the routing run's identity)")
        return str(study)
    _mapping(receipt.get("counts"), "receipt.counts")
    _mapping(receipt.get("results"), "receipt.results")
    timestamp = receipt.get("timestamp")
    if timestamp is not None and (not isinstance(timestamp, str) or not timestamp.strip()):
        raise ProjectionError("receipt.timestamp must be non-empty text when present")
    prompts = receipt.get("prompt_sha256")
    if prompts is not None and not isinstance(prompts, (list, Mapping)):
        raise ProjectionError(
            "receipt.prompt_sha256 must be a list or an object when present")
    return str(study)


# ── the declared metrics ─────────────────────────────────────────────────────


def _routing_replay_metrics(receipt: Mapping) -> tuple[Metric, ...]:
    """The declared ``routing_replay`` metrics, or a path-named refusal.

    A missing field refuses by path; a field present but null (the producer's own
    "not computed", e.g. a degenerate AUROC) projects no tuple for that metric —
    absence is recorded, never back-filled.
    """
    aggregates = _mapping(receipt.get("aggregates"), "receipt.aggregates")
    agreement = _mapping(aggregates.get("agreement"), "receipt.aggregates.agreement")
    calibration = _mapping(aggregates.get("calibration"), "receipt.aggregates.calibration")

    metrics: list[Metric] = []
    rate = _declared(agreement, "rate", "aggregates.agreement")
    wilson = _declared(agreement, "wilson_95", "aggregates.agreement")
    if rate is not None or wilson is not None:
        # The rate's denominator is the decided rows; n_decided is only demanded when
        # a rate actually exists (an all-unresolved run declines with zero rows).
        n_decided = _positive_int(aggregates.get("n_decided"), "aggregates.n_decided")
    if rate is not None:
        metrics.append(Metric(
            key="agreement_rate",
            direction_key="agreement.rate",
            metric="typed_decisions.routing_replay_agreement_rate",
            label="typed/incumbent agreement rate",
            value=_finite(rate, "aggregates.agreement.rate"),
            unit="fraction",
            reps=n_decided,
            reps_basis="scored: decided rows — the agreement rate's own denominator",
        ))
    if wilson is not None:
        low, _high = _wilson(wilson, "aggregates.agreement.wilson_95")
        metrics.append(Metric(
            key="agreement_wilson_95_low",
            direction_key="agreement.wilson_95_low",
            metric="typed_decisions.routing_replay_agreement_wilson_95_low",
            label="agreement rate Wilson 95% lower bound",
            value=low,
            unit="fraction",
            reps=n_decided,
            reps_basis="scored: decided rows — the agreement rate's own denominator",
        ))

    values = {key: _declared(calibration, key, "aggregates.calibration")
              for key in ("ece", "brier", "auroc")}
    if any(value is not None for value in values.values()):
        cal_n = _positive_int(calibration.get("n"), "aggregates.calibration.n")
        for key, label in (("ece", "expected calibration error (ECE)"),
                           ("brier", "Brier score"),
                           ("auroc", "AUROC")):
            if values[key] is None:
                continue
            metrics.append(Metric(
                key=key,
                direction_key=f"calibration.{key}",
                metric=f"typed_decisions.routing_replay_{key}",
                label=f"confidence-vs-frozen-label {label}",
                value=_finite(values[key], f"aggregates.calibration.{key}"),
                unit="fraction",
                reps=cal_n,
                reps_basis=("scored: decided rows carrying a confidence — the calibration "
                            "block's own n"),
            ))
    return tuple(metrics)


def _study_metrics(receipt: Mapping) -> tuple[Metric, ...]:
    """Extract every declared metric of the receipt, or refuse it by name.

    Nothing is inferred from a metric NAME: each value is read from its own
    receipts path, and a missing path is a refusal, not a skip.
    """
    study = _validate_receipt(receipt)
    if study == "routing_replay":
        return _routing_replay_metrics(receipt)
    counts = _mapping(receipt.get("counts"), "receipt.counts")
    results = _mapping(receipt.get("results"), "receipt.results")

    if study == "contamination":
        return (Metric(
            key="flip_rate",
            metric="typed_decisions.contamination_flip_rate",
            label="top-answer flip rate",
            value=_finite(results.get("flip_rate"), "results.flip_rate"),
            unit="fraction",
            reps=_positive_int(counts.get("comparable_pairs"), "counts.comparable_pairs"),
            reps_basis=("scored: question pairs resolved in both the canonical and "
                        "at least one permuted order"),
        ),)

    if study == "calibration":
        metrics = _mapping(results.get("metrics"), "results.metrics")
        scored = _positive_int(counts.get("scored"), "counts.scored")
        basis = "scored: resolved decisions with a matching label"
        return tuple(
            Metric(
                key=key,
                metric=f"typed_decisions.calibration_{key}",
                label=label,
                value=_finite(metrics.get(key), f"results.metrics.{key}"),
                unit="fraction",
                reps=scored,
                reps_basis=basis,
            )
            for key, label in (("ece", "expected calibration error (ECE)"),
                               ("brier", "Brier score"))
        )

    if study == "tool_args_pilot":
        arms = _mapping(results.get("arms"), "results.arms")
        agreement = _mapping(results.get("agreement"), "results.agreement")
        metrics = []
        for arm_key, arm_label in (("closed_set", "closed-set"),
                                   ("free_form", "free-form")):
            arm = _mapping(arms.get(arm_key), f"results.arms.{arm_key}")
            cases = _positive_int(arm.get("cases"), f"results.arms.{arm_key}.cases")
            metrics.extend((
                Metric(
                    key=f"{arm_key}_exact_match_rate",
                    direction_key="exact_match",
                    metric=f"typed_decisions.tool_args_pilot_{arm_key}_exact_match_rate",
                    label=f"{arm_label} exact-match rate",
                    value=_finite(arm.get("exact_match_rate"),
                                  f"results.arms.{arm_key}.exact_match_rate"),
                    unit="fraction",
                    reps=cases,
                    reps_basis=f"scored: {arm_label} cases attempted by the arm",
                ),
                Metric(
                    key=f"{arm_key}_per_arg_exact_match_rate",
                    direction_key="per_arg_exact_match",
                    metric=("typed_decisions.tool_args_pilot_"
                            f"{arm_key}_per_arg_exact_match_rate"),
                    label=f"{arm_label} per-argument exact-match rate",
                    value=_finite(arm.get("per_arg_exact_match_rate"),
                                  f"results.arms.{arm_key}.per_arg_exact_match_rate"),
                    unit="fraction",
                    reps=_positive_int(arm.get("per_arg_total"),
                                       f"results.arms.{arm_key}.per_arg_total"),
                    reps_basis=("scored: argument slots scored across the "
                                f"{arm_label} arm's cases"),
                ),
                Metric(
                    key=f"{arm_key}_wall_ms",
                    direction_key="wall_ms",
                    metric=f"typed_decisions.tool_args_pilot_{arm_key}_wall_ms",
                    label=f"{arm_label} arm wall time",
                    value=_finite(arm.get("wall_ms"), f"results.arms.{arm_key}.wall_ms"),
                    unit="ms",
                    reps=cases,
                    reps_basis=f"scored: {arm_label} arm cases timed in the run",
                ),
            ))
        metrics.append(Metric(
            key="agreement_rate",
            direction_key="agreement",
            metric="typed_decisions.tool_args_pilot_agreement_rate",
            label="closed-set/free-form agreement rate",
            value=_finite(agreement.get("rate"), "results.agreement.rate"),
            unit="fraction",
            reps=_positive_int(agreement.get("compared"), "results.agreement.compared"),
            reps_basis="scored: cases resolved in both the closed-set and free-form arms",
        ))
        return tuple(metrics)

    if study == "parallel_fanout":
        arms = _mapping(results.get("arms"), "results.arms")
        agreement = _mapping(results.get("agreement"), "results.agreement")
        metrics = []
        for arm_key, arm_label, calls_key in (
            ("batched", "batched", "batched_calls"),
            ("sequential_singleton", "sequential-singleton",
             "sequential_singleton_calls"),
            ("concurrent_singleton", "concurrent-singleton",
             "concurrent_singleton_calls"),
        ):
            arm = _mapping(arms.get(arm_key), f"results.arms.{arm_key}")
            calls = _positive_int(counts.get(calls_key), f"counts.{calls_key}")
            for suffix, direction_key, what in (
                ("wall_ms", "wall_ms", "wall time"),
                ("serial_sum_ms", "serial_sum_ms", "serial-sum time"),
            ):
                metrics.append(Metric(
                    key=f"{arm_key}_{suffix}",
                    direction_key=direction_key,
                    metric=f"typed_decisions.parallel_fanout_{arm_key}_{suffix}",
                    label=f"{arm_label} arm {what}",
                    value=_finite(arm.get(suffix), f"results.arms.{arm_key}.{suffix}"),
                    unit="ms",
                    reps=calls,
                    reps_basis=f"scored: {arm_label} calls timed in the run",
                ))
        states = _positive_int(counts.get("states"), "counts.states")
        for key, baseline, candidate in (
            ("speedup_concurrent_vs_batched", "batched", "concurrent-singleton"),
            ("speedup_concurrent_vs_sequential", "sequential-singleton",
             "concurrent-singleton"),
        ):
            value = results.get(key)
            if value is None:
                # The producer's own explicit "could not divide": the quantity was
                # not measured. Absence is recorded, never filled.
                continue
            metrics.append(Metric(
                key=key,
                metric=f"typed_decisions.parallel_fanout_{key}",
                label=f"{candidate}/{baseline} wall-clock speedup",
                value=_finite(value, f"results.{key}"),
                unit="ratio",
                reps=states,
                reps_basis=(f"scored: states over which the {baseline} and {candidate} "
                            "arms were timed (paired wall-clock comparison)"),
            ))
        for comparison, baseline, candidate in (
            ("concurrent_vs_batched", "batched", "concurrent-singleton"),
            ("sequential_vs_batched", "batched", "sequential-singleton"),
            ("concurrent_vs_sequential", "sequential-singleton", "concurrent-singleton"),
        ):
            raw = agreement.get(comparison)
            if isinstance(raw, Mapping):
                rate = _finite(raw.get("agreement_rate"),
                               f"results.agreement.{comparison}.agreement_rate")
                reps = _positive_int(raw.get("comparable_pairs"),
                                     f"results.agreement.{comparison}.comparable_pairs")
                basis = (f"scored: (state, question) pairs resolved in both the {baseline} "
                         f"and {candidate} arms")
            else:
                # The other shape the producer writes: a bare rate with no
                # comparable-pair count beside it. The rate is read as carried; the
                # denominator is the run's own pair universe, stated as such.
                rate = _finite(raw, f"results.agreement.{comparison}")
                reps = (states * _positive_int(counts.get("questions_per_state"),
                                               "counts.questions_per_state"))
                basis = (f"covered: the run's (state, question) pair universe; the receipt "
                         f"carries a bare rate for the {baseline}/{candidate} comparison, so "
                         "the comparable-pair count is not recorded")
            metrics.append(Metric(
                key=f"{comparison}_agreement_rate",
                direction_key="agreement_rate_vs_batched",
                metric=f"typed_decisions.parallel_fanout_{comparison}_agreement_rate",
                label=f"{candidate}/{baseline} agreement rate",
                value=rate,
                unit="fraction",
                reps=reps,
                reps_basis=basis,
            ))
        return tuple(metrics)

    # fanout
    batched = _mapping(results.get("batched"), "results.batched")
    singleton = _mapping(results.get("singleton"), "results.singleton")
    states = _positive_int(counts.get("states"), "counts.states")
    metrics = [
        Metric(
            key="agreement_rate",
            metric="typed_decisions.fanout_agreement_rate",
            label="batched/singleton agreement rate",
            value=_finite(results.get("agreement_rate"), "results.agreement_rate"),
            unit="fraction",
            reps=_positive_int(counts.get("comparable_pairs"), "counts.comparable_pairs"),
            reps_basis=("scored: (state, question) pairs resolved in both the batched and "
                        "singleton arms"),
        ),
        Metric(
            key="batched_wall_ms",
            metric="typed_decisions.fanout_batched_wall_ms",
            label="batched arm wall time",
            value=_finite(batched.get("wall_ms"), "results.batched.wall_ms"),
            unit="ms",
            reps=_positive_int(counts.get("batched_calls"), "counts.batched_calls"),
            reps_basis="scored: batched calls timed in the run",
        ),
        Metric(
            key="singleton_wall_ms",
            metric="typed_decisions.fanout_singleton_wall_ms",
            label="singleton arm wall time",
            value=_finite(singleton.get("wall_ms"), "results.singleton.wall_ms"),
            unit="ms",
            reps=_positive_int(counts.get("singleton_calls"), "counts.singleton_calls"),
            reps_basis="scored: singleton calls timed in the run",
        ),
    ]
    for key, label in (
        ("batched_speedup_serial", "batched speedup (serial sum)"),
        ("batched_speedup_wall", "batched speedup (wall clock)"),
    ):
        value = results.get(key)
        if value is None:
            # The producer's own explicit "could not divide" (zero denominator): the
            # quantity was not measured. Absence is recorded, never filled.
            continue
        metrics.append(Metric(
            key=key,
            metric=f"typed_decisions.fanout_{key}",
            label=label,
            value=_finite(value, f"results.{key}"),
            unit="ratio",
            reps=states,
            reps_basis="scored: states with both arms timed (paired batched vs singleton)",
        ))
    return tuple(metrics)


# ── explicit receipt labels (never inferred from a metric name) ──────────────


def _direction(value: Any, label: str) -> str:
    if value not in _DIRECTIONS:
        raise ProjectionError(
            f"{label} must be one of {sorted(_DIRECTIONS)} (got {value!r}) — recorded, "
            "never repaired and never inferred")
    return str(value)


def _category(value: Any, label: str) -> str:
    if value not in _CATEGORIES:
        raise ProjectionError(
            f"{label} must be one of {sorted(_CATEGORIES)} (got {value!r})")
    return str(value)


def _explicit_direction(receipt: Mapping, metric_key: str,
                        direction_key: str | None = None) -> str | None:
    """The receipt's own direction for this metric, or None. No name-based fallback.

    ``direction_key`` is the key this claim's direction is declared under in the
    receipt's per-metric map when it differs from the claim key (two arms sharing
    one label). The VALUE is still whatever the receipt records there; the alias
    only says WHERE to read it, and it comes from the adapter's declaration, not
    from the metric name.
    """
    lookup = direction_key or metric_key
    blocks = receipt.get("metrics")
    if isinstance(blocks, Mapping):
        block = blocks.get(metric_key)
        if isinstance(block, Mapping) and "metric_direction" in block:
            return _direction(block["metric_direction"],
                              f"metrics.{metric_key}.metric_direction")
    per_metric = receipt.get("metric_directions")
    if per_metric is not None:
        per_metric = _mapping(per_metric, "receipt.metric_directions")
        if lookup in per_metric:
            return _direction(per_metric[lookup], f"metric_directions.{lookup}")
    if "metric_direction" in receipt:
        return _direction(receipt["metric_direction"], "receipt.metric_direction")
    return None


def _routing_direction(receipt: Mapping, direction_key: str) -> tuple[str, str]:
    """(carrier direction, receipt token) from the routing receipt's own direction map.

    Read ONLY from ``receipt.metric_directions``: the routing_replay study declares a
    direction for every projected metric, so an absent key is refused by path rather
    than falling back to the direction-less clause of the earlier studies. The receipt
    token is returned for verbatim carriage; only the declared vocabulary map turns it
    into a token the carrier validates.
    """
    directions = _mapping(receipt.get("metric_directions"), "receipt.metric_directions")
    if direction_key not in directions:
        raise ProjectionError(
            f"receipt.metric_directions.{direction_key} is absent — the routing_replay study "
            "declares a direction for every projected metric and the adapter refuses to "
            "invent one")
    raw = directions[direction_key]
    carrier = _DIRECTION_VOCABULARY.get(raw)
    if carrier is None:
        raise ProjectionError(
            f"receipt.metric_directions.{direction_key} must be one of "
            f"{sorted(_DIRECTION_VOCABULARY)} (got {raw!r}) — recorded, never repaired")
    return carrier, str(raw)


def _explicit_category(receipt: Mapping, metric_key: str) -> tuple[str, str]:
    """(category, source). Falls back to BASELINE with the source named, never silently."""
    blocks = receipt.get("metrics")
    if isinstance(blocks, Mapping):
        block = blocks.get(metric_key)
        if isinstance(block, Mapping) and "category" in block:
            return _category(block["category"], f"metrics.{metric_key}.category"), \
                f"receipt:metrics.{metric_key}.category"
    per_metric = receipt.get("categories")
    if per_metric is not None:
        per_metric = _mapping(per_metric, "receipt.categories")
        if metric_key in per_metric:
            return _category(per_metric[metric_key], f"categories.{metric_key}"), \
                f"receipt:categories.{metric_key}"
    if "category" in receipt:
        return _category(receipt["category"], "receipt.category"), "receipt:category"
    return "BASELINE", "adapter-default:BASELINE"


def _explicit_protocol(receipt: Mapping) -> str:
    value = receipt.get("protocol_id")
    if value is None or value == "":
        return ""
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError("receipt.protocol_id must be non-empty text when present")
    return value.strip()


# ── identity, date, claim text ───────────────────────────────────────────────


def _date(receipt: Mapping) -> str:
    timestamp = receipt.get("timestamp")
    if isinstance(timestamp, str) and timestamp.strip():
        return timestamp.strip()[:10]
    return ""  # absent, never filled


def _identity(receipt: Mapping, metric_key: str) -> str:
    """Unique per (run, metric): the receipt's own identity fields only.

    Distinct runs cannot collapse (timestamp + prompt hashes differ), and distinct
    metrics of one run cannot collapse (the metric key is in the payload). Replaying
    the same receipt is stable — the same bytes yield the same claim ids. The
    routing_replay run is identified by snapshot sha256 + N + seed + timestamp; its
    per-row state/prompt hashes are row samples and never enter the run identity.
    """
    study = _study_of(receipt)
    if study == "routing_replay":
        config = receipt.get("config") or {}
        snapshot = receipt.get("snapshot") or {}
        payload = [
            _ID_SCHEME,
            study,
            receipt.get("timestamp"),
            snapshot.get("db_sha256"),
            config.get("n"),
            config.get("seed"),
            metric_key,
        ]
    else:
        payload = [
            _ID_SCHEME,
            study,
            receipt.get("timestamp"),
            receipt.get("mode"),
            receipt.get("role"),
            metric_key,
            # Carried whole: a flat list for the TD-2/TD-3 studies, a per-arm object for
            # parallel_fanout. Copying it to a list would silently drop the hashes.
            receipt.get("prompt_sha256") or [],
        ]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, default=str)
    return "tdmeas_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _claim(receipt: Mapping, metric: Metric, *, protocol_id: str,
           direction_present: bool) -> str:
    """Claim text built ONLY from receipt fields (and the recorded label sources)."""
    study = _study_of(receipt)
    mode = receipt.get("mode")
    role = receipt.get("role")
    counts = receipt.get("counts")
    results = receipt.get("results")

    if study == "contamination":
        head = (
            f"TD-2 typed-decision contamination study (mode {mode}, role {role}): "
            f"{counts.get('questions')} question(s) asked under {counts.get('orderings')} "
            f"deterministic ordering(s); {metric.label} {_fmt(metric.value)} over "
            f"{counts.get('comparable_pairs')} pair(s) resolved in both the canonical order and "
            f"a permuted order ({counts.get('flips')} flip(s), "
            f"{counts.get('unresolved_pairs')} unresolved pair(s), "
            f"{counts.get('canonical_unresolved')} question(s) unresolved in the canonical "
            "order)."
        )
    elif study == "calibration":
        metrics = results["metrics"]
        head = (
            f"TD-2 typed-decision calibration study (mode {mode}, role {role}): "
            f"{metrics.get('n')} scored decision(s) of {counts.get('questions')} question(s) "
            f"asked in one batched pass; {metric.label} {_fmt(metric.value)} "
            f"(accuracy {_fmt(metrics.get('accuracy'))}, mean confidence "
            f"{_fmt(metrics.get('mean_confidence'))}, {metrics.get('n_bins')} equal-width "
            f"bins; {counts.get('unlabeled')} unlabeled, "
            f"{counts.get('unresolved')} unresolved)."
        )
    elif study == "tool_args_pilot":
        closed = results["arms"]["closed_set"]
        free = results["arms"]["free_form"]
        agreement = results["agreement"]
        head = (
            f"TD-2 typed-decision tool-args pilot study (mode {mode}, role {role}): "
            f"{counts.get('tools')} tool(s) x {counts.get('cases')} case(s), "
            f"closed-set decode {closed.get('decode')!r} vs free-form decode "
            f"{free.get('decode')!r}; {metric.label} {_fmt(metric.value)} "
            f"({closed.get('exact_match')}/{closed.get('cases')} closed-set exact over "
            f"{closed.get('per_arg_total')} argument slot(s), "
            f"{free.get('exact_match')}/{free.get('cases')} free-form exact over "
            f"{free.get('per_arg_total')} argument slot(s); agreement "
            f"{_fmt(agreement.get('rate'))} over {agreement.get('compared')} comparable "
            f"case(s), {agreement.get('agreeing')} agreeing)."
        )
    elif study == "routing_replay":
        config = receipt.get("config") or {}
        snapshot = receipt.get("snapshot") or {}
        aggregates = receipt.get("aggregates") or {}
        agreement = aggregates.get("agreement") or {}
        calibration = aggregates.get("calibration") or {}
        agreeing_only = aggregates.get("calibration_agreeing_only") or {}
        path_split = aggregates.get("path_split") or {}
        head = (
            f"Typed-decision routing replay (mode {config.get('mode')}, role "
            f"{config.get('role')}, cue {config.get('cue_style')!r}): "
            f"{aggregates.get('n_rows')} recorded routing row(s) sampled from the frozen "
            f"snapshot (db sha256 {snapshot.get('db_sha256')}, "
            f"{snapshot.get('admissibility_reason')}); {metric.label} {_fmt(metric.value)} "
            f"(agreement {_fmt(agreement.get('rate'))} over {aggregates.get('n_decided')} "
            f"decided row(s), Wilson 95% {agreement.get('wilson_95')}, "
            f"{agreement.get('n_agreeing')} agreeing / {agreement.get('n_disagreeing')} "
            f"disagreeing; calibration n={calibration.get('n')}, ECE "
            f"{_fmt(calibration.get('ece'))}, Brier {_fmt(calibration.get('brier'))}, AUROC "
            f"{_fmt(calibration.get('auroc'))}; path split native {path_split.get('native')}"
            f"/json {path_split.get('json')}/unresolved {path_split.get('unresolved')}; wall "
            f"{_fmt(aggregates.get('wall_ms_total'))} ms total). {ROUTING_LABEL_CAVEAT} "
            f"calibration_agreeing_only n={agreeing_only.get('n')}: ECE "
            f"{_fmt(agreeing_only.get('ece'))}, Brier {_fmt(agreeing_only.get('brier'))}, "
            f"AUROC {_fmt(agreeing_only.get('auroc'))}."
        )
    elif study == "parallel_fanout":
        arms = results["arms"]
        agreement = results["agreement"]
        concurrent_vs_batched = _agreement_value(agreement.get("concurrent_vs_batched"))
        sequential_vs_batched = _agreement_value(agreement.get("sequential_vs_batched"))
        concurrent_vs_sequential = _agreement_value(
            agreement.get("concurrent_vs_sequential"))
        head = (
            f"TD-3b typed-decision parallel fan-out study (mode {mode}, role {role}): "
            f"{counts.get('states')} state(s) x {counts.get('questions_per_state')} probe "
            f"question(s) over {counts.get('workers')} concurrent worker(s); {metric.label} "
            f"{_fmt(metric.value)} (batched wall {_fmt(arms['batched'].get('wall_ms'))} ms over "
            f"{counts.get('batched_calls')} call(s), sequential-singleton wall "
            f"{_fmt(arms['sequential_singleton'].get('wall_ms'))} ms over "
            f"{counts.get('sequential_singleton_calls')} call(s), concurrent-singleton wall "
            f"{_fmt(arms['concurrent_singleton'].get('wall_ms'))} ms over "
            f"{counts.get('concurrent_singleton_calls')} call(s); speedups "
            f"{_fmt(results.get('speedup_concurrent_vs_batched'))}x concurrent/batched and "
            f"{_fmt(results.get('speedup_concurrent_vs_sequential'))}x concurrent/sequential; "
            f"agreement {_fmt(concurrent_vs_batched)} concurrent/batched, "
            f"{_fmt(sequential_vs_batched)} sequential/batched, "
            f"{_fmt(concurrent_vs_sequential)} concurrent/sequential)."
        )
    else:
        batched = results["batched"]
        singleton = results["singleton"]
        head = (
            f"TD-3 typed-decision fan-out study (mode {mode}, role {role}): "
            f"{counts.get('states')} state(s) x {counts.get('questions_per_state')} probe "
            f"question(s); {metric.label} {_fmt(metric.value)} (batched wall "
            f"{_fmt(batched.get('wall_ms'))} ms over {counts.get('batched_calls')} call(s) vs "
            f"singleton wall {_fmt(singleton.get('wall_ms'))} ms over "
            f"{counts.get('singleton_calls')} call(s); agreement "
            f"{_fmt(results.get('agreement_rate'))} over {counts.get('comparable_pairs')} "
            f"comparable pair(s), {counts.get('disagreements')} disagreement(s), "
            f"{counts.get('unresolved_pairs')} unresolved pair(s))."
        )

    clauses = [head]
    if protocol_id:
        clauses.append(f"The producer receipt records protocol_id {protocol_id!r}.")
    else:
        clauses.append(OBSERVATION_CLAUSE)
    if not direction_present:
        clauses.append(DIRECTION_ABSENT_CLAUSE)
    return " ".join(clauses)


# ── the reader and the projection ────────────────────────────────────────────


def native_rows(receipt: str | Path | Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """One native row per declared metric carried by the receipt; foreign docs refused.

    A Path (the ingest path) is read once and its digest computed from the bytes;
    a Mapping input has no file, so its attestation is honestly absent.
    """
    doc, path, digest, present = _load_receipt(receipt)
    metrics = _study_metrics(doc)
    # Resolve every explicit label here too, so a malformed one refuses the unit up
    # front instead of surfacing mid-ingest; nothing is defaulted into the document.
    study = _study_of(doc)
    _explicit_protocol(doc)
    for metric in metrics:
        if study == "routing_replay":
            _routing_direction(doc, metric.direction_key or metric.key)
        else:
            _explicit_direction(doc, metric.key, metric.direction_key)
        _explicit_category(doc, metric.key)
    return tuple({
        "receipt": doc,
        "metric_key": metric.key,
        "receipt_path": path,
        "receipt_sha256": digest,
        "attestation_present": present,
    } for metric in metrics)


@register(PROJECTION_NAME)
def project(native: Any) -> ClaimTuple:
    """Project one native row. Grading stays in ``claim_tuple.grade()``."""
    if not isinstance(native, Mapping):
        raise ProjectionError("typed-decision native row must be a mapping")
    receipt = native.get("receipt")
    metric_key = native.get("metric_key")
    if not isinstance(receipt, Mapping) or not isinstance(metric_key, str) or not metric_key:
        raise ProjectionError("typed-decision native row lacks its receipt or metric identity")
    metrics = {metric.key: metric for metric in _study_metrics(receipt)}
    metric = metrics.get(metric_key)
    if metric is None:
        raise ProjectionError(
            f"receipt does not carry the declared metric {metric_key!r}; declared: "
            f"{sorted(metrics)}")

    study = _study_of(receipt)
    if study == "routing_replay":
        direction, direction_token = _routing_direction(
            receipt, metric.direction_key or metric_key)
        direction_source = (f"receipt:metric_directions."
                            f"{metric.direction_key or metric_key}")
    else:
        direction = _explicit_direction(receipt, metric_key, metric.direction_key)
        direction_token = ""
        direction_source = ("receipt" if direction is not None
                            else "absent: ClaimTuple structural default")
    category, category_source = _explicit_category(receipt, metric_key)
    protocol_id = _explicit_protocol(receipt)
    path = str(native.get("receipt_path") or "")
    digest = str(native.get("receipt_sha256") or "")
    if digest and len(digest) != 64:
        raise ProjectionError("receipt_sha256 must be a 64-character hex digest")

    config: Mapping = (receipt.get("config")
                       if isinstance(receipt.get("config"), Mapping) else {})
    extra = {
        "producer": PRODUCER,
        "study": study,
        "mode": receipt.get("mode") or config.get("mode"),
        "role": receipt.get("role") or config.get("role"),
        "metric_key": metric_key,
        "counts": dict(receipt.get("counts") or {}),
        "prompt_sha256": list(receipt.get("prompt_sha256") or []),
        "receipt_path": path,
        "receipt_sha256": digest,
        "metric_direction_present": direction is not None,
        "metric_direction_source": direction_source,
        "category_source": category_source,
        "protocol_id_present": bool(protocol_id),
    }
    if study == "routing_replay":
        snapshot = _mapping(receipt.get("snapshot"), "receipt.snapshot")
        aggregates = _mapping(receipt.get("aggregates"), "receipt.aggregates")
        label_provenance = receipt.get("label_provenance")
        extra.update(
            snapshot=dict(snapshot),
            snapshot_db_sha256=snapshot.get("db_sha256"),
            config=dict(config),
            corpus=dict(receipt.get("corpus") or {}),
            aggregates=dict(aggregates),
            # Promoted beside the full aggregates block as well, so the caveat block a
            # reader must not miss is one key away, not buried in the diagnostic dump.
            calibration_agreeing_only=dict(
                aggregates.get("calibration_agreeing_only") or {}),
            label_provenance=(dict(label_provenance)
                              if isinstance(label_provenance, Mapping) else {}),
            label_caveat=ROUTING_LABEL_CAVEAT,
            metric_direction_receipt_token=direction_token,
            metric_direction_vocabulary="higher_is_better|lower_is_better -> "
                                        "higher_better|lower_better",
        )

    fields: dict[str, Any] = dict(
        measurement_id=_identity(receipt, metric_key),
        metric=metric.metric,
        value=metric.value,
        date=_date(receipt),
        category=category,
        claim=_claim(receipt, metric, protocol_id=protocol_id,
                     direction_present=direction is not None),
        protocol_id=protocol_id,
        reps=metric.reps,
        reps_basis=metric.reps_basis,
        unit=metric.unit,
        attestation_path="",
        attestation_sha256=digest,
        attestation_locator=(f"typed-decisions-receipt:{path}" if path else ""),
        attestation_present=native.get("attestation_present"),
        # SC69: True is set only because the digest was recomputed from the bytes read
        # here, at the write boundary; a mapping input carries no digest and claims none.
        attestation_verified=True if digest else None,
        source_kind=SOURCE_KIND,
        extra=extra,
    )
    if direction is not None:
        fields["metric_direction"] = direction
    return ClaimTuple(**fields)


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "PRODUCER", "PROJECTION_NAME", "SOURCE_KIND",
    "STUDIES", "Metric", "native_rows", "project",
]
