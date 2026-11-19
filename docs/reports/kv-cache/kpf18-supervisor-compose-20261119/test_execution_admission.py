"""Private grant/provider fixtures only; no official lock or model is touched."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SCRATCH = '/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ExecutionAdmission(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.flags = self.root / 'flags'
        (self.flags / 'grants').mkdir(parents=True)
        self.gate = load(HERE / 'execution_admission.py', 'admission_test_subject')
        self.gate.FLAGS = self.flags
        self.native = self.root / 'native-artifact'
        self.native.write_bytes(b'synthetic native input, never executed')
        self.provider = self.root / 'synthetic_provider.py'
        self.provider.write_text('from pathlib import Path\n'
                                 f'ORCHESTRATOR = Path({str(self.root)!r})\n'
                                 "SOURCES = ('native-artifact',)\n"
                                 'def capture(row, sources):\n'
                                 '    assert row == "synthetic-row"\n'
                                 '    return {"row_id": row}\n'
                                 'def recheck(witness):\n'
                                 '    assert witness["row_id"] == "synthetic-row"\n')
        artifacts = {role: str(self.native) for role in self.gate.ROLES}
        artifacts['python'] = str(Path('/proc/self/exe').resolve())
        self.config = {'row_id': 'synthetic-row', 'stop_file': str(self.root / 'STOP'),
                       'window_s': 9000, 'artifacts': artifacts, 'provider': str(self.provider),
                       'provider_sources': {str(self.native): sha(self.native)}}
        self.seal = {'execution': self.config, 'sources': {
            str(p): sha(p) for p in (self.native, self.provider, Path(artifacts['python']))}}
        self.grant = self.flags / 'grants/synthetic-row.grant'
        self.raw = ('regions=mi210_0,184-187 start=2030-01-01T00:00Z '
                    'end=2030-01-01T02:30Z holds=gpu-quiet,t184,t185,t186,t187\n')
        self.grant.write_text(self.raw)
        self.end = self.gate.epoch('2030-01-01T02:30Z')
        self.env = {'FILLER_ID': 'synthetic-row', 'FILLER_STOPFILE': self.config['stop_file'],
                    'FILLER_CPUS': '184-187', 'FILLER_THREADS': '4', 'FILLER_NEEDGPU': '1',
                    'FILLER_END': str(self.end), 'FILLER_DEADLINE': str(self.end - 90)}
        for context in (patch.dict(os.environ, self.env, clear=True),
                        patch.object(self.gate.time, 'time', return_value=self.end - 100),
                        patch.object(self.gate.os, 'sched_getaffinity', return_value={184,185,186,187})):
            context.start()
            self.addCleanup(context.stop)

    def test_current_grant_and_retained_provider_recheck(self):
        witness = self.gate.capture(self.seal)
        self.gate.recheck(self.seal, witness)

    def test_explicit_keeper_cpu_field(self):
        self.grant.write_text(self.raw.rstrip() + ' cpus=184-187\n')
        self.assertEqual(self.gate.contract(self.config), self.grant.read_text())

    def test_custody_missing_unsealed_and_drift_refused(self):
        for mode in ('missing', 'unsealed', 'drift', 'interpreter', 'provider-inventory'):
            seal = copy.deepcopy(self.seal)
            with self.subTest(mode=mode):
                if mode == 'missing': seal.pop('execution')
                if mode == 'unsealed': seal['sources'].pop(str(self.native))
                if mode == 'drift': seal['sources'][str(self.native)] = '0' * 64
                if mode == 'interpreter': seal['execution']['artifacts']['python'] = str(self.native)
                if mode == 'provider-inventory': seal['execution']['provider_sources'][str(self.native)] = '0' * 64
                with self.assertRaises(ValueError): self.gate.capture(seal)

    def test_weights_never_hashed_inside_execution(self):
        seal = copy.deepcopy(self.seal)
        seal['sources'][str(self.root / 'absent.gguf')] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'model weights forbidden'):
            self.gate.custody(seal)

    def test_smoke_direct_redirect_and_wrong_row_refused(self):
        for name, value in (('FILLER_SMOKE','1'), ('FILLER_DRYRUN','1'), ('FILLER_DIRECT','1'),
                            ('FILLER_ID','foreign'), ('FILLER_FLAGS_DIR','/private'),
                            ('FILLER_GRANTS_DIR','/private'), ('FILLER_END','0'),
                            ('FILLER_STOPFILE','/foreign/STOP'), ('FILLER_THREADS','1'),
                            ('FILLER_CPUS','184'), ('FILLER_NEEDGPU','0')):
            with self.subTest(name=name), patch.dict(os.environ, {name:value}):
                with self.assertRaises(ValueError): self.gate.contract(self.config)

    def test_grant_schema_refusals(self):
        for raw in (self.raw + 'end=2030-01-01T02:30Z', self.raw + 'extra=x',
                    self.raw.replace('holds=', 'old='), self.raw.replace('gpu-quiet', 'q0'),
                    self.raw.replace('mi210_0,', ''), self.raw.replace('02:30Z', '02:29Z'),
                    self.raw + 'lock=0-95', self.raw + 'cpus=184-193',
                    self.raw + 'cpus=184-187,184'):
            with self.subTest(raw=raw):
                self.grant.write_text(raw)
                with self.assertRaises(ValueError): self.gate.contract(self.config)

    def test_future_and_expired_grants_refused(self):
        for now in (self.end - 9001, self.end - 90, self.end):
            with self.subTest(now=now), patch.object(self.gate.time, 'time', return_value=now):
                with self.assertRaises(ValueError): self.gate.contract(self.config)

    def test_affinity_escape_refused(self):
        with patch.object(self.gate.os, 'sched_getaffinity', return_value={183,184}):
            with self.assertRaisesRegex(ValueError, 'affinity'): self.gate.contract(self.config)

    def test_stop_terminal_and_active_hold_refused(self):
        for path in (Path(self.config['stop_file']), self.grant.with_suffix('.ended'),
                     self.grant.with_suffix('.complete'), self.flags/'HOLD_ADMISSIONS'):
            with self.subTest(path=path):
                path.touch()
                try:
                    with self.assertRaises(ValueError): self.gate.contract(self.config)
                finally: path.unlink()
        (self.flags / 'HOLD_ADMISSIONS.lifted').touch()
        self.gate.contract(self.config)

    def test_symlinked_grant_and_dangling_stop_refused(self):
        target = self.root / 'grant-target'
        target.write_text(self.raw)
        self.grant.unlink()
        self.grant.symlink_to(target)
        with self.assertRaises(OSError): self.gate.contract(self.config)
        self.grant.unlink()
        self.grant.write_text(self.raw)
        Path(self.config['stop_file']).symlink_to(self.root / 'absent')
        with self.assertRaises(ValueError): self.gate.contract(self.config)

    def test_preloaded_provider_and_missing_provider_inventory_refused(self):
        with patch.dict(sys.modules, {'src.runtime': types.ModuleType('src.runtime')}):
            with self.assertRaisesRegex(ValueError, 'preloaded official'):
                self.gate.capture(self.seal)
        seal = copy.deepcopy(self.seal)
        seal['execution']['provider_sources'] = {}
        with self.assertRaisesRegex(ValueError, 'incomplete official'):
            self.gate.capture(seal)

    def test_provider_refusal_propagates(self):
        self.provider.write_text(self.provider.read_text().replace(
            'assert row == "synthetic-row"', 'raise ValueError("writer not held")'))
        self.seal['sources'][str(self.provider)] = sha(self.provider)
        with self.assertRaisesRegex(ValueError, 'writer not held'): self.gate.capture(self.seal)

    def test_grant_and_source_changes_refused_at_recheck(self):
        witness = self.gate.capture(self.seal)
        self.grant.write_text(self.raw.rstrip() + ' cpus=184-187\n')
        with self.assertRaisesRegex(ValueError, 'grant changed'): self.gate.recheck(self.seal, witness)
        self.grant.write_text(self.raw)
        self.native.write_bytes(b'drift')
        with self.assertRaisesRegex(ValueError, 'source drift'): self.gate.recheck(self.seal, witness)

    def test_actual_supervisor_order_and_refusal_before_driver_import(self):
        subject = load(HERE/'supervisor.py', 'supervisor_test_subject')
        driver = self.root / 'driver.py'
        marker = self.root / 'import-marker'
        driver.write_text('from pathlib import Path\n'
                          f'Path({str(marker)!r}).touch()\n'
                          'def main(): return 23\n')
        seal = dict(self.seal, admission=str(HERE/'execution_admission.py'), driver=str(driver))
        seal['sources'] = dict(seal['sources'], **{str(p):sha(p) for p in (
            driver, HERE/'execution_admission.py')})
        with patch.object(subject, 'verify', return_value=seal), \
             patch.object(subject, 'run', side_effect=lambda fn: fn()):
            with patch.dict(os.environ, FILLER_FLAGS_DIR=str(self.flags)):
                with self.assertRaisesRegex(ValueError, 'redirected official'):
                    subject.run_driver()
            self.assertFalse(marker.exists())

    def test_actual_supervisor_capture_import_recheck_main_order(self):
        subject = load(HERE/'supervisor.py', 'supervisor_test_subject')
        driver = self.root / 'driver.py'
        imported, entered = self.root/'imported', self.root/'main-entered'
        driver.write_text('from pathlib import Path\n'
                          f'Path({str(imported)!r}).touch()\n'
                          f'def main():\n    Path({str(entered)!r}).touch()\n    return 23\n')
        seal = dict(self.seal, admission=str(HERE/'execution_admission.py'), driver=str(driver))
        seal['sources'] = dict(seal['sources'], **{str(p):sha(p) for p in (
            driver, HERE/'execution_admission.py')})
        # Redirect only the canonical namespace of the actual loaded admission
        # module. All custody/contract/provider checks remain its real functions.
        flags = self.flags
        class PrivateNamespace(types.ModuleType):
            def __getattribute__(self, name):
                if name == 'capture': self.__dict__['FLAGS'] = flags
                return super().__getattribute__(name)
        original = subject.importlib.util.module_from_spec
        def module(spec):
            loaded = original(spec)
            if spec.name == '_execution_admission': loaded.__class__ = PrivateNamespace
            return loaded
        with patch.object(subject, 'verify', return_value=seal), \
             patch.object(subject, 'run', side_effect=lambda fn: fn()), \
             patch.object(subject.importlib.util, 'module_from_spec', side_effect=module):
            self.assertEqual(subject.run_driver(), 23)
            self.assertTrue(imported.is_file() and entered.is_file())
            imported.unlink(); entered.unlink()
            # Drift during driver import must prevent main, even after the
            # first admission succeeded. The driver itself is freshly sealed.
            driver.write_text(driver.read_text().replace('def main():',
                f'Path({str(self.native)!r}).write_bytes(b"drift")\ndef main():'))
            seal['sources'][str(driver)] = sha(driver)
            with self.assertRaisesRegex(ValueError, 'source drift'):
                subject.run_driver()
            self.assertTrue(imported.is_file())
            self.assertFalse(entered.exists())



class PublisherSmokeAdmission(unittest.TestCase):
    def setUp(self):
        ExecutionAdmission.setUp(self)
        self.config['mode'] = 'publisher-smoke'
        self.dry = self.flags / 'dryrun' / 'synthetic-row'
        (self.dry / 'grants').mkdir(parents=True)
        (self.dry / 'state').mkdir()
        self.result = self.dry / 'native-attempts/attempt-synthetic/native-result.json'
        self.result.parent.mkdir(parents=True)
        self.grant = self.dry / 'grants/synthetic-row.grant'
        self.raw = self.raw.rstrip() + (' schema=epyc.rowflow.dryrun-grant.v1'
                                       ' id=synthetic-row kind=rowflow-dryrun'
                                       ' admission_class=diagnostic\n')
        self.grant.write_text(self.raw)
        patcher = patch.dict(os.environ, {
            'FILLER_SMOKE': '1', 'FILLER_DRYRUN': '1',
            'FILLER_FLAGS_DIR': str(self.flags), 'FILLER_GRANTS_DIR': str(self.dry / 'grants'),
            'FILLER_DRYRUN_DIR': str(self.dry), 'FILLER_STATE_DIR': str(self.dry / 'state'),
            'FILLER_DRYRUN_RESULT_PATH': str(self.result)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_capture_and_recheck_use_publisher_grant_and_same_provider(self):
        witness = self.gate.capture(self.seal)
        self.gate.recheck(self.seal, witness)
        # Smoke never modifies the official grant or creates a result.
        self.assertEqual((self.flags/'grants/synthetic-row.grant').read_text(),
                         self.raw.split(' schema=')[0] + '\n')
        self.assertFalse(self.result.exists())

    def test_mode_cannot_be_selected_by_environment(self):
        self.config.pop('mode')
        with self.assertRaises(ValueError): self.gate.capture(self.seal)
        self.config['mode'] = 'unsupported'
        with self.assertRaisesRegex(ValueError, 'unknown sealed'): self.gate.capture(self.seal)

    def test_missing_or_redirected_publisher_context_refused(self):
        changes = [('FILLER_SMOKE', '0'), ('FILLER_DRYRUN', '0'),
                   ('FILLER_FLAGS_DIR', '/foreign'), ('ROWFLOW_FLAGS', '/foreign'),
                   ('FILLER_GRANTS_DIR', str(self.flags/'grants')),
                   ('FILLER_DRYRUN_DIR', str(self.flags/'dryrun/other-row')),
                   ('FILLER_STATE_DIR', str(self.flags/'state')),
                   ('FILLER_ID', 'other-row'), ('FILLER_PREFLIGHT', '1'),
                   ('FILLER_DIRECT', '1'), ('KPF_SMOKE', '1')]
        for name, value in changes:
            with self.subTest(name=name), patch.dict(os.environ, {name: value}):
                with self.assertRaises(ValueError): self.gate.contract(self.config)
        for name in ('FILLER_FLAGS_DIR', 'FILLER_GRANTS_DIR', 'FILLER_DRYRUN_DIR', 'FILLER_STATE_DIR'):
            with self.subTest(missing=name), patch.dict(os.environ):
                del os.environ[name]
                with self.assertRaises(ValueError): self.gate.contract(self.config)

    def test_official_or_foreign_dryrun_grant_refused(self):
        for raw in (self.raw.split(' schema=')[0],
                    self.raw.replace('id=synthetic-row', 'id=foreign-row'),
                    self.raw.replace('kind=rowflow-dryrun', 'kind=official'),
                    self.raw.replace('dryrun-grant.v1', 'dryrun-grant.v0'),
                    self.raw + ' extra=unknown', self.raw + ' id=synthetic-row'):
            with self.subTest(raw=raw):
                self.grant.write_text(raw)
                with self.assertRaises(ValueError): self.gate.contract(self.config)

    def test_exact_four_affinity_and_deadline_required(self):
        for affinity in ({184,185}, {184,185,186,188}):
            with patch.object(self.gate.os, 'sched_getaffinity', return_value=affinity):
                with self.assertRaisesRegex(ValueError, 'affinity'): self.gate.contract(self.config)
        self.grant.write_text(self.raw.replace('184-187', '184-185'))
        with patch.dict(os.environ, FILLER_CPUS='184-185', FILLER_THREADS='2'), \
             patch.object(self.gate.os, 'sched_getaffinity', return_value={184,185}):
            with self.assertRaisesRegex(ValueError, 'affinity'): self.gate.contract(self.config)
        self.grant.write_text(self.raw)
        with patch.object(self.gate.time, 'time', return_value=self.end - 90):
            with self.assertRaisesRegex(ValueError, 'deadline'): self.gate.contract(self.config)

    def test_result_isolation_and_context_drift_before_main(self):
        for path in (self.root/'official-result.json', self.dry/'native-result.json',
                     self.flags/'dryrun/foreign/native-attempts/attempt-x/native-result.json'):
            with self.subTest(path=path), patch.dict(os.environ, FILLER_DRYRUN_RESULT_PATH=str(path)):
                with self.assertRaisesRegex(ValueError, 'isolated native result'):
                    self.gate.contract(self.config)
        witness = self.gate.capture(self.seal)
        new = self.result.parent.parent/'attempt-other/native-result.json'
        new.parent.mkdir()
        with patch.dict(os.environ, FILLER_DRYRUN_RESULT_PATH=str(new)):
            with self.assertRaisesRegex(ValueError, 'grant changed'):
                self.gate.recheck(self.seal, witness)
        self.result.symlink_to(self.root/'absent')
        with self.assertRaises(ValueError): self.gate.contract(self.config)

    def test_stop_terminals_holds_symlinks_and_provider_loss_refused(self):
        ExecutionAdmission.test_stop_terminal_and_active_hold_refused(self)
        for name in ('stop', 'ended', 'complete'):
            path = self.dry/name
            path.touch()
            try:
                with self.assertRaises(ValueError): self.gate.contract(self.config)
            finally: path.unlink()
        ExecutionAdmission.test_symlinked_grant_and_dangling_stop_refused(self)
        Path(self.config['stop_file']).unlink()
        ExecutionAdmission.test_provider_refusal_propagates(self)

    def test_provider_loss_and_symlinked_namespace_refused(self):
        lost = self.root/'writer-lost'
        self.provider.write_text(self.provider.read_text().replace(
            'assert witness["row_id"] == "synthetic-row"',
            f'assert not Path({str(lost)!r}).exists(), "writer lost"'))
        self.seal['sources'][str(self.provider)] = sha(self.provider)
        witness = self.gate.capture(self.seal)
        lost.touch()
        with self.assertRaisesRegex(AssertionError, 'writer lost'):
            self.gate.recheck(self.seal, witness)
        lost.unlink()
        state = self.dry/'state'
        state.rmdir()
        state.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'unsafe rowflow directory'):
            self.gate.contract(self.config)

    def test_actual_supervisor_smoke_capture_import_recheck_main_and_drift(self):
        ExecutionAdmission.test_actual_supervisor_capture_import_recheck_main_order(self)

    def test_actual_supervisor_refuses_bad_context_before_import(self):
        ExecutionAdmission.test_actual_supervisor_order_and_refusal_before_driver_import(self)


if __name__ == '__main__': unittest.main()
