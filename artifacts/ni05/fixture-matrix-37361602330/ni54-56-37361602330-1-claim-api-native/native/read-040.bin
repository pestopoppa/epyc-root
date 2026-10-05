"""Backward-compatible shim — actual module at src/runtime/inference_lock.py.

Resolution normally never reaches this file's body: `src/__init__.py`
installs a MetaPathFinder (ahead of the standard path finder) that resolves
"src.inference_lock" straight to the already-imported
`src.runtime.inference_lock` module object via ``Loader.create_module()``,
so ``sys.modules["src.inference_lock"]`` is set to its FINAL value the one
and only time it is ever inserted -- no concurrent importer can ever
observe a half-swapped placeholder for this name.

Why this file used to be unsafe (TD-21): the previous version of this shim
did ``sys.modules[__name__] = _real`` from inside its own module body. That
pattern creates a window, protected only by CPython's own per-module import
lock, during which a concurrent first-time importer's fast path can read
this name's ``__spec__._initializing`` flag off the WRONG (already-loaded)
target spec and skip the lock entirely. Empirically this produced
intermittent ``ImportError: cannot import name 'inference_lock' from
'src.inference_lock'`` at roughly 1% frequency under 24-way concurrent
first import (confirmed via a subprocess stress harness; see
tests/unit/test_inference_lock_concurrent_import.py, which fails on the old
shim body and passes on the alias-finder fix).

The code below is a defense-in-depth fallback for the
(should-not-happen) case where this file's ``exec_module()`` runs
directly -- e.g. the alias finder in ``src/__init__.py`` failed to
install for some reason. It reproduces the pre-fix shim behavior; under
normal operation it is never reached (the finder wins first).
"""
import importlib as _il
import sys as _sys

_real = _il.import_module("src.runtime.inference_lock")
_sys.modules[__name__] = _real
