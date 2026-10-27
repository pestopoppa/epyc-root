#!/usr/bin/env python3
"""Native G1 finalization; uses existing carrier + shared grade, never a private ladder."""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('kpf62_original', BASE / 'deps/finalizer_v2.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
Refusal = legacy.Refusal
sha = legacy.file_sha256
utc = legacy.parse_utc

def load(path):
    def duplicate(items):
        out = {}
        for key, value in items:
            if key in out:
                raise Refusal(f'duplicate JSON key {key}')
            out[key] = value
        return out
    return json.loads(Path(path).read_text(), object_pairs_hook=duplicate,
                      parse_constant=lambda x: (_ for _ in ()).throw(Refusal(f'nonfinite JSON {x}')))

def verify_sources():
    assembly = load(BASE / 'assembly.json')
    candidate = Path(assembly['candidate'])
    root = Path(assembly['root_candidate'])
    from prepare_candidate import CHAMPION, ROOT
    for path, pin in ((candidate, CHAMPION), (root, ROOT)):
        actual = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != pin:
            raise Refusal(f'source HEAD drift: {path}')
    for name, digest in assembly['files'].items():
        if sha(candidate / name) != digest:
            raise Refusal(f'producer source drift: {name}')
    status = subprocess.check_output(['git', '-C', str(candidate), 'status', '--porcelain', '--untracked-files=all'], text=True)
    if {line[3:] for line in status.splitlines()} != set(assembly['files']):
        raise Refusal('candidate changed outside exact reviewed instrument/API files')
    root_status = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=all'], text=True)
    if root_status.strip():
        raise Refusal('ROOT reader checkout must be clean')
    adapter = root / 'scripts/vidya/adapters/chunk_kv.py'
    baseline = subprocess.check_output(['git', '-C', str(root), 'show', f'{ROOT}:scripts/vidya/adapters/chunk_kv.py'])
    if b'no_protocol_ids=("unknown",)' not in baseline or adapter.read_bytes() != baseline:
        raise Refusal('pinned reader lacks unknown-protocol correction')
    legacy.ROOT_WT = root
    legacy.ROOT_COMMIT = ROOT
    legacy.PRODUCER_WT = candidate
    legacy.PRODUCER_COMMIT = CHAMPION
    return assembly

def check(record, raw):
    assembly = verify_sources()
    capture = record['capture']
    if record['source_assembly_sha256'] != sha(BASE / 'assembly.json'):
        raise Refusal('invocation source assembly mismatch')
    if record['source_digest'] != assembly['source_digest']:
        raise Refusal('invocation source digest mismatch')
    if capture['n_chunk'] != 24 or capture['environment'].get('CKV_N_CHUNK') != '24':
        raise Refusal('this predeclaration requires exactly 24 chunk positions')
    if capture['environment'].get('CKV_SKIP_K_GATE') is not None:
        # The original producer treats even "0" as set; do not allow its false friend.
        raise Refusal('CKV_SKIP_K_GATE must be absent, including no value "0"')
    actual = datetime.now(timezone.utc)
    start, end = utc(record['grant']['start_utc'], 'grant start'), utc(record['grant']['end_utc'], 'grant end')
    if not start <= actual <= end:
        raise Refusal('finalization outside live recorded grant bounds')
    if abs((actual - utc(record['finalized_at_utc'], 'finalized_at')).total_seconds()) > 30:
        raise Refusal('finalized timestamp is not current')
    grant = Path(record['grant']['path'])
    if not grant.is_file() or grant.is_symlink() or sha(grant) != record['grant']['sha256']:
        raise Refusal('canonical grant bytes unavailable or changed')
    if grant.parent != Path('/mnt/raid0/llm/tmp/compute-flags/grants'):
        raise Refusal('noncanonical grant path')
    expected = 'regions={} start={} end={}\n'.format(record['grant']['regions'], record['grant']['start_utc'], record['grant']['end_utc'])
    if grant.read_text() != expected:
        raise Refusal('grant fields do not match canonical bytes')
    if list(Path('/mnt/raid0/llm/tmp/compute-flags').glob('HOLD_*')):
        raise Refusal('canonical HOLD present')
    for artifact in record['artifacts']:
        path = Path(artifact['path'])
        if not path.is_file() or sha(path) != artifact['sha256']:
            raise Refusal(f'provenance artifact changed: {path}')
    for required in ('binary_elf', 'generator_elf', 'libraries', 'build_receipt', 'authority',
                     'native_stdout', 'native_stderr', 'cpu_before', 'cpu_after', 'native_controls'):
        if required not in {item['kind'] for item in record['artifacts']}:
            raise Refusal(f'missing native provenance artifact kind: {required}')
    if record['lifecycle']['child_drained'] is not True:
        raise Refusal('native child not drained')
    if record['lifecycle']['timed_out'] is not False:
        raise Refusal('native capture timeout')
    if record['context'] != {'n_ctx_seq': 1024, 'n_ctx': 8192, 'n_seq_max': 8, 'n_batch': 512, 'n_ubatch': 512,
                             'n_suffix': 6, 'deltas': [1, 17, 300], 'seed': 1234}:
        raise Refusal('native fixed context/predeclaration mismatch')
    return assembly

def finalize(raw, invocation, out):
    record = load(invocation)
    check(record, raw)
    # Original invocation validation binds model/binary/raw, argv, env, complete
    # 18 groups and timestamps. It does not grant compute authority.
    legacy.read_invocation(Path(invocation), Path(raw))
    groups = legacy.validate_capture_rows(legacy.read_rows(Path(raw)), n_chunk=24)
    if sum(map(len, groups.values())) != 324:
        raise Refusal('native complete position count must be exactly 324')
    if out.exists():
        raise Refusal('refusing output overwrite')
    temporary = out.with_name(out.name + '.partial')
    if temporary.exists():
        raise Refusal('prior partial package requires diagnosis')
    temporary.mkdir(parents=True)
    # Keep failures and original bytes. An acceptance file exists only after all
    # checks, shared-reader round trips and artifact hashes have succeeded.
    try:
        for source, name in ((raw, 'g1-position.jsonl'), (invocation, 'invocation.json'),
                             (BASE / 'assembly.json', 'source-assembly.json')):
            shutil.copyfile(source, temporary / name)
        artifacts = temporary / 'provenance'
        artifacts.mkdir()
        retained = []
        for i, item in enumerate(record['artifacts']):
            target = artifacts / f'{i:03d}-{item["kind"]}'
            shutil.copyfile(item['path'], target)
            if sha(target) != item['sha256']:
                raise Refusal('provenance copy changed')
            retained.append({**item, 'packaged_relative_path': str(target.relative_to(temporary))})
        sys.path.insert(0, str(legacy.ROOT_WT / 'scripts/vidya'))
        import claim_tuple
        from adapters import chunk_kv
        measurements = legacy.build_measurements(record, groups)
        # Detail is already a retained carrier field. Preserve the entire native
        # envelope in every tuple without changing carrier identity or any ladder.
        detail = json.dumps({'scope': 'generated tiny correctness only', 'invocation': record,
                             'packaged_artifacts': retained, 'unit_context': 'native f32 sums; NMSE/fraction lower better',
                             'protocol_status': 'unknown; projection uses no protocol warrant'}, sort_keys=True)
        for m in measurements:
            m['detail'] = detail
            m['served_pin']['kernel_ref'] += ';source_digest=' + record['source_digest']
        # Use final path in native result locators, but publish atomically only
        # after validation. Writer hashes bytes currently at final path, so rename
        # the complete staging directory first; any failure removes acceptance.
        temporary.rename(out)
        sidecar = chunk_kv.write_belief_measurements(out, run_id=record['run_id'],
            producer='test-chunk-kv@' + record['source_digest'], results_path=out / 'g1-position.jsonl',
            measurements=measurements, protocol_id='unknown', emitted_at=record['finalized_at_utc'])
        native = chunk_kv.native_rows(sidecar)
        if len(native) != 27:
            raise Refusal('expected 27 shared carrier rows')
        tuples, grades = [], []
        for n in native:
            tup = chunk_kv.project(n)
            if tup.extra.get('detail') != detail or tup.protocol_id:
                raise Refusal('shared projection dropped provenance or invented protocol')
            q, t, reasons = claim_tuple.grade(tup)
            tuples.append(dataclasses.asdict(tup))
            grades.append({'measurement_id': tup.measurement_id, 'quality': q, 'truth': t, 'reasons': reasons})
        (out / 'claim-tuples.json').write_text(json.dumps(tuples, sort_keys=True, indent=2) + '\n')
        (out / 'grades.json').write_text(json.dumps(grades, sort_keys=True, indent=2) + '\n')
        acceptance = {'schema': 'epyc.kpf62.g1_finalized.v3', 'position_rows': 324, 'carrier_rows': 27,
                      'raw_sha256': sha(out / 'g1-position.jsonl'), 'sidecar_sha256': sha(sidecar),
                      'invocation_sha256': sha(out / 'invocation.json'), 'finalizer_sha256': sha(Path(__file__)),
                      'protocol_id': '', 'scope': 'generated tiny native G1 only; no G3 corpus/production claim'}
        (out / 'ACCEPTED.json').write_text(json.dumps(acceptance, sort_keys=True, indent=2) + '\n')
        return out
    except Exception as exc:
        failed = out if out.exists() else temporary
        (failed / 'REFUSED.txt').write_text(str(exc) + '\n')
        (failed / 'ACCEPTED.json').unlink(missing_ok=True)
        (failed / 'chunk_kv.beliefs.jsonl').unlink(missing_ok=True)
        raise

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--invocation', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    try:
        print(finalize(a.raw, a.invocation, a.out))
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as e:
        print('REFUSE ' + str(e), file=sys.stderr)
        raise SystemExit(2)
