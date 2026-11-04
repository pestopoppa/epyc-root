import concurrent.futures, json, os, tempfile, unittest
from pathlib import Path
from custody import begin

class NoRedraw(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
 def test_new_and_repeat(self):
  begin(self.root,'full-a','run-1')
  self.assertEqual(json.loads((self.root/'full-a.start.json').read_text())['run_id'],'run-1')
  with self.assertRaises(FileExistsError): begin(self.root,'full-a','run-2')
 def test_interrupted_prevents_successor(self):
  begin(self.root,'full-a','run-1')
  with self.assertRaises(ValueError): begin(self.root,'mask-a','run-1')
 def test_completed_predecessor_permits_next(self):
  begin(self.root,'full-a','run-1'); (self.root/'full-a.complete.json').write_text('{}')
  with self.assertRaises(ValueError): begin(self.root,'mask-a','run-1')
  begin(self.root,'mask-a','run-1',validate_prior=lambda dfd, prior, rid: prior=='full-a' and rid=='run-1'); self.assertTrue((self.root/'mask-a.start.json').exists())
 def test_concurrent_same_window_has_one_winner(self):
  def start(n):
   try: begin(self.root,'full-a',f'run-{n}'); return True
   except FileExistsError: return False
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
   self.assertEqual(sum(pool.map(start,range(32))),1)
 def test_rejects_marker_symlink(self):
  (self.root/'full-a.start.json').symlink_to('/dev/null')
  with self.assertRaises(ValueError): begin(self.root,'full-a','run-1')
 def test_rejects_completion_symlink(self):
  begin(self.root,'full-a','run-1'); (self.root/'full-a.complete.json').symlink_to('/dev/null')
  with self.assertRaises(ValueError): begin(self.root,'mask-a','run-1')
 def test_rejects_bad_identity_and_window(self):
  for name, ident in (('full-a','../bad'),('unknown','run-1')):
   with self.assertRaises(ValueError): begin(self.root,name,ident)
 def test_rejects_symlink_directory(self):
  link=self.root/'link';link.symlink_to(self.root, target_is_directory=True)
  with self.assertRaises(OSError): begin(link,'full-a','run-1')
if __name__=='__main__': unittest.main()
