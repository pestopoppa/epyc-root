"""Typed decision plane (TD-1 core): one-pass choice/score/noul decisions.

This package turns a catalogue of typed ``Question`` objects into typed
``Decision`` records through ONE local-model call over the existing
``LLMPrimitives.llm_call`` seam. It exists to replace prose-and-parse
pseudo-decisions with an explicit contract: a question either resolves to a
typed value with its probability distribution and a local confidence
statistic, or it yields a typed ``ParseFailure`` — never a silent default.

Contents:
    * ``types`` — frozen ``Question`` / ``Decision`` / ``ParseFailure`` /
      ``DecisionResult`` values.
    * ``confidence`` — adapter-verified local confidence formulas from
      intake-1473 (NOT calibrated confidence; see the module docstring).
    * ``schema`` — Draft 2020-12 response-schema and GBNF builders.
    * ``runner`` — ``run_typed_decisions`` (mode="json"; mode="native"
      dispatches to ``native``).
    * ``native`` — ``run_typed_decisions_native`` (TD-1b): one constrained
      generation, one token per question, candidate-probability slicing. The
      candidates are bound to exact token ids through a tokenizer seam
      (``/tokenize`` by default); multi-token or un-tokenizable candidates
      fall back to JSON mode as typed failures instead of being guessed.

Scope note: TD-1 ships the core only. Nothing in this package is wired into
a live route; TD-5 performs that wiring, gated by the default-off
``typed_decisions`` feature flag in ``src/features.py``.
"""

from __future__ import annotations

from src.typed_decisions.native import run_typed_decisions_native
from src.typed_decisions.runner import run_typed_decisions
from src.typed_decisions.types import (
    Decision,
    DecisionResult,
    ParseFailure,
    Question,
    QuestionKind,
)

__all__ = [
    "Decision",
    "DecisionResult",
    "ParseFailure",
    "Question",
    "QuestionKind",
    "run_typed_decisions",
    "run_typed_decisions_native",
]
