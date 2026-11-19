"""Installed full-run work-boundary controls; private admission, inert work."""
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
from test_execution_admission import load


class FullrunContext(unittest.TestCase):
    def test_installed_fullrun_cell_and_terminal_controls(self):
        for mode in ('valid', 'stop', 'grant', 'provider', 'reserve', 'output',
                     'underlying', 'hwm', 'source', 'deadline', 'sticky'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker', mode],
                                        capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def worker(mode):
    fixture = fixtures.ExecutionAdmission(); fixture.setUp()
    try:
        output = fixture.root / 'output'
        output.mkdir()
        fixture.config['output_root'] = str(output)
        destination = fixture.root / 'installed'
        install.install(destination, binding_revision=install.REVISION,
                        guard_revision='current-guard-v3',
                        execution=dict(fixture.config, sources=fixture.seal['sources']))
        outer = load(destination / 'supervisor.py', 'fullrun_outer')
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
                    import driver_boundary
                    import gpu_witness
                    # Actual retained wrapper's isinstance branch must recognize
                    # the bound subclass, retaining its original abort protocol.
                    assert issubclass(driver.RowflowContext, driver_boundary.RowflowContext)
                    assert driver.RowflowContext is not driver_boundary.RowflowContext
                    checks, work, records = [], [], []
                    context = NS(out=output, own_children=[],
                                 check_boundary=lambda: checks.append('underlying'))
                    ledger = NS(json=lambda name, value: records.append((name, value)))
                    state = {}
                    def setup(ctx, srv, target):
                        target.update(R=object(), record={}, identity={}, ledger=ledger)
                        state.update(target)
                    def controller(gate, ctx, *args):
                        assert isinstance(ctx, driver.RowflowContext)
                        assert ctx.out == context.out  # real retained delegation
                        ctx.check_boundary()
                        work.append('first')
                        if mode == 'stop': Path(fixture.config['stop_file']).touch()
                        if mode == 'grant': fixture.grant.write_text(fixture.raw + ' cpus=184-187\n')
                        if mode == 'provider':
                            captured['provider'].recheck = lambda witness: (_ for _ in ()).throw(ValueError('provider lost'))
                        if mode == 'output': context.out = fixture.root / 'elsewhere'
                        if mode == 'source': fixture.native.write_bytes(b'drift')
                        if mode == 'deadline': fixture.gate.time.time.return_value = fixture.end - 90
                        if mode == 'sticky':
                            stop = Path(fixture.config['stop_file']); stop.touch()
                            try: ctx.check_boundary()
                            except driver.EntryRefused: pass
                            else: raise AssertionError('STOP not refused')
                            stop.unlink()
                        with patch.object(driver.guard.output_reserve, 'check',
                                          side_effect=RuntimeError('reserve exhausted') if mode == 'reserve' else None), \
                             patch.object(driver.guard.resource, 'getrusage',
                                          return_value=NS(ru_maxrss=(177*1024**2 if mode == 'hwm' else 0))):
                            if mode == 'underlying':
                                context.check_boundary = lambda: (_ for _ in ()).throw(ValueError('server failed'))
                            ctx.check_boundary()
                            work.append('second')
                    def gate_main():
                        assert driver.gate.ITEMS[3] is driver.item3
                        steps = driver.item3(context)
                        steps[0].fn()
                        if mode == 'valid':
                            steps[1].fn()
                            assert work == ['first', 'second'] and checks == ['underlying', 'underlying']
                            assert not records
                        else:
                            try: steps[1].fn()
                            except driver.gate.Abort: pass
                            else: raise AssertionError('boundary refusal swallowed')
                            assert work == ['first']
                            assert records[0][0] == 'DIAGNOSTIC-REFUSAL.json'
                            reasons = {'stop': 'STOP', 'grant': 'grant changed',
                                       'provider': 'provider lost', 'reserve': 'reserve exhausted',
                                       'output': 'context output', 'underlying': 'server failed',
                                       'hwm': 'HWM', 'source': 'source drift',
                                       'deadline': 'deadline', 'sticky': 'STOP'}
                            assert reasons[mode] in records[0][1], records
                        return 29
                    with patch.object(driver.gate, 'Server', return_value=NS(sampler=None)), \
                         patch.object(driver.gate, 'start_steps', return_value=[]), \
                         patch.object(driver.gate, 'stop_step', return_value=driver.gate.Step('inert stop', 0, None)), \
                         patch.object(driver, 'setup', side_effect=setup), \
                         patch.object(driver, 'run', side_effect=controller), \
                         patch.object(driver.guard.shutil, 'disk_usage', return_value=NS(free=1024**4)), \
                         patch.object(driver_boundary, 'rowflow_entry', side_effect=AssertionError('historical adapter used')), \
                         patch.object(gpu_witness, 'install'), \
                         patch.object(driver.gate, 'main', side_effect=gate_main):
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
            assert outer.run_driver() == 29
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker': worker(sys.argv[2])
    else: unittest.main()
