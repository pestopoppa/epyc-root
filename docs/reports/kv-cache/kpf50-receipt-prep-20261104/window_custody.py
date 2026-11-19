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
def validate_prior(dfd, window, run_id):
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
        raw=read_file(window+'.complete.json')
        receipt=json.loads(raw)
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
        for key in ('clock_before','clock_after','trace_manifest'):
            if decoded[key].get('window')!=window or decoded[key].get('run_id')!=run_id:
                return False
        # A manifest hash alone does not bind the bytes it points to at the
        # later no-redraw decision. Re-read every named trace on consumption.
        trace = decoded['trace_manifest']
        if trace.get('schema') != 'kpf50.trace-manifest.v1' or trace.get('complete') is not True or not isinstance(trace.get('files'), list) or not trace['files']:
            return False
        seen = set()
        evidence_names = {e['file'] for e in evid.values()}
        for entry in trace['files']:
            if not isinstance(entry, dict) or set(entry) != {'file', 'sha256'} or not isinstance(entry['file'], str) or entry['file'] in seen or entry['file'] in evidence_names or entry['file'] in (window + '.start.json', window + '.complete.json') or not isinstance(entry['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']):
                return False
            seen.add(entry['file'])
            data = read_file(entry['file'])
            if not data or hashlib.sha256(data).hexdigest() != entry['sha256']:
                return False
        return True
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return False
