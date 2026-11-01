#!/usr/bin/env python3
"""Execute the actual extracted scoreboard loop against controlled Git responses."""
import contextlib
import io
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import proposal

HERE = pathlib.Path(__file__).resolve().parent
ORIGINAL = (HERE / 'original.sh').read_bytes()

class Scoreboard(unittest.TestCase):
    def run_loop(self, source, line, baseline='', suffix=''):
        script = source.decode().split("  python3 -I - <<'PY'", 1)[1].split('\nPY\n', 1)[0]
        script = script[script.index('\nimport '):script.index("\nbp = F +")]
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            for worker in ('ni', 'refactor', 'codex3'):
                (root / f'WORK-{worker}-code.md').write_text('- [S] handoffs/active/test.md:1 — Unique task\n')
            script = script.replace("F = '/mnt/raid0/llm/tmp/compute-flags/'", 'F = ' + repr(temp + '/'))
            def git(args, **kwargs):
                if 'rev-list' in args:
                    return subprocess.CompletedProcess(args, 0, 'base\n', '')
                if 'show' in args:
                    content = baseline if args[-1].startswith('base:') else line + '\n' + suffix
                    return subprocess.CompletedProcess(args, 0, content, '')
                raise AssertionError(args)
            namespace = {}
            with patch('subprocess.run', side_effect=git), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(script, 'extracted-scoreboard', 'exec'), namespace)
            return (namespace['done']['codex3'], namespace['today_n']['codex3'],
                    namespace['dec'].get('codex3', 0), len(namespace['uns'].get('codex3', [])))

    def test_controls(self):
        patched = proposal.propose(ORIGINAL)
        evidenced = '- [x] Unique task abcdef123 test.py'
        cases = [
            ('normal', evidenced, '', '', (1, 1, 0, 0), (1, 1, 0, 0)),
            ('old base', evidenced, evidenced, '', (1, 0, 0, 0), (1, 0, 0, 0)),
            ('decline', evidenced + ' DECLINED [closure: hygiene]', '', '', (0, 0, 1, 0), (0, 0, 1, 0)),
            ('hygiene', evidenced + ' [closure: hygiene]', '', '', (1, 1, 0, 0), (1, 0, 0, 0)),
            ('unsupported', '- [x] Unique task [closure: hygiene]', '', '', (0, 0, 0, 1), (0, 0, 0, 1)),
            ('marker next line', evidenced, '', '[closure: hygiene]', (1, 1, 0, 0), (1, 1, 0, 0)),
        ]
        for name, line, base, suffix, old, new in cases:
            with self.subTest(name=name):
                self.assertEqual(self.run_loop(ORIGINAL, line, base, suffix), old)
                self.assertEqual(self.run_loop(patched, line, base, suffix), new)
    def test_refuses_changed_source(self):
        with self.assertRaises(ValueError):
            proposal.propose(ORIGINAL + b'\n')

if __name__ == '__main__':
    unittest.main(verbosity=2)
