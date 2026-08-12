#!/usr/bin/env python3
"""Bounded, fail-closed deterministic re-score of already-persisted eval outputs.

WHY THIS EXISTS (2026-08-12, backlog rows B9/B10 of
``handoffs/active/autopilot-decision-plane-audit-2026-07-22.md``).

B9 asked for a *bounded deterministic completion over already-generated
outputs* once the scorer-isolation fix was integrated; B10 asked to resolve a
stored-vs-rescored BigCodeBench divergence **fail-closed, with a bounded
correction ledger**.  The E8-v5 namespace those rows named was destroyed (see
the ledger's ``b10_referenced_evidence`` block), but the *instrument* they
describe is the deliverable, and a live persisted corpus exists.  This tool is
that instrument, pointed at the corpus that still exists.

WHAT IT DOES.  It joins each persisted ``question_result`` row to its pool
question by ``question_id``, re-scores the **saved** answer through the
orchestrator's isolated ``debug_scorer.score_answer``, and compares the fresh
verdict to the stored one.  It generates nothing and calls no model.

FAIL-CLOSED, precisely.  Four properties, each covered by a test in
``tests/test_deterministic_rescore_ledger.py``:

1. **Nothing is written back.**  Corpora and pool are opened read-only and the
   tool has no code path that mutates them.  A divergence is *recorded*, never
   *applied*: every ledger entry carries ``applied: false``.
2. **The favourable direction gets no free pass.**  ``stored=false`` →
   ``rescored=true`` is the direction that silently improves a score.  It is
   counted, listed, and classified separately, and it does **not** clear the
   gate.  Any unadjudicated divergence in either direction makes the run exit
   non-zero, so a consumer that sees exit 0 knows the corpus is clean.
3. **No verdict is produced without a deterministic scorer.**  ``llm_judge``
   requires inference, so those rows are excluded *by method name before the
   scorer is called* — never merely "handled if it fails".  A scorer that
   declines (``ScoringUnavailableError``) yields an excluded row, not a False.
4. **Bounded.**  ``--max-rows`` caps the work and the run aborts rather than
   truncating silently, so a partial pass can never be mistaken for a full one.

DEBUGBENCH IS EXCLUDED AND FLAGGED, NOT RE-SCORED.  The debugbench oracle was
re-derived on 2026-08-12 as vacuous on 76.1% of upstream rows and
anti-correlated on some of ours (``artifacts/audit/debugbench-oracle-vacuity-
20260812.md``; rebuild tracked by ``mainC``).  Re-scoring those rows under
*either* the old or the new oracle would launder an uninterpretable number into
a ledger that looks adjudicated.  They are counted, listed by ordinal, and
marked ``pending-oracle-replacement`` instead.

INSTRUMENT DRIFT IS REPORTED, NOT HIDDEN.  The scorer used here is today's, not
the one that produced the stored verdicts.  The ledger binds the SHA-256 of
every input and of the scorer sources, and records the historical E8 scorer pin
alongside the current hash.  A divergence is therefore evidence of
*stored-verdict / current-instrument disagreement* — it is not, on its own,
proof the stored verdict was wrong.  That is exactly why nothing is applied.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "epyc.deterministic_rescore_ledger.v1"

# Suites whose oracle is known-broken. Rows are excluded and flagged, never
# scored. Keyed to the audit that proved it, so this list cannot grow by habit.
QUARANTINED_SUITES: dict[str, dict[str, str]] = {
    "debugbench": {
        "reason": "pending-oracle-replacement",
        "evidence": "artifacts/audit/debugbench-oracle-vacuity-20260812.md",
        "detail": (
            "oracle is a 100-char solution prefix: vacuous on 76.1% of upstream "
            "rows (echoing the buggy input passes) and anti-correlated on some "
            "of ours (the reference solution FAILS 3 of our 4 core-pool rows). "
            "Rebuild in flight; re-scoring under either oracle would launder an "
            "uninterpretable verdict into an adjudicated-looking ledger."
        ),
    },
}

# Scoring methods that are not deterministic offline. Excluded BY NAME before
# the scorer is invoked, so this pass can never reach for a model.
NONDETERMINISTIC_METHODS = frozenset({"llm_judge"})

# Methods that ignore ``scoring_config`` entirely, so a row can be re-scored
# faithfully from ``expected`` alone.
#
# WHY THIS SET EXISTS. The first version of this tool took the scoring method
# from the POOL and produced 629 divergences — every one an artifact. The
# corpus records the method that actually ran (``result.scoring_method``), and
# on this corpus it disagrees with the pool on 3,557 of 6,746 rows (52.7%):
# the math suite is fed by ``dataset_adapter_modules/math_adapter.py``, which
# assigns ``math_verify``, while the YAML pool row for the same ``question_id``
# says ``exact_match``. Re-scoring those with ``exact_match`` swaps in a more
# permissive scorer (its last-resort branch takes the final line) and
# manufactures "corrections" in the favourable direction. The recorded method
# is the authoritative witness; the pool is not.
#
# When the recorded method differs from the pool's, the pool's
# ``scoring_config`` belongs to the *other* method and cannot be trusted — so
# drift is only re-scorable when the recorded method ignores config. Otherwise
# the row's scoring contract is not reconstructible and it is excluded.
CONFIG_INSENSITIVE_METHODS = frozenset({"math_verify"})

# The E8-era scorer pin, from orchestrator
# scripts/benchmark/run_e8_quality_baseline_reseed.py::HISTORICAL_E8_SCORER_SOURCES.
# Carried so the ledger states instrument drift instead of implying there is none.
HISTORICAL_E8_SCORER_SOURCES = {
    "debug_scorer": (
        "90b2fe1f9d756ae584f2c4e9bffc0be3f244712828706e154e8ad41c047d475a"
    ),
    "seeding_scoring": (
        "fe59c4f97bcd8d977b73a11b4a014c97314d43fb4070121e77fd7cf1a48dcf3b"
    ),
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_scorer(scorer_path: Path):
    """Import the orchestrator's debug_scorer by path, under a private key.

    Mirrors ``seeding_scoring._load_orchestrator_debug_scorer``: importing by
    bare module name would bind whichever ``debug_scorer.py`` happened to win
    ``sys.path``, which is the very ambiguity the isolation work removed.
    """
    key = "epyc_audit_debug_scorer"
    spec = importlib.util.spec_from_file_location(key, scorer_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load debug_scorer from {scorer_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


def load_measurement_guards(orchestrator_root: Path):
    """Import the orchestrator's REL-1 guards. Fail closed if unavailable.

    ``src.autopilot_core.measurement_guards`` is the *consumer-side* rule for
    what counts as a measurement: an answer that is really an in-band
    ``[ERROR: ...]`` string is an infrastructure failure, not a wrong answer,
    and belongs out of the denominator. Re-implementing that predicate here
    would create the second copy the module was unified to remove, and two
    copies of an admissibility rule drift silently. So we import the real one
    or we stop.
    """
    root = str(orchestrator_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from src.autopilot_core.measurement_guards import (  # noqa: PLC0415
        inband_error_text,
    )

    return inband_error_text


def load_pool(pool_path: Path) -> dict[str, dict[str, Any]]:
    pool: dict[str, dict[str, Any]] = {}
    with open(pool_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            qid = row.get("id")
            if qid is not None:
                pool[qid] = row
    return pool


def iter_corpus_rows(corpus_path: Path):
    """Yield ``(line_no, row)`` for question_result rows. Read-only by construction."""
    with open(corpus_path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("row_type") == "question_result":
                yield line_no, row


def classify_row(
    row: dict[str, Any],
    pool: dict[str, dict[str, Any]],
    scorer: Any,
    inband_error_text: Any,
) -> dict[str, Any]:
    """Return one ledger entry for one persisted row.

    Every return path sets ``applied: false``. There is deliberately no
    parameter that would let a caller turn that off — a "dry run" flag is how a
    fail-closed tool acquires a fail-open mode.
    """
    result = row.get("result") or {}
    qid = result.get("question_id")
    suite = result.get("suite")
    entry: dict[str, Any] = {
        "ordinal": row.get("ordinal"),
        "question_id": qid,
        "suite": suite,
        "eval_batch_id": row.get("eval_batch_id"),
        "label": row.get("label"),
        "stored_correct": result.get("correct"),
        "rescored_correct": None,
        "applied": False,
    }

    quarantine = QUARANTINED_SUITES.get(suite or "")
    if quarantine is not None:
        entry["disposition"] = "excluded"
        entry["reason"] = f"quarantined_suite:{quarantine['reason']}"
        entry["evidence"] = quarantine["evidence"]
        return entry

    pool_row = pool.get(qid) if qid is not None else None
    if pool_row is None:
        entry["disposition"] = "excluded"
        entry["reason"] = "pool_miss"
        return entry

    # Method resolution. The corpus row records the method that actually
    # scored it; the pool records what the pool says today. Only the former is
    # a witness of the run, so it wins — and a row that recorded nothing is
    # excluded rather than scored under an assumption.
    recorded_method = result.get("scoring_method")
    pool_method = pool_row.get("scoring_method")
    entry["pool_scoring_method"] = pool_method
    entry["recorded_scoring_method"] = recorded_method

    if not recorded_method:
        entry["disposition"] = "excluded"
        entry["reason"] = "method_unrecorded"
        return entry

    method = recorded_method
    entry["scoring_method"] = method
    if method in NONDETERMINISTIC_METHODS:
        entry["disposition"] = "excluded"
        entry["reason"] = f"nondeterministic_method:{method}"
        return entry

    if method != pool_method:
        entry["pool_method_drift"] = True
        if method not in CONFIG_INSENSITIVE_METHODS:
            entry["disposition"] = "excluded"
            entry["reason"] = (
                f"method_drift_config_unreconstructible:"
                f"recorded={method},pool={pool_method}"
            )
            return entry

    # Two different failures wear the same shape here and must not share a
    # reason. "The corpus never persisted the output" is an evidence-retention
    # gap — the stored verdict is unauditable forever. "The model emitted
    # nothing" is a real, scorable event whose only possible verdict is False.
    # Collapsing them would hide the first inside the second.
    answer = row.get("answer")
    if "answer" not in row or answer is None:
        entry["disposition"] = "excluded"
        entry["reason"] = "answer_not_persisted"
        entry["tokens_generated"] = result.get("tokens_generated")
        return entry
    if not isinstance(answer, str) or not answer.strip():
        entry["disposition"] = "excluded"
        entry["reason"] = "answer_empty"
        entry["tokens_generated"] = result.get("tokens_generated")
        return entry

    # REL-1: an ``[ERROR: ...]`` answer is an infrastructure failure wearing an
    # answer's clothes. Scoring it would score the outage. It is excluded here
    # and reported, because a stored verdict on such a row is a measurement the
    # run never earned — the same class as B10's BigCodeBench divergence, but
    # biased the other way.
    error_text = inband_error_text(answer)
    if error_text:
        entry["disposition"] = "excluded"
        entry["reason"] = "inband_infrastructure_error"
        entry["inband_error"] = str(error_text)[:200]
        return entry

    stored = result.get("correct")
    if not isinstance(stored, bool):
        entry["disposition"] = "excluded"
        entry["reason"] = "no_stored_verdict"
        return entry

    unavailable = getattr(scorer, "ScoringUnavailableError", ())
    try:
        rescored = bool(
            scorer.score_answer(
                answer,
                pool_row.get("expected"),
                method,
                pool_row.get("scoring_config") or {},
            )
        )
    except unavailable as exc:  # type: ignore[misc]
        entry["disposition"] = "excluded"
        entry["reason"] = f"scorer_unavailable:{exc}"
        return entry
    except ValueError as exc:
        entry["disposition"] = "excluded"
        entry["reason"] = f"scorer_error:{exc}"
        return entry

    entry["rescored_correct"] = rescored
    if rescored == stored:
        entry["disposition"] = "agree"
        entry["reason"] = "stored_matches_rescore"
        return entry

    entry["disposition"] = "divergence"
    entry["reason"] = (
        "stored_false_rescored_true" if rescored else "stored_true_rescored_false"
    )
    # The favourable direction is named so it can never be read as a correction
    # that was safe to absorb.
    entry["favours_score"] = bool(rescored)
    return entry


def build_ledger(
    corpora: list[Path],
    pool_path: Path,
    scorer_path: Path,
    seeding_path: Path | None,
    orchestrator_root: Path,
    max_rows: int,
) -> dict[str, Any]:
    pool = load_pool(pool_path)
    scorer = load_scorer(scorer_path)
    inband_error_text = load_measurement_guards(orchestrator_root)

    scorer_sources = {"debug_scorer": sha256_path(scorer_path)}
    if seeding_path is not None and seeding_path.exists():
        scorer_sources["seeding_scoring"] = sha256_path(seeding_path)

    entries: list[dict[str, Any]] = []
    per_corpus: list[dict[str, Any]] = []
    scanned = 0

    for corpus_path in corpora:
        corpus_entries: list[dict[str, Any]] = []
        for _line_no, row in iter_corpus_rows(corpus_path):
            scanned += 1
            if scanned > max_rows:
                raise RuntimeError(
                    f"bounded pass exceeded --max-rows={max_rows}; refusing to "
                    "emit a truncated ledger that would look complete"
                )
            entry = classify_row(row, pool, scorer, inband_error_text)
            entry["corpus"] = str(corpus_path)
            corpus_entries.append(entry)
        entries.extend(corpus_entries)
        per_corpus.append(
            {
                "corpus": str(corpus_path),
                "sha256": sha256_path(corpus_path),
                "rows": len(corpus_entries),
                "dispositions": dict(
                    Counter(e["disposition"] for e in corpus_entries)
                ),
            }
        )

    dispositions = Counter(e["disposition"] for e in entries)
    reasons = Counter(e["reason"] for e in entries)
    divergences = [e for e in entries if e["disposition"] == "divergence"]
    quarantined = [
        e
        for e in entries
        if e["disposition"] == "excluded"
        and str(e.get("reason", "")).startswith("quarantined_suite:")
    ]

    # Fail-closed invariant, asserted rather than assumed: a quarantined row
    # must never carry a fresh verdict. If this ever trips, the ledger is wrong
    # and must not be published.
    leaked = [e for e in quarantined if e.get("rescored_correct") is not None]
    if leaked:
        raise RuntimeError(
            f"quarantined rows carried a re-scored verdict: {leaked[:3]}"
        )
    applied = [e for e in entries if e.get("applied")]
    if applied:
        raise RuntimeError(f"ledger entries marked applied: {applied[:3]}")

    inband = [e for e in entries if e["reason"] == "inband_infrastructure_error"]
    unpersisted = [e for e in entries if e["reason"] == "answer_not_persisted"]

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "scripts/audit/deterministic_rescore_ledger.py",
        "fail_closed": True,
        "corrections_applied": 0,
        "instrument": {
            "scorer_sources_sha256": scorer_sources,
            "historical_e8_scorer_sources_sha256": HISTORICAL_E8_SCORER_SOURCES,
            "scorer_drifted_from_e8_pin": (
                scorer_sources.get("debug_scorer")
                != HISTORICAL_E8_SCORER_SOURCES["debug_scorer"]
            ),
            "pool": {"path": str(pool_path), "sha256": sha256_path(pool_path)},
            "quarantined_suites": QUARANTINED_SUITES,
            "nondeterministic_methods": sorted(NONDETERMINISTIC_METHODS),
        },
        "summary": {
            "rows_scanned": scanned,
            "dispositions": dict(dispositions),
            "reasons": dict(reasons),
            "divergences": len(divergences),
            "divergences_favouring_score": sum(
                1 for e in divergences if e.get("favours_score")
            ),
            "divergences_against_score": sum(
                1 for e in divergences if not e.get("favours_score")
            ),
            "quarantined_rows": len(quarantined),
            # A stored verdict on an in-band infrastructure error is a
            # measurement the run never earned. Counted separately because it
            # biases scores DOWNWARD, the opposite direction to B10's case, and
            # a ledger that only looks for favourable corrections would miss it.
            "inband_infrastructure_error_rows": len(inband),
            "inband_infrastructure_error_by_stored_verdict": dict(
                Counter(str(e.get("stored_correct")) for e in inband)
            ),
            "inband_infrastructure_error_by_corpus": dict(
                Counter(e["corpus"] for e in inband)
            ),
            # Stored verdicts whose output was never persisted cannot be
            # audited by this or any future pass. An evidence-retention gap,
            # not a scoring one.
            "answer_not_persisted_rows": len(unpersisted),
            "answer_not_persisted_by_corpus": dict(
                Counter(e["corpus"] for e in unpersisted)
            ),
            # Excluded rows crossed with the verdict they carry, so a reader can
            # see whether an exclusion class is quietly dropping passes. An
            # excluded row is NOT an agreement: the scorer never had a decision
            # to make, and folding it into "agree" would inflate the rate with
            # rows that cannot disagree.
            "excluded_reason_by_stored_verdict": {
                reason: dict(
                    Counter(
                        str(e.get("stored_correct"))
                        for e in entries
                        if e["disposition"] == "excluded" and e["reason"] == reason
                    )
                )
                for reason in sorted(
                    {
                        e["reason"]
                        for e in entries
                        if e["disposition"] == "excluded"
                    }
                )
            },
            # Listed per persisted row, not deduplicated: a corpus repeats an
            # ordinal once per repetition batch, and collapsing them would
            # under-report how many stored verdicts are quarantined.
            "quarantined_ordinals": sorted(
                (
                    {
                        "corpus": e.get("corpus"),
                        "eval_batch_id": e.get("eval_batch_id"),
                        "ordinal": e.get("ordinal"),
                        "question_id": e.get("question_id"),
                        "stored_correct": e.get("stored_correct"),
                    }
                    for e in quarantined
                ),
                key=lambda d: (
                    str(d["corpus"]),
                    str(d["eval_batch_id"]),
                    d["ordinal"] if d["ordinal"] is not None else -1,
                ),
            ),
        },
        "per_corpus": per_corpus,
        "divergences": divergences,
        "quarantined": quarantined,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", action="append", required=True)
    parser.add_argument("--pool", required=True)
    parser.add_argument("--scorer", required=True)
    parser.add_argument("--seeding-scoring", default=None)
    parser.add_argument(
        "--orchestrator-root",
        required=True,
        help="epyc-orchestrator root, for the canonical REL-1 measurement guards",
    )
    parser.add_argument("--max-rows", type=int, default=20000)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    corpora = [Path(c) for c in args.corpus]
    ledger = build_ledger(
        corpora=corpora,
        pool_path=Path(args.pool),
        scorer_path=Path(args.scorer),
        seeding_path=Path(args.seeding_scoring) if args.seeding_scoring else None,
        orchestrator_root=Path(args.orchestrator_root),
        max_rows=args.max_rows,
    )

    text = json.dumps(ledger, indent=2, sort_keys=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    summary = ledger["summary"]
    print(
        f"scanned={summary['rows_scanned']} "
        f"agree={summary['dispositions'].get('agree', 0)} "
        f"divergence={summary['divergences']} "
        f"(favouring={summary['divergences_favouring_score']}, "
        f"against={summary['divergences_against_score']}) "
        f"excluded={summary['dispositions'].get('excluded', 0)} "
        f"quarantined={summary['quarantined_rows']}",
        file=sys.stderr,
    )
    # Fail-closed exit contract: unadjudicated divergences are a red gate.
    return 3 if summary["divergences"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
