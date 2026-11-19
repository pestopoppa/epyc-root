import copy
import unittest
from pathlib import Path
import tempfile
import probe

class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.expected = {'/x/libllama.so': 'a', '/x/libggml.so': 'b'}
        self.good = {'mapped':dict(self.expected), 'hits':1, 'breakpoints':2, 'exit_code':0}
    def test_success_is_prerequisite_only(self):
        self.assertEqual(probe.judge(self.good,self.expected),'PREREQUISITE_ONLY')
    def test_no_llama_mapping(self):
        self.good['mapped']={'/x/libggml.so':'b'}
        with self.assertRaises(probe.Invalid): probe.judge(self.good,self.expected)
    def test_changed_mapping(self):
        self.good['mapped']['/x/libggml.so']='drift'
        with self.assertRaises(probe.Invalid): probe.judge(self.good,self.expected)
    def test_unpinned_mapping(self):
        self.good['mapped']['/other/libggml.so']='b'
        with self.assertRaises(probe.Invalid): probe.judge(self.good,self.expected)
    def test_missing_extra_hit_and_failure(self):
        for key, val in [('hits',0),('hits',2),('breakpoints',1),('exit_code',1)]:
            with self.subTest(key=key,val=val):
                value=copy.deepcopy(self.good); value[key]=val
                with self.assertRaises(probe.Invalid): probe.judge(value,self.expected)
    def test_absent_required_fields(self):
        for key in self.good:
            value=copy.deepcopy(self.good); del value[key]
            with self.subTest(key=key):
                with self.assertRaises(probe.Invalid): probe.judge(value,self.expected)
    def test_pin_drift_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); (path/'libllama.so').write_bytes(b'changed')
            with self.assertRaises(probe.Invalid): probe.pins(path)
    def test_absent_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(OSError): probe.pins(Path(tmp))
    def test_one_shot_refuses_existing_exposure(self):
        with self.assertRaisesRegex(probe.Invalid,'already exposed'): probe.run()

if __name__=='__main__': unittest.main()
