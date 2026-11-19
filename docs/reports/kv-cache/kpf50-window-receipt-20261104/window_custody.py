"""Prospective KPF-50 no-redraw marker primitive; not integrated with the runner."""
import json, os, re, stat
from pathlib import Path

ORDER = ('full-a', 'mask-a', 'mask-b', 'full-b')

def begin(directory, window, run_id, validate_prior=None):
    """Durably record exposure before the caller is allowed to issue a request.

    Every existing start is terminal for this identity, even after a crash. The
    caller must retain this directory for the lifetime of the whole lineage.
    """
    if window not in ORDER or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', run_id):
        raise ValueError('invalid window or run identity')
    root = Path(directory)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    dfd = os.open(root, flags)
    try:
        for other in ORDER:
            try:
                st = os.stat(other + '.start.json', dir_fd=dfd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(st.st_mode):
                raise ValueError('non-regular exposure marker')
            if other == window:
                raise FileExistsError('window already exposed or begun')
        for prior in ORDER[:ORDER.index(window)]:
            try:
                st = os.stat(prior + '.complete.json', dir_fd=dfd, follow_symlinks=False)
            except FileNotFoundError as exc:
                raise ValueError('prior window incomplete') from exc
            if not stat.S_ISREG(st.st_mode):
                raise ValueError('non-regular completion marker')
            if validate_prior is None or validate_prior(dfd, prior, run_id) is not True:
                raise ValueError('prior completion not independently validated')
        name = window + '.start.json'
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
        try:
            payload = (json.dumps({'schema':'kpf50.window-start.v1','window':window,'run_id':run_id}, sort_keys=True)+'\n').encode()
            view = memoryview(payload)
            while view:
                n = os.write(fd, view)
                if n <= 0: raise OSError('short marker write')
                view = view[n:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(dfd)
    finally:
        os.close(dfd)

# This validator accepts only a specifically authored v1 window receipt. The
# current KPF-50 runner does not produce one; it must not create these markers.
# Receipt availability is never inferred from an existing generic done marker.
def validate_prior(dfd, window, run_id, receipt_override=None):
    import hashlib
    def read_file(name):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', name) or name.lower().endswith('.gguf'):
            raise ValueError('unsafe evidence path')
        fd=os.open(name,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=dfd)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size>10485760:
                raise ValueError('invalid evidence file')
            chunks=[]
            while True:
                block=os.read(fd,1048576)
                if not block: break
                chunks.append(block)
            return b''.join(chunks)
        finally: os.close(fd)
    try:
        receipt=(json.loads(read_file(window+'.complete.json')) if receipt_override is None else receipt_override)
        if set(receipt)!={'schema','window','run_id','start_sha256','evidence'}:
            return False
        if receipt['schema']!='kpf50.window-complete.v1' or receipt['window']!=window or receipt['run_id']!=run_id:
            return False
        start=read_file(window+'.start.json')
        if hashlib.sha256(start).hexdigest()!=receipt['start_sha256']:
            return False
        start_data=json.loads(start)
        if start_data!={'schema':'kpf50.window-start.v1','window':window,'run_id':run_id}:
            return False
        evid=receipt['evidence']
        if not isinstance(evid,dict) or set(evid)!={'outcome','cleanup','clock_before','clock_after','trace_manifest'}:
            return False
        decoded={}
        for key,entry in evid.items():
            if not isinstance(entry,dict) or set(entry)!={'file','sha256'} or not re.fullmatch(r'[0-9a-f]{64}',entry['sha256']):
                return False
            data=read_file(entry['file'])
            if hashlib.sha256(data).hexdigest()!=entry['sha256']:return False
            decoded[key]=json.loads(data)
        outcome=decoded['outcome']; cleanup=decoded['cleanup']
        # Strict typed binding, not a scientific quality or calibration verdict.
        if outcome.get('schema')!='kpf50.window-outcome.v1' or outcome.get('window')!=window or outcome.get('run_id')!=run_id or outcome.get('complete') is not True:
            return False
        if cleanup.get('schema')!='kpf50.cleanup.v1' or cleanup.get('window')!=window or cleanup.get('run_id')!=run_id or cleanup.get('verified_dead') is not True or cleanup.get('remaining_children')!=0:
            return False
        clocks=[]
        for key in ('clock_before','clock_after'):
            c=decoded[key]
            if c.get('schema')!='kpf50.clock-sample.v1' or c.get('window')!=window or c.get('run_id')!=run_id or c.get('phase')!=key:
                return False
            for field in ('hsa_tick','hsa_hz','mono_before_ns','mono_after_ns','pid','birth_ticks','process_start_bound_ns','process_end_bound_ns'):
                if type(c.get(field)) is not int or c[field]<0 or c[field]>=2**64:return False
            if not c['hsa_hz'] or not c['pid'] or not c['birth_ticks'] or not c['process_start_bound_ns']<=c['mono_before_ns']<=c['mono_after_ns']<=c['process_end_bound_ns']:return False
            if not re.fullmatch(r'[0-9a-f]{64}',c.get('producer_sha256','')) or not re.fullmatch(r'[0-9a-f]{64}',c.get('native_sha256','')):return False
            raw=read_file(c['native_file'])
            if hashlib.sha256(raw).hexdigest()!=c['native_sha256']:return False
            native=json.loads(raw); rows=native.get('samples')
            if native.get('schema')!='epyc.kpf50.hsa-clock.v1' or native.get('pid')!=c['pid'] or native.get('frequency_hz')!=c['hsa_hz'] or not isinstance(rows,list) or len(rows)<2:return False
            last=-1
            for row in rows:
                if not isinstance(row,dict) or set(row)!={'host_before_ns','hsa_ticks','host_after_ns'}:return False
                b,t,a=(row[k] for k in ('host_before_ns','hsa_ticks','host_after_ns'))
                if not all(type(v) is int and 0<=v<2**64 for v in (b,t,a)) or not c['process_start_bound_ns']<=b<=a<=c['process_end_bound_ns'] or t<last:return False
                last=t
            best=min(rows,key=lambda r:r['host_after_ns']-r['host_before_ns'])
            if (best['hsa_ticks'],best['host_before_ns'],best['host_after_ns'])!=(c['hsa_tick'],c['mono_before_ns'],c['mono_after_ns']):return False
            clocks.append(c)
        if clocks[0]['hsa_hz']!=clocks[1]['hsa_hz'] or clocks[0]['hsa_tick']>=clocks[1]['hsa_tick'] or clocks[0]['mono_after_ns']>clocks[1]['mono_before_ns']:return False
        trace=decoded['trace_manifest']
        if trace.get('schema')!='kpf50.trace-manifest.v1' or trace.get('window')!=window or trace.get('run_id')!=run_id or trace.get('complete') is not True or not isinstance(trace.get('files'),list) or not trace['files']:return False
        import csv, io
        names=set()
        for item in trace['files']:
            if not isinstance(item,dict) or set(item)!={'file','sha256'} or not isinstance(item['file'],str) or not item['file'].startswith(window+'.'+run_id+'.') or not item['file'].endswith('.csv') or item['file'] in names or not re.fullmatch(r'[0-9a-f]{64}',item['sha256']):return False
            names.add(item['file']);raw=read_file(item['file'])
            if not raw or hashlib.sha256(raw).hexdigest()!=item['sha256']:return False
            rows=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''))
            if not rows.fieldnames or len(rows.fieldnames)!=len(set(rows.fieldnames)) or not {'KernelName','BeginNs','EndNs'}<=set(rows.fieldnames):return False
            count=0
            for row in rows:
                if None in row or not row.get('KernelName','').strip() or int(row['BeginNs'])<0 or int(row['BeginNs'])>=int(row['EndNs']):return False
                count+=1
            if not count:return False
        return True
    except (OSError,ValueError,TypeError,KeyError,AttributeError,UnicodeError):
        return False


