import unittest
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from keeper_block import capture_keeper_block


class KeeperBlockTest(unittest.TestCase):
    def setUp(self):
        self.args = dict(env={'FILLER_ID': 'row1'}, row_id='row1',
            grant_path=Path('/tmp/row1.grant'), stop_path=Path('/tmp/row1.stop'),
            guard_sha256='a' * 64, output=Path('/tmp'), block={}, sampler={},
            sampler_sha256='b' * 64, spawn=lambda arm: None,
            verify_ready_and_identity=lambda process, arm: {}, port=1234,
            timeout_s=1, max_response_bytes=100)

    def test_same_claim_bound_to_admission_used_by_capture(self):
        with patch('keeper_block.FullHostBenchClaim') as claim, \
             patch('keeper_block.KeeperAdmission') as admission, \
             patch('keeper_block.capture_guarded_block', return_value={'state': 'CAPTURED_ONLY'}) as capture:
            admission.return_value.return_value = True
            self.assertEqual(capture_keeper_block(**self.args), {'state': 'CAPTURED_ONLY'})
        claim.assert_called_once_with('row1', 'a' * 64)
        self.assertIs(admission.call_args.kwargs['ownership_check'], claim.return_value)
        self.assertEqual(admission.call_args.kwargs['row_id'], 'row1')
        self.assertIs(capture.call_args.kwargs['admission'], admission.return_value)

    def test_denial_or_invalid_admission_never_captures(self):
        for result in (False, None, 1):
            with self.subTest(result=result), patch('keeper_block.FullHostBenchClaim'), \
                 patch('keeper_block.KeeperAdmission') as admission, \
                 patch('keeper_block.capture_guarded_block') as capture:
                admission.return_value.return_value = result
                with self.assertRaises(ValueError):
                    capture_keeper_block(**self.args)
                capture.assert_not_called()

    def test_real_admission_tracks_stop_after_initial_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            start, end = 1800000000, 1800003600
            stamp = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
            grant, stop = root / 'row1.grant', root / 'stop'
            grant.write_text(f'regions=q0,q1,q2,q3 holds=q0 start={stamp(start)} end={stamp(end)}\n')
            args = dict(self.args, grant_path=grant, stop_path=stop,
                env={'FILLER_ID':'row1', 'FILLER_END':str(end),
                     'FILLER_DEADLINE':str(end-90), 'FILLER_STOPFILE':str(stop)})
            def capture(**kwargs):
                self.assertTrue(kwargs['admission']())
                stop.touch()
                self.assertFalse(kwargs['admission']())
                return {'state': 'CAPTURED_ONLY'}
            with patch('keeper_block.FullHostBenchClaim', return_value=lambda: True), \
                 patch('keeper_admission.time.time', return_value=start + 1), \
                 patch('keeper_block.capture_guarded_block', side_effect=capture):
                self.assertEqual(capture_keeper_block(**args), {'state': 'CAPTURED_ONLY'})


if __name__ == '__main__':
    unittest.main()
