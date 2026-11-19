"""Offline failure and receipt controls; never invoke the native index builder."""
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, nullcontext
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
            (build, 'mount_binding', lambda task, base, root: str(root)),
            (build, 'producer_identity', lambda: {'builder': 'source'}),
            (build, 'inventory', lambda _: {'module': 'pinned'}),
            (build.native, 'writer_identity', lambda: {'version': 'pinned'}),
            (build, 'check_build_path', lambda _: None),
            (build, 'pinned_mounts', lambda _: nullcontext({})),
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
        self.assertTrue(all('bind-propagation=rprivate' in item for item in mounts if 'readonly' in item))
        self.assertTrue(any('dst=/original/base,readonly' in item for item in mounts))
        self.assertFalse((self.assets / 'work-python').exists())

    def test_nonzero_and_diagnostics_do_not_issue_receipts(self):
        with (patch.object(build.native, 'read_bounded', return_value=subprocess.CompletedProcess([], 1, b'', b'failed')),
              self.assertRaises(build.native.QueryError)):
            build.build_private_index(self.assets, self.request_sha, 'original', lambda cap: cap)
        self.cleanup.assert_called_once()
        self.assertFalse((self.assets / 'index-builds').exists())

    def test_timeout_cleanup_and_post_snapshot(self):
        with patch.object(build, 'inventory', side_effect=[{'module': 'pinned'}, {'module': 'pinned'}, {'module': 'changed'}]), \
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

    def test_host_mount_preserves_logical_payload_and_receipt(self):
        other = self.assets / 'fresh'
        other.mkdir(mode=0o700)
        self.assets = other
        host = '/trusted/row/bases/python'
        self.request_sha = build.prepare(other, {'original': host})
        digest, launch = self.run_build()
        command, _, payload, _ = launch.call_args.args
        self.assertIn(f'type=bind,src={host},dst=/original/base,readonly,bind-recursive=readonly,bind-propagation=rprivate', command)
        self.assertEqual(build.native.graph.strict_json(payload)['base'], self.base)
        receipt = other / 'index-builds/python.json'
        admitted = build.native.read_record(receipt, digest)
        self.assertEqual(admitted['base'], self.base)
        manifest = build.native.graph.strict_json(receipt.with_suffix('.manifest.json').read_bytes())
        self.assertEqual(manifest['mount_base'], host)

    def test_mount_layout_refuses_missing_and_extra_tasks(self):
        for mapping in ({}, {'original': '/host', 'replacement': '/other'}):
            with self.subTest(mapping=mapping), self.assertRaisesRegex(ValueError, 'exactly the original tasks'):
                build.mount_layout({'original': self.task}, {'original': self.base}, mapping)

    def test_host_base_drift_prevents_launch(self):
        with (patch.object(build, 'mount_binding', side_effect=ValueError('host base drift')),
              patch.object(build.native, 'read_bounded') as launch,
              self.assertRaisesRegex(ValueError, 'host base drift')):
            build.build_private_index(self.assets, self.request_sha, 'original', lambda cap: cap)
        launch.assert_not_called()
        self.assertFalse((self.assets / 'index-builds').exists())


class HostWorktreeControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git(self.repo, 'init', '-q')
        (self.repo / 'alpine.py').write_text('def alpine(): return 42\n')
        self.git(self.repo, 'add', 'alpine.py')
        self.git(self.repo, '-c', 'user.name=DCP fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'fixture')
        self.commit = self.git(self.repo, 'rev-parse', 'HEAD')
        self.host = self.root / 'trusted/bases/python'
        self.host.parent.mkdir(parents=True)
        self.git(self.repo, 'worktree', 'add', '--detach', str(self.host), self.commit)
        self.task = {'language': 'python', 'base_commit': self.commit, 'query': 'find alpine'}
        self.base = {'root': '/original/bases/python', 'base_commit': self.commit,
                     'base_tree': self.git(self.host, 'rev-parse', 'HEAD^{tree}'),
                     'query_sha256': build.native.sha256(b'find alpine').hexdigest()}
        # /tmp is deliberately untrusted in production. Only fixture ancestry is
        # bypassed here; all real Git/content/scope checks execute unchanged.
        self.custody = patch.object(build.native, 'check_custody')
        self.custody.start()
        self.addCleanup(self.custody.stop)

    def git(self, root, *args):
        result = subprocess.run(['git', '-C', str(root), *args], check=True,
                                capture_output=True, text=True, timeout=10)
        return result.stdout.strip()

    def test_exact_detached_original_base_is_accepted(self):
        self.assertEqual(build.mount_binding(self.task, self.base, str(self.host)), str(self.host))
        self.assertEqual(self.base['root'], '/original/bases/python')

    def test_wrong_commit_tree_or_query_is_refused(self):
        for field in ('base_commit', 'base_tree', 'query_sha256'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                build.mount_binding(self.task, {**self.base, field: '0' * 40}, str(self.host))

    def test_dirty_or_untracked_checkout_is_refused(self):
        (self.host / 'untracked.py').write_text('untracked')
        with self.assertRaisesRegex(ValueError, 'local modifications'):
            build.mount_binding(self.task, self.base, str(self.host))
        (self.host / 'untracked.py').unlink()
        (self.host / 'alpine.py').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'local modifications'):
            build.mount_binding(self.task, self.base, str(self.host))

    def test_hidden_index_entries_are_refused(self):
        self.git(self.host, 'update-index', '--assume-unchanged', 'alpine.py')
        with self.assertRaisesRegex(ValueError, 'hidden or unmerged'):
            build.mount_binding(self.task, self.base, str(self.host))

    def test_ignored_files_are_refused(self):
        exclude = Path(self.git(self.host, 'rev-parse', '--git-path', 'info/exclude'))
        exclude.write_text('ignored.py\n')
        (self.host / 'ignored.py').write_text('ignored')
        with self.assertRaisesRegex(ValueError, 'ignored checkout files'):
            build.mount_binding(self.task, self.base, str(self.host))



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

    def test_named_mounts_and_descriptor_cleanup(self):
        with tempfile.TemporaryDirectory() as name:
            target = Path(name) / 'data'
            target.write_bytes(b'original')
            opened = []
            real_open = build.os.open

            def capture(*args):
                fd = real_open(*args)
                opened.append(fd)
                return fd

            with patch.object(build.native, 'check_custody'), patch.object(build.os, 'open', side_effect=capture):
                with build.pinned_mounts([target, target]) as pins:
                    self.assertEqual(pins, {target: target})
                    self.assertEqual(pins[target].read_bytes(), b'original')
                for fd in opened:
                    with self.assertRaises(OSError):
                        build.os.fstat(fd)

    def test_named_mount_replacement_refused_after_teardown(self):
        with tempfile.TemporaryDirectory() as name:
            parent = Path(name) / 'owned'
            parent.mkdir(mode=0o700)
            target = parent / 'data'
            target.write_bytes(b'original')
            with (patch.object(build.native, 'check_custody'), self.assertRaisesRegex(
                    build.native.IsolationError, 'changed while pinned'), build.pinned_mounts([target])):
                parent.rename(Path(name) / 'moved')
                parent.mkdir()
                target.write_bytes(b'replacement')

    def test_shared_scratch_exception_cannot_reach_docker(self):
        with tempfile.TemporaryDirectory() as name:
            shared = Path(name)
            shared.chmod(0o777)
            target = shared / 'owned'
            target.mkdir(mode=0o700)
            # Even the designated bookkeeping exception cannot authorize a mount.
            with (patch.object(build, 'SHARED_TMP', shared),
                  self.assertRaises(build.native.IsolationError), build.pinned_mounts([target])):
                self.fail('untrusted named mount admitted')

    def test_transport_refusal_prevents_launch_and_receipt(self):
        with (patch.object(build, 'pinned_mounts', side_effect=build.native.IsolationError('custody')),
              patch.object(build.native, 'read_bounded') as launch,
              patch.object(build.shutil, 'which', return_value='/usr/bin/docker'),
              patch.object(build.os, 'geteuid', return_value=1000),
              self.assertRaisesRegex(build.native.IsolationError, 'custody')):
            build.run_isolated(Path('/unused/output'), {'root': '/unused/base'}, 1, lambda: None)
        launch.assert_not_called()

    def test_custody_still_refuses_untrusted_leaf_and_symlink(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            root.chmod(0o777)
            with self.assertRaises(build.native.IsolationError):
                build.check_build_path(root)
            root.chmod(0o700)
            (root / 'link').symlink_to('/etc/passwd')
            with self.assertRaises(build.native.IsolationError):
                build.check_build_path(root / 'link')

    def test_worker_syntax(self):
        subprocess.run([build.native.NODE, '--check', build.WORKER], check=True, timeout=10)


if __name__ == '__main__':
    unittest.main()
