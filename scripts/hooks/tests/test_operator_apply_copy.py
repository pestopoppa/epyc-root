#!/usr/bin/env python3
"""Guard the operator-apply-copy guard.

Two families of test carry the weight:

POSITIVE (the guard must FAIL when the property is violated) — the exact historical
mutation (`if False and autopilot_running()`), a byte-identical copy, and a heavier
mutation that deletes the gate and renames its identifiers. All three must be refused,
because the guard keys on DERIVATION, not on the gate's presence.

NEGATIVE (the guard must not forbid its own documentation, or the compliant path) —
the canonical original at its canonical path, mentions inside quotes/heredocs/comments,
ordinary script invocations, reading a copy rather than running it, and the guard's own
source files. A guard that forbids its own documentation is a failure this repo has
already paid for twice (C21, C47).

Plus the vacuous-verification check: with an EMPTY corpus of protected originals the
scanner must refuse to answer rather than say `clean`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent
REPO = HOOKS.parent.parent
sys.path.insert(0, str(HOOKS))
from operator_apply_copy_scan import (  # noqa: E402
    CONTAINMENT_THRESHOLD,
    MIN_ORIGINAL_LINES,
    copy_execution_verdict,
    derived_copies,
    distinctive_lines,
    protected_originals,
)

ORIGINAL = REPO / "artifacts/operator/apply_e8_quality_baseline_state.py"
HOOK = HOOKS / "check_operator_apply_copy.sh"


# --------------------------------------------------------------------------- corpus


def test_the_protected_corpus_is_not_empty() -> None:
    """The EMPTY-input failure mode: a guard with no corpus clears everything."""
    originals = protected_originals()
    assert len(originals) >= 10, f"only {len(originals)} protected originals discovered"
    assert ORIGINAL.resolve() in originals, "the incident's own script is not protected"


def test_an_empty_corpus_refuses_to_answer() -> None:
    with pytest.raises(RuntimeError):
        derived_copies("python3 /tmp/whatever.py", originals={})


def test_the_corpus_is_derived_not_listed() -> None:
    """Ungated helpers under a protected root must NOT be protected, or the guard
    would block every script that happens to sit in artifacts/operator/."""
    names = {p.name for p in protected_originals()}
    assert "apply_e8_quality_baseline_state.py" in names
    # A data/regenerator helper with no human-only gate marker stays out.
    assert "e8_quality_pool_regenerator.py" not in names


def test_a_tiny_gated_stub_is_not_admitted_as_an_original(tmp_path: Path) -> None:
    """Pins MIN_ORIGINAL_LINES. The live corpus bottoms out at 48 distinctive lines,
    so the constant is invisible there; a synthetic root makes it falsifiable.

    A 3-line "original" is 100%-contained in anything that quotes it — admitting one
    would turn the guard into a blanket refusal of unrelated scripts.
    """
    root = tmp_path / "protected"
    root.mkdir()
    (root / "stub.sh").write_text(
        "#!/bin/bash\n# human-only\nset -euo pipefail\necho 'apply something now'\n",
        encoding="utf-8",
    )
    assert protected_originals(roots=(str(root),)) == {}

    big = root / "real.sh"
    big.write_text(
        "#!/bin/bash\n# human-only\n"
        + "\n".join(f"printf 'apply step %s of the transaction\\n' {i}" for i in range(MIN_ORIGINAL_LINES + 5))
        + "\n",
        encoding="utf-8",
    )
    assert set(protected_originals(roots=(str(root),))) == {big.resolve()}


# ------------------------------------------------------- positive: copies are refused


def _copy(tmp_path: Path, name: str, transform=lambda text: text) -> Path:
    dest = tmp_path / name
    dest.write_text(transform(ORIGINAL.read_text(encoding="utf-8")), encoding="utf-8")
    return dest


def test_the_exact_historical_mutation_is_refused(tmp_path: Path) -> None:
    """`if False and canonical.autopilot_running()` — the C6 agent's actual patch."""
    copy = _copy(
        tmp_path,
        "apply_e8_copy.py",
        lambda t: t.replace("if autopilot_running():", "if False and autopilot_running():"),
    )
    assert "if False and autopilot_running():" in copy.read_text()
    assert copy_execution_verdict(f"python3 {copy} --attest TOK") == "derived-copy"


def test_a_verbatim_copy_is_refused(tmp_path: Path) -> None:
    """Keys on derivation, not on the gate being missing. This is the whole point:
    a copy whose gate is still intact today can be ungated tomorrow."""
    copy = _copy(tmp_path, "apply_verbatim.py")
    assert copy_execution_verdict(f"python3 {copy} --plan") == "derived-copy"


