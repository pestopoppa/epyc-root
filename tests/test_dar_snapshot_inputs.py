import importlib.util, json, os, stat, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/analysis/dar_snapshot_inputs.py'
spec = importlib.util.spec_from_file_location('snapshot', SCRIPT)
snapshot = importlib.util.module_from_spec(spec); spec.loader.exec_module(snapshot)

class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.progress = self.root/'source'; self.progress.mkdir()
        self.parent = self.root/'output'; self.parent.mkdir()
        self.baseline = self.root/'baseline'; self.baseline.write_text(json.dumps({'roles':{'coder':{'p50_s':2,'p90_s':4}}}))
        self.config = self.root/'config'; self.config.write_text('{"commit":"fixture", "configuration":"fixture"}')
        (self.progress/'a.jsonl').write_text('{"fixture":1}\n')
    def tearDown(self): self.tmp.cleanup()
    def run_cli(self, *args): return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
    def capture(self): return self.run_cli('capture','--parent',self.parent,'--progress',self.progress,'--baseline',self.baseline,'--provenance',self.config)
    def test_capture_verify_and_tamper(self):
        result = self.capture(); self.assertEqual(result.returncode,0,result.stderr)
        path = Path(result.stdout.strip()); self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o500)
        self.assertEqual(stat.S_IMODE((path/'progress'/'a.jsonl').stat().st_mode),0o400)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o500)
        self.assertEqual(json.loads((path/'baseline-roles.json').read_text()),['coder'])
        self.assertEqual(self.run_cli('verify',path).returncode,0)
        (path/'progress'/'a.jsonl').chmod(0o600)
        (path/'progress'/'a.jsonl').write_text('changed\n')
        self.assertNotEqual(self.run_cli('verify',path).returncode,0)
    def test_partial_line_rejected_and_cleaned(self):
        (self.progress/'a.jsonl').write_text('partial')
        self.assertNotEqual(self.capture().returncode,0); self.assertEqual(list(self.parent.iterdir()),[])
    def test_symlink_rejected(self):
        (self.progress/'b.jsonl').symlink_to(self.progress/'a.jsonl')
        self.assertNotEqual(self.capture().returncode,0)
    def test_bad_values_rejected(self):
        for value in (0, -1, True, float('nan'), '1'):
            self.baseline.write_text(json.dumps({'roles':{'bad':{'p50_s':value,'p90_s':4}}}))
            self.assertNotEqual(self.capture().returncode,0)
    def test_errors_do_not_disclose_sensitive_names(self):
        self.baseline.write_text(json.dumps({'roles':{'SECRET_ROLE':{'p50_s':0,'p90_s':4}}}))
        result = self.capture()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SECRET_ROLE', result.stderr)
        self.assertNotIn(str(self.root), result.stderr)
    def test_reversed_percentiles_rejected(self):
        self.baseline.write_text(json.dumps({'roles':{'coder':{'p50_s':4,'p90_s':2}}}))
        self.assertNotEqual(self.capture().returncode, 0)
    def test_selection_changes_fail(self):
        real = snapshot.names; n = [0]
        def changed(path):
            n[0] += 1
            return real(path) if n[0] == 1 else real(path)+['rotated.jsonl']
        args = type('Args',(),{'parent':str(self.parent),'progress':str(self.progress),'baseline':str(self.baseline),'provenance':str(self.config)})()
        with patch.object(snapshot,'names',side_effect=changed), self.assertRaises(ValueError): snapshot.snapshot(args)
        self.assertEqual(list(self.parent.iterdir()),[])
    def test_extra_progress_detected(self):
        result = self.capture(); self.assertEqual(result.returncode,0,result.stderr)
        path = Path(result.stdout.strip()); (path/'progress').chmod(0o700); (path/'progress'/'extra.jsonl').write_text('{}\n')
        self.assertNotEqual(self.run_cli('verify',path).returncode,0)

if __name__ == '__main__': unittest.main()
