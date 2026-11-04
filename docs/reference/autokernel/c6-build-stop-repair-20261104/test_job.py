import importlib.util, pathlib, subprocess, sys, tempfile, time, unittest
p=pathlib.Path(__file__).with_name('job.py')
spec=importlib.util.spec_from_file_location('c6_job',p)
job=importlib.util.module_from_spec(spec); spec.loader.exec_module(job)

class TestOwned(unittest.TestCase):
 def test_success_and_failure(self):
  job.stopped=lambda:False
  with tempfile.TemporaryFile() as log:
   job.run_owned([sys.executable,'-c','pass'],log)
   with self.assertRaises(subprocess.CalledProcessError): job.run_owned([sys.executable,'-c','raise SystemExit(4)'],log)
 def test_stop_terminates_owned_child(self):
  with tempfile.TemporaryDirectory() as d:
   marker=pathlib.Path(d)/'pid'
   job.stopped=lambda:marker.exists()
   code='import os,time,pathlib,sys,subprocess; c=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]); pathlib.Path(sys.argv[1]).write_text(str(os.getpid())+" "+str(c.pid)); time.sleep(60)'
   with tempfile.TemporaryFile() as log:
    with self.assertRaises(job.InterruptedBuild): job.run_owned([sys.executable,'-c',code,str(marker)],log)
   pid,descendant=map(int,marker.read_text().split())
   self.assertFalse(pathlib.Path('/proc',str(pid)).exists(),f'child {pid} not reaped')
   stat=pathlib.Path('/proc',str(descendant),'stat')
   if stat.exists(): self.assertEqual(stat.read_text().split(') ',1)[1][0], 'Z', f'descendant {descendant} still running')
 def test_stop_escalates_when_child_ignores_term(self):
  with tempfile.TemporaryDirectory() as d:
   marker=pathlib.Path(d)/'pid'
   job.stopped=lambda:marker.exists()
   code='import os,time,pathlib,sys,signal; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)'
   with tempfile.TemporaryFile() as log:
    with self.assertRaises(job.InterruptedBuild): job.run_owned([sys.executable,'-c',code,str(marker)],log)
   self.assertFalse(pathlib.Path('/proc',marker.read_text()).exists())
if __name__=='__main__': unittest.main()