def finish(directory, window, run_id, evidence):
    """Seal independently checkable evidence for an already-exposed window.

    Only pre-existing, prospectively recorded evidence may be passed here. The
    validator checks structural custody, not scientific validity. An interrupted
    write leaves a terminal incomplete marker, never permission to redraw.
    """
    import hashlib
    if window not in ORDER or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', run_id):
        raise ValueError('invalid window or lineage')
    dfd=os.open(Path(directory),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        startfd=os.open(window+'.start.json',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=dfd)
        try:
            st=os.fstat(startfd)
            if not stat.S_ISREG(st.st_mode) or st.st_size>4096: raise ValueError('invalid start marker')
            start=b''
            while True:
                block=os.read(startfd,4096)
                if not block: break
                start+=block
        finally: os.close(startfd)
        receipt={'schema':'kpf50.window-complete.v1','window':window,'run_id':run_id,
                 'start_sha256':hashlib.sha256(start).hexdigest(),'evidence':evidence}
        if not validate_prior(dfd,window,run_id,receipt_override=receipt):
            raise ValueError('evidence does not satisfy completion contract')
        fd=os.open(window+'.complete.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600,dir_fd=dfd)
        try:
            data=(json.dumps(receipt,sort_keys=True)+'\n').encode()
            view=memoryview(data)
            while view:
                n=os.write(fd,view)
                if n<=0: raise OSError('short receipt write')
                view=view[n:]
            os.fsync(fd)
        finally: os.close(fd)
        os.fsync(dfd)
    finally: os.close(dfd)
