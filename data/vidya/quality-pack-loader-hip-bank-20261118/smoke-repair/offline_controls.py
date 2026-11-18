#!/usr/bin/env python3
"""Exercise the admission runner with synthetic custody and failure fixtures."""

import base64
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import capture
import capture_base as native
from complete import complete
from make_plan import D, ITEM, ROW, build_plan, build_spec

PLAN = build_plan()
ITEM_PLAN = PLAN['items'][0]
RUNTIME = PLAN['arms']['production']
RECIPE = PLAN['recipes']['hip_slice']
CPUS = RECIPE['cpu_affinity']
MAPPED = {
    path: {'device': pin['stat'][0], 'inode': pin['stat'][1], 'sha256': pin['sha256']}
    for path, pin in (RUNTIME['runtime_files'] | RUNTIME['rocm_files']).items()
    if path != RUNTIME['binary']
}
FIT = '0.00.404.865 I load_tensors: loading model tensors, this can take a while... (mmap = false, direct_io = false)'
MAPPED_START = FIT.replace('mmap = false', 'mmap = true')
CONTEXT = '0.00.416.598 I llama_context: constructing llama_context'
TENSOR_LINES = [
    f'0.00.405.101 D create_tensor: loading tensor {tensor}'
    for tensor in PLAN['loader_witness']['tensors']
]


def synthetic_capture(case, arm, runtime, recipe, items, requests, out, cpus, deadline, stop):
    assert arm == 'production' and items == PLAN['items']
    assert runtime == RUNTIME and recipe == RECIPE and cpus == CPUS
    assert recipe['args'][-2:] == ['--verbosity', '5']
    production = out / arm
    production.mkdir()
    lines = TENSOR_LINES if case != 'fit_probe_only' else []
    if case == 'duplicate_phase_line':
        lines = [*TENSOR_LINES, TENSOR_LINES[0]]
    native.write(production / 'server.log', ('\n'.join([
        FIT, *TENSOR_LINES, CONTEXT, MAPPED_START, *lines, CONTEXT, '',
    ])).encode())
    argv = [runtime['binary'], '--host', '127.0.0.1', '--port', str(native.PORT),
            '--threads', str(len(cpus)), *recipe['args']]
    native.write_json(production / 'server.json', {
        'image': runtime, 'recipe': recipe, 'pid': 100, 'cpus': cpus,
        'argv': argv, 'mapped_libraries': MAPPED,
    })
    native.write_json(production / 'cleanup.json', {
        'pid': 100, 'dead': True, 'port_closed': True, 'kfd_entry_absent': case != 'cleanup_failure',
    })

    rows = []
    for item in items:
        name = item['id']
        if case == 'missing_item' and name == 'architect-general-hip-prose':
            continue
        request = requests[name]
        target = item['validator']['expected']
        content = native.canonical(target).decode() if isinstance(target, dict) else target
        if case == 'semantic_refusal' and name == ITEM:
            content = '{"route":"amber","enabled":1,"replicas":3}'
        if case == 'nonfixture_semantic_refusal' and name == 'architect-general-hip-code':
            content = 'unrelated answer'
        response = {
            'choices': [{'finish_reason': 'stop', 'message': {'content': content}}],
            'usage': {'completion_tokens': 3, 'prompt_tokens': 17,
                      'prompt_tokens_details': {'cached_tokens': 0}},
            '__verbose': {'tokens': [8, 9, 10], 'tokens_predicted': 3, 'tokens_evaluated': 17,
                          'truncated': False, 'generation_settings': {'speculative.types': 'none,none'},
                          'timings': {'predicted_n': 3, 'prompt_n': 17, 'cache_n': 0}},
        }
        if case == 'length_refusal' and name == 'architect-general-hip-prose':
            n = item['request_body']['max_tokens']
            response['choices'][0]['finish_reason'] = 'length'
            response['usage']['completion_tokens'] = n
            response['__verbose'].update(tokens=list(range(n)), tokens_predicted=n)
            response['__verbose']['timings']['predicted_n'] = n
        if case == 'no_spec_refusal' and name == ITEM:
            response['__verbose']['timings']['draft_n'] = 1
        raw = native.canonical(response)
        if case == 'nonfixture_request_drift' and name == 'architect-general-hip-prose':
            request += b' '
        native.write(production / f'{name}.request.json', request)
        native.write(production / f'{name}.response.json', raw)
        if case == 'transport_failure':
            raise RuntimeError('synthetic partial transport failure')
        samples = [
            {'t_ns': t, 'pid': 100, 'kfd_pids': [100], 'gpu_id': recipe['gpu_id'],
             'process_vram_bytes': 102400000, 'device_vram_bytes': 204800000, 'mapped_libraries': MAPPED}
            for t in (12, 19)
        ]
        if case == 'wrong_hip_pid' and name == ITEM:
            samples[1]['pid'] = 101
        evidence_sha = native.write_json(production / f'{name}.hip-residency.json', {
            'request_sent_ns': 10, 'response_end_ns': 20, 'samples': samples, 'errors': [],
        })
        rows.append({
            'id': name, 'request_sha256': native.sha(request), 'response_b64': base64.b64encode(raw).decode(),
            'response_sha256': native.sha(b'changed' if case == 'raw_tamper' and name == ITEM else raw),
            'hip_residency_sha256': evidence_sha,
        })
    return rows


