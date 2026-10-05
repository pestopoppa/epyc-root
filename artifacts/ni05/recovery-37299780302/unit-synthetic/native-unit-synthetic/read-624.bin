"""RTG-55 MHS-1/MHS-2 — PromptForge mutation safety contract.

Covers:
* the static AST safety screen (denylist positives + negatives),
* the guarantee that validation writes nothing into the repo and imports nothing,
* the typed return-effect enum (``MutationEffect``) and its classification.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(AUTOPILOT_DIR))

import species.prompt_forge as prompt_forge_mod  # noqa: E402
from species.prompt_forge import (  # noqa: E402
    CODE_MUTATION_ALLOWLIST,
    MEMORY_SCHEMA_SHAPE_EXAMPLE,
    SAFETY_BANNED_CALLS,
    SAFETY_BANNED_MODULES,
    SAFETY_IMPORT_ALLOWLIST,
    SAFETY_RESTRICTED_CALLS,
    SAFETY_STRICT_NODE_DENYLIST,
    CodeMutation,
    MutationEffect,
    PromptForge,
    classify_mutation_effect,
    screen_static_safety,
)

BENIGN = '''"""Docstring."""

import json
import logging

LIMIT = 5
log = logging.getLogger("x")


def helper(value):
    if value > LIMIT:
        return json.dumps({"value": value})
    return None


class Holder:
    def get(self):
        return LIMIT
'''


# ---------------------------------------------------------------------------
# Denylist — negatives (must PASS the screen)
# ---------------------------------------------------------------------------


def test_benign_def_only_module_passes() -> None:
    report = screen_static_safety(BENIGN)
    assert report.safe is True
    assert report.violations == ()
    assert report.reason == "ok"


def test_first_party_import_is_allowed() -> None:
    report = screen_static_safety("from src.tool_policy import x\n\n\ndef f():\n    return x\n")
    assert report.safe is True


def test_typing_guard_and_toplevel_if_are_allowed() -> None:
    code = (
        "from typing import TYPE_CHECKING\n\n"
        "if TYPE_CHECKING:\n    from src.escalation import Policy\n\n\n"
        "def f():\n    return 1\n"
    )
    assert screen_static_safety(code).safe is True


def test_original_capabilities_are_grandfathered() -> None:
    original = "import subprocess\n\n\ndef run():\n    return subprocess.run(['ls'])\n"
    mutated = original.replace("def run():", "def run():\n    pass\n\n\ndef run_two():")
    # A file that already shelled out is judged on what the mutation ADDS.
    assert screen_static_safety(mutated, original=original).safe is True
    # The same body proposed for a file that never shelled out is rejected.
    assert screen_static_safety(mutated, original="def run():\n    return 1\n").safe is False


@pytest.mark.parametrize("target", CODE_MUTATION_ALLOWLIST)
def test_noop_mutation_of_every_allowlisted_file_passes(target: str) -> None:
    """Regression guard: the screen must not reject the live allowlisted files."""
    source = (ROOT / target).read_text()
    report = screen_static_safety(source, original=source)
    assert report.safe is True, report.violations


# ---------------------------------------------------------------------------
# Denylist — positives (must FAIL the screen)
# ---------------------------------------------------------------------------


def test_toplevel_side_effect_is_rejected() -> None:
    code = "def f():\n    return 1\n\n\nf()\n"
    report = screen_static_safety(code)
    assert report.safe is False
    assert report.effect is MutationEffect.UNSAFE
    assert any("top-level side effect" in v for v in report.violations)


def test_toplevel_loop_is_rejected() -> None:
    code = "TOTAL = 0\nfor i in range(3):\n    TOTAL += i\n"
    report = screen_static_safety(code)
    assert report.safe is False
    assert any("top-level For" in v for v in report.violations)


def test_os_system_is_rejected() -> None:
    code = "import os\n\n\ndef f():\n    os.system('rm -rf /')\n"
    report = screen_static_safety(code)
    assert report.safe is False
    assert any("banned import: os" in v for v in report.violations)
    assert any("os.system()" in v for v in report.violations)


@pytest.mark.parametrize("name", sorted(SAFETY_BANNED_CALLS))
def test_every_banned_call_is_rejected(name: str) -> None:
    code = f"def f():\n    return {name}('x')\n"
    report = screen_static_safety(code)
    assert report.safe is False
    assert any(name in v for v in report.violations)


@pytest.mark.parametrize("name", sorted(SAFETY_RESTRICTED_CALLS))
def test_every_restricted_call_is_rejected_when_not_grandfathered(name: str) -> None:
    code = f"def f():\n    return {name}('x')\n"
    assert screen_static_safety(code, original="def f():\n    return 1\n").safe is False


@pytest.mark.parametrize("module", sorted(SAFETY_BANNED_MODULES))
def test_every_banned_module_import_is_rejected(module: str) -> None:
    report = screen_static_safety(f"import {module}\n\n\ndef f():\n    return 1\n")
    assert report.safe is False
    assert any(f"banned import: {module}" in v for v in report.violations)


def test_import_outside_allowlist_is_rejected() -> None:
    report = screen_static_safety("import numpy\n\n\ndef f():\n    return 1\n")
    assert report.safe is False
    assert any("import outside allowlist: numpy" in v for v in report.violations)


def test_subprocess_from_import_is_rejected() -> None:
    report = screen_static_safety("from subprocess import run\n\n\ndef f():\n    return run\n")
    assert report.safe is False


def test_dunder_attribute_access_is_rejected() -> None:
    code = "def f(obj):\n    return obj.__class__.__subclasses__()\n"
    report = screen_static_safety(code)
    assert report.safe is False
    assert any("dunder attribute access" in v for v in report.violations)


def test_allowed_dunder_attributes_do_not_trip_the_screen() -> None:
    code = "def f(obj):\n    return obj.__name__\n"
    assert screen_static_safety(code).safe is True


def test_syntax_error_is_unsafe_not_an_exception() -> None:
    report = screen_static_safety("def f(:\n")
    assert report.safe is False
    assert report.effect is MutationEffect.UNSAFE
    assert "syntax error" in report.reason


def test_violation_list_is_capped_and_reason_truncated() -> None:
    code = "\n".join(f"import mod{i}" for i in range(40)) + "\n\n\ndef f():\n    return 1\n"
    report = screen_static_safety(code)
    assert report.safe is False
    assert len(report.violations) <= 10
    assert len(report.reason) <= 240


# ---------------------------------------------------------------------------
# Strict (new_file) inertness profile — MHS-2
# ---------------------------------------------------------------------------


def test_strict_profile_accepts_inert_def_only_module() -> None:
    code = '"""Inert scaffold."""\n\nLIMIT = 3\n\n\ndef validate(action):\n    return action\n'
    report = screen_static_safety(code, strict=True)
    assert report.safe is True
    assert report.effect is MutationEffect.INERT


@pytest.mark.parametrize(
    "code",
    [
        "import json\n\n\ndef f():\n    return json\n",  # Import
        "from json import loads\n\n\ndef f():\n    return loads\n",  # ImportFrom
        "class Thing:\n    pass\n",  # ClassDef
        "def f():\n    while True:\n        break\n",  # While
        "def f(items):\n    with items:\n        return 1\n",  # With
        "F = lambda x: x\n",  # Lambda
        "def f():\n    raise ValueError('x')\n",  # Raise
        "def f():\n    global X\n",  # Global
        "def f(d):\n    del d['a']\n",  # Delete
        "def f():\n    yield 1\n",  # Yield
        "async def f(x):\n    return await x\n",  # Await
    ],
)
def test_strict_profile_rejects_denylisted_nodes(code: str) -> None:
    assert screen_static_safety(code, strict=True).safe is False


# ---------------------------------------------------------------------------
# MH-9 schema-evolution lane: the prompt's shape must match the denylist
# ---------------------------------------------------------------------------

# Exactly what the OLD (pre-RTG-55) prompt invited: a class-based contract with
# imports and a raise. Kept as a fixture so prompt/denylist drift cannot recur.
_OLD_SHAPE_CLASS_PROPOSAL = '''"""Proposed memory schema."""

from dataclasses import dataclass


@dataclass
class MemoryActionSchema:
    channel: str
    content: str

    def validate(self):
        if not self.channel:
            raise ValueError("channel required")
        return True
'''


def test_prompt_shape_example_passes_the_strict_screen() -> None:
    """The shape the MH-9 prompt ships must survive its own validator."""
    report = screen_static_safety(MEMORY_SCHEMA_SHAPE_EXAMPLE, strict=True)
    assert report.safe is True, report.violations
    assert report.effect is MutationEffect.INERT


def test_old_class_shaped_proposal_is_rejected_by_the_strict_screen() -> None:
    report = screen_static_safety(_OLD_SHAPE_CLASS_PROPOSAL, strict=True)
    assert report.safe is False
    assert report.effect is MutationEffect.UNSAFE
    assert any("ClassDef" in v for v in report.violations)
    assert any("ImportFrom" in v for v in report.violations)
    assert any("Raise" in v for v in report.violations)


def test_memory_schema_prompt_states_the_denylisted_shape(tmp_path: Path) -> None:
    schema_dir = tmp_path / "orchestration" / "repl_memory" / "schema_evolution"
    schema_dir.mkdir(parents=True)
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(prompt_forge_mod, "PROJECT_ROOT", tmp_path)
        monkey.setattr(prompt_forge_mod, "NEW_FILE_MUTATION_ROOT", tmp_path / "src")
        monkey.setattr(prompt_forge_mod, "MEMORY_SCHEMA_MUTATION_ROOT", schema_dir)
        forge = PromptForge(prompts_dir=tmp_path / "prompts", auto_commit=False)
        prompt = forge._build_code_mutation_prompt(
            target_file="orchestration/repl_memory/schema_evolution/plan_schema.py",
            mutation_type="new_file",
            original_content="",
            failure_context="",
            per_suite_quality=None,
            description="Add memory schema scaffold",
        )
    finally:
        monkey.undo()

    # The MH-9 intent survives the rewrite.
    assert "default-inert schema/scaffold module" in prompt
    assert "APPEND/CREATE/UPSERT" in prompt
    # The shape rules the validator actually enforces are now stated.
    assert "NO import statements of any kind" in prompt
    assert "NO `class` statements" in prompt
    assert "NO underscore-prefixed names" in prompt
    assert "`(ok, reason)` tuple instead of raising" in prompt
    assert MEMORY_SCHEMA_SHAPE_EXAMPLE in prompt


def test_strict_denylist_names_are_explicit() -> None:
    names = {node.__name__ for node in SAFETY_STRICT_NODE_DENYLIST}
    assert {
        "Import",
        "ImportFrom",
        "With",
        "While",
        "Lambda",
        "ClassDef",
        "Raise",
        "Global",
        "Delete",
        "Yield",
        "Await",
    } <= names


def test_strict_profile_rejects_underscore_names() -> None:
    code = "def helper(value):\n    _cache = value\n    return _cache\n"
    report = screen_static_safety(code, strict=True)
    assert report.safe is False
    assert any("underscore" in v for v in report.violations)


def test_strict_profile_is_not_applied_to_existing_file_mutations() -> None:
    # The same content is fine for an edit lane (imports + classes allowed there).
    assert screen_static_safety(BENIGN, strict=False).safe is True
    assert screen_static_safety(BENIGN, strict=True).safe is False


def test_import_allowlist_and_banned_modules_are_disjoint() -> None:
    assert not (SAFETY_IMPORT_ALLOWLIST & SAFETY_BANNED_MODULES)


# ---------------------------------------------------------------------------
# Validation must not touch the repo or execute the candidate
# ---------------------------------------------------------------------------

_SIDE_EFFECT_CANDIDATE = """import pathlib

