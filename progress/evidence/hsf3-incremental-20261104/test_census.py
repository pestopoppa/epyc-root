import hashlib,json,tempfile,unittest
from pathlib import Path
from census import scan

def prior(b): return {'source_frontiers':[{'source_class':'progress_jsonl','bytes_hashed_and_scanned':len(b),'sha256_hashed_and_scanned_bytes':hashlib.sha256(b).hexdigest()}]}
class Tests(unittest.TestCase):
 def test_tail_count_excludes_prior_and_incomplete(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'p'; b=b'{"event":"session_created"}\n'; p.write_bytes(b+b'{"event":"session_resumed"}\n'+b'{"event":"incomplete"}')
   x=scan([p],prior(b))['progress']; self.assertEqual((x['json_records'],x['target_events']),(1,1))
 def test_mutated_old_or_partial_frontier_are_unknown(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'p'; b=b'old\n'; p.write_bytes(b'bad\nnew\n'); self.assertEqual(scan([p],prior(b))['progress']['files_unmatched'],1)
   p.write_bytes(b'oldmore\n'); self.assertEqual(scan([p],prior(b'old'))['progress']['files_unmatched'],1)
 def test_duplicate_current_frontier_refused(self):
  with tempfile.TemporaryDirectory() as t:
   a=Path(t)/'a'; b=Path(t)/'b'; a.write_bytes(b'old\n'); b.write_bytes(b'old\n');
   with self.assertRaises(ValueError): scan([a,b],prior(b'old\n'))
 def test_invalid_and_nonobject_not_counted(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'p'; old=b'old\n'; p.write_bytes(old+b'bad\n[]\n{}\n'); x=scan([p],prior(old))['progress']; self.assertEqual((x['json_records'],x['invalid_json']),(1,2))
if __name__=='__main__': unittest.main()
