"""Parity fixture: a ``seq_refuted`` result must be EXCLUDED from the learning
loop AND quarantined in the StrategyStore, at parity with any other
refuted/rejected result — while a clean (non-refuted) result is neither.

Background (fable5-window2-findings-01 R1 / findings-03 §A I1). The sequential
e-process verdict (``AUTOPILOT_SEQ_VERDICT``) can *refute* a candidate whose
broader safety verdict otherwise PASSES. Such a trial produces a clean journal
row, so without an explicit exclusion its refuted evidence could be distilled
back into strategy memory and re-injected as a "winning" pattern. The fix wires
``seq_refuted`` into the SAME exclusion + quarantine machinery that already
handles other refuted/rejected/learning-excluded results:

  * learning loop  — ``classify_learning_exclusion`` returns ``seq_refuted`` as a
    NON-corrupt learning exclusion (valid negative evidence, not measurement
    corruption); the autopilot record path skips ``archive.update`` for any
    non-empty ``learning_excluded_by`` and stamps
    ``eval_details["learning_exclusion"]``.
  * strategy store — ``_journal_entry_excludes_strategy_evidence`` treats a row
    carrying ``eval_details["learning_exclusion"]`` exactly like a
    ``bug_corrupted_by`` / ``keep_revert_decision == "excluded"`` row, so
    ``excluded_strategy_evidence_trial_ids`` / ``retrieve_for_journal`` drop the
    downstream strategy WITHOUT mutating the persisted DB (read-time policy).

This file is the "decisive experiment" named in findings-01 (§ Falsification):
replay a refuted -> passing sequence through the REAL functions
(``classify_learning_exclusion`` + ``retrieve_for_journal``) with ZERO
inference, and lock the parity as a regression guard.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from orchestration.repl_memory.strategy_store import (  # noqa: E402
    StrategyStore,
    excluded_strategy_evidence_trial_ids,
)
from src.autopilot_core.learning_exclusions import (  # noqa: E402
    NON_CORRUPT_LEARNING_EXCLUSIONS,
    classify_learning_exclusion,
)


# ── fakes ────────────────────────────────────────────────────────────────────
def _verdict(*, categories: list[str], passed: bool = True) -> SimpleNamespace:
    """Minimal SafetyVerdict stand-in (classify reads .categories / .passed)."""
    return SimpleNamespace(categories=list(categories), passed=passed)


def _eval_result() -> SimpleNamespace:
    """Minimal EvalResult stand-in with no corruption/exogenous signals set."""
    return SimpleNamespace(
        bug_corrupted_by="",
        bug_corrupted_reason="",
        n_exogenous_unrecovered=0,
        exogenous_question_ids=[],
        n_questions=0,
        oracle_adequacy={},
    )


class _MockEmbedder:
    """Deterministic hash-based embedder — no model, no network."""

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def embed_text(self, text: str) -> np.ndarray:
        h = hashlib.sha256(text.encode()).digest()
        rng = np.random.RandomState(int.from_bytes(h[:4], "big"))
        vec = rng.randn(self.dim).astype(np.float32)
        vec /= np.linalg.norm(vec) + 1e-9
        return vec


@pytest.fixture
def store(tmp_path):
    s = StrategyStore(path=tmp_path / "strategies", embedding_dim=1024, embedder=_MockEmbedder())
    yield s
    s.close()


# Trial ids used across the store + journal fixtures.
SEQ_REFUTED_TID = 201  # e-process refuted, broader safety verdict PASSED
REVERTED_TID = 202  # already-refuted/rejected result (parity anchor)
CLEAN_TID = 203  # sound, non-refuted result (control)


def _journal() -> SimpleNamespace:
    """Folded journal view with one row per trial id.

    The ``seq_refuted`` row mirrors exactly what autopilot writes: a
    ``learning_exclusion`` stamp with NO ``bug_corrupted_by`` (it is valid
    negative evidence, not corruption). The reverted row is the parity anchor.
    """

    def entries_with_supersessions():
        return [
            SimpleNamespace(
                trial_id=SEQ_REFUTED_TID,
                bug_corrupted_by="",
                outcome_status="ok",
                keep_revert_decision="",
                eval_details={
                    "learning_exclusion": {
                        "by": "seq_refuted",
                        "reason": "sequential e-process refuted the candidate improvement",
                    }
                },
            ),
            SimpleNamespace(
                trial_id=REVERTED_TID,
                bug_corrupted_by="",
                outcome_status="ok",
                keep_revert_decision="excluded",
                eval_details={},
            ),
            SimpleNamespace(
                trial_id=CLEAN_TID,
                bug_corrupted_by="",
                outcome_status="ok",
                keep_revert_decision="",
                eval_details={},
            ),
        ]

    return SimpleNamespace(entries_with_supersessions=entries_with_supersessions)


# ── learning-loop exclusion parity ──────────────────────────────────────────
def test_seq_refuted_is_excluded_from_learning_as_valid_negative_evidence():
    """A passing-verdict seq_refuted trial is excluded from learning, and it is a
    NON-corrupt exclusion — parity with other refuted results (excluded) but NOT
    relabelled as measurement corruption."""
    by, reason, def_cat = classify_learning_exclusion(
        _verdict(categories=["seq_refuted"]), _eval_result()
    )
    assert by == "seq_refuted", "refuted trial must be flagged as a learning exclusion"
    assert def_cat == "seq_refuted"
    assert "refuted" in reason.lower()
    # Valid negative evidence: excluded from learning, but NOT tagged as bug
    # corruption. The autopilot record path leans on this set to decide whether to
    # stamp bug_corrupted_by.
    assert "seq_refuted" in NON_CORRUPT_LEARNING_EXCLUSIONS


def test_non_refuted_result_is_not_excluded_from_learning():
    """The control: a clean, non-refuted passing verdict is included normally."""
    by, reason, def_cat = classify_learning_exclusion(
        _verdict(categories=[]), _eval_result()
    )
    assert (by, reason, def_cat) == ("", "", "")


# ── strategy-store quarantine parity ────────────────────────────────────────
def test_seq_refuted_evidence_is_quarantined_at_parity_with_reverted():
    """``excluded_strategy_evidence_trial_ids`` quarantines the seq_refuted trial
    IDENTICALLY to an already-refuted/reverted trial, and leaves the clean trial
    untouched."""
    excluded = excluded_strategy_evidence_trial_ids(_journal())
    assert SEQ_REFUTED_TID in excluded  # refuted evidence quarantined ...
    assert REVERTED_TID in excluded  # ... at parity with the reverted anchor
    assert CLEAN_TID not in excluded  # sound evidence is retrievable


def test_retrieve_for_journal_drops_seq_refuted_strategy_at_parity(store):
    """End-to-end through the REAL retrieval path: a strategy whose evidence is a
    seq_refuted trial is absent from retrieve_for_journal — parity with the
    reverted-derived strategy — while the clean-derived strategy survives. No DB
    row is deleted (read-time policy)."""
    seq_id = store.store(
        "Strategy from a refuted candidate",
        "Insight distilled from a seq_refuted trial",
        source_trial_id=SEQ_REFUTED_TID,
        species="alpha",
        evidence_trial_ids=[SEQ_REFUTED_TID],
    )
    reverted_id = store.store(
        "Strategy from a reverted candidate",
        "Insight distilled from an already-refuted trial",
        source_trial_id=REVERTED_TID,
        species="alpha",
        evidence_trial_ids=[REVERTED_TID],
    )
    clean_id = store.store(
        "Strategy from a sound candidate",
        "Insight distilled from a clean trial",
        source_trial_id=CLEAN_TID,
        species="alpha",
        evidence_trial_ids=[CLEAN_TID],
    )
    assert store.count() == 3  # nothing deleted at write time

    results = store.retrieve_for_journal("Strategy", journal=_journal(), k=10)
    result_ids = {r.id for r in results}

    # seq_refuted-derived strategy is quarantined at parity with the reverted one.
    assert seq_id not in result_ids
    assert reverted_id not in result_ids
    # The clean-derived strategy remains retrievable.
    assert clean_id in result_ids
    # Read-time policy: the rows still physically exist.
    assert store.count() == 3


def test_seq_refuted_quarantine_needs_the_journal_stamp(store):
    """Guard against silent regression: WITHOUT the folded journal (no exclusion
    evidence) the seq_refuted-derived strategy is retrievable; the quarantine is
    driven entirely by the journal ``learning_exclusion`` stamp."""
    seq_id = store.store(
        "Strategy from a refuted candidate",
        "Insight distilled from a seq_refuted trial",
        source_trial_id=SEQ_REFUTED_TID,
        species="alpha",
        evidence_trial_ids=[SEQ_REFUTED_TID],
    )
    unfiltered = {r.id for r in store.retrieve("Strategy", k=10)}
    assert seq_id in unfiltered, "sanity: strategy is retrievable absent the journal stamp"

    filtered = {r.id for r in store.retrieve_for_journal("Strategy", journal=_journal(), k=10)}
    assert seq_id not in filtered, "journal stamp must quarantine it"
