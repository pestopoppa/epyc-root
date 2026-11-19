"""Private lock/proc fixtures; no GPU, official lock, grant or model work."""
import copy
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('publisher_pair_subject', HERE / 'publisher_provider.py')
provider = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider)


class PublisherProvider(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.device, self.quiet = self.root / 'device', self.root / 'quiet'
        self.device.touch(); self.quiet.touch()
        self.proc = self.root / 'proc'
        self.lineage = [101, 102, 103]
        self.ids = {pid: (os.getuid(), pid * 10) for pid in self.lineage}
        self.sources = {'native source fixture': 'a' * 64}
        self.record = {'schema': 'epyc.orchestrator.gpu_quiet_holder.v1',
                       'pid': 103, 'start_ticks': 1030, 'role': 'bench', 'mode': 'shared',
                       'lock_path': str(self.quiet), 'request_tag': 'filler-pair-test'}
        self.status = {'path': str(self.quiet), 'held': True, 'mode': 'shared',
                       'holders': [self.record]}
        self.owners = {103: 'shared'}
        self.native = NS(holders=lambda: copy.deepcopy(self.status),
                         lock_owners=lambda _: dict(self.owners))
        self.previous = NS(LOCK=self.quiet, source_digests=lambda: dict(self.sources),
                           provider=lambda: self.native, ancestors=lambda: self.lineage,
                           identity=lambda pid: self.ids[pid])
        self.inner(102)
        self.env = {'FILLER_ID': 'pair-test', 'FILLER_SMOKE': '1', 'FILLER_DRYRUN': '1',
                    'FILLER_DRYRUN_DIR': str(self.root / 'dryrun/pair-test'),
                    'FILLER_GRANTS_DIR': str(self.root / 'dryrun/pair-test/grants')}
        real_writer = provider.device_writer
        for context in (patch.object(provider, 'DEVICE', self.device),
                        patch.object(provider, 'FLAGS', self.root),
                        patch.object(provider, 'legacy', return_value=self.previous),
                        patch.object(provider, 'device_writer',
                                     side_effect=lambda *args: real_writer(*args, proc_root=self.proc)),
                        patch.dict(os.environ, self.env, clear=True)):
            context.start(); self.addCleanup(context.stop)

    def inner(self, pid):
        root = self.proc / str(pid)
        (root / 'fd').mkdir(parents=True)
        (root / 'fdinfo').mkdir()
        (root / 'fd/9').symlink_to(self.device)
        argv = ['/bin/bash', provider.ENGINE, '--inner', '--id', 'pair-test',
                '--class', 'gpu', '--cmd', 'inert fixture']
        (root / 'cmdline').write_bytes(('\0'.join(argv) + '\0').encode())
        st = self.device.stat()
        self.lock_line = (f'lock:\t1: FLOCK ADVISORY WRITE 999 '
                          f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino} 0 EOF\n')
        (root / 'fdinfo/9').write_text('flags:\t0100001\n' + self.lock_line)

    def capture(self):
        return provider.capture('pair-test', self.sources)

    def test_pair_is_retained_and_never_relabels_shared_as_exclusive(self):
        witness = self.capture()
        self.assertEqual(witness['quiet_owner'], 103)
        self.assertEqual(witness['device_writer']['pid'], 102)
        self.assertEqual(witness['mode'], 'publisher-shared-quiet-device-writer-v1')
        self.assertTrue(provider.recheck(witness))
        self.assertEqual(self.status['mode'], 'shared')
        self.assertEqual(self.record['mode'], 'shared')

    def test_official_legacy_rejects_actual_publisher_lock_shape(self):
        # Reproduce the existing provider's mismatch without taking real locks.
        raw = provider.LEGACY.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), provider.LEGACY_SHA)
        module = NS()
        exec(compile(raw, str(provider.LEGACY), 'exec'), module.__dict__)
        module.LOCK = self.quiet
        with self.assertRaisesRegex(ValueError, 'exclusive'):
            module.validate(self.status, self.owners, self.lineage,
                            self.ids, os.getuid(), 'pair-test')

    def test_explicit_smoke_only_and_canonical_namespaces(self):
        for key in self.env:
            with self.subTest(key=key), patch.dict(os.environ, {key: 'other'}):
                with self.assertRaises(ValueError): self.capture()
        with patch.dict(os.environ, {'FILLER_GPU_LOCK': '/private/device'}):
            with self.assertRaisesRegex(ValueError, 'identity'): self.capture()

    def test_shared_quiet_requires_one_kernel_owner_and_real_attribution(self):
        for owners in ({}, {103: 'exclusive'}, {102: 'shared', 103: 'shared'}, {999: 'shared'}):
            with self.subTest(owners=owners), patch.object(self, 'owners', owners):
                with self.assertRaises(ValueError): self.capture()
        for key, value in (('mode', 'exclusive'), ('held', False), ('path', '/private/quiet'),
                           ('holders', []), ('holders', [self.record, self.record])):
            old = self.status[key]
            self.status[key] = value
            with self.subTest(key=key):
                with self.assertRaises(ValueError): self.capture()
            self.status[key] = old

    def test_holder_row_uid_birth_and_verification_required(self):
        for key, value in (('pid', 102), ('start_ticks', 1), ('role', 'serve'),
                           ('mode', 'exclusive'), ('verified', False),
                           ('request_tag', 'filler-other'), ('lock_path', '/private/quiet'),
                           ('schema', 'unattributed')):
            with self.subTest(key=key), patch.dict(self.record, {key: value}):
                with self.assertRaises(ValueError): self.capture()
        with patch.dict(self.ids, {103: (os.getuid() + 1, 1030)}):
            with self.assertRaises(ValueError): self.capture()

    def test_device_owner_must_be_unique_inner_descendant_with_matching_row(self):
        path = self.proc / '102/cmdline'
        original = path.read_bytes()
        for old, new in ((b'pair-test', b'other-row'), (b'--inner', b'--outer'),
                         (provider.ENGINE.encode(), b'/private/engine'),
                         (b'--class\0gpu', b'--class\0cpu')):
            path.write_bytes(original.replace(old, new))
            with self.subTest(new=new):
                with self.assertRaisesRegex(ValueError, 'inner engine'): self.capture()
        path.write_bytes(original)
        with patch.dict(self.ids, {102: (os.getuid() + 1, 1020)}):
            with self.assertRaisesRegex(ValueError, 'foreign'): self.capture()
        self.inner(101)
        with self.assertRaisesRegex(ValueError, 'one captured'): self.capture()
        with patch.object(self, 'lineage', [103, 102, 101]):
            with self.assertRaisesRegex(ValueError, 'one captured'): self.capture()

    def test_device_lock_missing_read_waiter_and_wrong_device_or_inode_refuse(self):
        path = self.proc / '102/fdinfo/9'
        st = self.device.stat()
        identity = f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}'
        for value in ('', self.lock_line.replace('WRITE', 'READ'),
                      self.lock_line.replace('FLOCK', '-> FLOCK'),
                      self.lock_line.replace(' 0 EOF', ' 1 EOF'),
                      self.lock_line.replace(identity, f'ff:ff:{st.st_ino}'),
                      self.lock_line.replace(identity, f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino + 1}'),
                      self.lock_line + self.lock_line):
            path.write_text(value)
            with self.subTest(value=value):
                with self.assertRaises(ValueError): self.capture()
        path.write_text(self.lock_line)
        fd = self.proc / '102/fd/9'
        fd.unlink()
        with self.assertRaises(ValueError): self.capture()

    def test_device_descriptor_change_inside_capture_refuses(self):
        info = self.proc / '102/fdinfo/9'
        fd = self.proc / '102/fd/9'
        replacement = self.root / 'other-device'
        replacement.touch()
        original = Path.read_text
        def swapped(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path == info:
                fd.unlink(); fd.symlink_to(replacement)
            return result
        with patch.object(Path, 'read_text', swapped):
            with self.assertRaisesRegex(ValueError, 'descriptor changed'): self.capture()

    def test_quiet_inode_replacement_during_capture_refuses(self):
        original = provider.device_writer.side_effect
        replacement = self.root / 'quiet-replacement'
        replacement.touch()
        def swapped(*args):
            result = original(*args)
            replacement.replace(self.quiet)
            return result
        with patch.object(provider, 'device_writer', side_effect=swapped):
            with self.assertRaisesRegex(ValueError, 'quiet lock file replaced'): self.capture()

    def test_actual_kernel_fdinfo_and_flock_utility_inheritance(self):
        # Model-free lock fixture only; all descriptors belong to this test.
        fd = os.open(self.device, os.O_WRONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            actual = Path(f'/proc/self/fdinfo/{fd}').read_text()
            (self.proc / '102/fdinfo/9').write_text(actual)
            self.capture()
        finally:
            os.close(fd)
        result = subprocess.run(
            ['/bin/bash', '-c', 'exec 9>"$1"; flock -x 9; cat /proc/self/fdinfo/9',
             'publisher-lock-fixture', str(self.device)],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.proc / '102/fdinfo/9').write_text(result.stdout)
        self.capture()

    def test_source_and_ancestor_changes_before_and_during_capture(self):
        with patch.object(self.previous, 'source_digests', return_value={}):
            with self.assertRaisesRegex(ValueError, 'source drift'): self.capture()
        calls = iter([self.sources, {}])
        with patch.object(self.previous, 'source_digests', side_effect=lambda: next(calls)):
            with self.assertRaisesRegex(ValueError, 'during capture'): self.capture()
        original = self.previous.identity
        calls = []
        def identity(pid):
            calls.append(pid)
            return original(pid) if len(calls) <= 3 else (os.getuid(), -1)
        with patch.object(self.previous, 'identity', side_effect=identity):
            with self.assertRaisesRegex(ValueError, 'ancestor changed'): self.capture()

    def test_recheck_cannot_accept_replacement_writer_or_quiet_inode(self):
        witness = self.capture()
        self.ids[102] = (os.getuid(), 1021)
        with self.assertRaisesRegex(ValueError, 'no longer retained'): provider.recheck(witness)
        self.ids[102] = (os.getuid(), 1020)
        replacement = self.root / 'replacement'
        replacement.touch(); replacement.replace(self.quiet)
        with self.assertRaisesRegex(ValueError, 'no longer retained'): provider.recheck(witness)


if __name__ == '__main__': unittest.main()
