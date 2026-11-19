"""Model-free producer/consumer contract checks; no inference or source edits."""
import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('capture', ROOT/'scripts/vidya/adapters/kpf30_phase_capture.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)

def stream(phases, n_tokens=None):
    n = len(phases)
    lines = [f'KPF30_BEGIN call=1 count={n}']
    for i, phase in enumerate(phases):
        lines += [f'KPF30_PHASE call=1 index={i} seq={i} pos=40 phase={phase}']
    for i in range(n):
        lines += [f'KPF30 row={i} seq={i} pos=40 n_tokens={n_tokens or n} n_seqs={n} swa=0 causal=1 n_kv=64 blocks=1 live=1 mixed=0 unknown=0 live_unknown=0 invalid_mask=0']
    return lines + ['KPF30_END call=1 rc=0']

class PhaseContract(unittest.TestCase):
    def test_single_token_verify_is_verify(self):
        rows, _ = capture.parse_log(stream(['verify']))
        self.assertEqual([r['phase'] for r in rows], ['verify'])
    def test_multi_token_decode_is_decode(self):
        rows, _ = capture.parse_log(stream(['decode', 'decode']))
        self.assertEqual([r['phase'] for r in rows], ['decode', 'decode'])
    def test_mixed_batch_joins_each_row(self):
        rows, _ = capture.parse_log(stream(['prefill', 'verify', 'decode']))
        self.assertEqual([(r['seq'], r['phase']) for r in rows], [(1, 'verify'), (2, 'decode')])
    def test_current_producer_without_position_rejected(self):
        with self.assertRaisesRegex(ValueError, 'malformed mask row'):
            capture.parse_log([s.replace(' pos=40 n_tokens=', ' n_tokens=') for s in stream(['decode'])])
    def test_unknown_or_failed_or_unscoped_rejected(self):
        for lines in [stream(['unknown']), stream(['verify'])[:-1]+['KPF30_END call=1 rc=1'], stream(['decode'])+['KPF30_UNSCOPED_TARGET']]:
            with self.subTest(lines=lines), self.assertRaises(ValueError): capture.parse_log(lines)
    def test_partial_coverage_rejected(self):
        lines = stream(['verify', 'decode'])
        with self.assertRaises(ValueError): capture.parse_log([s for s in lines if 'row=1' not in s])

if __name__ == '__main__': unittest.main()
