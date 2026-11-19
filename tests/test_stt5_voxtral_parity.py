import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).parents[1] / 'scripts/speech'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('voxtral_parity', SCRIPTS / 'stt5_voxtral_parity.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def witness(ids=(32, 100, 32)):
    return '\n'.join([f'CS8_VOXTRAL_TOKENS {len(ids)}'] +
                     [f'CS8_VOXTRAL_TOKEN {i} {v}' for i, v in enumerate(ids)] +
                     ['CS8_VOXTRAL_TOKENS_END'])


class ParityTest(unittest.TestCase):
    def test_native_agreement_requires_success_and_residency(self):
        expected = ['/lib/libggml.so', '/lib/libcrispasr.so']
        for rc, stopped, loaded, verdict in [
                (0, False, expected, 'PASS'), (1, False, expected, 'INCONCLUSIVE'),
                (0, True, expected, 'INCONCLUSIVE'), (0, False, [], 'INCONCLUSIVE'),
                (0, False, expected + ['/foreign/libggml.so'], 'INCONCLUSIVE'),
                (0, False, expected + ['/foreign/libcrispasr.so'], 'INCONCLUSIVE')]:
            with self.subTest(rc=rc, stopped=stopped, loaded=loaded):
                self.assertEqual(m.evaluate('', witness(), witness(), rc, stopped,
                                            loaded, expected)['verdict'], verdict)

    def test_token_difference_is_fail_and_broken_witness_is_unknown(self):
        for actual, expected in [(witness((32, 100)), 'FAIL'), ('', 'INCONCLUSIVE'),
                                 (witness() + '\n' + witness(), 'INCONCLUSIVE')]:
            self.assertEqual(m.evaluate(actual, '', witness(), 0, False,
                                        ['/lib'], ['/lib'])['verdict'], expected)

    def test_duplicate_stream_witness_refused(self):
        self.assertEqual(m.evaluate(witness(), witness(), witness(), 0, False,
                                    ['/lib'], ['/lib'])['verdict'], 'INCONCLUSIVE')

    def test_reservation_prevents_redraw_even_without_exposure_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = m.admit_case(Path(tmp), '480')
            self.assertTrue(case.is_dir())
            with self.assertRaisesRegex(ValueError, 'no redraw'):
                m.admit_case(Path(tmp), '480')
            m.admit_case(Path(tmp), '960')

    def test_exclusive_receipt_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'result.json'
            m.write_new(path, {'verdict': 'FAIL'})
            with self.assertRaises(FileExistsError):
                m.write_new(path, {'verdict': 'PASS'})
            self.assertEqual(json.loads(path.read_text())['verdict'], 'FAIL')

    def test_cpu_argv_is_fixed(self):
        cfg = dict(model='/model', audio='/public', variants={'480': dict(runner='/v480')})
        self.assertEqual(m.command(cfg, '480'), ['/v480', '--backend', 'cpu', '--no-gpu',
                         '--threads', '1', '-m', '/model', '-f', '/public'])

    def test_owned_child_timeout_escalates_and_reaps(self):
        child = mock.Mock()
        child.poll.side_effect = [None, 0]
        child.wait.side_effect = [subprocess.TimeoutExpired('owned', 5), 0]
        m.drain(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)

    def test_preflight_binds_receipt_and_each_delay_to_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / 'model.gguf'
            model.write_bytes(b'not a model')
            receipt = root / 'model-receipt.json'
            st = model.stat()
            prepared = dict(verdict='PASS', download_rc=0, sha256=m.MODEL_SHA,
                            size=st.st_size, revision=m.REVISION, path=str(model),
                            model_stat=[st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns])
            receipt.write_text(json.dumps(prepared))
            audio = root / 'audio.wav'
            audio.write_bytes(b'public fixture stand-in')
            variants = {}
            artifacts = {}
            refs = {}
            for delay in ('480', '960'):
                directory = root / ('voxtral' + delay)
                directory.mkdir()
                runner = directory / 'runner'
                runner.write_bytes(b'ELF stand-in ' + delay.encode())
                lib = directory / 'libggml.so'
                lib.write_bytes(b'library stand-in')
                reference = directory / 'reference.log'
                reference.write_text(witness())
                refs[delay] = m.sha(reference)
                variants[delay] = dict(runner=str(runner), reference=str(reference),
                                       expected_maps=[str(lib)])
                artifacts.update({str(p): m.sha(p) for p in (runner, lib)})
            build = root / 'summary.json'
            build.write_text(json.dumps(dict(verdict='PASS', smoke=False,
                source_commit='2aa8d7669fcaa18d98d61a4bc8a077464e6b9919', artifacts=artifacts)))
            cfg = dict(model=str(model), model_receipt=str(receipt), build_summary=str(build),
                       audio=str(audio), variants=variants,
                       pins={str(p): m.sha(p) for p in root.rglob('*')
                             if p.is_file() and p != model})
            with mock.patch.object(m, 'MODEL_SIZE', st.st_size), \
                    mock.patch.object(m, 'JFK_SHA', m.sha(audio)), \
                    mock.patch.object(m, 'REFERENCES', refs):
                m.verify(cfg)
                bad = copy.deepcopy(cfg)
                bad['pins'][str(model)] = 'must not be hashed'
                with self.assertRaisesRegex(ValueError, 'weight hashing'):
                    m.verify(bad)
                alias = root / 'model-alias.bin'
                alias.hardlink_to(model)
                bad = copy.deepcopy(cfg)
                bad['pins'][str(alias)] = 'must not be hashed through a hard link'
                with self.assertRaisesRegex(ValueError, 'weight hashing'):
                    m.verify(bad)
                for mutation, pattern in [
                        (lambda c: c['pins'].pop(str(audio)), 'missing required'),
                        (lambda c: c['variants'].pop('960'), 'both delay'),
                        (lambda c: c['variants']['480'].update(runner=variants['960']['runner']), 'delay/runtime'),
                        (lambda c: c['pins'].update({str(audio): 'wrong'}), 'original public JFK')]:
                    bad = copy.deepcopy(cfg)
                    mutation(bad)
                    with self.subTest(pattern=pattern), self.assertRaisesRegex(ValueError, pattern):
                        m.verify(bad)
                bad = copy.deepcopy(cfg)
                bad['pins'][variants['480']['reference']] = 'different reference'
                with self.assertRaisesRegex(ValueError, 'original delay-specific'):
                    m.verify(bad)
                for field, value in [('verdict', 'FAIL'), ('download_rc', 28),
                                     ('sha256', 'wrong'), ('revision', 'wrong'),
                                     ('path', '/different-model')]:
                    altered = {**prepared, field: value}
                    receipt.write_text(json.dumps(altered))
                    bad = copy.deepcopy(cfg)
                    bad['pins'][str(receipt)] = m.sha(receipt)
                    with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'model receipt/stat'):
                        m.verify(bad)
                receipt.write_text(json.dumps(prepared))
                # Re-pinning a changed runtime cannot bypass the build receipt.
                runner = Path(variants['480']['runner'])
                runner.write_bytes(b'changed runtime')
                bad = copy.deepcopy(cfg)
                bad['pins'][str(runner)] = m.sha(runner)
                with self.assertRaisesRegex(ValueError, 'final build'):
                    m.verify(bad)
                runner.write_bytes(b'ELF stand-in 480')
                model.write_bytes(b'changed model bytes')
                with self.assertRaisesRegex(ValueError, 'model receipt/stat'):
                    m.verify(cfg)


if __name__ == '__main__':
    unittest.main()
