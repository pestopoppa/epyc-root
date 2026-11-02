import unittest
from worker_draft import run_attempt


class WorkerDraftTest(unittest.TestCase):
    def args(self):
        return dict(mode='full', attempt_id='a', root='/unused', argv=['fake'],
                    input_bytes=b'abc', env={}, deadline_monotonic=20.,
                    cleanup_margin_s=2., grant_valid=lambda: True,
                    stopped=lambda: False, now=lambda: 10.)

    def test_ceiling_mode_and_length_reach_components(self):
        observed = {}
        def supervisor(argv, data, env, **kw):
            observed.update(kw)
            return {'status': 'completed'}
        def writer(root, attempt_id, mode, result, **kw):
            return mode, result, kw
        mode, result, receipt = run_attempt(**self.args(), supervise_fn=supervisor, write_fn=writer)
        self.assertEqual(mode, 'full')
        self.assertEqual(observed['timeout_s'], 8.)
        self.assertEqual(receipt['expected_input_bytes'], 3)
        self.assertEqual(result['status'], 'completed')

    def test_qualification_is_not_promoted(self):
        args = self.args(); args['mode'] = 'qualification'
        result = run_attempt(**args, supervise_fn=lambda *a, **k: {'status': 'completed'},
                             write_fn=lambda root, ident, mode, result, **kw: mode)
        self.assertEqual(result, 'qualification')

    def test_invalid_grant_or_deadline_prevents_launch(self):
        args = self.args(); args['grant_valid'] = lambda: False
        with self.assertRaises(ValueError): run_attempt(**args)
        args = self.args(); args['deadline_monotonic'] = 11.
        with self.assertRaises(ValueError): run_attempt(**args)

    def test_lost_grant_after_exit_cannot_record_success(self):
        args = self.args(); grant = [True]
        args['grant_valid'] = lambda: grant[0]
        def supervisor(*a, **kw):
            grant[0] = False
            self.assertTrue(kw['stopped']())
            return {'status': 'completed'}
        status = run_attempt(**args, supervise_fn=supervisor,
                             write_fn=lambda root, ident, mode, result, **kw: result['status'])
        self.assertEqual(status, 'cancelled')


if __name__ == '__main__':
    unittest.main()
