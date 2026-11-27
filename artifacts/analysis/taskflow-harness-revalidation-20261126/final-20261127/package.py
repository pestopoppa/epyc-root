"""Explicit allowlist archival only: no inference, tests, commits or index writes."""
from pathlib import Path
import gzip
import hashlib
import json

BASE = Path('/mnt/raid0/llm/tmp/ws58-a3b-revalidate-20261126')
DEST = Path('/mnt/raid0/llm/tmp/ws58-a3b-finish-20261126/artifacts/analysis/taskflow-harness-revalidation-20261126/final-20261127')
sha = lambda data: hashlib.sha256(data).hexdigest()
items = {}


def add(source, target, compress=False):
    source = Path(source)
    assert source.is_file() and not source.is_symlink(), source
    assert target not in items, (target, source)
    items[target] = {'source': source, 'compress': compress}


def top(root, target):
    root = Path(root)
    if not root.is_dir():
        return
    for source in sorted(root.iterdir()):
        if source.is_file() and not source.is_symlink() and source.suffix in ['.py', '.json', '.md', '.sha256']:
            compress = source.suffix == '.json' and source.stat().st_size >= 65536
            add(source, target + '/' + source.name + ('.gz' if compress else ''), compress)


perf = BASE / 'performance/multi-epoch-v3'
paid = BASE / 'coverage/paid-call-accounting'
export = BASE / 'coverage/final-export'
add(perf / 'snapshot-persistent-final-01/REPORT.json', 'performance/REPORT.json.gz', True)
add(perf / 'snapshot-persistent-final-01/REPORT.md', 'performance/REPORT.md')
for name in ['REQUESTS.csv', 'TASKS.csv', 'SUMMARY.json', 'README.md']:
    add(export / 'files-v2' / name, 'performance/export/' + name)
for name in ['export.py', 'CSV-FORMAT-VALIDATION.json', 'OWNER-QUALITY-FINAL-ADDENDUM.json']:
    add(export / name, 'performance/export/' + name)
for name in ['collect_multi.py', 'prepare_persistent_inputs.py', 'INPUTS-PERSISTENT-FINAL-v2.json', 'FINAL-DESCRIPTOR-VALIDATION-v2.json', 'CALLBACK-LAYOUT-SOURCE.json']:
    source = perf / name
    compress = source.suffix == '.json' and source.stat().st_size >= 65536
    add(source, 'performance/collector/' + name + ('.gz' if compress else ''), compress)
add(perf.parent / 'collect_perf.py', 'performance/collector/collect_perf.py')
for name in ['ACCOUNTING.json', 'SUMMARY.md', 'METADATA.json', 'FINAL-SEAL.json', 'OWNER-QUALITY-ADDENDUM.json']:
    add(paid / 'snapshot-final-40' / name, 'paid-final-40/' + name + ('.gz' if name == 'ACCOUNTING.json' else ''), name == 'ACCOUNTING.json')
add(export / 'MANAGER-GOAL-COUNTER.json', 'paid-final-40/MANAGER-GOAL-COUNTER.json')
for name in ['collect.py', 'SOURCE-LOCK.json', 'SOURCE-SEAL.json', 'CONTROL.json', 'README.md']:
    add(paid / name, 'paid-final-40/collector/' + name)
for name in ['RECEIPT.json', 'STDOUT.txt', 'REPORT.md']:
    add(BASE / 'coverage/canonical-checker-validation' / name, 'canonical-47/' + name)
for root in ['feedback-final-audit', 'completion-audit-final']:
    for source in sorted((BASE / root).iterdir()):
        if source.is_file() and source.suffix in ['.py', '.json', '.md', '.sha256', '.txt']:
            add(source, 'audits/' + root + '/' + source.name)
for source in sorted((BASE / 'quality-assessments/registry').glob('*.json')):
    add(source, 'owner-quality-registry/' + source.name)
for name in ['COST-QUALIFICATION.json', 'REVIEW.json']:
    add(BASE / 'source-review-boundary-w66' / name, 'owner-quality-registry/cpu-w66-source/' + name)
serving = BASE / 'coverage/persistent-serving/runs/final-01'
for name in ['PRE-CLOSE.json', 'CLEANUP.json', 'READY.json', 'SERVING.json', 'GRANT.json', 'CONFIG-cpu.json', 'CONFIG-gpu.json']:
    add(serving / name, 'native-serving/' + name)
