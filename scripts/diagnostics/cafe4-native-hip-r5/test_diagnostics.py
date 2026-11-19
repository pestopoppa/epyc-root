"""Model-free regressions for evidence retention on failed native controls."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cafe4_r2_runtime', Path(__file__).with_name('runtime.py'))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

FAILED = '''CAFE4_MTP_LOAD_ENABLED
CAFE4_DRAFT_REWIND_V4 pos=12
CAFE4_TARGET_RS memory=0x1 seq=0 selected=1 used=1 mode=1
CAFE4_TARGET_RS memory=0x2 seq=0 selected=1 used=0 mode=2
UNKNOWN nonfault cold-prefix numerical control failed
CAFE4_REFERENCE floor=0.907920361 tolerance=0.743863867
CAFE4_MTP_ROLLBACK width=2 accepted=1 selected=1 faulted=1 off_error=0.907920361 observe_error=0.907920361 fault_error=18.5714054 off_observe=0 fault_observe=18.6988792 tolerance=0.743863867
'''
GOOD = FAILED.replace('0.907920361', '0').replace('UNKNOWN nonfault cold-prefix numerical control failed\n', '')


class FailedEvidence(unittest.TestCase):
    def test_failed_numerical_control_keeps_values_without_qualifying(self):
        record = runtime.diagnostics(FAILED, 2, 2, False)
        self.assertEqual(record['measurements']['off_error'], .907920361)
        self.assertEqual(record['measurements']['tolerance'], .743863867)
        self.assertEqual(record['failed_predicates'],
                         ['unexpected-exit', 'nonfault-numerical-control', 'result-witness'])
        self.assertEqual(len(record['native_messages']), 2)
        self.assertIsNone(runtime.controls(FAILED, 2, 2, False))
        json.dumps(record, allow_nan=False)

    def test_normal_and_intended_fault_still_require_exact_exit(self):
        for fault, witness in ((False, runtime.PASS), (True, runtime.FAULT)):
            text = GOOD + witness
            self.assertEqual(runtime.diagnostics(text, int(fault), 2, fault)['failed_predicates'], [])
            self.assertIsNotNone(runtime.controls(text, int(fault), 2, fault))
            self.assertIsNone(runtime.controls(text, 2, 2, fault))
            self.assertIn('unexpected-exit', runtime.diagnostics(text, 2, 2, fault)['failed_predicates'])

    def test_ambiguous_malformed_nonfinite_measurements_remain_json_safe(self):
        for text in ('', FAILED + FAILED,
                     FAILED.replace('off_error=0.907920361', 'off_error=nan'),
                     FAILED.replace('fault_error=18.5714054', 'fault_error=inf'),
                     FAILED.replace('off_error=0.907920361', 'off_error=oops'),
                     FAILED.replace('tolerance=0.743863867', 'tolerance=-1')):
            with self.subTest(text=text[-100:]):
                result = runtime.diagnostics(text, 2, 2, False)
                self.assertIsNone(result['measurements'])
                self.assertTrue(result['failed_predicates'])
                self.assertIsNone(runtime.controls(text, 2, 2, False))
                json.dumps(result, allow_nan=False)

    def test_individual_native_messages_survive_missing_numeric_marker(self):
        text = ('CAFE4_TRIAL_FAILURE mode=1 width=2 stage=verify-process\n'
                'CAFE4_CONTROL_FAILURE control=observe-lifecycle\n'
                'UNKNOWN lifecycle/provenance or matched-prefix control missing\n')
        result = runtime.diagnostics(text, 2, 2, False)
        self.assertEqual(result['native_messages'], text.splitlines())
        self.assertIn('rollback-marker-count', result['failed_predicates'])
        self.assertIn('target-mode-1', result['failed_predicates'])

    def test_relaxed_tolerance_is_diagnosed_and_never_qualifies(self):
        text = (GOOD + runtime.PASS).replace('tolerance=0.743863867', 'tolerance=1')
        self.assertIn('fixed-tolerance-mismatch', runtime.diagnostics(text, 0, 2, False)['failed_predicates'])
        self.assertIsNone(runtime.controls(text, 0, 2, False))

    def test_structural_and_fault_sensitivity_failures_are_distinct(self):
        text = GOOD.replace('accepted=1 selected=1', 'accepted=0 selected=0').replace('fault_error=18.5714054', 'fault_error=1')
        result = runtime.diagnostics(text + runtime.PASS, 0, 2, False)
        self.assertEqual(result['failed_predicates'], ['acceptance-or-target-counts', 'fault-sensitivity'])
        self.assertIsNone(runtime.controls(text + runtime.PASS, 0, 2, False))

    def test_failed_scheduled_case_persists_diagnostics_and_stops(self):
        # Exercise run() with a child spy: no model, inference, or real child.
        records = []
        class Child:
            def __init__(self, command, stdout, **kwargs):
                stdout.write(FAILED)
                stdout.flush()
                self.pid = 123
                self.calls = 0
            def poll(self):
                self.calls += 1
                return None if self.calls <= 2 else 2
            def wait(self, **kwargs):
                return 2
        with tempfile.TemporaryDirectory(prefix='cafe4-receipt-') as tmp:
            directory = Path(tmp)
            inputs = dict(row='test-row', executable='/unused/exe', model=dict(path='/unused/model'), build_receipt={})
            env = dict(FILLER_DRYRUN='0', FILLER_ID='test-row', FILLER_STOPFILE=str(directory / 'STOP'),
                       FILLER_DEADLINE='9999999999', FILLER_THREADS='4')
            with patch.object(runtime, 'D', directory), patch.object(runtime, 'inputs', return_value=inputs), \
                 patch.object(runtime, 'digest', return_value='test-hash'), \
                 patch.object(runtime.Path, 'is_file', return_value=True), \
                 patch.object(runtime, 'mappings', return_value=(True, ['local-lib'])), \
                 patch.object(runtime, 'residency', return_value=dict(pid=123, kfd_registered=True, vram_bytes=4096)), \
                 patch.object(runtime, 'atomic', side_effect=lambda path, record: records.append((path, record))), \
                 patch.object(runtime.resource, 'setrlimit'), patch.object(runtime.time, 'sleep'), \
                 patch.object(runtime.subprocess, 'Popen', side_effect=Child) as child, \
                 patch.dict(os.environ, env):
                self.assertEqual(runtime.run(), 2)
            self.assertEqual(child.call_count, 1)
            terminal = records[-1][1]
            self.assertEqual(terminal['status'], 'UNKNOWN')
            self.assertEqual(len(terminal['cases']), 1)
            case = terminal['cases'][0]
            self.assertIsNone(case['controls'])
            self.assertTrue(case['mapped'] and case['child_reaped'])
            self.assertEqual(len(case['residency']), 2)
            self.assertIn('nonfault-numerical-control', case['diagnostics']['failed_predicates'])
            self.assertEqual(case['diagnostics']['measurements']['off_error'], .907920361)
            json.dumps(terminal, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
