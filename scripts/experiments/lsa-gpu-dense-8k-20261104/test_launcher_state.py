import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class LauncherStateTest(unittest.TestCase):
    def test_smoke_result_cannot_complete_grant(self):
        source = Path(__file__).with_name('launcher.sh').read_text()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / 'run'
            smoke = root / 'smoke'
            launcher = root / 'launcher.sh'
            launcher.write_text(source.replace(
                'R=/mnt/raid0/llm/tmp/lsa-gpu-dense-bf16-8k-20261104',
                f'R={run}',
            ))
            (smoke / 'native').mkdir(parents=True)
            (smoke / 'native' / 'RESULT.json').write_text(json.dumps({'status': 'pass'}))
            env = dict(os.environ, FILLER_STATE_DIR=str(smoke / 'state'))
            env.pop('FILLER_DRYRUN', None)
            env.pop('FILLER_DRYRUN_DIR', None)

            def complete(e):
                return subprocess.run(['/bin/bash', str(launcher), '--complete'],
                                      env=e, capture_output=True).returncode

            self.assertNotEqual(complete(env), 0)
            dry = dict(env, FILLER_DRYRUN='1', FILLER_DRYRUN_DIR=str(smoke))
            self.assertEqual(complete(dry), 0)
            (run / 'native').mkdir(parents=True)
            (run / 'native' / 'RESULT.json').write_text(json.dumps({'status': 'pass'}))
            self.assertEqual(complete(env), 0)


if __name__ == '__main__':
    unittest.main()
