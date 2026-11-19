#!/usr/bin/env python3
"""Exercise packet checks without starting a server."""

import argparse
import base64
from copy import deepcopy
from http.client import HTTPException
import json
from pathlib import Path
import os
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import capture
from complete import complete
from cpu_native import D, canonical, sha
from make_plan import build_plan, build_spec


PLAN = build_plan()
ITEM, = PLAN['items']
NAME = ITEM['id']
RESPONSE = {
    'choices': [{'finish_reason': 'stop', 'message': {'content': '{"loader_probe":"amber","count":2}'}}],
    'usage': {'completion_tokens': 3, 'prompt_tokens_details': {'cached_tokens': 0}},
    '__verbose': {
        'tokens': [8, 9, 10], 'tokens_predicted': 3, 'truncated': False,
        'generation_settings': {'speculative.types': 'none,none'},
        'timings': {'predicted_n': 3, 'cache_n': 0},
    },
}
FIT_START = '0.00.404.865 I load_tensors: loading model tensors, this can take a while... (mmap = false, direct_io = false)'
MAPPED_START = FIT_START.replace('mmap = false', 'mmap = true')
CONTEXT_START = '0.00.416.598 I llama_context: constructing llama_context'
TENSOR_LINES = ['0.00.405.101 D create_tensor: loading tensor ' + name
                for name in PLAN['loader_witness']['tensors']]


def production_replay(target):
    evidence = capture.loader_log_evidence(target / 'server.log', PLAN, 'production')
    assert evidence['log_sha256'] == '56482cf0c5774db12f60ef62089ca5ce2aeed58ac7c8f2dacd2159043971bc0e'
    assert evidence['native_load_phase']['start']['line_number'] == 3058
    assert evidence['native_load_phase']['context_start']['line_number'] == 5513
    assert list(evidence['native_line_numbers'].values()) == [3115, 3119]
    wire = (target / f'{NAME}.request.json').read_bytes()
    raw = (target / f'{NAME}.response.json').read_bytes()
    record = {'id': NAME, 'request_sha256': sha(wire), 'response_sha256': sha(raw),
              'response_b64': base64.b64encode(raw).decode()}
    check = capture.check_response(ITEM, record, target, PLAN['recipes']['diagnostic']['endpoint'])
    assert check['finish'] == 'stop' and check['completion_tokens'] == 14
    assert check['semantic_matches'] is False
    print('archived production replay: mapped load and native response PASS; strict JSON semantics REFUSED')


def synthetic_run(case):
    calls = []
    with TemporaryDirectory() as folder:
        root = Path(folder)
        (root / 'plan.json').write_bytes((D / 'plan.json').read_bytes())
        (root / 'SOURCE.sha256').write_bytes((D / 'SOURCE.sha256').read_bytes())
        grant = root / 'fixture.grant'
        grant.write_bytes(b'fixture grant - no execution')
        env = {'FILLER_DRYRUN': '0', 'FILLER_ID': 'fixture', 'FILLER_GRANTS_DIR': folder,
               'FILLER_DEADLINE': '2099-01-01T00:00:00Z', 'FILLER_STOPFILE': str(root / 'STOP')}

        def simulate(arm, runtime, recipe, items, out, cpus, deadline, stop):
            calls.append(arm)
            if arm == 'candidate':
                prior = (out / 'banked-capture.json').read_bytes()
                assert sha(prior) == (out / 'banked-capture.sha256').read_text().strip()
                if case == 'http_failure':
                    raise HTTPException('offline synthetic failure')
            assert len(items) == 1 and len(cpus) == 24
            arm_dir = out / arm
            arm_dir.mkdir()
            wire = canonical(ITEM['request_body'])
            response = deepcopy(RESPONSE)
            if case == 'semantic_refusal' and arm == 'candidate':
                response['choices'][0]['message']['content'] = '{"loader_probe":"wrong","count":2}'
            raw = canonical(response)
            mapped_lines = list(TENSOR_LINES)
            if case == 'missing_loader_log':
                mapped_lines = []
            elif case == 'duplicate_in_load_phase':
                mapped_lines.append(TENSOR_LINES[0])
            elif case == 'ambiguous_load_phase':
                mapped_lines.extend([CONTEXT_START, MAPPED_START, *TENSOR_LINES])
            elif case == 'missing_context_boundary':
                mapped_lines.extend([FIT_START, *TENSOR_LINES])
            lines = '\n'.join([FIT_START, *TENSOR_LINES, CONTEXT_START,
                               MAPPED_START, *mapped_lines, CONTEXT_START, ''])
            for filename, content in {
                'server.log': lines.encode(), 'server.json': b'{}',
                'cleanup.json': b'{"dead":true,"port_closed":true}',
                f'{NAME}.request.json': wire, f'{NAME}.response.json': raw,
            }.items():
                (arm_dir / filename).write_bytes(content)
            return [{'id': NAME, 'request_sha256': sha(wire),
                     'response_sha256': sha(raw), 'response_b64': base64.b64encode(raw).decode()}]

        with patch.object(capture, 'D', root), patch.object(capture, 'preflight'), \
             patch.object(capture.native, 'capture_arm', simulate), \
             patch.object(capture.signal, 'signal'), patch.object(sys, 'argv', ['capture.py']), \
             patch.object(os, 'sched_getaffinity', return_value=set(range(24))), patch.dict(os.environ, env):
            rc = capture.run()
        result = json.loads((root / 'out/RESULT.json').read_bytes())
        assert result['broad_pack_input'] is False and result['quality_transfer_authorized'] is False
        phase_errors = {
            'missing_loader_log': 'found 0',
            'duplicate_in_load_phase': 'found 2',
            'ambiguous_load_phase': 'requires one native mmap=true load phase, found 2',
            'missing_context_boundary': 'lacks an unambiguous context boundary',
        }
        expected_arms = ['production'] if case in phase_errors else ['production', 'candidate']
        assert calls == expected_arms
        if case == 'pass':
            assert rc == 0 and complete(result, False) and all(result['comparison'].values())
            assert not complete(result, True)
        else:
            assert rc == 1 and not complete(result, False)
            if case == 'semantic_refusal':
                assert result['status'] == 'loader_exercised_response_refused'
                assert len(result['captures']) == 2
            elif case in phase_errors:
                assert result['error']['phase'] == 'production' and not result['captures']
                assert phase_errors[case] in result['error']['message']
            else:
                assert result['error']['phase'] == 'candidate' and set(result['captures']) == {'production'}
        print(f'{case}: PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--original-production', type=Path, help='read-only original native production directory')
    args = parser.parse_args()
    assert PLAN == json.loads((D / 'plan.json').read_bytes())
    assert build_spec() == json.loads((D / 'row.spec.json').read_bytes())
    capture.preflight(PLAN)
    print('deterministic plan/spec, model stat and exact runtime receipt preflight: PASS')
    if args.original_production is not None:
        production_replay(args.original_production)
    for test in ('pass', 'semantic_refusal', 'missing_loader_log', 'duplicate_in_load_phase',
                 'ambiguous_load_phase', 'missing_context_boundary', 'http_failure'):
        synthetic_run(test)
