"""Prospective LB4.9 native diagnostic capture; no grading policy lives here.

Deterministic op inputs are declared by pinned source, not observed buffer dumps.
Model identities retain the original head/tail pin scope. No historical backfill.
"""
import datetime
import ast
from dataclasses import replace
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

SCHEMA = 'epyc.lb49.combined.native.v1'
SOURCE_KIND = 'lb49-combined-diagnostic'
ADAPTER_ID = 'vidya.adapters.lb49_combined_diagnostic/v1'
AUTHORITY = 'measurement'
_PROJECT_ROWS = {}
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters._native_sidecar import content_hash, file_sha256, seal, to_claim_tuple
from claim_tuple import register, ProjectionError

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)

def identity(path):
    path = Path(path).resolve(strict=True)
    st = path.stat()
    return {'path': str(path), 'dev': st.st_dev, 'inode': st.st_ino,
            'size': st.st_size, 'mtime_ns': st.st_mtime_ns, 'sha256': file_sha256(path)}

def same_stat(row):
    st = Path(row['path']).stat()
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) == tuple(
        row[k] for k in ('dev', 'inode', 'size', 'mtime_ns'))

def source_path(record, archive=None):
    if archive and record['path'] in archive:
        saved = archive[record['path']]
        require(saved['sha256'] == record['sha256'] and file_sha256(Path(saved['path'])) == record['sha256'], 'archived original source changed')
        return Path(saved['path'])
    require(same_stat(record) and file_sha256(Path(record['path'])) == record['sha256'], 'original source changed')
    return Path(record['path'])

def selected_entry(decl, archive=None):
    """Selected entry comes from the captured job, never pin-map enumeration order.

    The legacy declaration omitted the selection field. Its already-pinned job source
    and native argv retain the original selection; this is a reader join, not a new
    measurement field. Future declarations record it prospectively as well.
    """
    jobs = [r for r in decl['sources'] if Path(r['path']).name == 'job.py']
    require(len(jobs) == 1, 'selected entry lacks original job source')
    tree = ast.parse(source_path(jobs[0], archive).read_text())
    values = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = {x.id for x in node.targets if isinstance(x, ast.Name)}
        if not decl['smoke'] and 'MODEL' in names and isinstance(node.value, ast.Call) and node.value.args and isinstance(node.value.args[0], ast.Constant):
            values.append(node.value.args[0].value)
        if decl['smoke'] and 'model' in names and isinstance(node.value, ast.IfExp) and isinstance(node.value.test, ast.Name) and node.value.test.id == 'smoke' and isinstance(node.value.body, ast.Constant):
            values.append(node.value.body.value)
    require(len(values) == 1 and isinstance(values[0], str) and values[0] in decl['model_pins'], 'selected entry not in full pinned set/original source')
    require(decl.get('selected_entry_model', values[0]) == values[0], 'selected entry conflicts with original source')
    return values[0]

def declaration(packet, smoke):
    packet = Path(packet)
    pins = json.loads((packet / 'MODEL-PINS.json').read_text())
    record = {'schema': SCHEMA, 'capture_started_at': now(), 'packet': str(packet),
            'smoke': smoke, 'scope': 'Gemma plumbing smoke only; no DS41 finding' if smoke else 'DS41 diagnostic observations only',
            'protocol_id': '', 'source_manifest': identity(packet / 'SOURCES.sha256'),
            'sources': [identity(packet / name) for name in ('job.py', 'reader.py', 'lb49_capture.py', 'src/test_opcases.cpp', 'src/capture_combined.cpp', 'PLAN.json')],
            'plan': json.loads((packet / 'PLAN.json').read_text()),
            'build_provenance': [identity(Path('/mnt/raid0/llm/tmp/lb49-codex-evidence-20261028') / name) for name in ('identity.txt', 'final-guard-source.sha256', 'final-guard-feature-hashes.sha256')],
            'model_pins': {p: v for p, v in pins.items() if smoke == ('gemma-3-1b' in p)},
            'model_pin_scope': 'canonical path, size, sha256 of first+last64MiB; not full-weight sha256',
            'input_custody': 'DECLARED_BY_PINNED_SOURCE; QKV/mask/sink buffers not dumped or independently observed',
            'grant': grant(smoke), 'affinity': sorted(os.sched_getaffinity(0))}
    record['selected_entry_model'] = selected_entry(record)
    return record

