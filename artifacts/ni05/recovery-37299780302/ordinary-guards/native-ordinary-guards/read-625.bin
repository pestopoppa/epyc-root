"""AP-33 negative-transfer safety checks for PromptForge."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(AUTOPILOT_DIR))

import species.prompt_forge as prompt_forge_mod  # noqa: E402
from species.prompt_forge import PromptForge  # noqa: E402


@pytest.fixture(autouse=True)
def _hermetic_eval_id_vocabulary(tmp_path_factory, monkeypatch):
    """RTG-55 MHS-3 fails closed without eval data; pin a tiny fixture pool."""
    pool = tmp_path_factory.mktemp("eval_ids") / "question_pool.jsonl"
    pool.write_text('{"id": "fixture_suite_000001", "suite": "fixture", "prompt": "p"}\n')
    monkeypatch.setenv(prompt_forge_mod.EVAL_ID_VOCAB_SOURCES_ENV, str(pool))


def _forge_with_prompt(
    tmp_path: Path,
    content: str = "Base prompt\n",
    filename: str = "frontdoor.md",
) -> PromptForge:
    (tmp_path / filename).write_text(content)
    return PromptForge(prompts_dir=tmp_path, auto_commit=False)


def test_resolve_prompt_exact_flat_file_wins_over_roles_copy(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (tmp_path / "frontdoor.md").write_text("flat\n")
    (roles_dir / "frontdoor.md").write_text("roles\n")
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)

    assert forge.read_prompt("frontdoor.md") == "flat\n"
    forge.write_prompt("frontdoor.md", "updated\n")
    assert (tmp_path / "frontdoor.md").read_text() == "updated\n"
    assert (roles_dir / "frontdoor.md").read_text() == "roles\n"


def test_resolve_prompt_bare_filename_falls_back_to_roles_dir(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "worker_general.md").write_text("worker\n")
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)

    assert forge.read_prompt("worker_general.md") == "worker\n"
    forge.write_prompt("worker_general.md", "updated worker\n")
    assert (roles_dir / "worker_general.md").read_text() == "updated worker\n"


def test_resolve_prompt_exact_roles_path_stays_in_roles_dir(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (tmp_path / "frontdoor.md").write_text("flat\n")
    (roles_dir / "frontdoor.md").write_text("roles\n")
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)

    assert forge.read_prompt("roles/frontdoor.md") == "roles\n"
    forge.write_prompt("roles/frontdoor.md", "updated roles\n")
    assert (roles_dir / "frontdoor.md").read_text() == "updated roles\n"
    assert (tmp_path / "frontdoor.md").read_text() == "flat\n"


def test_resolve_prompt_path_component_strips_to_flat_basename(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (tmp_path / "frontdoor.md").write_text("flat\n")
    (roles_dir / "frontdoor.md").write_text("roles\n")
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)

    assert forge.read_prompt("missing/frontdoor.md") == "flat\n"


def test_resolve_prompt_path_component_strips_to_roles_basename(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "frontdoor.md").write_text("roles\n")
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)

    assert forge.read_prompt("missing/frontdoor.md") == "roles\n"


def test_resolve_prompt_returns_canonical_in_tree_symlink_target(tmp_path: Path) -> None:
    target = tmp_path / "frontdoor.md"
    target.write_text("flat\n")
    (tmp_path / "alias.md").symlink_to(target)
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)

    assert forge._resolve_prompt_path("alias.md") == target.resolve()
    forge.write_prompt("alias.md", "updated\n")
    assert target.read_text() == "updated\n"


def test_resolve_prompt_basename_fallback_returns_canonical_target(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    target = roles_dir / "frontdoor.md"
    target.write_text("roles\n")
    (tmp_path / "frontdoor.md").symlink_to(target)
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)

    assert forge._resolve_prompt_path("missing/frontdoor.md") == target.resolve()


def test_resolve_prompt_missing_file_reports_original_joined_path(tmp_path: Path) -> None:
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)

    try:
        forge.read_prompt("missing/frontdoor.md")
    except FileNotFoundError as exc:
        assert str(tmp_path / "missing/frontdoor.md") in str(exc)
    else:
        raise AssertionError("expected missing prompt to raise FileNotFoundError")


def test_resolve_prompt_rejects_parent_directory_escape(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "outside.md").write_text("inside same basename\n")
    (tmp_path / "outside.md").write_text("outside\n")
    forge = PromptForge(prompts_dir=prompts_dir, auto_commit=False)

    try:
        forge.read_prompt("../outside.md")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected parent traversal to be rejected")


def test_resolve_prompt_rejects_absolute_path_escape(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n")
    forge = PromptForge(prompts_dir=prompts_dir, auto_commit=False)

    try:
        forge.read_prompt(str(outside))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected absolute path to be rejected")


def test_new_file_code_mutation_accepts_sanctioned_empty_path(tmp_path: Path, monkeypatch) -> None:
    src_dir = tmp_path / "src"
    generated_dir = src_dir / "generated"
    generated_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("")
    (generated_dir / "__init__.py").write_text("")
    monkeypatch.setattr(prompt_forge_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prompt_forge_mod, "NEW_FILE_MUTATION_ROOT", src_dir)
    monkeypatch.syspath_prepend(str(tmp_path))
    for module_name in [
        name for name in list(sys.modules) if name == "src" or name.startswith("src.")
    ]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    forge = PromptForge(prompts_dir=tmp_path / "prompts", auto_commit=False)
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _prompt: "```python\nVALUE = 1\n```",
    )

    mutation = forge.propose_code_mutation(
        target_file="src/generated/new_module.py",
        mutation_type="new_file",
    )

    assert mutation.syntax_valid is True
    assert mutation.original_content == ""
    assert mutation.mutated_content == "VALUE = 1"
    assert mutation.safety_valid is True


def test_new_file_code_mutation_apply_and_revert(tmp_path: Path, monkeypatch) -> None:
    src_dir = tmp_path / "src"
    generated_dir = src_dir / "generated"
    generated_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("")
    (generated_dir / "__init__.py").write_text("")
    monkeypatch.setattr(prompt_forge_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prompt_forge_mod, "NEW_FILE_MUTATION_ROOT", src_dir)
    monkeypatch.syspath_prepend(str(tmp_path))
    for module_name in [
        name for name in list(sys.modules) if name == "src" or name.startswith("src.")
    ]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    forge = PromptForge(prompts_dir=tmp_path / "prompts", auto_commit=False)
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _prompt: "```python\nVALUE = 1\n```",
    )
    target = generated_dir / "new_module.py"

    mutation = forge.propose_code_mutation(
        target_file="src/generated/new_module.py",
        mutation_type="new_file",
    )
    result = forge.apply_code_mutation(mutation)

    assert result["status"] == "applied"
    assert target.read_text() == "VALUE = 1"
    assert "--- /dev/null" in mutation.git_diff
    assert "+++ " in mutation.git_diff

    forge.revert_code_mutation(mutation)

    assert not target.exists()
    assert mutation.accepted is False


def test_new_file_code_mutation_rejects_traversal_and_absolute_paths(
    tmp_path: Path, monkeypatch
) -> None:
    src_dir = tmp_path / "src"
    (src_dir / "generated").mkdir(parents=True)
    (src_dir / "__init__.py").write_text("")
    (src_dir / "generated" / "__init__.py").write_text("")
    monkeypatch.setattr(prompt_forge_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prompt_forge_mod, "NEW_FILE_MUTATION_ROOT", src_dir)

    forge = PromptForge(prompts_dir=tmp_path / "prompts", auto_commit=False)

    with pytest.raises(FileNotFoundError):
        forge.propose_code_mutation(
            target_file="../escape.py",
            mutation_type="new_file",
        )

    with pytest.raises(FileNotFoundError):
        forge.propose_code_mutation(
            target_file=str(tmp_path / "escape.py"),
            mutation_type="new_file",
        )


def test_new_file_code_mutation_rejects_collision(tmp_path: Path, monkeypatch) -> None:
    src_dir = tmp_path / "src"
    generated_dir = src_dir / "generated"
    generated_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("")
    (generated_dir / "__init__.py").write_text("")
    target = generated_dir / "new_module.py"
    target.write_text("VALUE = 0\n")
    monkeypatch.setattr(prompt_forge_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prompt_forge_mod, "NEW_FILE_MUTATION_ROOT", src_dir)

    forge = PromptForge(prompts_dir=tmp_path / "prompts", auto_commit=False)

    with pytest.raises(FileExistsError):
        forge.propose_code_mutation(
            target_file="src/generated/new_module.py",
            mutation_type="new_file",
        )


def test_new_file_code_mutation_accepts_memory_schema_evolution_path(
    tmp_path: Path, monkeypatch
) -> None:
    schema_dir = tmp_path / "orchestration" / "repl_memory" / "schema_evolution"
    schema_dir.mkdir(parents=True)
    for init_dir in [
        tmp_path / "orchestration",
        tmp_path / "orchestration" / "repl_memory",
        schema_dir,
    ]:
        (init_dir / "__init__.py").write_text("")
    monkeypatch.setattr(prompt_forge_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prompt_forge_mod, "NEW_FILE_MUTATION_ROOT", tmp_path / "src")
    monkeypatch.setattr(prompt_forge_mod, "MEMORY_SCHEMA_MUTATION_ROOT", schema_dir)
    monkeypatch.syspath_prepend(str(tmp_path))
    for module_name in [
        name
        for name in list(sys.modules)
        if name == "orchestration" or name.startswith("orchestration.")
    ]:
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    forge = PromptForge(prompts_dir=tmp_path / "prompts", auto_commit=False)
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _prompt: "```python\nSCHEMA_VERSION = 1\nCHANNELS = ('plan',)\n```",
    )

    mutation = forge.propose_code_mutation(
        target_file="orchestration/repl_memory/schema_evolution/plan_schema.py",
        mutation_type="new_file",
        description="Add a default-inert memory schema helper",
    )

    assert mutation.syntax_valid is True
    assert mutation.original_content == ""
    assert "SCHEMA_VERSION = 1" in mutation.mutated_content
    assert mutation.safety_valid is True


def test_new_file_memory_schema_prompt_includes_automem_contract(
    tmp_path: Path, monkeypatch
) -> None:
    schema_dir = tmp_path / "orchestration" / "repl_memory" / "schema_evolution"
    schema_dir.mkdir(parents=True)
    monkeypatch.setattr(prompt_forge_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prompt_forge_mod, "NEW_FILE_MUTATION_ROOT", tmp_path / "src")
    monkeypatch.setattr(prompt_forge_mod, "MEMORY_SCHEMA_MUTATION_ROOT", schema_dir)
    forge = PromptForge(prompts_dir=tmp_path / "prompts", auto_commit=False)

    prompt = forge._build_code_mutation_prompt(
        target_file="orchestration/repl_memory/schema_evolution/plan_schema.py",
        mutation_type="new_file",
        original_content="",
        failure_context="Trial #1317 needs memory plan schema evolution.",
        per_suite_quality=None,
        description="Add memory schema scaffold",
    )

    assert "AutoMem memory schema-evolution contract (MH-9/P2)" in prompt
    assert "default-inert schema/scaffold module" in prompt
    assert "APPEND/CREATE/UPSERT" in prompt
    assert "status/inventory/strategy/plan/log" in prompt
    assert "Do not change SafetyGate, Pareto admission, eval scoring" in prompt
    assert "planner spend-breaker flags" in prompt


def test_resolve_prompt_rejects_symlink_escape(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n")
    (prompts_dir / "linked.md").symlink_to(outside)
    forge = PromptForge(prompts_dir=prompts_dir, auto_commit=False)

    try:
        forge.read_prompt("linked.md")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected symlink escape to be rejected")


def test_frontdoor_prompt_integrity_rejects_agent_commentary(tmp_path: Path, monkeypatch) -> None:
    forge = _forge_with_prompt(
        tmp_path,
        "# Front Door Orchestrator\nTaskIR mode\nDirect-answer mode\nAnswer tags (scoped)\n",
    )
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _prompt: (
            "```markdown\n"
            "fenced block from my response and writes it to the target file itself\n"
            "One note worth flagging: this is agent commentary.\n"
            "```"
        ),
    )

    mutation = forge.propose_mutation(target_file="frontdoor.md")

    assert mutation.safety_valid is False
    assert "prompt_integrity:frontdoor_corruption_marker" in mutation.safety_reason
    assert mutation.mutated_content == mutation.original_content


def test_frontdoor_prompt_integrity_rejects_missing_router_markers(
    tmp_path: Path, monkeypatch
) -> None:
    forge = _forge_with_prompt(
        tmp_path,
        "# Front Door Orchestrator\nTaskIR mode\nDirect-answer mode\nAnswer tags (scoped)\n",
    )
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _prompt: "```markdown\n# Front Door Orchestrator\nTaskIR mode\n```",
    )

    mutation = forge.propose_mutation(target_file="frontdoor.md")

    assert mutation.safety_valid is False
    assert "frontdoor_missing_required_markers" in mutation.safety_reason
    assert mutation.mutated_content == mutation.original_content


def test_frontdoor_prompt_integrity_rejects_bad_apply_and_revert(tmp_path: Path) -> None:
    forge = _forge_with_prompt(
        tmp_path,
        "# Front Door Orchestrator\nTaskIR mode\nDirect-answer mode\nAnswer tags (scoped)\n",
    )
    mutation = forge.propose_mutation(target_file="frontdoor.md")

    mutation.mutated_content = "fenced block from my response\n"
    try:
        forge.apply_mutation(mutation)
    except ValueError as exc:
        assert "prompt integrity rejected mutation" in str(exc)
    else:
        raise AssertionError("expected corrupted frontdoor apply to be rejected")

    mutation.mutated_content = mutation.original_content
    mutation.original_content = "one note worth flagging\n"
    try:
        forge.revert_mutation(mutation)
    except ValueError as exc:
        assert "prompt integrity rejected revert" in str(exc)
    else:
        raise AssertionError("expected corrupted frontdoor revert to be rejected")


def test_mutation_prompt_includes_negative_transfer_safety_block(tmp_path: Path) -> None:
    forge = _forge_with_prompt(tmp_path)

    prompt = forge._build_mutation_prompt(
        target_file="frontdoor.md",
        mutation_type="targeted_fix",
        original_content="Base prompt",
        failure_context="Trial #1 failed on coder.",
        per_suite_quality={"coder": 1.0},
        description="Improve coder reliability",
    )

    assert "Negative-transfer safety (AP-33)" in prompt
    assert "fewer than 5 trial IDs" in prompt
    assert "suite-specific fixes" in prompt


def test_diversity_coverage_penalty_uses_strategy_density() -> None:
    class FakeStore:
        def __init__(self):
            self.calls = []

        def retrieve(self, query_text, *, k, species):
            self.calls.append((query_text, k, species))
            return [
                SimpleNamespace(
                    id="strategy-1",
                    source_trial_id=11,
                    species="prompt_forge",
                    description="frontdoor targeted fix",
                    generalized_content="prefer narrow edits",
                    similarity_score=0.25,
                ),
                SimpleNamespace(
                    id="strategy-2",
                    source_trial_id=12,
                    species="prompt_forge",
                    description="frontdoor retry fix",
                    insight="avoid broad retries",
                    similarity_score=0.75,
                ),
            ]

    store = FakeStore()
    result = prompt_forge_mod.diversity_coverage_penalty(
        "frontdoor targeted_fix retry loop",
        store,
        k=2,
        species="prompt_forge",
    )

    assert store.calls == [("frontdoor targeted_fix retry loop", 2, "prompt_forge")]
    assert result["status"] == "ok"
    assert result["density"] == pytest.approx(0.5)
    assert result["negative_log_density"] == pytest.approx(-math.log(0.5))
    assert result["penalty"] == result["negative_log_density"]
    assert result["top_matches"][0]["source_trial_id"] == 11


def test_code_mutation_prompt_includes_mh6_proposer_prior_contract(
    tmp_path: Path,
) -> None:
    forge = _forge_with_prompt(tmp_path)

    prompt = forge._build_code_mutation_prompt(
        target_file="src/escalation.py",
        mutation_type="targeted_fix",
        original_content="def route():\n    return 'frontdoor'\n",
        failure_context="Trial #1 failed after an escalation loop.",
        per_suite_quality={"agentic": 1.0},
        description="Reduce escalation loops",
    )

    assert "Proposer-prior contract (MH-6)" in prompt
    assert "Read inputs in this order" in prompt
    assert "Failed traces and recent regressions" in prompt
    assert "Current frontier or accepted behavior" in prompt
    assert "Strategy-store or prior-mutation notes" in prompt
    assert "operator request / mutation goal" in prompt
    assert "expected_quality_delta" in prompt
    assert "expected_cost_delta" in prompt
    assert "no-task-specific-hints" in prompt
    assert "no_task_specific_hints" in prompt


def test_rejects_mismatched_suite_anchor_introduced_by_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    forge = _forge_with_prompt(tmp_path, filename="worker_general.md")
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _prompt: (
            "```markdown\nBase prompt\nAdd a USACO contest tactic for these coder failures.\n```"
        ),
    )

    mutation = forge.propose_mutation(
        target_file="worker_general.md",
        mutation_type="targeted_fix",
        failure_context="Trial #1: coder failure.",
        per_suite_quality={"coder": 1.0},
    )

    assert mutation.safety_valid is False
    assert mutation.mutated_content == "Base prompt\n"
    assert "domain_mismatched_anchoring" in mutation.safety_reason
    assert "low_evidence_trial_count:1" in mutation.safety_warnings


def test_warns_on_low_evidence_without_rejecting_generic_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    forge = _forge_with_prompt(tmp_path, filename="worker_general.md")
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _prompt: "```markdown\nBase prompt\nAsk for one concise verification step.\n```",
    )

    mutation = forge.propose_mutation(
        target_file="worker_general.md",
        mutation_type="targeted_fix",
        failure_context="Trial #7: answer drifted.",
        per_suite_quality={"coder": 1.0},
    )

    assert mutation.safety_valid is True
    assert mutation.safety_reason == "ok"
    assert mutation.safety_warnings == ["low_evidence_trial_count:1"]


def test_rejects_universal_suite_best_practice_without_source_context(
    tmp_path: Path, monkeypatch
) -> None:
    forge = _forge_with_prompt(tmp_path, filename="worker_general.md")
    monkeypatch.setattr(
        forge,
        "_invoke_claude",
        lambda _prompt: (
            "```markdown\n"
            "Base prompt\n"
            "Always use GPQA decomposition as a global default for all tasks.\n"
            "```"
        ),
    )

    mutation = forge.propose_mutation(
        target_file="worker_general.md",
        mutation_type="targeted_fix",
    )

    assert mutation.safety_valid is False
    assert "misapplied_best_practice" in mutation.safety_reason


def test_code_mutation_records_transfer_safety_rejection(tmp_path: Path) -> None:
    original = "def route():\n    return 'ok'\n"
    mutated = "def route():\n    return 'ok'  # Always apply GPQA to all tasks\n"
    forge = _forge_with_prompt(tmp_path)

    verdict = forge._transfer_safety_verdict(
        original_content=original,
        mutated_content=mutated,
        failure_context="",
        per_suite_quality=None,
        description="",
    )

    assert verdict.valid is False
    assert "misapplied_best_practice" in verdict.reason
