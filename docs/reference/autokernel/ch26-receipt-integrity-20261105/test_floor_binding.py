import copy
import hashlib
import json
import unittest
from unittest.mock import patch
import tempfile
import os
from runtime_linkage import REQUIRED
from pathlib import Path

from census_receipt import write_receipt

from floor_binding import bind_request_boundaries, verify_bound_receipt


def fixture(parent):
    directory = Path(tempfile.mkdtemp(dir=parent))
    orders = [["anchor", "candidate"] if i % 2 == 0 else ["candidate", "anchor"]
              for i in range(24)]
    row = {"schema": "epyc.autokernel.serving_floor.v2", "calibration_pairs": 24,
           "comparison_pairs": 5, "np": 1, "request_digest": "d" * 64,
           "calibration_plan": {"orders": orders}, "content_sha256": "old"}
    prompt = ("pinned-prompt", b"frozen request")
    sha = hashlib.sha256(prompt[1]).hexdigest()
    row["request_digest"] = hashlib.sha256(json.dumps([[prompt[0],sha]],ensure_ascii=False,separators=(",", ":")).encode()).hexdigest()
    files = {}
    for name in sorted(REQUIRED):
        path = directory / name
        path.write_bytes(b"fixture binary")
        st = path.stat()
        files[name] = {"path": str(path), "dev_major": os.major(st.st_dev),
                       "dev_minor": os.minor(st.st_dev), "inode": st.st_ino,
                       "size": st.st_size, "mtime_ns": st.st_mtime_ns,
                       "ctime_ns": st.st_ctime_ns, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    prepared = {"schema": "epyc.ch26.c5-mapped-preparation.v1", "files": files}
    events = []
    for ordinal in range(1, 49):
        for phase in ("warmup", "measurement"):
            start = (ordinal - 1) * 10 + (4 if phase == "measurement" else 0) + 1
            target = {"pid": ordinal, "start_ticks": ordinal + 1000, "boot_id": "boot-id"}
            observer_hash = f"{ordinal * 2 + (phase == 'measurement'):064x}"
            context = {"launch_ordinal": ordinal, "phase": phase, "slot_index": 0,
                       "prompt_id": prompt[0], "request_sha256": sha}
            observer = {"schema": "epyc.ch26.observer_request_receipt.v1",
                        "observer_id": "ch26:" + observer_hash,
                        "evidence_path": f"/tmp/native/{ordinal}-{phase}.json",
                        "evidence_sha256": observer_hash, "request_context": context,
                        "request_window_ns": [start, start + 1],
                        "markers": [
                            {"kind": "begin", "seq": 1, "pid": 500, "uid": 1000,
                             "start_ticks": 50, "boot_id": "boot-id", "timestamp_ns": start,
                             "received_ns": start + 1},
                            {"kind": "end", "seq": 2, "pid": 500, "uid": 1000,
                             "start_ticks": 50, "boot_id": "boot-id", "timestamp_ns": start + 1,
                             "received_ns": start + 2}],
                        "target_identity": target,
                        "target_observations": [copy.deepcopy(target) for _ in range(3)],
                        "status": "unproven", "measurement_admission": "none",
                        "placement": "unproven", "contention": "unproven"}
            mapped = {"status": "matching-c5-mapped-inodes", "target": target,
                      "coverage": "point-in-time-only", "measurement_admission": "none",
                      "files": {n: {k: v[k] for k in ("path", "dev_major", "dev_minor", "inode")}
                                for n, v in files.items()},
                      "prepared_sha256": {n: v["sha256"] for n, v in files.items()}}
            mapped["executable"] = dict(mapped["files"]["llama-server"])
            snapshot = {"runtime_linkage": mapped, "target": target, "tasks": {str(ordinal): [0, 1]},
                        "global_holders": {"q0": [1], "q1": [1], "q2": [1], "q3": [1]},
                        "preflight": {"verdict": "PASS"}}
            task = {"pid": ordinal, "tid": ordinal, "start_ticks": ordinal + 1000,
                    "identity_stable": True, "cpu_ticks": 1, "allowed_cpus": [0]}
            census = {"schema": "akagg.cpu-observation-candidate.v1", "collector_visibility": "unverified",
                      "request_start": 0.0, "request_end": 1.0,
                      "policy_observation": {"measurement_admission": "none"},
                      "request_phase_collector": {"schema": "akagg.request-phase-collector.v1",
                          "status": "unproven", "placement": "unproven", "contention": "unproven", "errors": []},
                      "samples": [{"scan_start": 1e-9, "monotonic_s": 1e-9, "scan_end": 2e-9,
                          "tasks": [task], "target": dict(target, identity_stable=True), "boot_id": "boot-id",
                          "errors": [], "census_complete": True, "truncated": False}]}
            receipt = write_receipt(directory / f"{ordinal}-{phase}.json", row=census, target=target,
                                    placement_window_ns=[start, start + 1], request_context=context)
            events.append({"launch_ordinal": ordinal, "phase": phase, "slot_index": 0,
                           "prompt_id": prompt[0], "request_sha256": sha,
                           "status": "observed-at-boundaries", "target": target,
                           "before": copy.deepcopy(snapshot), "after": copy.deepcopy(snapshot),
                           "placement_window_ns": [start, start + 1],
                           "placement_samples": [
                               {"monotonic_ns": start, "pid": ordinal,
                                "start_ticks": target["start_ticks"],
                                "topology": {"0": 0, "1": 0},
                                "tasks": {str(ordinal): {"cpu": 0, "node": 0}}},
                               {"monotonic_ns": start + 1, "pid": ordinal,
                                "start_ticks": target["start_ticks"],
                                "topology": {"0": 0, "1": 0},
                                "tasks": {str(ordinal): {"cpu": 1, "node": 0}}}],
                           "placement_observation": "sampled-during-request",
                           "placement_continuous": "unproven",
                           "contention_continuous": "unproven",
                           "no_inference_scope": "sanctioned-claim-witness-only",
                           "native_observer": observer, "host_census": receipt,
                           "writer_check": {"schema":"epyc.ch26.journal-writer-observation.v1",
                               "identity":{"pid":500,"uid":1000,"start_ticks":50,"boot_id":"boot-id"},
                               "scope":"self-reported-not-authenticated"},
                           "measurement_admission": "none"})
    return row, events, [prompt], prepared


def expected_request(prompts, row):
    return {"prompt_id": prompts[0][0], "request_sha256": hashlib.sha256(prompts[0][1]).hexdigest(), "request_digest": row["request_digest"]}


class FloorBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_binds_all_request_phases_to_plan_arms_and_prompt(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        result = bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        binding = result["request_binding"]
        self.assertEqual(binding["launch_count"], 48)
        self.assertEqual(binding["request_count"], 96)
        self.assertEqual(binding["launches"][0]["arm"], "anchor")
        self.assertEqual(binding["launches"][0]["phases"]["measurement"]["prompt_id"], prompts[0][0])
        self.assertEqual(len(binding["launches"][0]["phases"]["measurement"]["placement_samples"]), 2)
        self.assertEqual(binding["launches"][1]["arm"], "candidate")
        self.assertNotEqual(result["content_sha256"], "old")
        self.assertTrue(verify_bound_receipt(result, runtime_prepared=prepared, expected_request=expected_request(prompts, row), expected_plan=row["calibration_plan"]))

    def test_rejects_missing_or_duplicate_request_phase(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        with self.assertRaisesRegex(ValueError, "count"):
            bind_request_boundaries(row, events[:-1], prompts, runtime_prepared=prepared)
        row, events, prompts, prepared = fixture(self.tmp.name)
        events[-1] = copy.deepcopy(events[-2])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)

    def test_rejects_wrong_prompt_and_incomplete_boundary(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        events[0]["prompt_id"] = "other"
        with self.assertRaisesRegex(ValueError, "pinned prompt"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        row, events, prompts, prepared = fixture(self.tmp.name)
        events[0]["status"] = "incomplete"
        with self.assertRaisesRegex(ValueError, "incomplete"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)

    def test_rejects_placement_sample_outside_window_or_wrong_target(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        events[0]["placement_samples"][1]["monotonic_ns"] = 3
        with self.assertRaisesRegex(ValueError, "sample time"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        row, events, prompts, prepared = fixture(self.tmp.name)
        events[0]["placement_samples"][0]["start_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "target identity"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)

    def test_rejects_boundary_owner_change_and_unwarranted_contention_claim(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        events[0]["after"]["global_holders"]["q0"] = [2]
        with self.assertRaisesRegex(ValueError, "claim-owner state changed"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        row, events, prompts, prepared = fixture(self.tmp.name)
        events[0]["contention_continuous"] = "proven"
        with self.assertRaisesRegex(ValueError, "claim scope"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)

    def test_in_place_binary_mutation_refused_at_binding_and_replay(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        result = bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        binary = Path(prepared["files"]["llama-server"]["path"])
        before = binary.stat()
        binary.write_bytes(b"fixture binarX")
        os.utime(binary, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(binary.stat().st_ino, before.st_ino)
        with self.assertRaisesRegex(ValueError, "changed after hash"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        self.assertFalse(verify_bound_receipt(result, runtime_prepared=prepared, expected_request=expected_request(prompts, row), expected_plan=row["calibration_plan"]))

    def test_incomplete_map_old_preparation_and_wrong_target_refused(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        del events[0]["before"]["runtime_linkage"]["files"]["llama-server"]
        with self.assertRaisesRegex(ValueError, "incomplete mapped binary set"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        row, events, prompts, prepared = fixture(self.tmp.name)
        del prepared["files"]["llama-server"]["ctime_ns"]
        with self.assertRaisesRegex(ValueError, "changed after hash"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        row, events, prompts, prepared = fixture(self.tmp.name)
        events[0]["after"]["runtime_linkage"]["target"] = dict(events[0]["target"], start_ticks=9999)
        with self.assertRaisesRegex(ValueError, "target mismatch"):
            bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)

    def test_receipt_verifier_rechecks_bound_observations(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        result = bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        result["request_binding"]["launches"][0]["phases"]["warmup"]["placement_samples"] = []
        self.assertFalse(verify_bound_receipt(result, runtime_prepared=prepared, expected_request=expected_request(prompts, row), expected_plan=row["calibration_plan"]))

    def test_rehashed_tampering_cannot_change_process_request_or_plan(self):
        row, events, prompts, prepared = fixture(self.tmp.name)
        bound = bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
        expected = expected_request(prompts, row)
        def rehash(value):
            from floor_binding import _digest
            binding = value["request_binding"]
            binding["content_sha256"] = _digest({k:v for k,v in binding.items() if k != "content_sha256"})
            value["content_sha256"] = _digest({k:v for k,v in value.items() if k != "content_sha256"})
        for mode in ("swapped_birth", "reused_birth", "wrong_request", "wrong_arm", "wrong_pair", "changed_plan"):
            b = copy.deepcopy(bound); launches = b["request_binding"]["launches"]
            if mode == "swapped_birth": launches[0]["phases"]["measurement"]["target"] = launches[1]["phases"]["warmup"]["target"]
            if mode == "reused_birth":
                for phase in ("warmup", "measurement"):
                    launches[1]["phases"][phase]["target"] = copy.deepcopy(launches[0]["phases"]["warmup"]["target"])
            if mode == "wrong_request": launches[0]["phases"]["warmup"]["request_sha256"] = "b"*64
            if mode == "wrong_arm": launches[0]["arm"] = "candidate"
            if mode == "wrong_pair": launches[0]["pair_index"] = 1
            if mode == "changed_plan": b["calibration_plan"]["orders"][0].reverse()
            rehash(b)
            with self.subTest(mode=mode):
                # Isolate relationship checks from unrelated nested native receipts.
                with patch('floor_binding._validate_observation', side_effect=(lambda phase, pid, sha, *a, **kw: None if phase['prompt_id']==pid and phase['request_sha256']==sha else (_ for _ in ()).throw(ValueError('request')))):
                    self.assertFalse(verify_bound_receipt(b, runtime_prepared=prepared, expected_request=expected, expected_plan=row['calibration_plan']))

    def test_binding_rejects_process_reuse_and_phase_swap(self):
        for mode in ('reuse', 'swap'):
            row, events, prompts, prepared = fixture(self.tmp.name)
            if mode == 'reuse':
                events[2]['target'] = copy.deepcopy(events[0]['target']); events[3]['target'] = copy.deepcopy(events[0]['target'])
            else: events[1]['target'] = copy.deepcopy(events[2]['target'])
            with self.subTest(mode=mode), patch('floor_binding._validate_observation'), self.assertRaises(ValueError):
                bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)

    def test_reversed_and_overlapping_windows_refused_at_bind_and_rehashed_replay(self):
        from floor_binding import _digest
        for mode in ('phase_reversed', 'phase_overlap', 'launch_reversed', 'launch_overlap'):
            row, events, prompts, prepared = fixture(self.tmp.name)
            bound = bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
            expected = expected_request(prompts, row)
            launches = bound['request_binding']['launches']
            if mode == 'phase_reversed':
                events[0]['placement_window_ns'], events[1]['placement_window_ns'] = events[1]['placement_window_ns'], events[0]['placement_window_ns']
                launches[0]['phases']['warmup']['placement_window_ns'], launches[0]['phases']['measurement']['placement_window_ns'] = launches[0]['phases']['measurement']['placement_window_ns'], launches[0]['phases']['warmup']['placement_window_ns']
            elif mode == 'phase_overlap':
                events[1]['placement_window_ns'] = [1, 6]
                launches[0]['phases']['measurement']['placement_window_ns'] = [1, 6]
            elif mode == 'launch_reversed':
                events[2]['placement_window_ns'] = [1, 2]
                launches[1]['phases']['warmup']['placement_window_ns'] = [1, 2]
            else:
                events[2]['placement_window_ns'] = [5, 12]
                launches[1]['phases']['warmup']['placement_window_ns'] = [5, 12]
            binding = bound['request_binding']
            binding['content_sha256'] = _digest({k:v for k,v in binding.items() if k != 'content_sha256'})
            bound['content_sha256'] = _digest({k:v for k,v in bound.items() if k != 'content_sha256'})
            with self.subTest(mode=mode), patch('floor_binding._validate_observation'):
                with self.assertRaisesRegex(ValueError, 'overlap or are reversed'):
                    bind_request_boundaries(row, events, prompts, runtime_prepared=prepared)
                self.assertFalse(verify_bound_receipt(bound, runtime_prepared=prepared,
                    expected_request=expected, expected_plan=row['calibration_plan']))


if __name__ == "__main__":
    unittest.main()
