#!/usr/bin/env python3
"""CJ7 mechanically generated source-edit fixtures, not a fleet quality gate.

Three designs share one four-mutation real-source fixture. Exact comparison
uses the pinned Python AST formatter; descriptive/lazy execution reuses the
canonical code_execution scorer with held-out assertions. No code runs here.
The small single-function mix does not claim representative software engineering.
"""
from __future__ import annotations
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path

SOURCE_COMMIT = '3caaf22fa853daab5c5ae055ca46b67809e2c938'
SOURCE_PATH = 'scripts/benchmark/beam_scoring.py'
SOURCE_FUNCTION = 'def _mean(values: list[float]) -> float:\n    return sum(values) / len(values)\n'
MUTATIONS = (
    ('operator_swap', 'sum(values) * len(values)', 'Replace multiplication by division in the return expression.', 'Fix the mean calculation.'),
    ('off_by_one', 'sum(values) / (len(values) + 1)', 'Remove the added one from the denominator so it uses len(values).', 'Fix the denominator.'),
    ('removed_denominator', 'sum(values)', 'Divide the sum of the values by len(values) before returning.', 'Return the average.'),
    ('wrong_aggregation', 'min(values) / len(values)', 'Replace min(values) with sum(values), retaining division by len(values).', 'Compute the arithmetic mean.'),
)
HIDDEN_TEST = '''def check(candidate):
    assert candidate([2.0, 4.0]) == 3.0
    assert candidate([-3.0, 0.0, 6.0]) == 1.0
    assert candidate([7.0]) == 7.0
    assert candidate([0.0, 0.0]) == 0.0
'''


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def formatted(source: str) -> str:
    """Pinned formatter policy: Python AST unparse, ignores comments/whitespace."""
    return ast.unparse(ast.parse(source)) + '\n'


def exact_formatted_match(response: str, expected: str) -> bool:
    try:
        return formatted(response) == formatted(expected)
    except (SyntaxError, ValueError, TypeError):
        return False


def fixture() -> dict:
    inverse = [];anti = [];execution = []
    for mutation, expr, descriptive, lazy in MUTATIONS:
        before = SOURCE_FUNCTION.replace('sum(values) / len(values)', expr)
        delta = ''.join(difflib.unified_diff(SOURCE_FUNCTION.splitlines(True), before.splitlines(True), fromfile='old.py', tofile='new.py'))
        shared = {'fixture_id': mutation, 'original_sha256': digest(SOURCE_FUNCTION.encode()),
                  'mutated_sha256': digest(before.encode()), 'mutation': mutation}
        inverse.append(dict(shared, id=mutation+'-inverse', prompt=descriptive+'\nReturn the complete corrected Python function only.\n'+before, expected=SOURCE_FUNCTION))
        anti.append(dict(shared, id=mutation+'-antiapply', prompt='Given this new code and unified diff, recover the old Python code. Return code only.\nNEW CODE:\n'+before+'\nDIFF:\n'+delta, expected=SOURCE_FUNCTION, diff=delta))
        for kind, instruction in [('descriptive', descriptive), ('lazy', lazy)]:
            execution.append(dict(shared, id=mutation+'-'+kind, pair_id=mutation,
                                  instruction_kind=kind, prompt=instruction+'\nReturn the complete corrected Python function only.\n'+before,
                                  expected=SOURCE_FUNCTION, scoring_method='code_execution',
                                  scoring_config={'test': HIDDEN_TEST, 'entry_point': '_mean', 'timeout': 2}))
    return {
        'schema': 'epyc.cj7_mechanical_fixture.v1',
        'source': {'commit': SOURCE_COMMIT, 'path': SOURCE_PATH, 'function': '_mean',
                   'snippet_sha256': digest(SOURCE_FUNCTION.encode())},
        'design_sources': ['https://huggingface.co/datasets/JetBrains-Research/diff-xyz',
                           'https://github.com/nuprl/CanItEdit'],
        'inverse_mutation': inverse, 'anti_apply': anti,
        'suites': {'cj7_descriptive_lazy_candidate': execution},
        'preregistered': {'expected': 'known inverse source', 'formatter': 'ast.unparse, comments ignored',
                          'hidden_test_sha256': digest(HIDDEN_TEST.encode()),
                          'inverse_denominator': 4, 'anti_apply_denominator': 4,
                          'execution_denominator': 8, 'paired_instruction_ids': [x[0] for x in MUTATIONS],
                          'no_reference_or_hidden_tests_in_prompt': True,
                          'execution_oracle': 'existing answer_scoring code_execution -> code_exec_scorer.score_functional',
                          'known_limited_mix': 'four mutations of one arithmetic helper, no removed-guard/boolean-flip coverage',
                          'meaning': 'mechanical edit application/probe, not software engineering or model quality',
                          'routing_or_adoption': False},
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args(argv)
    a.out.write_text(json.dumps(fixture(),sort_keys=True,indent=2)+'\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
