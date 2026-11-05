import hashlib,json,pathlib,tempfile,unittest
from verify_receipt import verify
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.t.name)
  self.data=b'C,1,1,0\nA,7,3,12,10,20,123\n'
  self.r={'schema':'c6.sdk-buffer-receipt.v1','pid':123,'setup_status':0,'start_status':0,'stop_status':0,'flush_status':0,'bad_headers':0,'nonzero_drop_callbacks':0,'io_error':0,'callbacks':1,'headers_seen':1}
 def tearDown(self):self.t.cleanup()
 def runverify(self):
  (self.p/'records.csv').write_bytes(self.data);self.r['records_sha256']=hashlib.sha256(self.data).hexdigest();(self.p/'receipt.json').write_text(json.dumps(self.r));return verify(self.p,123)
 def test_consistent(self):self.assertEqual(self.runverify()['status'],'CONSISTENT_UNAUTHENTICATED')
 def test_drop(self):
  self.data=self.data.replace(b'C,1,1,0',b'C,1,1,1')
  with self.assertRaises(ValueError):self.runverify()
 def test_failure_status(self):
  self.r['flush_status']=1
  with self.assertRaises(ValueError):self.runverify()
 def test_wrong_pid(self):
  self.r['pid']=124
  with self.assertRaises(ValueError):self.runverify()
 def test_record_pid(self):
  self.data=self.data.replace(b'20,123',b'20,124')
  with self.assertRaises(ValueError):self.runverify()
 def test_truncated(self):
  self.data=self.data[:-1]
  with self.assertRaises(ValueError):self.runverify()
 def test_mismatched_count(self):
  self.r['headers_seen']=2
  with self.assertRaises(ValueError):self.runverify()
 def test_digest_drift(self):
  self.runverify();(self.p/'records.csv').write_bytes(b'changed\n')
  with self.assertRaises(ValueError):verify(self.p,123)
if __name__=='__main__':unittest.main(verbosity=2)
