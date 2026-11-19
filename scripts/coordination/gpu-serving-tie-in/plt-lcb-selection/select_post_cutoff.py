#!/usr/bin/env python3
"""Freeze a dated LCB selection from all hash-pinned v6 shards before inference.

Requires an explicit evidence-bound model cutoff or publication-date upper bound.
This tool never establishes the truth of the supplied evidence. The returned list
is not a scorer, a quality result, or evidence that a model was uncontaminated.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path

REVISION = '28efd4d97f479657d49989f83e30b9d51481ad9e'
MODEL_REVISION = 'b87cf3aa2186937b0d0362a684d7d30f234543e3'
SOURCE_MANIFEST_SHA256 = '22f8cc3c4f810d551ce90bbad8024493a6bd644ea061e3dc920717b35b5b983c'


def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _candidates_after_contest_date(rows, cutoff, minimum=200):
    if not isinstance(cutoff, dt.date) or isinstance(cutoff, dt.datetime):
        raise ValueError('cutoff must be a date')
    if type(minimum) is not int or minimum < 1:
        raise ValueError('minimum must be positive')
    seen = set()
    selected = []
    for row in rows:
        qid, stamp = row.get('question_id'), row.get('contest_date')
        if not isinstance(qid, str) or not qid or qid in seen:
            raise ValueError('missing or duplicate question_id')
        seen.add(qid)
        if not isinstance(stamp, str):
            raise ValueError('missing contest_date')
        try:
            date = dt.datetime.fromisoformat(stamp.replace('Z', '+00:00')).date()
        except ValueError as e:
            raise ValueError(f'invalid contest_date for {qid}') from e
        if date > cutoff:
            selected.append({'question_id': qid, 'contest_date': date.isoformat()})
    selected.sort(key=lambda x: (x['contest_date'], x['question_id']))
    if len(selected) < minimum:
        raise ValueError(f'only {len(selected)} eligible items; need {minimum}')
    return selected


def validate_release_audit(selected, audit, evidence_root):
    """Require reviewed, per-item original publication evidence; dates alone are insufficient."""
    if audit.get('dataset_revision') != REVISION or not isinstance(audit.get('reviewed_by'), str) or not audit['reviewed_by'].strip():
        raise ValueError('release audit needs dataset pin and reviewer')
    entries = audit.get('items')
    if not isinstance(entries, list):
        raise ValueError('release audit items missing')
    by_id = {}
    for entry in entries:
        qid = entry.get('question_id')
        if not qid or qid in by_id:
            raise ValueError('missing or duplicate release-audit question_id')
        by_id[qid] = entry
    if set(by_id) != {x['question_id'] for x in selected}:
        raise ValueError('release audit must cover every selected item exactly')
    root = Path(evidence_root).resolve(strict=True)
    out = []
    for item in selected:
        a = by_id[item['question_id']]
        if a.get('finding') != 'original_release_not_before_contest':
            raise ValueError('release lower-bound finding missing')
        url, digest, relative = a.get('source_url'), a.get('evidence_sha256'), a.get('evidence_file')
        if not isinstance(url, str) or not url.startswith('https://'):
            raise ValueError('original publication source required')
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('original publication evidence digest required')
        if not isinstance(relative, str) or Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('release evidence path must be relative and contained')
        evidence = (root / relative).resolve(strict=True)
        if not evidence.is_relative_to(root) or not evidence.is_file() or sha256_file(evidence) != digest:
            raise ValueError('missing, escaped or changed release evidence')
        original = dt.date.fromisoformat(a['original_release_date'])
        contest = dt.date.fromisoformat(item['contest_date'])
        if original < contest:
            raise ValueError('original publication predates contest; not a lower bound')
        out.append(dict(item, original_release_date=original.isoformat(), release_source_url=url,
                        release_evidence_sha256=digest))
    return out


def make_manifest(source, witness, rows, minimum, release_audit, evidence_root):
    if source.get('dataset') != 'livecodebench/code_generation_lite' or source.get('revision') != REVISION or source.get('config') != 'release_v6':
        raise ValueError('wrong official dataset pin')
    if witness.get('model_revision') != MODEL_REVISION or witness.get('kind') not in ('author_cutoff', 'publication_upper_bound'):
        raise ValueError('wrong model or evidence kind')
    if not isinstance(witness.get('source_url'), str) or not witness['source_url'].startswith('https://'):
        raise ValueError('an HTTPS primary evidence source is required')
    if not isinstance(witness.get('source_sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', witness['source_sha256']):
        raise ValueError('evidence bytes must be hash pinned')
    cutoff = dt.date.fromisoformat(witness['cutoff_date'])
    selected = _candidates_after_contest_date(rows, cutoff, minimum)
    selected = validate_release_audit(selected, release_audit, evidence_root)
    return {'schema': 'gpu-plt.lcb-selection.v1', 'dataset': source['dataset'], 'revision': REVISION,
            'config': 'release_v6', 'model_revision': MODEL_REVISION, 'cutoff': witness,
            'minimum': minimum, 'release_reviewed_by': release_audit['reviewed_by'], 'items': selected,
            'scope': 'candidate selection; witness truth, scorer and source licensing require review'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-manifest', type=Path, required=True)
    ap.add_argument('--witness', type=Path, required=True)
    ap.add_argument('--witness-evidence', type=Path, required=True)
    ap.add_argument('--release-audit', type=Path, required=True)
    ap.add_argument('--release-evidence-root', type=Path, required=True)
    ap.add_argument('--shard', type=Path, action='append', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if os.environ.get('FILLER_ID') or os.environ.get('FILLER_DRYRUN'):
        raise ValueError('selection and input hashing must be done before publishing')
    if sha256_file(args.source_manifest) != SOURCE_MANIFEST_SHA256:
        raise ValueError('unreviewed official shard manifest')
    source = json.loads(args.source_manifest.read_text()); witness = json.loads(args.witness.read_text())
    if sha256_file(args.witness_evidence) != witness.get('source_sha256'):
        raise ValueError('witness evidence hash mismatch')
    files = source.get('files', [])
    if len(files) != 9 or len(args.shard) != 9:
        raise ValueError('all nine source shards are required')
    expected = {f['name']: f for f in files}
    if len(expected) != 9 or set(expected) != {f'test-{i:05d}-of-00009.parquet' for i in range(9)}:
        raise ValueError('unexpected shard manifest')
    shards = {p.name: p for p in args.shard}
    if len(shards) != 9 or set(shards) != set(expected):
        raise ValueError('unexpected shard files')
    import pyarrow.parquet as pq
    rows = []
    for name in sorted(shards):
        p, entry = shards[name], expected[name]
        if p.stat().st_size != entry['bytes'] or sha256_file(p) != entry['sha256']:
            raise ValueError(f'shard size or digest mismatch: {name}')
        rows.extend(pq.read_table(p, columns=['question_id', 'contest_date']).to_pylist())
    audit = json.loads(args.release_audit.read_text())
    result = make_manifest(source, witness, rows, 200, audit, args.release_evidence_root)
    result['release_audit_sha256'] = sha256_file(args.release_audit)
    result['source_manifest_sha256'] = sha256_file(args.source_manifest)
    result['witness_sha256'] = sha256_file(args.witness)
    result['source_shards'] = files
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True); f.write('\n')


if __name__ == '__main__':
    main()
