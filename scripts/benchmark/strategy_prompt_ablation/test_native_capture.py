"""Model-free custody and incomplete-run tests; no inference or run authority."""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest

import native_capture as capture


def turn(request=b'request', response=b'response', **changes):
    value = dict(request=request, response=response, prompt_tokens=3,
                 output_tokens=2, elapsed_s=0.1, error=None)
    value.update(changes)
    return value


def args():
    return dict(plan_sha256='a'*64, question_id='q1', arm='strategy_short',
                prompt_sha256='b'*64, source_identity='asserted',
                slot_reset_receipt='asserted', origin='synthetic',
                status='complete', turns=[turn(), turn(b'r2', b's2')], correct=True)


class CaptureTest(unittest.TestCase):
    def test_ordered_custody_privacy_and_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'capture'
            path = capture.write_observation(output, **args())
            record = json.loads(path.read_text())
            self.assertEqual(record['origin'], 'synthetic')
            self.assertEqual([t['turn'] for t in record['turns']], [1, 2])
            for entry in record['turns']:
                for kind in ('request', 'response'):
                    f = output / entry[kind + '_file']
                    self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), entry[kind + '_sha256'])
                    self.assertEqual(stat.S_IMODE(f.stat().st_mode) & 0o077, 0)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode) & 0o077, 0)
            with self.assertRaises(FileExistsError):
                capture.write_observation(output, **args())

    def test_missing_counters_and_incomplete_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            values = args()
            values.update(status='incomplete', correct=None, error='timeout',
                          turns=[turn(response=None, prompt_tokens=None, output_tokens=None,
                                      elapsed_s=None, error='timeout')])
            record = json.loads(capture.write_observation(Path(temp)/'capture', **values).read_text())
            self.assertEqual(record['status'], 'incomplete')
            self.assertIsNone(record['correct'])
            for key in ('prompt_tokens', 'output_tokens', 'elapsed_s', 'response_file', 'response_sha256'):
                self.assertIsNone(record['turns'][0][key])

    def test_bad_inputs_refused_before_creating_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'capture'
            cases = [dict(origin=None), dict(status='incomplete', correct=True),
                     dict(error='task failed'), dict(turns=[turn(error='turn failed')]),
                     dict(turns=[turn(response=None)]), dict(turns=[turn(prompt_tokens=-1)]),
                     dict(turns=[turn(elapsed_s=float('nan'))])]
            for changes in cases:
                values = args(); values.update(changes)
                with self.assertRaises(ValueError):
                    capture.write_observation(output, **values)
                self.assertFalse(output.exists())
            values = args(); del values['origin']
            with self.assertRaises(TypeError):
                capture.write_observation(output, **values)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
