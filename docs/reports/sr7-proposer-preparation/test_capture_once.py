import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from capture_once import capture_once

TRACE = (b'statistics ngram-mod: #calls(b,g,a) = 1 4 3, #gen drafts = 3, #acc drafts = 2, #gen tokens = 10, #acc tokens = 8\n'
         b'statistics draft-mtp: #calls(b,g,a) = 1 4 3, #gen drafts = 3, #acc drafts = 2, #gen tokens = 30, #acc tokens = 12\n')

class CaptureOnceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.events = []
        self.root = Path(self.tmp.name)
        self.args = dict(root=self.root, request_id='p1', payload={'prompt':'hello','cache_prompt':False,'stream':False,'n_predict':4}, expected_names=['ngram-mod','draft-mtp'], port=10001, timeout_s=1,
                         admit=lambda: True, launch=lambda: object(), verify=lambda p,port: {'pid':1}, stop=lambda p:self.events.append('stop'), read_trace=lambda p:TRACE,
                         post=lambda port,payload,timeout:(200,json.dumps({'timings':{'draft_n':40,'draft_n_accepted':20}}).encode()))
    def test_capture_reconciles_and_blocks_retry(self):
        result = capture_once(**self.args)
        self.assertEqual(result['acceptance'], .5)
        self.assertEqual(self.events, ['stop'])
        self.assertTrue((self.root/'p1.trace.bin').exists())
        with self.assertRaises(FileExistsError): capture_once(**self.args)
    def test_transport_failure_leaves_exposure_and_stops(self):
        def fail(*a): raise TimeoutError('x')
        self.args['post'] = fail
        with self.assertRaises(TimeoutError): capture_once(**self.args)
        self.assertTrue((self.root/'p1.exposure.json').exists())
        self.assertTrue((self.root/'p1.error.json').exists())
        self.assertEqual(self.events, ['stop'])
    def test_wrong_counters_retains_raw_and_trace(self):
        self.args['post'] = lambda *a: (200,b'{"timings":{"draft_n":41,"draft_n_accepted":20}}')
        with self.assertRaises(ValueError): capture_once(**self.args)
        self.assertTrue((self.root/'p1.response.bin').exists())
        self.assertTrue((self.root/'p1.trace.bin').exists())
        self.assertFalse((self.root/'p1.parsed.json').exists())
    def test_denied_admission_never_launches(self):
        self.args['admit'] = lambda: False
        self.args['launch'] = lambda: self.fail('launched')
        with self.assertRaises(ValueError): capture_once(**self.args)
        self.assertEqual(list(self.root.iterdir()), [])
    def test_directory_sync_failure_prevents_launch(self):
        self.args['launch'] = lambda: self.fail('launched')
        with patch('capture_once.os.fsync', side_effect=[None, OSError('directory sync failed')]):
            with self.assertRaises(OSError): capture_once(**self.args)

if __name__ == '__main__': unittest.main()
