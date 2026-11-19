"""Bounded native-child execution for admitted rows; no serving process control."""
import json
import os
from pathlib import Path
import subprocess
import time

BUDGET = 36 * 1024**3


def sample(pid, bindir, gpu, device, *, proc_root=Path('/proc'),
           kfd_root=Path('/sys/class/kfd/kfd/proc')):
    """Read DURING execution; return None until the required libraries are mapped."""
    bindir = Path(bindir).resolve()
    maps = (proc_root / str(pid) / 'maps').read_text()
    paths = {Path(line.split()[-1]).resolve() for line in maps.splitlines()
             if len(line.split()) >= 6 and Path(line.split()[-1]).name.startswith(('libllama', 'libggml'))}
    if any(p.parent != bindir for p in paths):
        raise ValueError('native child mapped foreign llama/ggml library')
    names = {p.name for p in paths}
    required = ('libllama', 'libggml-base') + (('libggml-hip',) if gpu else ())
    if not all(any(name.startswith(prefix) for name in names) for prefix in required):
        return None
    record = dict(pid=pid, monotonic_ns=time.monotonic_ns(), libraries=sorted(map(str, paths)))
    if gpu:
        kfd = kfd_root
        own = kfd / str(pid)
        files = list(own.glob('vram_*'))
        if not files:
            return None
        vram = sum(int(p.read_text()) for p in files)
        used = int(Path(device).read_text())
        if vram > BUDGET or used > BUDGET:
            raise ValueError(f'36 GiB GPU memory budget exceeded: own={vram}, device={used}, limit={BUDGET}')
        if vram <= 0 or used <= 0:
            return None
        record.update(own_vram_bytes=vram, device_vram_bytes=used,
                      kfd_process_count=len(list(kfd.iterdir())))
    return record


def stop(child):
    """Only the Popen child owned by this call; wait proves termination."""
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
    if child.poll() is None:
        raise RuntimeError('owned native child survived termination')


class Executor:
    def __init__(self, root, bindir, *, gpu, device=None, timeout_s=3600):
        self.root = Path(root)
        self.bindir = Path(bindir).resolve()
        self.gpu, self.device, self.timeout_s = gpu, device, timeout_s
        if not 1 <= timeout_s <= 86400 or (gpu and device is None):
            raise ValueError('bounded timeout and GPU device counter required')

    def __call__(self, argv, *, env=None, check=True):
        self.root.mkdir(parents=True, exist_ok=False)
        env = dict(os.environ if env is None else env)
        env['LD_LIBRARY_PATH'] = str(self.bindir)
        env.pop('LLAMA_KV_AM_BETA', None)
        count, misses = 0, 0
        started = time.monotonic()
        with (self.root / 'stdout.log').open('xb') as stdout, (self.root / 'stderr.log').open('xb') as stderr:
            child = subprocess.Popen(argv, env=env, stdout=stdout, stderr=stderr)
            try:
                with (self.root / 'samples.jsonl').open('x') as samples:
                    while child.poll() is None:
                        try:
                            r = sample(child.pid, self.bindir, self.gpu, self.device)
                        except (FileNotFoundError, ProcessLookupError):
                            r = None  # Exit/startup race is not a negative residency observation.
                        if r is not None:
                            samples.write(json.dumps(r) + '\n')
                            samples.flush()
                            count += 1
                        else:
                            misses += 1
                        if time.monotonic() - started > self.timeout_s:
                            raise TimeoutError('native phase deadline exceeded')
                        try:
                            child.wait(timeout=.25)
                        except subprocess.TimeoutExpired:
                            pass
                if check and child.returncode:
                    raise subprocess.CalledProcessError(child.returncode, argv)
                if count < 2:
                    raise ValueError('fewer than two live native linkage/residency samples')
                summary = dict(schema='epyc.am.live-execution.v1', pid=child.pid,
                               rc=child.returncode, gpu=self.gpu, live_samples=count,
                               unsampled_looks=misses, elapsed_s=time.monotonic() - started,
                               scope='sampled residency/budget; not a continuous memory high-water proof')
                (self.root / 'EXECUTION.json').write_text(json.dumps(summary, indent=2) + '\n')
                return subprocess.CompletedProcess(argv, child.returncode)
            finally:
                stop(child)
