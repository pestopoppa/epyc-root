"""Executed only by GDB: capture mapped libraries from inside Test 6."""
import gdb
import hashlib
import json
import os
from pathlib import Path
import time

C = json.loads(Path(os.environ['KPF17_WITNESS_CONFIG']).read_text())
OUT = Path(os.environ['KPF17_WITNESS_OUTPUT'])
ENTRY = '_ZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEj'
DECODE = '_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUlP13llama_contextiiE_clESA_ii'
RESTORE = '_ZZL36test_partial_restore_busy_source_oneP11llama_modelRK13common_paramsRKSt6vectorIiSaIiEEjENKUliRKS4_IhSaIhEEE_clEiSC_'
state = {'schema':'kpf17.oracle-in-test-maps.v1', 'pid':None, 'birth_ticks':None,
         'initial_stop':None, 'mode':None, 'entries':[], 'samples':[], 'error':None}


def save():
    tmp=OUT.with_suffix('.tmp')
    with tmp.open('w') as f:
        f.write(json.dumps(state,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,OUT)
    fd=os.open(str(OUT.parent),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def birth(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])


def fail(exc):
    state['error'] = type(exc).__name__+': '+str(exc); save(); gdb.write('KPF17_WITNESS_ERROR '+state['error']+'\n'); return True


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576), b''): h.update(b)
    return h.hexdigest()


def start_capture_continue():
    # GDB must stop at the first instruction and durably record exact inferior identity
    # before it can continue to main or open the target model.
    gdb.execute('starti')
    pid=gdb.selected_inferior().pid
    if pid<=0:raise RuntimeError('starti produced no inferior PID')
    exe=Path(f'/proc/{pid}/exe').resolve(strict=True)
    if exe!=Path(C['binary']).resolve(strict=True):raise RuntimeError('starti inferior executable mismatch')
    nspid=[int(x) for x in next(x for x in Path(f'/proc/{pid}/status').read_text().splitlines() if x.startswith('NSpid:')).split()[1:]]
    if nspid != [pid]:raise RuntimeError('unexpected inferior PID namespace')
    ticks=birth(pid)
    # PID + birth are fsynced before witness publication and before continuation.
    with open(os.environ['FILLER_PIDFILE'],'a') as f:
        f.write(f'{pid} {ticks}\n');f.flush();os.fsync(f.fileno())
    state.update(pid=pid,birth_ticks=ticks,nspid=nspid,
                 initial_stop={'pid':pid,'birth_ticks':ticks,'exe':str(exe),'time_ns':time.time_ns()})
    save()
    gdb.execute('continue')

class Main(gdb.Breakpoint):
    def stop(self):
        try:
            pid=gdb.selected_inferior().pid
            if pid!=state['pid'] or birth(pid)!=state['birth_ticks'] or not state.get('initial_stop'):
                raise ValueError('main reached without matching durable starti identity')
            state['main_stop']={'pid':pid,'birth_ticks':state['birth_ticks'],'time_ns':time.time_ns()}
            self.enabled=False;save();return False
        except Exception as exc:return fail(exc)


class Entry(gdb.Breakpoint):
    def stop(self):
        try:
            mode=int(gdb.parse_and_eval('$ecx')) & 0xffffffff
            if mode not in (0,8) or state['pid']!=gdb.selected_inferior().pid or birth(state['pid'])!=state['birth_ticks']: raise ValueError('invalid Test 6 entry')
            state['mode']=mode; state['entries'].append({'mode':mode,'time_ns':time.time_ns(),'monotonic_ns':time.monotonic_ns()}); save(); return False
        except Exception as exc: return fail(exc)


def capture(point):
    pid=state['pid']; mode=state['mode']
    if mode not in (0,8) or pid!=gdb.selected_inferior().pid or birth(pid)!=state['birth_ticks']: raise ValueError('sample outside Test 6')
    if any(x['mode']==mode and x['point']==point for x in state['samples']): return
    raw=Path(f'/proc/{pid}/maps').read_text(); libs={}
    if C['model_path'] not in raw: raise ValueError('model not mapped during Test 6')
    for line in raw.splitlines():
        fields=line.split(None,5)
        if len(fields)<6 or not Path(fields[5]).name.startswith(('libggml','libllama')): continue
        if fields[5].endswith(' (deleted)'): raise ValueError('deleted mapped library')
        path=Path(fields[5]).resolve(strict=True); name=str(path)
        if name not in C['libraries'] or sha(path)!=C['libraries'][name]: raise ValueError('unattested mapped library: '+name)
        st=path.stat(); major,minor=(int(x,16) for x in fields[3].split(':'))
        if (major,minor,int(fields[4]))!=(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino): raise ValueError('mapped inode mismatch')
        libs[name]=C['libraries'][name]
    for required in ('libggml.so','libggml-base.so','libggml-cpu.so','libllama.so','libllama-common.so'):
        if not any(Path(x).name.startswith(required) for x in libs): raise ValueError('missing mapped '+required)
    state['samples'].append({'mode':mode,'point':point,'pid':pid,'birth_ticks':state['birth_ticks'],
        'time_ns':time.time_ns(),'monotonic_ns':time.monotonic_ns(),'libraries':libs,
        'maps_sha256':hashlib.sha256(raw.encode()).hexdigest(),'maps_text':raw,
        'source_commit':C['source_commit'],'patch_sha256':C['patch_sha256'],
        'receipt_sha256':C['receipt_sha256'],'model_sha256':C['model_sha256']})
    save()


class Decode(gdb.Breakpoint):
    def stop(self):
        try: capture('decode_entry'); return False
        except Exception as exc: return fail(exc)


class Restore(gdb.Breakpoint):
    def stop(self):
        try:
            dest=int(gdb.parse_and_eval('$esi')) & 0xffffffff
            if dest not in (1,2): raise ValueError('unexpected restore destination')
            capture('restore_dst_'+str(dest)); return False
        except Exception as exc: return fail(exc)


Main('*main',internal=True); Entry('*'+ENTRY,internal=True)
Decode('*'+DECODE,internal=True); Restore('*'+RESTORE,internal=True)