for side in ['cpu', 'gpu']:
    for name in ['proofs.json', 'server.json', 'live.json']:
        source = serving / f'out-{side}' / name
        if source.exists():
            add(source, f'native-serving/out-{side}/' + name)
coverage_roots = [
    'persistent-serving', 'persistent-callback', 'persistent-callback-admission-v2',
    'persistent-tu-on', 'persistent-tu-on-paid-2', 'persistent-w66-light',
    'persistent-w66-light-12', 'persistent-w66-light-identity', 'persistent-mm-mechanical',
    'persistent-mm-mechanical-watch', 'persistent-paw-paid-watch', 'persistent-paw-paid-watch-v2',
    'persistent-queue-watch', 'persistent-tu-off-auto-ci', 'cpu-tu-paid-final-review',
    'gpu-tu-autoci-final-review', 'gpu-tu-on-paid-diagnosis', 'gpu-tu-on-paid-final-review',
    'mm-final-scope-review', 'paw-clean-review', 'paw-clean-review-v2', 'paw-clean-review-v3',
    'w66-light-acceptance', 'w66-light-acceptance-v2', 'w66-light-brief', 'w66-light-brief-v2',
    'review-affinity-diagnostic', 'legacy-assisted-review', 'objective-followup',
    'mm-objective-followup', 'slot3-recovery',
]
for root in coverage_roots:
    top(BASE / 'coverage' / root, 'sources/coverage/' + root)
for root in sorted(BASE.glob('*-oracle-v*')):
    top(root, 'sources/checkers/' + root.name)
last_four = []
for family in ['gpu-tu-on-paid-final-review', 'mm-final-scope-review']:
    for seal in sorted((BASE / 'coverage' / family).glob('reviews/*/*/*/SEAL.json')):
        root = seal.parent
        record = json.loads(seal.read_text())
        run = Path(record['run'])
        relative = str(root.relative_to(BASE / 'coverage'))
        for name in ['SEAL.json', 'MAIN-APPROVAL.json', 'feedback.json', 'MAIN-AUDIT.json']:
            source = root / name
            if source.exists():
                add(source, 'last-four-paid/' + relative + '/' + name)
        for name in ['plan.json', 'measurement.json', 'execution.json', 'launch-start.json', 'prompt.md', 'assistance-accounting.json', 'events.jsonl']:
            source = run / name
            compress = name == 'events.jsonl' or (source.suffix == '.json' and source.stat().st_size >= 65536)
            add(source, 'last-four-paid/' + relative + '/run/' + name + ('.gz' if compress else ''), compress)
        last_four.append(str(root))
assert len(last_four) == 4, last_four
native = [
    ('tu-on-paid2', BASE / 'coverage/persistent-callback-admission-v2/runs/tu-on-paid-01/units/gpu-TU-GR-1-on-coding-paid-2', 'worker/candidate/candidate.patch'),
    ('w66-light-off-identity', BASE / 'coverage/persistent-w66-light-identity/runs/identity-01/units/gpu-DS41-W-66-off-common-light-v2-identity-1', 'independent/candidate.patch'),
]
for label, unit, patch in native:
    add(unit / patch, 'native-candidates/' + label + '/candidate.patch.gz', True)
    for name in ['RESULT.json', 'CALLBACK-RESULT.json', 'JOB.json', 'PROMPT.md', 'ORACLE.stdout.log', 'ORACLE.stderr.log', 'worker/receipt.json']:
        source = unit / name
        if source.exists():
            add(source, 'native-candidates/' + label + '/' + name.replace('worker/', 'worker-'))
for name in ['RESULT.json', 'stdout.log', 'stderr.log']:
    add(BASE / 'coverage/gpu-tu-on-paid-final-review/grade-v4' / name, 'native-candidates/tu-on-paid2/grade-v4/' + name)
for name in ['RESULT.json', 'REVIEW.json', 'SOURCE-CONTROL.sha256', 'grade_saved.py', 'observer.py']:
    add(BASE / 'w66-receipt-identity-followup-grade' / name, 'native-candidates/w66-light-off-identity/grade/' + name)

assert not DEST.exists(), 'never overwrite the owning publication package'
DEST.mkdir(parents=True)
records = []
for target, item in sorted(items.items()):
    source = item['source']
    data = source.read_bytes()
    stored = gzip.compress(data, compresslevel=9, mtime=0) if item['compress'] else data
    path = DEST / target
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stored)
    if not item['compress']:
        path.chmod(source.stat().st_mode & 0o777)
    records.append({'archive_path': target, 'source_path': str(source), 'encoding': 'gzip raw bytes, mtime=0' if item['compress'] else 'raw bytes', 'source_sha256': sha(data), 'archive_sha256': sha(stored), 'source_bytes': len(data), 'archive_bytes': len(stored)})
