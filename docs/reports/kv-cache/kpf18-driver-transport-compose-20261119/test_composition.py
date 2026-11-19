"""Full imported driver/controller composition; synthetic native peers only."""
import importlib.util
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


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(output):
    sys.path.insert(0, str(output))
    # Load the entire module, including its actual controller and gate imports.
    driver = load('qualified_full_driver', output / 'driver.py')
    import composition
    import controller
    import cancel_seed_transport as transport
    import slots_transport
    previous = load('consumer_fixtures', HERE.parent / 'kpf18-seed-cleanup-20261119/test_consumer.py')

    class DriverConsumer(previous.Consumer):
        @classmethod
        def setUpClass(cls):
            cls.module = transport

        @classmethod
        def tearDownClass(cls):
            pass

        def exercise(self, *args, **kwargs):
            # The actual controller's imported class is the consumer executed
            # by inherited tests. Native slots/SSE/logs remain synthetic.
            self.assertIs(controller.SeedControl, transport.SeedControl)
            with patch.object(transport, 'bounded_slots', side_effect=lambda ctx, **kw: ctx.client.slots()):
                return super().exercise(*args, **kwargs)

    class FullDriver(unittest.TestCase):
        def test_actual_controller_binding(self):
            self.assertIs(driver.run, controller.run)
            self.assertIs(controller.SeedControl, transport.SeedControl)
            self.assertIs(transport.bounded_slots, slots_transport.bounded_slots)
            self.assertEqual(Path(transport.__file__).parent, compose.TRANSPORT)
            self.assertEqual(driver.BASE, compose.BASE / 'candidate')
            self.assertEqual(driver.OUT, Path(os.environ['KPF_COMPOSITION_OUTPUT']))

        def invoke(self, source_error=False, preload_error=False, dry=True):
            events = []
            def sources():
                events.append('sources')
                if source_error:
                    raise ValueError('source refused')
            def preload(*args):
                events.append('preload')
                if preload_error:
                    raise ValueError('preload refused')
                return {'target': {}, 'drafter': {}}
            fake_guard = NS(sources=sources, boundary=lambda: events.append('boundary'),
                            tests_and_enrollment=lambda: events.append('enrollment'))
            fake_gate = NS(PROD_ENV={}, ITEMS={},
                           main=lambda: events.append('gate') or 23)
            witness = NS(install=lambda gate: events.append('gpu-install'))
            with patch.object(driver, 'guard', fake_guard), patch.object(driver, 'gate', fake_gate), \
                 patch.object(driver, 'load_preload_models', preload), \
                 patch.object(driver, 'unchanged_models', lambda: events.append('unchanged')), \
                 patch.dict(sys.modules, gpu_witness=witness), \
                 patch.object(sys, 'argv', ['driver.py'] + (['--dry-run'] if dry else [])):
                if source_error or preload_error:
                    with self.assertRaisesRegex(ValueError, 'refused'):
                        driver.main()
                    self.assertNotIn('gpu-install', events)
                    self.assertNotIn('gate', events)
                else:
                    self.assertEqual(driver.main(), 23)
                    self.assertEqual(events[-2:], ['gpu-install', 'gate'])
                    self.assertIs(fake_gate.ITEMS[3], driver.item3)
                return events

        def test_actual_main_dry_entry_order(self):
            self.assertEqual(self.invoke(), ['sources', 'gpu-install', 'gate'])

        def test_actual_main_source_refusal(self):
            self.invoke(source_error=True)

        def test_actual_main_preload_refusal(self):
            self.invoke(preload_error=True, dry=False)

        def test_actual_main_preload_composes_with_gpu(self):
            self.assertIn('preload', self.invoke(dry=False))

        def test_repeat_binding_refused(self):
            with self.assertRaisesRegex(ValueError, 'preloaded candidate'):
                composition.bind()

        def test_changed_driver_refused(self):
            path = output / 'driver.py'
            raw = path.read_bytes()
            try:
                path.write_bytes(raw + b'\n# injected drift\n')
                with self.assertRaisesRegex(ValueError, 'source drift'):
                    composition.verify()
            finally:
                path.write_bytes(raw)

    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(DriverConsumer),
        unittest.defaultTestLoader.loadTestsFromTestCase(FullDriver)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    composition.verify()
    print(json.dumps({'tests': result.testsRun, 'pass': result.wasSuccessful(),
                      'scope': 'full driver import/main fakes; controller-bound consumer synthetic peers'}))
    return 0 if result.wasSuccessful() else 1


class Composition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=compose.SCRATCH)
        cls.root = Path(cls.temp.name)
        cls.output = cls.root / 'driver'
        cls.seal = compose.install(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_full_driver(self):
        out = self.root / 'out'
        out.mkdir()
        env = dict(os.environ, KPF_COMPOSITION_OUTPUT=str(out), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'test_composition.py'),
                                 '--worker', str(self.output)], env=env, capture_output=True,
                                text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['tests'], 15)
        self.assertTrue(report['pass'])

    def test_both_direct_entries_disabled(self):
        for command in (['bash', str(self.output / 'launch.sh')],
                        [sys.executable, '-I', '-B', str(self.output / 'driver.py')]):
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 78)

    def test_existing_destination_refused(self):
        with self.assertRaises(ValueError):
            compose.install(self.output)

    def test_outside_scratch_refused(self):
        with self.assertRaises(ValueError):
            compose.install(Path('/tmp/kpf18-outside'))

    def test_incomplete_install_refused(self):
        # Refusal occurs before any imports, without loading the full driver.
        code = "import sys;sys.path.insert(0,sys.argv[1]);import composition;composition.verify()"
        marker = self.output / 'INCOMPLETE'
        try:
            marker.touch()
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(self.output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('incomplete composition', result.stderr)
        finally:
            marker.unlink()


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        raise SystemExit(worker(Path(sys.argv[2])))
    unittest.main()
