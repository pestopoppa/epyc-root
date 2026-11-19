import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from native_protocol import configs, negative_control, assess, execute, CELLS, source_bindings, verify_inputs
from test_invocation_trace_v3 import B, D, E


def base():
    return {'server_args': ['--flash-attn', 'on', '-ctk', 'q8_0', '-ctv', 'q8_0',
                            '--spec-type', 'draft-mtp', '--spec-draft-n-max', '1'],
            'requests': [{'n_predict': 128}], 'layer_manifest': 'unused',
            'row_id': 'g3-test', 'protocol_sources': source_bindings(),
            'environment_policy': {'sclk_mhz': [1000, 1700], 'mclk_mhz': [1500, 1700], 'max_gap_s': 2}}


def capture():
    return {'status': 'complete', 'process_group_drained': True,
            'requests': [{'tokens_predicted': 8}], 'request_windows': [[1, 2]],
            'residency': [{'status': 'PASS'}]}


def trace():
    return D.replace('invocation=12 correlation=host_scope', 'invocation=0 correlation=unknown') + ' time_ns=1500000000'


def records():
    r = {f'{kv}-mtp-off': {'rc': 0, 'control': {'status': 'PASS'}} for kv in ('q8_0', 'q4_0')}
    for kv, width in CELLS:
        result = capture()
        result['timed_analysis'] = {
            'status': 'SCOPED_DISPATCH_OBSERVED',
            'coverage': {'expected_dispatches': 1, 'bounded_dispatches': 1, 'unknown_dispatches': 0, 'complete': True},
            'trace': {'candidates': [{'draft_length': width, 'dispatches': [{'k_type': kv, 'v_type': kv}]}]},
            'observed': [{'kernel': 100}]}
        r[f'{kv}-d{width}'] = {'rc': 0, 'request_count': 1, 'result': result}
    return r


