#!/usr/bin/env python3
"""Owner proposal: native metadata registration and grant-time sweep under publication lock.

The caller must hold .publication.lock for the entire invocation AND grant write.
This program does not acquire a lease, issue grants, or assert producer coverage.
"""
import argparse
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import tempfile
import dryrun_check as dryrun

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registration_sweep as sweep

CAT = 'registration-catalog.json'
PENDING = '.registration-pending.json'
RECEIPTS = 'registration-receipts.json'
LEGACY = 'registration-legacy-cutover.json'
REGISTRY = 'registration-registry.json'


def load_optional(path, default):
    if not path.exists(): return default
    return sweep.load_json(path)[0]


def atomic(path, data):
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()


def table(col, cells):
    return ('| ' + ' | '.join(col) + ' |\n|' + '---|' * len(col) + '\n| ' + ' | '.join(cells) + ' |\n').encode()


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def native_binding(meta):
    if 'non_model' in meta:
        return
    proof = sweep.record(meta['native_validation'])
    sweep.require(proof.get('schema') == 'epyc.registration_native_validation.v1', 'invalid native validation receipt')
    sweep.require(proof.get('recipe') == meta['recipe'] and proof.get('anchors') == meta['session']['anchors'] and
                  proof.get('server') == meta.get('server'), 'native validation records differ')
    sweep.text(proof.get('validator_source'))
    if proof.get('server_custody'):
        custody = proof['server_custody']
        sweep.require(isinstance(custody, dict) and set(custody) == {'path', 'sha256'} and Path(custody['path']).is_absolute(), 'server custody evidence required')
        sweep.require(sha_bytes(sweep.read_regular(custody['path'])) == sweep.sha(custody['sha256']), 'server custody evidence changed')


def checked_catalog(cat, candidate):
    """Unvalidated peer provenance stays UNKNOWN; the candidate must validate."""
    rows = {}
    for rid, meta in cat['rows'].items():
        try: native_binding(meta)
        except (sweep.Invalid, KeyError, TypeError, OSError, ValueError):
            if rid == candidate: raise
            continue
        rows[rid] = meta
    return {'schema': cat['schema'], 'rows': rows}


