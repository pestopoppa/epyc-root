"""Isolated candidate composition of existing exploration implementations.

Reuse the bounded reader/renderers and the native actor C-family parser without
copying sources or mutating either imported module. Both candidate MCP adapters
consume this same object. This is not installation into the production REPL.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
from types import FunctionType

DEFAULT_RESEARCH_ROOT = Path('/mnt/raid0/llm/epyc-inference-research')


def load_actor_parser(research_root):
    """Load the declared actor implementation, refusing a cached different tree."""
    checkout = Path(research_root).resolve(strict=True)
    source = checkout / 'scripts/kernel_rnd/autokernel/loop/actor_tools_mcp.py'
    if not source.is_file():
        raise ValueError('research root must contain the native actor tools module')
    sys.path.insert(0, str(checkout / 'scripts/kernel_rnd'))
    actor = importlib.import_module('autokernel.loop.actor_tools_mcp')
    if Path(actor.__file__).resolve() != source:
        raise RuntimeError('actor parser did not load from the declared research checkout')
    return actor._outline_c


def _bind(function, overrides):
    """Reuse a renderer's code with isolated helper bindings, preserving defaults."""
    namespace = dict(function.__globals__)
    namespace.update(overrides)
    bound = FunctionType(function.__code__, namespace, function.__name__,
                         function.__defaults__, function.__closure__)
    bound.__kwdefaults__ = function.__kwdefaults__
    bound.__annotations__ = function.__annotations__
    return bound


class CandidateCore:
    """Shared candidate API; unmodified operations delegate to the base core."""

    def __init__(self, base, parser):
        self._base = base

        def read_text(*args, **kwargs):
            text, real = base._read_text(*args, **kwargs)
            if '\x00' in text:
                raise base.ExplorationError('file looks binary; refused')
            return text, real

        def outline_c(text):
            return parser(text.splitlines())

        overrides = {'_read_text': read_text, '_outline_c_heuristic': outline_c}
        # Rebinding globals avoids a second read and leaves the imported core intact.
        for name in ('read_range', 'read_file_page', 'grep_file', 'outline_file'):
            setattr(self, name, _bind(getattr(base, name), overrides))
        self._read_text = read_text

    def __getattr__(self, name):
        return getattr(self._base, name)


def candidate_core(base, *, research_root=DEFAULT_RESEARCH_ROOT):
    if isinstance(base, CandidateCore):
        return base
    return CandidateCore(base, load_actor_parser(research_root))
