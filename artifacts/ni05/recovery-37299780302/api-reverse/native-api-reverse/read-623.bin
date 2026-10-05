"""RTG-55 MHS-3 / MHS-4 — PromptForge anti-leakage guard and ANTI-OVERRIDE risk prior.

MHS-3: a mutation that names a specific eval instance is rejected, the id
vocabulary is sourced from eval data, and the guard fails CLOSED.
MHS-4: every mutation carries a closed CONSTRAIN-vs-REPLACE risk weight that
ranks candidates and gates application.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(AUTOPILOT_DIR))

from species.prompt_forge import (  # noqa: E402
    CODE_MUTATION_ALLOWLIST,
    DEFAULT_MUTATION_RISK_GATE,
    EVAL_ID_VOCAB_SOURCES_ENV,
    MUTATION_EFFECT_RISK,
    MUTATION_RISK_GATE_ENV,
    CodeMutation,
    EvalIdVocabulary,
    MutationEffect,
    PromptForge,
    PromptMutation,
    classify_prompt_effect,
    eval_leakage_reason,
    load_eval_id_vocabulary,
    mutation_effect_risk,
    mutation_risk_gate,
    mutation_risk_gate_reason,
    rank_mutations_by_risk,
    stable_question_qid,
)

POOL_ROWS = [
    {"id": f"gsm8k_{i:05d}", "suite": "math", "prompt": f"What is {i} + {i}?"}
    for i in range(5)
] + [
    {"id": "bcb_BigCodeBench/0", "suite": "bigcodebench", "prompt": "Write f."},
    {"id": "humaneval_HumanEval_3", "suite": "coder", "prompt": "Write g."},
    {"id": "hotpot_bridge_5a8b57f25542995d1e6f1371", "suite": "hotpotqa", "prompt": "Who?"},
    {"id": "hotpot_bridge_5a8c7595554299585d9e36b6", "suite": "hotpotqa", "prompt": "What?"},
    {"id": "hotpot_bridge_5a85ea095542994775f606a8", "suite": "hotpotqa", "prompt": "When?"},
    {"id": "leetcode_two-sum", "suite": "livecodebench", "prompt": "Two sum."},
    # Nested metadata ids that are too generic to name one instance.
    {"id": "debugbench_flood-fill_cpp", "suite": "debugbench", "metadata": {"question_id": "3"}},
]


def _vocab(rows=POOL_ROWS) -> EvalIdVocabulary:
    return EvalIdVocabulary.from_rows(rows, sources=("fixture",))


def _write_jsonl(path: Path, rows) -> Path:
    lines = [json.dumps({"__pool_metadata__": True})] + [json.dumps(r) for r in rows]
    path.write_text("\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------------------
# MHS-3 — positives (must be flagged)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Use gsm8k_00003 as the worked example.",
        "Special-case GSM8K_00001 because it is tricky.",  # case-insensitive
        "if qid == 'gsm8k_77777':",  # family member absent from the pool
        "For BigCodeBench/42 return the sorted list.",  # native family, from bcb_BigCodeBench/0
        "hotpot_bridge_5a8b57f25542995d1e6f1371",
        "hotpot_bridge_deadbeefcafe",  # hex family member absent from the pool
        "see leetcode_two-sum",
        "The gsm8k question 12 needs units.",  # suite-anchored instance
        "Remember math problem #4.",
        "sample #12 is a trap",
        "question id: 42",
        "if task_id == 17:",
        "problem number 3 has a typo",
    ],
)
def test_leakage_positive(text: str) -> None:
    assert _vocab().find_leaks(text), text
    reason = eval_leakage_reason(text, _vocab())
    assert reason is not None and reason.startswith("eval_instance_leakage")


def test_prompt_hash_qid_is_in_vocabulary() -> None:
    qid = stable_question_qid("math", "What is 2 + 2?")
    assert _vocab().find_leaks(f"skip {qid} when scoring") == [qid]


def test_nested_core_selection_qid_is_in_vocabulary() -> None:
    vocab = _vocab([{"id": "agentic_ma_004", "core_selection": {"stable_qid": "fab289cf465d6b5a"}}])
    assert vocab.find_leaks("prefer FAB289CF465D6B5A") == ["fab289cf465d6b5a"]


def test_stable_qid_matches_eval_tower() -> None:
    from scripts.autopilot import eval_tower

    for suite, prompt in [("math", "What is 2 + 2?"), ("coder", "é\x00ü"), ("", "")]:
        assert stable_question_qid(suite, prompt) == eval_tower._stable_question_qid(suite, prompt)


# ---------------------------------------------------------------------------
# MHS-3 — negatives (must NOT be flagged)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Check step 3 before answering.",
        "Always show your arithmetic.",
        "index = 0",
        "for idx, item in enumerate(items):",
        "Cite answers in the MATH-500 style.",
        "AIME 2024 problems have integer answers.",
        "For gsm8k-style word problems, track units.",  # suite name, no instance
        "two-sum style problems use a hash map",
        "xgsm8k_00003y",  # id embedded inside a longer token
        "retry up to 3 times",
        "question 3",  # no qualifier
    ],
)
def test_leakage_negative(text: str) -> None:
    assert _vocab().find_leaks(text) == [], text
    assert eval_leakage_reason(text, _vocab()) is None


def test_generic_numeric_nested_ids_are_not_vocabulary() -> None:
    assert "3" not in _vocab().ids
    assert _vocab().find_leaks("return 3") == []


# ---------------------------------------------------------------------------
# MHS-3 — fail-closed vocabulary loading
# ---------------------------------------------------------------------------


def test_missing_required_source_fails_closed(tmp_path: Path) -> None:
    vocab = load_eval_id_vocabulary(((tmp_path / "absent.jsonl", True),))
    assert not vocab.available
    reason = eval_leakage_reason("perfectly clean text", vocab)
    assert reason is not None and reason.startswith("eval_leakage_vocabulary_unavailable")


def test_malformed_source_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "pool.jsonl"
    bad.write_text('{"id": "gsm8k_00001"}\n{not json\n')
    vocab = load_eval_id_vocabulary(((bad, True),))
    assert not vocab.available
    assert "eval_id_source_unreadable" in vocab.error


def test_empty_source_fails_closed(tmp_path: Path) -> None:
    empty = _write_jsonl(tmp_path / "pool.jsonl", [])
    vocab = load_eval_id_vocabulary(((empty, True),))
    assert not vocab.available
    assert eval_leakage_reason("clean", vocab) is not None


def test_no_sources_fails_closed() -> None:
    assert eval_leakage_reason("clean", load_eval_id_vocabulary(())) is not None


def test_optional_missing_source_is_skipped(tmp_path: Path) -> None:
    pool = _write_jsonl(tmp_path / "pool.jsonl", POOL_ROWS)
    vocab = load_eval_id_vocabulary(((pool, True), (tmp_path / "absent.yaml", False)))
    assert vocab.available
    assert vocab.sources == (str(pool),)


def test_yaml_sentinel_source_is_read(tmp_path: Path) -> None:
    pool = _write_jsonl(tmp_path / "pool.jsonl", POOL_ROWS)
    sentinels = tmp_path / "sentinels.yaml"
    sentinels.write_text("- id: sentinel_math_01\n  suite: math\n  prompt: hi\n")
    vocab = load_eval_id_vocabulary(((pool, True), (sentinels, False)))
    assert vocab.find_leaks("like sentinel_math_01") == ["sentinel_math_01"]


def test_env_override_sources_are_required(tmp_path: Path, monkeypatch) -> None:
    pool = _write_jsonl(tmp_path / "pool.jsonl", POOL_ROWS)
    monkeypatch.setenv(EVAL_ID_VOCAB_SOURCES_ENV, str(pool))
    assert load_eval_id_vocabulary().available
    monkeypatch.setenv(EVAL_ID_VOCAB_SOURCES_ENV, str(tmp_path / "gone.jsonl"))
    assert not load_eval_id_vocabulary().available


def test_vocabulary_cache_invalidates_on_source_change(tmp_path: Path) -> None:
    pool = _write_jsonl(tmp_path / "pool.jsonl", POOL_ROWS)
    first = load_eval_id_vocabulary(((pool, True),))
    assert load_eval_id_vocabulary(((pool, True),)) is first
    _write_jsonl(pool, POOL_ROWS + [{"id": "brand_new_item_0001", "suite": "x"}])
    second = load_eval_id_vocabulary(((pool, True),))
    assert second is not first
    assert "brand_new_item_0001" in second.ids


# ---------------------------------------------------------------------------
# MHS-3 — wired into PromptForge
# ---------------------------------------------------------------------------


def _prompt_forge(tmp_path: Path, vocab: EvalIdVocabulary, response: str, monkeypatch):
    (tmp_path / "worker_math.md").write_text("Base prompt\nBe careful.\n")
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=vocab)
    monkeypatch.setattr(forge, "_invoke_claude", lambda _prompt: response)
    return forge


def test_prompt_mutation_naming_an_eval_item_is_rejected(tmp_path: Path, monkeypatch) -> None:
    forge = _prompt_forge(
        tmp_path,
        _vocab(),
        "```markdown\nBase prompt\nBe careful.\nFor gsm8k_00002 answer 4.\n```",
        monkeypatch,
    )
    mutation = forge.propose_mutation("worker_math.md", description="fix math")
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_instance_leakage")
    assert mutation.mutated_content == mutation.original_content


def test_clean_prompt_mutation_is_accepted(tmp_path: Path, monkeypatch) -> None:
    forge = _prompt_forge(
        tmp_path,
        _vocab(),
        "```markdown\nBase prompt\nBe careful.\nRe-check units before answering.\n```",
        monkeypatch,
    )
    mutation = forge.propose_mutation("worker_math.md", description="fix math")
    assert mutation.safety_valid is True, mutation.safety_reason
    assert "Re-check units" in mutation.mutated_content


def test_preexisting_reference_is_not_blamed_on_the_mutation(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "worker_math.md").write_text("Base prompt\nLegacy note gsm8k_00001.\n")
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=_vocab())
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _p: "```markdown\nBase prompt\nLegacy note gsm8k_00001.\nShow work.\n```",
    )
    mutation = forge.propose_mutation("worker_math.md")
    assert mutation.safety_valid is True, mutation.safety_reason


def test_unavailable_vocabulary_rejects_every_prompt_mutation(tmp_path: Path, monkeypatch) -> None:
    forge = _prompt_forge(
        tmp_path,
        EvalIdVocabulary(error="missing_eval_id_source:/nowhere"),
        "```markdown\nBase prompt\nBe careful.\nShow work.\n```",
        monkeypatch,
    )
    mutation = forge.propose_mutation("worker_math.md")
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_leakage_vocabulary_unavailable")


def test_code_mutation_naming_an_eval_item_is_rejected(tmp_path: Path, monkeypatch) -> None:
    target = "src/tool_policy.py"
    original = (ROOT / target).read_text()
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=_vocab())
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _p: f'```python\n{original}\nHARD_CASE = "humaneval_HumanEval_3"\n```',
    )
    mutation = forge.propose_code_mutation(target_file=target)
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_instance_leakage")
    assert mutation.effect is MutationEffect.UNSAFE
    assert mutation.mutated_content == original


def test_gepa_mutation_naming_an_eval_item_is_rejected(tmp_path: Path, monkeypatch) -> None:
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
                    mutated_content="Base\nFor sample #7 answer 12.\n",
                )
            )

    for module in (gepa_optimizer, gepa_optimizer_alias):
        monkeypatch.setattr(module, "GEPAPromptOptimizer", _FakeOptimizer)
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=_vocab())
    mutation = forge.propose_mutation("worker_math.md", mutation_type="gepa", eval_tower=object())
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("eval_instance_leakage")
    assert mutation.mutated_content == "Base\n"


def test_proposer_prompt_carries_leakage_and_anti_override_rules(tmp_path: Path) -> None:
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=_vocab())
    block = forge._negative_transfer_safety_block()
    assert "MHS-3" in block and "MHS-4" in block
    assert "CONSTRAIN" in block and "REPLACE" in block


_POOL = Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl")


@pytest.mark.skipif(not _POOL.exists(), reason="research question pool not on this host")
def test_real_vocabulary_has_no_false_positives_on_live_mutation_targets() -> None:
    """Regression guard: the real vocabulary must not flag the current mutation targets."""
    vocab = load_eval_id_vocabulary()
    assert vocab.available, vocab.error
    assert len(vocab.ids) > 50_000
    targets = sorted((ROOT / "orchestration" / "prompts").rglob("*.md"))
    targets += [ROOT / p for p in CODE_MUTATION_ALLOWLIST]
    flagged = {str(p): vocab.find_leaks(p.read_text()) for p in targets}
    assert {k: v for k, v in flagged.items() if v} == {}


# ---------------------------------------------------------------------------
# MHS-4 — risk prior
# ---------------------------------------------------------------------------


def test_risk_table_is_total_and_ordered() -> None:
    assert set(MUTATION_EFFECT_RISK) == set(MutationEffect)
    order = [
        MutationEffect.INERT,
        MutationEffect.CONSTRAIN,
        MutationEffect.EXPAND,
        MutationEffect.REPLACE,
        MutationEffect.UNKNOWN,
        MutationEffect.UNSAFE,
    ]
    weights = [MUTATION_EFFECT_RISK[e] for e in order]
    assert weights == sorted(weights) and len(set(weights)) == len(weights)
    assert math.isinf(MUTATION_EFFECT_RISK[MutationEffect.UNSAFE])


@pytest.mark.parametrize("raw", [None, 3, "bogus", "override", "guard"])
def test_risk_of_raw_effects_is_normalized(raw) -> None:
    assert mutation_effect_risk(raw) == MUTATION_EFFECT_RISK[MutationEffect.normalize(raw)]


def test_rank_is_safest_first_and_stable() -> None:
    muts = [
        SimpleNamespace(name="r", effect=MutationEffect.REPLACE),
        SimpleNamespace(name="c1", effect=MutationEffect.CONSTRAIN),
        SimpleNamespace(name="u", effect=None),
        SimpleNamespace(name="c2", effect="constrain"),
        SimpleNamespace(name="i", effect=MutationEffect.INERT),
    ]
    assert [m.name for m in rank_mutations_by_risk(muts)] == ["i", "c1", "c2", "r", "u"]


def test_default_gate_refuses_only_unclassified(monkeypatch) -> None:
    monkeypatch.delenv(MUTATION_RISK_GATE_ENV, raising=False)
    assert mutation_risk_gate() == DEFAULT_MUTATION_RISK_GATE
    for effect in ("inert", "constrain", "expand", "replace"):
        assert mutation_risk_gate_reason(effect) is None
    assert mutation_risk_gate_reason(MutationEffect.UNKNOWN).startswith("effect_risk_gate:unknown")
    assert mutation_risk_gate_reason(MutationEffect.UNSAFE) is not None


def test_constrain_only_gate(monkeypatch) -> None:
    monkeypatch.setenv(MUTATION_RISK_GATE_ENV, "0.9")
    assert mutation_risk_gate() == 0.9
    assert mutation_risk_gate_reason("replace").startswith("effect_risk_gate:replace")
    assert mutation_risk_gate_reason("expand") is None


@pytest.mark.parametrize("raw", ["nope", "1.5", "0", "-1", "nan", "inf"])
def test_malformed_gate_falls_back_and_never_loosens(monkeypatch, raw: str) -> None:
    monkeypatch.setenv(MUTATION_RISK_GATE_ENV, raw)
    assert mutation_risk_gate() == DEFAULT_MUTATION_RISK_GATE


@pytest.mark.parametrize(
    ("original", "mutated", "expected"),
    [
        ("A\nB\n", "A\nB\n", MutationEffect.INERT),
        ("A\nB\n", "A\nguard\nB\n", MutationEffect.CONSTRAIN),
        ("A\nB\n", "A\n\nB\n", MutationEffect.CONSTRAIN),
        ("A\nB\n", "A\nC\n", MutationEffect.REPLACE),
        ("A\nB\n", "A\n", MutationEffect.REPLACE),
        ("", "new\n", MutationEffect.CONSTRAIN),
    ],
)
def test_classify_prompt_effect(original: str, mutated: str, expected: MutationEffect) -> None:
    assert classify_prompt_effect(original, mutated) is expected


def test_prompt_mutation_carries_effect_and_risk(tmp_path: Path, monkeypatch) -> None:
    forge = _prompt_forge(
        tmp_path, _vocab(), "```markdown\nBase prompt\nBe careful.\nShow work.\n```", monkeypatch
    )
    mutation = forge.propose_mutation("worker_math.md")
    assert mutation.effect is MutationEffect.CONSTRAIN
    assert mutation.effect_risk == MUTATION_EFFECT_RISK[MutationEffect.CONSTRAIN]


def test_constrain_only_gate_rejects_prompt_rewrite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(MUTATION_RISK_GATE_ENV, "0.9")
    forge = _prompt_forge(tmp_path, _vocab(), "```markdown\nRewritten prompt\n```", monkeypatch)
    mutation = forge.propose_mutation("worker_math.md")
    assert mutation.effect is MutationEffect.REPLACE
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("effect_risk_gate:replace")
    assert mutation.mutated_content == mutation.original_content


def _code_forge(tmp_path: Path, response: str, monkeypatch) -> PromptForge:
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=_vocab())
    monkeypatch.setattr(forge, "_invoke_claude", lambda _p: response)
    return forge


def test_code_mutation_carries_risk_and_default_gate_admits_replace(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv(MUTATION_RISK_GATE_ENV, raising=False)
    target = "src/tool_policy.py"
    original = (ROOT / target).read_text()
    first = next(line for line in original.splitlines() if line.strip().startswith("import "))
    replaced = original.replace(first, first + "  # rewritten", 1)
    forge = _code_forge(tmp_path, f"```python\n{replaced}\n```", monkeypatch)
    mutation = forge.propose_code_mutation(target_file=target)
    assert mutation.effect is MutationEffect.REPLACE
    assert mutation.effect_risk == MUTATION_EFFECT_RISK[MutationEffect.REPLACE]
    assert mutation.safety_valid is True, mutation.safety_reason


def test_constrain_only_gate_rejects_code_replace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(MUTATION_RISK_GATE_ENV, "0.9")
    target = "src/tool_policy.py"
    original = (ROOT / target).read_text()
    first = next(line for line in original.splitlines() if line.strip().startswith("import "))
    replaced = original.replace(first, first + "  # rewritten", 1)
    forge = _code_forge(tmp_path, f"```python\n{replaced}\n```", monkeypatch)
    mutation = forge.propose_code_mutation(target_file=target)
    assert mutation.syntax_valid is True
    assert mutation.safety_valid is False
    assert mutation.safety_reason.startswith("effect_risk_gate:replace")
    assert mutation.mutated_content == original


def test_code_constrain_passes_constrain_only_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(MUTATION_RISK_GATE_ENV, "0.9")
    target = "src/tool_policy.py"
    original = (ROOT / target).read_text()
    forge = _code_forge(tmp_path, f"```python\n{original}\nEXTRA_LIMIT = 3\n```", monkeypatch)
    mutation = forge.propose_code_mutation(target_file=target)
    assert mutation.effect is MutationEffect.CONSTRAIN
    assert mutation.safety_valid is True, mutation.safety_reason


def test_apply_refuses_unknown_effect(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(MUTATION_RISK_GATE_ENV, raising=False)
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=_vocab())
    mutation = CodeMutation(
        file="src/tool_policy.py",
        mutation_type="targeted_fix",
        description="d",
        mutated_content="def f():\n    return 1\n",
    )
    mutation.syntax_valid = True  # effect left at the UNKNOWN default
    target = ROOT / "src/tool_policy.py"
    before = target.read_bytes()
    result = forge.apply_code_mutation(mutation)
    assert result["status"] == "rejected"
    assert result["reason"].startswith("effect_risk_gate:unknown")
    assert target.read_bytes() == before

    class _Ctx:
        worktree_path = tmp_path

        def apply_file(self, path: str, content: str) -> None:  # pragma: no cover
            raise AssertionError("must not apply an unclassified mutation")

    assert forge.apply_code_mutation_in_context(_Ctx(), mutation)["status"] == "rejected"


def test_apply_in_context_reports_risk(tmp_path: Path) -> None:
    class _Ctx:
        worktree_path = tmp_path

        def apply_file(self, path: str, content: str) -> None:
            pass

    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False, eval_id_vocabulary=_vocab())
    mutation = CodeMutation(
        file="src/tool_policy.py", mutation_type="targeted_fix", description="d"
    )
    mutation.syntax_valid = True
    mutation.effect = MutationEffect.EXPAND
    result = forge.apply_code_mutation_in_context(_Ctx(), mutation)
    assert result["effect_risk"] == MUTATION_EFFECT_RISK[MutationEffect.EXPAND]