def finish_transaction(flags, journal):
    """Replay only recorded generations; a conflict or stale provenance leaves pending."""
    allowed = {REGISTRY, CAT, RECEIPTS, 'FILLERS.md', 'ws58-quarters-20261027.queue',
               'ws58-quarters-20261027.queue.done', 'ws58-gpu.queue', 'ws58-gpu.queue.held'}
    entries = journal['files']
    sweep.require(journal.get('schema') == 'epyc.registration_pending.v2' and set(entries) <= allowed, 'bad journal')
    for name, entry in entries.items():
        path = flags / name
        current = sha_bytes(sweep.read_regular(path)) if path.exists() else None
        after = base64.b64decode(entry['after'], validate=True)
        sweep.require(sha_bytes(after) == entry['after_sha256'], 'journal corrupt')
        sweep.require(current in (entry['before_sha256'], entry['after_sha256']), 'transaction generation conflict: ' + name)
    for name, entry in entries.items():
        atomic(flags / name, base64.b64decode(entry['after'], validate=True))
    # Validate the reconstructed candidate and native references before release.
    col, rows, _ = sweep.rows(flags / 'FILLERS.md')
    cat, _ = sweep.load_json(flags / CAT)
    rid = journal['id']
    native_binding(cat['rows'][rid])
    result = sweep.sweep(rows, rows[rid], col, checked_catalog(cat, rid))
    sweep.require(result['allowed'], 'recovered registration no longer permitted')
    receipts, _ = sweep.load_json(flags / RECEIPTS)
    sweep.require(receipts['rows'][rid] == {'row_sha256': sweep.digest(rows[rid]), 'metadata_sha256': sweep.digest(cat['rows'][rid])}, 'recovery receipt mismatch')
    os.unlink(flags / PENDING)
    fd = os.open(flags, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return result


def recover(flags):
    journal, _ = sweep.load_json(flags / PENDING)
    return finish_transaction(flags, journal)


def abort(flags):
    journal, _ = sweep.load_json(flags / PENDING)
    sweep.require(journal.get('schema') == 'epyc.registration_pending.v2', 'unsupported abort journal')
    allowed = {REGISTRY, CAT, RECEIPTS, 'FILLERS.md', 'ws58-quarters-20261027.queue',
               'ws58-quarters-20261027.queue.done', 'ws58-gpu.queue', 'ws58-gpu.queue.held'}
    entries = journal['files']
    sweep.require(REGISTRY in entries and set(entries) <= allowed, 'bad abort journal')
    abort_registry = base64.b64decode(journal['abort_registry'], validate=True)
    abort_hash = sha_bytes(abort_registry)
    original_registry = json.loads(base64.b64decode(entries[REGISTRY]['before'], validate=True))
    revised_registry = json.loads(abort_registry)
    sweep.require({k: v for k, v in original_registry.items() if k != 'generation'} ==
                  {k: v for k, v in revised_registry.items() if k != 'generation'} and
                  original_registry.get('generation') != revised_registry.get('generation'), 'invalid abort registry')
    for name, entry in entries.items():
        path = flags / name
        current = sha_bytes(sweep.read_regular(path)) if path.exists() else None
        expected = [entry['before_sha256'], entry['after_sha256']]
        if name == REGISTRY: expected.append(abort_hash)
        sweep.require(current in expected, 'abort generation conflict: ' + name)
        before = None if entry['before'] is None else base64.b64decode(entry['before'], validate=True)
        sweep.require((sha_bytes(before) if before is not None else None) == entry['before_sha256'], 'corrupt before image')
    for name, entry in entries.items():
        path = flags / name
        before = None if entry['before'] is None else base64.b64decode(entry['before'], validate=True)
        if name == REGISTRY: atomic(path, abort_registry)
        elif before is None:
            if path.exists(): os.unlink(path)
        else: atomic(path, before)
    for name, entry in entries.items():
        path = flags / name
        actual = sha_bytes(sweep.read_regular(path)) if path.exists() else None
        sweep.require(actual == (abort_hash if name == REGISTRY else entry['before_sha256']), 'abort verification failed: ' + name)
    fd = os.open(flags, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd); os.unlink(flags / PENDING); os.fsync(fd)
    finally: os.close(fd)
    return {'restored': journal['id'], 'generation_rotated': True}


def state(flags):
    if (flags / PENDING).exists(): raise sweep.Invalid('unfinished-registration-recovery-required')
    cat = load_optional(flags / CAT, {'schema': sweep.SCHEMA, 'rows': {}})
    receipts = load_optional(flags / RECEIPTS, {'schema': 'epyc.registration_receipts.v1', 'rows': {}})
    registry, _ = sweep.load_json(flags / REGISTRY)
    legacy_raw = sweep.read_regular(flags / LEGACY)
    sweep.require(registry.get('schema') == 'epyc.registration_registry.v1' and isinstance(registry.get('enrolled'), list), 'bad registry')
    sweep.require(registry.get('legacy_sha256') == hashlib.sha256(legacy_raw).hexdigest(), 'legacy snapshot changed')
    sweep.require(receipts.get('schema') == 'epyc.registration_receipts.v1' and isinstance(receipts.get('rows'), dict), 'bad receipts')
    return cat, receipts, registry


def check_queue_args(flags, col, cells, pid, window, gib, regions, lane, minimum):
    violations = sweep.vf.check_row(cells, col, set(), pid_alive=lambda *_: True)
    sweep.require(not violations, 'invalid normalized row: ' + '; '.join(violations))
    sweep.require(window.isdecimal() and int(window) > 0, 'invalid queue window')
    sweep.require(re.fullmatch(r'\d+(?:\.\d+)?', gib) is not None and float(gib) > 0, 'invalid queue RAM')
    sweep.require(lane in ('cpu', 'gpu'), 'invalid lane')
    tokens = regions.split(',')
    sweep.require(all(re.fullmatch(r'(?:q[0-3]|mi210_0|\d+(?:-\d+)?)', x) for x in tokens), 'invalid region syntax')
    sweep.require(('mi210_0' in tokens) == (lane == 'gpu'), 'lane/region mismatch')
    if lane == 'gpu': sweep.require(minimum.isdecimal() and int(minimum) > 0, 'invalid GPU minimum')
    # Feed the existing dry-run row parser a private serialization of the single
    # already-parsed candidate; never re-open the mutable caller's input.
    with tempfile.NamedTemporaryFile(dir=flags, prefix='.rowcheck-', delete=False) as f:
        name = f.name; f.write(table(col, cells))
    try: native = dryrun.row_record(Path(name), cells[0])
    finally: os.unlink(name)
    sweep.require(native['requested'] == int(window), 'requested window differs from row')
    sweep.require(native['ram'] == float(gib), 'queue RAM differs from row')
    sweep.require(native['cpus'].issubset(dryrun.grant_cpus(regions)), 'queue regions do not cover claimed CPUs')
    native_min = dryrun.seconds(cells[col['min window']])
    sweep.require(int(window) >= native_min + 300, 'queue window below minimum plus margin')
    if lane == 'gpu': sweep.require(int(minimum) == native_min, 'GPU minimum differs from row')


def register(flags, candidate, meta_path, pid, window, gib, regions, lane='cpu', minimum='', regex=''):
    cat, receipts, registry = state(flags)
    meta, _ = sweep.load_json(meta_path)
    col, candidates, _ = sweep.rows(candidate)
    sweep.require(len(candidates) == 1, 'expected one candidate')
    rid, cells = next(iter(candidates.items()))
    sweep.require(isinstance(meta, dict), 'metadata object required')
    native_binding(meta)
    sweep.require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', rid) is not None, 'unsafe row id')
    sweep.require(not os.path.lexists(flags / 'grants' / (rid + '.grant')), 'active or dangling grant for row')
    sweep.require(pid.isdecimal() and re.search(r'(?<![\w])pid=' + re.escape(pid) + r'\b', cells[2]) is not None, 'candidate must be normalized with exact launcher pid')
    sweep.require(all(x and '|' not in x and '\n' not in x for x in (rid, pid, window, gib, regions)), 'invalid queue fields')
    cat['rows'][rid] = meta
    check_queue_args(flags, col, cells, pid, window, gib, regions, lane, minimum)
    queue_col, existing, _ = sweep.rows(flags / 'FILLERS.md')
    sweep.require(queue_col == col, 'candidate/queue header differs')
    result = sweep.sweep(existing, cells, col, checked_catalog(cat, rid))
    sweep.require(result['allowed'], 'unresolved peer: ' + ', '.join(result['problems']))
    raw = sweep.read_regular(flags / 'FILLERS.md').decode('utf-8')
    lines = raw.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.startswith('| ' + rid + ' |')]
    sweep.require(len(indices) <= 1, 'duplicate row')
    rowline = '| ' + ' | '.join(cells) + ' |\n'
    if indices: lines[indices[0]] = rowline
    else:
        candidates_idx = [i for i, line in enumerate(lines) if line.startswith('| codex-ni-')]
        sweep.require(bool(candidates_idx), 'insertion anchor absent')
        lines.insert(candidates_idx[-1] + 1, rowline)
    receipts['rows'][rid] = {'row_sha256': sweep.digest(cells), 'metadata_sha256': sweep.digest(meta)}
    sweep.require(lane in ('cpu', 'gpu'), 'invalid lane')
    sweep.require(lane == 'cpu' or all(x and '|' not in x and '\n' not in x for x in (minimum, regex)), 'invalid gpu queue fields')
    q = flags / ('ws58-quarters-20261027.queue' if lane == 'cpu' else 'ws58-gpu.queue')
    done = flags / ('ws58-quarters-20261027.queue.done' if lane == 'cpu' else 'ws58-gpu.queue.held')
    queue = [line for line in q.read_text().splitlines() if not line.startswith(rid + '|')]
    queue.append('|'.join((rid, pid, window, gib, regions) if lane == 'cpu' else (rid, pid, window, minimum, gib, regex, regions)))
    done_lines = [line for line in done.read_text().splitlines() if line != rid]
    registry['enrolled'] = sorted(set(registry['enrolled']) | {rid})
    registry['generation'] = os.urandom(16).hex()
    files = {REGISTRY: encoded(registry), CAT: encoded(cat), RECEIPTS: encoded(receipts),
             'FILLERS.md': ''.join(lines).encode(), q.name: ('\n'.join(queue) + '\n').encode(),
             done.name: ('\n'.join(done_lines) + ('\n' if done_lines else '')).encode()}
    entries = {}
    for name, data in files.items():
        path = flags / name
        before = sweep.read_regular(path) if path.exists() else None
        entries[name] = {'before_sha256': sha_bytes(before) if before is not None else None,
                         'before': base64.b64encode(before).decode() if before is not None else None,
                         'after_sha256': sha_bytes(data), 'after': base64.b64encode(data).decode()}
    abort_registry, _ = sweep.load_json(flags / REGISTRY)
    abort_registry['generation'] = os.urandom(16).hex()
    journal = {'schema': 'epyc.registration_pending.v2', 'id': rid, 'files': entries,
               'abort_registry': base64.b64encode(encoded(abort_registry)).decode()}
    journal_bytes = encoded(journal)
    sweep.require(len(journal_bytes) <= sweep.MAX_BYTES, 'transaction journal exceeds recovery read limit')
    atomic(flags / PENDING, journal_bytes)
    return finish_transaction(flags, journal)


