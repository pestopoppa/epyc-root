#!/usr/bin/env python3
"""Keeper-owned, one-use pre-grant qualification for the canonical filler engine.

The manifest fixes qualification.receipt before the nonce is issued. Workers may
prepare fixtures, but only the keeper's nonce store can make a receipt valid.
No test fixture is a production qualification: production=True requires the
real first request proof from the normal job entry in the actual namespace.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time

# -I intentionally drops the script directory. This directory is the pinned,
# keeper-installed bundle containing dryrun_check.py, not a worker PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parent))

KIND = 'epyc.qual.pass.v1'
FIXTURE_KIND = 'epyc.qual.fixture.v1'
ROOT = Path('/mnt/raid0/llm/tmp/compute-flags')
POLICY = Path(__file__).with_name('dryrun_disk_policy.json')
ALLOWLIST = ROOT / 'engine-allowlist.json'
GIB = 1024 ** 3
VOLATILE = {'keeper_log', 'hold'}

class Refused(Exception):
    pass

def need(ok: object, why: str) -> None:
    if not ok: raise Refused(why)

def sha(path: Path) -> str:
    need(path.is_file() and not path.is_symlink(), f'missing or symlink: {path}')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def jbytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def digest(value: object) -> str:
    return hashlib.sha256(jbytes(value)).hexdigest()

def manifest_digest(m: dict) -> str:
    return digest({k: v for k, v in m.items() if k not in VOLATILE})

def load_manifest(path: Path) -> dict:
    need(path.is_file() and not path.is_symlink(), 'manifest missing or symlink')
    m = json.loads(path.read_text())
    need(isinstance(m, dict) and m.get('schema') == 'epyc.ready.v2', 'manifest schema != epyc.ready.v2')
    need(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]+', str(m.get('id', ''))), 'bad id')
    need(isinstance(m.get('owner'), str) and m['owner'] and isinstance(m.get('regions'), str) and m['regions'],
         'owner/regions missing')
    need(type(m.get('gib')) in (int,float) and math.isfinite(m['gib']) and m['gib'] > 0, 'gib malformed')
    scratch = Path(str(m.get('scratch_root','')))
    need(scratch.is_absolute() and str(scratch).startswith('/mnt/raid0/llm/tmp/') and
         scratch.name not in ('compute-flags','disk-audit-20261028'), 'scratch_root invalid')
    for key in ('launcher', 'engine', 'job', 'qual_fixture'):
        v = m.get(key)
        need(isinstance(v, dict) and isinstance(v.get('path'), str) and re.fullmatch('[0-9a-f]{64}', str(v.get('sha256'))), f'{key} path/sha missing')
        need(Path(v['path']).is_absolute(), f'{key} path not absolute')
    need(type(m['qual_fixture'].get('items')) is int and m['qual_fixture']['items'] >= 2,
         'qual_fixture needs normal and cutoff items')
    kind=m.get('workload_kind')
    need(kind in ('llm','speech','command') or (m.get('production') is False and kind is None),
         'unsupported workload_kind; expected llm, speech, or command')
    if kind is None:kind='llm'  # isolated pre-production fixture compatibility
    if m.get('production') is True:
        recipe=m.get('production_recipe')
        need(isinstance(recipe,dict) and isinstance(recipe.get('path'),str) and Path(recipe['path']).is_absolute() and
             re.fullmatch('[0-9a-f]{64}',str(recipe.get('sha256',''))), 'production_recipe pin missing')
    for key in ('source_manifest', 'requires_tools', 'ports', 'shared_state'):
        need(key in m, f'{key} absent')
    need(re.fullmatch('[0-9a-f]{64}', str(m.get('request_manifest_sha256',''))),
         'request_manifest_sha256 missing')
    need(isinstance(m['requires_tools'], list) and all(isinstance(x, str) and x for x in m['requires_tools']), 'requires_tools malformed')
    need(isinstance(m['ports'], list) and all(type(x) is int and 1 <= x <= 65535 for x in m['ports']), 'ports malformed')
    need(len(set(m['ports'])) == len(m['ports']), 'duplicate port')
    need(isinstance(m['shared_state'], list) and all(isinstance(x, str) and x for x in m['shared_state']), 'shared_state malformed')
    need(m.get('exclusive_class') is None or isinstance(m['exclusive_class'], str), 'exclusive_class malformed')
    for key in ('window_s', 'min_window_s', 'items'):
        need(type(m.get(key)) is int and m[key] > 0, f'{key} must be positive integer')
    need(m['window_s'] % 60 == 0 and m['min_window_s'] % 60 == 0 and m['window_s'] >= m['min_window_s'] + 300, 'window/minimum malformed')
    if kind=='llm':
        llm_keys=['n_ctx_required','per_slot_n_ctx_required','n_parallel_required','prompt_tokens_required']
        if m.get('rate_basis',{}).get('scope')!='calibrated-work-unit':llm_keys.append('tokens_per_item')
        for key in llm_keys:
            need(type(m.get(key)) is int and m[key]>0, f'{key} must be positive integer for llm')
        mode=m.get('kv_cache_mode')
        need(mode in ('split','unified'), 'LLM kv_cache_mode must be split or unified')
        need(m['n_ctx_required'] >= (m['per_slot_n_ctx_required'] * m['n_parallel_required'] if mode=='split' else m['per_slot_n_ctx_required']) and
             m['prompt_tokens_required'] <= m['per_slot_n_ctx_required'], 'context/parallel/prompt declaration inconsistent')
    elif kind=='speech':
        need(not any(k in m for k in ('kv_cache_mode','tokens_per_item','n_ctx_required','per_slot_n_ctx_required','n_parallel_required','prompt_tokens_required')),
             'speech must not invent LLM token/context fields')
        s=m.get('speech')
        need(isinstance(s,dict),'speech declaration missing')
        for name in ('fixture_audio','source_catalog','source_binary'):
            item=s.get(name)
            need(isinstance(item,dict) and isinstance(item.get('path'),str) and Path(item['path']).is_absolute() and
                 re.fullmatch('[0-9a-f]{64}',str(item.get('sha256',''))),f'speech {name} pin missing')
        need(re.fullmatch('[0-9a-f]{64}',str(s.get('pcm_sha256',''))),'speech PCM SHA missing')
        for name in ('fixture_audio_seconds','planned_audio_seconds'):
            need(type(s.get(name)) in (int,float) and math.isfinite(s[name]) and s[name]>0,f'speech {name} invalid')
        for name in ('sample_rate_hz','batch_size','threads'):
            need(type(s.get(name)) is int and s[name]>0,f'speech {name} invalid')
        need(isinstance(s.get('decode_mode'),str) and s['decode_mode'] and
             (s.get('right_context')=='UNKNOWN' or type(s.get('right_context')) is int and s['right_context']>=0),
             'speech decode_mode/right_context missing; explicit UNKNOWN allowed')
    else:
        need(not any(k in m for k in ('kv_cache_mode','tokens_per_item','n_ctx_required','per_slot_n_ctx_required','n_parallel_required','prompt_tokens_required','speech')),
             'command must not invent LLM or speech fields')
        c=m.get('command')
        need(isinstance(c,dict) and isinstance(c.get('work_unit'),str) and c['work_unit'] and
             type(c.get('planned_work_units')) in (int,float) and math.isfinite(c['planned_work_units']) and c['planned_work_units']>0,
             'command work_unit/planned_work_units missing')
    need(m.get('qual_timeout_s',300) in (300,600), 'qual_timeout_s must be 300 or 600')
    for key in ('est_output_GiB', 'job_floor_gib'):
        v = m.get(key)
        need(type(v) in (int, float) and math.isfinite(v) and v >= 0, f'{key} malformed')
    need(m['job_floor_gib'] == 150, 'job floor differs from canonical 150 GiB')
    basis = m.get('rate_basis')
    allowed={'llm':('qualification-same-recipe','calibrated-production','calibrated-work-unit'),
             'speech':('speech-calibrated-production',),
             'command':('command-same-recipe','command-calibrated-production')}
    need(isinstance(basis, dict) and basis.get('scope') in allowed[kind] and
         type(basis.get('production_threads')) is int and basis['production_threads'] > 0, 'rate_basis missing')
    if basis['scope'] in ('qualification-same-recipe','command-same-recipe'):
        need(basis['production_threads'] == 2, 'two-SMT qualification rate cannot forecast a different production thread count')
    else:
        field=('wall_s_per_unit' if basis['scope']=='calibrated-work-unit' else
               {'llm':'rate_tok_s','speech':'rtf','command':'work_units_per_s'}[kind])
        need(type(basis.get(field)) in (int,float) and math.isfinite(basis[field]) and basis[field] > 0,
             f'calibrated production {field} missing')
        evidence = basis.get('evidence')
        need(isinstance(evidence,dict) and isinstance(evidence.get('path'),str) and
             re.fullmatch('[0-9a-f]{64}', str(evidence.get('sha256'))), 'calibration evidence pin missing')
        if basis['scope']=='calibrated-work-unit':
            need(isinstance(basis.get('work_unit'),str) and basis['work_unit'], 'calibrated LLM work_unit missing')
    if kind=='speech':
        need(basis.get('batch_size')==m['speech']['batch_size'] and basis.get('decode_mode')==m['speech']['decode_mode'] and
             basis['production_threads']==m['speech']['threads'], 'speech calibration role/batch/threads mismatch')
    need(isinstance(m.get('qualification'), dict) and isinstance(m['qualification'].get('receipt'), str), 'predeclared qualification.receipt missing')
    receipt = Path(m['qualification']['receipt'])
    need(receipt.is_absolute() and receipt.parent == scratch / 'qualification' and
         receipt.name == 'QUAL-'+m['id']+'.json', 'qualification.receipt path must be predeclared QUAL-id.json')
    need(type(m.get('production')) is bool, 'production boolean missing')
    return m

def bound_files(m: dict) -> dict:
    out = {}
    kind=m.get('workload_kind','llm')
    if m['production']:
        recipe=m['production_recipe']
        need(sha(Path(recipe['path']))==recipe['sha256'],'production recipe changed')
        out['production_recipe_sha256']=recipe['sha256']
    for key in ('launcher', 'engine', 'job', 'qual_fixture'):
        p = Path(m[key]['path'])
        actual = sha(p)
        need(actual == m[key]['sha256'], f'{key} sha mismatch')
        out[key] = {'path': str(p), 'sha256': actual}
    source = Path(m['source_manifest'])
    need(source.is_absolute(), 'source_manifest path not absolute')
    from dryrun_check import checked_manifest, Refused as DryrunRefused
    try: out['source_manifest_sha256'] = checked_manifest(source)
    except DryrunRefused as exc: raise Refused(str(exc)) from exc
    out['policy_sha256'] = sha(POLICY)
    if kind=='speech':
        for key in ('fixture_audio','source_catalog','source_binary'):
            item=m['speech'][key]
            need(sha(Path(item['path']))==item['sha256'],f'speech {key} changed')
        out['speech_inputs_sha256']={key:m['speech'][key]['sha256'] for key in ('fixture_audio','source_catalog','source_binary')}
    if m['rate_basis']['scope'] in ('calibrated-production','calibrated-work-unit','speech-calibrated-production','command-calibrated-production'):
        evidence = m['rate_basis']['evidence']
        need(sha(Path(evidence['path'])) == evidence['sha256'], 'calibration evidence changed')
        observed = json.loads(Path(evidence['path']).read_text())
        field=('wall_s_per_unit' if m['rate_basis']['scope']=='calibrated-work-unit' else
               {'llm':'rate_tok_s','speech':'rtf','command':'work_units_per_s'}[kind])
        obs=('observed_wall_s_per_unit' if m['rate_basis']['scope']=='calibrated-work-unit' else
             {'llm':'measured_tok_s','speech':'observed_rtf','command':'observed_work_units_per_s'}[kind])
        need(observed.get(obs) == m['rate_basis'][field] and
             observed.get('production_threads') == m['rate_basis']['production_threads'] and
             observed.get('production_recipe_sha256')==m['production_recipe']['sha256'],
             'calibration evidence does not support declared rate/threads')
        if kind=='speech':
            need(observed.get('batch_size')==m['speech']['batch_size'] and
                 observed.get('decode_mode')==m['speech']['decode_mode'] and
                 observed.get('source_catalog_sha256')==m['speech']['source_catalog']['sha256'],
                 'speech calibration batch/decode/source mismatch')
        if kind=='command':
            need(observed.get('work_unit')==m['command']['work_unit'], 'command calibration unit mismatch')
        if m['rate_basis']['scope']=='calibrated-work-unit':
            need(observed.get('work_unit')==m['rate_basis']['work_unit'],'LLM calibration work unit mismatch')
        out['rate_evidence_sha256'] = evidence['sha256']
    out['helper_sha256'] = {name: sha(Path(__file__).with_name(name)) for name in
                            ('qualify_launcher.py', 'keeper_qual_gate.py', 'dryrun_check.py', 'filler_lib.sh', 'ready_manifest.schema.json')}
    allow = json.loads(ALLOWLIST.read_text())
    need(allow.get('kind') == 'epyc.engine-allowlist.v1' and
         allow.get('engine') == out['engine'], 'engine path/sha not canonical allowlist entry')
    return out

def row_binding(m: dict, flags: Path) -> None:
    from dryrun_check import row_record, Refused as DryrunRefused
    try: row = row_record(flags/'FILLERS.md', m['id'])
    except DryrunRefused as exc: raise Refused(str(exc)) from exc
    notes = row['notes']
    need(str(m.get('claimed_cpus','')) == notes['claimed_cpus'].strip(), 'manifest/row claimed_cpus differ')
    need(row['requested'] == m['window_s'] and row['estimate'] == m['est_output_GiB'] and
         str(row['scratch']) == m['scratch_root'], 'manifest/row window/output/scratch differ')

def local_namespace(m: dict) -> dict:
    tools = {}
    for name in m['requires_tools']:
        path = name if name.startswith('/') else shutil.which(name)
        need(path and Path(path).exists(), f'tool missing: {name}')
        tools[name] = str(Path(path).resolve())
    interpreter = Path(m.get('qual_interpreter') or sys.executable).resolve()
    need(interpreter.is_file(), f'interpreter missing: {interpreter}')
    env = {k: os.environ.get(k, '') for k in ('PATH', 'HOME', 'LD_LIBRARY_PATH', 'VIRTUAL_ENV')}
    return {'root_inode': os.stat('/').st_ino, 'kernel': os.uname().release,
            'cwd': os.getcwd(), 'cwd_exists': Path.cwd().is_dir(),
            'interpreter': {'path': str(interpreter.resolve()), 'sha256': sha(interpreter),
                            'version': subprocess.check_output([str(interpreter), '--version'], stderr=subprocess.STDOUT, text=True).strip()},
            'tools': tools, 'env_fingerprint_sha256': digest(env)}

def launcher_namespace(manifest: Path, m: dict, env: dict, timeout: int = 30) -> dict:
    e = dict(env, WS58_FINGERPRINT_ONLY='1')
    need(ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0, 'subreaper setup failed')
    p = subprocess.Popen(['setsid', 'bash', m['launcher']['path']], cwd=str(ROOT), env=e,
                         text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    birth=group_birth(p.pid)
    try: output, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_group(p.pid,birth)
        drain_children()
        p.communicate(timeout=8)
        raise Refused('fingerprint launcher timed out and was drained')
    stop_group(p.pid,birth)
    drain_children()
    need(p.returncode == 0, f'fingerprint launcher rc={p.returncode}: {output[-240:]}')
    lines = [s.removeprefix('EPYC_NAMESPACE_JSON=') for s in output.splitlines() if s.startswith('EPYC_NAMESPACE_JSON=')]
    need(len(lines) == 1, 'fingerprint marker missing/duplicated')
    obj = json.loads(lines[0])
    need(obj.get('cwd_exists') is True, 'cwd absent in exec namespace')
    return obj

def group_birth(pid: int) -> int:
    for _ in range(30):
        try:
            stat=Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split()
            if int(stat[2]) == pid: return int(stat[19])
        except (OSError,ValueError,IndexError): pass
        time.sleep(.01)
    raise Refused('captured launcher never became its own setsid group')

def group_members(pgid: int, birth: int, proc_root:Path=Path('/proc')) -> list[int]:
    leader=proc_root/str(pgid)/'stat'
    if leader.exists():
        try:now_birth=int(leader.read_text().rsplit(') ',1)[1].split()[19])
        except (OSError,ValueError,IndexError):raise Refused('captured group leader identity unreadable')
        need(now_birth==birth,'captured launcher group leader PID was reused')
    members=[]
    for proc in proc_root.iterdir():
        if not proc.name.isdecimal():continue
        try:
            stat=proc.joinpath('stat').read_text().rsplit(') ',1)[1].split()
            if int(stat[2]) != pgid or stat[0] in ('Z','X','x'):continue
            need(proc.stat().st_uid == os.getuid() and int(stat[19]) >= birth,
                 'captured process group identity changed')
            members.append(int(proc.name))
        except (FileNotFoundError,ProcessLookupError,PermissionError,ValueError,IndexError):continue
    return members

def stop_group(pid: int, birth: int | None = None) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if birth is not None and not group_members(pid,birth):return
        try: os.killpg(pid, sig)
        except ProcessLookupError: return
        for _ in range(20):
            time.sleep(.1)
            if birth is not None:
                if not group_members(pid,birth):return
            else:
                try: os.killpg(pid, 0)
                except ProcessLookupError:return
    if birth is not None:need(not group_members(pid,birth),'captured launcher group survived TERM/KILL')

def pidfile_entry_state(pid:int,birth:int,proc_root:Path=Path('/proc')) -> str:
    """Never signal a PID that no longer has its captured birth identity."""
    entry=proc_root/str(pid)
    try:
        stat=entry.joinpath('stat').read_text().rsplit(') ',1)[1].split()
        actual=int(stat[19]);uid=entry.stat().st_uid
    except (FileNotFoundError,ProcessLookupError):return 'gone'
    except (OSError,ValueError,IndexError):raise Refused(f'PID {pid} identity unreadable')
    need(uid==os.getuid(),'registered PID owner changed')
    return 'live' if actual==birth and stat[0] not in ('Z','X','x') else 'gone' if actual==birth else 'reused'

def pidfile_drain(path:Path,ports:str) -> None:
    if not path.exists():return
    targets=[]
    for line in path.read_text().splitlines():
        if not line.strip():continue
        match=re.fullmatch(r'(\d+) (\d+)',line.strip())
        need(match,'PIDFILE requires pid birth_ticks pairs')
        pid,birth=map(int,match.groups())
        need(pid>1 and birth>0,'PIDFILE identity invalid')
        state=pidfile_entry_state(pid,birth)
        need(state!='reused',f'registered PID {pid} was reused; not signalling')
        if state=='live':
            if ports:
                argv=(Path('/proc')/str(pid)/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
                need(any(f'--port {port}' in argv for port in ports.split(',')),
                     f'registered PID {pid} no longer has declared port')
            targets.append((pid,birth))
    for sig in (signal.SIGTERM,signal.SIGKILL):
        for pid,birth in targets:
            state=pidfile_entry_state(pid,birth)
            need(state!='reused',f'PID {pid} reused during drain; not signalling')
            if state=='live':
                try:os.kill(pid,sig)
                except ProcessLookupError:pass
        for _ in range(20):
            if all(pidfile_entry_state(pid,birth)=='gone' for pid,birth in targets):return
            time.sleep(.1)
    need(all(pidfile_entry_state(pid,birth)=='gone' for pid,birth in targets),
         'registered native child survived TERM/KILL')

def drain_children() -> None:
    child_file = Path(f'/proc/self/task/{os.getpid()}/children')
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for _ in range(4):
            children = [int(x) for x in child_file.read_text().split()]
            if not children: return
            for child in children:
                try: os.kill(child, sig)
                except ProcessLookupError: pass
            time.sleep(.25)
            for child in children:
                try: os.waitpid(child, os.WNOHANG)
                except ChildProcessError: pass
    need(not child_file.read_text().strip(), 'qualification left live/adopted children')

def store_path(flags: Path, nonce: str) -> Path:
    need(re.fullmatch(r'[0-9a-f]{64}', nonce), 'invalid nonce')
    return flags / 'qual-nonces' / (nonce + '.json')

def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, sort_keys=True, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def issue(manifest: Path, flags: Path) -> str:
    m = load_manifest(manifest); bound_files(m); row_binding(m, flags)
    if m['production']:
        # The production issuer must be a live v8 keeper descendant, not a
        # worker invoking this public CLI. Fixture tests remain isolated.
        try: keeper_pid = int((flags / 'ws58-calendar-keeper.pid').read_text().strip())
        except (OSError, ValueError): raise Refused('keeper PID certificate absent')
        pid = os.getppid(); ancestry = set()
        for _ in range(6):
            if pid <= 1: break
            ancestry.add(pid)
            stat = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
            pid = int(stat[1])
        need(keeper_pid in ancestry, 'nonce issue is not a keeper descendant')
        cmd = (Path(f'/proc/{keeper_pid}/cmdline').read_bytes().replace(b'\0', b' ')).decode(errors='replace')
        need('ws58-calendar-keeper-v8.sh' in cmd, 'issuer is not v8 keeper')
        for old in (flags/'qual-nonces').glob('*.json'):
            try:record=json.loads(old.read_text())
            except (OSError,ValueError):raise Refused('nonce store unreadable; refuse issuance')
            if record.get('id')==m['id']:
                raise Refused('qualification nonce already issued for id; use fresh id after failure')
    nonce = secrets.token_hex(32)
    p = store_path(flags, nonce)
    p.parent.mkdir(parents=True, exist_ok=True)
    marker=flags/'qual-nonces'/'by-id'/(m['id']+'.json')
    marker.parent.mkdir(parents=True,exist_ok=True)
    need(not marker.is_symlink(),'nonce ID marker symlink')
    try:marker_fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:raise Refused('qualification nonce already issued for id; use fresh id after failure')
    with os.fdopen(marker_fd,'w') as f:
        json.dump({'id':m['id'],'nonce':nonce,'manifest_sha256':manifest_digest(m)},f,sort_keys=True)
    state = {'kind': 'epyc.qual.nonce.v1', 'id': m['id'], 'manifest_sha256': manifest_digest(m),
             'receipt': m['qualification']['receipt'], 'state': 'issued', 'issued_at': time.time()}
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f: json.dump(state, f, sort_keys=True)
    return nonce

def read_state(manifest: Path, flags: Path, nonce: str, required: str) -> tuple[dict, dict]:
    m = load_manifest(manifest)
    if m['production']:
        marker=flags/'qual-nonces'/'by-id'/(m['id']+'.json')
        need(marker.is_file() and not marker.is_symlink(),'keeper nonce ID marker absent')
        claim=json.loads(marker.read_text())
        need(claim.get('id')==m['id'] and claim.get('nonce')==nonce and
             claim.get('manifest_sha256')==manifest_digest(m), 'keeper nonce ID marker mismatch')
    p = store_path(flags, nonce)
    need(p.is_file() and not p.is_symlink(), 'nonce not keeper-issued')
    state = json.loads(p.read_text())
    need(state.get('kind') == 'epyc.qual.nonce.v1' and state.get('id') == m['id'] and
         state.get('manifest_sha256') == manifest_digest(m) and
         state.get('receipt') == m['qualification']['receipt'] and state.get('state') == required,
         'nonce state/replay/mismatch')
    return m, state

def choose_cpus(m: dict) -> str:
    # Only a free physical pair may be passed by the keeper; this helper validates
    # its shape. The keeper's R11/R6 admission is the resource authority.
    pair = os.environ.get('WS58_QUAL_CPUS', '')
    from dryrun_check import cpus, Refused as DryrunRefused
    try: c = sorted(cpus(pair))
    except DryrunRefused as exc: raise Refused(str(exc)) from exc
    need(len(c) == 2 and all(0 <= x < 192 for x in c) and len({x % 96 for x in c}) == 2,
         'qualification needs two distinct admitted physical cores')
    claimed = str(m.get('claimed_cpus', ''))
    if str(m.get('regions', '')).startswith(('any-cpu-quarter', 'any-of')):
        need(claimed in ('', 'dynamic', 'any-cpu-quarter'), 'relocatable row has fixed claimed_cpus')
    return pair

def feasible_rate(m: dict, first: dict) -> float:
    kind=m.get('workload_kind','llm');scope=m['rate_basis']['scope']
    if kind=='llm':value=(first.get('measured_tok_s') if scope=='qualification-same-recipe' else
                          m['rate_basis']['wall_s_per_unit'] if scope=='calibrated-work-unit' else m['rate_basis']['rate_tok_s'])
    elif kind=='speech':value=m['rate_basis']['rtf']
    else:value=first.get('measured_work_units_per_s') if scope=='command-same-recipe' else m['rate_basis']['work_units_per_s']
    need(type(value) in (int,float) and math.isfinite(value) and value > 0, 'production feasibility rate missing')
    return float(value)

def feasible_window(m: dict, rate: float) -> bool:
    kind=m.get('workload_kind','llm')
    if kind=='llm':needed=m['items']*rate if m['rate_basis']['scope']=='calibrated-work-unit' else m['items']*m['tokens_per_item']/rate
    elif kind=='speech':needed=m['speech']['planned_audio_seconds']*rate  # RTF = wall_s/audio_s
    else:needed=m['command']['planned_work_units']/rate
    return needed<=m['window_s']

def feasibility_record(m:dict,rate:float)->dict:
    kind=m.get('workload_kind','llm')
    obj={'rate_scope':m['rate_basis']['scope'],'production_threads':m['rate_basis']['production_threads']}
    if kind=='llm':
        if m['rate_basis']['scope']=='calibrated-work-unit':obj.update(wall_s_per_unit=rate,work_unit=m['rate_basis']['work_unit'])
        else:obj['rate_tok_s']=rate
    elif kind=='speech':obj.update(rtf=rate,unit='wall_s/audio_s',batch_size=m['speech']['batch_size'],decode_mode=m['speech']['decode_mode'])
    else:obj.update(work_units_per_s=rate,work_unit=m['command']['work_unit'])
    return obj

def gpu_claim_ancestor(row_id: str) -> dict:
    """Observe the native region-lock parent holding this exact qual tag."""
    pid = os.getppid()
    for _ in range(8):
        if pid <= 1: break
        proc = Path(f'/proc/{pid}')
        args = proc.joinpath('cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        stat = proc.joinpath('stat').read_text().rsplit(') ', 1)[1].split()
        if ('src.runtime.region_lock_cli' in args and '--gpu-quiet exclusive' in args and
                '--tag qual-'+row_id in args):
            return {'pid':pid,'birth_ticks':int(stat[19]),'argv_sha256':hashlib.sha256(args.encode()).hexdigest()}
        pid = int(stat[1])
    raise Refused('exclusive GPU region-lock ancestor/tag absent')

def first_request_ok(m: dict, first: dict) -> bool:
    if not isinstance(first, dict) or first.get('ok') is not True: return False
    if m['production'] and first.get('production_recipe_sha256')!=m['production_recipe']['sha256']:return False
    kind=m.get('workload_kind','llm')
    if (kind=='llm' and m.get('rate_basis',{}).get('scope')=='calibrated-work-unit' and
        first.get('work_unit')!=m['rate_basis']['work_unit']):return False
    if kind=='speech':
        s=m['speech']
        return (first.get('scope')=='TARGET_NATIVE_SPEECH' and
                first.get('manifest_sha256')==m['request_manifest_sha256'] and
                first.get('input_sha256')==s['fixture_audio']['sha256'] and
                first.get('pcm_sha256')==s['pcm_sha256'] and
                first.get('source_binary_sha256')==s['source_binary']['sha256'] and
                type(first.get('audio_duration_s')) in (int,float) and first['audio_duration_s']==s['fixture_audio_seconds'] and
                first.get('sample_rate')==s['sample_rate_hz'] and
                first.get('decode_mode')==s['decode_mode'] and first.get('right_context')==s['right_context'] and
                first.get('batch')==s['batch_size'] and first.get('threads')==2 and
                type(first.get('wall_s')) in (int,float) and first['wall_s']>0)
    if kind=='command':
        c=m['command']
        return (first.get('scope')=='COMMAND_NATIVE' and
                first.get('manifest_sha256')==m['request_manifest_sha256'] and
                first.get('work_unit')==c['work_unit'] and
                type(first.get('work_completed')) in (int,float) and first['work_completed']>0 and
                type(first.get('wall_s')) in (int,float) and first['wall_s']>0 and
                type(first.get('measured_work_units_per_s')) in (int,float) and
                first['measured_work_units_per_s']==first['work_completed']/first['wall_s'])
    total = first.get('n_ctx_total')
    per_slot = first.get('n_ctx_per_slot')
    parallel = first.get('total_slots')
    if not m['production']:
        total = total if type(total) is int else first.get('n_ctx')
        per_slot = per_slot if type(per_slot) is int else first.get('n_ctx')
        parallel = parallel if type(parallel) is int else first.get('n_parallel', 1)
    return ((not m['production'] or (first.get('scope')=='TARGET_SCRATCH_SERVER' and
            first.get('manifest_sha256') == m['request_manifest_sha256'])) and
            (not m['production'] or first.get('kv_cache_mode')==m['kv_cache_mode']) and
            type(total) is int and total >= m['n_ctx_required'] and
            type(per_slot) is int and per_slot >= m['per_slot_n_ctx_required'] and
            type(parallel) is int and parallel >= m['n_parallel_required'] and
            type(first.get('prompt_tokens')) is int and first['prompt_tokens'] == m['prompt_tokens_required'])

def make_grant(path: Path, m: dict, pair: str) -> None:
    now = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0) - dt.timedelta(minutes=1)
    end = now + dt.timedelta(seconds=m['window_s'])
    need(end > dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=m['min_window_s'] + 60), 'qualification synthetic window too short')
    path.write_text(f"regions={pair} start={now:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n")

def run(manifest: Path, flags: Path, nonce: str, timeout: int) -> dict:
    m, state = read_state(manifest, flags, nonce, 'issued')
    files = bound_files(m)
    row_binding(m, flags)
    pair = choose_cpus(m)
    gpu_qual = 'mi210_0' in str(m.get('regions', ''))
    need(os.environ.get('WS58_QUAL_GPU_HELD') == ('1' if gpu_qual else '0'), 'region-lock qualification claim marker absent')
    gpu_claim = gpu_claim_ancestor(m['id']) if gpu_qual else None
    receipt = Path(m['qualification']['receipt'])
    need(not receipt.exists(), 'receipt already exists; nonce replay')
    qdir = flags / 'qual' / nonce
    need(not qdir.exists(), 'qualification directory already exists')
    (qdir / 'grants').mkdir(parents=True)
    (qdir / 'results').mkdir()
    (qdir / 'state').mkdir()
    make_grant(qdir / 'grants' / (m['id'] + '.grant'), m, pair)
    env = dict(os.environ, WS58_QUAL='1', WS58_QUAL_NONCE=nonce,
               WS58_QUAL_CPUS=pair, WS58_QUAL_RESULTS=str(qdir / 'results'),
               WS58_QUAL_FIXTURE=m['qual_fixture']['path'], WS58_QUAL_PROOF=str(qdir / 'proof.json'),
               WS58_MANIFEST_PATH=str(manifest), WS58_QUALIFIER_PATH=str(Path(__file__)),
               FILLER_GRANTS_DIR=str(qdir / 'grants'), FILLER_STATE_DIR=str(qdir / 'state'), WS58_REGIONS=pair,
               WS58_QUAL_GPU_HELD='1' if gpu_qual else '0',
               WS58_QUAL_PRODUCTION='1' if m['production'] else '0',
               WS58_QUAL_WINDOW_S=str(m['window_s']),
               WS58_PRODUCTION_RECIPE_SHA256=m['production_recipe']['sha256'] if m['production'] else '')
    # The launcher must forward these through any env -i/chroot. A dropped var
    # causes refusal, never an unqualified real grant.
    namespace = launcher_namespace(manifest, m, env)
    # Adopt orphaned job children so a successful launcher cannot hide a live
    # server. Only descendants of this qualifier process are ever signalled.
    need(ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0, 'subreaper setup failed')
    with (qdir / 'launcher.out').open('w') as out:
        p = subprocess.Popen(['setsid', 'bash', m['launcher']['path']], cwd=str(ROOT), env=env,
                             stdout=out, stderr=subprocess.STDOUT)
        birth = group_birth(p.pid)
        try: rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_group(p.pid,birth)
            try: p.wait(timeout=8)
            except subprocess.TimeoutExpired: pass
            drain_children()
            raise Refused('qualification timeout; captured process group drained')
    stop_group(p.pid,birth)
    drain_children()
    need(rc == 0, f'qualification launcher rc={rc}; see {qdir / "launcher.out"}')
    if gpu_qual:
        need(gpu_claim_ancestor(m['id']) == gpu_claim, 'exclusive GPU claim lost during qualification')
    partial = qdir / 'receipt-partial.json'
    need(partial.is_file() and not partial.is_symlink(), 'engine partial receipt missing')
    proof = json.loads(partial.read_text())
    need(proof.get('kind') == 'epyc.qual.engine.v1' and proof.get('nonce') == nonce and proof.get('id') == m['id'], 'engine partial identity mismatch')
    need(proof.get('admission', {}).get('rc') == 0, 'admission did not pass')
    need(proof.get('completion', {}).get('complete_cmd_present') is True and proof.get('completion', {}).get('is_complete_rc') == 0, 'fixture completion predicate did not pass')
    need(proof.get('rc75', {}).get('exit_code') == 75 and proof.get('rc75', {}).get('partial_flag') is True, 'forced deadline did not exit 75/partial')
    first = proof.get('first_request', {})
    need(first_request_ok(m, first), 'native first request/compute does not match declared workload')
    rate = feasible_rate(m, first)
    need(feasible_window(m,rate), 'fixture rate makes declared work infeasible in window')
    writer = proof.get('result_writer', {})
    result = Path(str(writer.get('result_path', '')))
    need(writer.get('ok') is True and result.is_file() and result.resolve().is_relative_to((qdir / 'results').resolve()) and writer.get('sha256') == sha(result), 'fixture result writer proof invalid')
    need(proof.get('children_drained') is True, 'qualification children not drained')
    policy_floor = json.loads(POLICY.read_text())['normal_floor_gib']
    need(proof.get('disk', {}).get('job_floor_gib') == policy_floor == m['job_floor_gib'], 'disk floor mismatch')
    data = {'kind': KIND if m['production'] else FIXTURE_KIND, 'id': m['id'], 'nonce': nonce,
            'ran_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'ran_by': 'ws58-calendar-keeper', 'manifest_sha256': manifest_digest(m),
            'launcher_path': files['launcher']['path'], 'launcher_sha256': files['launcher']['sha256'],
            'engine_path': files['engine']['path'], 'engine_sha256': files['engine']['sha256'],
            'job_path': files['job']['path'], 'job_sha256': files['job']['sha256'],
            'fixture_path': files['qual_fixture']['path'], 'fixture_sha256': files['qual_fixture']['sha256'],
            'source_manifest_sha256': files['source_manifest_sha256'], 'policy_sha256': files['policy_sha256'],
            'helper_sha256': files['helper_sha256'], 'speech_inputs_sha256':files.get('speech_inputs_sha256'),
            'production_recipe_sha256':files.get('production_recipe_sha256'),
            'rate_evidence_sha256': files.get('rate_evidence_sha256'),
            'feasibility': feasibility_record(m,rate),
            'evidence_sha256': {'proof-normal.json': sha(qdir / 'proof-normal.json'),
                                'proof-cutoff.json': sha(qdir / 'proof-cutoff.json'),
                                'receipt-partial.json': sha(partial),
                                **({'cutoff-event.json':sha(qdir/'cutoff-event.json'),
                                    'cutoff-observed.json':sha(qdir/'cutoff-observed.json')} if m['production'] else {})},
            'exec_namespace': namespace, **{k: proof[k] for k in ('admission', 'first_request', 'result_writer', 'completion', 'rc75', 'disk', 'children_drained')},
            'cutoff_observation':proof.get('cutoff_observation'),
            'resource_claim': {'cpus': pair, 'gpu_quiet_exclusive': gpu_qual, 'region_lock_tag': 'qual-'+m['id'],
                               'gpu_claim_ancestor': gpu_claim},
            'launcher_group': {'pgid':p.pid,'birth_ticks':birth,'drained':True},
            'ports': m['ports'], 'exclusive_class': m['exclusive_class'], 'shared_state': m['shared_state']}
    data['receipt_sha256_excluding_self'] = digest(data)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f: json.dump(data, f, sort_keys=True, indent=2); f.write('\n')
    state['state'] = 'passed'; state['receipt_sha256'] = sha(receipt); state['passed_at'] = time.time()
    atomic_json(store_path(flags, nonce), state)
    return data

def verify(manifest: Path, flags: Path, fingerprint_now: bool = True) -> dict:
    m = load_manifest(manifest)
    need(m['production'] is True, 'fixture receipts cannot qualify production grants')
    receipt = Path(m['qualification']['receipt'])
    need(receipt.is_file() and not receipt.is_symlink(), 'qualification receipt absent')
    p = json.loads(receipt.read_text())
    need(p.get('kind') == KIND and p.get('id') == m['id'] and p.get('manifest_sha256') == manifest_digest(m), 'receipt manifest/id mismatch')
    need(p.get('receipt_sha256_excluding_self') == digest({k:v for k,v in p.items() if k != 'receipt_sha256_excluding_self'}), 'receipt edited')
    nonce = str(p.get('nonce', ''))
    _, state = read_state(manifest, flags, nonce, 'passed')
    need(state.get('receipt_sha256') == sha(receipt), 'receipt nonce-store sha mismatch')
    age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(p['ran_at'].replace('Z', '+00:00'))
    need(dt.timedelta() <= age <= dt.timedelta(hours=24), 'receipt older than 24 h')
    files = bound_files(m)
    row_binding(m, flags)
    for key in ('launcher', 'engine', 'job'):
        need(p.get(key+'_path') == files[key]['path'] and p.get(key+'_sha256') == files[key]['sha256'], key+' changed')
    need(p.get('fixture_path') == files['qual_fixture']['path'] and p.get('fixture_sha256') == files['qual_fixture']['sha256'], 'fixture changed')
    need(p.get('source_manifest_sha256') == files['source_manifest_sha256'] and p.get('policy_sha256') == files['policy_sha256'] and
         p.get('helper_sha256') == files['helper_sha256'] and p.get('rate_evidence_sha256') == files.get('rate_evidence_sha256') and
         p.get('speech_inputs_sha256')==files.get('speech_inputs_sha256') and
         p.get('production_recipe_sha256')==files.get('production_recipe_sha256'),
         'source/policy/helper/calibration changed')
    evidence = p.get('evidence_sha256', {})
    qdir = flags / 'qual' / nonce
    proof_names=('proof-normal.json','proof-cutoff.json','receipt-partial.json','cutoff-event.json','cutoff-observed.json')
    need(all(evidence.get(name) == sha(qdir / name) for name in proof_names),
         'qualification evidence changed')
    result = Path(str(p.get('result_writer', {}).get('result_path', '')))
    need(result.resolve().is_relative_to((qdir/'results').resolve()) and
         p['result_writer'].get('sha256') == sha(result), 'qualification result changed')
    need(p.get('admission', {}).get('rc') == 0 and p.get('completion', {}).get('is_complete_rc') == 0 and p.get('completion', {}).get('complete_cmd_present') is True, 'admission/completion proof absent')
    need(p.get('resource_claim', {}).get('gpu_quiet_exclusive') is ('mi210_0' in str(m.get('regions', ''))) and
         p.get('resource_claim', {}).get('region_lock_tag') == 'qual-'+m['id'], 'qualification claim mismatch')
    if 'mi210_0' in str(m.get('regions', '')):
        need(type(p['resource_claim'].get('gpu_claim_ancestor')) is dict and
             type(p['resource_claim']['gpu_claim_ancestor'].get('birth_ticks')) is int,
             'GPU claim ancestry evidence absent')
    need(p.get('rc75', {}).get('exit_code') == 75 and p.get('rc75', {}).get('partial_flag') is True, 'deadline proof absent')
    need(first_request_ok(m, p.get('first_request', {})), 'first request/context/parallel/prompt proof absent')
    need(p.get('cutoff_observation',{}).get('native_child_drained') is True and
         p['cutoff_observation'].get('native_first_event') is True,
         'active native cutoff child/drain proof absent')
    need(p.get('disk', {}).get('job_floor_gib') == p.get('disk', {}).get('policy_floor_gib') == m['job_floor_gib'], 'disk policy mismatch')
    need(p.get('children_drained') is True, 'children not drained')
    group=p.get('launcher_group',{})
    need(type(group.get('pgid')) is int and type(group.get('birth_ticks')) is int and
         group.get('drained') is True, 'captured launcher group drain proof absent')
    rate = feasible_rate(m, p['first_request'])
    need(p.get('feasibility') == feasibility_record(m,rate) and feasible_window(m,rate), 'feasibility failed')
    if fingerprint_now:
        env = dict(os.environ, WS58_MANIFEST_PATH=str(manifest), WS58_QUALIFIER_PATH=str(Path(__file__)))
        need(launcher_namespace(manifest, m, env) == p['exec_namespace'], 'exec namespace changed')
    return p

def disk_wait(manifest: Path, free_gib: float | None = None) -> bool:
    m = load_manifest(manifest)
    free = free_gib if free_gib is not None else os.statvfs(m['scratch_root']).f_bavail * os.statvfs(m['scratch_root']).f_frsize / GIB
    return free - m['est_output_GiB'] - 2 < m['job_floor_gib']

def disk_breach(manifest: Path) -> bool:
    m = load_manifest(manifest)
    fs = os.statvfs(m['scratch_root'])
    return fs.f_bavail * fs.f_frsize / GIB < m['job_floor_gib']

def placement_local(pair: str, engine_class: str, no_fold: int, claim: str) -> dict:
    """Mapping-only dry placement, without acquiring a quarter lock."""
    from dryrun_check import cpus, Refused as DryrunRefused
    try:
        actual = cpus(pair)
        wanted = cpus(claim) if claim else actual
    except DryrunRefused as exc: raise Refused(str(exc)) from exc
    need(len(actual) == 2 and len({x % 96 for x in actual}) == 2, 'synthetic placement needs two distinct cores')
    need(engine_class in ('cpu','gpu','cpu+gpu'), 'bad engine class')
    need(no_fold in (0,1), 'bad no-fold mode')
    if no_fold and engine_class == 'cpu' and all(x >= 96 for x in actual):
        raise Refused('SMT-only CPU list maps to no region under --no-fold-siblings')
    if claim and not (engine_class == 'gpu' and no_fold):
        need(wanted.issubset(actual), 'engine claim-cpus exceeds synthetic admitted pair')
    return {'cpus':sorted(actual),'physical_cores':sorted({x % 96 for x in actual}),
            'quarters':sorted({'q'+str((x % 96)//24) for x in actual})}

def engine_partial(manifest: Path, flags: Path, nonce: str) -> dict:
    """Assemble producer evidence after the normal and cutoff job entry paths."""
    m = load_manifest(manifest)
    qdir = flags / 'qual' / nonce
    need(os.environ.get('WS58_QUAL_NONCE') == nonce and os.environ.get('WS58_QUAL') == '1', 'engine partial outside qualification')
    normal = json.loads((qdir / 'proof-normal.json').read_text())
    cutoff = json.loads((qdir / 'proof-cutoff.json').read_text())
    need(normal.get('id') == cutoff.get('id') == m['id'], 'producer proof row id mismatch')
    need(normal.get('phase') == 'normal' and cutoff.get('phase') == 'cutoff', 'producer proof phase mismatch')
    need(normal.get('nonce') == cutoff.get('nonce') == nonce, 'producer proof nonce mismatch')
    need(cutoff.get('partial') is True, 'cutoff producer did not mark partial')
    cutoff_observation=None
    if m['production']:
        need(cutoff.get('stop_observed') is True or cutoff.get('deadline_reached') is True,
             'cutoff did not observe active STOP or deadline')
        need(cutoff.get('unknown_disposition')=='UNKNOWN', 'cutoff partial disposition must be UNKNOWN')
        observed=json.loads((qdir/'cutoff-observed.json').read_text())
        event=json.loads((qdir/'cutoff-event.json').read_text())
        need(observed.get('event_sha256')==sha(qdir/'cutoff-event.json') and
             observed.get('native_pid')==event.get('native_pid') and
             observed.get('native_birth_ticks')==event.get('native_birth_ticks') and
             observed.get('native_first_event') is True,
             'active cutoff event/child observation absent')
        pid=observed['native_pid']
        try: live_birth=int(Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split()[19])
        except (OSError,ValueError,IndexError):live_birth=None
        need(live_birth!=observed['native_birth_ticks'],'native cutoff child still alive')
        need(first_request_ok(m,cutoff.get('first_request',{})) and
             cutoff['first_request']==event.get('first_request'),
             'cutoff did not run native first request/compute before stop')
        cutoff_observation={**observed,'native_child_drained':True}
    first = normal.get('first_request', {})
    writer = normal.get('result_writer', {})
    need(first.get('ok') is True and writer.get('ok') is True, 'normal producer first request/result missing')
    result = Path(str(writer.get('result_path', '')))
    need(result.is_file() and result.resolve().is_relative_to((qdir / 'results').resolve()) and writer.get('sha256') == sha(result), 'producer result hash/path invalid')
    need(normal.get('disk', {}).get('job_floor_gib') == m['job_floor_gib'], 'producer disk floor mismatch')
    need(normal.get('observed_cpus') == cutoff.get('observed_cpus'), 'normal/cutoff CPU changed')
    from dryrun_check import cpus
    observed = set(normal.get('observed_cpus', []))
    try: claimed = cpus(os.environ.get('WS58_QUAL_CPUS', ''))
    except Exception as exc: raise Refused('synthetic CPU list malformed') from exc
    need(observed and observed.issubset(claimed), 'producer affinity not synthetic grant CPUs')
    obj = {'kind': 'epyc.qual.engine.v1', 'id': m['id'], 'nonce': nonce,
           'admission': {'rc': 0, 'grant_regions': os.environ.get('WS58_QUAL_CPUS'), 'observed_cpus': sorted(observed)},
           'first_request': first, 'result_writer': writer,
           'completion': {'complete_cmd_present': True, 'is_complete_rc': 0},
           'rc75': {'exit_code': 75, 'partial_flag': True,
                    'cutoff_mode':'active-stop' if m['production'] else 'fixture-immediate-deadline'},
           'disk': {'job_floor_gib': m['job_floor_gib'], 'policy_floor_gib': json.loads(POLICY.read_text())['normal_floor_gib'],
                    'est_output_gib': m['est_output_GiB']}, 'children_drained': True,
           'cutoff_observation':cutoff_observation}
    atomic_json(qdir / 'receipt-partial.json', obj)
    return obj

def trigger_cutoff(manifest:Path,flags:Path,nonce:str,stopfile:Path,timeout_s:int,job_pid:int)->dict:
    """Issue STOP only after an actual native event from a live owned child."""
    m=load_manifest(manifest);need(m['production'],'active cutoff belongs to production qualification only')
    qdir=flags/'qual'/nonce
    need(stopfile.resolve().is_relative_to(qdir.resolve()) and not stopfile.exists(), 'cutoff STOP path invalid')
    event_path=qdir/'cutoff-event.json';deadline=time.monotonic()+timeout_s
    while time.monotonic()<deadline:
        try:job_stat=Path(f'/proc/{job_pid}/stat').read_text().rsplit(') ',1)[1].split()
        except OSError:raise Refused('cutoff job exited before native first-event marker')
        need(job_stat[0] not in ('Z','X','x'),'cutoff job ended before native first-event marker')
        if event_path.is_file():
            event=json.loads(event_path.read_text())
            need(event.get('id')==m['id'] and event.get('nonce')==nonce and
                 event.get('phase')=='cutoff' and event.get('native_first_event') is True and
                 first_request_ok(m,event.get('first_request',{})), 'cutoff marker has no native first event')
            pid=event.get('native_pid');birth=event.get('native_birth_ticks')
            need(type(pid) is int and pid>1 and type(birth) is int and birth>0,'cutoff native child identity absent')
            stat=Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split()
            need(int(stat[19])==birth and os.getpgid(pid)==os.getpgrp() and
                 Path(f'/proc/{pid}').stat().st_uid==os.getuid(),
                 'cutoff native child not live in captured launcher group')
            observed={'native_pid':pid,'native_birth_ticks':birth,'native_first_event':True,
                      'event_sha256':sha(event_path),'observed_at':time.time()}
            atomic_json(qdir/'cutoff-observed.json',observed)
            fd=os.open(stopfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:f.write('qualification active cutoff\n')
            return observed
        time.sleep(.05)
    raise Refused('cutoff native first-event marker timed out before STOP')

def main() -> int:
    global ROOT, ALLOWLIST
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=('issue', 'run', 'verify', 'fingerprint', 'namespace-local', 'disk-wait', 'disk-breach', 'placement-local', 'engine-partial','trigger-cutoff','group-drain','pidfile-drain'))
    ap.add_argument('--manifest', required=True, type=Path)
    ap.add_argument('--flags', type=Path, default=ROOT)
    ap.add_argument('--nonce')
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--no-fingerprint-now', action='store_true')
    ap.add_argument('--free-gib', type=float)
    ap.add_argument('--qual-cpus', default='')
    ap.add_argument('--engine-class', default='')
    ap.add_argument('--no-fold', type=int, default=0)
    ap.add_argument('--claim-cpus', default='')
    ap.add_argument('--stop-file',type=Path)
    ap.add_argument('--job-pid',type=int)
    ap.add_argument('--pgid',type=int)
    ap.add_argument('--birth',type=int)
    ap.add_argument('--pidfile',type=Path)
    ap.add_argument('--ports',default='')
    args = ap.parse_args()
    ROOT=args.flags
    ALLOWLIST=args.flags/'engine-allowlist.json'
    try:
        if args.command=='group-drain':
            need(args.pgid and args.birth,'pgid and birth required');stop_group(args.pgid,args.birth);return 0
        if args.command=='pidfile-drain':
            need(args.pidfile,'pidfile required');pidfile_drain(args.pidfile,args.ports);return 0
        if args.command == 'namespace-local':
            print('EPYC_NAMESPACE_JSON=' + json.dumps(local_namespace(load_manifest(args.manifest)), sort_keys=True)); return 0
        if args.command == 'issue': print(issue(args.manifest, args.flags)); return 0
        if args.command == 'engine-partial':
            need(args.nonce, 'nonce required'); print(json.dumps(engine_partial(args.manifest, args.flags, args.nonce), sort_keys=True)); return 0
        if args.command == 'trigger-cutoff':
            need(args.nonce and args.stop_file and args.job_pid,'nonce, stop-file, and job-pid required')
            print(json.dumps(trigger_cutoff(args.manifest,args.flags,args.nonce,args.stop_file,args.timeout,args.job_pid),sort_keys=True));return 0
        if args.command == 'run':
            need(args.nonce, 'nonce required'); print(json.dumps(run(args.manifest, args.flags, args.nonce, args.timeout), sort_keys=True)); return 0
        if args.command == 'verify': print(json.dumps({'ok': True, 'id': verify(args.manifest, args.flags, not args.no_fingerprint_now)['id']})); return 0
        if args.command == 'fingerprint':
            m = load_manifest(args.manifest)
            print(json.dumps(launcher_namespace(args.manifest, m, dict(os.environ, WS58_MANIFEST_PATH=str(args.manifest), WS58_QUALIFIER_PATH=str(Path(__file__)))), sort_keys=True)); return 0
        if args.command == 'disk-wait': print('READY-WAIT-DISK' if disk_wait(args.manifest, args.free_gib) else 'DISK-READY'); return 1 if disk_wait(args.manifest, args.free_gib) else 0
        if args.command == 'disk-breach': print('DISK-FLOOR-BREACHED' if disk_breach(args.manifest) else 'DISK-OK'); return 1 if disk_breach(args.manifest) else 0
        if args.command == 'placement-local': print(json.dumps(placement_local(args.qual_cpus,args.engine_class,args.no_fold,args.claim_cpus))); return 0
    except (Refused, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        print('REFUSED: ' + str(e), file=sys.stderr); return 2
    return 2

if __name__ == '__main__': raise SystemExit(main())
