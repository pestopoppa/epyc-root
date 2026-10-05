"""Importing the stack launcher must have NO argv side effect.

Regression for the import-time ``os.execv`` re-exec in
``scripts/server/orchestrator_stack.py``: it replaced the *importer's* process
with ``orchestrator_stack.py <importer's argv[1:]>``, so every tool that imports
the launcher (``autokernel_enrollment.py`` imports it only to pin
``launcher.__file__`` and ``launcher.STACK_PRIORS_PATH``) died parsing its own
flags against the launcher's subparsers.  The failure is invisible to in-process
defences -- ``execv`` replaces the process, so neither patching ``argparse`` nor
catching ``SystemExit`` can observe it.  Only a subprocess probe can.

The re-exec only fires when the running interpreter is NOT the project venv
python, so the probe must be launched with a different interpreter; running the
probe under ``.venv/bin/python`` would pass even against the broken module.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VENV_PY = REPO_ROOT / ".venv/bin/python"

_PROBE = (
    "import os, sys; sys.path.insert(0, %r); pid = os.getpid();"
    "import scripts.server.orchestrator_stack as m;"
    "assert m.__file__ and os.getpid() == pid"
) % str(REPO_ROOT)

HOSTILE_ARGV = [
    ["--master-registry", "foo.yaml", "--revision", "deadbeef"],
    ["start", "--only", "worker_general"],
    ["--help"],
    ["stop", "--all"],
]


def _foreign_interpreter() -> str:
    """An interpreter that is not the project venv python (so re-exec would fire)."""
    resolved_venv = VENV_PY.resolve() if VENV_PY.exists() else None
    candidates = [
        "/usr/bin/python3",
        shutil.which("python3"),
        getattr(sys, "_base_executable", None),
        sys.executable,
    ]
    for cand in candidates:
        if not cand or not Path(cand).exists():
            continue
        if resolved_venv is None or Path(cand).resolve() != resolved_venv:
            return cand
    pytest.skip("no interpreter distinct from the project venv python is available")


def _probe_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("ORCHESTRATOR_STACK_REEXEC", None)  # the escape hatch must not mask the bug
    return env


def _run_probe(code: str, extra_argv: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [_foreign_interpreter(), "-c", code, *extra_argv],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=_probe_env(),
        timeout=300,
    )
    if "ModuleNotFoundError" in proc.stderr:
        pytest.skip(f"probe interpreter lacks a dependency: {proc.stderr.strip().splitlines()[-1]}")
    return proc


def test_import_with_hostile_argv_does_not_exit_or_print() -> None:
    for extra in HOSTILE_ARGV:
        proc = _run_probe(_PROBE, extra)
        assert proc.returncode == 0, (
            f"importing orchestrator_stack with argv {extra!r} exited "
            f"{proc.returncode}: {proc.stderr.strip()!r}"
        )
        assert proc.stdout == "", f"import wrote to stdout with argv {extra!r}: {proc.stdout!r}"
        assert proc.stderr == "", f"import wrote to stderr with argv {extra!r}: {proc.stderr!r}"


def test_import_does_not_replace_the_importing_process() -> None:
    code = (
        "import os, sys; sys.path.insert(0, %r); pid = os.getpid();"
        "import scripts.server.orchestrator_stack;"
        "sys.stderr.write('SURVIVED' if os.getpid() == pid else 'REPLACED')"
    ) % str(REPO_ROOT)
    proc = _run_probe(code, ["--master-registry", "foo.yaml"])
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr.strip() == "SURVIVED", (proc.stdout, proc.stderr)


def test_reexec_helper_is_still_available_for_the_entry_point() -> None:
    """The venv re-exec must survive as an explicit __main__-only step."""
    from scripts.server import orchestrator_stack as launcher

    assert callable(launcher._reexec_under_project_venv)
    source = Path(launcher.__file__).read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":\n    # Runs BEFORE' in source, (
        "the re-exec must be invoked only under the __main__ guard"
    )
    assert source.count("os.execv(") == 1, "re-exec should have exactly one call site"
