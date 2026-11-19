import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publish


class PublicationBindingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inventory = self.root / 'inputs.json'
        self.inventory.write_text(json.dumps({'row': 'p9-test'}))
        self.digest = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
        self.launcher = self.root / 'launch.sh'
        commands = ' '.join(f'{flag} "python3 $D/runtime.py {action} {self.digest}"'
                            for flag, action in [('--precond-cmd', 'inputs'), ('--cmd', 'run'), ('--complete-cmd', 'check')])
        self.launcher.write_text(f'#!/bin/bash\nD={self.root}\nexec bash engine {commands}\n')
        self.spec = dict(id='p9-test', launcher=str(self.launcher),
                         smoke_predicate=f'python3 {self.root}/runtime.py predicate {self.digest}')

    def test_accepts_bound_source_and_sealed_launcher(self):
        self.assertEqual(publish.validate(self.spec, self.inventory), self.digest)
        self.spec['launcher'] = dict(path=str(self.launcher), sha256=hashlib.sha256(self.launcher.read_bytes()).hexdigest())
        self.assertEqual(publish.validate(self.spec, self.inventory), self.digest)

    def test_rejects_stale_queued_predicate(self):
        self.spec['smoke_predicate'] = self.spec['smoke_predicate'].replace(self.digest, 'a' * 64)
        with self.assertRaisesRegex(ValueError, 'predicate inventory'):
            publish.validate(self.spec, self.inventory)

    def test_rejects_each_stale_launcher_command(self):
        original = self.launcher.read_text()
        for action in ('inputs', 'run', 'check'):
            with self.subTest(action=action):
                self.launcher.write_text(original.replace(action + ' ' + self.digest, action + ' ' + 'a' * 64))
                with self.assertRaisesRegex(ValueError, 'launcher inventory'):
                    publish.validate(self.spec, self.inventory)

    def test_rejects_changed_inventory_and_wrong_row(self):
        self.inventory.write_text(json.dumps({'row': 'p9-test', 'revision': 2}))
        with self.assertRaisesRegex(ValueError, 'launcher inventory'):
            publish.validate(self.spec, self.inventory)
        self.spec['id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'row identity'):
            publish.validate(self.spec, self.inventory)

    def test_rejects_launcher_tamper_directory_and_duplicate_commands(self):
        original = self.launcher.read_text()
        spec = copy.deepcopy(self.spec)
        spec['launcher'] = dict(path=str(self.launcher), sha256='a' * 64)
        with self.assertRaisesRegex(ValueError, 'launcher digest'):
            publish.validate(spec, self.inventory)
        for source in (original.replace('D=' + str(self.root), 'D=/wrong'), original + 'exec bash other\n',
                       original.replace('--cmd', '--precond-cmd')):
            self.launcher.write_text(source)
            with self.assertRaises(ValueError):
                publish.validate(self.spec, self.inventory)

    def test_invalid_submission_never_calls_publisher(self):
        self.spec['smoke_predicate'] += ' extra'
        spec_path = self.root / 'spec.json'
        spec_path.write_text(json.dumps(self.spec))
        with patch.object(publish.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                publish.main(['--spec', str(spec_path), '--inventory', str(self.inventory), '--publish'])
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
