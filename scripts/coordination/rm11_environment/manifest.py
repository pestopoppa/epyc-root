#!/usr/bin/env python3
"""Inventory the matched RM-11b slice from local evidence, without running tests."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

DEFAULT_ROOT = Path('/mnt/raid0/llm')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def generate_manifest(ids_path, rows_path, archive_path, expected_count=48):
    ids = ids_path.read_text(encoding='utf-8').split()
    if len(ids) != expected_count or len(set(ids)) != expected_count:
        raise ValueError(f'expected {expected_count} distinct IDs; got {len(ids)}')
    wanted = set(ids)
    matched = {}
    with rows_path.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            rid = row.get('row_id')
            if rid in wanted:
                if rid in matched:
                    raise ValueError(f'duplicate corpus row: {rid}')
                matched[rid] = row
    if set(matched) != wanted:
        raise ValueError(f'missing corpus IDs: {sorted(wanted - set(matched))}')
    items = []
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.namelist()
        names = set(entries)
        if len(names) != len(entries):
            raise ValueError('archive contains duplicate member names')
        for rid in sorted(ids):
            row = matched[rid]
            source = row['decontamination']
            provenance = row['provenance']
            instance = provenance['instance_id']
            if instance != source['instance_id'] or not source['repo'] or not source['base_commit']:
                raise ValueError(f'inconsistent instance identity: {rid}')
            prefix = f'testgen_combined/{instance}/'
            result_path = prefix + 'result.json'
            test_files = sorted(n for n in names if n.startswith(prefix + 'test_') and not n.endswith('/'))
            result = json.loads(archive.read(result_path)) if result_path in names else None
            if result is not None and result.get('instance_id') != instance:
                raise ValueError(f'archive instance mismatch: {instance}')
            idx = provenance.get('comment_index')
            selected = [t for t in (result or {}).get('results', []) if t.get('comment_index') == idx] if idx is not None else []
            if len(selected) > 1:
                raise ValueError(f'duplicate selected comment: {instance} {idx}')
            selected_file = selected[0].get('test_file') if selected else None
            selected_path = 'testgen_combined/' + selected_file if isinstance(selected_file, str) else None
            # A test from a different instance or a traversal is not a selected-instance test.
            if selected_path and (not selected_path.startswith(prefix) or '..' in selected_path.split('/')):
                raise ValueError(f'selected test path escapes instance: {instance}')
            selected_path = (selected_path if selected_path in names
                             and not archive.getinfo(selected_path).is_dir() else None)
            items.append({
                'row_id': rid, 'instance_id': instance, 'repo': source['repo'], 'base_commit': source['base_commit'],
                'candidate_is': provenance.get('candidate_is'), 'comment_index': idx,
                'archive': {'result_path': result_path if result is not None else None,
                            'test_files': test_files, 'selected_comment_present': bool(selected),
                            'selected_test_path': selected_path,
                            'selected_historical_success': selected[0].get('success') if selected else None},
                'local_base_commit_available': 'unknown', 'pinned_image_digest': None,
                'image_available': 'unknown', 'tests_independent_for_issue_solve': 'unknown',
                'test_execution_verified': False,
                'ready_for_solve_scoring': False,
                'readiness_reasons': ['base commit not verified locally', 'image digest not pinned',
                                      'issue-level test independence and coverage not established',
                                      'test execution not verified'],
            })
    if len({x['instance_id'] for x in items}) != len(items):
        raise ValueError('slice has duplicate instances; audit before use')
    return {'schema': 'rm11b.environment-inventory.v1',
            'scope': 'archive inventory only; not executable-environment or solve-scoring validation',
            'ready_for_solve_scoring': False,
            'inputs': {name: {'path': str(path), 'sha256': sha256(path)} for name, path in
                       [('row_ids', ids_path), ('corpus', rows_path), ('testgen_archive', archive_path)]},
            'instances': items}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids', type=Path, default=DEFAULT_ROOT / 'epyc-inference-research/docs/data/rm2_reviewer_slate_ccrab_p_rev1_matched_row_ids_20260719.txt')
    parser.add_argument('--rows', type=Path, default=DEFAULT_ROOT / 'datasets/nearmiss-corpus-v1/rows.jsonl')
    parser.add_argument('--archive', type=Path, default=DEFAULT_ROOT / 'datasets/c-crab/raw_results_compressed/testgen_combined.zip')
    args = parser.parse_args()
    try:
        print(json.dumps(generate_manifest(args.ids, args.rows, args.archive), indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f'inventory failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
