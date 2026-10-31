import importlib.util,os,sys,tempfile,subprocess,json
from pathlib import Path
base=Path(__file__).parent
spec=importlib.util.spec_from_file_location("candidate",base/"candidate-one-attempt.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(dir=base) as t:
 d=Path(t);m.D=d;m.S=d
 prior=d/"attempt-old";prior.mkdir();m.write_status(prior,"STARTING")
 try:m.check_prior_attempts();raise AssertionError("ambiguous attempt retried")
 except RuntimeError:pass
 m.write_status(prior,"RETRYABLE_PRE_NATIVE_ADMISSION_REFUSAL");m.check_prior_attempts()
 (d/"smoke-final").mkdir();(d/"smoke-final"/"RESULT.json").write_text("old")
 attempt=d/"attempt";attempt.mkdir()
 m.write_status(attempt,"PREPARING",native_exposure="none")
 assert json.loads((attempt/"status.json").read_text())["native_exposure"]=="none"
 m.archive(attempt,"prior-smoke");assert (attempt/"prior-smoke"/"RESULT.json").read_text()=="old" and not (d/"smoke-final").exists()
 stop=d/"STOP";stop.write_text("ours");st=stop.stat();ident=(st.st_dev,st.st_ino)
 moved=d/"old";stop.rename(moved);stop.write_text("foreign")
 try:m.remove_owned_stop(stop,ident);raise AssertionError("foreign STOP removed")
 except RuntimeError:pass
 assert stop.read_text()=="foreign"
 stop.unlink();moved.rename(stop);m.remove_owned_stop(stop,ident);assert not stop.exists()
m.subreaper.enable()
code="import subprocess,sys,time; p=subprocess.Popen([sys.argv[1],'-c','import time;time.sleep(60)']);print(p.pid,flush=True);time.sleep(60)"
link=base/"llama-server"
os.symlink(sys.executable,link)
leader=subprocess.Popen([sys.executable,"-c",code,str(link)],stdout=subprocess.PIPE,text=True)
grandchild=int(leader.stdout.readline())
assert grandchild in m.descendants(leader.pid)
capture=m.captured_server(leader.pid);assert capture and capture[1]==grandchild;os.close(capture[0]);link.unlink()
m.pf1_graceful.drain(leader=leader);leader.wait()
assert not m.subreaper.children()
assert not Path("/proc",str(grandchild)).exists()
print("archive, durable status, STOP ownership, live tree discovery, subreaper drain: PASS")
