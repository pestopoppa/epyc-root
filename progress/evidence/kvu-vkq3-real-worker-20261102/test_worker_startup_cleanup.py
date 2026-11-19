"""A server captured by Popen is drained even if early bookkeeping fails."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import worker
from test_port_worker_integration import FakeServer, Guard


class StartupCleanupTests(unittest.TestCase):
    def exercise(self, failure):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            root = Path(tmp)
            source = root / 'source'; source.mkdir()
            kernel = root / 'kernel'; kernel.mkdir()
            (kernel / 'llama-server').write_bytes(b'fake binary')
            (source / 'PLAN.json').write_text(json.dumps({
                'id': 'fixture', 'arms': [{'id': 'hybrid', 'GGML_FA_VKQ_F16': None}],
                'request': {'temperature': 0},
            }))
            for name in ('FULL-MODELS.sha256', 'RUNTIME-INPUTS.sha256', 'SOURCE-SHA256SUMS'):
                (source / name).write_text('fixture\n')
            drydir = root / 'dry'; attempt = drydir / 'native-attempts' / 'attempt-fixture'
            attempt.mkdir(parents=True)
            out = attempt / 'vkq3-control'; native = attempt / 'native-result.json'
            captured = []

            def launch(cmd, **kwargs):
                child = FakeServer(cmd, own_listener=False, **kwargs)
                captured.append((child, kwargs['stdout']))
                return child

            original_read = Path.read_text
            def read_text(path, *args, **kwargs):
                if failure == 'birth' and str(path) == f'/proc/{os.getpid()}/stat':
                    raise OSError('injected birth read failure')
                return original_read(path, *args, **kwargs)

            original_atom = worker.atom
            def atom(path, value):
                if failure == 'receipt' and path.name == 'hybrid.server.json':
                    raise OSError('injected receipt failure')
                return original_atom(path, value)

            env = {'FILLER_DRYRUN': '1', 'FILLER_DRYRUN_DIR': str(drydir),
                   'FILLER_STOPFILE': str(root / 'stop')}
            with mock.patch.dict(os.environ, env, clear=True), \
                 mock.patch.object(worker, 'D', source), mock.patch.object(worker, 'K', kernel), \
                 mock.patch.object(worker, 'grant_context', return_value=(Guard(), out, native)), \
                 mock.patch.object(worker.signal, 'signal'), \
                 mock.patch.object(worker.subprocess, 'Popen', side_effect=launch), \
                 mock.patch.object(Path, 'read_text', read_text), \
                 mock.patch.object(worker, 'atom', side_effect=atom), \
                 mock.patch.object(worker.urllib.request, 'urlopen') as http:
                with self.assertRaisesRegex(OSError, 'injected'):
                    worker.main()
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0][0].returncode, 0)
            self.assertTrue(captured[0][1].closed)
            self.assertTrue(json.loads((out / 'hybrid.drain.json').read_text())['drained'])
            self.assertFalse(native.exists())
            http.assert_not_called()

    def test_birth_read_failure_drains_captured_server(self):
        self.exercise('birth')

    def test_server_receipt_failure_drains_captured_server(self):
        self.exercise('receipt')


if __name__ == '__main__':
    unittest.main()
