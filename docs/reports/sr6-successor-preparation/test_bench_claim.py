import json
import os
import time
import unittest
from unittest.mock import patch

import bench_claim


class FakeGuard:
    LOCK_ROOT = '/mnt/raid0/llm/tmp'
    def __init__(self):
        self.owner = os.getpid() + 100000
        self.paths = {}
        for i, role in enumerate(('GLOBAL', 'bench')):
            for j, q in enumerate(bench_claim._QUADS):
                name = f'{self.LOCK_ROOT}/cpu_region.{role}.{q}.lock'
                payload = {'schema_version': 1, 'pid': self.owner, 'role': 'bench', 'region': q,
                           'regions': list(bench_claim._QUADS), 'request_tag': 'filler-test', 'started_at': time.time()}
                self.paths[name] = ((1, i * 4 + j + 1), json.dumps(payload).encode())
        self.paths[f'{self.LOCK_ROOT}/gpu_quiet.lock'] = ((1, 9), b'')
        self.locks = {identity: {self.owner} for identity, _ in self.paths.values()}
    def safe_root(self): return (1, 1)
    def ancestors(self): return {self.owner: (42, os.getuid())}
    def proc_lock_owners(self): return self.locks
    def open_identity(self, path): return self.paths[path]
    def dev_inode(self, identity): return identity
    def proc_stat(self, pid): return (1, 42, os.getuid())


class BenchClaimTest(unittest.TestCase):
    def setUp(self):
        self.g = FakeGuard()
        self.env = patch.dict(os.environ, {'ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT': '1'})
        self.env.start()
        self.addCleanup(self.env.stop)
    def test_complete_bench_claim(self):
        self.assertIs(bench_claim._admit(self.g, 'test'), True)
    def test_quiet_must_be_exclusive_and_owned(self):
        self.g.locks.pop((1, 9))  # no WRITE flock, including a shared-only quiet claim
        with self.assertRaises(ValueError): bench_claim._admit(self.g, 'test')
    def test_wrong_tag_or_role_rejected(self):
        path = f'{self.g.LOCK_ROOT}/cpu_region.bench.q0.lock'
        identity, raw = self.g.paths[path]
        for key, value in [('request_tag', 'filler-other'), ('role', 'build')]:
            data = json.loads(raw); data[key] = value
            self.g.paths[path] = identity, json.dumps(data).encode()
            with self.subTest(key=key), self.assertRaises(ValueError): bench_claim._admit(self.g, 'test')
        self.g.paths[path] = identity, raw
    def test_missing_global_and_changed_owner_refused(self):
        self.g.locks.pop((1, 1))
        with self.assertRaises(ValueError): bench_claim._admit(self.g, 'test')
        self.g = FakeGuard()
        self.g.proc_stat = lambda pid: (1, 43, os.getuid())
        with self.assertRaises(ValueError): bench_claim._admit(self.g, 'test')
    def test_replaced_lock_and_disabled_global_refused(self):
        real = self.g.open_identity
        count = [0]
        def changed(path):
            count[0] += 1
            identity, data = real(path)
            return ((1, 50), data) if count[0] == 10 else (identity, data)
        self.g.open_identity = changed
        with self.assertRaises(ValueError): bench_claim._admit(self.g, 'test')
        with patch.dict(os.environ, {'ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT': '0'}):
            with self.assertRaises(ValueError): bench_claim._admit(FakeGuard(), 'test')
    def test_digest_mismatch_refused(self):
        self.assertIs(bench_claim.FullHostBenchClaim('test', '0' * 64)(), False)


if __name__ == '__main__': unittest.main()
