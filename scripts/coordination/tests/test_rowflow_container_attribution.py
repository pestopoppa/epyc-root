"""Container attribution for GPU ownership (vllm-aiter-gfx90a-gpu-20261111-r3, 2026-11-12).

The row's own vLLM ran inside a docker container launched by the job. Container processes are children of
containerd-shim, not of the job, so descendant-based ownership read the pid as a FOREIGN KFD client and wrote
CONTAMINATED.json. own_pids now also counts KFD clients whose container carries DOCKER_ROW_LABEL=<row id>
(stamped by filler_run15's docker shim). An unlabelled or other-row container stays foreign.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_RF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow")
sys.path.insert(0, _RF)
import rowflow  # noqa: E402

RID = "vllm-row"
CIDS = {700: "a" * 64, 800: "b" * 64, 900: "c" * 64}          # pid -> container id
LABELS = {"a" * 64: RID, "b" * 64: "", "c" * 64: "other-row"}  # container id -> row label


class ContainerAttribution(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="rowflow-container-attrib-")
        self.alerts = []
        rowflow._CONTAINER_ROW.clear()
        self.patches = [
            mock.patch.object(rowflow, "route_alert", lambda kind, msg, ev, log=print: self.alerts.append((kind, ev)) or True),
            mock.patch.object(rowflow, "tree_pids", lambda pg: {100: {100, 101}}.get(pg, set())),
            mock.patch.object(rowflow, "row_leaf_pids", lambda rid: (False, set())),
            mock.patch.object(rowflow, "pid_container_id", lambda q: CIDS.get(q)),
            mock.patch.object(rowflow, "docker_row_label", side_effect=lambda cid: LABELS.get(cid)),
        ]
        for p in self.patches:
            p.start()
        self.g = {"id": RID, "holds": {rowflow.GPU}, "pid": 100}

    def tearDown(self):
        for p in self.patches:
            p.stop()
        rowflow._CONTAINER_ROW.clear()
        shutil.rmtree(self.d, ignore_errors=True)

    def test_labelled_container_pid_is_ours(self):
        occ = {"pids": {700: 9 << 30}, "vram_used": 9 << 30}
        own = rowflow.own_pids(self.d, self.g, occ["pids"])
        self.assertIn(700, own)
        self.assertEqual(rowflow.gpu_foreign(occ, own), ([], 0))

    def test_unlabelled_and_other_row_containers_are_foreign(self):
        occ = {"pids": {800: 5 << 30, 900: 4 << 30}}
        own = rowflow.own_pids(self.d, self.g, occ["pids"])
        self.assertNotIn(800, own)
        self.assertNotIn(900, own)
        self.assertEqual(rowflow.gpu_foreign(occ, own), ([800, 900], 9 << 30))

    def test_non_container_descendant_is_ours(self):
        occ = {"pids": {101: 3 << 30, 555: 2 << 30}}
        own = rowflow.own_pids(self.d, self.g, occ["pids"])
        self.assertIn(101, own)
        self.assertNotIn(555, own, "a non-container, non-descendant pid stays foreign")

    def test_docker_unreachable_is_foreign_and_not_cached(self):
        with mock.patch.object(rowflow, "docker_row_label", return_value=None):
            self.assertNotIn(700, rowflow.own_pids(self.d, self.g, [700]))
        self.assertNotIn("a" * 64, rowflow._CONTAINER_ROW)
        self.assertIn(700, rowflow.own_pids(self.d, self.g, [700]))

    def test_label_lookup_is_cached_per_container(self):
        rowflow.own_pids(self.d, self.g, [700, 800])
        rowflow.own_pids(self.d, self.g, [700, 800])
        self.assertEqual(rowflow.docker_row_label.call_count, 2)

    def test_container_pid_of_cpu_grant_is_a_fence_breach(self):
        g = {"id": RID, "holds": {"q0"}, "pid": 100}
        lines = []
        hits = rowflow.gpu_fence_breach(self.d, [g], lines.append, set(), occ={"pids": {700: 1 << 30, 800: 1 << 30}})
        self.assertEqual(hits, [(RID, 700)])

    def test_own_pids_without_candidates_unchanged(self):
        self.assertEqual(rowflow.own_pids(self.d, self.g), {100, 101})


if __name__ == "__main__":
    unittest.main()
