import os, subprocess, tempfile, unittest, hashlib, re
from pathlib import Path

D=Path('/mnt/raid0/llm/tmp/handoff-kvu-vkq3-independent-calibration-20261101')
class ModePathTests(unittest.TestCase):
    def capture(self, dry):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp); hook=t/'hook'; out=t/'argv'
            hook.write_text('exec() { printf "%s\\0" "$@" > "$TEST_CAPTURE"; }\n')
            env={**os.environ,'BASH_ENV':str(hook),'TEST_CAPTURE':str(out),'FILLER_DRYRUN':dry}
            p=subprocess.run(['/bin/bash',str(D/'launch.sh'),'--engine'],env=env,capture_output=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr.decode()); args=out.read_bytes().decode().split('\0')[:-1]
            self.assertEqual(args[0:2],['/bin/bash','/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh'])
            cmd=args[args.index('--cmd')+1]; complete=args[args.index('--complete-cmd')+1]
            suffix=f'/bin/bash {D}/launch.sh --job'
            self.assertTrue(cmd.endswith(suffix)); cmd=cmd[:-len(suffix)]+'/usr/bin/env'
            fakeenv={'PATH':'/usr/bin:/bin','FILLER_ID':'synthetic-fixture','FILLER_CPUS':'0-95','FILLER_NEEDGPU':'0','FILLER_STOPFILE':'fixture-stop','FILLER_END':'1999999999','FILLER_DEADLINE':'1999999900','WS58_REGIONS':'0-95'}
            p=subprocess.run(['/bin/bash','-c',cmd],env=fakeenv,capture_output=True,timeout=5,check=True)
            result=dict(line.split('=',1) for line in p.stdout.decode().splitlines());return result,complete
    def test_qualification_mode_reaches_job_without_target(self):
        e,c=self.capture('1'); self.assertEqual(e['FILLER_DRYRUN'],'1'); self.assertEqual(e['FILLER_ID'],'synthetic-fixture');self.assertIn('/qualification/QUALIFICATION.json',c)
    def test_full_mode_reaches_job(self):
        e,c=self.capture('0'); self.assertEqual(e['FILLER_DRYRUN'],'0');self.assertEqual(e['FILLER_ID'],'synthetic-fixture');self.assertIn('/run/TERMINAL.json',c)
    def test_launcher_pins_source_catalog_except_its_own_hash(self):
        text=(D/'launch.sh').read_text()
        pin=re.search(r'" = "([0-9a-f]{64})" \] \|\| \{ echo "source catalog pin mismatch"',text)
        self.assertIsNotNone(pin)
        lines=(D/'SOURCE-SHA256SUMS').read_bytes().splitlines(keepends=True)
        selected=b''.join(line for line in lines if not line.endswith(b'  launch.sh\n'))
        self.assertEqual(hashlib.sha256(selected).hexdigest(),pin.group(1))
        self.assertNotEqual(hashlib.sha256(selected.replace(b'worker.py',b'worker.px')).hexdigest(),pin.group(1))
    def test_engine_rejects_unknown_mode(self):
        for dry in ('', 'x', '2'):
            p=subprocess.run(['/bin/bash',str(D/'launch.sh'),'--engine'],env={**os.environ,'FILLER_DRYRUN':dry},capture_output=True,timeout=5)
            self.assertEqual(p.returncode,64)

if __name__=='__main__':unittest.main()
