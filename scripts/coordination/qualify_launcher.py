#!/usr/bin/env python3
"""LOOP-49 keeper-side qualification. No production grants or fixture removal.

Nonce records live in a keeper-controlled directory passed explicitly by the
keeper, never in a worker manifest. Same-uid workers are not a security boundary:
that directory must be protected by the keeper's OS execution identity.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dryrun_check import checked_manifest, floor_gib, grant_cpus, seconds

class Refused(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise Refused(reason)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

def create(path, value):
    """Exclusive append-only artifacts: no unlink, rename or replacement."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as out:
        json.dump(value, out, sort_keys=True, indent=2, allow_nan=False)
        out.write('\n')

def manifest_hash(m):
    return digest({k: v for k, v in m.items() if k not in ('qualification', 'keeper_log', 'hold')})

def path_of(m, key):
    value = m.get(key)
    return Path(value['path'] if isinstance(value, dict) else value)

def canonical_engine_path():
    """Resolve the keeper-configured deployment root, never this import's directory."""
    root = Path(os.environ.get('WS58_ROOT', '/workspace')).resolve()
    return root / 'scripts/coordination/filler_run14.sh'

def check_row_binding(m):
    """Reject a pinned row whose scheduling contract disagrees with its manifest."""
    row_path = path_of(m, 'row')
    matches = []
    for line in row_path.read_text().splitlines():
        if not line.startswith('|'):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if cells and cells[0] == m['id']:
            matches.append(cells)
    require(len(matches) == 1 and len(matches[0]) == 18, 'row-id-missing-duplicate-or-shape')
    cells = matches[0]
    try:
        notes = dict(re.findall(r'(?:^|;\s*)([A-Za-z][A-Za-z0-9_]*)=([^;]+)', cells[17]))
        requested = int(notes['requested_window_s'])
        estimate = float(notes['est_output_GiB'])
        process_limit = float(notes.get('process_limit_GiB', m['gib']))
        reserved_ram = float(cells[5].removesuffix('GiB').strip())
        row_window = seconds(cells[9])
        row_minimum = seconds(cells[10])
    except (KeyError, ValueError, TypeError) as exc:
        raise Refused('row-scheduling-fields-invalid:' + str(exc))
    require(row_window == int(m['window_s']) == requested, 'row-window-manifest-mismatch')
    require(row_minimum == int(m['min_window_s']), 'row-min-window-manifest-mismatch')
    require(reserved_ram == float(m['gib']), 'row-ram-manifest-mismatch')
    require(process_limit == float(m.get('process_limit_GiB', m['gib'])), 'row-process-limit-manifest-mismatch')
    require(estimate == float(m['est_output_GiB']), 'row-output-estimate-manifest-mismatch')
    require(Path(notes['scratch_root']).resolve() == Path(m['scratch_root']).resolve(), 'row-scratch-root-manifest-mismatch')
    row_claim = notes['claimed_cpus'].strip()
    declared_claim = str(m['claimed_cpus']).strip()
    if declared_claim.startswith('any-'):
        require(row_claim == declared_claim, 'row-relocatable-cpus-manifest-mismatch')
    else:
        try:
            require(grant_cpus(row_claim) == grant_cpus(declared_claim), 'row-cpus-manifest-mismatch')
        except Exception as exc:
            if isinstance(exc, Refused):
                raise
            raise Refused('row-cpus-invalid:' + str(exc))
    require(cells[3] == str(m['regions']), 'row-regions-manifest-mismatch')
    if m.get('booking_class') is not None:
        require(cells[8] == str(m['booking_class']), 'row-booking-class-manifest-mismatch')
    return {'row_sha256': sha(row_path), 'reserved_ram_gib': reserved_ram,
            'process_limit_GiB': process_limit, 'est_output_GiB': estimate,
            'scratch_root': str(Path(m['scratch_root']).resolve()),
            'claimed_cpus': row_claim, 'window_s': row_window,
            'min_window_s': row_minimum}

def finite_positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0

