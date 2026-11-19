"""Read-only authority/source/resource checks; no process or transport actions."""
import json
import os
from pathlib import Path
import time
import calendar
import re
import resource
import shutil
import output_reserve
from ledger import file_sha

BASE=Path(__file__).resolve().parent
DATA=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-normalization-r13/data')
VALIDATION=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-format-r9/q0')
ID='kpf18-g3-diagnostic-v1-20261029'
BIN=Path('/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/llama-server')
GRANT=Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))/(ID+'.grant')

def manifest(root,path):
    for line in Path(path).read_text().splitlines():
        expected,name=line.split('  ',1);target=Path(name)
        if not target.is_absolute():target=Path(root)/target
        if file_sha(target)!=expected:raise ValueError('source seal mismatch: '+str(target))

def sources():
    launch=BASE/'launch.sh';claimed=os.environ.get('KPF_LAUNCHER_SHA','')
    if not re.fullmatch('[0-9a-f]{64}',claimed) or file_sha(launch)!=claimed:raise ValueError('missing or changed launcher identity')
    matches=re.findall(r"printf '%s  %s\\n' ([0-9a-f]{64}) \"\$D/SOURCES.sha256\"",launch.read_text())
    if len(matches)!=1 or file_sha(BASE/'SOURCES.sha256')!=matches[0]:raise ValueError('manifest bootstrap changed')
    manifest(BASE,BASE/'SOURCES.sha256');manifest('/',BASE/'NATIVE-SOURCES.sha256')
    if file_sha(DATA/'SHA256SUMS')!='bf9745c975d70738b44709015c1cfd41a3bb7e7361d2578d469e3d87cd11af65':raise ValueError('accepted R13 data seal changed')
    manifest(DATA,DATA/'SHA256SUMS')
    if file_sha(VALIDATION/'SOURCES.sha256')!='3c32bf352e1f72426647c394d70a4b7c90399c9108ad9cbd503d34b2f25e6921':raise ValueError('accepted57+6 validation source changed')
    manifest(VALIDATION,VALIDATION/'SOURCES.sha256')
    manifest('/',VALIDATION/'NATIVE-SOURCES.sha256')
    if file_sha(BIN)!='2be7a16ed6d3712d82a36c668417b4dcec8d9cadd13a682e069cb4d57b9d0635':raise ValueError('wrong exact image ELF')
    if file_sha(BIN.parent/'libllama.so')!='33bf73eaedfee5a52aa07312d0d12431133e23c54d411744e7bd51bccf375f64':raise ValueError('wrong exact image DSO')

def tests_and_enrollment():
    # Historical framing result is scientific input, not a new approval receipt.
    replay=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-normalization-r14/revision-r3/cpu-replay/results/bridge/RESULT.json')
    if file_sha(replay)!='9c782023a139941349fb664e79c666df5ea894a231395761053bae2dd03a3225':raise ValueError('historical R14 framing result drift')
    result=json.loads(replay.read_text())
    if result.get('framing_pass') is not True or result.get('raw_sha256')!='7cbf105def05e9f874080f6def041754b19c109c7c9ddab5b2d64bf4666a33ee':raise ValueError('historical framing not valid')
    root=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/canonical-export-root')
    for name,digest in (('scripts/vidya/canonical.py','cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434'),('scripts/vidya/adapters/kv_prefix_fork.py','e6ead7b654defc820abefb71b997c12b93b49bc1dc0ac036e2b5e72b50b4895d'),('scripts/vidya/claim_tuple.py','6ae969f7029c1a6356593fd2432eca2320931f22aa4a8c4e3a388a72b81944e7')):
        if file_sha(root/name)!=digest:raise ValueError('historical projection code drift')
    return {'canonical_export':str(root),'scope':'diagnostic; no new enrollment receipt'}

def grant_window(start, end):
    def epoch(value):
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}Z", value):
            fmt="%Y-%m-%dT%H:%MZ"
        elif re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value):
            fmt="%Y-%m-%dT%H:%M:%SZ"
        else:raise ValueError("invalid UTC grant timestamp")
        return calendar.timegm(time.strptime(value,fmt))
    start_epoch,end_epoch=epoch(start),epoch(end)
    if end_epoch-start_epoch!=9000:raise ValueError("exact9000 GPU window invalid")
    return start_epoch,end_epoch

