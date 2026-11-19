"""In-window affinity witness for a structurally owned benchmark process."""
from pathlib import Path

def parse_cpu_list(value):
    cpus=set()
    for term in value.strip().split(','):
        bits=term.split('-')
        if len(bits)==1 and bits[0].isdigit(): lo=hi=int(bits[0])
        elif len(bits)==2 and all(x.isdigit() for x in bits): lo,hi=map(int,bits)
        else: raise ValueError('malformed CPU list')
        if lo>hi: raise ValueError('reversed CPU range')
        cpus.update(range(lo,hi+1))
    if not cpus: raise ValueError('empty CPU list')
    return cpus

def snapshot(pid, expected_binary, allowed=range(96), proc_root=Path('/proc')):
    """Capture all threads, verifying executable identity before and after scan.

    Caller first derives pid from its own process group; this function never
    searches by process name. Vanished/unreadable threads fail closed.
    """
    proc=Path(proc_root)/str(pid); exe=proc/'exe'
    expected=Path(expected_binary).resolve(strict=True)
    before=exe.resolve(strict=True)
    if before!=expected: raise ValueError('benchmark executable identity mismatch')
    def birth():
        stat=(proc/'stat').read_text(); close=stat.rfind(')')
        if close<0: raise ValueError('malformed process stat')
        fields=stat[close+2:].split()
        return int(fields[19])
    started=birth()
    tasks=sorted((proc/'task').iterdir(), key=lambda p:int(p.name))
    threads=[]
    for task in tasks:
        if not task.name.isdigit(): raise ValueError('malformed task id')
        status=(task/'status').read_text()
        lines=[line.split(':',1)[1].strip() for line in status.splitlines() if line.startswith('Cpus_allowed_list:')]
        if len(lines)!=1: raise ValueError('missing thread CPU affinity')
        cpus=parse_cpu_list(lines[0])
        if not cpus.issubset(set(allowed)): raise ValueError('thread escaped CPU claim')
        threads.append({'tid':int(task.name),'cpus_allowed_list':lines[0]})
    after={p.name for p in (proc/'task').iterdir()}
    if not threads or after!={p.name for p in tasks} or exe.resolve(strict=True)!=before or birth()!=started:
        raise ValueError('process or thread ownership changed during scan')
    return {'pid':pid,'start_ticks':started,'exe':str(before),'threads':threads}