def static_check(m, allowlist):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', m['id']), 'invalid-id')
    for field in ('requires_tools', 'ports', 'shared_state'):
        require(isinstance(m.get(field), list), 'missing-or-invalid:' + field)
    require(all(isinstance(t, str) and t for t in m['requires_tools']), 'invalid-tools')
    require(all(type(p) is int and 0 < p < 65536 for p in m['ports']), 'invalid-ports')
    require(all(isinstance(s, str) and s for s in m['shared_state']), 'invalid-shared-state')
    require('exclusive_class' in m and (m['exclusive_class'] is None or isinstance(m['exclusive_class'], str)), 'invalid-exclusive-class')
    for field in ('window_s', 'min_window_s', 'items', 'tokens_per_item', 'n_ctx_required'):
        require(finite_positive(m.get(field)), 'invalid:' + field)
    require(m['min_window_s'] % 60 == 0 and m['window_s'] >= m['min_window_s'], 'window-alignment')
    require(finite_positive(m.get('qual_timeout_s', 300)) and m.get('qual_timeout_s', 300) <= 600, 'invalid-qual-timeout')
    require(finite_positive(m.get('gib')), 'invalid:reserved-ram-gib')
    require(finite_positive(m.get('process_limit_GiB', m.get('gib'))) and
            m.get('process_limit_GiB', m.get('gib')) <= m.get('gib'), 'invalid:process-limit-gib')
    require(isinstance(m.get('est_output_GiB'), (float, int)) and math.isfinite(m['est_output_GiB']) and m['est_output_GiB'] >= 0, 'invalid-output-estimate')
    claimed = m.get('claimed_cpus', '')
    relocatable = str(m.get('regions', '')).startswith('any-')
    if relocatable:
        require(claimed == m['regions'], 'relocatable-with-fixed-cpus')
    else:
        require(bool(grant_cpus(str(claimed))), 'invalid-claimed-cpus')
    for field in ('launcher', 'engine', 'job', 'qual_fixture', 'source_manifest', 'row'):
        require(path_of(m, field).is_file(), 'missing:' + field)
    require(path_of(m, 'engine').resolve() == canonical_engine_path(), 'noncanonical-engine')
    scratch = Path(m['scratch_root'])
    require(scratch.is_absolute() and scratch.is_dir(), 'scratch-root-missing')
    check_row_binding(m)
    require(load(allowlist) == {'kind': 'epyc.engine-allowlist.v1', 'engines': [sha(path_of(m, 'engine'))]}, 'engine-not-allowlisted')
    checked_manifest(path_of(m, 'source_manifest'))
    return m

def hashes(m, policy):
    result = {'manifest_sha256': manifest_hash(m), 'policy_sha256': sha(policy), 'checker_sha256': sha(__file__),
              'engine_runtime_sha256': sha(HERE / 'filler_engine14.py')}
    for field in ('launcher', 'engine', 'job', 'qual_fixture', 'source_manifest'):
        result[field + '_path'] = str(path_of(m, field).resolve())
        result[field + '_sha256'] = sha(path_of(m, field))
    row = path_of(m, 'row') if m.get('row') else None
    if row is not None:
        result['row_sha256'] = sha(row)
    return result

def namespace(workdir, tools, interpreter=sys.executable):
    interp = str(Path(interpreter).resolve())
    require(Path(workdir).is_dir(), 'workdir-missing')
    return {'mode': 'host-chroot' if os.environ.get('WS58_EXEC_MODE') == 'host-chroot' else 'container',
            'root_inode': os.stat('/').st_ino, 'root_device': os.stat('/').st_dev,
            'kernel': os.uname().release, 'cwd': str(Path(workdir).resolve()), 'cwd_exists': True,
            'interpreter': {'path': interp, 'sha256': sha(interp), 'version': sys.version.split()[0]},
            'tools': {t: shutil.which(t) for t in tools},
            'env_fingerprint_sha256': digest({k: os.environ.get(k, '') for k in ('PATH', 'HOME', 'LD_LIBRARY_PATH', 'VIRTUAL_ENV')})}

