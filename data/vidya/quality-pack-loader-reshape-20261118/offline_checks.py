#!/usr/bin/env python3
"""Exercise packet checks without starting a server."""

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
            lines = (
                '' if case == 'missing_loader_log' else
                '\n'.join('create_tensor: loading tensor ' + name
                          for name in PLAN['loader_witness']['tensors']) + '\n'
            )
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
        expected_arms = ['production'] if case == 'missing_loader_log' else ['production', 'candidate']
        assert calls == expected_arms
        if case == 'pass':
            assert rc == 0 and complete(result, False) and all(result['comparison'].values())
            assert not complete(result, True)
        else:
            assert rc == 1 and not complete(result, False)
            if case == 'semantic_refusal':
                assert result['status'] == 'loader_exercised_response_refused'
                assert len(result['captures']) == 2
            elif case == 'missing_loader_log':
                assert result['error']['phase'] == 'production' and not result['captures']
            else:
                assert result['error']['phase'] == 'candidate' and set(result['captures']) == {'production'}
        print(f'{case}: PASS')


if __name__ == '__main__':
    assert PLAN == json.loads((D / 'plan.json').read_bytes())
    assert build_spec() == json.loads((D / 'row.spec.json').read_bytes())
    capture.preflight(PLAN)
    print('deterministic plan/spec, model stat and exact runtime receipt preflight: PASS')
    for test in ('pass', 'semantic_refusal', 'missing_loader_log', 'http_failure'):
        synthetic_run(test)
