import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import prepare as m


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='g3-successor-test-',dir='/mnt/raid0/llm/tmp/kvfork')
        cls.out=Path(cls.temp.name)/'successor'
        m.prepare(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def entry(self,*args):
        return subprocess.run(['bash',str(self.out/'launch.sh'),*args],capture_output=True,text=True)

    def test_both_barriers_and_custody(self):
        self.assertEqual(self.entry('custody-check').returncode,0)
        for mode in ((),('official',),('normal',),('cutoff',)):
            self.assertEqual(self.entry(*mode).returncode,78)
            r=subprocess.run(['bash',str(self.out/'candidate/launch.sh'),*mode],capture_output=True)
            self.assertEqual(r.returncode,78)

    def test_integrated_transport_and_boundary(self):
        transport=(self.out/'candidate/vendor/cancel_seed_transport.py').read_text()
        self.assertIn('with SocketDeadline(captured_socket,transport_deadline)',transport)
        self.assertIn('watchdog.check()',transport)
        self.assertIn('lock_witness.boundary()', (self.out/'candidate/guard.py').read_text())
        self.assertEqual(m.sha((self.out/'candidate/current_lock.py').read_bytes()),m.WITNESS_PIN)
        self.assertEqual(m.sha((self.out/'candidate/provider-sources.json').read_bytes()),m.PROVIDER_PIN)
        self.assertEqual(m.sha((m.SOURCE/'SOURCES.sha256').read_bytes()),m.RUNTIME_PIN)
        self.assertEqual(m.sha((m.SOURCE/'launch.sh').read_bytes()),m.LAUNCH_PIN)

    def test_source_drift_and_incomplete_refuse(self):
        for relative in ('candidate/vendor/socket_deadline.py','candidate/provider-sources.json','candidate/lock_witness.py','candidate/SOURCES.sha256'):
            path=self.out/relative;raw=path.read_bytes()
            try:
                path.write_bytes(raw+b'\n# drift\n')
                self.assertNotEqual(self.entry('custody-check').returncode,0)
            finally:
                path.write_bytes(raw)
        (self.out/'INCOMPLETE').touch()
        try:
            self.assertEqual(self.entry('custody-check').returncode,78)
        finally:
            (self.out/'INCOMPLETE').unlink()
        self.assertEqual(self.entry('custody-check').returncode,0)

    def test_wrong_review_pin_and_duplicate_destination_refuse(self):
        with self.assertRaises(ValueError):
            m.pinned(m.SOURCE/'SOURCES.sha256','0'*64)
        with self.assertRaises(ValueError):
            m.prepare(self.out)
        with self.assertRaises(ValueError):
            m.inventory(self.out,b'0'*64+b'  ../escape\n')

    def test_adapter_requires_exact_row_and_retains_witness(self):
        witness={'owner':123,'row_id':m.ROW}
        module=types.ModuleType('current_lock');calls=[]
        module.capture=lambda row,sources:(calls.append((row,sources)) or witness)
        module.recheck=lambda value:(calls.append(value) or True)
        with patch.dict(sys.modules,{'current_lock':module}):
            spec=importlib.util.spec_from_file_location('g3_adapter_fixture',self.out/'candidate/lock_witness.py')
            adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
            with patch.dict(os.environ,{'FILLER_ID':'historical'}):
                with self.assertRaises(ValueError):adapter.capture_gpu()
            with patch.dict(os.environ,{'FILLER_ID':m.ROW}):
                owner,identity=adapter.capture_gpu()
                self.assertEqual(calls[0],(m.ROW,json.loads((self.out/'candidate/provider-sources.json').read_text())))
                self.assertIs(identity,witness)
                self.assertTrue(adapter.verify_gpu(owner,identity))
                with self.assertRaises(ValueError):adapter.verify_gpu(999,identity)
                module.recheck=lambda value:(_ for _ in ()).throw(ValueError('writer changed'))
                with self.assertRaises(ValueError):adapter.boundary()

class IndependentValidation(unittest.TestCase):
    def test_reviewed_r9_closure_and_refusals(self):
        raw,paths=m.validation_closure(m.R9_RECEIPT,m.R9_RECEIPT_PIN)
        self.assertEqual([c['verified_entries'] for c in json.loads(raw)['checks']],[29,14,22])
        self.assertIn(str(m.R9_RECEIPT),paths)
        with self.assertRaises(ValueError):
            m.validation_closure(m.R9_RECEIPT,'0'*64)
        with tempfile.TemporaryDirectory(prefix='g3-r9-refusal-',dir='/mnt/raid0/llm/tmp/kvfork') as directory:
            root=Path(directory);receipt=root/'RESULT.json'
            result=json.loads(raw);result['checks'].pop()
            receipt.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError,'incomplete independent'):
                m.validation_closure(receipt,m.sha(receipt.read_bytes()))
            result=json.loads(raw)
            manifest=root/'manifest'
            manifest.write_bytes(Path(result['checks'][0]['manifest']).read_bytes()+b'\n')
            result['checks'][0]['manifest']=str(manifest)
            receipt.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError,'manifest digest mismatch'):
                m.validation_closure(receipt,m.sha(receipt.read_bytes()))
            (root/'INCOMPLETE').touch()
            with self.assertRaisesRegex(ValueError,'validation incomplete'):
                m.validation_closure(receipt,m.sha(receipt.read_bytes()))

if __name__=='__main__':unittest.main()
