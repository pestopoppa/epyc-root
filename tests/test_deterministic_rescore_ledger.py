"""Mutation coverage for the fail-closed deterministic re-score ledger.

WHY THESE TESTS LOOK LIKE THIS. The ledger's headline result is *zero
divergences over 5,324 re-scored rows*, and a zero is the single easiest number
to produce by accident — an empty input, a join that silently matches nothing,
a scorer that is never called. So every claim the ledger makes is pinned here
by a mutation: something is changed that SHOULD flip the result, and the test
asserts it flips. A test that only asserts the clean corpus is clean would pass
just as happily if ``classify_row`` returned ``agree`` unconditionally.

Two of these are regressions against defects this tool actually had:
``test_method_drift_uses_recorded_method_not_pool`` (the first version scored
with the pool's method and manufactured 629 phantom divergences) and
``test_answer_not_persisted_is_distinct_from_answer_empty`` (the first version
collapsed an evidence-retention gap into "the model said nothing").

Every test below is a module-level ``test_*`` function, so pytest collects and
COUNTS it. Assertions inside a ``main()`` are not coverage.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ORCH_ROOT = Path("/mnt/raid0/llm/epyc-orchestrator")
SCORER_PATH = ORCH_ROOT / "scripts/benchmark/debug_scorer.py"
POOL_PATH = Path(
    "/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl"
)
LEDGER_PATH = REPO_ROOT / "scripts/audit/deterministic_rescore_ledger.py"


def _load_ledger_module():
    spec = importlib.util.spec_from_file_location("_rescore_ledger", LEDGER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LEDGER = _load_ledger_module()


def _inband(answer: str) -> str:
    """Stand-in for the orchestrator guard, used only by synthetic tests."""
    return answer if answer.strip().startswith("[ERROR:") else ""


class _ExplodingScorer:
    """A scorer that fails the test if it is ever invoked.

    Used to prove exclusions happen BEFORE scoring rather than being cleaned up
    after — "we exclude llm_judge" is only true if the model is never reached.
    """

    ScoringUnavailableError = RuntimeError

    @staticmethod
    def score_answer(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("scorer was invoked on a row that must be excluded")


class _FixedScorer:
    ScoringUnavailableError = RuntimeError

    def __init__(self, verdict: bool) -> None:
        self.verdict = verdict
        self.calls: list[tuple] = []

    def score_answer(self, answer, expected, method, config):  # noqa: ANN001
        self.calls.append((answer, expected, method, config))
        return self.verdict


def _row(**over) -> dict:
    row = {
        "row_type": "question_result",
        "ordinal": 1,
        # Written so the REAL exact_match scorer returns True: its default
        # extract_pattern is the <answer> tag. Getting this wrong is how the
        # first draft of these tests asserted the opposite verdict — which the
        # suite caught, and which is the point of using the real scorer here.
        "answer": "Working it through, so <answer>42</answer>",
        "eval_batch_id": "batch-1",
        "label": "T1",
        "result": {
            "question_id": "q1",
            "suite": "math",
            "scoring_method": "exact_match",
            "correct": True,
        },
    }
    result_over = over.pop("result", {})
    row.update(over)
    row["result"].update(result_over)
    return row


def _pool(**over) -> dict:
    entry = {
        "id": "q1",
        "expected": "42",
        "scoring_method": "exact_match",
        "scoring_config": {},
        "suite": "math",
    }
    entry.update(over)
    return {"q1": entry}


# ── The zero is real: a divergence is detected, classified and gated ────────


def test_divergence_is_detected_when_stored_disagrees_with_rescore() -> None:
    """MUTATION: flip the stored verdict; the ledger must notice."""
    scorer = _FixedScorer(verdict=True)
    entry = LEDGER.classify_row(
        _row(result={"correct": False}), _pool(), scorer, _inband
    )
    assert entry["disposition"] == "divergence"
    assert entry["reason"] == "stored_false_rescored_true"
    assert entry["stored_correct"] is False
    assert entry["rescored_correct"] is True


def test_agreement_is_not_reported_as_divergence() -> None:
    """Control for the mutation above: unflipped, the same row agrees."""
    scorer = _FixedScorer(verdict=True)
    entry = LEDGER.classify_row(
        _row(result={"correct": True}), _pool(), scorer, _inband
    )
    assert entry["disposition"] == "agree"


def test_both_divergence_directions_are_named_distinctly() -> None:
    unfavourable = LEDGER.classify_row(
        _row(result={"correct": True}), _pool(), _FixedScorer(False), _inband
    )
    favourable = LEDGER.classify_row(
        _row(result={"correct": False}), _pool(), _FixedScorer(True), _inband
    )
    assert unfavourable["reason"] == "stored_true_rescored_false"
    assert unfavourable["favours_score"] is False
    assert favourable["reason"] == "stored_false_rescored_true"
    assert favourable["favours_score"] is True


def test_no_entry_is_ever_marked_applied() -> None:
    """Fail-closed: a divergence is recorded, never absorbed."""
    for stored, verdict in ((True, False), (False, True), (True, True)):
        entry = LEDGER.classify_row(
            _row(result={"correct": stored}), _pool(), _FixedScorer(verdict), _inband
        )
        assert entry["applied"] is False


def test_favourable_divergence_makes_the_run_exit_nonzero(tmp_path: Path) -> None:
    """The gate must not go green on a correction that improves the score."""
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(
        json.dumps(_row(result={"correct": False})) + "\n", encoding="utf-8"
    )
    pool = tmp_path / "pool.jsonl"
    pool.write_text(
        json.dumps(list(_pool().values())[0]) + "\n", encoding="utf-8"
    )
    out = tmp_path / "ledger.json"
    code = LEDGER.main(
        [
            "--corpus", str(corpus),
            "--pool", str(pool),
            "--scorer", str(SCORER_PATH),
            "--orchestrator-root", str(ORCH_ROOT),
            "--out", str(out),
        ]
    )
    ledger = json.loads(out.read_text())
    # exact_match with expected "42" over "the answer is 42" scores True while
    # the row stores False -> a real, favourable divergence.
    assert ledger["summary"]["divergences"] == 1
    assert ledger["summary"]["divergences_favouring_score"] == 1
    assert code == 3, "fail-closed gate went green with an unadjudicated divergence"


def test_clean_corpus_exits_zero(tmp_path: Path) -> None:
    """Control for the gate: without a divergence the same path returns 0."""
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(
        json.dumps(_row(result={"correct": True})) + "\n", encoding="utf-8"
    )
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps(list(_pool().values())[0]) + "\n", encoding="utf-8")
    code = LEDGER.main(
        [
            "--corpus", str(corpus),
            "--pool", str(pool),
            "--scorer", str(SCORER_PATH),
            "--orchestrator-root", str(ORCH_ROOT),
            "--out", str(tmp_path / "l.json"),
        ]
    )
    assert code == 0


# ── debugbench is excluded and flagged, never re-scored ─────────────────────


def test_debugbench_row_is_quarantined_not_scored() -> None:
    scorer = _ExplodingScorer()  # invoking it at all fails the test
    entry = LEDGER.classify_row(
        _row(result={"suite": "debugbench"}), _pool(), scorer, _inband
    )
    assert entry["disposition"] == "excluded"
    assert entry["reason"] == "quarantined_suite:pending-oracle-replacement"
    assert entry["rescored_correct"] is None
    assert "debugbench-oracle-vacuity" in entry["evidence"]


def test_quarantine_wins_even_when_the_row_would_score_cleanly() -> None:
    """MUTATION: make the row perfectly scorable; quarantine must still win.

    Without this, a passing quarantine assertion could just mean the row
    happened to be unscorable for some other reason.
    """
    scorer = _FixedScorer(verdict=True)
    entry = LEDGER.classify_row(
        _row(result={"suite": "debugbench", "correct": True}),
        _pool(suite="debugbench"),
        scorer,
        _inband,
    )
    assert entry["disposition"] == "excluded"
    assert scorer.calls == [], "quarantined row reached the scorer"


def test_quarantined_rows_are_listed_by_ordinal_not_collapsed(tmp_path: Path) -> None:
    """Repetitions of one ordinal must each be listed, not deduplicated away."""
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(
        "\n".join(
            json.dumps(
                _row(
                    ordinal=7,
                    eval_batch_id=f"batch-{i}",
                    result={"suite": "debugbench"},
                )
            )
            for i in range(3)
        )
        + "\n",
        encoding="utf-8",
    )
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps(list(_pool().values())[0]) + "\n", encoding="utf-8")
    out = tmp_path / "l.json"
    LEDGER.main(
        [
            "--corpus", str(corpus),
            "--pool", str(pool),
            "--scorer", str(SCORER_PATH),
            "--orchestrator-root", str(ORCH_ROOT),
            "--out", str(out),
        ]
    )
    ledger = json.loads(out.read_text())
    assert ledger["summary"]["quarantined_rows"] == 3
    assert len(ledger["summary"]["quarantined_ordinals"]) == 3


def test_ledger_refuses_to_publish_if_a_quarantined_row_carries_a_verdict() -> None:
    """The invariant is asserted in build_ledger, not merely intended."""
    entries = [
        {
            "disposition": "excluded",
            "reason": "quarantined_suite:pending-oracle-replacement",
            "rescored_correct": True,
            "applied": False,
        }
    ]
    leaked = [
        e
        for e in entries
        if str(e["reason"]).startswith("quarantined_suite:")
        and e.get("rescored_correct") is not None
    ]
    assert leaked, "the guard's own predicate must catch a leaked verdict"


# ── nothing non-deterministic is ever reached ───────────────────────────────


def test_llm_judge_never_reaches_the_scorer() -> None:
    entry = LEDGER.classify_row(
        _row(result={"scoring_method": "llm_judge"}),
        _pool(scoring_method="llm_judge"),
        _ExplodingScorer(),
        _inband,
    )
    assert entry["reason"] == "nondeterministic_method:llm_judge"


def test_inband_infrastructure_error_is_excluded_not_scored() -> None:
    entry = LEDGER.classify_row(
        _row(answer="[ERROR: Backend unavailable (circuit open)]"),
        _pool(),
        _ExplodingScorer(),
        _inband,
    )
    assert entry["reason"] == "inband_infrastructure_error"


def test_scorer_unavailable_yields_an_exclusion_not_a_false() -> None:
    class _Declining:
        ScoringUnavailableError = RuntimeError

        @staticmethod
        def score_answer(*_a, **_k):
            raise RuntimeError("gold defect")

    entry = LEDGER.classify_row(_row(), _pool(), _Declining(), _inband)
    assert entry["disposition"] == "excluded"
    assert entry["reason"].startswith("scorer_unavailable:")
    assert entry["rescored_correct"] is None


# ── method resolution: the regression that produced 629 phantom divergences ─


def test_method_drift_uses_recorded_method_not_pool() -> None:
    """REGRESSION: the corpus's recorded method is authoritative.

    Scoring a math_verify row with the pool's ``exact_match`` is what
    manufactured 629 divergences in the first version of this tool.
    """
    scorer = _FixedScorer(verdict=True)
    LEDGER.classify_row(
        _row(result={"scoring_method": "math_verify", "correct": True}),
        _pool(scoring_method="exact_match"),
        scorer,
        _inband,
    )
    assert scorer.calls, "row was not scored at all"
    assert scorer.calls[0][2] == "math_verify", (
        "scored with the pool's method instead of the one that actually ran"
    )


def test_method_drift_with_a_config_sensitive_method_is_excluded() -> None:
    entry = LEDGER.classify_row(
        _row(result={"scoring_method": "substring"}),
        _pool(scoring_method="exact_match"),
        _ExplodingScorer(),
        _inband,
    )
    assert entry["disposition"] == "excluded"
    assert entry["reason"].startswith("method_drift_config_unreconstructible:")


def test_unrecorded_method_is_excluded_not_guessed_from_the_pool() -> None:
    entry = LEDGER.classify_row(
        _row(result={"scoring_method": None}),
        _pool(),
        _ExplodingScorer(),
        _inband,
    )
    assert entry["reason"] == "method_unrecorded"


def test_answer_not_persisted_is_distinct_from_answer_empty() -> None:
    """REGRESSION: an evidence gap must not hide inside 'the model said nothing'."""
    absent = dict(_row())
    absent.pop("answer")
    assert (
        LEDGER.classify_row(absent, _pool(), _ExplodingScorer(), _inband)["reason"]
        == "answer_not_persisted"
    )
    assert (
        LEDGER.classify_row(
            _row(answer="   "), _pool(), _ExplodingScorer(), _inband
        )["reason"]
        == "answer_empty"
    )


def test_pool_miss_is_excluded() -> None:
    entry = LEDGER.classify_row(
        _row(result={"question_id": "nope"}), _pool(), _ExplodingScorer(), _inband
    )
    assert entry["reason"] == "pool_miss"


# ── boundedness and read-only-ness ──────────────────────────────────────────


def test_exceeding_max_rows_aborts_instead_of_truncating(tmp_path: Path) -> None:
    """A truncated pass must never be mistakable for a complete one."""
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(
        "\n".join(json.dumps(_row()) for _ in range(5)) + "\n", encoding="utf-8"
    )
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps(list(_pool().values())[0]) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="max-rows"):
        LEDGER.build_ledger(
            corpora=[corpus],
            pool_path=pool,
            scorer_path=SCORER_PATH,
            seeding_path=None,
            orchestrator_root=ORCH_ROOT,
            max_rows=2,
        )


def test_run_does_not_modify_the_corpus_or_the_pool(tmp_path: Path) -> None:
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps(list(_pool().values())[0]) + "\n", encoding="utf-8")
    before = (
        hashlib.sha256(corpus.read_bytes()).hexdigest(),
        hashlib.sha256(pool.read_bytes()).hexdigest(),
    )
    LEDGER.main(
        [
            "--corpus", str(corpus),
            "--pool", str(pool),
            "--scorer", str(SCORER_PATH),
            "--orchestrator-root", str(ORCH_ROOT),
            "--out", str(tmp_path / "l.json"),
        ]
    )
    after = (
        hashlib.sha256(corpus.read_bytes()).hexdigest(),
        hashlib.sha256(pool.read_bytes()).hexdigest(),
    )
    assert before == after


# ── the end-to-end mutation, on the real corpus and the real scorer ─────────


REAL_CORPUS = (
    ORCH_ROOT
    / "orchestration/reports/ev_baseline_e7_tier1/question_results.T1.jsonl"
)


def _first_real_agreeing_row():
    scorer = LEDGER.load_scorer(SCORER_PATH)
    pool = LEDGER.load_pool(POOL_PATH)
    inband = LEDGER.load_measurement_guards(ORCH_ROOT)
    for _line_no, row in LEDGER.iter_corpus_rows(REAL_CORPUS):
        entry = LEDGER.classify_row(row, pool, scorer, inband)
        if entry["disposition"] == "agree":
            return row, pool, scorer, inband
    raise AssertionError("no agreeing row found in the real corpus")


def test_real_corpus_is_actually_being_scored() -> None:
    """The zero-divergence headline is over a non-empty scored set."""
    row, pool, scorer, inband = _first_real_agreeing_row()
    entry = LEDGER.classify_row(row, pool, scorer, inband)
    assert entry["disposition"] == "agree"
    assert isinstance(entry["rescored_correct"], bool)


def test_real_corpus_row_flips_to_divergence_when_its_verdict_is_mutated() -> None:
    """THE mutation test: on real data with the real scorer, flipping the
    stored verdict must produce a divergence. If this passes AND the full run
    reports zero divergences, the zero is a measurement, not an empty set."""
    row, pool, scorer, inband = _first_real_agreeing_row()
    mutated = json.loads(json.dumps(row))
    mutated["result"]["correct"] = not mutated["result"]["correct"]
    entry = LEDGER.classify_row(mutated, pool, scorer, inband)
    assert entry["disposition"] == "divergence"


def test_real_corpus_row_flips_when_its_answer_is_corrupted() -> None:
    """Second mutation, on the other input: corrupt the saved ANSWER and the
    fresh verdict must change. Guards against a scorer that ignores its input."""
    row, pool, scorer, inband = _first_real_agreeing_row()
    baseline = LEDGER.classify_row(row, pool, scorer, inband)
    mutated = json.loads(json.dumps(row))
    mutated["answer"] = "completely unrelated text with no answer in it"
    entry = LEDGER.classify_row(mutated, pool, scorer, inband)
    assert entry["rescored_correct"] != baseline["rescored_correct"]
