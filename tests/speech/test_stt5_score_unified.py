"""Receipt controls for the read-only Unified rescorer; no inference or corpus."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts' / 'speech'
sys.path.insert(0, str(SCRIPTS))
import stt5_score_unified as score


class Receipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/stt5')
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name)
        (self.ledger / 'chunks').mkdir()
        self.record = dict(clip_id='fixture', pcm_sha256='pcm', wav_sha256='wav', frames=16, reference_raw='hello world')
        self.pins = dict(validation_sha256='input', plan_sha256='plan', models={'c1r0': 'model'},
                         runner_binary_sha256={'c1r0': 'bin'}, runner_library_set_sha256={'c1r0': 'lib'})
        self.unit = hashlib.sha256(b'c1r0|auto|fixture|0').hexdigest()
        chunk = dict(status='ok', id='fixture', original_pcm_sha256='pcm', original_wav_sha256='wav', n_samples=16,
                     chunks=[dict(index=0, start_sample=0, end_sample=16, pcm_sha256='pcm', wav_sha256='wav')])
        (self.ledger / 'chunks' / (hashlib.sha256(b'fixture').hexdigest() + '.chunks.json')).write_text(json.dumps(chunk))
        binding = dict(clip_id='fixture', chunk_index=0, chunk_pcm_sha256='pcm', chunk_wav_sha256='wav',
                       input_sha256='input', plan_sha256='plan', source_sha256='source', model_sha256='model',
                       binary_sha256='bin', library_set_sha256='lib', mode='auto')
        (self.ledger / (self.unit + '.exposure.json')).write_text(json.dumps(dict(binding=binding)))
        self.result = dict(binding=binding, rc=0, reaped=True, timedout=False)
        for suffix in ('stdout', 'stderr', 'txt'):
            path = self.ledger / (self.unit + '.' + suffix)
            path.write_text('hello world' if suffix == 'txt' else '')
            self.result[suffix + '_sha256'] = score.sha(path)
        self.save()

    def save(self):
        (self.ledger / (self.unit + '.result.json')).write_text(json.dumps(self.result))

    def read(self, parser=None):
        return score.read_setting(self.ledger, [self.record], self.pins, 'source', 'c1r0',
                                  parser or (lambda out, text: dict(hypothesis_with_unk=text, unk_count=0)))

    def test_success(self):
        rows, failures, ids = self.read()
        self.assertEqual((rows[0]['decode_status'], failures, ids), ('ok', [], [self.unit]))

    def test_failure_stays_full_deletion(self):
        self.result['rc'] = -15
        self.save()
        rows, failures, _ = self.read()
        self.assertEqual(rows[0]['hypothesis_chunks'], [''])
        self.assertEqual(rows[0]['decode_status'], 'error')
        self.assertTrue(rows[0]['unk_count_unknown'])
        self.assertEqual(failures[0]['rc'], -15)

    def test_missing_result_refuses_without_writes(self):
        (self.ledger / (self.unit + '.result.json')).unlink()
        before = sorted(str(p) for p in self.ledger.rglob('*'))
        with self.assertRaises(FileNotFoundError):
            self.read()
        self.assertEqual(before, sorted(str(p) for p in self.ledger.rglob('*')))

    def test_tampered_text_refuses(self):
        (self.ledger / (self.unit + '.txt')).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'output drift'):
            self.read()

    def test_nonempty_token_mismatch_refuses(self):
        def mismatch(*_):
            raise ValueError('token mismatch')
        with self.assertRaisesRegex(ValueError, 'token mismatch'):
            self.read(mismatch)

    def test_empty_decode_is_failure_with_unknown_token_count(self):
        path = self.ledger / (self.unit + '.txt')
        path.write_text('')
        self.result['txt_sha256'] = score.sha(path)
        self.save()
        def no_witness(*_):
            raise ValueError('no witness')
        rows, failures, _ = self.read(no_witness)
        self.assertEqual(rows[0]['decode_status'], 'error')
        self.assertTrue(rows[0]['unk_count_unknown'])
        self.assertTrue(failures[0]['empty'])

    def test_timeout_remains_failure_even_at_rc_zero(self):
        self.result['timedout'] = True
        self.save()
        rows, failures, _ = self.read()
        self.assertEqual(rows[0]['decode_status'], 'error')
        self.assertTrue(failures[0]['timedout'])

    def test_source_drift_refuses(self):
        self.result['binding']['source_sha256'] = 'foreign'
        self.save()
        with self.assertRaisesRegex(ValueError, 'binding'):
            self.read()

    def test_unreaped_and_bool_return_refused(self):
        for key, value in [('reaped', False), ('rc', True)]:
            original = self.result[key]
            self.result[key] = value
            self.save()
            with self.assertRaisesRegex(ValueError, 'binding/reaping'):
                self.read()
            self.result[key] = original


if __name__ == '__main__':
    unittest.main()
