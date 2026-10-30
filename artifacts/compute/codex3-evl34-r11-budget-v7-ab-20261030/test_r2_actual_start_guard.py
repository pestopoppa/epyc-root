import datetime,os,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import campaign_smoke as smoke
import campaign_supervisor as supervisor

class GuardTests(unittest.TestCase):
 def test_live_grant_reservations_and_missing_metadata(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);(root/'grants').mkdir();now=datetime.datetime.now(datetime.timezone.utc);fmt=lambda t:t.isoformat().replace('+00:00','Z')
   (root/'grants/a.grant').write_text('regions=0-23 start='+fmt(now-datetime.timedelta(minutes=1))+' end='+fmt(now+datetime.timedelta(minutes=1)))
   cells=['a']+['x']*16+['requested_window_s=3600; est_output_GiB=0.625'];(root/'FILLERS.md').write_text('| '+' | '.join(cells)+' |\n')
   self.assertEqual(smoke.live_output_reservations(root,now),int(.625*1024**3))
   cells[-1]='requested_window_s=3600';(root/'FILLERS.md').write_text('| '+' | '.join(cells)+' |\n')
   with self.assertRaisesRegex(RuntimeError,'missing output reservation'):smoke.live_output_reservations(root,now)
 def test_actual_supervisor_negative_and_positive_boundary(self):
  own=256*1024**2;other=2*1024**3;threshold=supervisor.FLOOR+own+other
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d, patch.object(smoke,'live_output_reservations',return_value=other), patch.dict(os.environ,{},clear=False):
   root=Path(d);marker=root/'started'
   cmd=[sys.executable,'-B','-c',f"from pathlib import Path; import time; Path({str(marker)!r}).write_text('started'); time.sleep(.2)"]
   with patch.object(supervisor.os,'statvfs',return_value=SimpleNamespace(f_bavail=threshold-1,f_frsize=1)),patch.object(supervisor.subprocess,'Popen') as popen:
    with self.assertRaisesRegex(RuntimeError,'disk admission refused'):smoke.run_control(cmd,root/'negative.log',memory_limit=8*1024**3,required_headroom=own,stop=lambda:False)
    popen.assert_not_called();self.assertFalse(marker.exists())
   with patch.object(supervisor.os,'statvfs',return_value=SimpleNamespace(f_bavail=threshold,f_frsize=1)):
    result=smoke.run_control(cmd,root/'positive.log',memory_limit=8*1024**3,required_headroom=own,stop=lambda:False)
   self.assertEqual(result['rc'],0);self.assertTrue(result['drained']);self.assertTrue(marker.exists());self.assertEqual(os.environ['EVL34_EXTRA_HEADROOM_BYTES'],str(other))
if __name__=='__main__':unittest.main()