def kill_owned(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
    # Descendants may outlive their leader. This is our captured setsid group.
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        os.killpg(proc.pid, 0)
    except ProcessLookupError:
        return
    raise Refused('children-not-drained')

def invoke(launcher, cwd, env, timeout, logfile):
    with Path(logfile).open('x') as log:
        proc = subprocess.Popen(['bash', str(launcher)], cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            rc = proc.wait(timeout=timeout)
        except BaseException:
            kill_owned(proc)
            raise
        kill_owned(proc)
    return rc

def fingerprint(launcher, cwd, timeout=30):
    env = dict(os.environ, WS58_FINGERPRINT_ONLY='1')
    proc = subprocess.Popen(['bash', str(launcher)], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except BaseException:
        kill_owned(proc)
        raise
    kill_owned(proc)
    require(proc.returncode == 0, 'fingerprint-failed:' + err[-250:])
    records = []
    for line in out.splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict) and 'exec_namespace' in item:
                records.append(item['exec_namespace'])
        except ValueError:
            pass
    require(len(records) == 1, 'fingerprint-missing-or-ambiguous')
    return records[0]

def evidence_check(m, p, policy):
    require(p['admission']['rc'] == 0, 'admission')
    require(p['admission']['affinity_ok'] is True, 'affinity')
    require(p['completion']['complete_cmd_present'] is True and p['completion']['is_complete_rc'] == 0, 'completion')
    require(p['rc75']['exit_code'] == 75 and p['rc75']['partial_flag'] is True, 'rc75')
    require(p['disk']['job_floor_gib'] == p['disk']['policy_floor_gib'] == floor_gib(Path(policy)), 'disk-floor-mismatch')
    require(p['children_drained'] is True, 'children-not-drained')
    f = p['first_request']
    require(f['ok'] is True and f['n_ctx'] >= m['n_ctx_required'] and f['prompt_tokens'] >= m['tokens_per_item'], 'n_ctx-or-prompt')
    require(finite_positive(f['measured_tok_s']), 'invalid-rate')
    require(m['items'] * m['tokens_per_item'] / f['measured_tok_s'] <= m['window_s'], 'infeasible-window')
    require(p['result_writer']['ok'] is True and sha(p['result_writer']['result_path']) == p['result_writer']['sha256'], 'result-writer')
    require(all(p['exec_namespace']['tools'].get(t) for t in m['requires_tools']), 'tool-missing')

def receipt_path(m):
    return Path(m['scratch_root']) / 'qualification' / ('QUAL-' + m['id'] + '.json')

def verify(m, args):
    static_check(m, args.allowlist)
    p = load(receipt_path(m))
    require(p['kind'] == 'epyc.qual.pass.v1' and p['id'] == m['id'], 'receipt-identity')
    require(re.fullmatch('[0-9a-f]{32,}', p['nonce']), 'nonce-format')
    issued = load(Path(args.nonce_store) / (p['nonce'] + '.issued.json'))
    sealed = load(Path(args.nonce_store) / (p['nonce'] + '.sealed.json'))
    require(issued['id'] == m['id'] and sealed['id'] == m['id'], 'nonce-identity')
    expected = digest({k: v for k, v in p.items() if k != 'receipt_sha256_excluding_self'})
    require(p['receipt_sha256_excluding_self'] == expected == sealed['receipt_sha256'], 'receipt-integrity')
    require(issued['binding'] == hashes(m, args.policy), 'issued-binding-stale')
    require(all(p.get(k) == v for k, v in hashes(m, args.policy).items()), 'file-binding-stale')
    age = time.time() - datetime.fromisoformat(p['ran_at'].replace('Z', '+00:00')).timestamp()
    require(0 <= age < 86400, 'receipt-expired')
    evidence_check(m, p, args.policy)
    if args.fingerprint_now:
        require(p['exec_namespace'] == fingerprint(path_of(m, 'launcher'), args.flags_dir), 'namespace-stale')
    return p

def _run(m, args):
    static_check(m, args.allowlist)
    require(re.fullmatch('[0-9a-f]{32,}', args.nonce), 'nonce-format')
    require(bool(grant_cpus(args.regions)), 'invalid-qual-regions')
    require(len(grant_cpus(args.regions)) == 2, 'qualification-needs-two-cpus')
    if not str(m['regions']).startswith('any-'):
        require(not (grant_cpus(args.regions) & grant_cpus(str(m['claimed_cpus']))), 'qualification-must-relocate')
    require(not args.out or Path(args.out).resolve() == receipt_path(m).resolve(), 'noncanonical-receipt-path')
    binding = hashes(m, args.policy)
    create(Path(args.nonce_store) / (args.nonce + '.issued.json'), {'id': m['id'], 'binding': binding})
    root = Path(args.flags_dir) / 'qual' / args.nonce
    root.mkdir(parents=True, exist_ok=False)
    grants = root / 'grants'; grants.mkdir()
    results = root / 'results'; results.mkdir()
    now = int(time.time()) // 60 * 60
    stamp = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    with (grants / (m['id'] + '.grant')).open('x') as f:
        f.write(f"regions={args.regions} start={stamp(now)} end={stamp(now + int(m['min_window_s']) + 300)}\n")
    lines = []
    for line in path_of(m, 'row').read_text().splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if line.startswith('|') and cells[0] == m['id']:
            require(len(cells) == 18, 'row-shape')
            cells[10] = str(int(m['min_window_s'])) + ' s'
            notes = cells[17]
            for key, value in (('requested_window_s', int(m['min_window_s']) + 300), ('claimed_cpus', args.regions)):
                require(re.search(r'(?:^|;\s*)' + key + r'=[^;]+', notes), 'row-missing:' + key)
                notes = re.sub(r'(?<![A-Za-z_])' + key + r'=[^;]+', key + '=' + str(value), notes)
            cells[17] = notes
            lines.append('| ' + ' | '.join(cells) + ' |')
    require(len(lines) == 1, 'row-id-missing-or-duplicate')
    with (root / 'FILLERS.md').open('x') as f:
        f.write(lines[0] + '\n')
    env = dict(os.environ, FILLERS_MD=str(root / 'FILLERS.md'), WS58_QUAL='1', WS58_QUAL_NONCE=args.nonce, WS58_QUAL_RESULTS=str(results),
               WS58_QUAL_ROOT=str(root), WS58_QUAL_MANIFEST=str(Path(args.manifest).resolve()),
               WS58_QUAL_POLICY=str(Path(args.policy).resolve()), FILLER_GRANTS_DIR=str(grants), WS58_REGIONS=args.regions)
    rc = invoke(path_of(m, 'launcher'), args.flags_dir, env, m.get('qual_timeout_s', 300), root / 'launcher.log')
    require(rc == 0, 'qual-launcher-rc:' + str(rc))
    p = load(root / 'receipt-partial.json')
    require(hashes(m, args.policy) == binding, 'files-changed-during-qualification')
    p.update(binding, kind='epyc.qual.pass.v1', id=m['id'], nonce=args.nonce,
             ran_at=datetime.now(timezone.utc).isoformat(), ran_by='ws58-calendar-keeper')
    require(p['exec_namespace'] == fingerprint(path_of(m, 'launcher'), args.flags_dir), 'namespace-changed-during-qualification')
    evidence_check(m, p, args.policy)
    p['receipt_sha256_excluding_self'] = digest(p)
    create(args.out or receipt_path(m), p)
    create(Path(args.nonce_store) / (args.nonce + '.sealed.json'), {'id': m['id'], 'receipt_sha256': p['receipt_sha256_excluding_self']})
    return p

def run(m, args):
    status = {'state': 'failed', 'id': m.get('id'), 'nonce': args.nonce}
    try:
        receipt = _run(m, args)
        status['state'] = 'passed'
        status['receipt_sha256'] = receipt['receipt_sha256_excluding_self']
        return receipt
    except Exception as exc:
        status['reason'] = str(exc)
        raise
    finally:
        root = Path(args.flags_dir) / 'qual' / args.nonce
        if re.fullmatch('[0-9a-f]{32,}', args.nonce) and root.is_dir():
            # An exclusive terminal marker never erases a prior failed attempt.
            status['ended_at'] = datetime.now(timezone.utc).isoformat()
            try:
                create(root / 'terminal.json', status)
            except FileExistsError:
                pass


def scheduling_state(m, active, free_gib, policy):
    """Keeper calls before writing any production grant. WAIT rows are uncounted."""
    if free_gib - m['est_output_GiB'] - 2 < floor_gib(Path(policy)):
        return 'READY-WAIT-DISK'
    for other in active:
        if set(m['ports']) & set(other['ports']):
            return 'READY-SKIP port-overlap'
        if m.get('exclusive_class') and m['exclusive_class'] == other.get('exclusive_class'):
            return 'READY-SKIP exclusive-class'
        if set(m['shared_state']) & set(other['shared_state']):
            return 'READY-SKIP shared-state'
    return 'READY-QUALIFIED'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('run', 'verify'):
        p = sub.add_parser(name)
        p.add_argument('--manifest', required=True)
        p.add_argument('--nonce-store', required=True)
        p.add_argument('--allowlist', required=True)
        p.add_argument('--policy', default=str(HERE / 'dryrun_disk_policy.json'))
        p.add_argument('--flags-dir', default='/mnt/raid0/llm/tmp/compute-flags')
        if name == 'run':
            p.add_argument('--nonce', required=True); p.add_argument('--regions', required=True); p.add_argument('--out')
        else:
            p.add_argument('--fingerprint-now', action='store_true')
    p = sub.add_parser('fingerprint'); p.add_argument('--launcher', required=True)
    p.add_argument('--flags-dir', default='/mnt/raid0/llm/tmp/compute-flags')
    args = parser.parse_args()
    try:
        result = fingerprint(Path(args.launcher), args.flags_dir) if args.command == 'fingerprint' else globals()[args.command](load(args.manifest), args)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
    except Exception as exc:
        print('READY-SKIP qual:' + str(exc))
        return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
