"""Execute the full imported driver cell, controller and gate with fake peers."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compose


def worker(output):
    sys.path.insert(0, str(output))
    spec = importlib.util.spec_from_file_location('full_driver', output / 'driver.py')
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    import composition
    import controller
    import driver_boundary as boundary
    import cancel_seed_transport as transport
    gate = driver.gate

    class ActualCell(unittest.TestCase):
        def exercise(self, mode, finalizer=False, refusal_ledger=False, ordinary=False):
            events = []
            root = Path(os.environ['KPF_COMPOSITION_OUTPUT'])
            stop = root / 'STOP'
            stop.unlink(missing_ok=True)
            record = {'load_id': 'fake', 'server_instance': {}, 'construction_attempts': []}
            identity = {'source_prompt_ids_sha256': 'fake', 'layout_normalizer_sha256': 'fake'}
            class Ledger:
                directory = root
                serial = 0
                def __init__(self):
                    self.views, self.events = [], []
                def cursor(self): return 0
                def invoke(self, label, slot, body, fn, **kwargs):
                    events.append(label)
                    if 'full32512-seed' in label:
                        return fn(), {'event_id': 1}
                    return {}, {'event_id': 1}
                def request(self, *args): return {}, {'event_id': 1}
                def action(self, slot, operation, body):
                    return ({'n_saved': 32000, 'n_written': 1} if operation == 'save' else
                            {'n_restored': 32000, 'n_read': 1}), {'event_id': 1}
                def artifact(self, path): return {'ref': 'fake'}
                def json(self, name, value):
                    events.append('ledger:' + name)
                    if finalizer and name == 'C1-seed-1.json':
                        raise OSError('attempt finalizer failed')
                    if refusal_ledger and name == 'DIAGNOSTIC-REFUSAL.json':
                        raise OSError('refusal ledger failed')
                    return {'ref': name}
            ledger = Ledger()
            fake_run = NS(extra={}, srv=None, run_id='fake', finish=lambda: events.append('partial-finish'))
            ctx = NS(open_runs=[fake_run], own_children=[], preempted=False,
                     client=NS(erase=lambda slot: {}))
            def stop_server():
                events.append('server-stop')
                ctx.own_children.remove(srv)
            srv = NS(label='fake', sampler=None, argv=[], stop=stop_server, ctx=ctx, log=root / 'synthetic.log')
            def start():
                ctx.own_children.append(srv)
                events.append('server-start')
            def setup(*args):
                args[-1].update(R=None, record=record, identity=identity, ledger=ledger)
            checks = []
            def original_boundary():
                checks.append(True)
                if mode == 'guard' and len(checks) == 2:
                    raise ValueError('underlying guard tripped')
            def seed(**kwargs):
                events.append('seed')
                if ordinary:
                    raise ValueError('ordinary seed failure')
                if mode == 'stop': stop.touch()
                kwargs['ctx'].check_boundary()
                self.fail('native seed work after refusal')
            group = {'T': 32000, 'trunk': [0]*32000, 'src_tail': [0]*512,
                     'suffixes': [[], [], [1]*4000], 'filler': [0]*32000}
            times = iter([10, 20])
            clock = (lambda: next(times)) if mode == 'deadline' else (lambda: 10)
            env = {'FILLER_END': '30', 'FILLER_DEADLINE': '20', 'FILLER_STOPFILE': str(stop)}
            if mode == 'missing': env['FILLER_END'] = ''
            argv = ['gate.py', 'item3', '--argv-file', 'fake', '--out', str(root / mode),
                    '--no-device-claim', 'synthetic peers only']
            # The actual item3 creates its actual cell and passes it to actual
            # gate.main. The cell calls actual controller.run (no AST extraction).
            with contextlib.ExitStack() as stack:
                overrides = [
                    (driver, 'guard', NS(BIN=Path('/fake'), ContextBoundary=lambda c: NS(check_boundary=original_boundary))),
                    (driver, 'setup', setup), (driver, 'publish', lambda *a: events.append('publish')),
                    (driver, 'time', NS(time=clock)),
                    (gate, 'Server', lambda *a, **kw: srv),
                    (gate, 'start_steps', lambda *a: [gate.Step('start fake', 0, start)]),
                    (gate, 'build_ctx', lambda *a: (ctx, [], [])),
                    (gate, 'print_plan', lambda *a: None), (gate, 'write_json', lambda *a: None),
                    (gate, 'G', lambda *a: group), (gate, 'flag_val', lambda *a: str(root)),
                    (controller.g, 'ORDER', ['C1']),
                    (controller, 'SeedControl', lambda **kw: seed),
                    (gate.signal, 'signal', lambda *a: None),
                    (sys, 'argv', argv), (gate, 'ITEMS', {3: driver.item3})]
                for obj, name, value in overrides:
                    stack.enter_context(patch.object(obj, name, value))
                stack.enter_context(patch.dict(os.environ, env))
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = gate.main()
            self.assertEqual(rc, 0 if ordinary else 3, (events, record))
            self.assertEqual(events.count('server-stop'), 1)
            self.assertTrue(fake_run.extra['partial'])
            self.assertLess(events.index('server-stop'), events.index('partial-finish'))
            if ordinary:
                self.assertIn('publish', events)
                self.assertEqual(len(record['construction_attempts']), 3)
                self.assertIn('bounded native exactT construction exhausted', record['diagnostic_error'])
            else:
                self.assertNotIn('publish', events)
                self.assertIn('diagnostic_error', record)
                self.assertEqual(len(record['construction_attempts']), 0 if mode == 'missing' else 1)
                self.assertIn({'stop': 'stop-file', 'deadline': 'deadline', 'guard': 'underlying guard tripped',
                               'missing': 'missing-or-invalid-rowflow-contract'}[mode], record['diagnostic_error'])
                if finalizer: self.assertIn('attempt finalizer failed', record['diagnostic_error'])
            stop.unlink(missing_ok=True)

        def test_stop(self): self.exercise('stop')
        def test_deadline(self): self.exercise('deadline')
        def test_guard(self): self.exercise('guard')
        def test_missing_contract(self): self.exercise('missing')
        def test_finalizer_preserves_stop(self): self.exercise('stop', finalizer=True)
        def test_refusal_ledger_still_aborts(self): self.exercise('stop', refusal_ledger=True)
        def test_both_ledgers_fail(self): self.exercise('deadline', finalizer=True, refusal_ledger=True)
        def test_ordinary_error_retains_bounded_retry(self): self.exercise('allowed', ordinary=True)
        def test_actual_bindings(self):
            self.assertIs(driver.run, controller.run)
            self.assertIs(controller.SeedControl, transport.SeedControl)
            self.assertIs(driver.RowflowContext, boundary.RowflowContext)
            self.assertEqual(Path(boundary.__file__).parent, compose.BOUNDARY)
        def test_repeat_binding_refused(self):
            with self.assertRaisesRegex(ValueError, 'preloaded terminal'):
                composition.bind()
        def test_changed_driver_refused(self):
            path = output / 'driver.py'
            raw = path.read_bytes()
            try:
                path.write_bytes(raw + b'\n# drift\n')
                with self.assertRaisesRegex(ValueError, 'source drift'): composition.verify()
            finally: path.write_bytes(raw)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ActualCell)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    composition.verify()
    print(json.dumps({'tests': result.testsRun, 'pass': result.wasSuccessful()}))
    return 0 if result.wasSuccessful() else 1


class Composition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=compose.SCRATCH)
        cls.root = Path(cls.temp.name)
        cls.output = cls.root / 'driver'
        compose.install(cls.output)
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def test_full_driver_cell(self):
        out = self.root / 'out'
        out.mkdir()
        result = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'test_composition.py'),
                                 '--worker', str(self.output)], capture_output=True, text=True, timeout=60,
                                env=dict(os.environ, KPF_COMPOSITION_OUTPUT=str(out), PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {'tests': 11, 'pass': True})
    def test_disabled_entries(self):
        for args in (['bash', str(self.output / 'launch.sh')],
                     [sys.executable, '-I', '-B', str(self.output / 'driver.py')]):
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 78)
    def test_destination_refusals(self):
        for path in (self.output, Path('/tmp/foreign-terminal-successor')):
            with self.assertRaises(ValueError): compose.install(path)
    def test_incomplete_and_preloaded_refusals(self):
        marker = self.output / 'INCOMPLETE'
        code = 'import sys;sys.path.insert(0,sys.argv[1]);import composition;composition.bind()'
        try:
            marker.touch()
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(self.output)], capture_output=True)
            self.assertIn(b'incomplete composition', result.stderr)
            self.assertNotEqual(result.returncode, 0)
        finally: marker.unlink()
        for name in ('adapter', 'driver_boundary'):
            prefix = 'import sys,types;sys.modules[' + repr(name) + ']=types.ModuleType(' + repr(name) + ');'
            result = subprocess.run([sys.executable, '-I', '-B', '-c', prefix + code, str(self.output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'preloaded terminal dependency', result.stderr)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']: raise SystemExit(worker(Path(sys.argv[2])))
    unittest.main()