class NativeProtocolTest(unittest.TestCase):
    def test_source_drift_and_missing_environment_policy_refused_before_process(self):
        for defect in ('source', 'policy', 'row'):
            b = base()
            if defect == 'source': b['protocol_sources']['diagnostic_runner.py'] = '0'*64
            if defect == 'policy': b['environment_policy'] = {}
            if defect == 'row': b['row_id'] = '../foreign'
            with self.assertRaises((ValueError, KeyError)):
                verify_inputs(b)

    def test_every_process_requires_independent_environment_gate(self):
        r = records()
        from test_environment_gates import samples, POLICY, DEVICE
        for cell in r.values():
            cell.update(row_id='g3-test', environment_policy=POLICY)
            cell.setdefault('result', {}).update(
                environment_assessment={'status': 'PASS'}, environment_samples=samples(),
                request_windows=[[1, 2]], environment_context={'pid': 42, 'device': DEVICE})
        self.assertEqual(assess(r)['status'], 'SCOPED_DISPATCH_OBSERVED')
        changed = copy.deepcopy(r)
        for sample in changed['q8_0-d4']['result']['environment_samples']:
            sample['grant_sha256'] = 'b'*64
        self.assertEqual(assess(changed)['status'], 'UNKNOWN')
        for key in r:
            broken = copy.deepcopy(r)
            # Claimed PASS remains intact; raw evidence must fail independently.
            broken[key]['result']['environment_samples'][0]['sclk_mhz'] = 0
            self.assertEqual(assess(broken)['status'], 'UNKNOWN')
            broken = copy.deepcopy(r)
            broken[key]['result']['environment_samples'][0]['allocations']['43'] = 1
            verdict = assess(broken)
            self.assertEqual(verdict['status'], 'UNKNOWN')
            self.assertIsNone(verdict['vec_observed'])

    def test_plan_separates_controls_and_preserves_four_cells(self):
        b = base()
        original = copy.deepcopy(b)
        plan = configs(b, '/scratch')
        self.assertEqual(b, original)
        self.assertEqual([k for k, _ in plan], ['q8_0-mtp-off', 'q4_0-mtp-off', 'q8_0-d1', 'q8_0-d4', 'q4_0-d1', 'q4_0-d4'])
        self.assertEqual(len({c['output'] for _, c in plan}), 6)
        for i, (_, c) in enumerate(plan):
            args = c['server_args']
            self.assertEqual(args[args.index('--spec-type') + 1], 'none' if i < 2 else 'draft-mtp')
            self.assertEqual(c['requests'], b['requests'])

    def test_ambiguous_option_refused(self):
        for extra in (['--spec-type', 'none'], ['--spec-type=none'], ['-fa', 'off']):
            b = base(); b['server_args'] += extra
            with self.assertRaises(ValueError): configs(b, '/scratch')

    def test_real_parser_accepts_independent_off_dispatch(self):
        self.assertEqual(negative_control(trace(), capture(), [3], 1, 'q8_0')['status'], 'PASS')

    def test_control_refuses_empty_startup_only_wrong_kv_and_candidate(self):
        for text in ('', trace().replace('1500000000', '500000000'),
                     trace().replace('q8_0', 'q4_0'),
                     '\n'.join([B + ' time_ns=1100000000', D + ' time_ns=1500000000', E + ' time_ns=1900000000']),
                     trace().replace('time_ns=1500000000', 'time_ns=bad')):
            with self.subTest(text=text):
                self.assertEqual(negative_control(text, capture(), [3], 1, 'q8_0')['status'], 'UNKNOWN')

    def test_control_requires_output_drain_residency_and_every_request(self):
        for field, value in [('status', 'partial'), ('process_group_drained', False),
                             ('requests', [{'tokens_predicted': 0}]), ('residency', []),
                             ('request_windows', [[1, 2], [3, 4]]), ('request_windows', [[1, float('nan')]])]:
            r = capture(); r[field] = value
            self.assertEqual(negative_control(trace(), r, [3], 1, 'q8_0')['status'], 'UNKNOWN')

    def test_full_protocol_cannot_certify_ownership(self):
        verdict = assess(records())
        self.assertEqual(verdict['dispatch_protocol'], 'PASS')
        self.assertIsNone(verdict['vec_observed'])
        self.assertEqual(verdict['status'], 'UNKNOWN')

    def test_missing_controls_or_cell_never_yield_vec(self):
        for key in records():
            r = records(); del r[key]
            verdict = assess(r)
            self.assertEqual(verdict['dispatch_protocol'], 'UNKNOWN')
            self.assertIsNone(verdict['vec_observed'])

    def test_partial_coverage_wrong_shape_and_failed_control_refused(self):
        for mutation in ('partial', 'shape', 'control', 'rc', 'count', 'kv'):
            r = records(); c = r['q8_0-d4']; t = c['result']['timed_analysis']
            if mutation == 'partial': t['coverage']['bounded_dispatches'] = 0
            if mutation == 'shape': t['trace']['candidates'][0]['draft_length'] = 1
            if mutation == 'control': r['q4_0-mtp-off']['control']['status'] = 'UNKNOWN'
            if mutation == 'rc': c['rc'] = 75
            if mutation == 'count': t['observed'] = []
            if mutation == 'kv': t['trace']['candidates'][0]['dispatches'][0]['k_type'] = 'f16'
            self.assertEqual(assess(r)['dispatch_protocol'], 'UNKNOWN')

    def test_malformed_capture_returns_unknown(self):
        r = records(); r['q8_0-d1']['result']['timed_analysis']['trace'] = None
        self.assertEqual(assess(r)['status'], 'UNKNOWN')

    def test_executor_executes_all_six_and_retains_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); layers = root / 'layers.json'
            layers.write_text(json.dumps({'verify_attention_layer_ids': [3]}))
            b = base(); b['layer_manifest'] = str(layers)
            calls = []
            def run(argv, **kwargs):
                config = json.loads(Path(argv[-1]).read_text())
                out = Path(config['output']); out.mkdir(); calls.append(str(out))
                cell = records()[out.name]
                result = cell.get('result', capture())
                (out / 'result.json').write_text(json.dumps(result))
                (out / 'server.log').write_text(trace().replace('q8_0', out.name.split('-')[0]))
                return type('Done', (), {'returncode': 0})()
            with patch('native_protocol.subprocess.run', side_effect=run):
                verdict = execute(b, root / 'run')
            self.assertEqual(len(calls), 6)
            self.assertEqual(len(set(calls)), 6)
            self.assertEqual(verdict['dispatch_protocol'], 'PASS')
            self.assertEqual(verdict['status'], 'UNKNOWN')
            self.assertEqual(json.loads((root / 'run' / 'endpoint.json').read_text())['assessment'], verdict)

    def test_executor_runs_separate_processes_and_stops_on_control_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); layers = root / 'layers.json'
            layers.write_text(json.dumps({'verify_attention_layer_ids': [3]}))
            b = base(); b['layer_manifest'] = str(layers)
            calls = []
            def run(argv, **kwargs):
                config = json.loads(Path(argv[-1]).read_text()); calls.append(config)
                out = Path(config['output']); out.mkdir()
                (out / 'result.json').write_text(json.dumps(capture()))
                (out / 'server.log').write_text(trace())
                return type('Done', (), {'returncode': 0})()
            with patch('native_protocol.subprocess.run', side_effect=run):
                verdict = execute(b, root / 'run')
            # Second independent KV control fails: q8 trace cannot pass q4.
            self.assertEqual(len(calls), 2)
            self.assertEqual(verdict['dispatch_protocol'], 'UNKNOWN')
            self.assertTrue((root / 'run' / 'endpoint.json').is_file())
            self.assertTrue((root / 'run' / 'protocol.json').is_file())


if __name__ == '__main__': unittest.main()
