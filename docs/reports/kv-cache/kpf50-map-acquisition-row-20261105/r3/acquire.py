"""Native own-child map-file acquisition. Import only; no CLI or implicit spawn."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import time

CLOCK = time.CLOCK_MONOTONIC_RAW

def now():
    return time.clock_gettime_ns(CLOCK)

def canonical_map_range(address):
    begin, end = (int(x, 16) for x in address.split('-'))
    if begin < 0 or end <= begin:
        raise ValueError('invalid mapping range')
    return f'{begin:x}-{end:x}'

def identity(pid):
    raw = Path(f'/proc/{pid}/stat').read_bytes()
    tail = raw[raw.rfind(b')') + 2:].split()
    return {'pid': pid, 'ppid': int(tail[1]), 'birth_ticks': int(tail[19]),
            'state': tail[0].decode(), 'stat_sha256': hashlib.sha256(raw).hexdigest()}

class OwnChild:
    """Keep this owner alive until capture and close complete. No shell launches."""
    def __init__(self, argv, *, env, cwd, stdout, stderr, pinned_fds):
        if not isinstance(argv, (list, tuple)) or not argv:
            raise ValueError('explicit argv required')
        self.pinned_fds = tuple(pinned_fds)
        if not self.pinned_fds: raise ValueError("parent-pinned descriptors required")
        self.pre_spawn_stats = {fd: os.fstat(fd) for fd in self.pinned_fds}
        self.pre_spawn_hashes = {}
        for fd, st in self.pre_spawn_stats.items():
            if not 0 < st.st_size <= 64*1024*1024: raise ValueError('unsupported pre-spawn file size')
            raw = os.pread(fd,st.st_size,0)
            if len(raw)!=st.st_size: raise RuntimeError('short pre-spawn descriptor read')
            self.pre_spawn_hashes[fd] = hashlib.sha256(raw).hexdigest()
        self.pre_spawn_clock_ns = now()
        self.process = subprocess.Popen(argv, env=env, cwd=cwd, stdout=stdout,
                                        stderr=stderr, stdin=subprocess.PIPE, close_fds=True, pass_fds=self.pinned_fds, shell=False)
        self.pidfd = None
        try:
            self.pidfd = os.pidfd_open(self.process.pid)
            self.birth = identity(self.process.pid)['birth_ticks']
            self.check()
        except BaseException:
            # Popen owns this freshly created, unreaped child; no PID search.
            self.process.kill()
            self.process.wait()
            if self.pidfd is not None:
                os.close(self.pidfd)
            raise

    def check(self):
        row = identity(self.process.pid)
        if (row['ppid'] != os.getpid() or row['birth_ticks'] != self.birth
                or row['state'] in ('Z', 'X') or self.process.poll() is not None):
            raise RuntimeError('owned live-child birth/parent identity unavailable')
        return row

    def close(self):
        if self.process.poll() is None:
            # pidfd binds the signal to the captured kernel process, never a reused PID.
            signal.pidfd_send_signal(self.pidfd, signal.SIGTERM)
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                signal.pidfd_send_signal(self.pidfd, signal.SIGKILL)
                self.process.wait(timeout=3)
        rc = self.process.wait(timeout=0)
        if self.process.stdin is not None:
            self.process.stdin.close()
        try:
            remaining = identity(self.process.pid)
        except FileNotFoundError:
            remaining = None
        if remaining is not None and remaining['birth_ticks'] == self.birth:
            raise RuntimeError('captured process still present after reap')
        os.close(self.pidfd)
        self.pidfd = None
        return {'pid': self.process.pid, 'birth_ticks': self.birth,
                'returncode': rc, 'captured_process_absent': True,
                'descendants_verified': False}

    def capture(self, *, max_segment_bytes=32*1024*1024):
        """Observe mapped file ranges using parent-retained inherited FDs."""
        out={'schema':'epyc.kpf50.own-child-inherited-fd-acquisition.v1',
             'status':'UNKNOWN','scientific_validity':'UNKNOWN',
             'mechanism':'parent-pinned-inherited-fd','clock':'CLOCK_MONOTONIC_RAW',
             'pre_spawn_clock_ns':self.pre_spawn_clock_ns,'begin_ns':now(),'supervisor_pid':os.getpid(),'mappings':[]}
        def statkey(st):
            return (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
        try:
            if type(max_segment_bytes) is not int or not 0<max_segment_bytes<=32*1024*1024:
                raise ValueError('invalid read bound')
            out['before']=self.check()
            proc=Path(f'/proc/{self.process.pid}')
            pins={}
            for fd in self.pinned_fds:
                st=os.fstat(fd)
                if statkey(st)!=statkey(self.pre_spawn_stats[fd]): raise RuntimeError('pinned file changed since before spawn')
                if not 0<st.st_size<=64*1024*1024: raise RuntimeError('unsupported pinned file size')
                data=os.pread(fd,st.st_size,0)
                if len(data)!=st.st_size: raise RuntimeError('short pinned file read')
                h=hashlib.sha256(data).hexdigest()
                if h!=self.pre_spawn_hashes[fd]: raise RuntimeError('pinned content changed since before spawn')
                pins[(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)]=(fd,st,h)
            maps=(proc/'maps').read_bytes();out['maps_raw']=maps.decode('utf8')
            out['maps_sha256']=hashlib.sha256(maps).hexdigest();seen=set()
            for line in out['maps_raw'].splitlines():
                parts=line.split(None,5)
                if len(parts)<6 or 'x' not in parts[1]:continue
                address,perms,offset,dev,inode,name=parts
                major,minor=(int(x,16) for x in dev.split(':'))
                key=(major,minor,int(inode))
                if key not in pins:continue
                fd,st,whole=pins[key];seen.add(key)
                begin,end=(int(x,16) for x in address.split('-'));length=end-begin
                if length<=0 or length>max_segment_bytes:raise RuntimeError('unsupported mapped range')
                start=int(offset,16);raw=os.pread(fd,length,start)
                if len(raw)!=length:raise RuntimeError('short inherited FD range read')
                out['mappings'].append({'range':address,'permissions':perms,'file_offset':start,
                    'pathname_observed':name,'dev':dev,'inode':int(inode),
                    'parent_retained_fd':fd,'spawn_inherited_fd':fd,
                    'file_stat_pre_spawn':list(statkey(self.pre_spawn_stats[fd])),'file_sha256_pre_spawn':self.pre_spawn_hashes[fd],
                    'file_stat_before':list(statkey(st)),'file_sha256_before':whole,
                    'observed_bytes':len(raw),'range_sha256':hashlib.sha256(raw).hexdigest(),
                    'status':'OBSERVED_FILE_RANGE','clock_ns':now()})
            if seen!=set(pins):raise RuntimeError('not every pinned FD has a native executable mapping')
            out['after']=self.check()
            after=(proc/'maps').read_bytes();out['maps_after_sha256']=hashlib.sha256(after).hexdigest()
            if after!=maps:raise RuntimeError('mapping set changed')
            for key,(fd,st,whole) in pins.items():
                st2=os.fstat(fd);data=os.pread(fd,st2.st_size,0)
                h=hashlib.sha256(data).hexdigest()
                if statkey(st2)!=statkey(st) or len(data)!=st.st_size or h!=whole:
                    raise RuntimeError('pinned file changed during observation')
                for row in out['mappings']:
                    if row['parent_retained_fd']==fd:
                        row['file_stat_after']=list(statkey(st2));row['file_sha256_after']=h
            out['status']='OBSERVED_FILE_RANGES'
            out['limitation']='File-backed ranges via inherited FDs; no map_files open, physical memory, residency, full target image, or request binding claim.'
        except (OSError,RuntimeError,ValueError,UnicodeError) as exc:
            out['reason']=f'{type(exc).__name__}: {exc}'
        finally:out['end_ns']=now()
        return out
