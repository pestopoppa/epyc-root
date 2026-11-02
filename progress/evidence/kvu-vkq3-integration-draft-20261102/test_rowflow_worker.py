import datetime as dt
import hashlib
import os
from pathlib import Path
import signal
import tempfile
import sys
import unittest
from unittest import mock
import rowflow_worker as rw


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.grants = self.root / 'grants'; self.grants.mkdir()
        self.t = 1793613600; self.end = self.t + 3600
        stamp = lambda n: dt.datetime.fromtimestamp(n, dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        (self.grants/'sample.grant').write_text(f'regions=0-95 start={stamp(self.t-60)} end={stamp(self.end)} holds=\n')
        self.env = {'FILLER_ID':'sample', 'FILLER_NEEDGPU':'0', 'FILLER_CPUS':'0-95',
                    'FILLER_END':str(self.end), 'FILLER_DEADLINE':str(self.end-90),
                    'FILLER_STOPFILE':str(self.root/'stop'), 'FILLER_GRANTS_DIR':str(self.grants)}
        files = []
        for name in ('full', 'short', 'tokenizer', 'model', 'library'):
            p = self.root/name; p.write_bytes(b'test'); files.append(str(p))
        full, short, tokenizer, model, library = files
        files += [sys.executable, str(rw._WRAPPER)]
        self.plan = dict(id='sample', grant_dir=str(self.grants), local_stop=str(self.root/'local-stop'),
            result_path=str(self.root/'full.jsonl'), qualification_input=short, full_input=full,
            tokenizer=tokenizer, model=model, model_files=[model], runtime_files=[library], library_path=str(self.root),
            input_sha256={'full': hashlib.sha256(b'test').hexdigest(),
                          'qualification': hashlib.sha256(b'test').hexdigest()},
            inputs={p:rw._stat(p) for p in files}, identity_sha256={p:'a'*64 for p in files}, input_limit=10, cleanup_margin_s=2,
            attempt_id='test', receipt_root=str(self.root))
        self.plan['identity_sha256'][full] = hashlib.sha256(b'test').hexdigest()
        self.plan['identity_sha256'][short] = hashlib.sha256(b'test').hexdigest()

    def test_guard_through_publication_and_signal_restored(self):
        prior = signal.getsignal(signal.SIGTERM)
        def worker(**kw):
            self.assertEqual(kw['mode'], 'full'); self.assertTrue(kw['grant_valid']())
            self.assertEqual(kw['argv'][0], self.plan['tokenizer'])
            return self.root/'attempt'
        def publish(mode, attempt, directory, result, *, before_publish):
            before_publish()
            self.assertEqual((mode, attempt, directory), ('full','test',self.root/'attempt'))
            self.assertNotEqual(signal.getsignal(signal.SIGTERM), prior)
        rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t, worker=worker, publish=publish)
        self.assertEqual(signal.getsignal(signal.SIGTERM), prior)

    def test_grant_revocation_prevents_publication(self):
        def worker(**kw):
            (self.grants/'sample.grant').unlink()
            return self.root/'attempt'
        with mock.patch('rowflow_worker.publish_unit') as publish:
            with self.assertRaisesRegex(RuntimeError, 'grant lost'):
                rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t, worker=worker, publish=publish)
            publish.assert_not_called()

    def test_replaced_input_rejected_before_launch(self):
        Path(self.plan['full_input']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t)

    def test_dryrun_alias_rejected(self):
        self.env.update(FILLER_DRYRUN='1', FILLER_DRYRUN_RESULT_PATH=self.plan['result_path'])
        with self.assertRaisesRegex(ValueError, 'aliases'):
            rw.run(self.plan, self.env)

    def test_native_dryrun_uses_engine_grant_and_output(self):
        drydir = self.root / 'dry'; drydir.mkdir()
        grants = drydir / 'grants'; grants.mkdir()
        stamp = lambda n: dt.datetime.fromtimestamp(n, dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        (grants / 'sample.grant').write_text(
            f'regions=0-3 start={stamp(self.t-60)} end={stamp(self.end)} holds= '
            'schema=epyc.rowflow.dryrun-grant.v1 id=sample kind=rowflow-dryrun\n')
        destination = str(drydir / 'result.json')
        self.env.update(FILLER_DRYRUN='1', FILLER_DRYRUN_DIR=str(drydir),
                        FILLER_GRANTS_DIR=str(grants), FILLER_CPUS='0-3',
                        FILLER_DRYRUN_RESULT_PATH=destination)
        def worker(**kw):
            self.assertEqual(kw['mode'], 'qualification')
            self.assertTrue(kw['grant_valid']())
            return self.root / 'attempt'
        def publish(mode, attempt, directory, result, *, before_publish):
            before_publish()
            self.assertEqual((mode, result), ('qualification', destination))
        self.assertEqual(rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t,
                                worker=worker, publish=publish), destination)

    def test_grant_lost_during_publish_refuses_visibility(self):
        def worker(**kw):
            return self.root / 'attempt'
        def publish(mode, attempt, directory, result, *, before_publish):
            (self.grants/'sample.grant').unlink()
            before_publish()
            self.fail('published after revocation')
        with self.assertRaisesRegex(RuntimeError, 'during result publication'):
            rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t, worker=worker, publish=publish)

    def test_missing_preflight_identity_rejected(self):
        del self.plan['identity_sha256'][self.plan['tokenizer']]
        with self.assertRaisesRegex(ValueError, 'identities'):
            rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t)

    def test_wrong_input_digest_rejected(self):
        self.plan['input_sha256']['full'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'digest'):
            rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t)

    def test_unbound_wrapper_or_model_shard_rejected(self):
        del self.plan['inputs'][str(rw._WRAPPER)]
        del self.plan['identity_sha256'][str(rw._WRAPPER)]
        with self.assertRaisesRegex(ValueError, 'unbound'):
            rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t)
        self.plan['inputs'][str(rw._WRAPPER)] = rw._stat(str(rw._WRAPPER))
        self.plan['identity_sha256'][str(rw._WRAPPER)] = 'a'*64
        self.plan['model_files'].append(str(self.root/'missing-shard'))
        with self.assertRaisesRegex(ValueError, 'unbound'):
            rw.run(self.plan, self.env, now=lambda:10, wall=lambda:self.t)

if __name__ == '__main__': unittest.main()
