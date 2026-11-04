"""LOOP-53 (operator decision B, 2026-11-02): the destructive-scratch hook has NO override.

The refusal used to end with "or set EPYC_ALLOW_SCRATCH_DELETE=...", an override no tool call
could set. The operator chose to remove the mention and keep no override path. These tests pin
that: the refusal names no override, the former env name does not unlock anything, and the
fixture table shared with test_destructive_scratch_hook.sh still holds when run through the hook.

Dangerous strings are assembled from pieces (as in destructive_scratch_cases.py) so this file
never contains a runnable delete line.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
HOOK = HOOKS / "check_destructive_scratch.sh"
SCAN = HOOKS / "destructive_scratch_scan.py"
CASES = HOOKS / "tests" / "destructive_scratch_cases.py"

R = "rm"
RF = R + " -" + "rf"
T = "/mnt/raid0/llm/tm" + "p"
FORMER_ENV = "EPYC_ALLOW_" + "SCRATCH_DELETE"


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if k not in (FORMER_ENV, "EPYC_DESTRUCTIVE_SCRATCH_ROOTS")}
    env.update(extra or {})
    return env


def _scan(command: str, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCAN)], input=command, text=True,
                          capture_output=True, env=_env(extra), timeout=60)


def test_refusal_message_names_no_override() -> None:
    res = _scan(f"{RF} {T}/x")
    assert res.returncode == 2
    assert "guarded_rm.sh" in res.stderr          # the sanctioned route is still named
    assert FORMER_ENV not in res.stderr
    assert "override" not in res.stderr.lower()
    assert "EPYC_" not in res.stderr               # no environment knob of any name


@pytest.mark.parametrize("value", ["operator: dp 2026-11-02: test", "yes please"])
def test_former_override_env_does_not_unlock(value: str) -> None:
    res = _scan(f"{RF} {T}/x", {FORMER_ENV: value})
    assert res.returncode == 2
    assert "override" not in res.stderr.lower()


def test_scanner_source_has_no_override_constant() -> None:
    src = SCAN.read_text(encoding="utf-8")
    assert "os.environ.get(ACK_ENV" not in src and "ACK_ENV" not in src


def _cases(tmp_path: Path) -> list[dict]:
    fake = tmp_path / "fakeroot"
    (fake / "full" / "sub").mkdir(parents=True)
    (fake / "empty").mkdir()
    rt = "shutil" + ".rmtree"
    (tmp_path / "purge_batch.py").write_text(
        f'import shutil\nRT=x\n{rt}("/mnt/raid0/llm/.trash/b1")\n', encoding="utf-8")
    (tmp_path / "harmless.py").write_text('print("hello")\n', encoding="utf-8")
    out = subprocess.run([sys.executable, str(CASES), str(tmp_path), str(fake)],
                         capture_output=True, text=True, check=True, timeout=60)
    return json.loads(out.stdout)


@pytest.mark.skipif(shutil.which("jq") is None or shutil.which("bash") is None,
                    reason="the hook needs bash and jq")
def test_fixture_table_through_the_hook(tmp_path: Path) -> None:
    failures = []
    for case in _cases(tmp_path):
        raw = case["raw"] if "raw" in case else json.dumps(case["input"])
        res = subprocess.run(["bash", str(HOOK)], input=raw, text=True, capture_output=True,
                             env=_env(case["env"]), timeout=60)
        got = "block" if res.returncode == 2 else "allow"
        if got != case["expect"]:
            failures.append((case["name"], case["expect"], res.returncode, res.stderr[:200]))
        if got == "block" and ("guarded_rm.sh" not in res.stderr or FORMER_ENV in res.stderr):
            failures.append((case["name"], "refusal route", res.returncode, res.stderr[:200]))
    assert (tmp_path / "fakeroot" / "full" / "sub").is_dir()   # the hook never deletes
    assert failures == []