def test_a_heavily_mutated_copy_is_still_refused(tmp_path: Path) -> None:
    """Gate function deleted outright, identifiers renamed, comments stripped —
    the mutation a copier would reach for after learning the naive one is caught."""

    def transform(text: str) -> str:
        lines = text.splitlines()
        out, skipping = [], False
        for line in lines:
            if line.startswith("def autopilot_running("):
                skipping = True
                continue
            if skipping:
                if line and not line[0].isspace():
                    skipping = False
                else:
                    continue
            if line.lstrip().startswith("#"):
                continue
            out.append(
                line.replace("autopilot_running()", "False")
                .replace("ApplyError", "OpError")
                .replace("E8 baseline-state", "baseline-state")
            )
        return "\n".join(out) + "\n"

    copy = _copy(tmp_path, "reworked_apply.py", transform)
    body = copy.read_text()
    assert "autopilot_running" not in body and "ApplyError" not in body
    assert copy_execution_verdict(f"python3 {copy} --attest TOK") == "derived-copy"


@pytest.mark.parametrize(
    "command",
    [
        "python3 {p} --attest TOK",
        "python3 {p}",
        "bash -x /bin/true && python3 {p} --recover TOK",
        "timeout 600 python3 {p} --attest TOK",
        "cd /tmp; python3 {p} --attest TOK",
        "PYTHONPATH=/x python3 {p} --attest TOK",
    ],
)
def test_invocation_shapes_are_all_refused(tmp_path: Path, command: str) -> None:
    copy = _copy(tmp_path, "apply_shapes.py")
    assert copy_execution_verdict(command.format(p=copy)) == "derived-copy"


def test_a_shell_original_copy_is_refused(tmp_path: Path) -> None:
    src = REPO / "artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh"
    dest = tmp_path / "ratify_copy.sh"
    dest.write_text(
        src.read_text(encoding="utf-8").replace(
            "autopilot_running &&", "false && autopilot_running &&"
        ),
        encoding="utf-8",
    )
    assert copy_execution_verdict(f"bash {dest}") == "derived-copy"


# ------------------------------------------------- negative: the compliant path passes


def test_the_canonical_original_is_never_blocked() -> None:
    for command in (
        f"python3 {ORIGINAL} --plan",
        f"python3 {ORIGINAL} --validate-only --state s.json --evidence e.json",
        "python3 artifacts/operator/apply_e8_quality_baseline_state.py --status",
        "bash artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh",
    ):
        assert copy_execution_verdict(command) == "clean", command


def test_reading_a_copy_is_not_executing_it(tmp_path: Path) -> None:
    """Auditing a suspicious copy is how the 2026-08-05 incident was contained.
    Blocking the audit would make the guard worse than useless."""
    copy = _copy(tmp_path, "suspect.py")
    for command in (
        f"diff {ORIGINAL} {copy}",
        f"grep -n autopilot_running {copy}",
        f"cp {ORIGINAL} {copy}",
        f"sha256sum {copy}",
        f"git diff --no-index {ORIGINAL} {copy}",
    ):
        assert copy_execution_verdict(command) == "clean", command


def test_mentions_are_data_not_invocations(tmp_path: Path) -> None:
    copy = _copy(tmp_path, "mentioned.py")
    for command in (
        f'echo "never run python3 {copy} --attest"',
        f"python3 bus.py append --json '{{\"note\":\"ran python3 {copy}\"}}'",
        f"true # python3 {copy} --attest TOK is what the C6 agent did",
        f"cat <<'EOF'\npython3 {copy} --attest TOK\nEOF",
    ):
        assert copy_execution_verdict(command) == "clean", command


def test_ordinary_repo_invocations_are_untouched() -> None:
    for command in (
        "python3 scripts/handoffs/index_state.py --check",
        "python3 -m pytest scripts/hooks/tests/ -q",
        "bash scripts/session/health_check.sh",
        "python3 scripts/coordination/session_bus.py drain --agent mainA",
        "./scripts/hooks/check_operator_apply_copy.sh",
        "ls artifacts/operator/*.py",
    ):
        assert copy_execution_verdict(command) == "clean", command


def test_an_unrelated_script_in_a_scratch_dir_passes(tmp_path: Path) -> None:
    other = tmp_path / "unrelated.py"
    other.write_text(
        "\n".join(f"value_{i} = compute_something({i}) + offset_table[{i}]" for i in range(80)),
        encoding="utf-8",
    )
    assert copy_execution_verdict(f"python3 {other}") == "clean"


def test_the_guard_does_not_forbid_its_own_source() -> None:
    """Both the scanner and the hook DESCRIBE the copy attack in prose. Feeding each
    to the guard as a command must be clean, and neither may fingerprint as a copy."""
    originals = protected_originals()
    for path in (HOOK, HOOKS / "operator_apply_copy_scan.py", Path(__file__)):
        text = path.read_text(encoding="utf-8")
        assert copy_execution_verdict(text, originals) == "clean", path
        fingerprint = distinctive_lines(text)
        worst = max(
            len(fingerprint & fp) / len(fp) for fp in originals.values()
        )
        assert worst < CONTAINMENT_THRESHOLD, f"{path} fingerprints as a copy ({worst:.2f})"


