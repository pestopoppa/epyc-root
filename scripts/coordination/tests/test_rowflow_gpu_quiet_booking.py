"""A cpu self-claim row whose launcher says `--gpu-quiet exclusive` BOOKS the gpu-quiet token (quiet-host shape), so the
allocator never grants it while another grant or lease holds the GPU lock (inf22 recipe r2 stalled 17:43-17:53Z behind a
GPU-exclusive holder because its lease was taken inside the job, invisible to the allocator). Model-free, pure plan()."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), 'rowflow'))
import rowflow as rf  # noqa: E402

ENGINE = "/mnt/raid0/llm/tmp/x/source/scripts/coordination/rowflow/filler_run15.sh"


def _launcher(td, gpuq):
    p = os.path.join(td, "launch.sh")
    flag = f"--gpu-quiet {gpuq} " if gpuq else ""
    with open(p, "w") as f:
        f.write("#!/bin/bash\nset -euo pipefail\nexec bash %s --id r --class cpu --claim-cpus 0-95 --role bench --min-window 6900 "
                "--stop /x/STOP --workdir /x %s--self-claim --cmd '/x/job.sh' --complete-cmd '/x/c.py'\n" % (ENGINE, flag))
    return p


def _cand(td, gpuq):
    d = {"id": "r", "regions": "0-95", "launcher": {"path": _launcher(td, gpuq)}, "gib": 48}
    opts, bench = rf.row_shape(d)
    return {"id": "r", "kind": "grant", "lane": "cpu", "rank": 100.0, "lane_count": 0, "gib": 48, "bench": bench,
            "options": opts, "shape": rf.shape_of(d), "window_s": 8940}


class GpuQuietBooking(unittest.TestCase):
    def test_exclusive_flag_books_gpu_token_and_whole_host(self):
        with tempfile.TemporaryDirectory() as td:
            c = _cand(td, "exclusive")
            self.assertEqual(c["shape"], "quiet-host")
            self.assertTrue(all(rf.GPU in o and set(rf.QUARTERS) <= o for o in c["options"]))

    def test_not_granted_while_gpu_held_exclusive_elsewhere(self):
        with tempfile.TemporaryDirectory() as td:
            free = set(rf.QUARTERS)  # gpu-quiet busy (held EXCL by another grant): not in free
            assigned, _idle, pending = rf.plan(free, [_cand(td, "exclusive")], 900)
            self.assertEqual(assigned, [])

    def test_granted_with_gpu_token_when_everything_free(self):
        with tempfile.TemporaryDirectory() as td:
            assigned, _idle, _p = rf.plan(set(rf.REGIONS), [_cand(td, "exclusive")], 900)
            self.assertEqual(len(assigned), 1)
            self.assertIn(rf.GPU, assigned[0][1])

    def test_control_without_flag_ignores_gpu_lock(self):
        # the r2 shape: no --gpu-quiet in the launcher -> the allocator does not know about the GPU lock
        with tempfile.TemporaryDirectory() as td:
            c = _cand(td, "")
            self.assertTrue(all(rf.GPU not in o for o in c["options"]))
            assigned, _i, _p = rf.plan(set(rf.QUARTERS), [c], 900)
            self.assertEqual(len(assigned), 1)


if __name__ == "__main__":
    unittest.main()
