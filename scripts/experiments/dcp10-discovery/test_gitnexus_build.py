"""Offline failure and receipt controls; never invoke the native index builder."""
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import gitnexus_build as build


class BuildControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.assets = Path(self.temp.name)
        self.assets.chmod(0o700)
        self.base = {'root': '/original/base', 'base_commit': 'base', 'base_tree': 'tree', 'query_sha256': 'issue'}
        self.task = {'language': 'python'}
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for owner, key, value in (
            (build.native, 'original_tasks', lambda: {'original': self.task}),
            (build, 'task_binding', lambda _: self.base),
            (build, 'producer_identity', lambda: {'builder': 'source'}),
            (build, 'inventory', lambda _: {'module': 'pinned'}),
            (build.native, 'writer_identity', lambda: {'version': 'pinned'}),
            (build.native, 'check_custody', lambda _: None),
            (build.native, 'seal_file', lambda *_: None),
            (build.os, 'geteuid', lambda: 1000),
            (build.shutil, 'which', lambda _: '/usr/bin/docker'),
        ):
            self.stack.enter_context(patch.object(owner, key, value))
        self.request_sha = build.prepare(self.assets)
        self.cleanup = self.stack.enter_context(patch.object(build.native, 'remove_container'))

    def fake_build(self, command, env, payload, timeout):
        index = self.assets / 'work-python/index'
        index.mkdir()
        (index / 'lbug').write_bytes(b'synthetic database')
        build.write_new(index / 'meta.json', {'repoPath': self.base['root'], 'lastCommit': 'base',
                                            'stats': {'files': 1, 'nodes': 2, 'edges': 1, 'embeddings': 0}})
        return subprocess.CompletedProcess(command, 0, b'synthetic progress', b'')

    def run_build(self, effect=None):
        with patch.object(build.native, 'read_bounded', side_effect=effect or self.fake_build) as launch:
            digest = build.build_private_index(self.assets, self.request_sha, 'original', lambda cap: cap)
        return digest, launch

    def test_checkpointed_receipt_is_consumed_by_existing_reader(self):
        digest, launch = self.run_build()
        index, receipt = self.assets / 'indexes/python', self.assets / 'index-builds/python.json'
        snapshot = build.native.index_identity(index, receipt, digest, task_id='original',
                                                base=self.base, writer={'version': 'pinned'})
        self.assertEqual(set(snapshot), {'lbug', 'meta.json'})
        self.cleanup.assert_called_once()
        command = launch.call_args.args[0]
        self.assertIn('--network=none', command)
        self.assertIn('--read-only', command)
        self.assertIn('--cpus=4', command)
        self.assertIn('--pids-limit=256', command)
        image = command.index(build.native.IMAGE)
        self.assertTrue(all(command.index(option) < image for option in ('--tmpfs', '--mount')))
        mounts = [command[i + 1] for i, option in enumerate(command) if option == '--mount']
        self.assertEqual(sum('readonly' not in item for item in mounts), 1)
        self.assertTrue(any('dst=/original/base,readonly' in item for item in mounts))
        self.assertFalse((self.assets / 'work-python').exists())

    def test_nonzero_and_diagnostics_do_not_issue_receipts(self):
        with (patch.object(build.native, 'read_bounded', return_value=subprocess.CompletedProcess([], 1, b'', b'failed')),
              self.assertRaises(build.native.QueryError)):
            build.build_private_index(self.assets, self.request_sha, 'original', lambda cap: cap)
        self.cleanup.assert_called_once()
        self.assertFalse((self.assets / 'index-builds').exists())

    def test_timeout_cleanup_and_post_snapshot(self):
        with patch.object(build, 'inventory', side_effect=[{'module': 'pinned'}, {'module': 'changed'}]), \
             patch.object(build.native, 'read_bounded', side_effect=build.native.QueryError('timeout')), \
             self.assertRaisesRegex(ValueError, 'source/base/request drift'):
            build.build_private_index(self.assets, self.request_sha, 'original', lambda cap: cap)
        self.cleanup.assert_called_once()
        self.assertFalse((self.assets / 'index-builds').exists())

    def test_sidecars_refused_without_cleanup_deletion(self):
        def sidecar(*args):
            result = self.fake_build(*args)
            (self.assets / 'work-python/index/lbug.wal').write_bytes(b'uncommitted')
            return result
        with self.assertRaisesRegex(ValueError, 'sidecars'):
            self.run_build(sidecar)
        self.assertTrue((self.assets / 'work-python/index/lbug.wal').exists())
        self.assertFalse((self.assets / 'index-builds').exists())

    def test_source_drift_refused_before_launch(self):
        with patch.object(build, 'inventory', return_value={'module': 'changed'}), \
             patch.object(build.native, 'read_bounded') as launch, \
             self.assertRaisesRegex(ValueError, 'source/base/request drift'):
            build.build_private_index(self.assets, self.request_sha, 'original', lambda cap: cap)
        launch.assert_not_called()

    def test_task_substitution_and_repeat_attempt_refused(self):
        with self.assertRaisesRegex(ValueError, 'outside original cohort'):
            build.build_private_index(self.assets, self.request_sha, 'replacement', lambda cap: cap)
        (self.assets / 'work-python').mkdir()
        with self.assertRaises(FileExistsError):
            self.run_build()


class SourceControls(unittest.TestCase):
    def test_inventory_rejects_external_links_and_binds_internal_links(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'module.js').write_bytes(b'one')
            (root / 'internal').symlink_to('module.js')
            first = build.inventory(root)
            self.assertEqual(first['internal'], {'link': 'module.js'})
            (root / 'module.js').write_bytes(b'two')
            self.assertNotEqual(first, build.inventory(root))
            (root / 'outside').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                build.inventory(root)

    def test_worker_syntax(self):
        subprocess.run([build.native.NODE, '--check', build.WORKER], check=True, timeout=10)


if __name__ == '__main__':
    unittest.main()
