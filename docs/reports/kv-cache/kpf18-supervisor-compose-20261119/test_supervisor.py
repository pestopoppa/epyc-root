import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def worker(destination, mode):
    supervisor = load(destination / 'supervisor.py', 'supervisor')
    events = []
    pid = None
    def entry():
        nonlocal pid
        events.append('driver-start')
        rd, wr = os.pipe()
        pid = os.fork()
        if not pid:
            os.close(rd)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            os.write(wr, b'R')
            os.close(wr)
            while True: signal.pause()
        os.close(wr)
        with os.fdopen(rd, 'rb') as stream:
            assert stream.read(1) == b'R'
        try:
            if mode == 'exception': raise ValueError('entry-error')
            if mode == 'exit': raise SystemExit(3)
            return 7
        finally:
            assert Path('/proc', str(pid)).exists()
            events.extend(['server-stop', 'partial-finish'])
    if mode == 'preexisting':
        child = subprocess.Popen([sys.executable, '-c', 'import signal;signal.pause()'])
        fd = os.pidfd_open(child.pid)
        try:
            try: supervisor.run(lambda: events.append('BAD'))
            except RuntimeError as exc: assert 'preexisting children' in str(exc)
            else: raise AssertionError('accepted preexisting child')
            assert not events and child.poll() is None
        finally:
            signal.pidfd_send_signal(fd, signal.SIGKILL)
            os.close(fd)
            child.wait(timeout=5)
    elif mode == 'threaded':
        import threading
        ready, release = threading.Event(), threading.Event()
        def peer():
            ready.set()
            release.wait(5)
        thread = threading.Thread(target=peer)
        thread.start(); ready.wait(5)
        try:
            try: supervisor.run(lambda: events.append('BAD'))
            except RuntimeError as exc: assert 'single-threaded' in str(exc)
            else: raise AssertionError('accepted threads')
            assert not events
        finally:
            release.set(); thread.join(5)
    elif mode == 'preloaded':
        import types
        sys.modules['composition'] = types.ModuleType('composition')
        try:
            supervisor.run_driver()
        except ValueError as exc:
            assert 'preloaded driver binding' in str(exc)
        else:
            raise AssertionError('accepted preloaded binding')
    elif mode == 'driver':
        # Transform the sealed existing fixture only in memory. Its actual
        # full imported item3/controller/gate calls now cross the supervisor.
        path = HERE.parent / 'kpf18-driver-terminal-compose-20261119/test_composition.py'
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == '2a7700938e25b8508e571bf4419adc2b3163a6bb394c31d853420cebd1f3d057'
        text = raw.decode()
        assert text.count('rc = gate.main()') == 1
        text = text.replace('rc = gate.main()', 'rc = outer.run(gate.main)')
        # The successor driver is a symlink to immutable predecessor bytes.
        # Exercise drift on our new launcher rather than the inherited driver.
        assert text.count("path = output / 'driver.py'") == 1
        text = text.replace("path = output / 'driver.py'", "path = output / 'launch.sh'")
        # Fixture imports its own compose module; avoid an inherited module.
        sys.path.insert(0, str(path.parent))
        namespace = {'__name__': 'supervised_fixture', '__file__': str(path), 'outer': supervisor}
        exec(compile(text, str(path), 'exec'), namespace)
        assert namespace['worker'](destination) == 0
    else:
        try:
            result = supervisor.run(entry)
        except ValueError as exc:
            assert mode == 'exception' and str(exc) == 'entry-error'
        except SystemExit as exc:
            assert mode == 'exit' and exc.code == 3
        else:
            assert mode == 'normal' and result == 7
        assert events == ['driver-start', 'server-stop', 'partial-finish']
        assert pid and not Path('/proc', str(pid)).exists()
    print('SUPERVISOR-PASS', mode)


class Supervisor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=install.SCRATCH)
        cls.output = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        cls.destination = Path(cls.temp.name) / 'supervisor'
        install.install(cls.destination)
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        cls.output.cleanup()
    def case(self, mode):
        result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker',
                                 str(self.destination), mode], capture_output=True, text=True, timeout=20,
                                env=dict(os.environ, KPF_COMPOSITION_OUTPUT=self.output.name,
                                         PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('SUPERVISOR-PASS ' + mode, result.stdout)
    def test_return_drains_after_driver_finalizers(self): self.case('normal')
    def test_exception_drains_and_preserves_error(self): self.case('exception')
    def test_systemexit_drains_and_preserves_rc(self): self.case('exit')
    def test_preexisting_child_is_refused_untouched(self): self.case('preexisting')
    def test_threads_refused_before_entry(self): self.case('threaded')
    def test_actual_full_imported_driver_cell(self): self.case('driver')
    def test_driver_refuses_preloaded_binding(self): self.case('preloaded')
    def test_relocated_digest_mismatch_refused(self):
        from unittest.mock import patch
        target = HERE.parent / 'kpf18-g3-owned-drain-20261104/adapter.py'
        original = install.digest
        def changed(path):
            return '0' * 64 if path == target else original(path)
        destination = Path(self.temp.name) / 'bad-relocation'
        with patch.object(install, 'digest', changed):
            with self.assertRaisesRegex(ValueError, 'inherited source drift'):
                install.install(destination)
        self.assertFalse(destination.exists())
    def test_disabled_entries(self):
        for argv in (['bash', str(self.destination / 'launch.sh')],
                     [sys.executable, '-I', '-B', str(self.destination / 'supervisor.py')]):
            self.assertEqual(subprocess.run(argv, capture_output=True, timeout=5).returncode, 78)
    def test_source_drift_refused_before_entry(self):
        path = self.destination / 'launch.sh'
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b'# drift\n')
            mod = load(self.destination / 'supervisor.py', 'drift')
            with self.assertRaisesRegex(ValueError, 'source drift'):
                mod.run(lambda: self.fail('entry ran'))
        finally: path.write_bytes(raw)
    def test_incomplete_refused(self):
        path = self.destination / 'INCOMPLETE'
        path.touch()
        try:
            with self.assertRaisesRegex(ValueError, 'incomplete supervisor'):
                load(self.destination / 'supervisor.py', 'incomplete').verify()
        finally: path.unlink()
    def test_existing_destination_refused(self):
        with self.assertRaises(ValueError): install.install(self.destination)


