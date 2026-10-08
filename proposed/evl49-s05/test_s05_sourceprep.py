"""Synthetic, no-host tests for the S-05 receipt gate; no inference or I/O fixtures."""
import hashlib
import json
import os
from pathlib import Path
import unittest

import s05_sourceprep as s05


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(policy="interleave=all", cpus="0-95"):
    manifest = {
        "cell_id": "qwen36_q8_0-C1-np4-full",
        "instances": [{"port": 19080, "cpu_list": cpus, "numactl_policy": policy}],
    }
    digest = _sha(s05._canonical_json(manifest))
    launch = ["taskset", "-c", cpus]
    if policy == "interleave=all":
        launch += ["numactl", "--interleave=all"]
    launch += ["llama-server"]
    maps_ready = "00400000 default file=/bin/server\n10000000 interleave:0-3 anon=16 N0=8 N1=8\n"
    maps_after = "00400000 default file=/bin/server\n10000000 interleave:0-3 anon=18 N0=9 N1=9\n"
    if policy == "none":
        maps_ready = "10000000 default anon=16 N0=8 N1=8\n"
        maps_after = "10000000 default anon=18 N0=9 N1=9\n"
    evidence = {
        "manifest_sha256": digest,
        "provenance": {"research_commit": s05.SOURCE_COMMIT, "generator_blob": s05.GENERATOR_BLOB,
            "runbook_blob": s05.RUNBOOK_BLOB, "harness_blob": s05.SWEEP_HARNESS_BLOB,
            **{key: "e" * 64 for key in ("binary_sha256", "model_sha256", "input_sha256", "recipe_sha256", "admission_artifact_sha256")},
            "owner_window_admitted": True},
        "measurement_window": {"start_utc": "2026-10-08T00:00:02Z", "end_utc": "2026-10-08T00:00:04Z"},
        "cache_drop": {"argv": ["sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"], "start_utc": "2026-10-08T00:00:00Z", "end_utc": "2026-10-08T00:00:01Z", "exit_status": 0, "cached_kib_before": 100, "cached_kib_after": 10},
        "harness": {"exit_status": 0, "stdout_sha256": "a" * 64, "stderr_sha256": "b" * 64,
                    "cell_result_sha256": "c" * 64, "cell_result_cell_id": manifest["cell_id"]},
        "instances": [{"pid": 123, "start_ticks": 456, "launch_argv": launch, "cpus_allowed_list": cpus,
            "affinity_preflight": {"exit_status": 0, "live_affinity_verified": True, "observed_cpu_list": cpus,
                                   "artifact_sha256": "d" * 64},
            "numa_maps_ready": maps_ready, "numa_maps_after_cell": maps_after,
            "observation_times": {"ready": "2026-10-08T00:00:01Z", "during_cell": "2026-10-08T00:00:03Z", "after_cell": "2026-10-08T00:00:05Z"},
            "numa_maps_during_cell": maps_after, "numastat_during_cell": "Node 0 9 pages\nNode 1 9 pages\n",
            "pages_by_node_during_cell": {"N0": 9, "N1": 9},
            "numastat_ready": "Node 0 8 pages\nNode 1 8 pages\n",
            "numastat_after_cell": "Node 0 9 pages\nNode 1 9 pages\n",
            "pages_by_node_ready": {"N0": 8, "N1": 8}, "pages_by_node_after_cell": {"N0": 9, "N1": 9}}],
        "teardown": {"all_pids_dead": True},
    }
    return manifest, evidence


class ReceiptTests(unittest.TestCase):
    def test_full_machine_without_interleave_refused(self):
        manifest, evidence = _fixture(policy="none")
        with self.assertRaisesRegex(ValueError, "full-machine"):
            s05.validate_evidence(manifest, evidence)

    def test_smt_half_is_not_full_machine(self):
        for cpus in ("0-47,96-143", "48-95,144-191"):
            manifest, evidence = _fixture(cpus=cpus)
            with self.assertRaisesRegex(ValueError, "full-machine"):
                s05.validate_evidence(manifest, evidence)

    def test_posthoc_sample_refused(self):
        manifest, evidence = _fixture()
        evidence["instances"][0]["observation_times"]["during_cell"] = "2026-10-08T00:00:05Z"
        with self.assertRaisesRegex(ValueError, "overlap"):
            s05.validate_evidence(manifest, evidence)

    def test_missing_provenance_refused(self):
        manifest, evidence = _fixture()
        evidence.pop("provenance")
        with self.assertRaisesRegex(ValueError, "provenance"):
            s05.validate_evidence(manifest, evidence)

    def test_full_interleave_receipt_passes(self):
        manifest, evidence = _fixture()
        s05.validate_evidence(manifest, evidence)




    def test_affinity_disagreement_fails_closed(self):
        manifest, evidence = _fixture()
        evidence["instances"][0]["cpus_allowed_list"] = "0-47"
        with self.assertRaisesRegex(ValueError, "affinity"):
            s05.validate_evidence(manifest, evidence)

    def test_missing_pages_by_node_fails_closed(self):
        manifest, evidence = _fixture()
        evidence["instances"][0].pop("pages_by_node_after_cell")
        with self.assertRaisesRegex(ValueError, "pages_by_node"):
            s05.validate_evidence(manifest, evidence)

    def test_straddling_control_is_taskset_only(self):
        manifest, evidence = _fixture(policy="none", cpus="0-47,96-143")
        manifest["notes"] = s05.CONTROL_NOTE
        evidence["manifest_sha256"] = _sha(s05._canonical_json(manifest))
        evidence["instances"][0]["launch_argv"] = ["taskset", "-c", "0-47,96-143", "llama-server"]
        evidence["instances"][0]["cpus_allowed_list"] = "0-47,96-143"
        evidence["instances"][0]["affinity_preflight"]["observed_cpu_list"] = "0-47,96-143"
        s05.validate_evidence(manifest, evidence)


@unittest.skipUnless(os.environ.get("EPYC_RESEARCH_ROOT"), "hosted pinned-source check only")
class PinnedRosterTests(unittest.TestCase):
    def test_builds_only_current_stage_b_candidate(self):
        generator = s05._load_generator(Path(os.environ["EPYC_RESEARCH_ROOT"]).resolve())
        cells = s05.build_roster(generator)
        self.assertEqual(33, len(cells))
        self.assertEqual(10, sum(c.get("s05_shape_variant") == "full_machine_corrected" for c in cells))
        self.assertFalse(any(c.get("window") == "W0" for c in cells))
        for cell in cells:
            for instance in cell["instances"]:
                if instance["cpu_list"] == "0-95":
                    self.assertEqual("interleave=all", instance["numactl_policy"])
                elif instance["cpu_list"] in (generator.CPUSET_HALF0, generator.CPUSET_HALF1):
                    self.assertIn(s05.CONTROL_NOTE, cell["notes"])

if __name__ == "__main__":
    unittest.main()
