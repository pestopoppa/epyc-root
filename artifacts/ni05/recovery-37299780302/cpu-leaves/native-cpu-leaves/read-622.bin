"""RTG-55 MHS-3 (2026-09-15 structural form) — eval CONTENT leakage refusals.

Beyond the id vocabulary, PromptForge refuses a mutation whose ADDED text
  * shares a verbatim >= 8-token n-gram with eval content or the trace bank,
  * carries an exact expected answer,
  * was derived from a trace of an eval question (source identity),
  * special-cases an eval suite that IS in the source context.
The content index is built in the vocabulary pass and shares its fail-closed cache.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(AUTOPILOT_DIR))

import species.prompt_forge as pf  # noqa: E402
from species.prompt_forge import (  # noqa: E402
    CODE_MUTATION_ALLOWLIST,
    EvalIdVocabulary,
    PromptForge,
    PromptMutation,
    eval_leakage_reason,
    harness_content,
    load_eval_id_vocabulary,
    suite_special_casing_reason,
)

PASSAGE = (
    "The quartermaster Zebulon Farquharson inventoried seventeen brass astrolabes "
    "aboard the schooner Wandering Heron before the equinox storm"
)
TRACED_QUESTION = (
    "Which cartographer named Ignatius Pemberton charted the Vorlaxian archipelago "
    "using a heliograph relay in the winter expedition?"
)
TEMPLATE = "Answer the following question and put the final result inside the answer tags please"
ROWS = [
    {"id": "fixture_story_0001", "suite": "hotpotqa", "prompt": PASSAGE, "expected": "Farquharson"},
    {
        "id": "fixture_story_0002",
        "suite": "simpleqa",
        "prompt": "Who?",
        "expected": "Michio Sugeno",
    },
    {"id": "fixture_story_0003", "suite": "math", "prompt": "Sum?", "expected": "145"},
    {"id": "fixture_story_0004", "suite": "math", "prompt": "Word?", "expected": "contention"},
    {
        "id": "fixture_story_0005",
        "suite": "tool_use",
        "prompt": "T",
        "expected": "__resolved_at_runtime__",
    },
    {
        "id": "fixture_trace_0006",
        "suite": "hotpotqa",
        "prompt": TRACED_QUESTION,
        "expected": "1847",
    },
    {
        "id": "fixture_code_0007",
        "suite": "coder",
        "prompt": "Write it.",
        "expected": "has_close_elements",
    },
    {"id": "fixture_gsm_0008", "suite": "gsm8k", "prompt": "How many?", "expected": "7"},
] + [
    {"id": f"fixture_tmpl_{i:04d}", "suite": "general", "prompt": f"Item {i}. {TEMPLATE}"}
    for i in range(pf._CONTENT_TEMPLATE_DF)
]


def _empty_harness() -> pf._HarnessContent:
    empty = np.empty(0, dtype=np.uint64)
    return pf._HarnessContent(shingles=empty, tokens=empty, token_files=np.empty(0, np.int64))


EMPTY = _empty_harness()


@pytest.fixture(scope="module")
def vocab() -> EvalIdVocabulary:
    built = EvalIdVocabulary.from_rows(ROWS, sources=("fixture",))
    assert built.available
    return built


def _reason(text: str, vocabulary: EvalIdVocabulary, **kw) -> str | None:
    kw.setdefault("harness", EMPTY)
    return eval_leakage_reason(text, vocabulary, **kw)


def _write_jsonl(path: Path, rows) -> Path:
    lines = [json.dumps({"__pool_metadata__": True})] + [json.dumps(r) for r in rows]
    path.write_text("\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------------------
# Tokeniser / hashing / packed index
# ---------------------------------------------------------------------------


def test_token_hash_is_position_and_case_independent() -> None:
    _b, _s, _e, h = pf._content_tokens("Alpha, beta! ALPHA gamma_1 héllo")
    assert h[0] == h[2] and h[0] != h[1]
    assert pf._content_tokens("x alpha")[3][1] == h[0]
    assert h.size == 5


def test_chunked_hashing_matches_single_buffer(monkeypatch) -> None:
    text = " ".join(f"word{i % 97} tok{i}" for i in range(4000))
    whole = pf._content_tokens(text)
    monkeypatch.setattr(pf, "_CONTENT_CHUNK_BYTES", 1000)
    pieces = pf._content_tokens(text)
    assert np.array_equal(whole[3], pieces[3])
    assert np.array_equal(whole[1], pieces[1]) and np.array_equal(whole[2], pieces[2])


def test_packed_lookup_matches_a_set() -> None:
    rng = np.random.default_rng(3)
    keys = rng.integers(0, 2**63, size=5000, dtype=np.uint64)
    rows = rng.integers(0, 1000, size=5000).astype(np.uint64)
    bits = 10
    packed = np.sort(((keys >> np.uint64(bits)) << np.uint64(bits)) | rows)
    probe = np.concatenate([keys[:100], rng.integers(0, 2**63, size=100, dtype=np.uint64)])
    found = pf._packed_lookup(packed, probe, bits)
    assert np.array_equal(found[:100], rows[:100].astype(np.int64))
    assert (found[100:] == -1).all()


# ---------------------------------------------------------------------------
# Refusal 1 — verbatim n-gram overlap
# ---------------------------------------------------------------------------


def test_ngram_overlap_with_eval_row_is_refused_with_source_id(vocab) -> None:
    text = "Tip: inventoried seventeen brass astrolabes aboard the schooner Wandering Heron."
    reason = _reason(text, vocab)
    assert reason is not None and reason.startswith("eval_content_ngram_overlap")
    assert "source=fixture_story_0001" in reason


def test_overlap_is_punctuation_and_case_insensitive(vocab) -> None:
    text = "ZEBULON-farquharson; inventoried... SEVENTEEN brass, astrolabes aboard THE!"
    assert (_reason(text, vocab) or "").startswith("eval_content_ngram_overlap")


def test_seven_token_overlap_is_not_refused(vocab) -> None:
    assert _reason("inventoried seventeen brass astrolabes aboard the schooner", vocab) is None


def test_overlap_already_in_original_is_not_blamed(vocab) -> None:
    text = "inventoried seventeen brass astrolabes aboard the schooner Wandering Heron"
    assert _reason(text, vocab, original=f"Legacy example: {text}\n") is None


def test_overlap_already_in_harness_is_not_blamed(vocab) -> None:
    text = "inventoried seventeen brass astrolabes aboard the schooner Wandering Heron"
    harness = pf._text_shingles_tokens([text])
    assert _reason(text, vocab, harness=harness) is None


def test_template_text_shared_by_many_rows_is_not_refused(vocab) -> None:
    assert _reason(TEMPLATE, vocab) is None


def test_unanchored_overlap_needs_a_long_verbatim_run(monkeypatch) -> None:
    monkeypatch.setattr(pf, "_CONTENT_RARE_TF", 0)  # nothing is rare -> no anchors
    vocab = EvalIdVocabulary.from_rows(ROWS)
    words = pf._content_tokens(PASSAGE)[0].decode().split()
    needed = pf._CONTENT_NGRAM + pf._CONTENT_MIN_UNANCHORED_RUN - 1  # 15 tokens
    assert len(words) > needed
    assert _reason(" ".join(words[: needed - 1]), vocab) is None
    assert (_reason(" ".join(words[:needed]), vocab) or "").startswith("eval_content_ngram_overlap")


def test_long_row_edges_are_exact_and_middle_is_winnowed(monkeypatch) -> None:
    monkeypatch.setattr(pf, "_CONTENT_LONG_ROW_BYTES", 2000)
    monkeypatch.setattr(pf, "_CONTENT_LONG_EDGE_SHINGLES", 20)
    words = [f"lexeme{i}x" for i in range(3000)]
    row = {"id": "fixture_long_0001", "suite": "longbench", "prompt": " ".join(words)}
    vocab = EvalIdVocabulary.from_rows([row])
    assert dict(vocab.content.stats)["long_rows"] == 1
    assert vocab.content.shingles.size < 3000
    head = " ".join(words[3:11])  # 8 tokens inside the exact head
    assert (_reason(head, vocab) or "").startswith("eval_content_ngram_overlap")
    guaranteed = pf._CONTENT_NGRAM + pf._CONTENT_WINNOW - 1
    middle = " ".join(words[1500 : 1500 + guaranteed])
    assert (_reason(middle, vocab) or "").startswith("eval_content_ngram_overlap")


TRACE_CONTEXT = (
    "## Previously Rejected Mutations of `x.md`\n- none\n\n"
    "## Contrastive Execution Traces\n### Failure Examples\n"
    "[1] trial #41, prompt_forge/targeted_fix\nReason: wrong answer\nTrace:\n"
    "ROLE worker\nPROMPT:\n" + TRACED_QUESTION + "\nRESPONSE:\n"
    "The obsidian lighthouse keeper transmitted coordinates through mirrored semaphore towers\n\n"
    "## Past Strategy Insights\n- Trial #3 (prompt_forge): kept answers short and precise always\n"
)


def test_ngram_overlap_with_trace_bank_is_refused(vocab) -> None:
    text = "Use this: obsidian lighthouse keeper transmitted coordinates through mirrored semaphore towers."
    reason = _reason(text, vocab, trace_context=TRACE_CONTEXT)
    assert reason is not None and reason.startswith("eval_content_ngram_overlap")
    assert "source=trace_bank[[1] trial #41" in reason
    assert "fixture_trace_0006" in reason  # the traced question id is recorded


def test_text_outside_trace_sections_is_not_trace_bank(vocab) -> None:
    text = "Trial insight: kept answers short and precise always when possible"
    assert _reason(text, vocab, trace_context=TRACE_CONTEXT) is None


# ---------------------------------------------------------------------------
# Refusal 2 — exact expected answer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, source",
    [
        ("If unsure, answer Michio Sugeno.", "fixture_story_0002"),
        ('return "has_close_elements"', "fixture_code_0007"),
    ],
)
def test_expected_answer_is_refused(vocab, text: str, source: str) -> None:
    reason = _reason(text, vocab)
    assert reason is not None and reason.startswith("eval_expected_answer_leakage"), reason
    assert f"source={source}" in reason


@pytest.mark.parametrize(
    "text",
    [
        "Avoid lock contention between workers.",  # plain lower-case one-word answer
        "The sum is 145 here.",  # bare numbers never anchor
        "value = '__resolved_at_runtime__'",  # placeholder answers are not answers
        "Michio alone is not the answer.",  # partial multi-token answer
    ],
)
def test_non_identifying_answers_are_not_refused(vocab, text: str) -> None:
    assert _reason(text, vocab) is None


def test_answer_present_in_harness_is_not_refused(vocab) -> None:
    harness = pf._text_shingles_tokens(["def has_close_elements(values): ..."])
    assert _reason('return "has_close_elements"', vocab, harness=harness) is None


def test_sentinel_expected_answer_is_refused(tmp_path: Path) -> None:
    pool = _write_jsonl(tmp_path / "question_pool.jsonl", ROWS)
    sentinels = tmp_path / "sentinel_questions.yaml"
    sentinels.write_text(
        '- id: sentinel_general_01\n  suite: general\n  prompt: "Capital of Australia?"\n'
        '  expected: "Canberra"\n'
    )
    vocab = load_eval_id_vocabulary(((pool, True), (sentinels, False)))
    reason = _reason("When asked about capitals, Canberra is a safe bet.", vocab)
    assert reason is not None and reason.startswith("eval_expected_answer_leakage")
    assert "source=sentinel_questions.yaml:sentinel_general_01" in reason


# ---------------------------------------------------------------------------
# Refusal 3 — source identity (paraphrase of a traced eval question)
# ---------------------------------------------------------------------------

PARAPHRASE = (
    "Example: if a mapmaker (say Pemberton) surveyed the Vorlaxian islands with a "
    "heliograph, reason step by step."
)


def test_paraphrase_of_traced_question_is_refused(vocab) -> None:
    reason = _reason(PARAPHRASE, vocab, trace_context=TRACE_CONTEXT)
    assert reason is not None and reason.startswith("eval_source_identity_leakage"), reason
    assert "fixture_trace_0006" in reason
    assert "trial #41" in reason


def test_paraphrase_without_trace_context_is_not_refused(vocab) -> None:
    assert _reason(PARAPHRASE, vocab) is None


def test_two_shared_rare_tokens_are_not_enough(vocab) -> None:
    text = "Example: a mapmaker called Pemberton used a heliograph."
    assert _reason(text, vocab, trace_context=TRACE_CONTEXT) is None


def test_unresolvable_trace_does_not_trigger_source_identity(vocab) -> None:
    context = (
        "## Recent Execution Traces\nROLE worker\nPROMPT:\n"
        "Pemberton Vorlaxian heliograph unrelated scratch text\n"
    )
    assert _reason(PARAPHRASE, vocab, trace_context=context) is None


def test_trace_ir_explicit_question_id_resolves() -> None:
    rows = [{"id": "fixture_other_0001", "suite": "general", "prompt": "Unrelated text only."}]
    vocab = EvalIdVocabulary.from_rows(rows)
    ir = {
        "trace_examples": [
            {
                "outcome": "failure",
                "trial_id": 9,
                "trace_hash": "abc123",
                "question_id": "gpqa_diamond_0042",
                "steps": [{"content_preview": "Pemberton charted Vorlaxian isles by heliograph"}],
            }
        ]
    }
    context = (
        "## Harness Trace IR (MH-11 observe-only)\nThis structured trace evidence is diagnostic.\n"
        f"```json\n{json.dumps(ir, indent=2)}\n```\n"
    )
    reason = _reason(PARAPHRASE, vocab, trace_context=context)
    assert reason is not None and reason.startswith("eval_source_identity_leakage"), reason
    assert "gpqa_diamond_0042" in reason and "trial #9" in reason


def test_trace_blocks_parse_all_three_renderings() -> None:
    blocks = pf._trace_blocks(
        TRACE_CONTEXT
        + "\n## Recent Execution Traces\nraw tail here\n\nTrial #5 (prompt_forge):\nanalysis\n"
        + "## Harness Trace IR (MH-11 observe-only)\n```json\nnot json\n```\n"
    )
    labels = [label for label, _ in blocks]
    assert labels[0].startswith("[1] trial #41")
    assert "Past Strategy Insights" not in blocks[0][1]
    assert "recent_traces" in labels and "trace_ir" in labels
    recent = dict(blocks)["recent_traces"]
    assert "raw tail here" in recent and "analysis" not in recent
    assert pf._trace_blocks("no traces at all") == []


# ---------------------------------------------------------------------------
# In-suite special-casing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "added, form",
    [
        ('    if suite == "math":\n        return 3', "keyed"),
        ('    if row["suite"] in ("coder", "math"):', "keyed"),
        ('    if benchmark_name.startswith("hotpotqa"):', "keyed"),
        ("For the math benchmark, restate units.", "keyed"),
        ("Treat gsm8k problems with extra care.", "phrase"),
        ("Remember that hotpotqa needs two hops.", "mention"),
    ],
)
def test_suite_special_casing_is_refused(vocab, added: str, form: str) -> None:
    reason = suite_special_casing_reason("base\n", f"base\n{added}\n", vocab, harness=EMPTY)
    assert reason is not None and reason.startswith("eval_suite_special_casing"), (added, reason)
    assert f"form={form}" in reason


@pytest.mark.parametrize(
    "original, mutated",
    [
        ("base\n", "base\nFor math problems, show the working.\n"),  # common word, bare
        ("Use hotpotqa style.\n", "Use hotpotqa style, briefly.\n"),  # count unchanged
        ("base\n", "base\nrole = 'coder'\n"),  # not keyed on a suite identifier
    ],
)
def test_suite_special_casing_negatives(vocab, original: str, mutated: str) -> None:
    assert suite_special_casing_reason(original, mutated, vocab, harness=EMPTY) is None


def test_harness_vocabulary_suite_name_is_not_a_bare_mention(vocab) -> None:
    _b, _s, _e, hashes = pf._content_tokens("tool_use")
    harness = pf._HarnessContent(
        shingles=np.empty(0, np.uint64),
        tokens=np.sort(hashes),
        token_files=np.array([pf._SUITE_HARNESS_VOCAB_FILES]),
    )
    added = "base\nPrefer tool_use traces.\n"
    assert suite_special_casing_reason("base\n", added, vocab, harness=EMPTY) is not None
    assert suite_special_casing_reason("base\n", added, vocab, harness=harness) is None
    keyed = 'base\nif suite == "tool_use":\n'
    assert suite_special_casing_reason("base\n", keyed, vocab, harness=harness) is not None


# ---------------------------------------------------------------------------
# PromptForge wiring: one checker for prompt, code and GEPA mutations
# ---------------------------------------------------------------------------


def _forge(tmp_path: Path, vocab, response: str, monkeypatch) -> PromptForge:
    (tmp_path / "worker_math.md").write_text("Base prompt\nBe careful.\n")
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=vocab)
    monkeypatch.setattr(forge, "_invoke_claude", lambda _prompt: response)
    return forge


def test_prompt_mutation_from_traced_question_is_rejected(tmp_path, vocab, monkeypatch) -> None:
    forge = _forge(
        tmp_path, vocab, f"```markdown\nBase prompt\nBe careful.\n{PARAPHRASE}\n```", monkeypatch
    )
    mutation = forge.propose_mutation(
        "worker_math.md", failure_context=TRACE_CONTEXT, per_suite_quality={"hotpotqa": 1.0}
    )
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_source_identity_leakage")
    assert mutation.mutated_content == mutation.original_content


def test_prompt_mutation_with_in_suite_special_casing_is_rejected(
    tmp_path, vocab, monkeypatch
) -> None:
    text = "For hotpotqa questions, always cite both paragraphs."
    forge = _forge(
        tmp_path, vocab, f"```markdown\nBase prompt\nBe careful.\n{text}\n```", monkeypatch
    )
    mutation = forge.propose_mutation(
        "worker_math.md",
        failure_context="Trial #1 hotpotqa miss",
        per_suite_quality={"hotpotqa": 1.0},
    )
    assert mutation.safety_valid is False
    # The AP-33 universal-practice refusal keeps precedence for its own shape.
    assert mutation.safety_reason.startswith("misapplied_best_practice")
    text = "For hotpotqa questions, cite both paragraphs."
    forge = _forge(
        tmp_path, vocab, f"```markdown\nBase prompt\nBe careful.\n{text}\n```", monkeypatch
    )
    mutation = forge.propose_mutation(
        "worker_math.md",
        failure_context="Trial #1 hotpotqa miss",
        per_suite_quality={"hotpotqa": 1.0},
    )
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_suite_special_casing"), mutation.safety_reason


def test_clean_prompt_mutation_with_traces_is_accepted(tmp_path, vocab, monkeypatch) -> None:
    forge = _forge(
        tmp_path,
        vocab,
        "```markdown\nBase prompt\nBe careful.\nRe-check units first.\n```",
        monkeypatch,
    )
    mutation = forge.propose_mutation("worker_math.md", failure_context=TRACE_CONTEXT)
    assert mutation.safety_valid is True, mutation.safety_reason


def test_code_mutation_hardcoding_an_expected_answer_is_rejected(
    tmp_path, vocab, monkeypatch
) -> None:
    target = "src/tool_policy.py"
    original = (ROOT / target).read_text()
    response = f'```python\n{original}\nKNOWN_NAME = "Michio Sugeno"\n```'
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=vocab)
    monkeypatch.setattr(forge, "_invoke_claude", lambda _p: response)
    mutation = forge.propose_code_mutation(target_file=target)
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_expected_answer_leakage")
    assert mutation.mutated_content == original


def test_code_mutation_comparing_to_a_suite_is_rejected(tmp_path, vocab, monkeypatch) -> None:
    target = "src/tool_policy.py"
    original = (ROOT / target).read_text()
    added = '\n\ndef _special(suite_name):\n    return suite_name == "gsm8k"\n'
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=vocab)
    monkeypatch.setattr(forge, "_invoke_claude", lambda _p: f"```python\n{original}{added}```")
    mutation = forge.propose_code_mutation(target_file=target, per_suite_quality={"gsm8k": 1.0})
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_suite_special_casing"), mutation.safety_reason


def test_gepa_mutation_copying_eval_content_is_rejected(tmp_path, vocab, monkeypatch) -> None:
    from scripts.autopilot.species import gepa_optimizer
    from species import gepa_optimizer as gepa_optimizer_alias

    class _FakeOptimizer:
        def __init__(self, **_kw) -> None:
            pass

        def run(self, **_kw):
            return SimpleNamespace(
                to_prompt_mutation=lambda: PromptMutation(
                    file="worker_math.md",
                    mutation_type="gepa",
                    description="gepa",
                    original_content="Base\n",
                    mutated_content=f"Base\nExample: {PASSAGE}\n",
                )
            )

    for module in (gepa_optimizer, gepa_optimizer_alias):
        monkeypatch.setattr(module, "GEPAPromptOptimizer", _FakeOptimizer)
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=vocab)
    mutation = forge.propose_mutation("worker_math.md", mutation_type="gepa", eval_tower=object())
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_content_ngram_overlap")
    assert mutation.mutated_content == "Base\n"


# ---------------------------------------------------------------------------
# Fail-closed semantics and caching
# ---------------------------------------------------------------------------


def test_vocabulary_without_content_index_is_unavailable() -> None:
    bare = EvalIdVocabulary(ids=frozenset({"fixture_story_0001"}))
    assert not bare.available
    seen = []
    pf.set_eval_leakage_observer(lambda ok, err: seen.append((ok, err)))
    try:
        reason = eval_leakage_reason("anything", bare, harness=EMPTY)
    finally:
        pf.set_eval_leakage_observer(None)
    assert reason == "eval_leakage_vocabulary_unavailable:eval_content_index_missing"
    assert seen == [(False, "eval_content_index_missing")]


def test_content_check_crash_fails_closed(vocab, monkeypatch) -> None:
    def boom(*_a, **_kw):
        raise RuntimeError("kaput")

    monkeypatch.setattr(pf, "eval_content_leakage_reason", boom)
    reason = _reason("harmless text", vocab)
    assert reason is not None
    assert reason.startswith("eval_leakage_vocabulary_unavailable:content_check_failed")


def test_content_build_failure_fails_closed(tmp_path: Path, monkeypatch) -> None:
    pool = _write_jsonl(tmp_path / "question_pool.jsonl", ROWS)

    def broken(self):
        raise MemoryError("index too large")

    monkeypatch.setattr(pf._EvalContentIndexBuilder, "build", broken)
    vocab = load_eval_id_vocabulary(((pool, True),))
    assert not vocab.available
    assert vocab.error.startswith("eval_id_source_unreadable")
    reason = eval_leakage_reason("x", vocab, harness=EMPTY)
    assert reason.startswith("eval_leakage_vocabulary_unavailable")


def test_content_index_shares_the_vocabulary_cache(tmp_path: Path) -> None:
    pool = _write_jsonl(tmp_path / "question_pool.jsonl", ROWS)
    first = load_eval_id_vocabulary(((pool, True),))
    assert load_eval_id_vocabulary(((pool, True),)) is first
    assert first.content.labels[0] == "question_pool.jsonl:fixture_story_0001"
    new_answer = "Quillon Varnesbury"
    assert _reason(f"say {new_answer}", first) is None
    _write_jsonl(pool, ROWS + [{"id": "fixture_new_0001", "suite": "x", "expected": new_answer}])
    second = load_eval_id_vocabulary(((pool, True),))
    assert second is not first
    assert (_reason(f"say {new_answer}", second) or "").startswith("eval_expected_answer_leakage")


def test_harness_content_is_cached_by_file_identity(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("alpha beta gamma delta epsilon zeta eta theta iota\n")
    first = harness_content(tmp_path)
    assert harness_content(tmp_path) is first
    (tmp_path / "b.md").write_text("qzxvunmatchedlexeme appears nowhere else\n")
    second = harness_content(tmp_path)
    assert second is not first
    assert second.tokens.size > first.tokens.size


# ---------------------------------------------------------------------------
# Cost bounds
# ---------------------------------------------------------------------------


def test_index_memory_is_bounded_by_its_packing(vocab) -> None:
    content = vocab.content
    assert content.shingles.dtype == np.uint64 and content.answers.dtype == np.uint64
    assert all(
        t.dtype == np.uint16 and t.size == 1 << pf._CONTENT_SKETCH_BITS for t in content.sketch
    )
    assert content.row_bits == max(1, (len(ROWS) - 1).bit_length())
    stats = dict(content.stats)
    assert stats["shingles"] <= stats["row_shingles"]
    # Sketch dominates a tiny index: 2 x 4 MiB of uint16.
    assert content.nbytes < 20 * 1024 * 1024
    assert np.all(np.diff(content.shingles.astype(np.float64)) >= 0)


def test_per_call_cost_is_small(vocab) -> None:
    import time

    text = "Re-check units before answering. " * 200
    started = time.perf_counter()
    for _ in range(20):
        _reason(text, vocab, trace_context=TRACE_CONTEXT)
    assert (time.perf_counter() - started) / 20 < 0.25


_POOL = Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl")


@pytest.mark.skipif(not _POOL.exists(), reason="research question pool not on this host")
def test_real_pool_cost_coverage_and_no_false_positives_on_live_targets() -> None:
    """Measured bounds on the real pool (see meta-harness-operator-guide.md § 7)."""
    import time

    started = time.monotonic()
    vocab = load_eval_id_vocabulary()
    assert vocab.available, vocab.error
    stats = dict(vocab.content.stats)
    assert stats["rows"] > 50_000
    assert stats["shingles"] < 30_000_000
    assert vocab.content.nbytes < 300 * 1024 * 1024
    assert time.monotonic() - started < 120

    # False positives: a small benign edit to every live mutation target is clean.
    harness = harness_content()
    targets = sorted((ROOT / "orchestration" / "prompts").rglob("*.md"))
    targets += [ROOT / p for p in CODE_MUTATION_ALLOWLIST]
    flagged = {}
    for path in targets:
        original = path.read_text()
        mutated = original + "\n# Re-check the result before returning it.\n"
        reason = eval_leakage_reason(
            pf._added_text(original, mutated), vocab, original=original, harness=harness
        ) or suite_special_casing_reason(original, mutated, vocab, harness=harness)
        if reason:
            flagged[str(path)] = reason
    assert flagged == {}

    # Coverage: verbatim eval prompts are refused.
    rows = []
    with _POOL.open() as handle:
        next(handle)
        for index, line in enumerate(handle):
            if index % 400 == 0:
                row = json.loads(line)
                if len(row["prompt"]) < pf._CONTENT_LONG_ROW_BYTES:
                    rows.append(row)
    caught = sum(
        (eval_leakage_reason(r["prompt"], vocab, harness=harness) or "").startswith(
            "eval_content_ngram_overlap"
        )
        for r in rows
    )
    assert caught >= 0.97 * len(rows), (caught, len(rows))
