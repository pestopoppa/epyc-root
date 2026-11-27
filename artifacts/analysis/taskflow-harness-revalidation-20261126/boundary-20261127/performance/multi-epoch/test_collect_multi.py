"""Model-free controls for multi-epoch observation, custody and unknown values."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import collect_multi as c


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


class CollectMultiTests(unittest.TestCase):
    def setUp(self):
        fixed = tempfile.TemporaryDirectory()
        self.addCleanup(fixed.cleanup)
        self.tmp = Path(fixed.name)
        self.old = self.tmp / "old-serving"
        self.new = self.tmp / "new-serving"
        self.old_unit = self.old / "units/task-a"
        self.new_units = self.new / "jobs/batch/units"
        self.new_unit = self.new_units / "task-a-resume"
        self.plans = [put(self.old / "plan.json", [{"id": "task-a", "backend": "cpu"}, {"id": "queued"}]),
                      put(self.new / "jobs/batch/approval.json", {"legacy_rows": ["task-a-resume"]})]
        self.config = {"epochs": [
            {"id": "old", "layout": "quality", "serving_root": str(self.old), "units_root": str(self.old / "units"),
             "plan": str(self.plans[0]), "backends": ["cpu"],
             "overlays": [{"backend": "cpu", "ids": ["task-a"], "tag": "cpu_placement_incident"}]},
            {"id": "new", "layout": "cpu_repaired", "serving_root": str(self.new), "units_root": str(self.new_units),
             "plan": str(self.plans[1]), "backends": ["cpu"], "default_backend": "cpu"},
        ]}
        result = put(self.old_unit / "RESULT.json", {"status": "oracle_pass", "backend": "cpu", "started_at": 9,
                                                    "terminal_at": 14, "patch_sha256": "candidate",
                                                    "oracle": {"rc": 0}})
        session = put(self.old_unit / "OPEN-CODE-SESSION.json", {"messages": [{"content": "SECRET BODY"}]})
        put(self.new_unit / "RESULT.json", {"status": "running", "started_at": 12, "resume": {
            "prior": str(self.old_unit), "prior_result_sha256": c.digest(result.read_bytes()),
            "prior_session_sha256": c.digest(session.read_bytes()), "previous_generated_observed": 12}})
        put(self.new_unit / "worker/receipt.json", {"status": "running", "started_at": 13})
        self.original = {"seq": 1, "t0": 10, "wall_s": 5, "backend": "cpu", "slot": 0, "body_ref": "a.json.gz",
                         "http_status": 200, "draft_n": 8, "draft_accepted": 4,
                         "prompt_n": 20, "cache_n": 8, "predicted_n": 14,
                         "ttft_s": 0.4, "delivered_ttft_s": 1.4, "client_ttft_s": 1.4, "queue_wait_s": 1.0,
                         "prompt_ms": 1000, "predicted_ms": 3000, "usage": {"prompt_tokens_details": {"cached_tokens": 8}}}
        self.resumed = {**self.original, "t0": 12, "predicted_n": 9, "body_ref": "b.json.gz", "draft_n": None}
        self.wire(self.old_unit / "wire", [self.original], {"a.json.gz": True})
        self.wire(self.new_unit / "worker/wire", [self.original, self.resumed],
                  {"a.json.gz": True, "b.json.gz": False, "pending.json.gz": True}, partial="{partial")
        for root, ticks in ((self.old, (2, 11, 12, 19)), (self.new, (5, 13, 16, 25))):
            (root / "resource-samples.jsonl").write_text("".join(
                json.dumps({"epoch_s": t, "cpu": {"rss_pages": t}}) + "\n" for t in ticks))
        put(self.old / "out-cpu/server.json", {"argv": ["native", "--cache-ram", "0"], "pid": 42})
        path = self.new / "out-cpu/server.log"
        path.parent.mkdir()
        path.write_text("1.02 I slot print_timing: id  2 | task 999 | n_decoded = 12, tg = 8.00 t/s\n")

    def wire(self, path, rows, bodies, partial=""):
        path.mkdir(parents=True)
        for name, stream in bodies.items():
            body = {"stream": stream, "messages": [{"role": "user", "content": "SECRET BODY"}]}
            (path / name).write_bytes(gzip.compress(json.dumps(body).encode(), mtime=0))
        (path / "requests.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows) + partial)

    def rows(self, report):
        return {row["id"]: row for row in report["attempts"]}

    def test_nested_wire_duplicate_and_lineage_costs(self):
        report = c.collect(self.config)
        rows = self.rows(report)
        self.assertEqual(report["rollup"]["forwarded_receipts"], 2)
        self.assertEqual(report["rollup"]["tokens"]["predicted_n"]["known_sum"], 23)
        newer = rows["task-a-resume"]
        self.assertEqual(len(newer["duplicate_receipts"]), 1)
        self.assertEqual(newer["duplicate_receipts"][0]["first_seen"]["unit_path"], str(self.old_unit))
        self.assertTrue(newer["continuation_costs"]["complete_bound_chain"])
        self.assertEqual(newer["continuation_costs"]["current_phase"]["generated"]["known_sum"], 9)
        self.assertEqual(newer["continuation_costs"]["previous_phases"][0]["generated"]["known_sum"], 14)
        self.assertEqual(newer["ancestry"]["prior_declared_tokens_at_resume"], 12)
        self.assertEqual(newer["continuation_costs"]["captured_cumulative"]["request_windows"]["request_wall_union_s"], 7)

    def test_partial_unknown_confounds_and_epoch_resource_windows(self):
        report = c.collect(self.config)
        rows = self.rows(report)
        self.assertEqual(rows["queued"]["status"], "not_started")
        self.assertEqual(len(report["read_warnings"]), 1)
        self.assertEqual(report["unreceipted_archives"], 1)
        self.assertIsNone(rows["task-a-resume"]["unreceipted_archives"][0]["generated_tokens"])
        self.assertEqual(rows["task-a"]["qualification_tags"], ["cpu_placement_incident"])
        self.assertEqual(rows["task-a"]["resources"]["sample_indices"], [1, 2])
        self.assertEqual(rows["task-a-resume"]["resources"]["sample_indices"], [1, 2])
        self.assertEqual(rows["task-a-resume"]["resources"]["process_rss_pages"]["min"], 13)
        self.assertEqual(len(report["epochs"][1]["resource_samples"]), 4)
        self.assertTrue(report["epochs"][0]["server_identity"]["cpu"]["shared_ram_cache_disabled"])
        self.assertEqual(rows["task-a"]["summary"]["tokens"]["cache_n"]["known_sum"], 8)
        self.assertNotIn("SECRET BODY", json.dumps(report))
        self.assertEqual(json.dumps(report, sort_keys=True), json.dumps(c.collect(self.config), sort_keys=True))

    def test_ttft_and_mtp_avoid_substitution_of_unknown_fields(self):
        report = c.collect(self.config)
        rows = self.rows(report)
        streamed, = rows["task-a"]["requests"]
        nonstream, = rows["task-a-resume"]["requests"]
        self.assertEqual((streamed["ttft_s"], streamed["client_ttft_s"], streamed["queue_wait_s"]), (0.4, 1.4, 1.0))
        self.assertIsNone(nonstream["ttft_s"])
        self.assertIsNone(nonstream["delivered_ttft_s"])
        self.assertIsNone(nonstream["client_ttft_s"])
        self.assertIsNone(report["epochs"][1]["native_logs"]["cpu"]["ttft_s"])
        self.assertEqual(report["epochs"][1]["native_logs"]["cpu"]["tasks"][0]["last_decode_progress"]["generated_so_far"], 12)
        self.assertEqual(report["rollup"]["mtp_paired"]["acceptance_ratio"], 0.5)
        self.assertEqual(report["rollup"]["mtp_paired"]["unknown_receipts"], 1)

    def test_review_requires_independent_patch_bound_record(self):
        report = c.collect(self.config)
        self.assertEqual(self.rows(report)["task-a"]["acceptance"]["state"], "pending_independent_review")
        self.assertEqual(report["accepted_count"], 0)
        review = put(self.tmp / "review.json", {"decision": "accepted", "candidate_patch_sha256": "other"})
        self.config["reviews"] = {str(self.old_unit): {"path": str(review), "sha256": c.digest(review.read_bytes())}}
        self.assertEqual(self.rows(c.collect(self.config))["task-a"]["acceptance"]["state"], "unverified_review_record")
        put(review, {"decision": "accepted", "candidate_patch_sha256": "candidate"})
        self.config["reviews"][str(self.old_unit)]["sha256"] = c.digest(review.read_bytes())
        self.assertEqual(c.collect(self.config)["accepted_count"], 1)

    def test_unfinalized_oracle_pass_stays_partial(self):
        path = self.old_unit / "RESULT.json"
        record = json.loads(path.read_bytes())
        del record["terminal_at"]
        put(path, record)
        old = self.rows(c.collect(self.config))["task-a"]
        self.assertTrue(old["partial"])
        self.assertEqual(old["status"], "oracle_pass")
        self.assertEqual(old["acceptance"]["state"], "pending_independent_review")

    def test_rejected_parent_hash_never_reuses_old_cost(self):
        path = self.old_unit / "RESULT.json"
        result = json.loads(path.read_bytes())
        put(path, {**result, "terminal_at": 15})
        newer = self.rows(c.collect(self.config))["task-a-resume"]
        self.assertFalse(newer["continuation_costs"]["complete_bound_chain"])
        self.assertEqual(newer["continuation_costs"]["previous_phases"], [])
        self.assertEqual(newer["continuation_costs"]["captured_cumulative"]["summary"]["tokens"]["predicted_n"]["known_sum"], 9)

    def test_missing_gpu_epoch_uses_reviewed_plan_and_no_samples(self):
        future = self.tmp / "future"
        approval = put(self.tmp / "approval.json", {"initial_rows": ["gpu-first"]})
        self.config["epochs"].append({"id": "future", "layout": "legacy_gpu", "serving_root": str(future),
                                      "units_root": str(future / "units"), "plan": str(approval),
                                      "backends": ["gpu"], "default_backend": "gpu",
                                      "bindings": [{"path": str(approval), "sha256": c.digest(approval.read_bytes())}]})
        report = c.collect(self.config)
        self.assertEqual(report["epochs"][-1]["state"], "not_started")
        self.assertEqual(self.rows(report)["gpu-first"]["status"], "not_started")
        self.assertEqual(report["epochs"][-1]["bindings"][0]["state"], "matched")


if __name__ == "__main__":
    unittest.main()