pathlib.Path("MHS_MARKER").write_text("pwned")


def f():
    return 1
"""


def test_validation_never_writes_the_target_file(tmp_path: Path) -> None:
    target = "src/tool_policy.py"
    abs_path = ROOT / target
    before_bytes = abs_path.read_bytes()
    before_stat = abs_path.stat()

    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)
    # Keep the original body so the shrinkage guard does not short-circuit the
    # screen: the rejection must come from the static safety denylist itself.
    candidate = before_bytes.decode() + "\n" + _SIDE_EFFECT_CANDIDATE
    valid, reason = forge._validate_code_mutation(
        before_bytes.decode(),
        candidate,
        target,
    )

    assert valid is False
    assert "banned" in reason or "top-level" in reason
    assert abs_path.read_bytes() == before_bytes
    after_stat = abs_path.stat()
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert after_stat.st_size == before_stat.st_size
    assert not (ROOT / "MHS_MARKER").exists()
    assert not (Path.cwd() / "MHS_MARKER").exists()


def test_validation_does_not_import_the_candidate_module(tmp_path: Path) -> None:
    """The old step 4 deleted the module from sys.modules and re-imported it."""
    target = "src/tool_policy.py"
    module_name = "src.tool_policy"
    before = sys.modules.get(module_name)

    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)
    source = (ROOT / target).read_text()
    valid, _ = forge._validate_code_mutation(source, source, target)

    assert valid is True
    assert sys.modules.get(module_name) is before


def test_validation_of_a_nonexistent_new_file_creates_nothing(tmp_path: Path) -> None:
    target = "src/generated/mhs_probe_module.py"
    abs_path = ROOT / target
    assert not abs_path.exists()

    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)
    valid, _ = forge._validate_code_mutation(
        "",
        "def probe():\n    return 1\n",
        target,
        is_new_file=True,
    )

    assert valid is True
    assert not abs_path.exists()


def test_screen_report_carries_effect(tmp_path: Path) -> None:
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)
    report = forge._screen_code_mutation(
        "",
        "def probe():\n    return 1\n",
        "src/generated/mhs_probe_module.py",
        is_new_file=True,
    )
    assert report.safe is True
    assert report.effect is MutationEffect.INERT


# ---------------------------------------------------------------------------
# Effect enum — MHS-1
# ---------------------------------------------------------------------------


def test_effect_enum_is_closed() -> None:
    assert {e.value for e in MutationEffect} == {
        "inert",
        "constrain",
        "expand",
        "replace",
        "unsafe",
        "unknown",
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CONSTRAIN", MutationEffect.CONSTRAIN),
        (" replace ", MutationEffect.REPLACE),
        ("add-only", MutationEffect.CONSTRAIN),
        ("no_op", MutationEffect.INERT),
        ("MutationEffect.expand", MutationEffect.EXPAND),
        ("override", MutationEffect.REPLACE),
        ("rewrite", MutationEffect.REPLACE),
        (MutationEffect.UNSAFE, MutationEffect.UNSAFE),
    ],
)
def test_effect_normalization(raw: object, expected: MutationEffect) -> None:
    assert MutationEffect.normalize(raw) is expected


@pytest.mark.parametrize("raw", [None, 7, "", "escalate_to_operator", "x" * 500, object()])
def test_unrecognized_effects_normalize_to_unknown(raw: object) -> None:
    assert MutationEffect.normalize(raw) is MutationEffect.UNKNOWN


def test_classify_new_file_is_inert() -> None:
    assert (
        classify_mutation_effect("", "def f():\n    return 1\n", is_new_file=True)
        is MutationEffect.INERT
    )


def test_classify_add_only_is_constrain() -> None:
    original = "def f(x):\n    return x\n"
    mutated = "def f(x):\n    if x < 0:\n        return 0\n    return x\n"
    assert classify_mutation_effect(original, mutated) is MutationEffect.CONSTRAIN


def test_classify_added_definition_is_expand() -> None:
    original = "def f(x):\n    return x\n"
    mutated = original + "\n\ndef g(x):\n    return x + 1\n"
    assert classify_mutation_effect(original, mutated) is MutationEffect.EXPAND


def test_classify_rewritten_body_is_replace() -> None:
    original = "def f(x):\n    return x\n"
    mutated = "def f(x):\n    return 0\n"
    assert classify_mutation_effect(original, mutated) is MutationEffect.REPLACE


def test_classify_removed_definition_is_replace() -> None:
    original = "def f(x):\n    return x\n\n\ndef g(x):\n    return x\n"
    mutated = "def f(x):\n    return x\n"
    assert classify_mutation_effect(original, mutated) is MutationEffect.REPLACE


def test_classify_unparsable_is_unknown() -> None:
    assert classify_mutation_effect("def f(:\n", "def f():\n    pass\n") is MutationEffect.UNKNOWN


def test_code_mutation_defaults_to_unknown_effect() -> None:
    mutation = CodeMutation(
        file="src/tool_policy.py", mutation_type="targeted_fix", description="d"
    )
    assert mutation.effect is MutationEffect.UNKNOWN


def test_apply_rejects_unsafe_effect(tmp_path: Path) -> None:
    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)
    mutation = CodeMutation(
        file="src/tool_policy.py",
        mutation_type="targeted_fix",
        description="d",
        mutated_content="def f():\n    return 1\n",
    )
    mutation.syntax_valid = True
    mutation.effect = MutationEffect.UNSAFE

    target = ROOT / "src/tool_policy.py"
    before = target.read_bytes()
    result = forge.apply_code_mutation(mutation)

    assert result == {"status": "rejected", "reason": "effect_unsafe"}
    assert target.read_bytes() == before
    assert mutation.accepted is False


def test_apply_in_context_reports_effect(tmp_path: Path) -> None:
    class _Ctx:
        worktree_path = tmp_path
        applied: list[tuple[str, str]] = []

        def apply_file(self, path: str, content: str) -> None:
            self.applied.append((path, content))

    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)
    mutation = CodeMutation(
        file="src/tool_policy.py",
        mutation_type="targeted_fix",
        description="d",
        mutated_content="def f():\n    return 1\n",
    )
    mutation.syntax_valid = True
    mutation.effect = MutationEffect.CONSTRAIN

    result = forge.apply_code_mutation_in_context(_Ctx(), mutation)
    assert result["status"] == "applied_isolated"
    assert result["effect"] == "constrain"


def test_apply_in_context_rejects_unsafe_effect(tmp_path: Path) -> None:
    class _Ctx:
        worktree_path = tmp_path

        def apply_file(self, path: str, content: str) -> None:  # pragma: no cover
            raise AssertionError("must not apply an unsafe mutation")

    forge = PromptForge(prompts_dir=tmp_path, auto_commit=False)
    mutation = CodeMutation(
        file="src/tool_policy.py",
        mutation_type="targeted_fix",
        description="d",
        mutated_content="def f():\n    return 1\n",
    )
    mutation.syntax_valid = True
    mutation.effect = MutationEffect.UNSAFE

    assert forge.apply_code_mutation_in_context(_Ctx(), mutation) == {
        "status": "rejected",
        "reason": "effect_unsafe",
    }
