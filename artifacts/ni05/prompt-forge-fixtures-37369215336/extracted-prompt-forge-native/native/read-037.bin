"""Deterministic verifiers for synthesized Agent-World tasks (NIB2-44 AW-1).

Each ``VerifierSpec`` compiles to a pure-Python callable that accepts
the agent's final output and returns a scalar in [0, 1]. These
verifiers are intentionally strict and cheap — they run on every
synthesized task at scoring time, and any ambiguity becomes a
difficulty-band miscalibration the autopilot can learn from.

Three verifier families are supported today:

  REGEX        ``re.fullmatch(pattern, output.strip())`` → 1.0 or 0.0
  EXACT_MATCH  case + whitespace normalised strict equality
  F1           token-level F1 against a reference set with an allowlist
               of "also correct" answers (Agent-World paper's pattern
               for reasoning tasks where many phrasings are valid)

The builder refuses to emit a verifier whose ``reference`` is empty or
whose pattern is trivially accept-all — this is the first safety line
against degenerate tasks polluting the T1 suite.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

log = logging.getLogger("autopilot.env_synth.verifier_builder")


class VerifierType(str, Enum):
    REGEX = "regex"
    EXACT_MATCH = "exact_match"
    F1 = "f1"


@dataclass
class VerifierSpec:
    """Declarative spec for a verifier. Compilation produces a callable."""

    type: VerifierType
    reference: str = ""                         # used by exact_match
    pattern: str = ""                           # used by regex
    allowlist: list[str] = field(default_factory=list)  # used by f1
    case_sensitive: bool = False
    min_tokens: int = 1                         # F1 guard: reject empty outputs

    def compile(self) -> Callable[[str], float]:
        """Return a ``(output: str) -> float in [0, 1]`` scorer."""
        t = self.type
        if t == VerifierType.REGEX:
            return _compile_regex(self)
        if t == VerifierType.EXACT_MATCH:
            return _compile_exact_match(self)
        if t == VerifierType.F1:
            return _compile_f1(self)
        raise ValueError(f"Unknown verifier type: {t!r}")


class VerifierBuilder:
    """Build + validate VerifierSpec objects. Rejects degenerate specs."""

    @staticmethod
    def build(spec: VerifierSpec) -> Callable[[str], float]:
        VerifierBuilder._validate(spec)
        return spec.compile()

    @staticmethod
    def _validate(spec: VerifierSpec) -> None:
        if spec.type == VerifierType.REGEX:
            if not spec.pattern:
                raise ValueError("regex verifier requires a non-empty pattern")
            if spec.pattern.strip() in (".*", "^.*$", "", ".+"):
                raise ValueError(
                    "regex verifier pattern is trivially accept-all; "
                    "task is not reliably verifiable"
                )
            try:
                re.compile(spec.pattern)
            except re.error as e:
                raise ValueError(f"invalid regex: {e}") from e
        elif spec.type == VerifierType.EXACT_MATCH:
            if not spec.reference.strip():
                raise ValueError("exact_match verifier requires a non-empty reference")
        elif spec.type == VerifierType.F1:
            if not spec.reference.strip() and not spec.allowlist:
                raise ValueError(
                    "f1 verifier requires a non-empty reference or allowlist entry"
                )
            if spec.min_tokens < 1:
                raise ValueError("f1 verifier min_tokens must be >= 1")


# ── compilers ──────────────────────────────────────────────────────


def _compile_regex(spec: VerifierSpec) -> Callable[[str], float]:
    flags = 0 if spec.case_sensitive else re.IGNORECASE
    pattern = re.compile(spec.pattern, flags)

    def score(output: str) -> float:
        text = (output or "").strip()
        return 1.0 if pattern.fullmatch(text) else 0.0

    return score


def _normalize(text: str, case_sensitive: bool) -> str:
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t if case_sensitive else t.lower()


def _compile_exact_match(spec: VerifierSpec) -> Callable[[str], float]:
    ref = _normalize(spec.reference, spec.case_sensitive)
    alts = [_normalize(a, spec.case_sensitive) for a in spec.allowlist]

    def score(output: str) -> float:
        candidate = _normalize(output, spec.case_sensitive)
        if candidate == ref:
            return 1.0
        return 1.0 if candidate in alts else 0.0

    return score


def _tokens(text: str, case_sensitive: bool) -> list[str]:
    norm = _normalize(text, case_sensitive)
    return [t for t in re.split(r"\W+", norm) if t]


def _token_f1(pred: list[str], ref: list[str]) -> float:
    if not pred or not ref:
        return 0.0
    pred_set = set(pred)
    ref_set = set(ref)
    overlap = pred_set & ref_set
    if not overlap:
        return 0.0
    precision = len(overlap) / len(pred_set)
    recall = len(overlap) / len(ref_set)
    return 2 * precision * recall / (precision + recall)


def _compile_f1(spec: VerifierSpec) -> Callable[[str], float]:
    cs = spec.case_sensitive
    ref_tokens = _tokens(spec.reference, cs) if spec.reference else []
    allowlist_tokens = [_tokens(a, cs) for a in spec.allowlist]

    def score(output: str) -> float:
        pred = _tokens(output, cs)
        if len(pred) < spec.min_tokens:
            return 0.0
        best = 0.0
        if ref_tokens:
            best = max(best, _token_f1(pred, ref_tokens))
        for alt in allowlist_tokens:
            if alt:
                best = max(best, _token_f1(pred, alt))
        return best

    return score