def test_rewriting_every_comment_does_not_launder_a_copy(tmp_path: Path) -> None:
    """Pins WHY `distinctive_lines` drops comments.

    The live corpus is ~1% comments, so this property is invisible there — dropping
    the comment filter breaks nothing measurable and the check would be decorative.
    A synthetic comment-heavy original makes it falsifiable: with the filter the
    comment-rewritten copy is caught; the second assertion shows that without it the
    same copy would score under threshold and walk.
    """
    root = tmp_path / "protected"
    root.mkdir()
    code = [f"result_{i} = transform(record_{i}, options=DEFAULTS)" for i in range(40)]
    comments = [f"# explanatory prose about step {i} of the apply transaction" for i in range(60)]
    original = root / "apply_synthetic.py"
    original.write_text(
        '"""human-only apply."""\nTOKEN = "--attest"\n' + "\n".join(comments + code) + "\n",
        encoding="utf-8",
    )
    originals = protected_originals(roots=(str(root),))
    assert original.resolve() in originals

    laundered = tmp_path / "laundered.py"
    laundered.write_text(
        '"""human-only apply."""\nTOKEN = "--attest"\n'
        + "\n".join([f"# completely different wording, revision {i}" for i in range(60)] + code)
        + "\n",
        encoding="utf-8",
    )
    assert copy_execution_verdict(f"python3 {laundered}", originals) == "derived-copy"

    def with_comments(text: str) -> set[str]:
        return {ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 12}

    naive = with_comments(laundered.read_text()) & with_comments(original.read_text())
    assert len(naive) / len(with_comments(original.read_text())) < CONTAINMENT_THRESHOLD


def test_a_partial_excerpt_is_deliberately_allowed(tmp_path: Path) -> None:
    """Documents the threshold rather than asserting a spelling: lifting a minority
    of an original's lines into a new tool is not a copy and must not be blocked."""
    lines = ORIGINAL.read_text(encoding="utf-8").splitlines()
    excerpt = tmp_path / "excerpt.py"
    excerpt.write_text("\n".join(lines[: len(lines) // 4]) + "\n", encoding="utf-8")
    assert copy_execution_verdict(f"python3 {excerpt}") == "clean"


# ------------------------------------------------------------------ end-to-end hook


def _run_hook(command: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, capture_output=True, text=True
    )


@pytest.mark.skipif(shutil.which("jq") is None, reason="hook needs jq")
def test_hook_blocks_the_copy_and_allows_the_original(tmp_path: Path) -> None:
    copy = _copy(
        tmp_path,
        "hook_copy.py",
        lambda t: t.replace("if autopilot_running():", "if False and autopilot_running():"),
    )
    blocked = _run_hook(f"python3 {copy} --attest TOK")
    assert blocked.returncode == 2, blocked.stderr
    assert "DERIVED COPY" in blocked.stderr
    assert str(copy) in blocked.stderr and "reproduces" in blocked.stderr

    allowed = _run_hook(f"python3 {ORIGINAL} --plan")
    assert allowed.returncode == 0, allowed.stderr


@pytest.mark.skipif(shutil.which("jq") is None, reason="hook needs jq")
def test_hook_ignores_non_bash_tools(tmp_path: Path) -> None:
    copy = _copy(tmp_path, "write_payload.py")
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": str(copy), "content": "x"}}
    )
    done = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True)
    assert done.returncode == 0


# ------------------------------------------------------------------------ lint mode


def test_lint_mode_flags_a_copy_and_refuses_empty_input(tmp_path: Path) -> None:
    scan = HOOKS / "operator_apply_copy_scan.py"
    copy = _copy(tmp_path, "lint_copy.py")
    flagged = subprocess.run(
        [sys.executable, str(scan), str(copy)], capture_output=True, text=True
    )
    assert flagged.returncode == 1 and flagged.stdout.startswith("derived-copy\t")

    ok = subprocess.run(
        [sys.executable, str(scan), str(ORIGINAL)], capture_output=True, text=True
    )
    assert ok.returncode == 0 and ok.stdout.startswith("canonical\t")

    empty = tmp_path / "empty.py"
    empty.write_text("", encoding="utf-8")
    refused = subprocess.run(
        [sys.executable, str(scan), str(empty)], capture_output=True, text=True
    )
    assert refused.returncode == 2 and "refusing to emit a verdict" in refused.stderr

    blank_stdin = subprocess.run(
        [sys.executable, str(scan)], input="", capture_output=True, text=True
    )
    assert blank_stdin.returncode == 2
