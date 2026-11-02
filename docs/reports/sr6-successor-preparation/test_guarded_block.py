import unittest
from pathlib import Path
from unittest.mock import patch

from guarded_block import capture_guarded_block
from keeper_admission import KeeperAdmission


class GuardedBlockTest(unittest.TestCase):
    def test_same_admission_and_session_drain_are_wired(self):
        admission = object.__new__(KeeperAdmission)
        admission.deadline = 1234567890
        admission.stop_path = Path('/tmp/example-stop')
        with patch('guarded_block.VerifiedPost') as post, patch('guarded_block.execute_block') as execute:
            execute.return_value = {'state': 'CAPTURED_ONLY'}
            self.assertEqual(capture_guarded_block(output=Path('/tmp'), block={}, sampler={},
                sampler_sha256='a'*64, admission=admission, spawn=lambda arm: None,
                verify_ready_and_identity=lambda child, arm: {}, port=12345, timeout_s=1,
                max_response_bytes=1024), {'state': 'CAPTURED_ONLY'})
        self.assertIs(post.call_args.kwargs['admission_check'], admission)
        self.assertIs(execute.call_args.kwargs['admission_check'], admission)
        self.assertIs(execute.call_args.kwargs['post'], post.return_value)
        from session_drain import drain_session
        self.assertIs(execute.call_args.kwargs['drain'], drain_session)

    def test_untrusted_admission_rejected(self):
        with self.assertRaises(ValueError):
            capture_guarded_block(output=Path('/tmp'), block={}, sampler={}, sampler_sha256='a'*64,
                admission=lambda: True, spawn=lambda arm: None,
                verify_ready_and_identity=lambda child, arm: {}, port=12345, timeout_s=1,
                max_response_bytes=1024)


if __name__ == '__main__':
    unittest.main()
