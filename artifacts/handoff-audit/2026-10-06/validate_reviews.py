#!/usr/bin/env python3
"""Validate JEV audit review inventory and MAIN disposition records.

Read-only: compares extracted review/decision artifacts with the original Git
snapshot and the selected repository checkout. --coverage-only omits MAIN
finding-decision requirements while still requiring complete shard coverage.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MANIFEST_PATH = BASE / 'manifest.json'
MANIFEST = json.loads(MANIFEST_PATH.read_text())


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(['git', '-C', str(repo), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def repo_default() -> Path:
    for candidate in (Path(__file__).resolve(), Path.cwd(), Path(MANIFEST['root'])):
        for parent in (candidate.parent, *candidate.parents):
            if (parent / '.git').exists():
                return parent
    raise SystemExit('cannot locate repository; pass --repo')


def original_bytes(repo: Path, path: str) -> bytes:
    return git(repo, 'show', f"{MANIFEST['root_commit']}:{path}")


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None


def validate(repo: Path, coverage_only: bool, applied_ref: str | None = None) -> dict:
    errors: list[str] = []
    inv_files = MANIFEST['files']
    by_path = {f['path']: f for f in inv_files}
    if len(by_path) != len(inv_files):
        errors.append('manifest has duplicate file paths')
    open_by_file = {p: {b['key'] for b in f.get('boxes', []) if not b['checked']} for p, f in by_path.items()}
    expected_keys = {k for ks in open_by_file.values() for k in ks}
    if len(expected_keys) != sum(map(len, open_by_file.values())):
        errors.append('manifest has duplicate unchecked task keys across files')

    # The manifest's SHA-256 identifies bytes in the pinned original tree. Verify
    # that claim from Git, not from a mutable worktree which may contain appends.
    for path, row in by_path.items():
        try:
            blob = original_bytes(repo, path)
        except subprocess.CalledProcessError:
            errors.append(f'{path}: absent from root_commit {MANIFEST["root_commit"]}')
            continue
        if sha256(blob) != row['sha256']:
            errors.append(f'{path}: manifest SHA-256 does not match root_commit Git blob')

    review_by_shard = {}
    all_reviewed_files = []
    all_reviewed_keys = []
    all_findings = {}
    for shard_meta in MANIFEST['shards']:
        sid = shard_meta['id']
        shard = load_json(BASE / f'{sid}.json')
        review = load_json(BASE / f'{sid}-review.json')
        if shard is None or review is None:
            errors.append(f'{sid}: missing shard input or review')
            continue
        review_by_shard[sid] = (shard, review)
        if review.get('shard_id') != sid:
            errors.append(f'{sid}: review shard_id mismatch')
        exp = {f['path']: f for f in shard['files']}
        for shard_row in shard['files']:
            manifest_row = by_path.get(shard_row['path'])
            if manifest_row is None or shard_row != manifest_row:
                errors.append(f'{sid}:{shard_row.get("path")}: shard input differs from pinned manifest row')
        actual = review.get('files', [])
        counts = collections.Counter(f.get('path') for f in actual)
        if set(counts) != set(exp) or any(n != 1 for n in counts.values()):
            errors.append(f'{sid}: file coverage mismatch; missing={sorted(set(exp)-set(counts))}; extra={sorted(set(counts)-set(exp))}')
        for row in actual:
            path = row.get('path')
            if path not in exp:
                continue
            src = exp[path]
            all_reviewed_files.append(path)
            if row.get('source_sha256') != src['sha256']:
                errors.append(f'{sid}:{path}: review source digest differs from shard inventory')
            keys = {b['key'] for b in src['boxes'] if not b['checked']}
            reviewed = row.get('reviewed_open_keys', [])
            if set(reviewed) != keys or len(reviewed) != len(keys):
                errors.append(f'{sid}:{path}: unchecked-key coverage mismatch')
            all_reviewed_keys.extend(reviewed)
            dispositions = collections.Counter(k for d in row.get('task_dispositions', []) for k in d.get('keys', []))
            if set(dispositions) != keys or any(n != 1 for n in dispositions.values()):
                errors.append(f'{sid}:{path}: each open key must have exactly one disposition')
            for finding in row.get('findings', []):
                fid = finding.get('id')
                if not fid or fid in all_findings:
                    errors.append(f'{sid}:{path}: missing or duplicate finding id {fid!r}')
                else:
                    all_findings[fid] = (sid, path, finding)
                if not set(finding.get('task_keys', [])) <= keys:
                    errors.append(f'{sid}:{path}: finding references unknown/closed task key')
                for field in ('title','revised_deliverable','non_inference_scope','inference_acceptance','gate','ownership','verification'):
                    if not finding.get(field):
                        errors.append(f'{sid}:{path}: finding missing {field}')
                if finding.get('verification') == 'source_verified' and not finding.get('source_evidence'):
                    errors.append(f'{sid}:{path}: source-verified finding lacks source anchors')

    if len(all_reviewed_files) != len(set(all_reviewed_files)):
        errors.append('shards overlap on file coverage')
    if set(all_reviewed_files) != set(by_path):
        errors.append(f'global file inventory mismatch: missing={len(set(by_path)-set(all_reviewed_files))} extra={len(set(all_reviewed_files)-set(by_path))}')
    if len(all_reviewed_keys) != len(set(all_reviewed_keys)):
        errors.append('shards overlap on unchecked task keys')
    if set(all_reviewed_keys) != expected_keys:
        errors.append(f'global unchecked-key inventory mismatch: missing={len(expected_keys-set(all_reviewed_keys))} extra={len(set(all_reviewed_keys)-expected_keys)}')
    total_open = sum(map(len, open_by_file.values()))
    if len(by_path) != 528 or total_open != 3558:
        errors.append(f'manifest inventory count changed: files={len(by_path)} open_keys={total_open}, expected 528/3558')

    decision_count = 0
    if not coverage_only:
        decisions_by_id = {}
        for sm in MANIFEST['shards']:
            sid = sm['id']
            data = load_json(BASE / f'{sid}-main-decisions.json')
            if data is None:
                errors.append(f'{sid}: missing MAIN decision file')
                continue
            shard_review_pair = review_by_shard.get(sid)
            expected_files = sm['files']
            expected_open = sm['open_boxes']
            if data.get('shard') != sid or data.get('accepted') is not True:
                errors.append(f'{sid}: MAIN shard decision must explicitly have matching shard and accepted=true')
            if data.get('files') != expected_files or data.get('open_keys') != expected_open:
                errors.append(f'{sid}: MAIN files/open_keys counts do not match manifest')
            for item in data.get('decisions', []):
                fid = item.get('id')
                if not fid or fid in decisions_by_id:
                    errors.append(f'{sid}: missing or duplicate MAIN decision id {fid!r}')
                else:
                    decisions_by_id[fid] = item
                    decision_count += 1
        for fid, (sid, path, finding) in all_findings.items():
            dec = decisions_by_id.get(fid)
            if dec is None:
                errors.append(f'{fid}: no MAIN accept/reject decision')
                continue
            decision = dec.get('decision', '').lower()
            if decision.startswith('accept'):
                if dec.get('path') != path:
                    errors.append(f'{fid}: accepted decision path does not match finding path')
                append = dec.get('applied_append')
                if not append:
                    errors.append(f'{fid}: accepted finding lacks applied_append')
                    continue
                try:
                    current = git(repo, 'show', f'{applied_ref}:{path}') if applied_ref else (repo / path).read_bytes()
                except (OSError, subprocess.CalledProcessError):
                    source = f'--applied-ref {applied_ref}' if applied_ref else '--repo'
                    errors.append(f'{fid}: accepted target absent from {source}')
                    continue
                if append.encode() not in current:
                    errors.append(f'{fid}: accepted append is not present in target file')
                if dec.get('original_sha256') and dec['original_sha256'] != by_path[path]['sha256']:
                    errors.append(f'{fid}: decision original hash differs from pinned manifest')
                if dec.get('new_sha256') and dec['new_sha256'] != sha256(current):
                    errors.append(f'{fid}: decision new_sha256 differs from current target file')
            elif decision.startswith('reject') or decision in ('withdrawn','rejected_redundant_then_withdrawn'):
                if not (dec.get('reason') or dec.get('review_notes')):
                    errors.append(f'{fid}: rejected finding lacks reason/review notes')
            else:
                errors.append(f'{fid}: decision must explicitly accept or reject, got {dec.get("decision")!r}')
        # MAIN may explicitly withdraw a proposal after review (for example a
        # duplicate append found during integration); that is a valid rejection
        # disposition even though the final shard review no longer emits it as a finding.
        extras = set(decisions_by_id) - set(all_findings)
        for fid in sorted(extras):
            dec = decisions_by_id[fid]
            decision = dec.get('decision', '').lower()
            if not (decision.startswith('reject') or 'withdrawn' in decision) or not (dec.get('reason') or dec.get('review_notes')):
                errors.append(f'MAIN decision refers to unknown finding without explicit rejection/withdrawal: {fid}')

    return {'mode':'coverage-only' if coverage_only else 'full', 'repo':str(repo), 'applied_ref':applied_ref, 'files':len(all_reviewed_files), 'open_boxes':len(all_reviewed_keys), 'findings':len(all_findings), 'main_decisions':decision_count, 'errors':errors}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, default=None, help='checkout containing original root_commit and current accepted handoff edits')
    ap.add_argument('--coverage-only', action='store_true', help='validate complete inventory/review coverage but permit missing MAIN decisions')
    ap.add_argument('--applied-ref', help='Git ref whose target-file bytes contain accepted appends; defaults to mutable --repo checkout')
    args = ap.parse_args()
    repo = (args.repo or repo_default()).resolve()
    result = validate(repo, args.coverage_only, args.applied_ref)
    print(json.dumps(result, indent=2))
    return 1 if result['errors'] else 0

if __name__ == '__main__':
    sys.exit(main())