def attempt_root():
    value=os.environ.get('KPF_OUTPUT_ROOT','')
    root=Path(value)
    parent=BASE/'attempts'
    if not value or root.parent!=parent or not re.fullmatch(r'run-[0-9]+',root.name):raise ValueError('invalid attempt root')
    if parent.is_symlink() or root.is_symlink() or not root.is_dir():raise ValueError('unsafe attempt root')
    return root

def boundary():
    flags=Path('/mnt/raid0/llm/tmp/compute-flags')
    output_reserve.check(shutil.disk_usage(BASE).free,output_reserve.owned_bytes(attempt_root()))
    if os.environ.get('KPF_SMOKE')=='1':
        import gpu_smoke_admission
        gpu_smoke_admission.check()
        if (BASE/'STOP-smoke').exists() or (BASE/'STOP-smoke').is_symlink():raise ValueError('smoke STOP')
        end=int(os.environ['FILLER_END']);deadline=int(os.environ['FILLER_DEADLINE'])
        if not time.time()<deadline<end:raise ValueError('smoke deadline')
        return end
    if list(flags.glob('HOLD_*')) or list(Path('/mnt/raid0/llm/tmp').glob('HOLD_*')):raise ValueError('whole-host HOLD')
    if (BASE/'STOP').exists() or (BASE/'STOP').is_symlink():raise ValueError('STOP')
    if GRANT.is_symlink():raise ValueError('symlink grant')
    parts=GRANT.read_text().strip().split()
    if os.environ.get('FILLER_PREFLIGHT') or GRANT.parent!=flags/'grants':raise ValueError('private preflight or noncanonical grant forbidden')
    if len(parts)!=3 or parts[0]!='regions=mi210_0,184-191':raise ValueError('wrong exclusive GPU grant')
    start,end=grant_window(parts[1].removeprefix('start='),parts[2].removeprefix('end='))
    if end-start!=9000 or not start<=time.time()<end-90:raise ValueError('exact9000 GPU window/deadline invalid')
    if os.environ.get('FILLER_ID')!=ID or os.environ.get('FILLER_CPUS')!=parts[0].removeprefix('regions=mi210_0,'):
        raise ValueError('engine/grant identity mismatch')
    if os.environ.get('FILLER_STOPFILE')!=str(BASE/'STOP') or os.environ.get('FILLER_NEEDGPU')!='1':raise ValueError('engine stop or GPU identity mismatch')
    if os.environ.get('FILLER_END')!=str(end) or os.environ.get('FILLER_DEADLINE')!=str(end-90) or os.environ.get('FILLER_THREADS')!='8':
        raise ValueError('engine grant-derived boundaries mismatch')
    allowed=set(range(184,192))
    if not os.sched_getaffinity(0)<=allowed:raise ValueError('host-thread escape')
    if GRANT.with_suffix('.ended').exists() or GRANT.with_suffix('.complete').exists():raise ValueError('grant already terminal')
    return end

class ContextBoundary:
    def __init__(self,ctx):object.__setattr__(self,'original',ctx)
    def __getattr__(self,name):return getattr(self.original,name)
    def check_boundary(self):
        boundary();self.original.check_boundary()
        # Conservative sum of process high-water marks, not an invented
        # simultaneous measurement; only captured own server PIDs are read.
        peak_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        for server in self.original.own_children:
            if server.proc is None or server.proc.poll() is not None:continue
            status=Path(f'/proc/{server.proc.pid}/status').read_text().splitlines()
            peak_kib+=sum(int(line.split()[1]) for line in status if line.startswith('VmHWM:'))
        if peak_kib>176*1024**2:raise ValueError('conservative own process HWM sum exceeds176GiB (admission192GiB)')
        output=attempt_root()
        output_reserve.check(shutil.disk_usage(BASE).free,output_reserve.owned_bytes(output))
