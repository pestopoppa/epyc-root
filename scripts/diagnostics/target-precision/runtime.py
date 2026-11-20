"""Owned-child residency observations. No model reads and no grading authority."""
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import time

SCHEMA = 'epyc.target-precision.runtime.v1'
ACCELERATORS = tuple('libggml-' + name for name in ('hip', 'cuda', 'vulkan', 'sycl', 'metal', 'opencl', 'musa', 'cann'))


def _birth(directory):
    # comm may contain spaces or parentheses; starttime is field 22.
    fields = (directory / 'stat').read_text().rsplit(')', 1)[1].split()
    if fields[0] in ('Z', 'X'):
        raise ValueError('child is no longer running')
    return int(fields[19])


def _identity(path, cache):
    """Stream library bytes once per stable inode; reject replacements/races."""
    def key(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    named = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(named.st_mode) or named.st_size > 512 << 20:
        raise ValueError('library must be a bounded regular file')
    if key(named) not in cache:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            digest = hashlib.sha256()
            total = 0
            while True:
                block = os.read(fd, 1 << 20)
                if not block:
                    break
                total += len(block)
                if total > 512 << 20:
                    raise ValueError('library byte bound exceeded')
                digest.update(block)
            if (key(before) != key(named) or key(os.fstat(fd)) != key(named)
                    or key(path.stat(follow_symlinks=False)) != key(named) or total != named.st_size):
                raise ValueError('library changed during read')
            cache[key(named)] = digest.hexdigest()
        finally:
            os.close(fd)
    return dict(sha256=cache[key(named)], device=named.st_dev, inode=named.st_ino)


def snapshot(pid, libraries, backend, cache, proc=Path('/proc'), kfd=Path('/sys/class/kfd/kfd/proc')):
    directory = proc / str(pid)
    birth = _birth(directory)
    maps = (directory / 'maps').read_text()
    mapped = {}
    for line in maps.splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6 and parts[5].startswith('/'):
            path = parts[5]
            name = Path(path).name
            if path in libraries or name.startswith(('libggml', 'libllama')):
                if path not in libraries:
                    raise ValueError('undeclared inference library: ' + path)
                identity = _identity(Path(path), cache)
                major, minor = (int(v, 16) for v in parts[3].split(':'))
                if (identity['device'], identity['inode']) != (os.makedev(major, minor), int(parts[4])):
                    raise ValueError('mapped library inode differs from hashed file')
                if identity['sha256'] != libraries[path]:
                    raise ValueError('mapped library digest mismatch')
                mapped[path] = identity
    if set(mapped) != set(libraries):
        raise ValueError('declared libraries not mapped in owned child')
    if backend == 'cpu' and any(Path(p).name.startswith(ACCELERATORS) for p in mapped):
        raise ValueError('accelerator library in CPU panel')
    if backend == 'hip' and not any(Path(p).name.startswith('libggml-hip') for p in mapped):
        raise ValueError('HIP library absent')
    client = kfd / str(pid)
    vram = {p.name: int(p.read_text().strip()) for p in client.glob('vram_*')} if client.is_dir() else {}
    if any(v < 0 for v in vram.values()):
        raise ValueError('negative VRAM counter')
    if backend == 'hip' and (not client.is_dir() or sum(vram.values()) <= 0):
        raise ValueError('HIP child lacks KFD membership/nonzero VRAM')
    if _birth(directory) != birth:
        raise ValueError('process identity changed during sample')
    return dict(pid=pid, start_ticks=birth, monotonic_ns=time.monotonic_ns(),
                maps=maps, libraries=mapped, kfd_registered=client.is_dir(), vram=vram)


def validate(record, plan, request):
    """Replay the retained per-cell observations; consistency is not attestation."""
    if (record.get('schema') != SCHEMA or record.get('request') != request
            or any(type(record.get(k)) is not int or record[k] <= 0 for k in ('owner_pid', 'child_pid'))
            or record.get('child_pid') == record.get('owner_pid')):
        raise ValueError('runtime ownership/request mismatch')
    samples = record.get('samples', [])
    if record.get('fatal_error') or record.get('timed_out') or record.get('returncode') != 0:
        raise ValueError('runtime observation failed')
    if len(samples) < 2:
        raise ValueError('two during-cell residency observations required')
    expected = plan['admission']['runtime_proof']['mapped_library_sha256']
    if plan['backend'] == 'cpu' and any(Path(p).name.startswith(ACCELERATORS) for p in expected):
        raise ValueError('retained accelerator library in CPU panel')
    birth = samples[0]['start_ticks']
    previous = -1
    for sample in samples:
        if any(type(sample.get(k)) is not int or sample[k] <= 0 for k in ('pid', 'start_ticks', 'monotonic_ns')):
            raise ValueError('invalid runtime process/time identity')
        if (sample['pid'] != record['child_pid'] or sample['start_ticks'] != birth
                or sample['monotonic_ns'] <= previous):
            raise ValueError('runtime PID/birth/time mismatch')
        previous = sample['monotonic_ns']
        if {p: v['sha256'] for p, v in sample['libraries'].items()} != expected:
            raise ValueError('runtime library binding mismatch')
        # Replay maps against the retained inode identities, not present-day files.
        seen = set()
        for line in sample['maps'].splitlines():
            parts = line.split(None, 5)
            if len(parts) != 6:
                continue
            path = parts[5]
            if path in expected:
                identity = sample['libraries'][path]
                major, minor = (int(v, 16) for v in parts[3].split(':'))
                if (os.makedev(major, minor), int(parts[4])) != (identity['device'], identity['inode']):
                    raise ValueError('retained maps inode mismatch')
                seen.add(path)
            elif Path(path).name.startswith(('libggml', 'libllama')):
                raise ValueError('undeclared retained inference library')
        if seen != set(expected):
            raise ValueError('retained maps lack declared libraries')
        if plan['backend'] == 'hip' and (not sample['kfd_registered'] or not sample['vram']
                or any(type(v) is not int or v < 0 for v in sample['vram'].values())
                or sum(sample['vram'].values()) <= 0
                or not any(Path(p).name.startswith('libggml-hip') for p in expected)):
            raise ValueError('retained HIP residency missing')
    return record


def execute(command, env, stdout, stderr, timeout, plan, request):
    """Observe only the Popen child, retaining two qualifying samples and errors.

    Wait timeouts pace in-process observation, never coordination/queue polling.
    A missed/short window refuses success; it cannot establish non-residency.
    """
    record = dict(schema=SCHEMA, request=request, owner_pid=os.getpid(), samples=[],
                  errors=[], attempts=0)
    cache = {}
    deadline = time.monotonic() + timeout
    with subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr) as child:
        record['child_pid'] = child.pid
        try:
            while child.poll() is None:
                record['attempts'] += 1
                try:
                    sample = snapshot(child.pid, plan['admission']['runtime_proof']['mapped_library_sha256'], plan['backend'], cache)
                    if len(record['samples']) < 2:
                        record['samples'].append(sample)
                    elif sample['start_ticks'] != record['samples'][0]['start_ticks']:
                        raise ValueError('child birth changed')
                except (OSError, ValueError) as exc:
                    if len(record['errors']) < 8:
                        record['errors'].append(str(exc))
                    if isinstance(exc, ValueError) and str(exc) not in (
                            'declared libraries not mapped in owned child', 'HIP library absent',
                            'HIP child lacks KFD membership/nonzero VRAM', 'child is no longer running'):
                        record['fatal_error'] = str(exc)
                        child.kill()
                        child.wait()
                        break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                try:
                    child.wait(timeout=min(.1, remaining))
                except subprocess.TimeoutExpired:
                    continue
            record['returncode'] = child.returncode
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            record.update(timed_out=True, returncode=child.returncode)
        except BaseException:
            child.kill()  # only our own captured PID; wait confirms death/reaps it
            child.wait()
            raise
    return record
