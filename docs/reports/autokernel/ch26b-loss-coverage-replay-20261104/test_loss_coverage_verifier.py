import base64
import copy
import struct
import unittest

from loss_coverage_verifier import EVENTS, verify


def sample(eid, cpu, tracepoint, stamp=250):
    body = struct.pack("=QQIIQIIQI", eid, 0, 1, 1, stamp, cpu, 0, 1, 4)
    body += struct.pack("=H", tracepoint) + b"xx"
    record = struct.pack("=IHH", 9, 0, 8 + len(body)) + body
    return record + bytes(256 - len(record)), len(record)


def make_doc(cpus={0}):
    doc = {"measurement_admission": "none", "errors": [],
           "markers": [{"timestamp_ns": 200}, {"timestamp_ns": 300}],
           "source_provenance": [], "snapshots": [], "rings": []}
    eid = 100
    for cpu in sorted(cpus):
        for index, name in enumerate(sorted(EVENTS), 1):
            tracepoint = 1000 + eid
            raw, head = sample(eid, cpu, tracepoint)
            doc["source_provenance"].append({"cpu": cpu, "name": name,
                                               "event_id": eid, "tracepoint_id": tracepoint})
            ring = {"snapshot": {"encoding": "base64", "data": base64.b64encode(raw).decode()},
                    "head": head, "tail": 0, "errors": []}
            doc["snapshots"].append({"cpu": cpu, "name": name, "event_id": eid,
                                     "ring": copy.deepcopy(ring)})
            doc["rings"].append({"cpu": cpu, "name": name, "event_id": eid,
                                 "errors": [], "lost_samples": 0, "enable_after_ns": 100,
                                 "disable_before_ns": 400, "enabled_ns": 300,
                                 "running_ns": 300, "count": 1, "ring": ring})
            eid += 1
    return doc


class LossCoverageReplayTests(unittest.TestCase):
    def test_valid_complete_structural_receipt_stays_unproven(self):
        result = verify(make_doc(), expected_cpus={0})
        self.assertEqual(result["status"], "structural_pass")
        self.assertEqual(result["source_count"], 5)
        self.assertEqual(result["losslessness"], "unproven")
        self.assertEqual(result["coverage"], "unproven")
        self.assertEqual(result["measurement_admission"], "none")

    def test_rejects_nonzero_kernel_lost_counter(self):
        doc = make_doc()
        doc["rings"][0]["lost_samples"] = 1
        with self.assertRaisesRegex(ValueError, "loss/error"):
            verify(doc, expected_cpus={0})

    def test_rejects_missing_cpu_event_source(self):
        doc = make_doc()
        doc["source_provenance"].pop()
        with self.assertRaisesRegex(ValueError, "source inventory"):
            verify(doc, expected_cpus={0})

    def test_rejects_counter_sample_disagreement(self):
        doc = make_doc()
        doc["rings"][0]["count"] = 2
        with self.assertRaisesRegex(ValueError, "count disagreement"):
            verify(doc, expected_cpus={0})

    def test_rejects_ring_gap(self):
        doc = make_doc()
        doc["snapshots"][0]["ring"]["tail"] = 8
        with self.assertRaisesRegex(ValueError, "sequence gap"):
            verify(doc, expected_cpus={0})

    def test_rejects_request_outside_perf_interval(self):
        doc = make_doc()
        doc["rings"][0]["enable_after_ns"] = 201
        with self.assertRaisesRegex(ValueError, "outside conservative"):
            verify(doc, expected_cpus={0})


if __name__ == "__main__":
    unittest.main()
