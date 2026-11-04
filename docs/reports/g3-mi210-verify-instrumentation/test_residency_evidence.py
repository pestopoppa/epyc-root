import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from residency_evidence import analyze_residency


class ResidencyEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backend = Path(self.tmp.name) / 'libggml-hip.so'
        self.backend.write_bytes(b'candidate')
        st = self.backend.stat()
        maps = f'1000-2000 r-xp 00000000 {os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x} {st.st_ino} {self.backend}\n'
        def smi(used):
            return json.dumps({'card0': {'Card series': 'AMD Instinct MI210', 'VRAM Total Used Memory (B)': str(used)}})
        self.base = {'time': 1, 'rocm_smi_rc': 0, 'rocm_smi': smi(100)}
        self.sample = {'time': 3, 'pid': 42, 'alive': True, 'maps': maps,
                       'kfd_pid_present': True, 'rocm_smi_rc': 0, 'rocm_smi': smi(200)}
        self.args = dict(baseline=self.base, samples=[self.sample], card='card0', pid=42,
                         backend=self.backend, expected_sha256=hashlib.sha256(b'candidate').hexdigest(), start=2, end=4)

    def check_unknown(self):
        self.assertEqual(analyze_residency(**self.args)['status'], 'UNKNOWN')

    def test_all_witnesses_in_one_sample(self):
        result = analyze_residency(**self.args)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['matching_samples'][0]['vram_delta_bytes'], 100)

    def test_witnesses_cannot_be_combined_across_samples(self):
        self.sample['kfd_pid_present'] = False
        other = dict(self.sample, time=3.5, kfd_pid_present=True, maps='')
        self.args['samples'].append(other)
        self.check_unknown()

    def test_baseline_and_window_required(self):
        self.base['time'] = 2
        self.check_unknown()
        self.base['time'] = 1
        self.sample['time'] = 5
        self.check_unknown()

    def test_wrong_library_or_receipt_is_unknown(self):
        self.sample['maps'] = self.sample['maps'].replace(str(self.backend), str(self.backend) + '.other')
        self.check_unknown()
        self.sample['maps'] = ''
        self.args['expected_sha256'] = '0' * 64
        self.assertIn('backend digest mismatch', analyze_residency(**self.args)['reasons'])

    def test_mi210_and_positive_delta_required(self):
        self.sample['rocm_smi'] = self.base['rocm_smi']
        self.check_unknown()
        self.sample['rocm_smi'] = self.sample['rocm_smi'].replace('MI210', 'MI250')
        self.check_unknown()

    def test_missing_backend_is_unknown(self):
        self.backend.unlink()
        self.check_unknown()

    def test_kfd_pid_and_live_process_required(self):
        for key, value in [('kfd_pid_present', False), ('pid', 43), ('alive', False)]:
            old = self.sample[key]
            self.sample[key] = value
            self.check_unknown()
            self.sample[key] = old


if __name__ == '__main__':
    unittest.main()
