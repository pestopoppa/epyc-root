#!/usr/bin/env python3
"""Model-free regression check for the r5 M4 Q38 job launcher."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE_JOB = Path('/mnt/raid0/llm/tmp/inf22-m4-q38-recipe-r5-20261104/job.sh')


class JobLaunchRegression(unittest.TestCase):
    def test_full_run_output_creation_and_dry_run_separation(self) -> None:
        with tempfile.TemporaryDirectory(prefix='q38-job-regression-') as td:
            root = Path(td)
            base = root / 'isolated-base'
            base.mkdir()
            (base / 'source/scripts/benchmark/m4_cpu_ownership').mkdir(parents=True)
            (base / 'source/scripts/benchmark').mkdir(parents=True, exist_ok=True)
            (base / 'plan').mkdir()
            (base / 'plan/PLAN.json').write_text('{}\n')
            (base / 'source/scripts/benchmark/m4_cpu_recipe_entry.py').touch()
            (base / 'source/scripts/benchmark/m4_cpu_ownership/lease_owner.py').touch()
            (root / 'flags').mkdir()
            (root / 'grants').mkdir()
            (root / 'grants/fake.grant').write_text('fake lease fixture\n')
            (root / 'stop').touch()
            invocations = root / 'invocations.jsonl'
            fake_python = root / 'fake-python'
            fake_python.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_PY_LOG"], "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
''')
            fake_python.chmod(0o755)
            script = root / 'job.sh'
            text = SOURCE_JOB.read_text()
            text = text.replace('base=/mnt/raid0/llm/tmp/inf22-m4-q38-recipe-r5-20261104', f'base={base}')
            text = text.replace('python=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python', f'python={fake_python}')
            script.write_text(text)
            script.chmod(0o755)

            env = os.environ.copy()
            env.update({
                'FILLER_FLAGS_DIR': str(root / 'flags'),
                'FILLER_GRANTS_DIR': str(root / 'grants'),
                'FILLER_ID': 'fake',
                'FILLER_STOPFILE': str(root / 'stop'),
                'FILLER_DEADLINE': '2099-01-01T00:00:00Z',
                'FAKE_PY_LOG': str(invocations),
            })
            output = base / 'captures/run-r1'
            self.assertFalse(output.parent.exists())

            full = subprocess.run([str(script)], env=env, text=True, capture_output=True)
            self.assertEqual(full.returncode, 0, full.stderr)
            self.assertTrue(output.is_dir(), 'full-run must create the output parent and target')
            self.assertEqual(len(list(output.iterdir())), 0)
            first_log = invocations.read_text().splitlines()
            self.assertEqual(len(first_log), 1, 'full-run must invoke the fake lease/python once')
            self.assertTrue(any(arg.endswith('/lease_owner.py') for arg in json.loads(first_log[0])))

            repeated = subprocess.run([str(script)], env=env, text=True, capture_output=True)
            self.assertNotEqual(repeated.returncode, 0, 'existing output must refuse a repeated full-run')
            self.assertIn('File exists', repeated.stderr)
            self.assertEqual(len(invocations.read_text().splitlines()), 1,
                             'refused repeat must not invoke the lease entry')

            shutil.rmtree(output)
            output.parent.rmdir()
            env['FILLER_DRYRUN'] = '1'
            dry = subprocess.run([str(script)], env=env, text=True, capture_output=True)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertFalse(output.parent.exists(), 'dry-run must not create the full-run output directory')
            calls = [json.loads(line) for line in invocations.read_text().splitlines()]
            self.assertEqual(len(calls), 2)
            self.assertTrue(any(arg.endswith('/m4_cpu_recipe_entry.py') for arg in calls[1]))
            self.assertNotIn('lease_owner.py', calls[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
