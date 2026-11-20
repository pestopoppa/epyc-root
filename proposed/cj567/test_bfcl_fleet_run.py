"""Controls for coverage semantics and owned-child cleanup; no model runs."""
import subprocess
import sys
import unittest
from unittest.mock import Mock

from bfcl_fleet_run import CaptureBudget, select_rows, stop_server, summarize


class BudgetControls(unittest.TestCase):
    def test_request_and_cleanup_must_fit_strictly_before_deadline(self):
        now = [100.0]
        budget = CaptureBudget(False, 8442, lambda: False, clock=lambda: now[0])
        self.assertEqual(budget.timeout, 8312)
        self.assertFalse(budget.can_start())
        with self.assertRaises(TimeoutError):
            budget.guard({'max_tokens': 4096})
        now[0] -= .001
        self.assertTrue(budget.can_start())
        budget.guard({'max_tokens': 4096})

    def test_slow_response_fits_new_budget_but_not_old_timeout(self):
        import io
        from bfcl_residency import LocalNativeTransport
        clock = [0.0]
        budget = CaptureBudget(False, 10000, lambda: False, clock=lambda: clock[0])
        simulated_seconds = 120 + 4096 / 1.08
        self.assertGreater(simulated_seconds, 300)
        self.assertLess(simulated_seconds, budget.timeout)
        self.assertEqual((budget.metadata['max_tokens'], budget.metadata['cleanup_s']), (4096, 30))
        smoke = CaptureBudget(True, 20000, lambda: False, clock=lambda: 0)
        self.assertEqual((smoke.max_tokens, smoke.timeout), (24, 300))
        # Exercise the actual HTTP-call path with a fake clock, without waiting.
        transport = LocalNativeTransport.__new__(LocalNativeTransport)
        transport.identity = {'model': 'fixture'}; transport.port = 123
        transport.timeout = budget.timeout; transport.request_guard = budget.guard
        transport.probe = Mock(); transport.opener = Mock()

        def response(request, timeout):
            if simulated_seconds > timeout:
                raise TimeoutError('old budget would expire')
            clock[0] += simulated_seconds
            return io.BytesIO(b'{"choices": []}')

        transport.opener.open.side_effect = response
        self.assertEqual(transport({'model': 'fixture', 'max_tokens': 4096}), {'choices': []})
        transport.opener.open.assert_called_once()
        self.assertGreater(clock[0], 300)

    def test_stop_and_invalid_request_budget_refuse(self):
        stopped = [False]
        budget = CaptureBudget(False, 10000, lambda: stopped[0], clock=lambda: 0)
        for tokens in (None, True, 0, -1, 4097, 4096.0):
            with self.subTest(tokens=tokens), self.assertRaises(ValueError):
                budget.guard({'max_tokens': tokens})
        stopped[0] = True
        with self.assertRaises(TimeoutError):
            budget.guard({'max_tokens': 4096})
        self.assertFalse(budget.can_start())
        for deadline in (float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                CaptureBudget(False, deadline, lambda: False)

    def test_worker_shares_budget_and_does_not_expose_without_full_window(self):
        import json
        import os
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from bfcl_fleet_run import run
        from bfcl_residency import fingerprint

        for mode in ('available', 'insufficient', 'timeout'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                model = root / 'fixture-weight'; model.write_bytes(b'not model weights')
                (root / 'MODEL.json').write_text(json.dumps({'path': str(model),
                    'stat': fingerprint(model.stat()), 'sha256': 'a' * 64}))
                (root / 'CONFIG.json').write_text(json.dumps({'model': 'fixture',
                    'server': '/fixture', 'server_binary_sha256': 'b' * 64,
                    'library_path': '/fixture', 'checker': '', 'catalog': ''}))
                (root / 'BUILD.json').write_text('{}')
                (root / 'SELECTION.json').write_text('{}')
                grants = root / 'grants'; grants.mkdir()
                (grants / 'fixture.grant').write_text('grant')
                process = Mock(pid=123, returncode=-15); process.poll.return_value = None
                health = Mock(); health.__enter__ = Mock(return_value=Mock(status=200))
                health.__exit__ = Mock(return_value=False)
                opener = Mock(); opener.open.return_value = health
                row = {'case': {'id': 'fixture'}}
                clock = [100.0]

                def capture(*args, **kwargs):
                    self.assertFalse(args[7]())  # before-exposure admission callback
                    guard = native.call_args.kwargs['request_guard']
                    guard({'max_tokens': 4096})
                    if mode == 'timeout':
                        raise TimeoutError('fixture transport timeout; no retry')
                    grant = grants / 'fixture.grant'
                    for change in ('changed', 'missing', 'STOP'):
                        if change == 'changed':
                            grant.write_text('different grant')
                        elif change == 'missing':
                            grant.unlink()
                        else:
                            (root / 'STOP').touch()
                        self.assertTrue(args[7]())
                        with self.assertRaises(TimeoutError):
                            guard({'max_tokens': 4096})
                        grant.write_text('grant')
                        (root / 'STOP').unlink(missing_ok=True)
                    # Time expires between turns: next exposure must be refused.
                    clock[0] += 2000
                    self.assertTrue(args[7]())
                    with self.assertRaises(TimeoutError):
                        guard({'max_tokens': 4096})
                    return {'valid': None}

                # Worker subtracts another 20 seconds before request admission.
                deadline = 8462 if mode == 'insufficient' else 10100
                with patch.dict(os.environ, {'FILLER_SMOKE': '0', 'FILLER_ID': 'fixture',
                        'FILLER_GRANTS_DIR': str(grants), 'FILLER_DEADLINE': str(deadline)}), \
                     patch('bfcl_fleet_run.time.time', side_effect=lambda: clock[0]), \
                     patch('bfcl_fleet_run.subprocess.Popen', return_value=process), \
                     patch('bfcl_fleet_run.build_opener', return_value=opener), \
                     patch('bfcl_fleet_run.LocalNativeTransport') as native, \
                     patch('bfcl_fleet_run.stop_server') as shutdown, \
                     patch('bfcl_fleet_run.OfficialV3'), \
                     patch('bfcl_fleet_run.select_rows', return_value=[row]), \
                     patch('bfcl_fleet_run.capture_case', side_effect=capture) as captured:
                    if mode == 'timeout':
                        with self.assertRaises(TimeoutError):
                            run(root)
                    else:
                        run(root)
                self.assertEqual(native.call_args.kwargs['timeout'], 8312)
                identity = native.call_args.args[2]
                self.assertEqual(identity['request_budget']['timeout_s'], 8312)
                attempt = json.loads((root / 'run/attempt.json').read_text())
                self.assertEqual(attempt['identity'], identity)
                self.assertEqual(captured.call_count, 0 if mode == 'insufficient' else 1)
                shutdown.assert_called_once_with(process)
                if mode == 'timeout':
                    self.assertFalse((root / 'run/RESULT.json').exists())
                    self.assertEqual(json.loads((root / 'run/ABORTED.json').read_text())['completed'], 0)
                else:
                    result = json.loads((root / 'run/RESULT.json').read_text())
                    self.assertEqual(result['completed'], 0 if mode == 'insufficient' else 1)
                    self.assertIsNone(result['score'])


class FleetControls(unittest.TestCase):
    def test_single_turn_selection_excludes_sql_and_multiturn(self):
        import json
        from pathlib import Path
        manifest = json.loads(Path('data/benchmarks/bfcl-v3-cj3d-prep-20261104/sample-manifest.json').read_text())
        rows = select_rows(manifest, 'single-turn')
        self.assertEqual(len(rows), 14)
        self.assertEqual({r['category'] for r in rows},
                         {'simple', 'multiple', 'parallel', 'parallel_multiple', 'java', 'javascript'})
        self.assertEqual(rows, manifest['cases'][:14])
        for replacement in (manifest['cases'][14], manifest['cases'][16], rows[0]):
            damaged = {'cases': rows[:-1] + [replacement]}
            with self.assertRaises(ValueError):
                select_rows(damaged, 'single-turn')
        with self.assertRaises(ValueError):
            select_rows({'cases': rows[:-1]}, 'single-turn')
        with self.assertRaises(ValueError):
            select_rows(manifest, 'all')

    def test_unknown_cannot_become_failure_or_score(self):
        summary = summarize([{'valid': True}, {'valid': False}, {'valid': None}], 10)
        self.assertEqual((summary['known'], summary['unknown'], summary['passed']), (2, 1, 1))
        self.assertFalse(summary['coverage_complete'])
        self.assertIsNone(summary['score'])
        self.assertIsNone(summarize([{'valid': True}] * 10, 10)['score'])

    def test_selection_refuses_missing_duplicate_and_nonmultiturn(self):
        valid = {'cases': [{}] * 16 + [{'case': {'id': str(i)}, 'category': 'multi_turn_base'}
                                     for i in range(10)]}
        self.assertEqual(len(select_rows(valid)), 10)
        with self.assertRaises(ValueError):
            select_rows({'cases': valid['cases'][:-1]})
        valid['cases'][-1] = valid['cases'][-2]
        with self.assertRaises(ValueError):
            select_rows(valid)
        valid['cases'][-1] = {'case': {'id': 'new'}, 'category': 'sql'}
        with self.assertRaises(ValueError):
            select_rows(valid)

    def test_cleanup_reaps_only_captured_child(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        stop_server(child)
        self.assertIsNotNone(child.poll())
        stop_server(child)  # already dead is safe

    def test_cleanup_escalates_and_confirms_death(self):
        child = Mock()
        child.poll.side_effect = [None, -9]
        child.wait.side_effect = [subprocess.TimeoutExpired('fixture', 15), -9]
        stop_server(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)

    def test_smoke_uses_synthetic_input_without_loading_or_scoring_cohort(self):
        import json
        import os
        from pathlib import Path
        import tempfile
        import time
        from unittest.mock import patch
        from bfcl_fleet_run import run
        from bfcl_residency import fingerprint

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / 'fixture-weight'
            model.write_bytes(b'fixture, not a model')
            (root / 'MODEL.json').write_text(json.dumps({'path': str(model),
                'stat': fingerprint(model.stat()), 'sha256': 'a' * 64}))
            (root / 'CONFIG.json').write_text(json.dumps({'model': 'fixture',
                'server': '/fixture', 'server_binary_sha256': 'b' * 64,
                'library_path': '/fixture'}))
            (root / 'BUILD.json').write_text('{}')
            (root / 'SELECTION.json').write_text('intentionally invalid cohort JSON')
            dry = root / 'dry'; dry.mkdir()
            attempt = dry / 'attempt1'; attempt.mkdir()
            process = Mock(); process.pid = 123; process.returncode = -15; process.poll.return_value = None
            health = Mock(); health.__enter__ = Mock(return_value=Mock(status=200))
            health.__exit__ = Mock(return_value=False)
            opener = Mock(); opener.open.return_value = health
            transport = Mock(return_value={'choices': [{'message': {'content': ''}}]})
            transport.probe.return_value = {'fixture': 'mock proof'}
            with patch.dict(os.environ, {'FILLER_SMOKE': '1', 'FILLER_DRYRUN_DIR': str(dry),
                    'FILLER_ID': 'fixture', 'FILLER_FLAGS_DIR': str(root),
                    'FILLER_DRYRUN_RESULT_PATH': str(attempt / 'native-result.json'),
                    'FILLER_DEADLINE': str(time.time() + 1000)}), \
                 patch('bfcl_fleet_run.subprocess.Popen', return_value=process), \
                 patch('bfcl_fleet_run.build_opener', return_value=opener), \
                 patch('bfcl_fleet_run.LocalNativeTransport', return_value=transport), \
                 patch('bfcl_fleet_run.stop_server') as shutdown, \
                 patch('bfcl_fleet_run.OfficialV3', side_effect=AssertionError('checker used')), \
                 patch('bfcl_fleet_run.capture_case', side_effect=AssertionError('cohort used')):
                run(root)
                # A prior smoke completion cannot complete or contaminate a new attempt.
                attempt2 = dry / 'attempt2'; attempt2.mkdir()
                with patch.dict(os.environ, {'FILLER_DRYRUN_RESULT_PATH': str(attempt2 / 'native-result.json')}):
                    run(root)
                self.assertTrue((attempt2 / 'native-result.json').exists())
            payload = transport.call_args.args[0]
            self.assertEqual(payload['max_tokens'], 24)
            self.assertEqual(payload['messages'][0]['content'], 'Use add to add 2 and 3.')
            self.assertFalse((root / 'run').exists())
            terminal = json.loads((attempt / 'bfcl-native/TERMINAL.json').read_text())
            self.assertEqual(terminal['status'], 'smoke_pass')
            self.assertEqual(terminal['completed'], 1)
            self.assertEqual(json.loads((attempt / 'native-result.json').read_text()), terminal)
            self.assertIsNone(terminal['score'])
            self.assertEqual(shutdown.call_count, 2)
            shutdown.assert_called_with(process)
