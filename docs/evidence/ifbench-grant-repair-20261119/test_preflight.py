"""Exercise the actual workers' grant preflight without loading corpus or model."""
import ast
import os
import pathlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path('/mnt/raid0/llm/tmp/canonical-judge-suite-revamp')
ARMS = ['ifbench-v3-cj6a-20261104', 'ifbench-cj6e-35b-20261119']


class GrantPreflight(unittest.TestCase):
    def preflight(self, arm, env):
        tree = ast.parse((ROOT / arm / 'worker.py').read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        # Execute exactly the grant lookup and fail-closed check. The next statement
        # accesses model verification; no cohort/model/network code is executed.
        end = next(i for i, n in enumerate(main.body) if isinstance(n, ast.If))
        nodes = main.body[:end + 1]
        self.assertIn('grant missing', ast.unparse(nodes[-1]))
        namespace = {'os': os, 'pathlib': pathlib, 'D': Path(env['IFBENCH_OUT'])}
        with patch.dict(os.environ, env, clear=True):
            exec(compile(ast.Module(body=nodes, type_ignores=[]), 'worker-preflight', 'exec'), namespace)
        return namespace

    def test_full_mode_lookup_and_fail_closed_both_arms(self):
        for arm in ARMS:
            for empty in (False, True):
                with self.subTest(arm=arm, empty=empty), tempfile.TemporaryDirectory() as tmp:
                    flags = Path(tmp) / 'flags'
                    grants = flags / 'grants'
                    grants.mkdir(parents=True)
                    env = {'IFBENCH_MODE': 'full', 'IFBENCH_OUT': tmp,
                           'FILLER_ID': 'synthetic-preflight', 'FILLER_FLAGS_DIR': str(flags)}
                    if empty:
                        env['FILLER_GRANTS_DIR'] = ''
                    with self.assertRaisesRegex(RuntimeError, 'grant missing'):
                        self.preflight(arm, env)
                    grant = grants / 'synthetic-preflight.grant'
                    grant.write_bytes(b'synthetic grant; never used for inference\n')
                    result = self.preflight(arm, env)
                    self.assertEqual(result['gp'], grant)
                    self.assertEqual(result['grant'], grant.read_bytes())
                    # Explicit alternate grant roots must take precedence.
                    env['FILLER_GRANTS_DIR'] = str(Path(tmp) / 'alternate')
                    with self.assertRaisesRegex(RuntimeError, 'grant missing'):
                        self.preflight(arm, env)
                    Path(env['FILLER_GRANTS_DIR']).mkdir()
                    alternate = Path(env['FILLER_GRANTS_DIR']) / grant.name
                    alternate.write_bytes(b'alternate identity')
                    self.assertEqual(self.preflight(arm, env)['grant'], b'alternate identity')

    def test_launcher_clean_environment_propagates_default_and_override(self):
        for arm in ARMS:
            launcher = (ROOT / arm / 'launch.sh').read_text()
            subprocess.run(['bash', '-n', str(ROOT / arm / 'launch.sh')], check=True)
            cmd = launcher.split("--cmd '", 1)[1].split("' ;;", 1)[0]
            # Replace only the final job invocation; exercise the real env -i bridge.
            cmd = cmd.rsplit('/bin/bash ', 1)[0] + '/usr/bin/env'
            for overrides, expected in [({}, '/mnt/raid0/llm/tmp/compute-flags/grants'),
                                        ({'FILLER_GRANTS_DIR': '', 'FILLER_FLAGS_DIR': ''}, '/mnt/raid0/llm/tmp/compute-flags/grants'),
                                        ({'FILLER_FLAGS_DIR': '/synthetic/flags'}, '/synthetic/flags/grants'),
                                        ({'FILLER_GRANTS_DIR': '/synthetic/override'}, '/synthetic/override')]:
                with self.subTest(arm=arm, overrides=overrides):
                    proc = subprocess.run(['bash', '-c', cmd], env={'PATH': '/usr/bin:/bin', **overrides},
                                          text=True, capture_output=True, check=True)
                    result = dict(line.split('=', 1) for line in proc.stdout.splitlines())
                    self.assertEqual(result['FILLER_GRANTS_DIR'], expected)
                    self.assertEqual(result['IFBENCH_MODE'], 'full')


if __name__ == '__main__':
    unittest.main(verbosity=2)
