import json,tempfile,unittest
from pathlib import Path
from trace_manifest import publish
class Tests(unittest.TestCase):
 def test_cases(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);name='full-a.run1.trace.csv';(p/'full-a.start.json').write_text(json.dumps({'schema':'kpf50.window-start.v1','window':'full-a','run_id':'run1'}))
   for s in ('','KernelName,BeginNs,EndNs\n','KernelName,BeginNs,EndNs\nk,9,9\n'):
    (p/name).write_text(s)
    with self.assertRaises(ValueError):publish(p,'full-a','run1',[name])
   (p/name).write_text('KernelName,BeginNs,EndNs\nk,9,10\n');r=publish(p,'full-a','run1',[name]);self.assertEqual(r['window'],'full-a')
   with self.assertRaises(FileExistsError):publish(p,'full-a','run1',[name])
 def test_wrong_run(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'full-a.start.json').write_text(json.dumps({'schema':'kpf50.window-start.v1','window':'full-a','run_id':'run1'}))
   with self.assertRaises(ValueError):publish(p,'full-a','run1',['full-a.run2.trace.csv'])
if __name__=='__main__':unittest.main()