def grant(flags, rid):
    cat, receipts, registry = state(flags)
    entry = receipts['rows'].get(rid)
    if entry is None:
        sweep.require(rid not in registry['enrolled'] and rid not in cat.get('rows', {}), 'enrolled row missing receipt')
        legacy, _ = sweep.load_json(flags / LEGACY)
        sweep.require(legacy.get('schema') == 'epyc.registration_legacy_cutover.v1', 'bad legacy snapshot')
        col, rows, _ = sweep.rows(flags / 'FILLERS.md')
        sweep.require(rid in rows and legacy.get('rows', {}).get(rid) == sweep.digest(rows[rid]), 'missing receipt or changed legacy row')
        return {'legacy_unbound': True, 'row': rid, 'owner_adopted': False, 'all_producers_bound': False}
    col, rows, _ = sweep.rows(flags / 'FILLERS.md')
    sweep.require(rid in rows and rid in cat['rows'], 'missing registered row or metadata')
    cells = rows[rid]; meta = cat['rows'][rid]
    native_binding(meta)
    sweep.require(entry == {'row_sha256': sweep.digest(cells), 'metadata_sha256': sweep.digest(meta)}, 'stale receipt')
    result = sweep.sweep(rows, cells, col, checked_catalog(cat, rid))
    sweep.require(result['allowed'], 'unresolved peer: ' + ', '.join(result['problems']))
    result['legacy_unbound'] = False
    return result

