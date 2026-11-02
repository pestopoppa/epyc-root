import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/analysis/dar_join_coverage.py'
SECRET = 'PRIVATE_PROMPT_SENTINEL'


def start(tid, ts='2026-09-24T10:02:30Z'):
    return {'task_id': tid, 'event_type': 'task_started', 'timestamp': ts,
            'data': {'objective': SECRET, 'task_type': 'fixture'}}


def end(tid, ts='2026-09-24T10:02:40Z', role='coder'):
    return {'task_id': tid, 'event_type': 'task_completed', 'timestamp': ts,
            'data': {'producer_role': role}, 'outcome': 'success'}


def reward(tid, ts='2026-09-24T10:02:40Z', wall=10, role='coder'):
    return {'task_id': tid, 'timestamp': ts, 'producer_role': role,
            'wall_clock_s': wall, 'reward_post_fix': 0.7, 'outcome': 'success'}


class AuditTest(unittest.TestCase):
    def run_audit(self, events, rewards, roles=('coder',), malformed=False):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); p = d/'events.jsonl'; r = d/'rewards.jsonl.gz'; b = d/'roles.json'
            p.write_text(''.join(json.dumps(x)+'\n' for x in events) + ('{bad\n' if malformed else ''))
            with gzip.open(r, 'wt') as f:
                f.writelines(json.dumps(x)+'\n' for x in rewards)
            b.write_text(json.dumps(roles))
            result = subprocess.run([sys.executable, str(SCRIPT), '--progress', str(p),
                '--rewards', str(r), '--baseline-roles', str(b)], capture_output=True, text=True, check=True)
            self.assertNotIn(SECRET, result.stdout + result.stderr)
            self.assertNotIn('sensitive-id', result.stdout + result.stderr)
            return json.loads(result.stdout)['counts']

    def test_valid_and_malformed(self):
        c = self.run_audit([start('sensitive-id'), end('sensitive-id')], [reward('sensitive-id')], malformed=True)
        self.assertEqual(c['joined_unique_feature_reward'], 1)
        self.assertEqual(c['joined_e18_or_later_duration_inputs_available'], 1)
        self.assertEqual(c['progress_malformed'], 1)

    def test_duplicates_and_terminal_conflicts_excluded(self):
        fail = dict(end('b'), event_type='task_failed')
        c = self.run_audit([start('a'), start('a'), end('a'), start('b'), end('b'), fail,
                            start('c'), end('c')], [reward('a'), reward('b'), reward('c'), reward('c')])
        self.assertEqual(c['duplicate_start'], 1)
        self.assertEqual(c['conflicting_terminals'], 1)
        self.assertEqual(c['duplicate_reward'], 1)
        self.assertNotIn('joined_unique_feature_reward', c)

    def test_timing_role_outcome_and_baselines(self):
        ev = []; rw = []
        for name in ('wall', 'time', 'role', 'outcome', 'baseline'):
            ev.extend([start(name), end(name, role='unknown' if name == 'baseline' else 'coder')])
            row = reward(name, wall=9 if name == 'wall' else 10,
                         ts='2026-09-24T10:02:41Z' if name == 'time' else '2026-09-24T10:02:40Z',
                         role='unknown' if name == 'baseline' else ('other' if name == 'role' else 'coder'))
            if name == 'outcome': row['outcome'] = 'failure'
            rw.append(row)
        c = self.run_audit(ev, rw)
        for k in ('reward_duration_missing_or_mismatch', 'reward_timestamp_mismatch',
                  'role_missing_or_mismatch', 'outcome_mismatch', 'joined_missing_duration_baseline'):
            self.assertEqual(c[k], 1)
        self.assertEqual(c['joined_unique_feature_reward'], 1)
        self.assertNotIn('joined_duration_inputs_available', c)

    def test_large_numeric_fields_are_excluded(self):
        row = reward('a', wall=10**309)
        c = self.run_audit([start('a'), end('a')], [row])
        self.assertEqual(c['reward_duration_missing_or_mismatch'], 1)
        row = reward('b'); row['reward_post_fix'] = 10**309
        c = self.run_audit([start('b'), end('b')], [row])
        self.assertEqual(c['invalid_reward'], 1)

    def test_truncated_gzip_error_is_sanitized(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); p = d/'events'; r = d/'sensitive-id.gz'; b = d/'roles'
            p.write_text(''); r.write_bytes(gzip.compress(b'{}\n')[:-4]); b.write_text('[]')
            result = subprocess.run([sys.executable, str(SCRIPT), '--progress', str(p),
                '--rewards', str(r), '--baseline-roles', str(b)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('sensitive-id', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_boundary_and_invalid_time(self):
        ev = [start('old', '2026-09-24T10:02:28Z'), end('old', '2026-09-24T10:02:38Z'),
              start('exact', '2026-09-24T10:02:29Z'), end('exact', '2026-09-24T10:02:39Z'),
              start('bad', '2026-09-24T10:02:30'), end('bad')]
        rw = [reward('old', '2026-09-24T10:02:38Z'), reward('exact', '2026-09-24T10:02:39Z'), reward('bad')]
        c = self.run_audit(ev, rw)
        self.assertEqual(c['joined_duration_inputs_available'], 2)
        self.assertEqual(c['joined_e18_or_later_duration_inputs_available'], 1)
        self.assertEqual(c['invalid_timestamp'], 1)

if __name__ == '__main__': unittest.main()
