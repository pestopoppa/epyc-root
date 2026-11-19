"""Composed consumer and actual bounded HTTP controls; no native/model run."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import install

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/mnt/raid0/llm/tmp/kvu/transport-compose-20261119')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRATCH.mkdir(parents=True, exist_ok=True)
TEMP = tempfile.TemporaryDirectory(dir=SCRATCH)
OUTPUT = Path(TEMP.name) / 'successor'
SEAL = install.install(OUTPUT)
sys.path[:0] = [str(OUTPUT), SEAL['dependency_path']]
transport = load('cancel_seed_transport', OUTPUT / 'cancel_seed_transport.py')
sys.modules['cancel_seed_transport'] = transport
helper = sys.modules['slots_transport']
old = load('previous_consumer_tests', HERE.parent / 'kpf18-seed-cleanup-20261119/test_consumer.py')
http_tests = load('previous_slots_tests', HERE.parent / 'kpf18-g3-slots-deadline-result-20261105/test_slots.py')


class ComposedConsumer(old.Consumer):
    @classmethod
    def setUpClass(cls):
        cls.module = transport

    @classmethod
    def tearDownClass(cls):
        pass

    def exercise(self, *args, **kwargs):
        # Native/SSE peers are synthetic; exercise the installed consumer, with
        # slots transport tested through real sockets by ActualBoundedHTTP.
        with patch.object(transport, 'bounded_slots', side_effect=lambda ctx, **kw: ctx.client.slots()):
            return super().exercise(*args, **kwargs)


class ActualBoundedHTTP(http_tests.Slots):
    pass


class Cleanup(unittest.TestCase):
    def exercise(self, primary=False, response_error=True, connection_error=False):
        stop = type('Stop', (RuntimeError,), {})('typed STOP')
        closed = []
        class Response:
            status = 200
            def read(self, limit):
                if primary:raise stop
                return b'[{"id":1}]'
            def close(self):
                closed.append('response')
                if response_error:raise OSError('response close failed')
        class Connection:
            def __init__(self, *a, **kw):self.sock=NS(shutdown=lambda *a: None)
            def connect(self):pass
            def request(self, *a, **kw):pass
            def getresponse(self):return Response()
            def close(self):
                closed.append('connection')
                if connection_error:raise OSError('connection close failed')
        ctx = NS(check_boundary=lambda: None, client=NS(base='http://127.0.0.1:8083'),
                 args=NS(port=8083), deadline=NS(remaining=lambda: 1))
        with patch.object(helper.http.client, 'HTTPConnection', Connection):
            with self.assertRaises(RuntimeError if primary else OSError) as caught:
                helper.bounded_slots(ctx)
        self.assertEqual(closed, ['response', 'connection'])
        if primary:
            self.assertIs(caught.exception, stop)
            self.assertTrue(any('cleanup failed' in n for n in stop.__notes__))

    def test_response_failure_closes_connection(self):self.exercise()
    def test_stop_survives_response_cleanup(self):self.exercise(primary=True)
    def test_stop_survives_both_cleanup_failures(self):self.exercise(primary=True, connection_error=True)
    def test_connection_failure_propagates(self):self.exercise(response_error=False, connection_error=True)
    def test_installed_entry_disabled(self):
        result = subprocess.run(['bash', str(OUTPUT / 'launch.sh')], capture_output=True)
        self.assertEqual(result.returncode, 78)
        self.assertFalse(SEAL['runtime_dispatch'])
        self.assertFalse((OUTPUT / 'INCOMPLETE').exists())
        for name, digest in SEAL['sources'].items():
            self.assertEqual(install.digest(Path(name)), digest)
    def test_existing_destination_refused(self):
        with self.assertRaises(ValueError):install.install(OUTPUT)
    def test_outside_scratch_refused(self):
        with self.assertRaises(ValueError):install.install(Path('/tmp/kvu-should-not-exist'))


def tearDownModule():
    TEMP.cleanup()


if __name__ == '__main__':unittest.main()