def cutover(flags):
    sweep.require(not (flags / LEGACY).exists(), 'cutover snapshot already exists')
    sweep.require(not (flags / REGISTRY).exists() and not (flags / PENDING).exists(), 'cutover already started')
    _, rows, queue_sha = sweep.rows(flags / 'FILLERS.md')
    snapshot = {'schema': 'epyc.registration_legacy_cutover.v1', 'queue_sha256': queue_sha,
                'rows': {rid: sweep.digest(cells) for rid, cells in rows.items()}}
    raw = encoded(snapshot)
    atomic(flags / PENDING, encoded({'schema': 'epyc.registration_pending.v1', 'id': 'cutover'}))
    atomic(flags / LEGACY, raw)
    atomic(flags / REGISTRY, encoded({'schema': 'epyc.registration_registry.v1', 'legacy_sha256': hashlib.sha256(raw).hexdigest(), 'enrolled': []}))
    os.unlink(flags / PENDING)
    fd = os.open(flags, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return snapshot


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--flags', type=Path, required=True)
    sub = p.add_subparsers(dest='command', required=True)
    gr = sub.add_parser('grant'); gr.add_argument('--id', required=True)
    rh = sub.add_parser('row-hash'); rh.add_argument('--id', required=True)
    a = p.parse_args()
    if a.command == 'grant': result = grant(a.flags, a.id)
    elif a.command == 'row-hash':
        _, rows, _ = sweep.rows(a.flags / 'FILLERS.md')
        print(sweep.digest(rows[a.id]) + ':' + sha_bytes(sweep.read_regular(a.flags / REGISTRY))); return
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    try: main()
    except (sweep.Invalid, sweep.vf.Malformed, dryrun.Refused, KeyError, TypeError, OSError, ValueError) as e:
        print('refuse: ' + str(e), file=sys.stderr); sys.exit(2)
