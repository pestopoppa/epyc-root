"""Independent model-free controls for retained-bindings-v2, not R9 replay."""
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
import install


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(destination, mode):
    # Fresh process imports the installed full driver, with no synthetic modules.
    outer = load(destination / 'supervisor.py', 'outer')
    outer.verify()
    sys.path.insert(0, str(destination))
    if mode == 'bad-output':
        try:
            load(destination / 'driver.py', 'full_driver')
        except ValueError as error:
            assert 'scratch output' in str(error)
            return
        raise AssertionError('accepted unsafe output')
    driver = load(destination / 'driver.py', 'full_driver')
    import composition
    import controller
    import cancel_seed_transport
    import driver_boundary
    import normalize_bridge
    import evidence_view
    assert driver.run is controller.run
    assert controller.SeedControl is cancel_seed_transport.SeedControl
    assert driver.RowflowContext is driver_boundary.RowflowContext
    assert Path(normalize_bridge.__file__) == install.RETAINED / 'normalize_bridge.py'
    assert Path(evidence_view.__file__) == install.RETAINED / 'evidence_view.py'
    root = Path(os.environ['KPF_COMPOSITION_OUTPUT'])
    assert driver.OUT == root and composition.output_root() == root
    gate = driver.gate
    if mode == 'main':
        # Traverse actual main without native launch; source authority, GPU and
        # model loading are outside this control's scope.
        calls = []
        with patch.object(driver.guard, 'sources', side_effect=lambda: calls.append('sources')), \
             patch.object(driver, 'load_preload_models', side_effect=AssertionError('loaded model')), \
             patch.object(sys, 'argv', ['driver.py', 'item3', '--dry-run', '--out', str(root)]), \
             patch.object(gate, 'main', side_effect=lambda: calls.append('gate-main') or 9):
            import gpu_witness
            with patch.object(gpu_witness, 'install', side_effect=lambda g: calls.append('witness')):
                assert outer.run(driver.main) == 9
        assert calls == ['sources', 'witness', 'gate-main'], calls
    elif mode == 'smoke-output':
        # Real item3_smoke closure writes through imported driver.OUT. Only
        # server/request/resource peers are inert; this is not a native smoke.
        srv = NS(sampler=NS(n_own_nonzero=1))
        ctx = NS(client=NS(_req=lambda *a, **kw: (200, {'tokens': [7]})),
                 check_boundary=lambda: None)
        with patch.object(gate, 'Server', return_value=srv), \
             patch.object(gate, 'start_steps', return_value=[]), \
             patch.object(gate, 'stop_step', return_value=None), \
             patch.object(gate, 'G', return_value={'trunk': list(range(40))}), \
             patch.object(driver.guard, 'boundary', return_value=None):
            steps = driver.item3_smoke(ctx)
            # Gate Step is a dataclass with an actual callable action.
            action = next(value for value in vars(steps[0]).values() if callable(value))
            outer.run(action)
            result = json.loads((root / 'SMOKE-REQUEST.json').read_text())
            assert result['first_request_ok'] and result['tokens'] == 1
            try:
                outer.run(action)
            except FileExistsError:
                pass
            else:
                raise AssertionError('overwrote prior smoke output')
    elif mode == 'rebind':
        try:
            composition.bind()
        except ValueError as error:
            assert 'preloaded terminal' in str(error)
        else:
            raise AssertionError('accepted repeated bindings')
    else:
        raise AssertionError(mode)
    composition.verify()


class RetainedSuccessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=install.SCRATCH)
        cls.destination = Path(cls.temp.name) / 'v2'
        cls.before = {path: install.digest(path) for path in install.PINS}
        cls.seal = install.install(cls.destination, binding_revision=install.REVISION)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def invoke(self, mode, root):
        result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker',
                                 str(self.destination), mode], capture_output=True, text=True,
                                timeout=30, env=dict(os.environ, KPF_COMPOSITION_OUTPUT=str(root),
                                                    PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_full_import_and_actual_main(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as out:
            self.invoke('main', out)

    def test_real_smoke_closure_routes_output_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as out:
            self.invoke('smoke-output', out)

    def test_repeated_binding_refused(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as out:
            self.invoke('rebind', out)

    def test_invalid_output_roots_refused_before_main(self):
        for root in ('', 'relative', '/tmp', '/mnt/raid0/llm/tmp/kvu/absent-v2-output'):
            with self.subTest(root=root):
                self.invoke('bad-output', root)

    def test_output_symlink_refused(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as out:
            link = Path(out) / 'link'
            link.symlink_to(out, target_is_directory=True)
            self.invoke('bad-output', link)

    def test_version_and_historical_inventory_are_distinct(self):
        self.assertEqual(self.seal['schema'], 'kpf18.disabled-supervisor.v2')
        self.assertEqual(self.seal['historical_sources'], install.SUPERSEDED)
        self.assertTrue(set(install.SUPERSEDED).isdisjoint(self.seal['sources']))
        for path, expected in install.REPLACEMENTS.items():
            self.assertEqual(self.seal['sources'][str(path)], expected)
        self.assertIn(str(HERE / 'test_successor.py'), self.seal['sources'])
        for path, expected in self.before.items():
            self.assertEqual(install.digest(path), expected)

    def test_replacement_drift_refused_without_creating_destination(self):
        original = install.digest
        for target in install.REPLACEMENTS:
            destination = Path(self.temp.name) / 'drift'
            with patch.object(install, 'digest', side_effect=lambda p: '0'*64 if p == target else original(p)):
                with self.assertRaisesRegex(ValueError, 'retained replacement drift'):
                    install.install(destination, binding_revision=install.REVISION)
            self.assertFalse(destination.exists())

    def test_unknown_revision_refused(self):
        destination = Path(self.temp.name) / 'unknown'
        with self.assertRaisesRegex(ValueError, 'unknown binding revision'):
            install.install(destination, binding_revision='v3')
        self.assertFalse(destination.exists())

    def test_default_keeps_original_r9_requirements(self):
        with self.assertRaises(FileNotFoundError):
            install.install(Path(self.temp.name) / 'historical')

    def test_all_direct_entries_disabled(self):
        for path in ('supervisor.py', 'driver.py'):
            result = subprocess.run([sys.executable, '-I', '-B', str(self.destination / path)],
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 78, result.stderr)
        self.assertEqual(subprocess.run(['bash', str(self.destination / 'launch.sh')]).returncode, 78)

    def test_no_execution_authority_inferred(self):
        outer = load(self.destination / 'supervisor.py', 'outer_test')
        admission = load(self.destination / 'execution_admission.py', 'admission_test')
        with self.assertRaisesRegex(ValueError, 'complete current execution custody'):
            admission.custody(outer.verify())

    def test_source_drift_refused(self):
        path = self.destination / 'launch.sh'
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b'# drift\n')
            outer = load(self.destination / 'supervisor.py', 'drift_test')
            with self.assertRaisesRegex(ValueError, 'source drift'):
                outer.run(lambda: self.fail('entry reached'))
        finally:
            path.write_bytes(raw)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()
