import os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import campaign_job as job
import campaign_smoke as smoke
import campaign_supervisor as supervisor

class RamControlTests(unittest.TestCase):
 def test_server_floor_before_popen_and_one_exposure(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);(root/'CAMPAIGN-SOURCES.sha256').write_text('fixture')
   with patch.object(job,'D',root),patch.object(job.c,'headroom',return_value=False),patch.object(job.subprocess,'Popen') as popen:
    with self.assertRaisesRegex(RuntimeError,'disk floor'):job.start_server(['fixture'],{},None,None,smoke=True,output_root=root)
    popen.assert_not_called();self.assertFalse((root/'CONTROL-EXPOSURE-START.json').exists())
   with patch.object(job,'D',root),patch.object(job.c,'headroom',return_value=True),patch.object(job.subprocess,'Popen') as popen:
    popen.side_effect=lambda *a,**k: self.assertTrue((root/'CONTROL-EXPOSURE-START.json').exists())
    job.start_server(['fixture'],{},None,None,smoke=True,output_root=root)
    with self.assertRaises(FileExistsError):job.start_server(['fixture'],{},None,None,smoke=True,output_root=root)
    self.assertEqual(popen.call_count,1)
 def test_smoke_supervisor_floor_boundary_and_drain(self):
  threshold=supervisor.FLOOR+smoke.METADATA_RESERVE
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);marker=root/'sentinel';cmd=[sys.executable,'-B','-c',f"from pathlib import Path; import time; Path({str(marker)!r}).write_text('ok'); time.sleep(.2)"]
   with patch.object(supervisor.os,'statvfs',return_value=SimpleNamespace(f_bavail=threshold-1,f_frsize=1)),patch.object(supervisor.subprocess,'Popen') as popen:
    with self.assertRaisesRegex(RuntimeError,'disk admission'):smoke.run_control(cmd,root/'bad.log',memory_limit=8*1024**3,stop=lambda:False,ram_root=root)
    popen.assert_not_called();self.assertFalse(marker.exists())
   with patch.object(supervisor.os,'statvfs',return_value=SimpleNamespace(f_bavail=threshold,f_frsize=1)):
    r=smoke.run_control(cmd,root/'ok.log',memory_limit=8*1024**3,stop=lambda:False,ram_root=root)
   self.assertEqual(r['rc'],0);self.assertTrue(r['drained']);self.assertTrue(marker.exists())
 def test_ram_output_guard_stops_owned_child(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);(root/'payload').write_bytes(b'x'*4096)
   with patch.object(smoke,'RAM_LIMIT',1024),patch.object(supervisor.os,'statvfs',return_value=SimpleNamespace(f_bavail=supervisor.FLOOR+smoke.METADATA_RESERVE,f_frsize=1)):
    r=smoke.run_control([sys.executable,'-B','-c','import time;time.sleep(5)'],root/'guard.log',memory_limit=8*1024**3,stop=lambda:False,ram_root=root)
   self.assertEqual(r['reason'],'stop');self.assertTrue(r['drained'])
 def test_campaign_parent_and_child_temp_environment_stay_in_ram(self):
  import subprocess,tempfile
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d,patch.dict(os.environ,{},clear=False),patch.object(tempfile,'tempdir',None):
   root=Path(d);inherited_home=os.environ.get('HOME');job.configure_control_environment(root)
   output=subprocess.check_output([sys.executable,'-B','-c','import os,tempfile; print(os.environ["HOME"]); print(tempfile.gettempdir())'],text=True).splitlines()
   self.assertEqual(output,[inherited_home,str(root/'tmp')]);self.assertEqual(os.environ.get('HOME'),inherited_home);self.assertTrue((root/'tmp').is_dir())
   server=job.server_environment(root,True);self.assertEqual(server.get('HOME'),inherited_home);self.assertEqual(server['TMPDIR'],str(root/'tmp'))
 def test_normal_caller_reservation_propagates_and_namespace_is_stable(self):
  with patch.dict(os.environ,{'EVL34_EXTRA_HEADROOM_BYTES':'123456','EVL44_EXTRA_HEADROOM_BYTES':'999999','EVL54_EXTRA_HEADROOM_BYTES':'999999'}):
   self.assertEqual(job.extra_headroom(False),123456);self.assertEqual(job.extra_headroom(True),0)
  for name in ('campaign_job.py','campaign_smoke.py','control_driver.py','gpu_witness.py','launch_campaign.sh'):
   text=(Path(__file__).parent/name).read_text();self.assertNotIn('EVL44_',text);self.assertNotIn('EVL54_',text)
 def test_control_ram_path_and_normal_pilot_path(self):
  ram=Path('/dev/shm/codex3-evl34-deepdive-r8-control-20261030')
  with patch.dict(os.environ,{'EVL34_CONTROL_RAM_ROOT':str(ram)}),patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False):
   self.assertEqual(job.control_output_root(True),ram);self.assertEqual(job.control_output_root(False),job.D)
  with patch.dict(os.environ,{'EVL34_CONTROL_RAM_ROOT':'/tmp/not-control'}):
   with self.assertRaisesRegex(RuntimeError,'invalid control RAM root'):job.control_output_root(True)
if __name__=='__main__':unittest.main()
