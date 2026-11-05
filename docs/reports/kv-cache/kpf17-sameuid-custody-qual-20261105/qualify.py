#!/usr/bin/env python3
"""Bounded model-free probes of the retained KPF-17 map validator."""
import hashlib
import importlib.util
import json
import mmap
import os
from pathlib import Path
import secrets
import tempfile
import threading

ROOT = Path(__file__).resolve().parent
ROW = 'kvfork17-sameuid-custody-qual-20261105'
CUSTODY = 'ab6d10e509d7483963a39b0da2caccab4ac8b85ee33a9e0b117107601d8d8702'
BINDING = '5b56f806a39f24a2f68dafe147b5b56295a2975fea3914bca2a388e571b16b82'
NAMES = ('libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libllama.so', 'libllama-common.so')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def need(condition, message):
    if not condition:
        raise ValueError(message)

def stop():
    need(not (ROOT/'STOP').exists(), 'STOP requested')

def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        tmp = Path(stream.name)
    try:
        stop()
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)

def inputs():
    seal = json.loads((ROOT/'packet-seal.json').read_text())
    for name, expected in seal['files'].items():
        need(sha(ROOT/name) == expected, 'packet input changed: '+name)
    need(sha(ROOT/'custody.py') == CUSTODY, 'retained custody source changed')
    need(sha(ROOT/'binding.json') == BINDING, 'retained r5 binding changed')
    binding = json.loads((ROOT/'binding.json').read_text())
    need(binding['runner_files']['custody.py'] == CUSTODY, 'r5 binding mismatch')
    spec = importlib.util.spec_from_file_location('retained_kpf17_custody', ROOT/'custody.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def probe(custody, parent, window):
    with tempfile.TemporaryDirectory(prefix=window+'-', dir=parent) as td:
        fixture = Path(td)
        paths = []
        lines = []
        expected = {}
        for i, name in enumerate(NAMES):
            path = fixture/name
            path.write_bytes(b'A'*4096)
            stat = path.stat()
            paths.append(path)
            lines.append(f'{0x100000+i*4096:x}-{0x101000+i*4096:x} r-xp 00000000 {os.major(stat.st_dev):x}:{os.minor(stat.st_dev):x} {stat.st_ino} {path}')
            expected[str(path)] = sha(path)
        target = paths[0]
        alias = fixture/'same-uid-writer-alias'
        os.link(target, alias)
        before = target.stat()
        baseline = custody.validate_maps(lines, expected)
        need(len(baseline) == 5, 'incomplete accepted baseline')
        events = ['retained_validate_maps_accepted']
        ready = threading.Event()
        done = threading.Event()
        errors = []
        def writer():
            try:
                need(ready.wait(2), 'writer barrier timeout')
                need(os.getuid() == alias.stat().st_uid, 'writer UID differs from fixture owner')
                with alias.open('r+b', buffering=0) as stream:
                    stream.write(b'B'*4096)
                    os.fsync(stream.fileno())
                events.append('same_uid_alias_inplace_write_complete')
            except Exception as exc:
                errors.append(repr(exc))
            finally:
                done.set()
        # mmap is a private fixture data witness, never an ELF/native-loader claim.
        with target.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            worker = threading.Thread(target=writer)
            worker.start()
            ready.set()
            finished = done.wait(3)
            worker.join(3)
            need(finished and not worker.is_alive() and not errors, 'writer failed: '+repr(errors))
            after = target.stat()
            need((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino), 'overwrite replaced inode')
            visible = mapped[:] == b'B'*4096
            need(visible, 'mapped mutation visibility inconclusive')
            if window == 'before-revalidation':
                try:
                    custody.validate_maps(lines, expected)
                except ValueError as exc:
                    reason = str(exc)
                    need(reason.startswith('unattested mapped library:'), 'unexpected refusal: '+reason)
                    response = 'REFUSED'
                    events.append('retained_validate_maps_refused')
                else:
                    response, reason = 'ACCEPTED', 'unsafe acceptance after mutation'
            else:
                response, reason = 'NO_CHECK_AFTER_MUTATION', 'final accepted check precedes the synchronized write'
                events.append('mapped_fixture_read_mutated_bytes_without_revalidation')
        return {'window': window, 'baseline_library_count': len(baseline), 'writer_uid': os.getuid(),
                'owner_uid': before.st_uid, 'same_inode': True, 'hardlink_count': after.st_nlink,
                'mapped_mutation_visible': visible, 'validator_response': response, 'reason': reason,
                'before_sha256': expected[str(target)], 'after_sha256': sha(target), 'events': events}

def validate_result(path):
    inputs()
    result = json.loads(Path(path).read_text())
    context = json.loads((ROOT/'out/attempt.json').read_text())
    need(result['schema'] == 'kpf17.sameuid-custody-qualification.v1', 'result schema')
    need(result['row_id'] == ROW and result['attempt_nonce'] == context['nonce'], 'attempt binding')
    need(result['context_sha256'] == sha(ROOT/'out/attempt.json'), 'context digest')
    need(result['packet_seal_sha256'] == sha(ROOT/'packet-seal.json'), 'input digest')
    evidence = ROOT/'out'/context['nonce']/'cases.json'
    need(result['evidence_path'] == str(evidence) and result['evidence_sha256'] == sha(evidence), 'evidence binding')
    cases = json.loads(evidence.read_text())
    need(result['cases'] == cases and result['case_count'] == 2, 'case binding')
    need(cases[0]['validator_response'] == 'REFUSED', 'pre-revalidation unsafe or inconclusive')
    need(cases[1]['validator_response'] == 'NO_CHECK_AFTER_MUTATION', 'wrong post-check window')
    need(all(c['same_inode'] and c['mapped_mutation_visible'] and c['owner_uid'] == c['writer_uid'] for c in cases), 'case evidence missing')
    need(result['status'] == 'UNSAFE' and result['qualification_status'] == 'COMPLETE', 'unsafe outcome suppressed')
    stop()

def run():
    stop()
    custody = inputs()
    dryrun = os.environ.get('FILLER_DRYRUN_RESULT_PATH')
    if not dryrun:
        need(os.environ.get('FILLER_ID') == ROW, 'full run requires matching FILLER_ID')
    # Publisher smoke never changes full-run attempt/result eligibility.
    out = ROOT/('smoke-out' if dryrun else 'out')
    out.mkdir(exist_ok=True)
    (out/'RESULT.json').unlink(missing_ok=True)
    nonce = secrets.token_hex(24)
    attempt = out/nonce
    attempt.mkdir(mode=0o700)
    context = {'row_id': ROW, 'nonce': nonce, 'kind': 'model-free-smoke' if dryrun else 'full',
               'packet_seal_sha256': sha(ROOT/'packet-seal.json')}
    atomic(out/'attempt.json', context)
    try:
        cases = [probe(custody, attempt, window) for window in ('before-revalidation', 'after-final-check')]
        stop()
        atomic(attempt/'cases.json', cases)
        status = 'UNSAFE' if cases[1]['mapped_mutation_visible'] else 'INCONCLUSIVE'
        result = {'schema': 'kpf17.sameuid-custody-qualification.v1', 'row_id': ROW,
                  'status': status, 'qualification_status': 'COMPLETE', 'case_count': len(cases), 'unit_key': 'case_count',
                  'cases': cases, 'attempt_nonce': nonce, 'context_sha256': sha(out/'attempt.json'),
                  'packet_seal_sha256': sha(ROOT/'packet-seal.json'), 'custody_source_sha256': CUSTODY,
                  'result_kind': context['kind'], 'evidence_path': str(attempt/'cases.json'),
                  'evidence_sha256': sha(attempt/'cases.json'),
                  'limits': 'Actual retained validate_maps only, synthetic proc-map lines and non-ELF fixture mmap; no build_identity, native loading, model, inference, or whole-chain safety claim. UNSAFE means same-UID hardlink writes remain visible after the final accepted check.'}
    except Exception as exc:
        result = {'schema': 'kpf17.sameuid-custody-qualification.v1', 'row_id': ROW, 'status': 'INVALID',
                  'qualification_status': 'INCONCLUSIVE', 'error': repr(exc), 'case_count': 0,
                  'unit_key': 'case_count', 'attempt_nonce': nonce}
    destination = Path(dryrun) if dryrun else out/'RESULT.json'
    atomic(destination, result)
    print(json.dumps({'progress': 'custody-qualification-finished', 'case_count': result['case_count'], 'status': result['status']}), flush=True)
    return 0 if result['qualification_status'] == 'COMPLETE' else 1

if __name__ == '__main__':
    raise SystemExit(run())
