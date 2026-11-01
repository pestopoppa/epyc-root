import os,subprocess,tempfile,unittest
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/handoff-kvu-16i-c5-20261101')
class LaunchPathTests(unittest.TestCase):
 def capture(self,dry):
  with tempfile.TemporaryDirectory() as td:
   hook=Path(td)/'hook';out=Path(td)/'args'
   hook.write_text('exec() { printf "%s\\0" "$@" > "$TEST_CAPTURE"; }\n')
   env={**os.environ,'BASH_ENV':str(hook),'TEST_CAPTURE':str(out),'FILLER_DRYRUN':dry}
   p=subprocess.run(['/bin/bash',str(D/'launch.sh'),'--engine'],env=env,capture_output=True,timeout=5)
   self.assertEqual(p.returncode,0,p.stderr.decode());args=out.read_bytes().decode().split('\0')[:-1]
   self.assertEqual(args[0:2],['/bin/bash','/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh'])
   self.assertEqual(args[args.index('--id')+1],'handoff-kvu-16i-c5-replay-20261101')
   cmd=args[args.index('--cmd')+1];complete=args[args.index('--complete-cmd')+1]
   suffix=f'/bin/bash {D}/launch.sh --job';self.assertTrue(cmd.endswith(suffix));cmd=cmd[:-len(suffix)]+'/usr/bin/env'
   env={'PATH':'/usr/bin:/bin','FILLER_ID':'fixture','FILLER_CPUS':'184-191','FILLER_NEEDGPU':'1',
        'FILLER_STOPFILE':'/tmp/stop','FILLER_END':'1999999999','FILLER_DEADLINE':'1999999900',
        'FILLER_PORTS':'18196','FILLER_PIDFILE':'/tmp/pids','FILLER_GRANTS_DIR':'/tmp/grants','WS58_REGIONS':'mi210_0,184-191'}
   p=subprocess.run(['/bin/bash','-c',cmd],env=env,capture_output=True,timeout=5,check=True)
   return dict(line.split('=',1) for line in p.stdout.decode().splitlines()),complete
 def test_modes_and_owned_runtime_vars(self):
  for raw,word in (('1','qualification'),('0','full')):
   with self.subTest(raw=raw):
    env,complete=self.capture(raw);self.assertEqual(env['FILLER_DRYRUN'],raw)
    self.assertEqual(env['FILLER_PIDFILE'],'/tmp/pids');self.assertEqual(env['FILLER_GRANTS_DIR'],'/tmp/grants')
    self.assertIn(word,complete)
 def test_missing_mode_refuses(self):
  for raw in ('','2','bogus'):
   p=subprocess.run(['/bin/bash',str(D/'launch.sh'),'--engine'],env={**os.environ,'FILLER_DRYRUN':raw},capture_output=True,timeout=5)
   self.assertEqual(p.returncode,64)
if __name__=='__main__':unittest.main()
