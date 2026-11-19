"""Current admission fixtures and real installed driver; never native execution."""
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
import test_execution_admission as fixtures
from test_execution_admission import load, sha
import install


class CurrentGuard(unittest.TestCase):
    def setUp(self):
        fixtures.PublisherSmokeAdmission.setUp(self)
        self.binding = load(HERE / 'execution_binding.py', 'binding_subject')
        self.seal.update(guard_revision=self.binding.REVISION, binding_revision=install.REVISION)
        self.guard_path = self.root / 'retained_guard.py'
        self.guard_path.write_text('# inert retained guard\n')
        self.seal['sources'][str(self.guard_path)] = sha(self.guard_path)
        self.guard = NS(__file__=str(self.guard_path), BIN=Path('/historical/server'),
                        boundary=object(), tests_and_enrollment=object())
        self.driver = NS(guard=self.guard, OUT=self.result.parent)
        self.captured = self.gate.capture(self.seal)
        argv = patch.object(sys, 'argv', ['driver.py', '--out', str(self.result.parent)])
        argv.start(); self.addCleanup(argv.stop)

    def prepare(self):
        return self.binding.prepare(self.seal, self.gate, self.captured)

    def test_current_sources_attempt_root_server_and_preserved_checks(self):
        boundary, enrollment = self.guard.boundary, self.guard.tests_and_enrollment
        output, bind = self.prepare()
        bind(self.driver)
        self.guard.sources()
        self.assertEqual(self.guard.attempt_root(), self.result.parent)
        self.assertEqual(output(), self.driver.OUT)
        self.assertEqual(self.guard.BIN, self.native)
        self.assertIs(self.guard.boundary, boundary)
        self.assertIs(self.guard.tests_and_enrollment, enrollment)
        with self.assertRaisesRegex(ValueError, 'already bound'): bind(self.driver)

    def test_source_drift_and_provider_loss_refuse_guard_checks(self):
        _, bind = self.prepare(); bind(self.driver)
        self.native.write_bytes(b'drift')
        with self.assertRaisesRegex(ValueError, 'source drift'): self.guard.sources()
        with self.assertRaisesRegex(ValueError, 'source drift'): self.guard.attempt_root()

    def test_provider_loss_and_cli_output_redirection_refused(self):
        _, bind = self.prepare()
        for argv in (['driver.py'], ['driver.py', '--out', str(self.root)],
                     ['driver.py', '--out='+str(self.result.parent)],
                     ['driver.py', '--out', str(self.result.parent), '--out', str(self.result.parent)]):
            with self.subTest(argv=argv), patch.object(sys, 'argv', argv):
                with self.assertRaisesRegex(ValueError, 'argv'): bind(self.driver)
        bind(self.driver)
        with patch.object(self.captured[0], 'recheck', side_effect=ValueError('provider lost')):
            with self.assertRaisesRegex(ValueError, 'provider lost'): self.guard.sources()

    def test_stop_and_grant_change_refuse_after_binding(self):
        _, bind = self.prepare(); bind(self.driver)
        stop = Path(self.config['stop_file']); stop.touch()
        with self.assertRaisesRegex(ValueError, 'STOP'): self.guard.sources()
        stop.unlink()
        self.grant.write_text(self.raw + ' admission_class=changed')
        with self.assertRaises(ValueError): self.guard.attempt_root()

    def test_alias_redirection_refused(self):
        for name in ('KPF_OUTPUT_ROOT', 'KPF_COMPOSITION_OUTPUT'):
            with self.subTest(name=name), patch.dict(os.environ, {name: str(self.root)}):
                with self.assertRaisesRegex(ValueError, 'redirected'): self.prepare()

    def test_symlink_output_refused_after_binding(self):
        output, bind = self.prepare(); bind(self.driver)
        self.result.parent.rmdir()
        self.result.parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): output()

    def test_unsealed_guard_wrong_output_and_revision_refused(self):
        _, bind = self.prepare()
        self.driver.OUT = self.root
        with self.assertRaisesRegex(ValueError, 'differs'): bind(self.driver)
        self.driver.OUT = self.result.parent
        self.guard.__file__ = str(self.root / 'unsealed.py')
        with self.assertRaisesRegex(ValueError, 'unsealed'): bind(self.driver)
        self.seal['guard_revision'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'explicit'): self.prepare()

    def test_result_retarget_refused(self):
        output, _ = self.prepare()
        other = self.result.parent.parent / 'attempt-other'
        other.mkdir()
        with patch.dict(os.environ, FILLER_DRYRUN_RESULT_PATH=str(other / 'native-result.json')):
            with self.assertRaisesRegex(ValueError, 'grant changed'): output()

    def test_official_requires_sealed_private_output(self):
        fixture = fixtures.ExecutionAdmission(); fixture.setUp()
        try:
            seal = dict(fixture.seal, guard_revision=self.binding.REVISION,
                        binding_revision=install.REVISION)
            captured = fixture.gate.capture(seal)
            for root in ('', 'relative', '/tmp', str(self.binding.SCRATCH)):
                seal['execution']['output_root'] = root
                with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'sealed private'):
                    self.binding.prepare(seal, fixture.gate, captured)
            seal['execution']['output_root'] = str(fixture.root)
            output, _ = self.binding.prepare(seal, fixture.gate, captured)
            self.assertEqual(output(), fixture.root)
        finally:
            fixture.doCleanups()

    def test_installer_requires_explicit_execution_and_revision(self):
        for revision, execution in [('other', {}), (self.binding.REVISION, None)]:
            with self.assertRaisesRegex(ValueError, 'current guard requires'):
                install.install(self.root / 'refused', binding_revision=install.REVISION,
                                guard_revision=revision, execution=execution)
        self.assertFalse((self.root / 'refused').exists())

    def test_installed_real_driver_main_uses_current_guard_and_publisher_output(self):
        result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker'],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def worker():
    fixture = fixtures.PublisherSmokeAdmission(); fixture.setUp()
    try:
        execution = dict(fixture.config, sources=fixture.seal['sources'])
        destination = fixture.root / 'installed'
        seal = install.install(destination, binding_revision=install.REVISION,
                               guard_revision='current-guard-v3', execution=execution)
        outer = load(destination / 'supervisor.py', 'installed_outer')
        assert outer.verify()['schema'] == 'kpf18.disabled-supervisor.v3'
        # Use the real custody/contract/provider code with an explicitly private
        # canonical flags directory. No actual grant/provider is accessed.
        admission = load(destination / 'execution_admission.py', 'installed_admission')
        admission.FLAGS = fixture.flags
        # Run the real supervisor capture/import/bind/recheck/main path. Module
        # interception redirects only canonical FLAGS and supplies inert gate/
        # server peers when the actual driver's main is accessed.
        import types
        class PrivateAdmission(types.ModuleType):
            def __getattribute__(self, name):
                if name == 'capture': self.__dict__['FLAGS'] = fixture.flags
                return super().__getattribute__(name)
        class InertDriver(types.ModuleType):
            def __getattribute__(self, name):
                original = super().__getattribute__(name)
                if name != 'main': return original
                def main():
                    driver = self
                    assert driver.OUT == fixture.result.parent
                    assert driver.guard.attempt_root() == fixture.result.parent
                    assert driver.guard.BIN == fixture.native
                    import gpu_witness
                    with patch.object(gpu_witness, 'install'), \
                         patch.object(driver.gate, 'main', return_value=19):
                        # guard.sources is real current admission, not patched.
                        assert original() == 19
                    srv = NS(sampler=NS(n_own_nonzero=1))
                    ctx = NS(client=NS(_req=lambda *a, **kw: (200, {'tokens': [7]})),
                             check_boundary=lambda: None)
                    with patch.object(driver.gate, 'Server', return_value=srv), \
                         patch.object(driver.gate, 'start_steps', return_value=[]), \
                         patch.object(driver.gate, 'stop_step', return_value=None), \
                         patch.object(driver.gate, 'G', return_value={'trunk': list(range(40))}), \
                         patch.object(driver.guard, 'boundary'):
                        steps = driver.item3_smoke(ctx)
                        action = next(v for v in vars(steps[0]).values() if callable(v))
                        action()
                        path = driver.OUT / 'SMOKE-REQUEST.json'
                        assert json.loads(path.read_text())['first_request_ok'] is True
                        try: action()
                        except FileExistsError: pass
                        else: raise AssertionError('overwrote output')
                    Path(fixture.config['stop_file']).touch()
                    try: driver.guard.sources()
                    except ValueError: pass
                    else: raise AssertionError('accepted STOP')
                    return 19
                return main
        original_module = outer.importlib.util.module_from_spec
        def module(spec):
            loaded = original_module(spec)
            if spec.name == '_execution_admission': loaded.__class__ = PrivateAdmission
            if spec.name == '_supervised_driver': loaded.__class__ = InertDriver
            return loaded
        # Installer is deliberately preloaded in this fixture only. Remove its
        # cache entry before the real isolated-entry refusal check.
        sys.modules.pop('install', None)
        with patch.object(sys, 'argv', ['driver.py', 'item3', '--dry-run', '--out', str(fixture.result.parent)]), \
             patch.object(outer.importlib.util, 'module_from_spec', side_effect=module):
            assert outer.run_driver() == 19
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    if sys.argv[1:] == ['--worker']: worker()
    else: unittest.main()
