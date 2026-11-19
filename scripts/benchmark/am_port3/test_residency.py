from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import residency as r


class Residency(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bindir = self.root / 'bin'
        self.bindir.mkdir()
        self.proc = self.root / 'proc'
        (self.proc / '42').mkdir(parents=True)
        self.kfd = self.root / 'kfd'
        (self.kfd / '42').mkdir(parents=True)
        (self.kfd / '42/vram_1').write_text('4096')
        self.device = self.root / 'device'
        self.device.write_text('8192')
        self.maps(['libllama.so', 'libggml-base.so', 'libggml-hip.so'])

    def maps(self, names):
        (self.proc / '42/maps').write_text('\n'.join('0-1 r-xp 0 0 0 ' + str(self.bindir / n) for n in names))

    def sample(self, gpu=True):
        return r.sample(42, self.bindir, gpu, self.device, proc_root=self.proc, kfd_root=self.kfd)

    def test_live_linkage_own_and_device_vram(self):
        s = self.sample()
        self.assertEqual(s['pid'], 42)
        self.assertEqual(s['own_vram_bytes'], 4096)
        self.assertEqual(s['device_vram_bytes'], 8192)
        self.assertEqual(s['kfd_process_count'], 1)
        self.assertEqual(len(s['libraries']), 3)

    def test_missing_backend_or_memory_is_unsampled_not_negative_proof(self):
        self.maps(['libllama.so', 'libggml-base.so'])
        self.assertIsNone(self.sample())
        self.assertIsNotNone(self.sample(gpu=False))
        self.maps(['libllama.so', 'libggml-base.so', 'libggml-hip.so'])
        (self.kfd / '42/vram_1').unlink()
        self.assertIsNone(self.sample())

    def test_foreign_mapped_backend_refused(self):
        with (self.proc / '42/maps').open('a') as f:
            f.write('\n0-1 r-xp 0 0 0 /elsewhere/libggml-cpu.so')
        with self.assertRaisesRegex(ValueError, 'foreign'):
            self.sample()

    def test_own_or_device_over_budget_refused(self):
        for path in (self.device, self.kfd / '42/vram_1'):
            original = path.read_text()
            path.write_text(str(r.BUDGET + 1))
            with self.assertRaisesRegex(ValueError, '36 GiB'):
                self.sample()
            path.write_text(original)

    def test_terminate_escalates_only_owned_child_and_reaps(self):
        class Child:
            returncode = None
            calls = []
            def poll(self): return self.returncode
            def terminate(self): self.calls.append('term')
            def kill(self): self.calls.append('kill'); self.returncode = -9
            def wait(self, timeout):
                self.calls.append('wait')
                if self.returncode is None:
                    raise subprocess.TimeoutExpired('owned', timeout)
        child = Child()
        r.stop(child)
        self.assertEqual(child.calls, ['term', 'wait', 'kill', 'wait'])
        self.assertEqual(child.poll(), -9)

    def executor(self, samples):
        class Child:
            pid, returncode, waits = 42, None, 0
            def poll(self): return self.returncode
            def wait(self, timeout):
                self.waits += 1
                if self.waits < 3:
                    raise subprocess.TimeoutExpired('owned', timeout)
                self.returncode = 0
            def terminate(self): self.returncode = -15
        child = Child()
        runner = r.Executor(self.root / 'execution', self.bindir, gpu=True, device=self.device)
        with patch.object(r.subprocess, 'Popen', return_value=child) as popen, patch.object(r, 'sample', side_effect=samples):
            result = runner(['/fixture'], env={'LLAMA_KV_AM_BETA': '1'})
            env = popen.call_args.kwargs['env']
            self.assertNotIn('LLAMA_KV_AM_BETA', env)
            self.assertEqual(env['LD_LIBRARY_PATH'], str(self.bindir))
            return result

    def test_executor_requires_two_live_samples_and_seals(self):
        result = self.executor([None, {'pid': 42}, {'pid': 42}])
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.root / 'execution/EXECUTION.json').exists())

    def test_executor_refuses_missed_window_without_completion(self):
        with self.assertRaisesRegex(ValueError, 'two live'):
            self.executor([None, None, {'pid': 42}])
        self.assertFalse((self.root / 'execution/EXECUTION.json').exists())


if __name__ == '__main__':
    unittest.main()