class DependencyBinding(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        # The test runner imports the installer; the isolated production entry
        # must not. Restore the runner's module dictionary after each control.
        modules = patch.dict(sys.modules)
        modules.start()
        self.addCleanup(modules.stop)
        sys.modules.pop('install', None)

    def subject(self):
        # Unit controls use a source inventory, not a fabricated admission.
        # They need no installed runtime or model bytes.
        mod = load(HERE / 'supervisor.py', 'dependency_gate')
        sources = json.loads((install.BASE / 'manifest.json').read_text())['sources']
        return mod, {'sources': sources, 'driver': str(install.BASE / 'driver.py')}

    def test_preloaded_native_peers_refused_before_import(self):
        from unittest.mock import patch
        import types
        supervisor, seal = self.subject()
        for name in ('guard', 'controller', 'native_group3', 'pipeline', 'kpf18_gate',
                     'adapter', 'driver_boundary', 'foreign.controller'):
            with self.subTest(name=name):
                with patch.dict(sys.modules, {name: types.ModuleType(name)}):
                    with patch.object(supervisor, 'run', side_effect=lambda entry: entry()), \
                         patch.object(supervisor, 'verify', return_value=seal):
                        with patch.object(supervisor.importlib.util, 'spec_from_file_location',
                                          side_effect=AssertionError('driver import reached')):
                            with self.assertRaisesRegex(ValueError, 'preloaded driver binding'):
                                supervisor.run_driver()
                self.assertNotIn(name, sys.modules)
        self.assertIsNone(supervisor.refuse_preloaded_dependencies(seal))

    def test_matching_origin_still_refused(self):
        from unittest.mock import patch
        import types
        supervisor, seal = self.subject()
        peer = types.ModuleType('controller')
        peer.__file__ = next(name for name in seal['sources']
                             if name.endswith('/controller.py'))
        with patch.dict(sys.modules, controller=peer):
            with self.assertRaisesRegex(ValueError, 'controller'):
                supervisor.refuse_preloaded_dependencies(seal)


    def test_unrelated_loaded_module_permitted(self):
        from unittest.mock import patch
        import types
        supervisor, seal = self.subject()
        with patch.dict(sys.modules, unrelated_peer=types.ModuleType('unrelated_peer')):
            self.assertIsNone(supervisor.refuse_preloaded_dependencies(seal))

    def test_inventory_extension_protects_new_peer(self):
        from unittest.mock import patch
        import types
        supervisor, seal = self.subject()
        seal = dict(seal, sources={**seal['sources'], '/sealed/new_native_peer.py': 'unused'})
        with patch.dict(sys.modules, new_native_peer=types.ModuleType('new_native_peer')):
            with self.assertRaisesRegex(ValueError, 'new_native_peer'):
                supervisor.refuse_preloaded_dependencies(seal)


class CallableBinding(unittest.TestCase):
    """Exercise the real callable entry without the reclaimed R9 runtime."""

    def case(self, foreign_peer):
        with tempfile.TemporaryDirectory(dir=install.SCRATCH) as temporary:
            root = Path(temporary)
            subject = root / 'supervisor.py'
            subject.write_bytes((HERE / 'supervisor.py').read_bytes())
            driver = root / 'driver.py'
            marker = root / 'driver-entered'
            driver.write_text('from pathlib import Path\n'
                              f'def main():\n    Path({str(marker)!r}).touch()\n    return 19\n')
            sources = {str(path): install.digest(path)
                       for path in (subject, driver, install.HELPER)}
            (root / 'manifest.json').write_text(json.dumps({
                'runtime_dispatch': False, 'sources': sources,
                'helper': str(install.HELPER), 'driver': str(driver)}))
            code = '''
import importlib.util
from pathlib import Path
import sys
import types
spec = importlib.util.spec_from_file_location('supervisor', sys.argv[1])
subject = importlib.util.module_from_spec(spec)
sys.modules['supervisor'] = subject
spec.loader.exec_module(subject)
if sys.argv[2] == 'foreign':
    peer = types.ModuleType('foreign.supervisor')
    peer.__file__ = subject.__file__
    sys.modules['foreign.supervisor'] = peer
    try:
        subject.run_driver()
    except ValueError as exc:
        assert 'foreign.supervisor' in str(exc), str(exc)
    else:
        raise AssertionError('foreign same-origin object accepted')
    assert not Path(sys.argv[3]).exists()
else:
    assert subject.run_driver() == 19
    assert Path(sys.argv[3]).is_file()
print('CALLABLE-BINDING-PASS')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code,
                                     str(subject), 'foreign' if foreign_peer else 'self',
                                     str(marker)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('CALLABLE-BINDING-PASS', result.stdout)

    def test_registered_supervisor_can_call_driver(self):
        self.case(False)

    def test_same_origin_foreign_supervisor_refused_before_driver(self):
        self.case(True)

if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']: worker(Path(sys.argv[2]), sys.argv[3])
    else: unittest.main()
