import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from diagnostic_runner import gpu_sample, read_samples


class CaptureTest(unittest.TestCase):
    def test_unreadable_or_corrupt_samples_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'samples'
            records, error = read_samples(path)
            self.assertEqual(records, [])
            self.assertIsNotNone(error)
            path.write_text('{broken\n')
            records, error = read_samples(path)
            self.assertEqual(records, [])
            self.assertIsNotNone(error)
            path.write_text(json.dumps({'time': 1}) + '\n')
            self.assertEqual(read_samples(path), ([{'time': 1}], None))

    def test_smi_failure_is_recorded(self):
        with patch('diagnostic_runner.subprocess.run', side_effect=FileNotFoundError('missing')):
            sample = gpu_sample()
        self.assertIn('rocm_smi_error', sample)
        self.assertIsInstance(sample['time'], float)


if __name__ == '__main__':
    unittest.main()
