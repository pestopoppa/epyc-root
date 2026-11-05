"""Prospective G3 PCI/KFD-bound sampling; does not launch or authorize inference.

The native gate still owns Popen/start/stop. install() replaces its sampling
implementation only. Device-wide allocation is a ceiling input, never own VRAM.
Missing residency stays UNKNOWN; samples do not establish GPU compute activity.
"""
import hashlib
import os
from pathlib import Path
import sys
import time
import types

HELPER_SHA256 = 'dd36ae78e28f4fd048ed6411a038386410cfd6853b5c7ffc9194308b412e68a9'
BINARY = Path('/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/llama-server')
BINARY_SHA256 = '2be7a16ed6d3712d82a36c668417b4dcec8d9cadd13a682e069cb4d57b9d0635'
BACKEND = BINARY.parent / 'libggml-hip.so.0.16.0'
BACKEND_SHA256 = '65063d18e76079c2e74b5ca882e72f8266c9237dc9d9f598edc50576babc51e9'


def pinned(path, digest):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular source/artifact required: ' + str(path))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('GPU source/artifact pin mismatch: ' + str(path))
    return raw


def helper():
    # Execute exactly the reviewed bytes, avoiding import search and stale pyc.
    path = Path(__file__).with_name('sysfs_residency.py')
    module = types.ModuleType('g3_bound_sysfs_residency')
    exec(compile(pinned(path, HELPER_SHA256), str(path), 'exec'), module.__dict__)
    return module


def discover():
    return helper().discover()


def stat_identity(path):
    st = Path(path).stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def device_used():
    device = discover()
    used = int(Path(device['device_vram']).read_text())
    if used < 0:
        raise ValueError('negative device VRAM')
    return used


class Witness:
    def __init__(self, device, *, backend=BACKEND, binary=BINARY,
                 proc_root=Path('/proc'), kfd_root=Path('/sys/class/kfd/kfd/proc'),
                 mechanism=None, artifacts=None):
        self.mechanism = mechanism or helper()
        self.device = device
        self.backend, self.binary = Path(backend), Path(binary)
        self.proc_root, self.kfd_root = Path(proc_root), Path(kfd_root)
        self.artifacts = artifacts or {str(p): stat_identity(p) for p in (self.binary, self.backend)}
        self.pid = self.birth = None

    def sample(self, pid):
        if any(stat_identity(path) != identity for path, identity in self.artifacts.items()):
            raise ValueError('pinned GPU artifact changed')
        if type(pid) is not int or pid <= 0:
            raise ValueError('native owned PID required')
        birth = self.mechanism.proc_birth(pid, self.proc_root)
        if self.pid is None:
            self.pid, self.birth = pid, birth
        if (pid, birth) != (self.pid, self.birth):
            raise ValueError('native owned PID/birth changed')
        if self.mechanism.discover(Path(self.device['drm']), Path(self.device['nodes'])) != self.device:
            raise ValueError('GPU topology changed')
        sample = self.mechanism.read_sysfs_sample(
            pid=pid, birth=birth, device=self.device, backend=self.backend,
            proc_root=self.proc_root, kfd_root=self.kfd_root)
        sample['exe_matches_binary'] = os.path.samefile(self.proc_root / str(pid) / 'exe', self.binary)
        sample['status'] = ('RESIDENT_SNAPSHOT' if sample['exe_matches_binary'] and
                            sample['hip_mapped'] and sample['kfd_pid_present'] and
                            type(sample['own_vram_bytes']) is int and sample['own_vram_bytes'] > 0
                            else 'UNKNOWN')
        # Birth must enclose the executable check as well as the maps/KFD reads.
        if self.mechanism.proc_birth(pid, self.proc_root) != birth:
            raise ValueError('native owned PID/birth changed during witness')
        return sample


def install(gate):
    """Bind native --card and sampling before gate.main parses its arguments.

    Native Sampler assigns own_pid from its actual Popen. We never discover PIDs
    by name. No gate process or socket lifecycle function is replaced.
    """
    if getattr(gate, '_g3_bound_sampler_installed', False):
        raise ValueError('GPU sampler already installed')
    pinned(BINARY, BINARY_SHA256)
    pinned(BACKEND, BACKEND_SHA256)
    artifacts = {str(p): stat_identity(p) for p in (BINARY, BACKEND)}
    mechanism = helper()
    device = mechanism.discover()
    card = Path(device['device_vram']).parent
    if any(arg == '--card' or arg.startswith('--card=') for arg in sys.argv[1:]):
        raise ValueError('caller card override forbidden')
    sys.argv.extend(['--card', str(card)])
    original = gate.Sampler

    class BoundSampler(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if Path(self.card) != card:
                raise ValueError('native sampler device mismatch')
            self.witness = Witness(device, mechanism=mechanism, artifacts=artifacts)

        def _run(self):
            while not self._stop.is_set():
                try:
                    if mechanism.discover() != device:
                        raise ValueError('GPU topology changed')
                    used = int(Path(device['device_vram']).read_text())
                    if used < 0:
                        raise ValueError('negative device VRAM')
                    rec = {'t': time.time(), 'device_identity': device,
                           'card_used_b': used, 'own_pid': self.own_pid,
                           'own_vram_b': None, 'status': 'UNKNOWN'}
                    if self.own_pid is not None:
                        sample = self.witness.sample(self.own_pid)
                        rec['owned_witness'] = sample
                        rec['status'] = sample['status']
                        rec['own_vram_b'] = sample['own_vram_bytes']
                        if sample['status'] == 'RESIDENT_SNAPSHOT':
                            self.n_own_nonzero += 1
                            self.own_peak = max(self.own_peak, sample['own_vram_bytes'])
                            self.consec_own_zero = 0
                        else:
                            self.consec_own_zero += 1
                    self.sink.add(rec)
                    self.n += 1
                    self.first_t = self.first_t or rec['t']
                    self.last_t = rec['t']
                    self.card_peak = max(self.card_peak, used)
                    self.kfd_count_max = max(self.kfd_count_max, int(rec['status'] == 'RESIDENT_SNAPSHOT'))
                    if used > self.ceiling or (rec['own_vram_b'] is not None and rec['own_vram_b'] > self.ceiling):
                        raise ValueError('bound GPU VRAM ceiling')
                except Exception as error:
                    # The native sampler starts before Popen and stops after
                    # confirmed process death. Missing proc at those edges is
                    # retained as UNKNOWN; identity/topology errors abort.
                    missing_owned_proc = (isinstance(error, FileNotFoundError) and self.own_pid is not None and
                                          str(error.filename).startswith('/proc/' + str(self.own_pid) + '/'))
                    if missing_owned_proc or isinstance(error, ProcessLookupError):
                        self.sink.add({'t': time.time(), 'own_pid': self.own_pid,
                                       'status': 'UNKNOWN', 'error': str(error)})
                    else:
                        self.abort_reason = str(error)
                        self.abort.set()
                        self.sink.add({'t': time.time(), 'abort': self.abort_reason})
                        return
                self._stop.wait(1.0)

        def summary(self):
            result = super().summary()
            result.update(device_identity=device, schema='kpf18.g3.gpu-witness.v1',
                          binary_sha256=BINARY_SHA256, backend_sha256=BACKEND_SHA256,
                          residency_source_sha256=HELPER_SHA256,
                          interpretation='own PID/birth and exact HIP mapping with per-device KFD allocation; snapshots only, no compute or true peak claim',
                          kfd_process_count_max_scope='captured own PID only')
            return result

    gate.Sampler = BoundSampler
    gate._g3_bound_sampler_installed = True
    return device
