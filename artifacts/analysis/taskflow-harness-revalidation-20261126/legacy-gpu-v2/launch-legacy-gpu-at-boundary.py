import os,time,json,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUNNER=ROOT/'legacy-gpu-v2'
CONFIG=ROOT/'legacy-boundary-v2-approval.json'
x=json.loads(CONFIG.read_text())
def state(pid):
 try:return Path(f'/proc/{pid}/stat').read_text().split()[21]
 except FileNotFoundError:return None
def save(status,**kw):
 p=ROOT/'legacy-boundary-v2-state.json'; q=p.with_suffix('.tmp');q.write_text(json.dumps(dict(status=status,pid=os.getpid(),at=time.time(),**kw),indent=2)+'\n');q.replace(p)
assert hashlib.sha256((RUNNER/'MAIN-APPROVAL.json').read_bytes()).hexdigest()==x['approval_sha256']
save('waiting_for_owned_controller',controller=x['controller'])
while state(x['controller']['pid'])==x['controller']['start_ticks']:time.sleep(1)
for item in x['servers']:
 deadline=time.monotonic()+90
 while state(item['pid'])==item['start_ticks']:
  if time.monotonic()>deadline:
   save('refused_owned_server_still_alive',server=item);raise SystemExit(2)
  time.sleep(1)
save('launching_legacy')
with (ROOT/'legacy-boundary-v2-launch.log').open('wb') as log:
 process=subprocess.Popen(x['argv'],cwd=x['cwd'],stdout=log,stderr=subprocess.STDOUT)
 save('legacy_controller_running',child_pid=process.pid)
 rc=process.wait()
save('legacy_controller_terminal',rc=rc)
raise SystemExit(rc)
