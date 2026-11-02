"""Offline RM-6 grammar prototype. This is not a runner or a validated decoder.

Both arms emit the same mandatory ReviewDecision subset. `advisory.feedback` is
nested per the full schema. Evidence may be empty or contain any number of
kind/ref records; the arms differ only in the order of top-level fields.
"""
from __future__ import annotations
import json

ORDERS = {
    'decision-first': ('decision', 'confidence', 'blocking', 'evidence', 'advisory'),
    'evidence-first': ('evidence', 'blocking', 'confidence', 'decision', 'advisory'),
}
DECISIONS = ('approve', 'reject', 'reject_to_empty', 'request_changes',
             'request_evidence', 'abstain', 'escalate')
KINDS = ('file_span', 'test_result', 'gate_result', 'scorer_result', 'answer_span',
         'retrieval_provenance', 'trace_event', 'protocol_claim')


def lit(value: str) -> str:
    """Encode a literal UTF-8 output fragment as a GBNF literal."""
    return json.dumps(value, ensure_ascii=True)


def grammar(arm: str) -> str:
    if arm not in ORDERS:
        raise ValueError(f'unknown arm {arm!r}')
    fields = [f'{lit(json.dumps(key) + ":")} ws {key}' for key in ORDERS[arm]]
    root = 'root ::= ' + lit('{') + ' ws ' + (' ' + lit(',') + ' ws ').join(fields) + ' ' + lit('}') + ' ws'
    def choices(values):
        return ' | '.join(lit(json.dumps(value)) for value in values)
    # A deliberately restricted but nonempty schema-valid numeric and object subset.
    rules = [root,
        'decision ::= ' + choices(DECISIONS),
        'confidence ::= "0" ("." [0-9]+)? | "1" ("." "0"+)?',
        'blocking ::= ' + lit('{"tripwire":') + ' ws boolean ' + lit('}'),
        'evidence ::= ' + lit('[') + ' ws (evidence-item (ws ' + lit(',') + ' ws evidence-item)*)? ws ' + lit(']'),
        'evidence-item ::= ' + lit('{"kind":') + ' ws kind ws ' + lit(',"ref":') + ' ws string ' + lit('}'),
        'kind ::= ' + choices(KINDS),
        'advisory ::= ' + lit('{"feedback":') + ' ws string ' + lit('}'),
        'boolean ::= "true" | "false"',
        r'string ::= "\"" ([^"\\\x00-\x1f] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4}))* "\""',
        r'ws ::= [ \t\n\r]*',
    ]
    return '\n'.join(rules) + '\n'
