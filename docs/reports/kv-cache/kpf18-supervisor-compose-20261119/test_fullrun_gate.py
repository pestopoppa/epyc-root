"""Current official gate routing; private admission and inert item3 work only."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install
import test_execution_admission as fixtures
from test_execution_admission import load, sha


class FullrunGate(unittest.TestCase):
    def test_installed_official_gate_routing(self):
        for mode in ('valid', 'empty-prefix', 'prefix', 'command', 'write', 'out',
                     'duplicate', 'server', 'input', 'drift', 'stop', 'smoke', 'failure',
                     'claim-override', 'provider-loss'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker', mode],
                                        capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def worker(mode):
    fixture = fixtures.ExecutionAdmission(); fixture.setUp()
    try:
        output = fixture.root / 'output'; output.mkdir()
        fixture.config['output_root'] = str(output)
        prepared = []
        for option, leaf in (('--argv-file', 'argv.txt'), ('--prompt-set', 'prompts.jsonl')):
            path = fixture.root / leaf; path.write_text('private prepared input\n')
            fixture.seal['sources'][str(path)] = sha(path)
            prepared.extend([option, str(path)])
        destination = fixture.root / 'installed'
        install.install(destination, binding_revision=install.REVISION,
                        guard_revision='current-guard-v3',
                        execution=dict(fixture.config, sources=fixture.seal['sources']))
        outer = load(destination / 'supervisor.py', 'fullrun_gate_outer')
        captured = {}
        class PrivateAdmission(ModuleType):
            def __getattribute__(self, name):
                if name == 'capture':
                    self.__dict__['FLAGS'] = fixture.flags
                    original = super().__getattribute__(name)
                    def capture(seal):
                        result = original(seal)
                        captured['provider'] = result[0]
                        return result
                    return capture
                return super().__getattribute__(name)
        class DriverControl(ModuleType):
            def __getattribute__(self, name):
                original = super().__getattribute__(name)
                if name != 'main': return original
                def main():
                    driver = self
                    import gpu_witness
                    wrapped = driver.gate.main
                    visited, worked = [], []
                    def build_ctx(args, items):
                        visited.append(True)
                        assert items == [3] and args.out == str(output)
                        assert args.fork_bin == str(fixture.native) and args.launch_prefix == ''
                        assert driver.gate.ITEMS[3] is driver.item3
                        assert args.no_device_claim == 'current captured keeper GPU writer; rechecked before gate entry'
                        return NS(args=args, own_children=[], open_runs=[], preempted=False), [], []
                    def item3(ctx):
                        def work():
                            worked.append(True)
                            if mode == 'failure': raise RuntimeError('inert work failure')
                        return [driver.gate.Step('private full-run work', 0, work)]
                    def entry():
                        # Main's dry prerequisite branch is intentional. Exercise
                        # actual parser/loop with inert item3, without enrollment
                        # receipts, native server, controller or device claim.
                        args = ['gate.py', 'item3', '--out', str(output),
                                '--fork-bin', str(fixture.native), *prepared]
                        additions = {'empty-prefix': ['--launch-prefix', ''],
                                     'prefix': ['--launch-prefix', '/bin/false'],
                                     'claim-override': ['--no-device-claim', 'caller says so'],
                                     'write': ['--argv-out', str(fixture.root / 'escape')],
                                     'duplicate': ['--out', str(output)]}
                        args.extend(additions.get(mode, []))
                        if mode == 'command': args[1] = 'make-argv-file'
                        for key, option in (('out', '--out'), ('server', '--fork-bin'),
                                            ('input', '--prompt-set')):
                            if mode == key: args[args.index(option) + 1] = str(fixture.root / 'foreign')
                        if mode == 'drift': Path(prepared[-1]).write_text('drift')
                        if mode == 'stop': Path(fixture.config['stop_file']).touch()
                        if mode == 'smoke': os.environ['KPF_SMOKE'] = '1'
                        if mode == 'provider-loss':
                            provider = captured['provider']
                            provider.recheck = lambda witness: (_ for _ in ()).throw(ValueError('provider lost'))
                        positive = mode in ('valid', 'empty-prefix', 'failure')
                        with patch.object(sys, 'argv', args):
                            caller = sys.argv
                            try:
                                rc = wrapped()
                            except ValueError as error:
                                assert not positive, error
                                reasons = {'prefix': 'launch prefix', 'command': 'requires item3',
                                           'write': 'unsupported', 'out': 'output changed',
                                           'duplicate': 'unsupported', 'server': 'server mismatch',
                                           'input': 'sealed prepared inputs', 'drift': 'source drift',
                                           'stop': 'STOP', 'smoke': 'smoke selection',
                                           'claim-override': 'unsupported', 'provider-loss': 'provider lost'}
                                assert reasons[mode] in str(error), str(error)
                            else:
                                assert positive, ('accepted invalid entry', mode)
                                assert rc == (4 if mode == 'failure' else 0), rc
                            assert sys.argv is caller and caller == args
                        if positive:
                            assert visited == [True] and worked == [True]
                            meta = json.loads((output / 'run_meta.json').read_text())
                            assert meta['items'] == [3] and meta['args']['launch_prefix'] == ''
                            assert len(list((output / 'done').iterdir())) == (0 if mode == 'failure' else 1)
                        else:
                            assert visited == [] and worked == []
                            assert list(output.iterdir()) == []
                            assert not (fixture.root / 'escape').exists()
                        return 31
                    with patch.object(driver, 'item3', side_effect=item3), \
                         patch.object(driver.gate, 'build_ctx', side_effect=build_ctx), \
                         patch.object(driver.gate, 'print_plan'), \
                         patch.object(driver.gate, 'main', side_effect=entry), \
                         patch.object(driver.guard.shutil, 'disk_usage', return_value=NS(free=1024**4)), \
                         patch.object(gpu_witness, 'install'):
                        return original()
                return main
        original_module = outer.importlib.util.module_from_spec
        def module(spec):
            loaded = original_module(spec)
            if spec.name == '_execution_admission': loaded.__class__ = PrivateAdmission
            if spec.name == '_supervised_driver': loaded.__class__ = DriverControl
            return loaded
        sys.modules.pop('install', None)
        with patch.object(sys, 'argv', ['driver.py', 'item3', '--dry-run', '--out', str(output)]), \
             patch.object(outer.importlib.util, 'module_from_spec', side_effect=module):
            assert outer.run_driver() == 31
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker': worker(sys.argv[2])
    else: unittest.main()
