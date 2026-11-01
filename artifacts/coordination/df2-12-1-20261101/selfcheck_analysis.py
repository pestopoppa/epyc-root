#!/usr/bin/env python3
"""Synthetic science-decision check; never a model or production qualification."""
from __future__ import annotations

import json
import pathlib
import shutil

import df2_parity as dp


ROOT = pathlib.Path(__file__).resolve().parent / 'SYNTHETIC-DECISION'
SHAPE = 'frontdoor_mtp'
C = 2
PHASES = ('baseline-np1', 'repeat-np1', 'baseline-off-np1', 'repeat-off-np1',
          'logits-off-np1', 'logits-repeat-off-np1', 'joint-np4', 'joint-repeat-np4',
          'off-np4', 'off-repeat-np4', 'logits-off-np4', 'logits-repeat-off-np4')


def record(key, phase):
    divergent = phase in ('joint-np4', 'joint-repeat-np4') and key == 'salt-A'
    tokens = [1, 9] if divergent else [1, 2]
    probs = [{'top_logprobs': [{'id': 2, 'logprob': -0.1}, {'id': 3, 'logprob': -2.1}]}
             for _ in tokens] if phase.startswith('logits-') else []
    return {'id': key, 'status': 'ok', 'tokens': tokens, 'raw': {'completion_probabilities': probs},
            'started': 1.0, 'ended': 2.0, 'slot_observed': 0}


def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    frozen = dp.make_manifest()
    for phase in PHASES:
        folder = ROOT / SHAPE / f'{phase}-c{C}' / 'responses'
        folder.mkdir(parents=True)
        ids = [key for key, _ in dp.phase_requests(frozen, phase, C)]
        np = 1 if phase in dp.NP1_PHASES else 4
        spec = 'off' if phase in dp.OFF_PHASES else 'on'
        model = '/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
        argv = {'shape': SHAPE, 'backend': 'cpu', 'np': np, 'spec': spec,
                'n_ctx_total': 262144 if np == 4 else 65536, 'n_ctx_per_slot': 65536,
                'scratch_argv': ['/synthetic/llama-server', '-m', model, '-np', str(np),
                                 '-c', str(262144 if np == 4 else 65536), '-t', '96',
                                 '--spec-type', 'none' if spec == 'off' else 'draft-mtp'] +
                                ([] if spec == 'off' else ['--spec-draft-n-max', '4'])}
        dp.write_json(folder.parent / 'ARGV.json', argv)
        dp.write_json(folder.parent / 'ACTUAL-LAUNCH.json', {'argv': argv['scratch_argv'],
                      'claimed_cpus': '0-95', 'env_keys': {'HIP_VISIBLE_DEVICES': '-1'}})
        (folder.parent / 'server.log').write_text('synthetic trace only\n')
        dp.write_json(folder.parent / 'SERVER-DRAIN.json', {'own_pid_dead': True,
                      'server_pgid': 100, 'launcher_pgid': 100,
                      'n_ctx_total_values': [argv['n_ctx_total']],
                      'server_log_sha256': dp.sha((folder.parent / 'server.log').read_bytes())})
        source_sha = dp.sha((folder.parent / 'server.log').read_bytes())
        counts = {key: 1 for key in ids}
        fps = {key: dp.prompt_fp([101 + i]) for i, key in enumerate(ids)}
        dp.write_json(folder / 'REQUEST-PLAN.json', {'manifest_sha256': dp.sha(dp.canonical(frozen) + b'\n'),
                      'shape': SHAPE, 'phase': phase, 'concurrency': C, 'expected_requests': ids,
                      'server_identity': dp.sha((folder.parent / 'ARGV.json').read_bytes()),
                      'rendered_token_counts': counts, 'rendered_prompt_fingerprints': fps,
                      'observed_props': {'model_path': model, 'total_slots': np, 'n_ctx_per_slot': 65536},
                      'observed_slots': [{'id': i, 'n_ctx': 65536} for i in range(np)]})
        for key in ids:
            dp.write_json(folder / (key + '.response.json'), record(key, phase))
        dp.write_json(folder / 'NATIVE-TRACE.json', {'complete': False, 'round_markers': [],
                      'batch_markers': [], 'malformed': [], 'source_sha256': source_sha})
        if phase in ('joint-np4', 'joint-repeat-np4', 'off-np4', 'off-repeat-np4',
                     'logits-off-np4', 'logits-repeat-off-np4'):
            dp.write_json(folder / 'NATIVE-TRACE.json', {'complete': spec == 'on',
                          'source_sha256': source_sha, 'malformed': [],
                          'round_markers': ([{'batch': 1, 'slot': 0, 'draft_n': 4,
                                              'accepted': 2, 'rollback': 2}] if spec == 'on' else []),
                          'batch_markers': [{'batch': 1, 'slot': i, 'task': 10+i, 'phase': 'prompt',
                                             'prompt_len': 1, 'prompt_fp': fps[key], 'slot_tokens': 4}
                                            for i, key in enumerate(ids)]})
    dp.write_json(ROOT / SHAPE / 'IMAGE-PREFLIGHT.json', {'pass': True, 'synthetic': True,
                  'binary': '/synthetic/llama-server', 'artifacts': {}})
    dp.write_json(ROOT / SHAPE / 'ROLLBACK-TEST.json', {'pass': True, 'synthetic': True,
                  'identity_sha256': dp.sha((ROOT / SHAPE / 'IMAGE-PREFLIGHT.json').read_bytes())})
    dp.analyze(type('Args', (), {'root': str(ROOT), 'out': str(ROOT / 'ANALYSIS.json')})())
    result = json.loads((ROOT / 'ANALYSIS.json').read_text())
    assert result['verdict'] == 'DEFECT_TRIGGER', result['verdict']
    assert len(result['supported_defects']) == 1, result['supported_defects']
    assert result['supported_defects'][0]['id'] == 'salt-A'
    assert result['denominator_all_requests'] == 304
    joint_trace = ROOT / SHAPE / f'joint-np4-c{C}' / 'responses' / 'NATIVE-TRACE.json'
    altered = json.loads(joint_trace.read_text())
    for marker in altered['batch_markers']:
        marker['phase'] = 'decode'
    dp.write_json(joint_trace, altered)
    dp.analyze(type('Args', (), {'root': str(ROOT), 'out': str(ROOT / 'DECODE-ONLY-ANALYSIS.json')})())
    decode_only = json.loads((ROOT / 'DECODE-ONLY-ANALYSIS.json').read_text())
    assert decode_only['verdict'] == 'INCONCLUSIVE'
    assert not decode_only['co_prefill_observed'][str((SHAPE, 'joint-np4', C))]
    print('synthetic defect branch and decode-only refusal PASS; denominator 304; no model evidence')


if __name__ == '__main__':
    main()
