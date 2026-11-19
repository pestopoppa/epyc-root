"""Installed R7 enrollment through the real smoke recipe; native peers are inert."""
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
    visited, requests, stopped = [], [], []
    identity = output / 'PRELOAD-MODEL-IDENTITY.json'
    request_path = output / 'SMOKE-REQUEST.json'

    def install_witness(gate):
        calls.append('witness')
        assert json.loads(identity.read_text()) == {
            role: driver.PRELOAD_MODELS[role] for role in ('target', 'drafter')}
        if mode == 'stop': Path(fixture.config['stop_file']).touch()
        if mode == 'drift':
            Path(sys.argv[sys.argv.index('--prompt-set') + 1]).write_text('drift')

    def request(method, path, body, **kwargs):
        requests.append((method, path, body))
        assert method == 'POST' and path == '/completion' and kwargs['timeout'] == 60
        return (503 if mode == 'http' else 200), {
            'tokens': [] if mode == 'tokens' else [7]}

    def build_ctx(args, items):
        visited.append(True)
        assert items == [3] and not args.dry_run and args.out == str(output)
        assert args.fork_bin == str(fixture.native) and args.launch_prefix == ''
        assert driver.gate.ITEMS[3] is driver.item3_smoke is driver.item3
        assert driver.guard.attempt_root() == fixture.result.parent == driver.OUT
        args.no_device_claim = 'private model-free R7 smoke integration'
        return NS(args=args, own_children=[], open_runs=[], preempted=False,
                  client=NS(_req=request), check_boundary=driver.guard.boundary), [], []

    reasons = {'digest': 'receipt digest mismatch', 'stat': 'stat tuple drift',
               'metadata': 'metadata dflash.block_count mismatch',
               'r7missing': 'unsealed current prerequisite',
               'r7wrong': 'unsealed current prerequisite',
               'unknown': 'unknown framing enrollment mode',
               'projection': 'unsealed current prerequisite',
               'prefix': 'launch prefix', 'server': 'server mismatch',
               'stop': 'STOP', 'drift': 'source drift'}
    runtime_failure = mode in ('http', 'tokens', 'residency')
    reaches_gate = mode == 'pass' or runtime_failure
    srv = NS(sampler=NS(n_own_nonzero=0 if mode == 'residency' else 1))
    with patch.object(preload, 'EXPECTED_RECEIPT_SHA256', expected_receipt), \
         patch.object(witness, 'install', side_effect=install_witness), \
         patch.object(driver.gate, 'build_ctx', side_effect=build_ctx), \
         patch.object(driver.gate, 'print_plan'), \
         patch.object(driver.gate, 'Server', return_value=srv), \
         patch.object(driver.gate, 'start_steps', return_value=[]), \
         patch.object(driver.gate, 'stop_step', side_effect=lambda server: driver.gate.Step(
             'inert smoke stop', 0, lambda: stopped.append(True))), \
         patch.object(driver.gate, 'G', return_value={'trunk': list(range(40))}), \
         patch.object(driver.guard.shutil, 'disk_usage', return_value=NS(free=1024**4)):
        try: rc = original()
        except Exception as error:
            assert not reaches_gate, repr(error)
            assert reasons[mode] in str(error), repr(error)
            assert type(error).__name__ == (
                'VerificationError' if mode in ('digest', 'stat', 'metadata') else 'ValueError')
        else:
            assert reaches_gate, ('accepted invalid smoke entry', mode)
            assert rc == (4 if runtime_failure else 0), rc
    if reaches_gate:
        assert calls == ['witness'] and visited == [True] and len(requests) == 1
        meta = json.loads((output / 'run_meta.json').read_text())
        assert meta['items'] == [3] and not meta['args']['dry_run']
        assert meta['args']['launch_prefix'] == ''
        if runtime_failure:
            assert not request_path.exists() and not stopped
            assert not list((output / 'done').iterdir())
        else:
            assert stopped == [True]
            assert json.loads(request_path.read_text()) == {
                'scope': 'one native gate request; no group3 verdict',
                'first_request_ok': True, 'gpu_samples': 1, 'tokens': 1}
            assert len(list((output / 'done').iterdir())) == 2
    else:
        assert not visited and not requests and not stopped
        before_witness = mode in ('digest', 'stat', 'metadata', 'r7missing',
                                  'r7wrong', 'unknown', 'projection')
        assert calls == ([] if before_witness else ['witness'])
        assert sorted(p.name for p in output.iterdir()) == (
            [] if before_witness else [identity.name])
    # These tests never impersonate the publisher's native result or a full verdict.
    assert not fixture.result.exists()
    assert not list(output.rglob('VERDICT.json'))
    return 0


class RetainedR7Smoke(unittest.TestCase):
    def test_installed_nondry_r7_smoke_recipe_and_refusals(self):
        for mode in ('pass', 'http', 'tokens', 'residency', 'digest', 'stat',
                     'metadata', 'r7missing', 'r7wrong', 'unknown', 'projection',
                     'prefix', 'server', 'stop', 'drift'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, '-I', '-B', __file__, '--worker', mode],
                                        capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        from test_nondry_entry import worker
        worker(sys.argv[2], combined='smoke', retained=True, smoke=True)
    else: unittest.main()
