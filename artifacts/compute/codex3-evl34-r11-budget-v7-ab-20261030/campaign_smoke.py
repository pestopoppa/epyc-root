#!/usr/bin/env python3
"""Bounded disjoint GPU control under the caller's exclusive GPU lock."""
import datetime,json,math,os,re,shutil,sys,time
from pathlib import Path
from campaign_supervisor import supervise
D=Path(__file__).resolve().parent
FLAGS=Path('/mnt/raid0/llm/tmp/compute-flags')
RAM_ROOT=Path('/mnt/micron/codex3-evl34-r11-budget-v7-ab-20261030/control')
RAM_LIMIT=512*1024**2
METADATA_RESERVE=128*1024**2
last=[0.0,True]
def stopped(force=False):
    if (D/'STOP').exists() or list(FLAGS.glob('HOLD_*')): return True
    if not force and time.monotonic()-last[0]<.5: return last[1]
    last[0]=time.monotonic(); last[1]=True
    rows={}
    for line in (FLAGS/'FILLERS.md').read_text().splitlines():
        cells=[x.strip() for x in line.split('|')[1:-1]]
        if len(cells)==18: rows[cells[0]]=cells[8]
    now=time.time()
    for p in (FLAGS/'grants').glob('*.grant'):
        try: fields=dict(x.split('=',1) for x in p.read_text().split())
        except FileNotFoundError: continue
        begin=datetime.datetime.fromisoformat(fields['start'].replace('Z','+00:00')).timestamp()
        end=datetime.datetime.fromisoformat(fields['end'].replace('Z','+00:00')).timestamp()
        if begin<=now<end and rows.get(p.stem) not in ('block-correctness','diagnostic'): return True
    last[1]=False; return False

def admission_clear():
    # Caller holds the exclusive GPU lock. Correctness/diagnostic metadata
    # may overlap; live timing or unknown-class grants still refuse admission.
    deadline=time.monotonic()+1.5
    while True:
        if (D/'STOP').exists() or list(FLAGS.glob('HOLD_*')): return False
        if not stopped(force=True): return True
        remaining=deadline-time.monotonic()
        if remaining<=0: return False
        time.sleep(min(.1,remaining))
def select_memory_limit(args):
    if not args: return 8*1024**3
    if args==['--calibration-smoke48']: return 48*1024**3
    raise ValueError('invalid smoke arguments')

def live_output_reservations(flags=FLAGS, now=None):
    now=now or datetime.datetime.now(datetime.timezone.utc)
    rows={}
    for line in (flags/'FILLERS.md').read_text().splitlines():
        cells=[x.strip() for x in line.split('|')[1:-1]]
        if len(cells)==18: rows[cells[0]]=cells
    total=0
    for p in (flags/'grants').glob('*.grant'):
        try: fields=dict(x.split('=',1) for x in p.read_text().split())
        except FileNotFoundError: continue
        begin=datetime.datetime.fromisoformat(fields['start'].replace('Z','+00:00'))
        end=datetime.datetime.fromisoformat(fields['end'].replace('Z','+00:00'))
        if begin<=now<end:
            row=rows.get(p.stem)
            match=re.search(r'(?:^|;)\s*est_output_GiB\s*=\s*([0-9.]+)',row[-1]) if row else None
            if not match:raise RuntimeError('active grant missing output reservation: '+p.stem)
            value=float(match.group(1))
            if not math.isfinite(value) or value<0:raise ValueError('invalid output reservation')
            total+=math.ceil(value*1024**3)
    return total

def sampled_ram_bytes(root):
    total=0
    for parent,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[name for name in dirs if not Path(parent,name).is_symlink()]
        for name in files:
            path=Path(parent,name)
            try:
                st=path.lstat()
                if path.is_symlink():continue
                total+=max(st.st_size,st.st_blocks*512)
            except FileNotFoundError:continue
    return total

def run_control(command,output,*,memory_limit,stop,ram_root=RAM_ROOT):
    def guarded_stop():return stop() or sampled_ram_bytes(ram_root)>RAM_LIMIT
    return supervise(command,output,seconds=265,required_headroom=METADATA_RESERVE,mem_limit=memory_limit,stop=guarded_stop)

if __name__=='__main__':
    try: memory_limit=select_memory_limit(sys.argv[1:])
    except ValueError: raise SystemExit(64)
    if os.sched_getaffinity(0)!={184,185} or not admission_clear(): raise SystemExit(75)
    if (D/'CONTROL-EXPOSURE-START.json').exists() or RAM_ROOT.exists(): raise RuntimeError('control already reserved or RAM output exists; use archive-only recovery')
    disk=os.statvfs(D)
    if disk.f_bavail*disk.f_frsize<150*1024**3+METADATA_RESERVE:raise RuntimeError('disk admission refused')
    RAM_ROOT.mkdir(mode=0o700)
    preflight=Path(os.environ['EVL34_PREFLIGHT_LOG'])
    if preflight.parent!=Path('/mnt/raid0/llm/tmp/codex3-evl34-r11-budget-v7-ab-20261030') or not preflight.name.startswith('codex3-evl34-r11-v7-preflight-') or not preflight.is_file() or preflight.is_symlink():raise RuntimeError('invalid preflight log')
    shutil.copy2(preflight,RAM_ROOT/'source-preflight.log')
    os.environ['EVL34_CONTROL_RAM_ROOT']=str(RAM_ROOT)
    output=RAM_ROOT/'campaign-supervisor.log'
    try:
        if os.sched_getaffinity(0)!={184,185} or stopped(force=True): raise SystemExit(75)
        result=run_control(['/mnt/micron/codex3-evl34-deepdive-r9-20261030/bin/python3.11',str(D/'campaign_job.py'),'--smoke'],output,memory_limit=memory_limit,stop=stopped)
    except BaseException:
        if not (D/'CONTROL-EXPOSURE-START.json').exists():
            entries=list(RAM_ROOT.iterdir())
            if entries==[RAM_ROOT/'source-preflight.log']:
                entries[0].unlink();RAM_ROOT.rmdir()
        raise
    result.update(ram_output_bytes=sampled_ram_bytes(RAM_ROOT),ram_output_limit_bytes=RAM_LIMIT)
    with (RAM_ROOT/'campaign-supervisor.json').open('x') as f: json.dump(result,f);f.flush();os.fsync(f.fileno())
    if result['rc']==0 and result['reason'] is None and result['drained']:
        from entry_qualification import build
        from paired_journal import create
        from sealed_journal import DECL
        import hashlib
        attempts=list(RAM_ROOT.glob('campaign-control-*'))
        if len(attempts)!=1:raise RuntimeError('control attempt identity')
        source=hashlib.sha256((D/'CAMPAIGN-SOURCES.sha256').read_bytes()).hexdigest()
        create(D/'LAUNCH-QUALIFICATION.json',build(attempts[0],DECL,source))
    print(json.dumps(result),flush=True)
    raise SystemExit(75 if result['reason'] else result['rc'])
