"""Private installed non-dry main controls; synthetic pins, no model execution."""
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install
import test_execution_admission as fixtures
from test_execution_admission import load, sha


def worker(mode, *, combined=False):
    fixture = fixtures.ExecutionAdmission(); fixture.setUp()
    try:
        root = fixture.root
        out = root / 'output'; out.mkdir()
        base = root / 'private-base'; base.mkdir()
        verifier = load(install.RETAINED / 'verify_receipt.py', 'fixture_verifier')
        models = {}
        for role in ('target', 'drafter'):
            path = root / (role + '.fixture')
            path.write_bytes(b'tiny private stat fixture; never executed')
            models[role] = {'path': str(path), 'sha256': 'a' * 64,
                            'stat_identity': verifier.stat_identity(str(path)),
                            'tensor_count': 1, 'metadata': (
                                dict(verifier.DRAFT_SHAPE) if role == 'drafter'
                                else {'general.architecture': 'private-fixture'})}
        if mode == 'metadata':
            models['drafter']['metadata']['dflash.block_count'] = 6
        receipt = root / 'receipt.json'; receipt.write_text(json.dumps(models))
        manifest = base / 'ORIGINAL-MODELS.json'; manifest.write_text(json.dumps(models))
        framing = root / 'framing.json'
        framing.write_text(json.dumps({'framing_pass': mode != 'framing', 'raw_sha256': 'b' * 64}))
        canonical = root / 'canonical'; canonical.mkdir()
        projection = canonical / 'projection.fixture'; projection.write_text('private projection')
        prepared = []
        for option, leaf in (('--argv-file', 'argv.txt'), ('--prompt-set', 'prompts.jsonl')):
            path = root / leaf; path.write_text('private prepared input\n')
            fixture.seal['sources'][str(path)] = sha(path)
            prepared.extend([option, str(path)])
        inputs = (receipt, manifest, framing, projection)
        fixture.seal['sources'].update({str(p): sha(p) for p in inputs})
        fixture.config.update(output_root=str(out), preload_receipt=str(receipt),
                              enrollment={'framing_result': str(framing),
                                          'canonical_export': str(canonical)})
        destination = root / 'installed'
        install.install(destination, binding_revision=install.REVISION,
                        guard_revision='current-guard-v3',
                        execution=dict(fixture.config, sources=fixture.seal['sources']))
        outer = load(destination / 'supervisor.py', 'private_outer')
        # These fixtures explicitly replace scientific input pins in memory.
        # No historical framing/receipt qualification or production admission.
        class PrivateAdmission(types.ModuleType):
            def __getattribute__(self, name):
                if name == 'capture': self.__dict__['FLAGS'] = fixture.flags
                return super().__getattribute__(name)
        class PrivateBinding(types.ModuleType):
            def __getattribute__(self, name):
                if name == 'prepare':
                    self.__dict__.update(FRAMING_SHA=sha(framing), FRAMING_RAW_SHA='b' * 64,
                                         PROJECTION={'projection.fixture': sha(projection)})
                return super().__getattribute__(name)
        calls = []
        class PrivateDriver(types.ModuleType):
            def __getattribute__(self, name):
                original = super().__getattribute__(name)
                if name != 'main': return original
                def main():
                    driver = self
                    driver.BASE = base
                    import preload_integration
                    import gpu_witness
                    # Keep actual verify(), load_preload_models(), both stat
                    # checks, enrollment, current boundary and main unchanged.
                    expected = '0' * 64 if mode == 'digest' else sha(receipt)
                    if mode == 'stat':
                        Path(models['target']['path']).write_bytes(b'changed stat fixture')
                    if combined:
                        if combined == 'context':
                            from test_combined_context import combined_main
                        else:
                            from test_combined_entry import combined_main
                        return combined_main(driver, original, fixture, out, mode,
                                             preload_integration, gpu_witness, expected, calls)
                    def gate_main():
                        calls.append('gate')
                        assert driver.PRELOAD_MODELS['draft_cache_shape']['draft_swa_layers'] == 5
                        assert driver.gate.ITEMS[3] is driver.item3
                        assert driver.guard.attempt_root() == out
                        return 23
                    with patch.object(preload_integration, 'EXPECTED_RECEIPT_SHA256', expected), \
                         patch.object(gpu_witness, 'install', side_effect=lambda g: calls.append('witness')), \
                         patch.object(driver.gate, 'main', side_effect=gate_main), \
                         patch.object(driver.guard.shutil, 'disk_usage', return_value=types.SimpleNamespace(free=1024**4)):
                        if mode == 'pass':
                            assert original() == 23
                            recorded = json.loads((out / 'PRELOAD-MODEL-IDENTITY.json').read_text())
                            assert recorded == {role: driver.PRELOAD_MODELS[role] for role in models}
                            assert calls == ['witness', 'gate'], calls
                        else:
                            expected_error = {'digest': 'receipt digest mismatch',
                                              'stat': 'stat tuple drift',
                                              'metadata': 'metadata dflash.block_count mismatch'}[mode]
                            try: original()
                            except verifier.VerificationError:
                                raise AssertionError('unexpected fixture verifier class')
                            except Exception as error:
                                # Exception originates from the real retained module.
                                assert type(error).__name__ == 'VerificationError', repr(error)
                                assert expected_error in str(error), str(error)
                            else: raise AssertionError('accepted invalid preload')
                            assert not calls, calls
                            assert not (out / 'PRELOAD-MODEL-IDENTITY.json').exists()
                        return 0
                return main
        original_module = outer.importlib.util.module_from_spec
        def module(spec):
            loaded = original_module(spec)
            cls = {'_execution_admission': PrivateAdmission,
                   '_kpf_current_binding': PrivateBinding,
                   '_supervised_driver': PrivateDriver}.get(spec.name)
            if cls: loaded.__class__ = cls
            return loaded
        sys.modules.pop('install', None)
        argv = ['driver.py', 'item3', '--out', str(out)]
        if combined:
            argv.extend(['--fork-bin', str(fixture.native), *prepared])
            if mode == 'prefix': argv.extend(['--launch-prefix', '/bin/false'])
            if mode == 'server': argv[argv.index('--fork-bin') + 1] = str(root / 'foreign')
        with patch.object(sys, 'argv', argv), \
             patch.object(outer.importlib.util, 'module_from_spec', side_effect=module):
            assert outer.run_driver() == 0
    finally:
        fixture.doCleanups()


class InstalledNondryEntry(unittest.TestCase):
    def invoke(self, mode):
        result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker', mode],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_main_retained_verifier_and_identity_output(self): self.invoke('pass')
    def test_digest_refusal_precedes_output_witness_and_gate(self): self.invoke('digest')
    def test_stat_refusal_precedes_output_witness_and_gate(self): self.invoke('stat')
    def test_metadata_refusal_precedes_output_witness_and_gate(self): self.invoke('metadata')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker': worker(sys.argv[2])
    else: unittest.main()
