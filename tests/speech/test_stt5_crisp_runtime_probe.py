"""Model-free checks for the public runtime probe's no-redraw/process contract."""
import hashlib
import json
import signal
import tempfile
from unittest import mock
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

spec = importlib.util.spec_from_file_location('probe', Path(__file__).parents[2] / 'scripts/speech/stt5_crisp_runtime_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class RuntimeProbeTests(unittest.TestCase):
    def test_matrix_preserves_native_context_mapping_and_language(self):
        self.assertEqual(len(set(probe.matrix())), 8)
        cfg = dict(runner='runner', model='model', audio='audio')
        for context, preset in [('r0', '1'), ('r3', '0'), ('r6', '2'), ('r13', '3')]:
            for mode, language in [('auto', 'auto'), ('forced', 'en-US')]:
                self.assertEqual(probe.command(cfg, context, mode, Path('txt')),
                                 ['runner', 'model', 'audio', preset, language, '3', 'txt'])

    def test_transcribe_context_language_and_native_token_request(self):
        cfg = dict(runner='runner', model='model', audio='audio', runner_kind='transcribe')
        for context, mode in probe.matrix():
            argv = probe.command(cfg, context, mode, Path('txt'))
            self.assertEqual(argv[argv.index('--stream-att-right') + 1], context[1:])
            self.assertEqual(argv[argv.index('--backend') + 1], 'cpu')
            self.assertIn('--raw-tokens', argv)
            self.assertEqual('--language' in argv, mode == 'forced')
            if mode == 'forced':
                self.assertEqual(argv[argv.index('--language') + 1], 'en-US')

    def test_native_witness_adapter_preserves_duplicate_and_malformed_rows(self):
        parser = mock.Mock()
        text = 'noise\nCS8_NEMO_TOKENS 1\nCS8_NEMO_TOKEN 0 8\n  timing row\nCS8_NEMO_TOKENS_END\n'
        probe.parse_native(parser, text, 'text', 'transcribe')
        parser.parse.assert_called_once_with('CS8_MATCHED_NEMO_TOKENS 1\nCS8_MATCHED_NEMO_TOKEN 0 8\nCS8_MATCHED_NEMO_TOKENS_END', 'text')
        parser.reset_mock()
        probe.parse_native(parser, text + 'CS8_NEMO_TOKEN broken\n', 'text', 'transcribe')
        self.assertTrue(parser.parse.call_args.args[0].endswith('CS8_MATCHED_NEMO_TOKEN broken'))

    def test_reference_disagreement_or_missing_evidence_cannot_pass(self):
        import copy
        good = dict(status='PASS', rc=0, reaped=True, case='r3-auto',
                    model_sha256='model', audio_sha256='audio',
                    tokens=dict(token_ids=[1, 2], unk_count=0, hypothesis_with_unk='hello'))
        self.assertTrue(probe.reference_agrees(good, good))
        for key, value in [('status', 'UNKNOWN'), ('rc', -15), ('reaped', False),
                           ('case', 'r0-auto'), ('model_sha256', 'wrong'), ('audio_sha256', 'wrong')]:
            bad = copy.deepcopy(good)
            bad[key] = value
            self.assertFalse(probe.reference_agrees(good, bad))
        for key, value in [('token_ids', [2, 1]), ('unk_count', 1), ('hypothesis_with_unk', 'other')]:
            bad = copy.deepcopy(good)
            bad['tokens'][key] = value
            self.assertFalse(probe.reference_agrees(good, bad))

    def test_scoped_repetition_rejects_invalid_or_duplicate_cases(self):
        self.assertEqual(probe.matrix({'cases': [['r0', 'forced']]}), [('r0', 'forced')])
        for cases in ([], [['r1', 'auto']], [['r0', 'forced']] * 2):
            with self.assertRaises(ValueError):
                probe.matrix({'cases': cases})

    def test_drain_reaps_owned_child_that_ignores_term(self):
        code = 'import signal,sys,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print("ready",flush=True); time.sleep(60)'
        child = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
            probe.drain(child)
            self.assertIsNotNone(child.poll())
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            child.stdout.close()

    def test_exposed_missing_results_are_unknown_without_redraw(self):
        for scoped in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                model = base / 'model'
                model.write_bytes(b'model-free fixture')
                parser = base / 'parser.py'
                parser.write_text('def parse(*args): raise AssertionError("no native call")\n')
                output = base / ('smoke' if scoped else 'output')
                output.mkdir()
                st = model.stat()
                config = base / 'config.json'
                config.write_text(json.dumps(dict(model=str(model), parser=str(parser),
                    model_stat=[st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns],
                    pins={}, output=str(base / 'output'), expected_maps=[],
                    **({'cases': [['r0', 'forced']], 'smoke_output': str(output)} if scoped else {}))))
                digest = hashlib.sha256(config.read_bytes()).hexdigest()
                for context, mode in probe.matrix({'cases': [['r0', 'forced']]} if scoped else None):
                    probe.write_new(output / (context + '-' + mode + '.exposure.json'),
                                    dict(config_sha256=digest))
                old_handlers = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
                try:
                    with mock.patch.dict(probe.os.environ, {'FILLER_SMOKE': '1' if scoped else '0'}), mock.patch.object(sys, 'argv', ['probe', str(config)]), mock.patch.object(
                            probe.os, 'sched_getaffinity', return_value=set(range(24))), mock.patch.object(
                            probe.subprocess, 'Popen', side_effect=AssertionError('redraw forbidden')) as spawn:
                        self.assertEqual(probe.main(), 0)
                        spawn.assert_not_called()
                finally:
                    for signum, handler in old_handlers.items():
                        signal.signal(signum, handler)
                summary = json.loads((output / 'summary.json').read_text())
                self.assertEqual(summary['verdict'], 'INCONCLUSIVE')
                self.assertEqual(len(summary['cases']), 1 if scoped else 8)
                if scoped:
                    self.assertFalse((base / 'output').exists())
                self.assertTrue(all(c['status'] == 'UNKNOWN' for c in summary['cases']))
                self.assertFalse(summary['validation_exposed'])

    def test_exposure_write_never_overwrites(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'exposure.json'
            probe.write_new(path, {'original': True})
            with self.assertRaises(FileExistsError):
                probe.write_new(path, {'original': False})
            self.assertEqual(path.read_text(), '{"original": true}\n')


if __name__ == '__main__':
    unittest.main()
