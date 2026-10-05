"""TD-21: concurrent first-import safety of the `src.inference_lock` shim.

`src/inference_lock.py` is a backward-compatible alias for
`src.runtime.inference_lock`. The pre-fix version of that shim did
``sys.modules[__name__] = _real`` from inside its own module body -- a
pattern that is unsafe under concurrent first import: CPython's import
fast path can read this name's ``__spec__._initializing`` off the WRONG
(already-loaded) target spec while the swap is still in flight and skip
the module lock entirely, handing a concurrent importer a half-swapped
placeholder. Empirically this produced intermittent::

    ImportError: cannot import name 'inference_lock' from 'src.inference_lock'

at roughly 1% frequency under 24-way concurrent first import in a fresh
interpreter (measured via the same subprocess harness used below, run
several thousand times).

The fix (see ``src/__init__.py``) resolves "src.inference_lock" through a
``MetaPathFinder`` whose loader implements ``create_module()`` to hand back
the already-imported target module directly, so
``sys.modules["src.inference_lock"]`` is set to its FINAL value the one and
only time anything is ever inserted under that key. This module proves
both halves: the current tree is safe under the stress harness, and the
harness itself reliably reproduces the old failure against a reconstructed
pre-fix tree.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# tests/unit/test_inference_lock_concurrent_import.py -> tests/unit -> tests -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
ORCH_SRC = REPO_ROOT / "src"

_WORKER_SCRIPT = textwrap.dedent(
    """
    import sys, threading, traceback
    sys.path.insert(0, {repo_root!r})
    sys.setswitchinterval(0.000005)

    errors = []
    N = 24
    barrier = threading.Barrier(N)

    def worker():
        try:
            barrier.wait()
            from src.inference_lock import inference_lock  # noqa: F401
        except BaseException:
            errors.append(traceback.format_exc())

    threads = [threading.Thread(target=worker) for _ in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        sys.stderr.write(errors[0])
        print("FAILED", len(errors))
        sys.exit(1)
    print("OK")
    """
)


def _run_trials(repo_root: Path, trials: int, workers: int = 48) -> int:
    """Run the concurrent-import reproducer ``trials`` times, each a FRESH
    interpreter subprocess rooted at ``repo_root``. Returns how many trials
    raised ImportError under 24-way concurrent first import.
    """
    script = _WORKER_SCRIPT.format(repo_root=str(repo_root))

    def _one(_i: int) -> bool:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode != 0

    failures = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for failed in ex.map(_one, range(trials)):
            if failed:
                failures += 1
    return failures


def test_inference_lock_concurrent_first_import_is_safe():
    """Regression guard: 24 threads racing
    ``from src.inference_lock import inference_lock`` on a fresh interpreter
    must never raise ImportError against the current (fixed) tree.
    """
    failures = _run_trials(ORCH_SRC.parent, trials=120)
    assert failures == 0, (
        f"{failures}/120 concurrent first-import trials raised ImportError; "
        "src.inference_lock is not safe under concurrent import"
    )


_OLD_UNSAFE_SHIM = textwrap.dedent(
    """
    # Backward-compatible shim -- actual module at src/runtime/inference_lock.py
    import importlib as _il
    import sys as _sys
    _real = _il.import_module("src.runtime.inference_lock")
    _real.__name__ = __name__
    _sys.modules[__name__] = _real
    """
)

_OLD_INIT_NO_ALIAS_FINDER = (
    '"""Hierarchical Local-Agent Orchestration (test fixture: pre-TD-21 __init__, '
    'no alias finder installed).\n"""\n'
)


def test_reproducer_catches_the_pre_fix_shim(tmp_path):
    """Self-check: point the exact same harness at a reconstructed pre-fix
    tree (old shim body in src/inference_lock.py, src/__init__.py without
    the alias MetaPathFinder) and confirm it reliably reproduces the
    concurrent-import ImportError. This demonstrates that
    ``test_inference_lock_concurrent_first_import_is_safe`` would have
    failed before the TD-21 fix, and passes after it.
    """
    broken_root = tmp_path / "orch_old"
    shutil.copytree(
        ORCH_SRC,
        broken_root / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (broken_root / "src" / "inference_lock.py").write_text(_OLD_UNSAFE_SHIM, encoding="utf-8")
    (broken_root / "src" / "__init__.py").write_text(_OLD_INIT_NO_ALIAS_FINDER, encoding="utf-8")

    # The race is probabilistic (~1% per trial at this concurrency in the
    # reference environment); run enough trials that a false "no failure"
    # result is vanishingly unlikely (~0.99^700 < 0.1%).
    failures = _run_trials(broken_root, trials=700, workers=64)
    assert failures > 0, (
        "expected the reconstructed pre-fix shim to reproduce the "
        "concurrent-import ImportError at least once in 700 trials; "
        "the harness or fixture is stale"
    )
