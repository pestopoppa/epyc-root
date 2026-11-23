"""Disk hardening 2026-11-23: LARGE-DERIVED flag, floor+40 DISK-WARN, pressure-aware idle window, worktree_gate by-owner."""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_COORD = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_COORD, 'rowflow'))
sys.path.insert(0, os.path.join(os.path.dirname(_COORD), 'system'))
import notify  # noqa: E402
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
import worktree_gate as wg  # noqa: E402


def _sparse(path, size):
    with open(path, 'wb') as f:
        f.truncate(size)


class LargeDerived(unittest.TestCase):
    def test_flags_undeclared_and_respects_declaration_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'gguf'))
            _sparse(os.path.join(d, 'gguf', 'big.gguf'), 2 << 30)
            _sparse(os.path.join(d, 'small.gguf'), 1 << 20)
            _sparse(os.path.join(d, 'notes.txt'), 3 << 30)
            _sparse(os.path.join(d, 'raw.bin'), 1 << 30)
            os.symlink(os.path.join(d, 'gguf', 'big.gguf'), os.path.join(d, 'link.gguf'))
            got = [os.path.basename(p) for p, _ in rf.large_derived(d)]
            self.assertEqual(got, ['big.gguf', 'raw.bin'])
            self.assertEqual([os.path.basename(p) for p, _ in rf.large_derived(d, ['gguf/*.gguf'])], ['raw.bin'])
            self.assertEqual(rf.large_derived(d, ['*']), [])

    def test_check_logs_once_per_file_and_reads_manifest(self):
        with tempfile.TemporaryDirectory() as flags, tempfile.TemporaryDirectory() as root:
            _sparse(os.path.join(root, 'm.gguf'), 1 << 30)
            os.makedirs(os.path.join(flags, 'ready'), exist_ok=True)
            orig = rf.load_json
            rf.load_json = lambda p: {'scratch_root': root} if ('r1' in p and 'ready' in p) else orig(p)
            try:
                lines = []
                out = rf.large_derived_check(flags, [{'id': 'r1'}], lines.append, now=1000, state_path=os.path.join(flags, 'ld.json'))
                self.assertEqual(len(out), 1)
                self.assertIn('LARGE-DERIVED r1', lines[0])
                out2 = rf.large_derived_check(flags, [{'id': 'r1'}], lines.append, now=1000 + rf.LARGE_DERIVED_EVERY_S + 1,
                                              state_path=os.path.join(flags, 'ld.json'))
                self.assertEqual(out2, [])   # already logged
            finally:
                rf.load_json = orig

    def test_spec_key_and_keep_lint(self):
        self.assertIn('reclaimable', pr.SPEC_KEYS)
        spec = {'id': 'x', 'regions': 'q0', 'result_path': '/x/RESULT.json', 'kind': 'compute', 'scratch_gb': 5, 'keep': ['out/*.gguf']}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            pr.lint(spec)
        self.assertIn('keeps-model-files', buf.getvalue())
        spec2 = dict(spec, reclaimable=['tmp/*.gguf'], publish_warnings=None)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            pr.lint(spec2)
        self.assertNotIn('keeps-model-files', buf.getvalue())


class DiskWarn(unittest.TestCase):
    def test_warn_band_once_regrow_and_rearm(self):
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, 'w.json')
            emitted, logs = [], []
            orig = notify.emit
            notify.emit = lambda *a, **k: emitted.append(a[1])
            try:
                kw = dict(floor=150, margin=40, hyst=25, log=logs.append, cands_fn=lambda: [{'path': '/t/a', 'gib': 30}])
                self.assertIsNone(notify.disk_warn_check(d, sp, free=200, **kw))          # above floor+40
                self.assertEqual(notify.disk_warn_check(d, sp, free=185, **kw), 'raised')
                self.assertIsNone(notify.disk_warn_check(d, sp, free=181, **kw))          # same crossing, small drop
                self.assertEqual(notify.disk_warn_check(d, sp, free=172, **kw), 'raised')  # dropped >= 10 more
                self.assertEqual(notify.disk_warn_check(d, sp, free=230, **kw), 'cleared')
                self.assertEqual(notify.disk_warn_check(d, sp, free=189, **kw), 'raised')  # re-armed
            finally:
                notify.emit = orig
            self.assertEqual(emitted.count('disk-warn'), 3)
            self.assertTrue(any('DISK-WARN' in l and '/t/a' in l for l in logs))

    def test_wired_into_allocator(self):
        src = open(os.path.join(_COORD, 'rowflow', 'rowflow.py')).read()
        self.assertIn('notify.disk_warn_check(', src)
        self.assertIn('large_derived_check(flags, grants, log)', src)


class PressureIdle(unittest.TestCase):
    def test_keeper_shortens_idle_window_under_pressure(self):
        src = open(os.path.join(_COORD, 'rowflow', 'ws58-calendar-keeper-v13.sh')).read()
        self.assertRegex(src, r'REAP_PRESSURE_FREE_GIB:-200')
        self.assertRegex(src, r'REAP_IDLE_DAYS=\$\{REAP_IDLE_DAYS_PRESSURE:-0\.0833\}')
        # the shortening comes after the default assignment and before the env export
        self.assertLess(src.index('REAP_IDLE_DAYS=${REAP_IDLE_DAYS:-1}'), src.index('REAP_IDLE_DAYS_PRESSURE'))
        self.assertLess(src.index('REAP_IDLE_DAYS_PRESSURE'), src.index('REAP_IDLE_DAYS=$REAP_IDLE_DAYS REAP_WORKTREES'))


class ByOwner(unittest.TestCase):
    def test_grouping_and_filter(self):
        rows = [
            {'path': '/w/ak-x-1', 'branch': 'ak/x', 'verdict': 'REMOVABLE', 'idle_days': 1.0, 'size_bytes': 5},
            {'path': '/w/ak-y-1', 'branch': 'ak/y', 'verdict': 'REMOVABLE', 'idle_days': 1.0, 'size_bytes': 9},
            {'path': '/w/cx3-a', 'branch': 'codex/a', 'verdict': 'REMOVABLE', 'idle_days': 0.01},
            {'path': '/w/pm-q', 'branch': 'pm/q', 'verdict': 'DIRTY', 'idle_days': 3},
            {'path': '/w/zzz', 'branch': 'main2', 'verdict': 'REMOVABLE', 'idle_days': 2},
        ]
        g = wg.by_owner(rows, 0.25)
        self.assertEqual(sorted(g), ['autokernel', 'other'])
        self.assertEqual([r['path'] for r in g['autokernel']], ['/w/ak-y-1', '/w/ak-x-1'])
        self.assertEqual(wg.owner_of(rows[2]), 'codex')


if __name__ == '__main__':
    unittest.main()
