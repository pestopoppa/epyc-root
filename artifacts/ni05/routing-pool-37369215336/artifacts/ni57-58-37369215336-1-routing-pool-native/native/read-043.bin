"""
Hierarchical Local-Agent Orchestration.

A multi-tier agent system for CPU-optimized LLM inference on AMD EPYC hardware.

Packages:
    api: FastAPI application, routes, request/response models, structured logging
    backends: LLM inference backends (llama.cpp HTTP, completion, speculative)
    classifiers: Intent and complexity classification for task routing
    db: SQLite models for episodic memory, skills, and session storage
    graph: Pydantic-graph orchestration nodes (triage, plan, execute, review)
    llm_primitives: Low-level LLM call wrappers with retry and streaming
    metrics: Inference telemetry and performance counters
    models: Pydantic models for document processing pipeline
    pipeline_monitor: Real-time pipeline health and anomaly detection
    proactive_delegation: Complexity-driven task delegation to specialist agents
    prompt_builders: Role-specific prompt assembly (frontdoor, coder, architect)
    repl_environment: Sandboxed Python REPL with AST security and tool access
    services: Document processing, caching, corpus retrieval services
    session: Session persistence, checkpointing, and document caching
    tools: Callable tool implementations (code, data, file, web, canvas)
    vision: Image/video analysis with CLIP embeddings and batch processing
"""

# --- src.inference_lock compat-alias bootstrap (TD-21) ----------------------
#
# `src/inference_lock.py` is a backward-compatible alias for
# `src.runtime.inference_lock`. A naive shim body that does
# `sys.modules[__name__] = _real` from inside its own module exec is unsafe
# under concurrent first import: a concurrent importer's fast path can read
# this name's `__spec__._initializing` off the wrong (already fully loaded)
# target spec and skip CPython's own module lock, intermittently observing a
# half-swapped placeholder (`ImportError: cannot import name 'inference_lock'
# from 'src.inference_lock'`, confirmed at ~1% frequency under 24-way
# concurrency; see tests/unit/test_inference_lock_concurrent_import.py).
#
# Fix: resolve "src.inference_lock" through a MetaPathFinder, installed here
# ahead of the standard path finder, whose Loader implements
# create_module() to return the already-imported target module object
# directly. importlib then inserts that FINAL object into
# sys.modules["src.inference_lock"] the one and only time anything is ever
# inserted under that key -- there is no placeholder-then-swap window for a
# concurrent importer to observe. This also keeps
# `sys.modules["src.inference_lock"] is sys.modules["src.runtime.inference_lock"]`
# (required so `monkeypatch.setattr("src.inference_lock.X", ...)` stays
# visible to code that reads `X` from inside src.runtime.inference_lock).
#
# This registration only teaches the import system how to resolve one
# specific dotted name; it does not import the (lazily-loaded) target
# module eagerly, and it has no effect on any other import.
import sys as _sys
from importlib.abc import Loader as _Loader, MetaPathFinder as _MetaPathFinder
from importlib.util import spec_from_loader as _spec_from_loader

_INFERENCE_LOCK_ALIAS = "src.inference_lock"
_INFERENCE_LOCK_TARGET = "src.runtime.inference_lock"


class _InferenceLockAliasLoader(_Loader):
    """``create_module()`` hands back the already-imported target module."""

    def create_module(self, spec):
        import importlib

        return importlib.import_module(_INFERENCE_LOCK_TARGET)

    def exec_module(self, module):
        # Target module is already fully initialized; nothing to execute.
        pass


class _InferenceLockAliasFinder(_MetaPathFinder):
    """Resolves only "src.inference_lock"; defers everything else."""

    def find_spec(self, fullname, path, target=None):
        if fullname != _INFERENCE_LOCK_ALIAS:
            return None
        return _spec_from_loader(fullname, _InferenceLockAliasLoader())


if not any(
    isinstance(_finder, _InferenceLockAliasFinder) for _finder in _sys.meta_path
):
    _sys.meta_path.insert(0, _InferenceLockAliasFinder())
