#!/usr/bin/env python3
"""Candidate edits after owner review must fail before any live write."""
import hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile,unittest
BASE=pathlib.Path(__file__).resolve().parents[1]
class InstallerPin(unittest.TestCase):
 def test_reviewed_candidate_edit_refused_before_live_write(self):
  live=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grant_ok.sh')
  original=hashlib.sha256(live.read_bytes()).hexdigest()
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   d=pathlib.Path(td)
   for n in ('install_for_ws58.py','REVIEWED-PACKAGE-SHA256.json'):shutil.copy2(BASE/n,d/n)
   for child in ('src/scripts/coordination','keeper'):
    shutil.copytree((BASE.parents[2]/'scripts/coordination') if child=='src/scripts/coordination' else BASE/child,d/child)
   candidate=d/'keeper/grant_ok-v3.sh';candidate.write_bytes(candidate.read_bytes()+b'\n# unreviewed edit\n')
   reviewed=hashlib.sha256((d/'REVIEWED-PACKAGE-SHA256.json').read_bytes()).hexdigest()
   env=dict(os.environ,WS58_OWNER_BOUNDARY='1',WS58_REVIEWED_PACKAGE_SHA256=reviewed)
   run=subprocess.run([sys.executable,str(d/'install_for_ws58.py'),'--apply'],env=env,text=True,capture_output=True)
   self.assertNotEqual(run.returncode,0)
   self.assertIn('candidate bytes differ',run.stderr+run.stdout)
  self.assertEqual(hashlib.sha256(live.read_bytes()).hexdigest(),original)
if __name__=='__main__':unittest.main()
