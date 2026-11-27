"""Main-only optional affinity intervention; default inspect, no kills/model calls."""
from pathlib import Path
import argparse,json,os,time
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--include-cli',action='store_true');a=p.parse_args()
snapshot=json.loads((HERE/'SNAPSHOT.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==snapshot['boot_id']
def read(pid):
    path=Path('/proc')/str(pid);s=(path/'stat').read_text();v=s[s.rindex(')')+2:].split()
    return {'pid':pid,'ppid':int(v[1]),'start_ticks':int(v[19]),'cmdline':(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(),'cwd':str((path/'cwd').resolve())}
def same(expected):
    observed=read(expected['pid'])
    assert all(observed[k]==expected[k] for k in ['pid','ppid','start_ticks','cmdline','cwd']),('identity changed',expected['pid'])
    return observed
fixed={r['pid']:r for r in snapshot['processes']}
roots=[3792770,3793107] if a.include_cli else [3816277,3817224]
rows=[]
for root in roots:
    try:
        seed=same(fixed[root]);same(fixed[seed['ppid']])
    except FileNotFoundError:
        rows.append({'root':root,'status':'already-terminal-no-change'});continue
    candidates={}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:r=read(int(proc.name));candidates[r['pid']]=r
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    owned={root:seed}
    while True:
        extra={pid:r for pid,r in candidates.items() if r['ppid'] in owned and pid not in owned}
        if not extra:break
        owned.update(extra)
    for pid,r in owned.items():
        try:
            same(r)
            for task in (Path('/proc')/str(pid)/'task').iterdir():
                tid=int(task.name);same(r)
                before=sorted(os.sched_getaffinity(tid))
                if a.apply:os.sched_setaffinity(tid,{180,181,182,183})
                after=sorted(os.sched_getaffinity(tid));rows.append({'root':root,'pid':pid,'start_ticks':r['start_ticks'],'tid':tid,'before':before,'after':after,'applied':a.apply})
        except (FileNotFoundError,ProcessLookupError):rows.append({'root':root,'pid':pid,'status':'exited-during-inspection'})
record={'observed_epoch':time.time(),'apply':a.apply,'include_cli':a.include_cli,'rows':rows,'no_kills':True,'target_affinity':[180,181,182,183]}
print(json.dumps(record,indent=2))
if a.apply:
    path=HERE/('INTERVENTION-'+str(time.time_ns())+'.json');path.write_text(json.dumps(record,indent=2)+'\n')
