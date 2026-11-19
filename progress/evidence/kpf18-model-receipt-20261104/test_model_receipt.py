import hashlib, json, pathlib, sys, tempfile, types, unittest
from unittest import mock
sys.modules['gguf_identity'] = types.SimpleNamespace(metadata=lambda p: None)
import model_receipt as m
import prepare as prep

class Receipt(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.d=pathlib.Path(self.tmp.name)
  self.paths={k:self.d/k for k in m.ROLES}
  for p in self.paths.values():p.write_bytes(b'fake weight bytes')
  self.original={k:{'path':str(v),'sha256':hashlib.sha256(v.read_bytes()).hexdigest()} for k,v in self.paths.items()}
  def fake(path):
   return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'stat_identity':m.signature(path),'metadata':{'general.architecture':'dflash','dflash.block_count':5,'dflash.attention.sliding_window':2048,'dflash.attention.sliding_window_pattern':[True]*5}}
  self.patch=mock.patch.object(prep,'metadata',side_effect=fake);self.patch.start()
  self.receipt=self.d/'receipt.json';self.sha=prep.prepare(self.paths,self.original,self.receipt)
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def test_runtime_never_reads_weights(self):
  with mock.patch.object(prep,'metadata',side_effect=AssertionError('hash forbidden')):
   self.assertEqual(m.load_verified(self.receipt,self.sha,self.paths,self.original)['draft_cache_shape']['draft_swa_layers'],5)
 def test_changed_weight_refused(self):
  self.paths['target'].write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'stat changed'):m.load_verified(self.receipt,self.sha,self.paths,self.original)
 def test_receipt_mutation_refused(self):
  self.receipt.write_bytes(self.receipt.read_bytes()+b' ')
  with self.assertRaisesRegex(ValueError,'altered'):m.load_verified(self.receipt,self.sha,self.paths,self.original)
 def test_wrong_model_path_refused(self):
  paths=dict(self.paths);paths['target']=paths['drafter']
  with self.assertRaisesRegex(ValueError,'identity mismatch'):m.load_verified(self.receipt,self.sha,paths,self.original)
 def test_symlink_receipt_and_model_refused(self):
  link=self.d/'link';link.symlink_to(self.receipt)
  with self.assertRaises(OSError):m.load_verified(link,self.sha,self.paths,self.original)
  self.paths['target'].unlink();self.paths['target'].symlink_to(self.paths['drafter'])
  with self.assertRaisesRegex(ValueError,'regular file'):m.load_verified(self.receipt,self.sha,self.paths,self.original)
 def test_receipt_not_overwritten(self):
  with self.assertRaises(FileExistsError):prep.prepare(self.paths,self.original,self.receipt)

if __name__=='__main__':unittest.main()
