"""Capture native KPF-50 HSA samples and bind them to one window and phase.

Runs only under the caller's GPU claim. A typed witness is structural evidence,
not a clock-calibration or scientific-validity verdict.
"""
import hashlib, json, os, re, stat, subprocess, sys, tempfile, time
from pathlib import Path

WINDOWS=('full-a','mask-a','mask-b','full-b')
PHASES=('clock_before','clock_after')
ID=re.compile(r'[A-Za-z0-9_.-]{1,128}\Z')

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def birth(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])

def validate(raw, pid, begin_ns, end_ns):
    x=json.loads(raw)
    if x.get('schema')!='epyc.kpf50.hsa-clock.v1' or x.get('pid')!=pid:
        raise ValueError('native schema or process mismatch')
    hz=x.get('frequency_hz'); rows=x.get('samples')
    if type(hz) is not int or hz<=0 or not isinstance(rows,list) or len(rows)<2:
        raise ValueError('missing native frequency or samples')
    last=-1
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'host_before_ns','hsa_ticks','host_after_ns'}:
            raise ValueError('invalid native sample')
        b,t,a=(row[k] for k in ('host_before_ns','hsa_ticks','host_after_ns'))
        if not all(type(v) is int and 0<=v<2**64 for v in (b,t,a)) or not begin_ns<=b<=a<=end_ns or t<last:
            raise ValueError('unordered or out-of-lifetime native sample')
        last=t
    # Choosing the narrowest host bracket minimizes local sampling uncertainty;
    # retain every original sample in the raw record for later calibration.
    best=min(rows,key=lambda row:row['host_after_ns']-row['host_before_ns'])
    return hz,best

def capture(directory, window, run_id, phase, producer, producer_sha256, *, timeout=30):
    if window not in WINDOWS or phase not in PHASES or not isinstance(run_id,str) or not ID.fullmatch(run_id):
        raise ValueError('invalid window, phase or lineage')
    producer=Path(producer).resolve(strict=True)
    if not re.fullmatch(r'[0-9a-f]{64}',producer_sha256) or digest(producer)!=producer_sha256:
        raise ValueError('clock producer does not match pin')
    root=Path(directory).resolve(strict=True)
    raw_name=f'{window}.{phase}.raw.json'; out_name=f'{window}.{phase}.json'
    if (root/raw_name).exists() or (root/out_name).exists(): raise FileExistsError('clock sample already captured')
    fd,tmp=tempfile.mkstemp(prefix='.clock-',suffix='.json',dir=root);os.close(fd)
    env=dict(os.environ,HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0',LD_LIBRARY_PATH='/opt/rocm/lib')
    proc=None
    try:
        begin=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        proc=subprocess.Popen([sys.executable,str(producer),'--out',tmp],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try: ticks=birth(proc.pid)
        except (FileNotFoundError,ValueError,IndexError):
            proc.wait(timeout=timeout)
            raise ValueError('producer birth identity unavailable')
        try: _,err=proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill();proc.communicate(timeout=5)
            raise TimeoutError('clock producer timed out')
        end=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        if proc.returncode!=0: raise RuntimeError('clock producer failed: '+err.decode(errors='replace')[-500:])
        if digest(producer)!=producer_sha256: raise ValueError('clock producer changed')
        fd=os.open(tmp,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size>1024*1024:raise ValueError('invalid native clock file')
            raw=b''
            while True:
                block=os.read(fd,65536)
                if not block:break
                raw+=block
        finally:os.close(fd)
        hz,best=validate(raw,proc.pid,begin,end)
        witness={'schema':'kpf50.clock-sample.v1','window':window,'run_id':run_id,'phase':phase,
                 'hsa_tick':best['hsa_ticks'],'hsa_hz':hz,'mono_before_ns':best['host_before_ns'],
                 'mono_after_ns':best['host_after_ns'],'native_file':raw_name,
                 'native_sha256':hashlib.sha256(raw).hexdigest(),'producer_sha256':producer_sha256,
                 'pid':proc.pid,'birth_ticks':ticks,'process_start_bound_ns':begin,'process_end_bound_ns':end}
        # Exclusive links do not overwrite earlier lineage evidence.
        with open(tmp,'rb') as f:os.fsync(f.fileno())
        os.link(tmp,root/raw_name,follow_symlinks=False)
        data=(json.dumps(witness,sort_keys=True)+'\n').encode()
        outfd=os.open(root/out_name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
        try:
            view=memoryview(data)
            while view:
                n=os.write(outfd,view)
                if n<=0:raise OSError('short witness write')
                view=view[n:]
            os.fsync(outfd)
        finally:os.close(outfd)
        dfd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
        return witness
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass
