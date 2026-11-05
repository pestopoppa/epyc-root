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

def identity(pid):
    raw = Path(f'/proc/{pid}/stat').read_bytes()
    tail = raw[raw.rfind(b')') + 2:].split()
    return {'pid': pid, 'ppid': int(tail[1]), 'birth_ticks': int(tail[19]),
            'state': tail[0].decode(), 'stat_sha256': hashlib.sha256(raw).hexdigest()}

class OwnChild:
    """Keep this owner alive until capture and close complete. No shell launches."""
    def __init__(self, argv, *, env, cwd, stdout, stderr):
        if not isinstance(argv, (list, tuple)) or not argv:
            raise ValueError('explicit argv required')
        self.process = subprocess.Popen(argv, env=env, cwd=cwd, stdout=stdout,
                                        stderr=stderr, stdin=subprocess.PIPE, close_fds=True, shell=False)
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
        """Read executable and ggml/llama executable mappings through map_files.

        Hash exactly the mapped file range, not a pathname reopened elsewhere.
        No weights, arbitrary pathname, offset guessing or supplied JSON evidence.
        """
        out = {'schema': 'epyc.kpf50.own-child-map-acquisition.v1',
               'status': 'UNKNOWN', 'scientific_validity': 'UNKNOWN',
               'clock': 'CLOCK_MONOTONIC_RAW', 'begin_ns': now(),
               'supervisor_pid': os.getpid(), 'mappings': []}
        try:
            if type(max_segment_bytes) is not int or not 0 < max_segment_bytes <= 32*1024*1024:
                raise ValueError('invalid read bound')
            out['before'] = self.check()
            proc = Path(f'/proc/{self.process.pid}')
            exe = os.readlink(proc/'exe')
            out['exe_link'] = exe
            maps = (proc/'maps').read_bytes()
            out['maps_raw'] = maps.decode('utf-8', errors='strict')
            out['maps_sha256'] = hashlib.sha256(maps).hexdigest()
            selected = []
            for line in out['maps_raw'].splitlines():
                parts = line.split(None, 5)
                if len(parts) < 6 or 'x' not in parts[1]:
                    continue
                address, perms, offset, dev, inode, name = parts
                base = name.rsplit('/', 1)[-1]
                if name != exe and not base.startswith(('libggml', 'libllama')):
                    continue
                selected.append((address, offset, dev, inode, name, perms))
            if not selected:
                raise RuntimeError('no selected native executable mapping')
            for address, offset, dev, inode, name, perms in selected:
                begin, end = (int(x, 16) for x in address.split('-'))
                length = end - begin
                row = {'range': address, 'file_offset': int(offset, 16),
                       'map_dev': dev, 'map_inode': int(inode), 'pathname_observed': name,
                       'permissions': perms, 'begin_ns': now(), 'status': 'UNKNOWN'}
                out['mappings'].append(row)
                if length <= 0 or length > max_segment_bytes:
                    raise RuntimeError('mapping exceeds declared range-read bound')
                link = proc/'map_files'/address
                row['map_files_link'] = os.readlink(link)
                fd = os.open(link, os.O_RDONLY | os.O_CLOEXEC)
                try:
                    st = os.fstat(fd)
                    row['native_map_files_fd'] = fd
                    row['opened_identity'] = {'dev_major': os.major(st.st_dev),
                        'dev_minor': os.minor(st.st_dev), 'inode': st.st_ino, 'size': st.st_size}
                    major, minor = (int(x, 16) for x in dev.split(':'))
                    if (major, minor, int(inode)) != (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino):
                        raise RuntimeError('map_files opened-object identity mismatch')
                    raw = os.pread(fd, length, int(offset, 16))
                    if len(raw) != length:
                        raise RuntimeError('short mapped-file range read')
                    row.update(observed_bytes=len(raw), range_sha256=hashlib.sha256(raw).hexdigest(),
                               status='OBSERVED_FILE_RANGE', end_ns=now())
                finally:
                    os.close(fd)
            out['after'] = self.check()
            maps_after = (proc/'maps').read_bytes()
            out['maps_after_sha256'] = hashlib.sha256(maps_after).hexdigest()
            if maps_after != maps:
                raise RuntimeError('mapping set changed during acquisition')
            out['status'] = 'OBSERVED_FILE_RANGES'
            out['limitation'] = 'File-backed bytes only; not resident memory, full DSO digest, HIP activity, GPU residency, request binding or trunk attribution.'
        except (OSError, RuntimeError, ValueError, UnicodeError) as exc:
            out['reason'] = f'{type(exc).__name__}: {exc}'
        finally:
            out['end_ns'] = now()
        return out
