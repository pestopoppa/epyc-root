"""Offline tests: exercise the pinned runner integration, never start inference."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cpu_continuation as job
import cpu_resume


class ContinuationTests(unittest.TestCase):
    def test_no_grant_refused_before_import_or_state(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(job, 'load_runner') as load:
            with self.assertRaisesRegex(RuntimeError, 'keeper grant'):
                job.main()
            load.assert_not_called()

    def test_expired_grant_refused_before_import(self):
        with patch.dict(os.environ, dict(FILLER_ID='test', FILLER_END='1')), patch.object(job, 'load_runner') as load:
            with self.assertRaisesRegex(RuntimeError, 'expired'):
                job.main()
            load.assert_not_called()

    def test_actual_pinned_runner_uses_granted_threads_and_native_proof(self):
        runner = job.load_runner()
        runner.SLOTS = Path('/scratch/slots')
        command = job.server_argv(runner, [88, 89, 90, 91])
        self.assertEqual(command[command.index('-t')+1], '4')
        self.assertEqual(command[command.index('-tb')+1], '4')
        self.assertNotIn('region-lock', ' '.join(command))
        self.assertNotIn('0-95', command)
        self.assertIn('--device', command)
        self.assertEqual(command[command.index('--device')+1], 'none')
        self.assertEqual(runner.INPUTS, job.FIXTURES/'cpu_leg/inputs')
        self.assertTrue(runner.load_inputs()['bad'] == [])
        with tempfile.TemporaryDirectory() as tmp:
            runner.RESULTS = Path(tmp)
            runner.SLOTS = Path(tmp)/'slots'
            state = runner.RESULTS/'CY2/state.json'
            state.parent.mkdir()
            state.write_text(json.dumps(dict(arm='CY2', turn=42, depth=367636, saved_turn=42)))
            runner.run = Mock(side_effect=lambda args: json.loads(state.read_text()))
            identity = dict(model_sha256='a'*64, build_sha256='b'*64, argv_sha256='c'*64)
            args = SimpleNamespace(arm='CY2', force_preflight=False, selftest_external=False)
            fresh = cpu_resume.run_guarded(runner, args, identity, Path(tmp)/'receipt.json')
            self.assertEqual(fresh, cpu_resume.fresh_state('CY2'))
            self.assertEqual(json.loads(state.with_name('resume-decision.json').read_text())['action'], 're-prefill')

    def test_changed_model_refused_without_rehashing_weights(self):
        inputs = dict(research_commit=job.REV, model='model.gguf', model_stat={'ino': 123})
        with patch.object(job, 'prepared_stat', return_value={'ino': 456}), patch.object(job, 'digest') as hashed:
            with self.assertRaisesRegex(ValueError, 'model changed'):
                job.check_inputs(inputs)
            hashed.assert_not_called()

    def test_cleanup_escalates_and_reaps_only_child(self):
        import subprocess
        child = Mock()
        child.poll.side_effect = [None, 0]
        child.wait.side_effect = [subprocess.TimeoutExpired('own', 20), 0]
        job.stop_own(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)

    def test_main_cleans_up_on_interrupted_request_and_keeps_native_preflight(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d/'INPUTS.json').write_text(json.dumps(dict(model_sha256='a'*64, build_sha256='b'*64)))
            runner = SimpleNamespace()
            child = Mock()
            child.poll.return_value = 0
            def interrupted(runner, args, identity, receipt, **kwargs):
                self.assertTrue(kwargs['checkpoint'])
                self.assertFalse(args.force_preflight)
                self.assertFalse(args.selftest_external)
                self.assertFalse(args.wait)
                self.assertTrue(args.i_own_the_window)
                self.assertLessEqual(float(time.time()),
                    __import__('datetime').datetime.fromisoformat(args.block_until).timestamp())
                raise SystemExit(75)
            with patch.dict(os.environ, dict(FILLER_ID='test', FILLER_END=str(time.time()+2000))), \
                 patch.object(job.Path, 'cwd', return_value=d), \
                 patch.object(job, 'load_runner', return_value=runner), \
                 patch.object(job, 'check_inputs'), \
                 patch.object(job, 'server_argv', return_value=['server']), \
                 patch.object(job, 'install_server', return_value=[child]), \
                 patch.object(job, 'stop_own') as stop, \
                 patch.object(cpu_resume, 'run_guarded', side_effect=interrupted):
                with self.assertRaises(SystemExit):
                    job.main()
                stop.assert_called_once_with(child)
                result = json.loads((d/'RESULT.json').read_text())
                self.assertTrue(result['own_server_reaped'])
                self.assertEqual(result['verdict'], 'INCOMPLETE')
                self.assertEqual(runner.SLOTS, d/'out/continuation/slots')
                self.assertEqual(result['attempt'], str(d/'out/continuation'))

    def test_verdict_requires_complete_valid_decode_and_five_needles(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertEqual(job.summarize(out, 0)['verdict'], 'INCOMPLETE')
            path = out/'CY2/probe_510000.json'
            path.parent.mkdir()
            probe = dict(needles=[dict(grade='correct') for _ in range(5)],
                decode=dict(depth=511000, decode_tps=2.1, http=200, predicted_n=128),
                local=dict(degeneracy=dict(cls='OK')))
            path.write_text(json.dumps(probe))
            self.assertEqual(job.summarize(out, 0)['verdict'], 'PASS')
            self.assertEqual(job.summarize(out, 5)['verdict'], 'INCOMPLETE')
            probe['needles'][0]['grade'] = 'wrong'
            probe['needles'][1]['grade'] = 'wrong'
            path.write_text(json.dumps(probe))
            self.assertEqual(job.summarize(out, 0)['verdict'], 'FAIL')
            probe['decode']['http'] = 500
            path.write_text(json.dumps(probe))
            self.assertEqual(job.summarize(out, 0)['verdict'], 'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
