import copy
import hashlib
import unittest

from floor_binding import bind_request_boundaries as bind_impl, verify_bound_receipt as verify_impl
from runtime_linkage import REQUIRED

PREPARED={"schema":"epyc.ch26.c5-mapped-preparation.v1", "files":{n:{"path":"/test/"+n,"dev_major":1,"dev_minor":2,"inode":i+1,"sha256":f"{i+1:064x}"} for i,n in enumerate(sorted(REQUIRED))}}

def bind_request_boundaries(*args): return bind_impl(*args,runtime_prepared=PREPARED)
def verify_bound_receipt(*args): return verify_impl(*args,runtime_prepared=PREPARED)


def fixture():
    orders = [["anchor", "candidate"] if i % 2 == 0 else ["candidate", "anchor"]
              for i in range(24)]
    row = {"schema": "epyc.autokernel.serving_floor.v2", "calibration_pairs": 24,
           "comparison_pairs": 5, "np": 1, "request_digest": "d" * 64,
           "calibration_plan": {"orders": orders}, "content_sha256": "old"}
    prompt = ("pinned-prompt", b"frozen request")
    sha = hashlib.sha256(prompt[1]).hexdigest()
    events = []
    for ordinal in range(1, 49):
        for phase in ("warmup", "measurement"):
            target = {"pid": ordinal, "start_ticks": ordinal + 1000, "boot_id": "boot-id"}
            observer_hash = f"{ordinal * 2 + (phase == 'measurement'):064x}"
            context = {"launch_ordinal": ordinal, "phase": phase, "slot_index": 0,
                       "prompt_id": prompt[0], "request_sha256": sha}
            observer = {"schema": "epyc.ch26.observer_request_receipt.v1",
                        "observer_id": "ch26:" + observer_hash,
                        "evidence_path": f"/tmp/native/{ordinal}-{phase}.json",
                        "evidence_sha256": observer_hash, "request_context": context,
                        "request_window_ns": [1, 2],
                        "markers": [
                            {"kind": "begin", "seq": 1, "pid": 500, "uid": 1000,
                             "start_ticks": 50, "boot_id": "boot-id", "timestamp_ns": 1,
                             "received_ns": 2},
                            {"kind": "end", "seq": 2, "pid": 500, "uid": 1000,
                             "start_ticks": 50, "boot_id": "boot-id", "timestamp_ns": 2,
                             "received_ns": 3}],
                        "target_identity": target,
                        "target_observations": [copy.deepcopy(target) for _ in range(3)],
                        "status": "unproven", "measurement_admission": "none",
                        "placement": "unproven", "contention": "unproven"}
            runtime = {"target":target,"status":"matching-c5-mapped-inodes","coverage":"point-in-time-only","measurement_admission":"none", "files":{n:{k:v for k,v in record.items() if k!='sha256'} for n,record in PREPARED['files'].items()}, "prepared_sha256":{n:record['sha256'] for n,record in PREPARED['files'].items()}}
            snapshot = {"runtime_linkage":runtime,"target": target, "tasks": {str(ordinal): [0, 1]},
                        "global_holders": {"q0": [1], "q1": [1], "q2": [1], "q3": [1]},
                        "preflight": {"verdict": "PASS"}}
            events.append({"launch_ordinal": ordinal, "phase": phase, "slot_index": 0,
                           "prompt_id": prompt[0], "request_sha256": sha,
                           "status": "observed-at-boundaries", "target": target,
                           "before": copy.deepcopy(snapshot), "after": copy.deepcopy(snapshot),
                           "placement_window_ns": [1, 2],
                           "placement_samples": [
                               {"monotonic_ns": 1, "pid": ordinal,
                                "start_ticks": target["start_ticks"],
                                "topology": {"0": 0, "1": 0},
                                "tasks": {str(ordinal): {"cpu": 0, "node": 0}}},
                               {"monotonic_ns": 2, "pid": ordinal,
                                "start_ticks": target["start_ticks"],
                                "topology": {"0": 0, "1": 0},
                                "tasks": {str(ordinal): {"cpu": 1, "node": 0}}}],
                           "placement_observation": "sampled-during-request",
                           "placement_continuous": "unproven",
                           "contention_continuous": "unproven",
                           "no_inference_scope": "sanctioned-claim-witness-only",
                           "native_observer": observer})
    return row, events, [prompt]


