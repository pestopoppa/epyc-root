"""K4 (handoffs/active/dynamic-stack-concurrency.md): llama.cpp clamps
``cparams.n_ubatch = min(n_batch, n_ubatch)``, and the launcher never emits
``-b`` on any of its command-builder paths, so ``n_batch`` defaults to 2048.
A declared ``-ub`` above 2048 was therefore silently inert -- the server's
EFFECTIVE micro-batch was 2048 no matter what the launcher printed on the
command line.

These tests pin the fix at the two points that made the defect possible:

  1. ``orchestration/launch_manifest.yaml``'s ``default_ubatch_tokens`` (the
     source of ``stack_manifest.DEFAULT_UBATCH_TOKENS``) must not declare a
     value above the clamp -- it now equals it (2048), so the declared and
     effective values agree.
  2. Every command-builder path that emits ``-ub`` without ``-b`` must warn
     (``_warn_if_ubatch_exceeds_batch``) if a future prior or fallback ever
     re-introduces a declared value above the effective batch, so this cannot
     recur silently.

Fixtures use synthetic priors (never the live, possibly-stale
``orchestration/derived/stack_priors.yaml``) so these tests exercise the code
path fixed here, not whatever the last real compile happened to bake in.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

from scripts.server import orchestrator_stack as oss


def _flag_value(cmd: list[str], flag: str) -> str | None:
    if flag not in cmd:
        return None
    idx = cmd.index(flag)
    if idx + 1 >= len(cmd):
        return None
    return cmd[idx + 1]


def _write_launch_prior(
    tmp_path: Path,
    role: str,
    *,
    requirements: dict[str, Any],
    runtime: dict[str, Any],
) -> Path:
    path = tmp_path / "stack_priors.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "roles": {
                    role: {
                        "deployment_status": "live_stack",
                        "serving": {
                            "launch": {
                                "requirements": requirements,
                                "runtime": runtime,
                            }
                        },
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _effective_batch(cmd: list[str]) -> int:
    """The batch llama.cpp actually clamps -ub to: explicit -b, else 2048."""
    explicit = _flag_value(cmd, "-b")
    return int(explicit) if explicit is not None else 2048


def _assert_ubatch_not_inert(cmd: list[str]) -> None:
    ubatch = _flag_value(cmd, "-ub")
    assert ubatch is not None, "-ub missing from command"
    assert int(ubatch) <= _effective_batch(cmd), (
        f"-ub {ubatch} exceeds effective batch {_effective_batch(cmd)} "
        "(llama.cpp clamp n_ubatch=min(n_batch, n_ubatch)) -- declared "
        "ubatch is INERT. K4 regression."
    )


# -----------------------------------------------------------------------------
# 1. Manifest source of truth
# -----------------------------------------------------------------------------


def test_default_ubatch_tokens_does_not_exceed_the_llamacpp_batch_default() -> None:
    # llama.cpp's own default n_batch (used whenever -b is absent, which every
    # builder here does) is 2048. The declared default must not exceed it.
    assert oss.DEFAULT_UBATCH_TOKENS <= 2048


def test_worker_general_degraded_fallback_does_not_exceed_batch_default() -> None:
    assert oss._WORKER_GENERAL_DEGRADED_FALLBACK["ubatch"] <= 2048


# -----------------------------------------------------------------------------
# 2. Main default-mode role builder (_build_role_command, ~orchestrator_stack.py:1463)
# -----------------------------------------------------------------------------


def test_build_role_command_ubatch_not_inert_with_no_priors(
    tmp_path: Path, monkeypatch
) -> None:
    """No compiled priors at all -> falls through to DEFAULT_UBATCH_TOKENS."""
    monkeypatch.setattr(oss, "STACK_PRIORS_PATH", tmp_path / "missing.yaml")
    role = SimpleNamespace(
        name="frontdoor",
        model=SimpleNamespace(full_path="/fallback/frontdoor.gguf"),
        acceleration=SimpleNamespace(type="none", experts=None, draft_role=None),
    )

    cmd = oss._build_role_command(role, port=8070)

    assert "-b" not in cmd  # this builder never emits -b -- pin that fact
    _assert_ubatch_not_inert(cmd)


def test_build_role_command_ubatch_not_inert_representative_roles(
    tmp_path: Path, monkeypatch
) -> None:
    """Representative default-mode roles, each with a synthetic prior."""
    for role_name, declared_ubatch in (
        ("frontdoor", 2048),
        ("architect_general", 2048),
        ("toolrunner", 2048),
    ):
        priors = _write_launch_prior(
            tmp_path,
            role_name,
            requirements={},
            runtime={
                "binary_path": "/prior/llama-server",
                "cache": {
                    "context_tokens": 32768,
                    "slots": 1,
                    "ubatch": declared_ubatch,
                },
                "flags": {"flash_attn": False, "jinja": False, "spec": {"enabled": False}},
            },
        )
        monkeypatch.setattr(oss, "STACK_PRIORS_PATH", priors)
        role = SimpleNamespace(
            name=role_name,
            model=SimpleNamespace(full_path=f"/fallback/{role_name}.gguf"),
            acceleration=SimpleNamespace(type="none", experts=None, draft_role=None),
        )

        cmd = oss._build_role_command(role, port=8070)

        _assert_ubatch_not_inert(cmd)


# -----------------------------------------------------------------------------
# 3. Eval-lane builder (_build_eval_batch_frontdoor_command, ~orchestrator_stack.py:1150)
# -----------------------------------------------------------------------------


def test_eval_batch_frontdoor_command_ubatch_not_inert_with_no_priors(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(oss, "STACK_PRIORS_PATH", tmp_path / "missing.yaml")

    cmd = oss._build_eval_batch_frontdoor_command(18070)

    assert "-b" not in cmd  # this lane never emits -b either
    _assert_ubatch_not_inert(cmd)


def test_eval_batch_frontdoor_command_ubatch_not_inert_with_synthetic_prior(
    tmp_path: Path, monkeypatch
) -> None:
    priors = _write_launch_prior(
        tmp_path,
        "frontdoor",
        requirements={"model_path": "/prior/frontdoor.gguf"},
        runtime={
            "binary_path": "/prior/llama-server",
            "cache": {"context_tokens": 32768, "slots": 2, "ubatch": 2048},
            "flags": {"flash_attn": True, "jinja": True, "spec": {"enabled": False}},
        },
    )
    monkeypatch.setattr(oss, "STACK_PRIORS_PATH", priors)

    cmd = oss._build_eval_batch_frontdoor_command(18070)

    _assert_ubatch_not_inert(cmd)


# -----------------------------------------------------------------------------
# 4. worker_general builder (_build_worker_general_command, ~orchestrator_stack.py:1050)
# -----------------------------------------------------------------------------


def test_build_worker_general_command_ubatch_not_inert_with_no_priors(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(oss, "STACK_PRIORS_PATH", tmp_path / "missing.yaml")

    cmd = oss._build_worker_general_command(
        port=8072, model_path="/m/gemma4.gguf", binary_override=None,
    )

    assert "-b" not in cmd
    _assert_ubatch_not_inert(cmd)


# -----------------------------------------------------------------------------
# 5. Guard fires on a synthetic ubatch > batch config
# -----------------------------------------------------------------------------


def test_warn_if_ubatch_exceeds_batch_fires_on_clamp(capsys) -> None:
    oss._warn_if_ubatch_exceeds_batch("some_role", 8192)  # no explicit batch -> 2048 default

    out = capsys.readouterr().out
    assert "[WARN]" in out
    assert "some_role" in out
    assert "8192" in out
    assert "2048" in out


def test_warn_if_ubatch_exceeds_batch_fires_against_an_explicit_lower_batch(capsys) -> None:
    oss._warn_if_ubatch_exceeds_batch("some_role", 4096, batch=2048)

    out = capsys.readouterr().out
    assert "[WARN]" in out


def test_warn_if_ubatch_exceeds_batch_silent_when_not_clamped(capsys) -> None:
    oss._warn_if_ubatch_exceeds_batch("some_role", 2048)
    oss._warn_if_ubatch_exceeds_batch("some_role", 8192, batch=8192)

    out = capsys.readouterr().out
    assert "[WARN]" not in out


def test_build_role_command_guard_fires_when_prior_declares_above_clamp(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The guard must actually be wired into the builder, not just exist.

    A synthetic prior that (mis)declares ubatch above the 2048 default batch
    must trip the warning -- this is the regression K4 describes: a config
    surface that could misrepresent the effective value with nothing to flag
    it. We are NOT asserting the emitted -ub is coerced down (behaviour-
    neutral fix: the launcher still emits whatever is declared, unmodified;
    only the DEFAULT changed, and a guard now watches for a re-introduced
    mismatch either via priors drift or a future edit).
    """
    priors = _write_launch_prior(
        tmp_path,
        "frontdoor",
        requirements={},
        runtime={
            "binary_path": "/prior/llama-server",
            "cache": {"context_tokens": 32768, "slots": 1, "ubatch": 8192},
            "flags": {"flash_attn": False, "jinja": False, "spec": {"enabled": False}},
        },
    )
    monkeypatch.setattr(oss, "STACK_PRIORS_PATH", priors)
    role = SimpleNamespace(
        name="frontdoor",
        model=SimpleNamespace(full_path="/fallback/frontdoor.gguf"),
        acceleration=SimpleNamespace(type="none", experts=None, draft_role=None),
    )

    cmd = oss._build_role_command(role, port=8070)

    assert _flag_value(cmd, "-ub") == "8192"  # declared value passes through unmodified
    out = capsys.readouterr().out
    assert "[WARN]" in out and "frontdoor" in out
