"""The smoke must reject observations outside the request or from another PID."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cafe3-adaptive'))
import native_smoke


class SmokeEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.record = dict(pid=17, child_reaped=True, tokens_predicted=32, cutoff=None,
                           request_start=10., request_end=11., samples=[
                               dict(pid=17, at=t, kfd_registered=True, vram_bytes=4096,
                                    models_mapped=True, libraries_mapped=True) for t in (10.2, 10.4)])

    def test_valid(self):
        native_smoke.validate(self.record)

    def test_rejects_missing_or_misattributed_evidence(self):
        for key, value in [('pid', 18), ('at', 9.9), ('at', 11.1),
                           ('kfd_registered', False), ('vram_bytes', 0),
                           ('models_mapped', False), ('libraries_mapped', False)]:
            with self.subTest(key=key, value=value):
                record = copy.deepcopy(self.record)
                record['samples'][0][key] = value
                with self.assertRaises(ValueError):
                    native_smoke.validate(record)

    def test_rejects_noninference_cutoff_unreaped_or_duplicate_sample(self):
        for key, value in [('tokens_predicted', 0), ('cutoff', 'deadline'), ('child_reaped', False),
                           ('samples', self.record['samples'][:1]),
                           ('samples', [self.record['samples'][0]] * 2)]:
            with self.subTest(key=key):
                record = dict(self.record, **{key: value})
                with self.assertRaises(ValueError):
                    native_smoke.validate(record)


if __name__ == '__main__':
    unittest.main()
