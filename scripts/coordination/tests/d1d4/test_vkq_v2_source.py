"""Model-free controls for the exact VKQ scope in the versioned gate."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
COORD = HERE.parents[1]
V2 = COORD / 'qual_v2'
sys.path.insert(0, str(V2))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
q = load('vkq_v2_source_q', V2 / 'qualify_launcher.py')
router = load('vkq_v2_source_router', COORD / 'qual_router.py')
SOURCE_HASH = 'ea92f6cecd0934519f6044f004a151203964049121b1e1345fd018a5d9416a06'
class VKQSourceContract(unittest.TestCase):
    def setUp(self):
        self.path = HERE / 'fixtures/vkq/manifest.json'
        self.m = json.loads(self.path.read_text())
        self.original_sha = q.sha
    def pin_sha(self, path):
        return SOURCE_HASH if str(path) == self.m['source_manifest'] else self.original_sha(path)
    def test_exact_scope_is_unknown_and_routes_v2(self):
        with patch.object(q, 'sha', side_effect=self.pin_sha):
            m = q.load_manifest(self.path)
            self.assertTrue(q.vkq_bootstrap_allowed(m))
            self.assertIsNone(q.feasible_rate(m, {}))
            self.assertTrue(q.feasible_window(m, None))
            self.assertEqual(q.feasibility_record(m, None)['forecast'], 'UNKNOWN')
        self.assertEqual(router.version(self.path), router.V2)
        with tempfile.TemporaryDirectory() as td:
            legacy = dict(self.m); legacy.pop('qualification_row'); legacy.pop('qualifier_version')
            p = Path(td) / 'legacy.json'; p.write_text(json.dumps(legacy))
            self.assertEqual(router.version(p), router.V1)
    def test_scope_changes_fail_closed(self):
        changes = [('id','other'),('owner','other'),('gib',128),('regions','0-47'),('calibration_only',False),('items',2)]
        with patch.object(q, 'sha', side_effect=self.pin_sha):
            for key,value in changes:
                m = copy.deepcopy(self.m); m[key] = value
                with self.subTest(key=key): self.assertFalse(q.vkq_bootstrap_allowed(m))
            m = copy.deepcopy(self.m); m['job']['sha256'] = '0'*64
            self.assertFalse(q.vkq_bootstrap_allowed(m))
        with patch.object(q, 'sha', return_value='0'*64):
            self.assertFalse(q.vkq_bootstrap_allowed(self.m))
    def test_draft_row_binding_does_not_write_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            flags=Path(td); (flags/'ready').mkdir(); ledger=flags/'FILLERS.md'
            ledger.write_text('| filler-id | owner |\n|---|---|\n'); before=ledger.read_bytes()
            row=flags/'ready'/(self.m['id']+'.row.md'); row.write_bytes((HERE/'fixtures/vkq/row.md').read_bytes())
            m=copy.deepcopy(self.m); m['qualification_row']['path']=str(row)
            q.row_binding(m,flags); self.assertEqual(ledger.read_bytes(),before)
            with self.assertRaises(q.Refused): q.row_binding(m,flags,require_canonical=True)
            row.write_text(row.read_text()+'altered')
            with self.assertRaises(q.Refused): q.row_binding(m,flags)
    def test_calibration_receipt_cannot_be_ordinary_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            flags=Path(td); m=copy.deepcopy(self.m); receipt=flags/'receipt.json'; m['qualification']['receipt']=str(receipt)
            with patch.object(q,'load_manifest',return_value=m):
                with self.assertRaisesRegex(q.Refused,'receipt absent'): q.verify(self.path,flags,False)
                receipt.write_text(json.dumps({'kind':q.KIND,'id':m['id'],'manifest_sha256':q.manifest_digest(m)}))
                with self.assertRaisesRegex(q.Refused,'receipt manifest/id mismatch'): q.verify(self.path,flags,False)
            self.assertNotEqual(q.CALIBRATION_KIND,q.KIND)
    def test_cutoff_must_report_stop_and_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            flags=Path(td); nonce='a'*64; d=flags/'qual'/nonce; d.mkdir(parents=True)
            normal={'id':self.m['id'],'phase':'normal','nonce':nonce}
            cutoff={'id':self.m['id'],'phase':'cutoff','nonce':nonce,'partial':True}
            (d/'proof-normal.json').write_text(json.dumps(normal))
            with patch.object(q,'load_manifest',return_value=self.m),patch.dict(os.environ,{'WS58_QUAL':'1','WS58_QUAL_NONCE':nonce}):
                (d/'proof-cutoff.json').write_text(json.dumps(cutoff))
                with self.assertRaisesRegex(q.Refused,'did not observe active STOP'): q.engine_partial(self.path,flags,nonce)
                cutoff['stop_observed']=True;cutoff['unknown_disposition']='PASS'
                (d/'proof-cutoff.json').write_text(json.dumps(cutoff))
                with self.assertRaisesRegex(q.Refused,'must be UNKNOWN'): q.engine_partial(self.path,flags,nonce)
if __name__ == '__main__': unittest.main()