def grant(smoke):
    if smoke:
        return {'mode': 'R11_CPU_SMOKE_NO_GRANT', 'env': {}}
    p = Path('/mnt/raid0/llm/tmp/compute-flags/grants/codex-ni-lb49-combined-ready-20261030.grant')
    raw = p.read_text()
    return {'mode': 'scheduled', 'identity': identity(p), 'native_text': raw,
            'env': {k: v for k, v in os.environ.items() if k.startswith('FILLER_') or k == 'WS58_REGIONS'}}

class Window:
    """Write actual process observations during its lifetime; never reopen after reap."""
    def __init__(self, root, rec, pid):
        self.path = Path(root) / (rec['name'] + '.live.jsonl')
        self.pid = pid
        self.birth = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()[19]
        self.objects = {}
        self.rec = rec
        rec['native_binary'] = identity(rec['cmd'][0])
        rec['live_path'] = str(self.path)
        rec['live_samples'] = 0

    def sample(self):
        base = Path(f'/proc/{self.pid}')
        raw = (base / 'stat').read_text().rsplit(') ', 1)[1].split()
        if raw[19] != self.birth or raw[0] == 'Z':
            return
        maps = (base / 'maps').read_text().splitlines()
        mapped = []
        for line in maps:
            parts = line.split(maxsplit=5)
            if len(parts) != 6 or not ('/libggml' in parts[5] or '/libllama' in parts[5]):
                continue
            p = Path(parts[5])
            st = p.stat()
            device = parts[3].split(':')
            if int(parts[4]) != st.st_ino or (int(device[0], 16), int(device[1], 16)) != (os.major(st.st_dev), os.minor(st.st_dev)):
                raise ValueError('mapped library stat mismatch')
            key = str(p)
            if key not in self.objects:
                self.objects[key] = identity(p)
            if not same_stat(self.objects[key]):
                raise ValueError('mapped library changed during native window')
            mapped.append({'mapping': line, 'identity': self.objects[key]})
        # Confirm identity still refers to the same non-zombie process after hashing.
        tail = (base / 'stat').read_text().rsplit(') ', 1)[1].split()
        if tail[19] != self.birth or tail[0] == 'Z':
            return
        row = {'at': now(), 'monotonic_ns': __import__('time').monotonic_ns(),
               'pid': self.pid, 'birth_ticks': self.birth, 'state': tail[0],
               'affinity': sorted(os.sched_getaffinity(self.pid)), 'mapped_objects': mapped,
               'kfd_registered': Path(f'/sys/class/kfd/kfd/proc/{self.pid}').exists()}
        with self.path.open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
            f.flush()
        self.rec['live_samples'] += 1

