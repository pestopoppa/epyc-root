"""Installed non-dry prerequisites through actual gate parser/loop; inert work."""
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
    visited, worked = [], []
    identity = output / 'PRELOAD-MODEL-IDENTITY.json'

    def install_witness(gate):
        calls.append('witness')
        # The retained verifier and both model-stat checks have returned.
        recorded = json.loads(identity.read_text())
        assert recorded == {role: driver.PRELOAD_MODELS[role] for role in ('target', 'drafter')}
        assert driver.PRELOAD_MODELS['draft_cache_shape']['draft_swa_layers'] == 5
        if mode == 'stop': Path(fixture.config['stop_file']).touch()
        if mode == 'drift':
            Path(sys.argv[sys.argv.index('--prompt-set') + 1]).write_text('drift')

    def build_ctx(args, items):
        visited.append(True)
        assert calls == ['witness'] and identity.exists()
        assert items == [3] and not args.dry_run and args.out == str(output)
        assert args.fork_bin == str(fixture.native) and args.launch_prefix == ''
        assert driver.gate.ITEMS[3] is driver.item3
        assert args.no_device_claim == 'current captured keeper GPU writer; rechecked before gate entry'
        return NS(args=args, own_children=[], open_runs=[], preempted=False), [], []

    def item3(ctx):
        def work():
            worked.append(True)
            if mode == 'failure': raise RuntimeError('inert combined failure')
        return [driver.gate.Step('private combined work', 0, work)]

    reasons = {'digest': 'receipt digest mismatch', 'stat': 'stat tuple drift',
               'metadata': 'metadata dflash.block_count mismatch',
               'framing': 'historical framing not valid',
               'prefix': 'launch prefix', 'server': 'server mismatch',
               'stop': 'STOP', 'drift': 'source drift'}
    positive = mode in ('pass', 'failure')
    with patch.object(preload, 'EXPECTED_RECEIPT_SHA256', expected_receipt), \
         patch.object(witness, 'install', side_effect=install_witness), \
         patch.object(driver, 'item3', side_effect=item3), \
         patch.object(driver.gate, 'build_ctx', side_effect=build_ctx), \
         patch.object(driver.gate, 'print_plan'), \
         patch.object(driver.guard.shutil, 'disk_usage', return_value=NS(free=1024**4)):
        try: rc = original()
        except Exception as error:
            assert not positive, repr(error)
            assert reasons[mode] in str(error), repr(error)
            assert type(error).__name__ == ('VerificationError' if mode in ('digest', 'stat', 'metadata') else 'ValueError')
        else:
            assert positive, ('accepted invalid combined entry', mode)
            assert rc == (4 if mode == 'failure' else 0), rc
    if positive:
        assert calls == ['witness'] and visited == [True] and worked == [True]
        meta = json.loads((output / 'run_meta.json').read_text())
        assert meta['items'] == [3] and not meta['args']['dry_run']
        assert meta['args']['launch_prefix'] == ''
        assert len(list((output / 'done').iterdir())) == (0 if mode == 'failure' else 1)
    else:
        assert not visited and not worked
        before_gate = mode in ('digest', 'stat', 'metadata', 'framing')
        assert calls == ([] if before_gate else ['witness']), calls
        assert identity.exists() is not before_gate
        assert sorted(p.name for p in output.iterdir()) == ([] if before_gate else [identity.name])
    return 0


class CombinedEntry(unittest.TestCase):
    def test_installed_nondry_prerequisites_and_real_gate(self):
        for mode in ('pass', 'failure', 'digest', 'stat', 'metadata', 'framing',
                     'prefix', 'server', 'stop', 'drift'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker', mode],
                                        capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        from test_nondry_entry import worker
        worker(sys.argv[2], combined=True)
    else: unittest.main()
