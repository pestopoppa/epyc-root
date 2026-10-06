"""Actual byte-rebase builder fixtures; no canonical records or source claims."""
import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts/vidya'))
from rebase_current_index import prepare,validate_rebase_custody

class IndexRebaseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name)
  self.ids=['intake-'+str(i) for i in range(2000,2030)]
  def record(k,text):return ('- id: '+k+'\n  key_claims:\n  - '+text+'\n').encode()
  self.old=b'# native fixture\n'+b''.join(record(k,'historical') for k in self.ids)
  self.review=b'# native fixture\n'+b''.join(record(k,'reviewed') for k in self.ids)
  self.current=self.old+record('intake-3000','peer untouched')
  for n,b in [('old',self.old),('review',self.review),('current',self.current)]: (self.d/n).write_bytes(b)
  (self.d/'source').write_text(json.dumps({'target_ids':self.ids[:22]}));(self.d/'demote').write_text(json.dumps({'targets':[{'entry_id':k} for k in self.ids[22:]]}))
 def build(self):
  with contextlib.redirect_stdout(io.StringIO()):prepare(self.d/'old',self.d/'review',self.d/'current',self.d/'source',self.d/'demote',self.d/'out','synthetic-commit')
 def test_actual_builder_preserves_peer_bytes(self):
  self.build();receipt=json.loads((self.d/'out/index-rebase-receipt.json').read_text());candidate=(self.d/'out/candidate.intake_index.yaml').read_bytes()
  self.assertEqual(candidate,self.review+self.current[len(self.old):]);self.assertTrue(validate_rebase_custody(receipt,self.review,self.current,candidate,set(self.ids)))
 def test_current_target_change_refuses_before_output(self):
  (self.d/'current').write_bytes(self.current.replace(b'historical',b'peer change',1))
  with self.assertRaisesRegex(ValueError,'target base blocks changed'):self.build()
  self.assertFalse((self.d/'out').exists())
 def test_post_preparation_peer_byte_tamper_rejected(self):
  self.build();receipt=json.loads((self.d/'out/index-rebase-receipt.json').read_text());candidate=(self.d/'out/candidate.intake_index.yaml').read_bytes().replace(b'peer untouched',b'peer altered')
  with self.assertRaisesRegex(ValueError,'custody SHA mismatch'):validate_rebase_custody(receipt,self.review,self.current,candidate,set(self.ids))
if __name__=='__main__':unittest.main()
