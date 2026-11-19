import copy
import unittest

from request_observer_join import join_event


def fixture():
    target = {"pid": 900, "start_ticks": 12, "boot_id": "boot-1"}
    context = {"launch_ordinal": 3, "phase": "warmup", "slot_index": 0,
               "prompt_id": "pinned", "request_sha256": "a" * 64}
    digest = "b" * 64
    receipt = {"schema": "epyc.ch26.observer_request_receipt.v1",
               "observer_id": "ch26:" + digest, "evidence_path": "/tmp/observer.json",
               "evidence_sha256": digest, "request_context": context,
               "request_window_ns": [200, 800],
               "markers": [
                   {"kind": "begin", "seq": 1, "pid": 700, "uid": 1000,
                    "start_ticks": 9, "boot_id": "boot-1", "timestamp_ns": 200,
                    "received_ns": 201},
                   {"kind": "end", "seq": 2, "pid": 700, "uid": 1000,
                    "start_ticks": 9, "boot_id": "boot-1", "timestamp_ns": 800,
                    "received_ns": 801}],
               "target_identity": target,
               "target_observations": [copy.deepcopy(target) for _ in range(3)],
               "status": "unproven", "measurement_admission": "none",
               "placement": "unproven", "contention": "unproven"}
    event = {**context, "status": "observed-at-boundaries", "target": target,
             "placement_window_ns": [100, 900], "placement_continuous": "unproven",
             "contention_continuous": "unproven", "measurement_admission": "none"}
    return event, receipt


class RequestObserverJoinTests(unittest.TestCase):
    def test_exact_request_receipt_joins_and_preserves_unknowns(self):
        event, receipt = fixture()
        joined = join_event(event, receipt)
        self.assertEqual(joined["native_observer"]["observer_id"], receipt["observer_id"])
        self.assertEqual(joined["native_observer"]["request_window_ns"], [200, 800])
        self.assertEqual(joined["placement_continuous"], "unproven")
        self.assertEqual(joined["contention_continuous"], "unproven")
        self.assertEqual(joined["measurement_admission"], "none")
        self.assertNotIn("native_observer", event)

    def test_missing_or_wrong_phase_receipt_refused(self):
        event, receipt = fixture()
        with self.assertRaisesRegex(ValueError, "missing"):
            join_event(event, None)
        receipt["request_context"]["phase"] = "measurement"
        with self.assertRaisesRegex(ValueError, "context mismatch"):
            join_event(event, receipt)

    def test_mismatched_timestamp_target_id_and_overclaim_refused(self):
        for field, value, error in (
                ("request_window_ns", [201, 800], "timestamps differ"),
                ("target_identity", {"pid": 901, "start_ticks": 12, "boot_id": "boot-1"}, "target identity"),
                ("observer_id", "ch26:" + "c" * 64, "not bound"),
                ("contention", "proven", "overstates")):
            with self.subTest(field=field):
                event, receipt = fixture()
                receipt[field] = value
                with self.assertRaisesRegex(ValueError, error):
                    join_event(event, receipt)

    def test_observer_interval_must_fit_inside_serving_boundary(self):
        event, receipt = fixture()
        event["placement_window_ns"] = [300, 900]
        with self.assertRaisesRegex(ValueError, "outside serving boundary"):
            join_event(event, receipt)


if __name__ == "__main__":
    unittest.main()
