"""Typed run-failure outcomes for the DTAP disposable runner.

The runner emits verdicts (task_success / attack_success) for completed runs and
a *typed failure* for runs that could not complete. The failure type is drawn
from exactly this set (TU-DTAP-1 contract):

    model|parser|tool|endpoint|harness|judge|infrastructure|overflow

Failure taxonomy:
  * model          - endpoint responded and parsed, but the model output is
                     unusable for the agent loop (empty completion, refusal, or
                     no final answer within max_turns).
  * parser         - endpoint response could not be parsed into an agent turn
                     (malformed JSON / tool-call arguments) after retries.
  * tool           - a tool call failed to execute.
  * endpoint       - transport/HTTP/API failure talking to the endpoint.
  * harness        - internal harness bug (programmer error).
  * judge          - the judge module failed to load or raised during eval.
  * infrastructure - environment/state-store/fixture failure (stub side).
  * overflow       - context-window overflow (finish_reason=length or the
                     endpoint reported a context-length error).
"""
from __future__ import annotations

from enum import Enum


class OutcomeType(str, Enum):
    MODEL = "model"
    PARSER = "parser"
    TOOL = "tool"
    ENDPOINT = "endpoint"
    HARNESS = "harness"
    JUDGE = "judge"
    INFRASTRUCTURE = "infrastructure"
    OVERFLOW = "overflow"


ALL_OUTCOME_TYPES = frozenset(t.value for t in OutcomeType)


class RunFailure(Exception):
    """Base class for typed run failures. `type_` is the canonical OutcomeType."""

    type_ = OutcomeType.HARNESS

    def __init__(self, message: str, *, detail: dict | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail or {}

    def to_outcome(self) -> dict:
        return {"type": self.type_.value, "message": self.message, "detail": self.detail}


class ModelFailure(RunFailure):
    type_ = OutcomeType.MODEL


class ParseFailure(RunFailure):
    type_ = OutcomeType.PARSER


class ToolFailure(RunFailure):
    type_ = OutcomeType.TOOL


class EndpointFailure(RunFailure):
    type_ = OutcomeType.ENDPOINT


class HarnessFailure(RunFailure):
    type_ = OutcomeType.HARNESS


class JudgeFailure(RunFailure):
    type_ = OutcomeType.JUDGE


class InfrastructureFailure(RunFailure):
    type_ = OutcomeType.INFRASTRUCTURE


class OverflowFailure(RunFailure):
    type_ = OutcomeType.OVERFLOW


def classify(exc: BaseException) -> OutcomeType:
    """Map any exception to its canonical typed outcome.

    RunFailure subclasses carry their type; unknown exceptions are harness
    failures (they indicate a harness bug, which is what a classification
    fallthrough means).
    """
    if isinstance(exc, RunFailure):
        return exc.type_
    return OutcomeType.HARNESS