def exercise(case):
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        for filename in ('plan.json', 'SOURCE.sha256'):
            (root / filename).write_bytes((D / filename).read_bytes())
        (root / f'{ROW}.grant').write_bytes(b'synthetic fixture grant')
        result = root / 'out/RESULT.json'
        env = {'FILLER_ID': ROW, 'FILLER_NEEDGPU': '1', 'FILLER_GPU_FENCE': '0',
               'FILLER_GRANTS_DIR': temporary, 'FILLER_DEADLINE': '2099-01-01T00:00:00Z',
               'FILLER_STOPFILE': str(root / 'STOP')}
        def simulate(*args, **kwargs):
            return synthetic_capture(case, *args, **kwargs)

        with patch.object(capture, 'D', root), patch.object(capture, 'preflight', return_value=native.read_requests(PLAN)), \
                patch.object(native, 'capture_arm', side_effect=simulate) as arm, \
                patch.object(os, 'sched_getaffinity', return_value=set(CPUS)), patch.dict(os.environ, env):
            rc = capture.run(PLAN, native.file_sha(root / 'plan.json'), result, False, 8)
        arm.assert_called_once()
        record = json.loads(result.read_bytes())
        assert record['candidate_collected'] is False and not complete(result, True)
        assert rc == (0 if case == 'pass' else 1)
        assert complete(result, False) is (case == 'pass')
        if case == 'pass':
            assert record['loader_log_evidence']['native_load_phase']['start']['line_number'] == 5
            bank = result.parent / 'native/production-fixture-capture.json'
            bank.write_bytes(bank.read_bytes() + b'\n')
            assert not complete(result, False)
        elif case in ('semantic_refusal', 'nonfixture_semantic_refusal', 'length_refusal'):
            assert record['status'] == 'inadmissible_bank' and len(record['checks']) == 4
            assert any(check['semantic_matches'] is False or check['finish'] != check['expected_finish']
                       for check in record['checks'].values())
        else:
            assert record['status'] == 'incomplete' and record['error']['message']
        print(f'{case}: PASS')


if __name__ == '__main__':
    assert PLAN == json.loads((D / 'plan.json').read_bytes())
    assert build_spec() == json.loads((D / 'row.spec.json').read_bytes())
    source = json.loads((D / 'hip-plan.original.json').read_bytes())
    original = source['recipes']['hip_slice']
    old_args = list(original['args'])
    old_args[old_args.index('--chat-template-file') + 1] = str(D / 'chat-template.jinja')
    assert RECIPE == {**original, 'args': old_args + ['--verbosity', '5']}
    assert PLAN['pack_shape']['recipe_sha256'] == native.sha(native.canonical(RECIPE))
    assert PLAN['smoke_items'] == source['smoke_items']
    assert ITEM_PLAN['request_body'] not in [row['request_body'] for row in source['items']]
    retained = {row['id']: row['request_body'] for row in source['items']}
    for item in PLAN['items'][1:]:
        assert native.canonical(item['request_body']) == native.canonical(retained[item['id']])
    assert set(PLAN['arms']) == {'production'}
    capture.preflight(PLAN)
    print('deterministic plan/spec, effective one-recipe shape pin, three unchanged requests and sole production arm: PASS')
    for case in ('pass', 'semantic_refusal', 'nonfixture_semantic_refusal', 'length_refusal',
                 'no_spec_refusal', 'wrong_hip_pid', 'fit_probe_only', 'duplicate_phase_line',
                 'cleanup_failure', 'raw_tamper', 'nonfixture_request_drift', 'missing_item',
                 'transport_failure'):
        exercise(case)
