import fcntl,hashlib,os,re,subprocess,tempfile,time,unittest
from pathlib import Path
class NormalLauncher(unittest.TestCase):
 def test_busy_28_pair_does_not_gate_normal_engine(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
   root=Path(tmp);launch=Path(__file__).parent/'launch_campaign.sh';engine=root/'fixture_engine.sh';engine.write_text('#!/bin/bash\nexec /usr/bin/python3 -B -c \'import os,sys,time;assert os.environ.get("RUS3_DIAGNOSTIC")=="1" and os.environ.get("MKL_NUM_THREADS")=="1";print("launcher up pid="+str(os.getpid()),flush=True);time.sleep(2)\' "$@"\n');engine.chmod(0o700)
   member=root/'source-member.py';member.write_text('original fixture')
   catalog=root/'CAMPAIGN-SOURCES.sha256';catalog.write_text(hashlib.sha256(member.read_bytes()).hexdigest()+'  '+str(member)+'\n')
   expected=hashlib.sha256(catalog.read_bytes()).hexdigest()
   source=launch.read_text().replace('/mnt/raid0/llm/tmp/codex3-evl34-r11-budget-v7-ab-20261030',str(root)).replace('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/engine/filler_run13.sh',str(engine))
   source=re.sub(r'(?m)^EXPECTED_CATALOG_SHA256=.*$', 'EXPECTED_CATALOG_SHA256='+expected,source);fixture=root/'launch.sh';fixture.write_text(source)
   lock=open('/mnt/raid0/llm/tmp/compute-flags/prep-locks/28-29.lock','r+')
   try:
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:pass
    p=subprocess.Popen(['bash',str(fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
     time.sleep(.2);self.assertEqual((root/'ws58-launcher.out').read_text().strip(),'launcher up pid='+str(p.pid));cmd=Path('/proc',str(p.pid),'cmdline').read_bytes().replace(b'\0',b' ').decode();self.assertIn('--id codex3-evl34-r11-budget-v7-ab-20261030',cmd);self.assertIn('--min-window 19740',cmd);self.assertEqual(p.wait(timeout=5),0)
    finally:
     if p.poll() is None:p.terminate();p.wait(timeout=3)
    before=(root/'ws58-launcher.out').read_bytes();member.write_text('tampered fixture')
    denied=subprocess.run(['bash',str(fixture)],capture_output=True,text=True);self.assertEqual(denied.returncode,78);self.assertEqual((root/'ws58-launcher.out').read_bytes(),before)
    catalog.write_text('tampered catalog')
    denied=subprocess.run(['bash',str(fixture)],capture_output=True,text=True);self.assertEqual(denied.returncode,78);self.assertEqual((root/'ws58-launcher.out').read_bytes(),before)
   finally:lock.close()
if __name__=='__main__':unittest.main()
