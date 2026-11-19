"""Non-dry installed main to real gate/item3/RowflowContext; inert native peers."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def combined_main(driver, original, fixture, output, mode, preload, witness,
                  expected_receipt, calls):
    import driver_boundary
    checks, work, records, published = [], [], [], []
    assert issubclass(driver.RowflowContext, driver_boundary.RowflowContext)
    assert driver.RowflowContext is not driver_boundary.RowflowContext
    context = None

    def install_witness(gate):
        calls.append('witness')
        identity = json.loads((output / 'PRELOAD-MODEL-IDENTITY.json').read_text())
        assert identity == {role: driver.PRELOAD_MODELS[role] for role in ('target', 'drafter')}

    def build_ctx(args, items):
        nonlocal context
        assert calls == ['witness'] and not args.dry_run and items == [3]
        assert args.out == str(output) and args.fork_bin == str(fixture.native)
        assert args.launch_prefix == '' and driver.gate.ITEMS[3] is driver.item3
        args.no_device_claim = 'private model-free context integration'
        context = NS(args=args, out=output, own_children=[], open_runs=[], preempted=False,
                     check_boundary=lambda: checks.append('underlying'))
        return context, [], []

    def setup(ctx, srv, state):
        assert ctx is context
        state.update(R=object(), record={}, identity={},
                     ledger=NS(json=lambda name, value: records.append((name, value))))

    def controller(gate, ctx, *args):
        assert isinstance(ctx, driver.RowflowContext) and ctx.out == output
        ctx.check_boundary()
        work.append('first')
        if mode == 'stop': Path(fixture.config['stop_file']).touch()
        if mode == 'grant': fixture.grant.write_text(fixture.raw + ' cpus=184-187\n')
        if mode == 'output': context.out = fixture.root / 'foreign'
        if mode == 'source': fixture.native.write_bytes(b'drift')
        if mode == 'deadline': fixture.gate.time.time.return_value = fixture.end - 90
        if mode == 'underlying':
            context.check_boundary = lambda: (_ for _ in ()).throw(ValueError('server failed'))
        if mode == 'sticky':
            stop = Path(fixture.config['stop_file']); stop.touch()
            try: ctx.check_boundary()
            except driver.EntryRefused: pass
            else: raise AssertionError('STOP not refused')
            stop.unlink()
        with patch.object(driver.guard.output_reserve, 'check',
                          side_effect=RuntimeError('reserve exhausted') if mode == 'reserve' else None), \
             patch.object(driver.guard.resource, 'getrusage',
                          return_value=NS(ru_maxrss=177*1024**2 if mode == 'hwm' else 0)):
            ctx.check_boundary()
            work.append('second')

    with patch.object(preload, 'EXPECTED_RECEIPT_SHA256', expected_receipt), \
         patch.object(witness, 'install', side_effect=install_witness), \
         patch.object(driver.gate, 'build_ctx', side_effect=build_ctx), \
         patch.object(driver.gate, 'print_plan'), \
         patch.object(driver.gate, 'Server', return_value=NS(sampler=None)), \
         patch.object(driver.gate, 'start_steps', return_value=[]), \
         patch.object(driver.gate, 'stop_step', return_value=driver.gate.Step('private stop', 0, None)), \
         patch.object(driver, 'setup', side_effect=setup), \
         patch.object(driver, 'run', side_effect=controller), \
         patch.object(driver, 'publish', side_effect=lambda *args: published.append(True)), \
         patch.object(driver.guard.shutil, 'disk_usage', return_value=NS(free=1024**4)), \
         patch.object(driver_boundary, 'rowflow_entry', side_effect=AssertionError('historical adapter used')):
        rc = original()
    meta = json.loads((output / 'run_meta.json').read_text())
    assert meta['items'] == [3] and not meta['args']['dry_run']
    done = list((output / 'done').iterdir())
    if mode == 'valid':
        assert rc == 0 and work == ['first', 'second'] and published == [True]
        assert checks == ['underlying', 'underlying'] and not records
        assert len(done) == 4, done
    else:
        assert rc == 3, rc
        assert work == ['first'] and not published
        assert len(done) == 1, done
        assert records[0][0] == 'DIAGNOSTIC-REFUSAL.json', records
        reasons = {'stop': 'STOP', 'grant': 'grant changed', 'output': 'context output',
                   'source': 'source drift', 'deadline': 'deadline', 'underlying': 'server failed',
                   'sticky': 'STOP', 'reserve': 'reserve exhausted', 'hwm': 'HWM'}
        assert reasons[mode] in records[0][1], records
    return 0


class CombinedContext(unittest.TestCase):
    def test_nondry_parser_item3_and_terminal_boundaries(self):
        for mode in ('valid', 'stop', 'grant', 'output', 'source', 'deadline',
                     'underlying', 'sticky', 'reserve', 'hwm'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker', mode],
                                        capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        from test_nondry_entry import worker
        worker(sys.argv[2], combined='context')
    else: unittest.main()