class FloorBindingTests(unittest.TestCase):
    def test_binds_all_request_phases_to_plan_arms_and_prompt(self):
        row, events, prompts = fixture()
        result = bind_request_boundaries(row, events, prompts)
        binding = result["request_binding"]
        self.assertEqual(binding["launch_count"], 48)
        self.assertEqual(binding["request_count"], 96)
        self.assertEqual(binding["launches"][0]["arm"], "anchor")
        self.assertEqual(binding["launches"][0]["phases"]["measurement"]["prompt_id"], prompts[0][0])
        self.assertEqual(len(binding["launches"][0]["phases"]["measurement"]["placement_samples"]), 2)
        self.assertEqual(binding["launches"][1]["arm"], "candidate")
        self.assertNotEqual(result["content_sha256"], "old")
        self.assertTrue(verify_bound_receipt(result))

    def test_rejects_missing_or_duplicate_request_phase(self):
        row, events, prompts = fixture()
        with self.assertRaisesRegex(ValueError, "count"):
            bind_request_boundaries(row, events[:-1], prompts)
        row, events, prompts = fixture()
        events[-1] = copy.deepcopy(events[-2])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            bind_request_boundaries(row, events, prompts)

    def test_rejects_wrong_prompt_and_incomplete_boundary(self):
        row, events, prompts = fixture()
        events[0]["prompt_id"] = "other"
        with self.assertRaisesRegex(ValueError, "pinned prompt"):
            bind_request_boundaries(row, events, prompts)
        row, events, prompts = fixture()
        events[0]["status"] = "incomplete"
        with self.assertRaisesRegex(ValueError, "incomplete"):
            bind_request_boundaries(row, events, prompts)

    def test_rejects_placement_sample_outside_window_or_wrong_target(self):
        row, events, prompts = fixture()
        events[0]["placement_samples"][1]["monotonic_ns"] = 3
        with self.assertRaisesRegex(ValueError, "sample time"):
            bind_request_boundaries(row, events, prompts)
        row, events, prompts = fixture()
        events[0]["placement_samples"][0]["start_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "target identity"):
            bind_request_boundaries(row, events, prompts)

    def test_rejects_boundary_owner_change_and_unwarranted_contention_claim(self):
        row, events, prompts = fixture()
        events[0]["after"]["global_holders"]["q0"] = [2]
        with self.assertRaisesRegex(ValueError, "claim-owner state changed"):
            bind_request_boundaries(row, events, prompts)
        row, events, prompts = fixture()
        events[0]["contention_continuous"] = "proven"
        with self.assertRaisesRegex(ValueError, "claim scope"):
            bind_request_boundaries(row, events, prompts)

    def test_runtime_mismatch_and_resealed_tampering_refused(self):
        row, events, prompts = fixture()
        events[0]['before']['runtime_linkage']['target']=dict(events[0]['before']['runtime_linkage']['target'],start_ticks=9999)
        with self.assertRaisesRegex(ValueError,'target mismatch'):
            bind_request_boundaries(row, events, prompts)
        row, events, prompts = fixture()
        del events[0]['before']['runtime_linkage']['files']['llama-server']
        with self.assertRaisesRegex(ValueError,'incomplete mapped'):
            bind_request_boundaries(row, events, prompts)
        row, events, prompts = fixture()
        result=bind_request_boundaries(row,events,prompts)
        phase=result['request_binding']['launches'][0]['phases']['warmup']
        for edge in ('before','after'): phase[edge]['runtime_linkage']['files']['llama-server']['inode']+=1
        from floor_binding import _digest
        binding=result['request_binding'];binding.pop('content_sha256');binding['content_sha256']=_digest(binding)
        result.pop('content_sha256');result['content_sha256']=_digest(result)
        self.assertFalse(verify_bound_receipt(result))
        row, events, prompts = fixture()
        for edge in ('before','after'):events[0][edge]['runtime_linkage']['prepared_sha256']['llama-server']='0'*64
        with self.assertRaisesRegex(ValueError,'digests'):
            bind_request_boundaries(row,events,prompts)

    def test_receipt_verifier_rechecks_bound_observations(self):
        row, events, prompts = fixture()
        result = bind_request_boundaries(row, events, prompts)
        result["request_binding"]["launches"][0]["phases"]["warmup"]["placement_samples"] = []
        self.assertFalse(verify_bound_receipt(result))


if __name__ == "__main__":
    unittest.main()
