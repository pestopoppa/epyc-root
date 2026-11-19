import os,signal,subprocess,time,ctypes,re
from pathlib import Path
import device_identity
class Refusal(RuntimeError): pass
def birth_ticks(pid):
    s = (Path('/proc') / str(pid) / 'stat').read_text()
    return int(s[s.rfind(')') + 2:].split()[19])

def proc_group_members(pgid):
    members = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            rest = (p / 'stat').read_text().split(')', 1)[1].split()
            state, pgrp = rest[0], int(rest[2])
            if pgrp == pgid and state != 'Z':
                members.append(int(p.name))
        except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
            continue
    return members

def terminate_owned(proc, birth, timeout=5):
    # p3batch creates threads, not child processes. Signal only the captured leader.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if proc.poll() is not None: break
        try:
            if birth_ticks(proc.pid) != birth:
                raise Refusal('refusing reused captured PID during cleanup')
            # No name/group wildcard: only the Popen-captured, birth-checked PID.
            os.kill(proc.pid, sig)
        except (ProcessLookupError, FileNotFoundError): pass
        try: proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired: continue
    try: proc.wait(timeout=1)
    except subprocess.TimeoutExpired as e: raise Refusal('captured child did not reap') from e
    # Never guess ownership of surviving group members after leader exit.
    if proc_group_members(proc.pid):
        raise Refusal('uncaptured group members remain; cleanup incomplete, no group signal sent')
    if Path('/proc', str(proc.pid)).exists():
        raise Refusal('PID exists after reap; ownership unknown, no signal sent')
    return {'pid': proc.pid, 'birth_ticks': birth, 'verified_dead': True}


def child_setup(parent_pid):
    # Linux PR_SET_PDEATHSIG: child receives KILL if its owning producer dies.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent_pid:
        os._exit(127)

def maps_proof(pid, birth, libdir, expected):
    if birth_ticks(pid) != birth:
        raise Refusal('captured process PID was reused')
    paths = set()
    for line in (Path('/proc') / str(pid) / 'maps').read_text().splitlines():
        fields = line.split()
        if fields and fields[-1].startswith('/'):
            p = fields[-1].removesuffix(' (deleted)')
            try:
                paths.add(str(Path(p).resolve()))
            except FileNotFoundError:
                continue
    wanted = {name: str((libdir / name).resolve(strict=True)) for name in expected}
    loaded = {name: path in paths for name, path in wanted.items()}
    return loaded

def read_kfd(pid, birth, device, libdir, expected):
    mapped = maps_proof(pid, birth, libdir, expected)
    device_identity.revalidate(device)
    d = Path('/sys/class/kfd/kfd/proc') / str(pid)
    target = d / f"vram_{device['gpu_id']}"
    own = int(target.read_text().strip()) if target.is_file() else 0
    for other in d.glob('vram_*'):
        if other != target and int(other.read_text().strip()) > 0:
            raise Refusal('captured process has VRAM on a non-target KFD device')
    card = int(Path(device['card_vram_path']).read_text().strip())
    device_identity.revalidate(device)
    if birth_ticks(pid) != birth:
        raise Refusal('captured process identity changed during KFD sample')
    return {'t_monotonic': time.monotonic(), 'pid': pid, 'birth_ticks': birth,
            'gpu_id': device['gpu_id'], 'gpu_bdf': device['bdf'],
            'own_vram_b': own, 'card_vram_b': card, 'mapped_libraries': mapped}

def validate_cpu_grant(text, qualification):
    if not re.fullmatch(r'[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*', text):
        raise Refusal('missing/invalid actual CPU grant')
    cpus = set()
    for token in text.split(','):
        lo, _, hi = token.partition('-')
        lo, hi = int(lo), int(hi or lo)
        if hi < lo or hi > 191: raise Refusal('invalid CPU grant range')
        cpus.update(range(lo, hi + 1))
    inherited = set(os.sched_getaffinity(0))
    if qualification:
        available = sorted(cpus & inherited)
        if len(available) < 4:
            raise Refusal('GPU smoke needs four CPUs inside both grant and inherited affinity')
        actual = set(available[:4])
        os.sched_setaffinity(0, actual)
        if set(os.sched_getaffinity(0)) != actual:
            raise Refusal('failed to restrict smoke to exactly four granted CPUs')
    else:
        actual = inherited
        if cpus != actual or len(actual) != 8:
            raise Refusal('full affinity must equal the eight CPU grant')
    return {'declared': text, 'inherited_affinity': sorted(inherited),
            'affinity': sorted(actual), 'count': len(actual)}
