"""Model-free compatibility checks against the pinned native Sampler class."""
import ast
import hashlib
from pathlib import Path
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

import gpu_witness as g

NATIVE = Path('/mnt/raid0/llm/tmp/kvfork/g3-rowflow-prep-20261104/candidate/vendor/kpf18_gate.native.py')
PIN = '76bc6e18c9b58d4270d091c2b9f42358e2225aa6481585fbf4bbb9970424f4c9'


def native_sampler():
    raw = NATIVE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise ValueError('native sampler source changed')
    tree = ast.parse(raw)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Sampler')
    class Sink:
        def __init__(self, path): self.path, self.records = path, []
        def add(self, record): self.records.append(record)
    namespace = {'Path': Path, 'threading': threading, 'time': time, 'Jsonl': Sink, 'GIB': 1024**3}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(NATIVE), 'exec'), namespace)
    return namespace['Sampler']


class SamplerIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vram = self.root/'mem_info_vram_used'
        self.vram.write_text('100')
        self.device = {'device_vram': str(self.vram)}
        self.mechanism = types.SimpleNamespace(discover=lambda: self.device)
        self.gate = types.SimpleNamespace(Sampler=native_sampler())
        patches = [patch.object(g, 'pinned', return_value=b''),
                   patch.object(g, 'stat_identity', return_value=[1]),
                   patch.object(g, 'helper', return_value=self.mechanism),
                   patch.object(sys, 'argv', ['gate'])]
        for p in patches:
            p.start(); self.addCleanup(p.stop)
        g.install(self.gate)
        self.sampler = self.gate.Sampler(self.root/'samples', self.root, 1, None)
        self.sampler.own_pid = 42
        # Exactly one synchronous iteration, without sleeping or starting threads.
        self.sampler._stop = types.SimpleNamespace(is_set=lambda: bool(self.sampler.n), wait=lambda _: None)

    def test_resident_sample_updates_native_counts(self):
        sample = {'status': 'RESIDENT_SNAPSHOT', 'own_vram_bytes': 50}
        with patch.object(self.sampler.witness, 'sample', return_value=sample):
            self.sampler._run()
        summary = self.sampler.summary()
        self.assertEqual((summary['samples'], summary['own_vram_nonzero_samples']), (1, 1))
        self.assertEqual(self.sampler.sink.records[0]['owned_witness'], sample)
        self.assertEqual(summary['kfd_process_count_max_scope'], 'captured own PID only')
        self.assertFalse(self.sampler.abort.is_set())

    def test_unknown_does_not_count_as_residency(self):
        with patch.object(self.sampler.witness, 'sample', return_value={'status': 'UNKNOWN', 'own_vram_bytes': 0}):
            self.sampler._run()
        self.assertEqual(self.sampler.n_own_nonzero, 0)
        self.assertEqual(self.sampler.consec_own_zero, 1)
        self.assertEqual(self.sampler.sink.records[0]['status'], 'UNKNOWN')

    def test_identity_drift_aborts_without_residency(self):
        with patch.object(self.sampler.witness, 'sample', side_effect=ValueError('PID/birth changed')):
            self.sampler._run()
        self.assertTrue(self.sampler.abort.is_set())
        self.assertEqual(self.sampler.abort_reason, 'PID/birth changed')
        self.assertEqual(self.sampler.n_own_nonzero, 0)


if __name__ == '__main__':
    unittest.main()