def finish(root, result, decl):
    """Called by the producer once all owned native children have been reaped."""
    root = Path(root)
    artifacts = [identity(p) for p in sorted(root.rglob('*')) if p.is_file()
                 and p.suffix not in ('.tmp',) and p.name not in ('native.json', 'beliefs.jsonl')]
    receipt = {'schema': SCHEMA, 'emitted_at': now(), 'declaration': decl,
               'result': result, 'artifacts': artifacts,
               'status': 'partial' if result.get('partial') else 'complete' if result.get('exit_ok') else 'error'}
    receipt['row_sha256'] = content_hash(receipt)
    write(root / 'native.json', receipt)
    if receipt['status'] == 'complete':
        rows = authored_rows(root / 'native.json')
        (root / 'beliefs.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))
    return root / 'native.json'

def require(ok, why):
    if not ok:
        raise ValueError(why)

def native_log_text(path):
    # Token display may contain arbitrary bytes. Custody binds the original bytes;
    # only ASCII native framing markers are inspected here, never decoded token text.
    return Path(path).read_bytes().decode('utf-8', errors='replace')

def read_native(path, *, original_error_recovery=False, source_archive=None):
    path = Path(path)
    r = json.loads(path.read_text())
    require(r.get('schema') == SCHEMA, 'native schema')
    require(r.get('row_sha256') == content_hash({k: v for k, v in r.items() if k != 'row_sha256'}), 'native self hash')
    if original_error_recovery:
        require(r['status'] == 'error' and r['result'].get('exit_ok') is False and r['result'].get('error') == 'ValueError: native invocation/input joins' and not r['result'].get('partial'), 'not the original model-join refusal')
    else:
        require(r['status'] == 'complete' and r['result'].get('exit_ok') and not r['result'].get('partial'), 'partial/error is not complete')
    d, result = r['declaration'], r['result']
    checked = set()
    def bound_file(a):
        key = tuple(a[k] for k in ('path', 'dev', 'inode', 'size', 'mtime_ns', 'sha256'))
        require(same_stat(a), 'native file stat changed ' + a['path'])
        if key not in checked:
            require(file_sha256(Path(a['path'])) == a['sha256'], 'native file hash changed ' + a['path'])
            checked.add(key)
    require(d['protocol_id'] == '' and d['input_custody'].startswith('DECLARED_BY_PINNED_SOURCE'), 'undeclared warrant')
    for a in r['artifacts']:
        bound_file(a)
    for a in [d['source_manifest'], *d['sources'], *d['build_provenance']]:
        source_path(a, source_archive)
    expected_files = {str(Path(line.split('  ', 1)[1]).resolve()): line.split('  ', 1)[0]
                      for line in source_path(d['source_manifest'], source_archive).read_text().splitlines()}
    require([p['name'] for p in result['phases']] == ['opcases', 'baseline', 'candidate'], 'phase cardinality/order')
    for p in result['phases']:
        require(p['rc'] == 0 and p['cleanup_verified'] and not p['cutoff'], 'native phase cleanup/rc')
        bound_file(p['native_binary'])
        require(expected_files.get(p['native_binary']['path']) == p['native_binary']['sha256'], 'native ELF outside frozen closure')
        samples = [json.loads(line) for line in Path(p['live_path']).read_text().splitlines()]
        require(len(samples) == p['live_samples'] and len(samples) >= 1, 'no live native observations')
        has_runtime = False
        for s in samples:
            require(s['pid'] == p['pid'] and s['birth_ticks'] == p['birth_ticks'] and s['state'] != 'Z', 'process identity/window')
            require(p['started_at'] <= s['at'] <= p['finished_at'], 'live sample outside window')
            require(s['affinity'] == d['affinity'] and not s['kfd_registered'], 'CPU native residency')
            for obj in s['mapped_objects']:
                ident = obj['identity']
                require(Path(ident['path']).parent == Path(p['runtime']), 'wrong mapped runtime')
                has_runtime |= 'libggml-cpu' in ident['path']
                bound_file(ident)
                require(expected_files.get(ident['path']) == ident['sha256'], 'mapped library outside frozen closure')
        require(has_runtime, 'no live mapped CPU runtime proof')
    native = Path(result['phases'][0]['log']).read_text()
    rows = [line for line in native.splitlines() if line.startswith('RESULT ')]
    require(rows == result['opcases_rows'] and len(rows) == 72 and len(set(rows)) == 72, 'opcase matrix cardinality')
    expected = {'ds41-swa-layer0', 'ds41-swa-layer1', 'ds41-stock-mask', 'gathered-640', 'gathered-768', 'fully-masked', 'generic-fallback', 'null-sinks', 'ds41-sinks-zero-swa0', 'ds41-sinks-zero-stock', 'gathered-640-sinks-zero', 'gathered-768-sinks-zero'}
    bycase = {}
    for line in rows:
        fields = dict(word.split('=', 1) for word in line.split()[1:])
        require(fields['verdict'] == 'PASS', 'native opcase refused')
        bycase.setdefault(fields['case'], []).append(fields)
        if 'nth' in fields:
            require(float(fields['nmse']) <= 5e-4 and float(fields['oracle_nmse']) <= 5e-4, 'inherited op NMSE')
    require(set(bycase) == expected, 'opcase names')
    for cells in bycase.values():
        require(len(cells) == 6 and sorted(int(c['nth']) for c in cells if 'nth' in c) == [1,16,32,64,96] and sum(c.get('control') == 'off' for c in cells) == 1, 'opcase thread/control matrix')
    # The existing scientific metric reader remains authoritative and unchanged.
    reader_record = next(a for a in d['sources'] if Path(a['path']).name == 'reader.py')
    spec = importlib.util.spec_from_file_location('lb49_scientific_reader', source_path(reader_record, source_archive))
    reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
    capture = path.parent / 'capture'
    computed = reader.read(capture)
    require(computed == result['comparison'], 'native metric joins changed')
    h, count = (2, 1) if d['smoke'] else (65, 3)
    require(len(computed['records']) == count, 'prompt cardinality')
    model = selected_entry(d, source_archive)
    for p in result['phases'][1:]:
        cmd = p['cmd']
        require(len(cmd) == 8 and cmd[1] == model and Path(cmd[2]) == capture / p['name']
                and int(cmd[4]) == h and int(cmd[5]) == count and cmd[6] == p['name']
                and Path(cmd[7]) == capture / 'baseline', 'native invocation/input joins')
        text = native_log_text(p['log'])
        require(text.count('NATIVE_REQUEST_BEGIN mode=' + p['name']) == count and
                text.count('PROMPT_COMPLETE ') == count and 'COMBINED_CAPTURE_COMPLETE' in text,
                'native request completion joins')
        if p['name'] == 'candidate':
            require('ARM_OPTION --cpu-iqk-fa on' in text, 'native feature-on assertion missing')
    require(result['phases'][1]['native_binary']['sha256'] != result['phases'][2]['native_binary']['sha256'], 'baseline not independently linked')
    for index, joined in enumerate(computed['records']):
        label = joined['label']
        bm = json.loads((capture / 'baseline' / (label + '.comparison.json')).read_text())
        cm = json.loads((capture / 'candidate' / (label + '.comparison.json')).read_text())
        require(bm == dict(cm, mode='baseline') and bm['mode'] == 'baseline' and cm['mode'] == 'candidate', 'arm metadata join')
        require(bm['horizon'] == h and bm['prompt'] == d['plan']['teacher_forcing']['prompts'][index], 'prompt/horizon identity')
        ids = [int(x) for x in (capture / 'baseline' / (label + '.baseline-token-ids.txt')).read_text().split()]
        require(len(ids) == h, 'teacher token cardinality')
        _, values = reader.vec(capture / 'baseline' / (label + '.logits.f32le'))
        nv = len(values) // h
        require(ids == [max(range(nv), key=lambda i: (values[s*nv+i], -i)) for s in range(h)], 'teacher tokens not baseline argmax')
        require(joined['horizon'] == h and len(joined['per_step']) == h and [x['step_zero_based'] for x in joined['per_step']] == list(range(h)), 'position joins')
    require(len(list((capture / 'candidate').glob('*.comparison.json'))) == count, 'candidate extra/missing prompts')
    return r

RECOVERY_SCHEMA = 'epyc.lb49.combined.projection-recovery.v1'

def read_recovered(path):
    receipt = json.loads(Path(path).read_text())
    require(receipt.get('schema') == RECOVERY_SCHEMA and receipt.get('projection_only') is True, 'not a projection-only recovery')
    require(receipt.get('row_sha256') == content_hash({k:v for k,v in receipt.items() if k != 'row_sha256'}), 'recovery self hash')
    original = receipt['original_native']
    require(same_stat(original) and file_sha256(Path(original['path'])) == original['sha256'], 'original native refusal changed')
    for original_path, saved in receipt['source_archive'].items():
        require(file_sha256(Path(saved['path'])) == saved['sha256'], 'original source archive changed')
    native = read_native(original['path'], original_error_recovery=True, source_archive=receipt['source_archive'])
    require(receipt['original_status'] == native['status'] == 'error' and receipt['original_error'] == native['result']['error'], 'recovery relabels original event')
    return native, receipt

def authored_rows(path):
    path = Path(path)
    envelope = json.loads(path.read_text())
    recovery = None
    if envelope.get('schema') == RECOVERY_SCHEMA:
        r, recovery = read_recovered(path)
    else:
        r = read_native(path)
    d = r['declaration']
    out = []
    def emit(metric, value, unit, claim, category, native):
        horizon, prompts = (2, 1) if d['smoke'] else (65, 3)
        mode = 'independent-baseline+fresh-KV-repeat+separate-feature-ON-forced-replay'
        scope = {'model_file': Path(selected_entry(d, recovery['source_archive'] if recovery else None)).name, 'backend': 'cpu',
                 'shape': f'positions={horizon};prompts={prompts};mode={mode}'}
        if metric == 'opcase_nmse':
            scope = {'backend': 'cpu', 'op': 'FLASH_ATTN_EXT', 'shape': 'D512 H64 KVH1 synthetic exact cases'}
        mechanism_scope = {'applicability': scope, 'positions': horizon, 'prompts': prompts, 'mode': mode}
        extra = {'native_record': native, 'scope': d['scope'], 'smoke': d['smoke'],
                 'applicability': scope,
                 'mechanism_scope': mechanism_scope,
                 'mechanism_id': 'lb49-combined-diagnostic/' + metric + '/' + content_hash(mechanism_scope)[:16],
                 'mechanism_statement': d['scope'] + f'; positions={horizon}, prompts={prompts}; ' + metric + '; positions are not independent launch replicates',
                 'native_receipt_sha256': r['row_sha256']}
        if recovery:
            extra['projection_recovery'] = {'projection_only': True, 'original_native': recovery['original_native'], 'original_status': recovery['original_status'], 'original_error': recovery['original_error']}
            extra['mechanism_statement'] += '; projection-only recovery, original aggregate rc1'
        row = {'schema': SCHEMA, 'run_id': path.parent.name, 'producer': 'lb49/job.py',
               'measurement_id': 'lb49_' + content_hash([r['row_sha256'], metric, native] + ([recovery['row_sha256']] if recovery else []))[:24],
               'metric': metric, 'value': value, 'unit': unit, 'metric_direction': 'higher_better' if metric == 'baseline_margin_logit_units' else 'lower_better',
               'category': category, 'claim': ('Projection-only recovery of original aggregate rc1; ' if recovery else '') + d['scope'] + ': ' + claim, 'protocol_id': '',
               'reps': 1, 'reps_basis': 'scored one native launch; positions are not independent replicates',
               'results_path': str(path), 'results_sha256': file_sha256(path),
               'date': r['emitted_at'][:10], 'emitted_at': r['emitted_at'], 'extra': extra}
        out.append(seal(row))
    for line in r['result']['opcases_rows']:
        f = dict(w.split('=', 1) for w in line.split()[1:])
        if 'nmse' in f:
            emit('opcase_nmse', float(f['nmse']), 'NMSE', 'native opcase ' + line, 'CANDIDATE', f)
    for rec in r['result']['comparison']['records']:
        for step in rec['per_step']:
            native = {'label': rec['label'], 'prompt': rec['prompt'], **step}
            for metric in ('max_abs_logit_delta', 'mean_abs_logit_delta', 'baseline_repeat_max_abs', 'baseline_margin_logit_units'):
                emit(metric, step[metric], 'logit', f"{rec['label']} position {step['step_zero_based']} {metric}={step[metric]}; descriptive only", 'BASELINE' if metric.startswith('baseline') else 'CANDIDATE', native)
    return out

def _native_rows_impl(path):
    path = Path(path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    require(bool(rows), 'empty sidecar')
    receipt = Path(rows[0]['results_path'])
    expected = authored_rows(receipt)
    require(rows == expected, 'sidecar did not rederive from captured native receipt')
    _PROJECT_ROWS[str(receipt)] = (file_sha256(receipt), expected)
    return tuple({'row': row, 'sidecar_path': str(path)} for row in rows)

def _project_impl(native):
    row = native['row']
    receipt = Path(row['results_path'])
    cached = _PROJECT_ROWS.get(str(receipt))
    digest = file_sha256(receipt)
    if cached is None or cached[0] != digest:
        cached = (digest, authored_rows(receipt))
        _PROJECT_ROWS[str(receipt)] = cached
    require(row in cached[1], 'unbound native row')
    t = to_claim_tuple(row, source_kind=SOURCE_KIND, locator=row['results_path'], sidecar_path=native.get('sidecar_path', ''))
    return replace(t, applicability=row['extra']['applicability'],
                   observation={'mechanism': {'id': row['extra']['mechanism_id'], 'statement': row['extra']['mechanism_statement']}, 'outcome_native': 'diagnostic observation only'})


def native_rows(path):
    try:
        return _native_rows_impl(path)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise ProjectionError('LB49_NATIVE_REFUSED: ' + str(exc)) from exc

@register(SOURCE_KIND)
def project(native):
    try:
        return _project_impl(native)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise ProjectionError('LB49_NATIVE_REFUSED: ' + str(exc)) from exc
