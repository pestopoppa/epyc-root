import fcntl,json,os,pathlib,subprocess,sys,time
root=pathlib.Path(__file__).resolve().parent
with open('/mnt/raid0/llm/tmp/compute-flags/prep-locks/32-33.lock','a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 lock.seek(0);lock.truncate();lock.write('codex-ni QKV sourceprep cpus=128-129\n');lock.flush()
 env=os.environ.copy();env['OMP_NUM_THREADS']='1';env['LD_LIBRARY_PATH']='/mnt/raid0/llm/tmp/lb49-codex-evidence-20261028/build-deterministic-feature/bin'
 start=time.monotonic();peak=0;samples=0
 with (root/'native.log').open('wb') as log:
  p=subprocess.Popen(['taskset','-c','128-129','bash',str(root/'check.sh')],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  try:
   while p.poll() is None:
    # Descendants only; captured process group, no name matching.
    rss=0
    for item in pathlib.Path('/proc').iterdir():
     if not item.name.isdigit():continue
     try:
      stat=(item/'stat').read_text().rsplit(') ',1)[1].split()
      if int(stat[2])==p.pid:rss+=int(stat[21])*os.sysconf('SC_PAGE_SIZE')
     except (OSError,ValueError,IndexError):pass
    peak=max(peak,rss);samples+=1
    if rss>8*1024**3 or time.monotonic()-start>900:raise RuntimeError('standing prep resource bound')
    time.sleep(.05)
   rc=p.wait()
  finally:
   if p.poll() is None:
    os.killpg(p.pid,15)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait(timeout=5)
 result={'rc':rc,'wall_s':time.monotonic()-start,'sampled_tree_rss_max_bytes':peak,'samples':samples,'cpus':'128-129','kind':'model-free source helper build/fixture only','model_loaded':False}
 (root/'CHECK.json').write_text(json.dumps(result,indent=2)+'\n')
 sys.exit(rc)
