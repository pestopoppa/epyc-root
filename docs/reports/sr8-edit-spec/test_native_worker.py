import json
import tempfile
from unittest.mock import patch
from pathlib import Path
import unittest
from native_worker import stats_from_log, Invalid, check_structure, run_fixture, capture_native_record, sha_file

class TestStats(unittest.TestCase):
    def test_real_shape(self):
        log='statistics     draft-dflash: #calls(b,g,a) = 1 8 6, #gen drafts = 8, #acc drafts = 4, #gen tokens = 32, #acc tokens = 20'
        self.assertEqual(stats_from_log(log,'current_dflash2'),(6,32,20))
    def test_wrong_or_ambiguous(self):
        with self.assertRaises(Invalid): stats_from_log('', 'prompt_lookup')
        one='statistics ngram-simple: #calls(b,g,a) = 1 8 6, #gen drafts = 8, #acc drafts = 4, #gen tokens = 32, #acc tokens = 20'
        with self.assertRaises(Invalid): stats_from_log(one+'\n'+one,'prompt_lookup')
    def test_invalid_counts(self):
        one='statistics ngram-simple: #calls(b,g,a) = 1 8 6, #gen drafts = 8, #acc drafts = 4, #gen tokens = 32, #acc tokens = 33'
        with self.assertRaises(Invalid): stats_from_log(one,'prompt_lookup')
class TestFixture(unittest.TestCase):
    def test_canonical_tax(self):
        task={'id':'t5_bugfix','files':{'tax.py':'def total(price):\n    return price * 0.1\n'},
              'verifier_cmd':"python3 -c \"import tax; assert abs(tax.total(100)-110.0)<1e-6; print('PASS')\""}
        structure=check_structure(task['id'],'<<<FILE: tax.py>>>\ndef total(price):\n    return price * 1.1\n<<<END>>>')
        with tempfile.TemporaryDirectory() as d: self.assertEqual(run_fixture(task,structure,Path(d))['status'],'PASS')
    def test_forbidden_import(self):
        task={'id':'t5_bugfix','files':{},'verifier_cmd':'true'}
        structure=check_structure(task['id'],'<<<FILE: tax.py>>>\nimport os\n<<<END>>>')
        with tempfile.TemporaryDirectory() as d: self.assertEqual(run_fixture(task,structure,Path(d))['status'],'UNKNOWN')

class TestNativeCapture(unittest.TestCase):
    def test_capture_and_grant_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); out=base/'out'; out.mkdir(); grant=base/'job.grant'; grant.write_text('grant=auth')
            (base/'candidate-plan.json').write_text(json.dumps({'corpus_sha256':'c','source_repo_head':'s','rendering_source_sha256':'r'}))
            (base/'preflight.json').write_text(json.dumps({'models':[],'kernel':'k','kernel_sha256':'b','hip':'h','hip_sha256':'g'}))
            for n in ('analysis.py','session_drain.py'): (base/n).write_text(n)
            for n in ('request.json','template-request.json','response.json','server.log','residency.json','edit-structure.json','edit-validity.json'): (out/n).write_text(n)
            digest=sha_file(grant)
            with patch('native_worker.BASE',base):
                capture=capture_native_record({'decode_tps':2.5},out,grant,digest)
                record=json.loads(Path(capture['path']).read_text())
                self.assertEqual(record['native_artifacts']['response']['sha256'],sha_file(out/'response.json'))
                self.assertEqual(record['grant']['sha256'],digest)
                grant.write_text('changed')
                with self.assertRaises(Invalid): capture_native_record({'decode_tps':2.5},out,grant,digest)

if __name__=='__main__': unittest.main()
