import hashlib,json,unittest
from pathlib import Path
R=Path(__file__).resolve().parent.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class BundleTests(unittest.TestCase):
 def test_manifest_covers_exact_private_files(self):
  root=R/'host-src'; p=root/'SOURCE-MANIFEST-v15.json'
  self.assertEqual(sha(p),'aca5319284d9a3c04901e71e90aefe05dd29991337aacf53566237e36fee5160')
  manifest=json.loads(p.read_text())
  for name,digest in manifest['files'].items():
   self.assertEqual(sha(root/name),digest,name)
  self.assertIn('one_item.py',manifest['files'])
  self.assertEqual((root/'worker.py').read_bytes(),(R/'tests/worker.one-item.py').read_bytes())
 def test_launcher_hard_disabled(self):
  lines=(R/'launch.sh').read_text().splitlines()
  self.assertLess(lines.index('exit 78'),next(i for i,s in enumerate(lines) if s.startswith('exec /bin/bash')))
  host=(R/'host-launch.sh').read_text().splitlines()
  self.assertLess(host.index('exit 78'),next(i for i,s in enumerate(host) if s.startswith('exec /usr/bin/sudo')))
 def test_original_cohort_identity_and_stop_routes(self):
  text=(R/'host-src/job_side.py').read_text()
  self.assertIn("COHORT=Path('/mnt/micron/refactor-yarn-s2-v32-20261031/cohort')",text)
  self.assertIn("(FLAGS/'dryrun'/ROW_ID/'stop') if env.get('FILLER_DRYRUN')=='1' else (ROOT.parent/'STOP')",text)
  self.assertIn('prior=cohort_status.read',text)
if __name__=='__main__':unittest.main()
