#!/usr/bin/env python3
"""Aggregate-only audit of progress start/completion and rescore JSONL joins.

Never emits input values, paths, task IDs, text, or exception details. The caller
must supply the exact E18 scorer's positive duration baseline role names as a JSON
array; this verifies coverage of inputs, not the provenance of stored rewards.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path

E18 = datetime.fromisoformat('2026-09-24T10:02:39+00:00')


def timestamp(s):
    try:
        t = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return t.astimezone(timezone.utc) if t.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def rows(paths, counts, prefix):
    for path in paths:
        opener = gzip.open if str(path).endswith('.gz') else open
        with opener(path, 'rt', encoding='utf-8', errors='strict') as f:
            for line in f:
                counts[prefix + '_lines'] += 1
                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        raise ValueError()
                except (ValueError, RecursionError):
                    counts[prefix + '_malformed'] += 1
                    continue
                yield obj


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def audit(progress, rewards, baseline_roles):
    c = Counter()
    events = defaultdict(lambda: {'task_started': [], 'task_completed': [], 'task_failed': []})
    replay = defaultdict(list)
    for event in rows(progress, c, 'progress'):
        typ, tid = event.get('event_type'), event.get('task_id')
        if typ not in ('task_started', 'task_completed', 'task_failed'):
            continue
        if not isinstance(tid, str) or not tid.strip():
            c['progress_lifecycle_missing_id'] += 1
            continue
        events[tid][typ].append(event)
    for row in rows(rewards, c, 'reward'):
        tid = row.get('task_id')
        if not isinstance(tid, str) or not tid.strip():
            c['reward_missing_id'] += 1
            continue
        replay[tid].append(row)
    c['progress_task_ids'] = len(events)
    c['reward_task_ids'] = len(replay)
    c['reward_without_progress'] = len(replay.keys() - events.keys())
    for tid, e in events.items():
        starts, ends, failures = e['task_started'], e['task_completed'], e['task_failed']
        if failures: c['ids_with_failed_events'] += 1
        if not starts: c['missing_start'] += 1
        if not ends: c['missing_completion'] += 1
        if len(starts) > 1: c['duplicate_start'] += 1
        if len(ends) > 1: c['duplicate_completion'] += 1
        if failures and ends: c['conflicting_terminals'] += 1
        if not replay.get(tid): c['missing_reward'] += 1
        if len(replay.get(tid, [])) > 1: c['duplicate_reward'] += 1
        if len(starts) != 1 or len(ends) != 1 or failures or len(replay.get(tid, [])) != 1:
            continue
        s, end, rew = starts[0], ends[0], replay[tid][0]
        sd, ed = s.get('data'), end.get('data')
        if not isinstance(sd, dict) or not isinstance(ed, dict):
            c['invalid_data'] += 1
            continue
        st, et, rt = timestamp(s.get('timestamp')), timestamp(end.get('timestamp')), timestamp(rew.get('timestamp'))
        if not st or not et or not rt:
            c['invalid_timestamp'] += 1
            continue
        if et < st:
            c['negative_duration'] += 1
            continue
        if et != rt:
            c['reward_timestamp_mismatch'] += 1
            continue
        role = ed.get('role') or ed.get('producer_role') or ed.get('final_answer_role')
        # Rescore doesn't emit bare role, so cannot validate identity when it wins.
        replay_role = rew.get('producer_role') or rew.get('final_answer_role')
        if not isinstance(role, str) or not role or role != replay_role:
            c['role_missing_or_mismatch'] += 1
            continue
        wall = rew.get('wall_clock_s')
        if not finite_number(wall) or abs(wall - (et-st).total_seconds()) > 0.00101:
            c['reward_duration_missing_or_mismatch'] += 1
            continue
        val = rew.get('reward_post_fix')
        if not finite_number(val) or not -1 <= val <= 1:
            c['invalid_reward'] += 1
            continue
        if (end.get('outcome') or 'success') != rew.get('outcome'):
            c['outcome_mismatch'] += 1
            continue
        # Prompt is inspected only for presence, never copied, hashed, or emitted.
        objective = sd.get('objective')
        if not isinstance(objective, str) or not objective.strip():
            c['missing_objective'] += 1
            continue
        c['joined_unique_feature_reward'] += 1
        c['start_feature_task_type_present'] += int(bool(sd.get('task_type')))
        c['completion_e18_or_later'] += int(et >= E18)
        if role not in baseline_roles:
            c['joined_missing_duration_baseline'] += 1
            continue
        c['joined_duration_inputs_available'] += 1
        if et >= E18: c['joined_e18_or_later_duration_inputs_available'] += 1
    return {'schema': 'dar-join-audit.v1', 'counts': dict(sorted(c.items())),
            'interpretation': 'Counts are candidate coverage only. Reward provenance, actual E18 scorer configuration, baseline provenance, role eligibility, selection bias, and feature truncation require independent verification. Stream order is not verified against the replay. No stored reward is certified E18 by this audit.'}


RECEIPT_SCHEMA = 'epyc.dar_join_coverage.receipt.v1'


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _git_revision():
    try:
        out = subprocess.run(['git', '-C', str(Path(__file__).resolve().parent), 'rev-parse', 'HEAD'],
                             capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        return out if len(out) == 40 else None
    except (OSError, subprocess.SubprocessError):
        return None


def receipt(progress, rewards, baseline_roles_path, roles, scorer_config, result):
    """Write-time capture for VB-DAR-JOIN-COVERAGE-WIRE: digests and aggregates only, never paths,
    task IDs, prompt text or exception details. Self-hashed so a reader can detect edits."""
    body = {'schema': RECEIPT_SCHEMA,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'status': 'completed',
            'producer': {'name': Path(__file__).name, 'sha256': _file_sha256(__file__),
                         'git_revision': _git_revision()},
            'e18_cutoff_utc': E18.isoformat(),
            'inputs': {'progress': [_file_sha256(p) for p in progress],
                       'rewards': [_file_sha256(p) for p in rewards],
                       'baseline_roles': {'sha256': _file_sha256(baseline_roles_path), 'n_roles': len(roles)},
                       'scorer_config_sha256': _file_sha256(scorer_config)},
            'result': result}
    canonical = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    body['receipt_sha256'] = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return body


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--progress', nargs='+', type=Path, required=True)
    p.add_argument('--rewards', nargs='+', type=Path, required=True)
    p.add_argument('--baseline-roles', type=Path, required=True, help='JSON array of roles with validated positive p50 baselines')
    p.add_argument('--receipt-out', type=Path, help='also write an immutable write-time receipt (needs --scorer-config)')
    p.add_argument('--scorer-config', type=Path, help='the exact E18 scorer configuration file; its digest is recorded')
    args = p.parse_args()
    if bool(args.receipt_out) != bool(args.scorer_config):
        p.exit(2, '--receipt-out and --scorer-config go together.\n')
    try:
        roles = json.loads(args.baseline_roles.read_text())
        if not isinstance(roles, list) or any(not isinstance(r, str) or not r for r in roles):
            raise ValueError()
        result = audit(args.progress, args.rewards, set(roles))
        if args.receipt_out:
            doc = receipt(args.progress, args.rewards, args.baseline_roles, roles, args.scorer_config, result)
            with open(args.receipt_out, 'x', encoding='utf-8') as f:
                f.write(json.dumps(doc, indent=2, sort_keys=True) + '\n')
    except (OSError, EOFError, UnicodeError, ValueError, TypeError, OverflowError):
        p.exit(2, 'Input error; no input details emitted.\n')
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
