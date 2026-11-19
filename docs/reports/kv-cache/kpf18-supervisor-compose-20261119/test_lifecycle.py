"""Wrapper ordering/refusal tests with inert supervisor bodies only."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('lifecycle_subject', HERE / 'lifecycle.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'out'
        self.output.mkdir()
        for mode in ('official', 'publisher-smoke'):
            destination = self.root / mode
            destination.mkdir()
            config = {'mode': mode, 'row_id': 'private-fixture', 'output_root': str(self.output),
                      'artifacts': {'server': '/inert/server'},
                      'prepared': {'argv': '/inert/argv', 'prompts': '/inert/prompts'}}
            (destination / 'manifest.json').write_text(json.dumps({'execution': config}))
        self.smoke = self.output / 'native-result.json'
        for context in (patch.dict(os.environ, {'FILLER_SMOKE': '1', 'FILLER_DRYRUN': '1',
                                               'FILLER_DRYRUN_RESULT_PATH': str(self.smoke)}, clear=True),
                        patch.object(sys, 'argv', ['private-fixture'])):
            context.start(); self.addCleanup(context.stop)

    def supervisor(self, body):
        (self.root / 'publisher-smoke/supervisor.py').write_text(
            'from pathlib import Path\nimport json\ndef run_driver():\n' +
            '\n'.join('    ' + line for line in body.splitlines()) + '\n')

    def test_success_record_follows_native_work_and_supervisor_cleanup_return(self):
        self.supervisor(f"assert not Path({str(self.smoke)!r}).exists()\n"
                        f"Path({str(self.output / 'SMOKE-REQUEST.json')!r}).write_text("
                        "json.dumps(dict(first_request_ok=True, gpu_samples=2, tokens=1)))\nreturn 0")
        self.assertEqual(subject.run(self.root), 0)
        self.assertEqual(subject.complete(self.root), 0)
        self.assertTrue(json.loads(self.smoke.read_text())['owned_cleanup_returned'])
        self.assertEqual(sys.argv[1], 'item3')
        self.assertNotIn('--dry-run', sys.argv)

    def test_refusal_rc_or_cleanup_exception_never_writes_progress(self):
        for body in ('return 3', "raise RuntimeError('owned child survives')"):
            self.supervisor(body)
            if body.startswith('return'):
                self.assertEqual(subject.run(self.root), 3)
            else:
                with self.assertRaisesRegex(RuntimeError, 'child survives'): subject.run(self.root)
            self.assertFalse(self.smoke.exists())
            self.assertEqual(subject.complete(self.root), 1)

    def test_empty_native_return_and_missing_residency_never_write_progress(self):
        self.supervisor('return 0')
        with self.assertRaises(FileNotFoundError): subject.run(self.root)
        path = self.output / 'SMOKE-REQUEST.json'
        for data in ({}, {'first_request_ok': True, 'gpu_samples': 0, 'tokens': 1},
                     {'first_request_ok': True, 'gpu_samples': 1, 'tokens': 0}):
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'not established'): subject.run(self.root)
            self.assertFalse(self.smoke.exists())

    def test_mode_drift_and_existing_result_refuse(self):
        with patch.dict(os.environ, {'FILLER_DRYRUN': '0'}):
            with self.assertRaisesRegex(ValueError, 'inconsistent'): subject.run(self.root)
        path = self.root / 'publisher-smoke/manifest.json'
        data = json.loads(path.read_text())
        data['execution']['mode'] = 'official'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'sealed'): subject.run(self.root)
        data['execution']['mode'] = 'publisher-smoke'
        path.write_text(json.dumps(data)); self.smoke.touch()
        with self.assertRaisesRegex(ValueError, 'already exists'): subject.run(self.root)


if __name__ == '__main__': unittest.main()
