"""The signer of a ratification is typed by a human, never defaulted.

RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926 recorded `operator: "node"` because every
ratifier resolved the signer as "${RATIFY_OPERATOR:-${USER:-unknown}}". These tests pin
the repair: the receipt tool refuses an unset, system-account, login or agent-id name,
the shared shell guard exits the calling script, and no ratifier keeps a $USER fallback
(except the one historical script whose exemption pins its as-run bytes).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts/operator/ratification_receipt.py"
LIB = ROOT / "scripts/operator/lib/ratify_operator.sh"
EXEMPTIONS = ROOT / "scripts/validate/ratification_receipt_exemptions.json"


def _load_tool():
    spec = importlib.util.spec_from_file_location("ratification_receipt", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve their module by name
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


@pytest.mark.parametrize("name", [None, "", "   ", "node", "ROOT", "unknown", "nobody", "claude",
                                  "workspace-8d", "mainA", "codex-cli", "fable5"])
def test_refused_names(tool, name):
    assert tool.operator_problem(name) is not None


def test_login_account_is_refused(tool, monkeypatch):
    monkeypatch.setenv("USER", "someloginname")
    assert tool.operator_problem("someloginname") is not None
    assert tool.operator_problem("SomeLoginName") is not None


@pytest.mark.parametrize("name", ["Daniele Pinna", "tester", "pestopoppa-signs"])
def test_accepted_names(tool, name, monkeypatch):
    monkeypatch.setenv("USER", "node")
    monkeypatch.setenv("LOGNAME", "node")
    assert tool.operator_problem(name) is None


def _check(name: str | None, env_name: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("RATIFY_OPERATOR", None)
    if env_name is not None:
        env["RATIFY_OPERATOR"] = env_name
    argv = ["python3", str(TOOL), "check-operator"] + ([name] if name is not None else [])
    return subprocess.run(argv, capture_output=True, text=True, env=env)


def test_check_operator_cli():
    assert _check("node").returncode == 65
    assert _check(None).returncode == 65
    ok = _check(None, env_name="  Daniele Pinna ")
    assert ok.returncode == 0 and ok.stdout.strip() == "Daniele Pinna"


def _lib(script: str, env_name: str | None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("RATIFY_OPERATOR", None)
    if env_name is not None:
        env["RATIFY_OPERATOR"] = env_name
    return subprocess.run(["bash", "-c", f'source "{LIB}"; {script}'],
                          capture_output=True, text=True, env=env)


def test_shell_guard_exits_calling_script():
    r = _lib('ratify_require_operator; echo SHOULD-NOT-REACH', env_name="node")
    assert r.returncode == 65 and "SHOULD-NOT-REACH" not in r.stdout
    r = _lib('ratify_require_operator; echo SHOULD-NOT-REACH', env_name=None)
    assert r.returncode == 65
    r = _lib('ratify_require_operator; echo "signed:$RATIFY_OPERATOR"', env_name="Daniele Pinna")
    assert r.returncode == 0 and "signed:Daniele Pinna" in r.stdout
    r = _lib('ratify_require_operator "root"', env_name="Daniele Pinna")
    assert r.returncode == 65


# A non-empty shell default (`${RATIFY_OPERATOR:-$USER}`, `:-unknown`) or a Python `or $USER`.
# `${RATIFY_OPERATOR:-}` (empty default under set -u) is not a fallback.
FALLBACK_RE = re.compile(r"RATIFY_OPERATOR:-[^}]|\bor\s+os\.environ\.get\(\s*[\"']USER[\"']")


def test_no_ratifier_falls_back_to_user():
    """Class check: a new ratifier with the $USER fallback fails here, not in an audit.

    Exempt historical scripts are skipped: the exemption pins their as-run sha256, so
    editing one would lapse it (check_ratification_receipts.py) and the exemption list
    is human-only. Each is also unreachable on the fallback line (already applied).
    """
    exempt = {e["script"] for e in json.loads(EXEMPTIONS.read_text())["exemptions"]}
    offenders = []
    for pattern in ("scripts/operator/**/*.sh", "scripts/operator/**/*.py",
                    "artifacts/operator/**/*.sh", "artifacts/operator/**/*.py",
                    "scripts/**/ratify_*.sh", "scripts/**/ratify_*.py"):
        for path in ROOT.glob(pattern):
            rel = path.relative_to(ROOT).as_posix()
            if rel in exempt or rel == "scripts/operator/lib/ratify_operator.sh":
                continue
            code = "\n".join(l for l in path.read_text(errors="replace").splitlines()
                             if not l.lstrip().startswith("#"))
            if FALLBACK_RE.search(code):
                offenders.append(rel)
    assert not offenders, f"ratifiers with a defaulted signer: {sorted(set(offenders))}"