layout = {
    'schema': 'taskflow.final-explicit-allowlist.v1', 'records': records,
    'last_four_review_roots': last_four,
    'selection': 'Explicit files and extension-filtered TOPLEVEL files from named runtime/checker/review roots only',
    'exclusions': ['No lane/baseline/work/sandbox/refs/vendor copies', 'No raw wire body archives or duplicate request logs', 'No model or full source-tree copies', 'No other raw paid event logs beyond the last four'],
    'immutable_semantics': 'REPORT and ACCOUNTING compressed byte-for-byte; metrics accepted9 unchanged. Latest owner registry and final mechanical3 rejection addendum are separate quality authority. Original objective2 acceptance concerns another patch.',
    'commits_index_measurements_models': 'none; owning main reviews and commits',
}
(DEST / 'ARCHIVE-LAYOUT.json').write_text(json.dumps(layout, indent=2) + '\n')
(DEST / 'ARCHIVE-LAYOUT.md').write_text('''# Final revalidation archive

This explicit allowlist preserves final performance/paid accounting, exports, canonical47-test evidence, audits, owner quality records, serving shutdown/configuration proofs, source adapters and the requested last four reviews/native patches. ARCHIVE-LAYOUT.json maps copied/compressed files to their source and raw SHA-256.

REPORT.json.gz and paid ACCOUNTING.json.gz preserve exact raw JSON bytes. Metrics accepted9 and billed40 vectors remain immutable. Latest owner registry and OWNER-QUALITY-FINAL-ADDENDUM.json separately reject supplemental mechanical3 cap1; original objective2 acceptance concerns another patch. CPU W66 adoption preserves5663known generation plus1unknown receipt and adds no paid call.

CSV files are the LF field-equivalent files-v2 export with its validation receipt/exporter. Gzip files are raw-byte archives with mtime0; decompress before use. Last-four events retain exact JSONL bytes. No lane, baseline, work, sandbox, refs, vendor, raw wire body, model or full source-tree copies are present.

ARTIFACTS.sha256 hashes stored files. ARCHIVE-VALIDATION.json records decoded source-hash validation and size. Packaging ran no new tests, measurements, model/API calls or commits/index writes.

Next: owning main review and commit this package.
''')
(DEST / 'package.py').write_bytes(Path(__file__).read_bytes())
for r in records:
    stored = (DEST / r['archive_path']).read_bytes()
    decoded = gzip.decompress(stored) if r['encoding'].startswith('gzip') else stored
    assert sha(stored) == r['archive_sha256'] and sha(decoded) == r['source_sha256']
    assert sha(Path(r['source_path']).read_bytes()) == r['source_sha256'], ('source changed during packaging', r['source_path'])
files = [p for p in DEST.rglob('*') if p.is_file()]
size = sum(p.stat().st_size for p in files)
assert size < 10 * 1024 * 1024, ('archive should stay few MB', size)
validation = {'decoded_source_files_verified': len(records), 'stored_files_before_validation_manifest': len(files), 'total_bytes_before_validation_manifest': size, 'last_four_paid_review_roots': 4, 'forbidden_directory_copies': 0, 'raw_wire_copies': 0, 'all_decoded_source_hashes_match': True, 'all_source_hashes_rechecked_after_copy': True, 'tests_measurements_models_api_commits_index_writes': 0}
(DEST / 'ARCHIVE-VALIDATION.json').write_text(json.dumps(validation, indent=2) + '\n')
(DEST / 'ARTIFACTS.sha256').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(DEST)}\n' for p in sorted(DEST.rglob('*')) if p.is_file() and p.name != 'ARTIFACTS.sha256'))
print(json.dumps({'destination': str(DEST), 'source_files': len(records), 'stored_files': len([p for p in DEST.rglob('*') if p.is_file()]), 'total_bytes': sum(p.stat().st_size for p in DEST.rglob('*') if p.is_file()), 'validation_sha256': sha((DEST / 'ARCHIVE-VALIDATION.json').read_bytes()), 'artifacts_manifest_sha256': sha((DEST / 'ARTIFACTS.sha256').read_bytes())}, indent=2))
