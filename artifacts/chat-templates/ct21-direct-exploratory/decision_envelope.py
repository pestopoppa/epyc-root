"""CT21 diagnostic interface v1; original native verdicts are immutable."""
from dataclasses import dataclass
from typing import Callable, Any
import re

@dataclass(frozen=True)
class Decision:
    kind: str
    payload: str | None = None


def parse_decision(text: str) -> Decision:
    # A single complete decision line is the architect's contract; never infer
    # an answer from a delegation brief, extra prose, or an approval token.
    if not isinstance(text, str):
        return Decision('malformed')
    line = text.strip()
    if not line or '\n' in line or '\r' in line:
        return Decision('malformed')
    if line.startswith('D|'):
        payload = line[2:].strip()
        if not payload:
            return Decision('malformed')
        if payload.casefold() == 'approved':
            return Decision('approved')
        return Decision('direct', payload)
    if re.fullmatch(r'I\|brief:.+\|to:[A-Za-z0-9_-]+', line):
        return Decision('delegation')
    return Decision('malformed')


def score_direct(text: str, expected: str, method: str, config: dict,
                 native_score: Callable[..., Any], parse_error: type[Exception], *, parse_errors_enabled: bool) -> dict:
    decision = parse_decision(text)
    if decision.kind != 'direct':
        return {'status': 'unobservable', 'reason': decision.kind, 'correct': None}
    if not parse_errors_enabled:
        raise ValueError("native parse failures must be observable")
    try:
        result = native_score(decision.payload, expected, method, config)
    except parse_error:
        return {'status': 'unobservable', 'reason': 'native_parse_failure', 'correct': None}
    return {'status': 'observable', 'reason': None, 'correct': bool(result)}


def diagnostic_prefix(text: str, prefix: str) -> dict:
    decision = parse_decision(text)
    if decision.kind != 'direct':
        return {'status': 'unobservable', 'reason': decision.kind, 'matches': None}
    return {'status': 'observable', 'reason': None,
            'matches': decision.payload.lstrip().startswith(prefix)}


def complete_metric(records: list[dict]) -> dict:
    """Refuse aggregate accuracy if any required answer is unobservable."""
    if not records:
        return {'status': 'refused', 'reason': 'empty', 'correct': None, 'n': 0}
    if any(r.get('status') != 'observable' or type(r.get('correct')) is not bool for r in records):
        return {'status': 'refused', 'reason': 'unobservable', 'correct': None, 'n': len(records)}
    return {'status': 'complete', 'reason': None, 'correct': sum(r['correct'] for r in records), 'n': len(records)}
