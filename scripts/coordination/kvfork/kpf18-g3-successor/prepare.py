#!/usr/bin/env python3
"""Integrate reviewed G3 repairs into a new disabled scratch preparation."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TOOLS = HERE.with_name('kpf18-g3-custody')
sys.path.insert(0, str(TOOLS))
from rebind_manifest import read_regular
from verify_manifest import verify
from prepare_r9_validation import PINS as R9_PINS, R9 as R9_ROOT
from rowflow_entry import command as rowflow_command

SOURCE = Path('/mnt/raid0/llm/tmp/kpf18-g3-repair-successor-20261029/candidate')
CUSTODY = Path('/mnt/raid0/llm/tmp/kvfork/g3-integrated-prep-20261104')
ROW = 'kpf18-g3-provider-transport-prep-20261104'
RUNTIME_PIN = '04c0d3922939496fb100b0a7b0a0efe228ee7f3611ad025cc6d47d3c8bb684f7'
WITNESS_PIN = '8b598901b6d4d5edd1ca1e9cf5844b7ca22e4f3ede2817a1df72edb104f2478c'
PROVIDER_PIN = '75d470545c780089bb4bf2e5492e3036b77ea51a8cb12ed50fb6f311011932ab'
LAUNCH_PIN = 'b6c5f22784322e8784c39712d77bcd723ab00bd7f0559f5dc0bfaedc6fce5a6c'
ROWFLOW_PINS = {
    'filler_run15.sh': '492fbcec0b7e21e0f8fff7207049ec533275c26251da35d5cfed8ed0e3e9588c',
    'filler_lib.sh': '241e522f4a7d7208e7485834c90d77676434a9bc88fd253575e034ad2934237c',
}


R9_RECEIPT = Path('/mnt/raid0/llm/tmp/kvfork/g3-r9-validation-complete-20261104/RESULT.json')
R9_RECEIPT_PIN = '72cdb01f1a53e51fa3810c6e46efd46892d1923ba0d760ffcb4a2a3f2a61d8f5'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, expected):
    raw = read_regular(path)
    if sha(raw) != expected:
        raise ValueError('reviewed source pin mismatch: ' + str(path))
    return raw


def inventory(source, raw):
    entries = {}
    for line in raw.decode().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([^\n]+)', line)
        if not match:
            raise ValueError('malformed runtime inventory')
        digest, name = match.groups()
        if Path(name).is_absolute() or '..' in Path(name).parts or name in entries:
            raise ValueError('unsafe runtime inventory')
        target = source / name
        if name == 'fork-launch-native.raw' and not target.exists():
            target = Path('/mnt/raid0/llm/tmp/kvfork/g3-custody/candidate/fork-launch-native.raw')
        entries[name] = pinned(target, digest)
    if not entries:
        raise ValueError('empty runtime inventory')
    return entries


ADAPTER = '''"""Prospective official-row provider adapter; never acquires a lock."""
import json, os
from pathlib import Path
import current_lock
ROW = ROW_VALUE
SOURCES = json.loads((Path(__file__).parent/'provider-sources.json').read_text())
_witness = None

def capture_gpu():
    global _witness
    if os.environ.get('FILLER_ID') != ROW:
        raise ValueError('successor official row identity absent')
    if _witness is None:
        _witness = current_lock.capture(ROW, SOURCES)
    else:
        current_lock.recheck(_witness)
    return _witness['owner'], _witness

def verify_gpu(owner, witness):
    if os.environ.get('FILLER_ID') != ROW or owner != witness['owner'] or witness['row_id'] != ROW:
        raise ValueError('successor row/provider changed')
    return current_lock.recheck(witness)

def boundary():
    owner, witness = capture_gpu()
    return verify_gpu(owner, witness)
'''.replace('ROW_VALUE', repr(ROW))



def validation_closure(receipt_path, receipt_pin):
    """Recheck independently reviewed R9 result; a current digest is never approval."""
    receipt_path = Path(receipt_path)
    if (receipt_path.parent/'INCOMPLETE').exists():
        raise ValueError('independent validation incomplete')
    raw = pinned(receipt_path, receipt_pin)
    result = json.loads(raw)
    if result.get('status') != 'INDEPENDENT_R9_CUSTODY_ONLY' or result.get('runtime_dispatch') is not False:
        raise ValueError('independent validation receipt not custody-only')
    checks = result.get('checks', [])
    expected = {str(R9_ROOT/name): digest for name, digest in R9_PINS.items()}
    if len(checks) != 3 or {c.get('original') for c in checks} != set(expected):
        raise ValueError('incomplete independent validation closure')
    paths = [str(receipt_path)]
    for check in checks:
        original=check['original']; original_pin=expected[original]
        if check['original_sha256'] != original_pin:
            raise ValueError('independent original pin changed')
        pinned(Path(original), original_pin)
        count=verify(Path(check['manifest']),check['expected_paths'],check['manifest_sha256'])
        if count != check['verified_entries']:
            raise ValueError('independent validation count changed')
        paths.extend([original,check['manifest'],*check['expected_paths']])
    return raw, sorted(set(paths))


def prepare(output):
    output = Path(output)
    if not output.is_absolute() or output.exists():
        raise ValueError('new absolute destination required')
    raw = pinned(SOURCE/'SOURCES.sha256', RUNTIME_PIN)
    entries = inventory(SOURCE, raw)
    launch = pinned(SOURCE/'launch.sh', LAUNCH_PIN)
    supervision = HERE.with_name('kpf18-g3-supervision')
    base = read_regular(supervision/'BASE.sha256').decode().strip().split('  ')
    if len(base) != 2 or base[1] != str(SOURCE/'vendor/cancel_seed_transport.py'):
        raise ValueError('unexpected transport base')
    pinned(Path(base[1]), base[0])
    provider = ROOT/'docs/reports/kv-cache/kpf18-g3-current-lock-20261104'
    witness = pinned(provider/'current_lock.py', WITNESS_PIN)
    source_seal = pinned(provider/'provider-sources.json', PROVIDER_PIN)
    # Validate the reviewed source bytes; this map is not an authorization receipt.
    reviewed = json.loads(source_seal)
    for name, digest in reviewed.items():
        pinned(Path('/mnt/raid0/llm/epyc-orchestrator')/name, digest)
    custody = subprocess.run(['bash',str(CUSTODY/'launch.sh'),'custody-check'],capture_output=True,text=True)
    if custody.returncode:
        raise ValueError('predecessor custody refused: '+custody.stderr)
    validation_raw, validation_paths = validation_closure(R9_RECEIPT, R9_RECEIPT_PIN)
    rowflow = {name: pinned(ROOT/'scripts/coordination/rowflow'/name, digest)
               for name, digest in ROWFLOW_PINS.items()}
    output.mkdir()
    (output/'INCOMPLETE').write_text('Never dispatch runtime; preparation incomplete.\n')
    (output/'INDEPENDENT-R9-RESULT.json').write_bytes(validation_raw)
    runtime=output/'candidate';runtime.mkdir()
    for name, data in entries.items():
        target=runtime/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (runtime/'predecessor-launch.sh.disabled').write_bytes(launch)
    (runtime/'predecessor-SOURCES.sha256').write_bytes(raw)
    (runtime/'NATIVE-SOURCES.sha256').write_bytes(read_regular(CUSTODY/'NATIVE-SOURCES.sha256'))
    patch=read_regular(supervision/'cancel_seed_transport.patch')
    (output/'cancel_seed_transport.patch').write_bytes(patch)
    subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(output/'cancel_seed_transport.patch')],cwd=runtime,check=True,capture_output=True)
    (runtime/'vendor/socket_deadline.py').write_bytes(read_regular(supervision/'socket_deadline.py'))
    (runtime/'current_lock.py').write_bytes(witness)
    (runtime/'provider-sources.json').write_bytes(source_seal)
    (runtime/'lock_witness.py').write_text(ADAPTER)
    (runtime/'rowflow_entry.py').write_bytes(read_regular(HERE/'rowflow_entry.py'))
    for name, data in rowflow.items():
        (runtime/name).write_bytes(data)
    (runtime/'rowflow-command.json').write_text(json.dumps(rowflow_command(runtime), indent=2)+'\n')
    # Reviewable wiring only: none of these predicates may dispatch or complete a row.
    for name in ('rowflow-launch.sh', 'precondition.sh', 'complete.sh'):
        (runtime/name).write_text('#!/bin/bash\nset -euo pipefail\n'
                                 'echo "REFUSED: G3 rowflow runtime unqualified" >&2\nexit 78\n')
    (runtime/'publisher_smoke.py').write_bytes(read_regular(HERE/'publisher_smoke.py'))
    # Modify only the copied, pinned predecessor; retained NI bytes are immutable.
    admission=(runtime/'gpu_smoke_admission.py').read_text()
    for expected in ('import lock_witness', " if os.sched_getaffinity(0)!={184,185}:raise RuntimeError('GPU smoke requires host CPUs 184-185')", 'start>=now+300', 'if int(m.group(1))<=185 and int(m.group(2) or m.group(1))>=184:'):
        if admission.count(expected)!=1:raise ValueError('unexpected historical smoke admission')
    admission=admission.replace('import lock_witness', 'import lock_witness, publisher_smoke')
    admission=admission.replace(" if os.sched_getaffinity(0)!={184,185}:raise RuntimeError('GPU smoke requires host CPUs 184-185')",
                                ' cpus,deadline=publisher_smoke.context(Path(__file__).resolve().parent)')
    admission=admission.replace('start>=now+300', 'start>=deadline')
    admission=admission.replace("if int(m.group(1))<=185 and int(m.group(2) or m.group(1))>=184:",
                                "if cpus.intersection(range(int(m.group(1)),int(m.group(2) or m.group(1))+1)):")
    (runtime/'gpu_smoke_admission.py').write_text(admission)
    supervisor=(runtime/'supervisor.py').read_text()
    supervisor=supervisor.replace('import guard,owned_drain,lock_witness,gpu_smoke_admission,ram_admission',
                                  'import guard,owned_drain,lock_witness,gpu_smoke_admission,ram_admission,publisher_smoke')
    old="  os.environ.update(KPF_SMOKE='1',FILLER_CPUS='184-185',FILLER_ID='kpf18-g3-diagnostic-smoke',FILLER_END=str(int(time.time())+300),FILLER_DEADLINE=str(int(time.time())+240),FILLER_STOPFILE=str(D/'STOP-smoke'))"
    if supervisor.count(old)!=1:raise ValueError('unexpected historical smoke setup')
    supervisor=supervisor.replace(old,"  publisher_smoke.context(D)\n  os.environ['KPF_SMOKE']='1'")
    if supervisor.count("cpus='184-191' if mode=='official' else '184-185'")!=1:raise ValueError('unexpected historical smoke CPU dispatch')
    supervisor=supervisor.replace("cpus='184-191' if mode=='official' else '184-185'", "cpus='184-191' if mode=='official' else os.environ['FILLER_CPUS']")
    (runtime/'supervisor.py').write_text(supervisor)
    guard=(runtime/'guard.py').read_text().replace("ID='kpf18-g3-diagnostic-v1-20261029'",'ID='+repr(ROW))
    guard=guard.replace('def boundary():\n','def boundary():\n    import lock_witness\n    lock_witness.boundary()\n')
    # Keep the independently integrated smoke branch, replace retired normal parsing.
    start=guard.index("    if list(flags.glob('HOLD_*'))", guard.index('def boundary():'))
    end=guard.index('\nclass ContextBoundary:', start)
    guard=guard[:start]+'''    import rowflow_entry
    return rowflow_entry.boundary()
''' + guard[end:]
    (runtime/'guard.py').write_text(guard)
    # Runtime launcher has its own unconditional barrier; no historical dispatch tail.
    (runtime/'launch.sh').write_text('#!/bin/bash\nset -euo pipefail\necho "REFUSED: G3 runtime remains unqualified" >&2\nexit 78\n')
    names=sorted(str(p.relative_to(runtime)) for p in runtime.rglob('*') if p.is_file())
    (runtime/'SOURCES.sha256').write_text(''.join(f'{sha(read_regular(runtime/n))}  {n}\n' for n in names))
    receipt={'status':'PROVIDER_TRANSPORT_PREPARATION_NOT_READY','row_id':ROW,'runtime_dispatch':False,
             'predecessor_runtime_manifest_sha256':RUNTIME_PIN,'provider_sources_sha256':PROVIDER_PIN,
             'independent_r9_receipt_sha256':R9_RECEIPT_PIN,
             'independent_r9_custody':'verified 29+14+22; custody only, no R9 test rerun',
             'scope':'disabled current-rowflow command and lifecycle integration; no enrollment or live provider witness',
             'rowflow_engine_pins':ROWFLOW_PINS,
             'rowflow_entry':'candidate/rowflow-launch.sh always rc78; command is review-only JSON',
             'outstanding':['official rowflow enrollment and qualification of entry/completion predicates',
                            '214 GiB disk admission',
                            'native cancellation/task release qualification','whole-attempt cleanup/overshoot qualification',
                            'remaining historical launcher/config paths and grant semantics','own-process KFD/VRAM residency and actual GPU binding (retained supervisor uses card2)',
                            'four-CPU publisher smoke runtime qualification (source integration only)',
                            'GPU qualification']}
    (output/'PREPARATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    # Complete source inventory includes copied runtime, provider, patch and external native inventory.
    external=json.loads(read_regular(CUSTODY/'expected-paths.json'))
    paths=sorted(set([str(p) for p in output.rglob('*') if p.is_file() and p.name!='INCOMPLETE']+external+validation_paths))
    seals=''.join(f'{sha(read_regular(p))}  {p}\n' for p in paths)
    (output/'ALL-SOURCES.sha256').write_text(seals)
    (output/'expected-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
    for name in ('verify_manifest.py','rebind_manifest.py'):
        (output/name).write_bytes(read_regular(TOOLS/name))
    bootstrap_names=['ALL-SOURCES.sha256','expected-paths.json','verify_manifest.py','rebind_manifest.py']
    bootstrap=''.join(f'{sha(read_regular(output/n))}  {n}\n' for n in bootstrap_names)
    (output/'BOOTSTRAP.sha256').write_text(bootstrap)
    entry='''#!/bin/bash
set -euo pipefail
D=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ ! -e "$D/INCOMPLETE" ]] || exit 78
printf '%s  %s\\n' BOOT "$D/BOOTSTRAP.sha256" | sha256sum --status -c -
(cd "$D" && sha256sum --quiet -c BOOTSTRAP.sha256)
python3 -B -I -c 'import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=[sys.argv[1]+"/verify_manifest.py",sys.argv[1]+"/ALL-SOURCES.sha256",sys.argv[1]+"/expected-paths.json",sys.argv[2]];runpy.run_path(sys.argv[0],run_name="__main__")' "$D" ALLPIN
case "${1:-official}" in
 custody-check) [[ $# == 1 ]] || exit 64;;
 *) echo 'REFUSED: provider/transport preparation only; runtime unqualified' >&2; exit 78;;
esac
'''.replace('BOOT',sha(bootstrap.encode()),1).replace('ALLPIN',sha(seals.encode()))
    (output/'launch.sh').write_text(entry)
    (output/'INCOMPLETE').unlink()
    verify(output/'ALL-SOURCES.sha256',paths,sha(seals.encode()))
    return receipt


if __name__=='__main__':
    print(json.dumps(prepare(sys.argv[1]),indent=2))
