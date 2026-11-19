"""AKX-P1d classifier controls over synthetic, normalized proof records.

These fixtures test the prototype screen's decision logic, not native dispatch,
actual workload tensor inventories, footprint extraction, or verified custody.
The caller supplies execution witnesses; the screen does not derive them from a
model quantization label. W4's assistant and mixed-quant tensors make that
separation essential. P1d's build/correctness-surface acceptance remains open.
"""
import copy
import unittest

from screen import classify


A = "a" * 64
B = "b" * 64
WORKLOADS = ("W1", "W2", "W3", "W4", "W5", "W6")


def proof():
    """A synthetic two-shape envelope, with independently supplied hunk hits."""
    shape = {
        "anchor_lines": 32, "candidate_lines": 32,
        "hunks": {"dispatch": {"executed": False}}, "knobs": {},
        "anchor_hip_matmul_routes": {}, "candidate_hip_matmul_routes": {},
        "anchor_op_backend": {"MUL_MAT:CPU": 2},
        "candidate_op_backend": {"MUL_MAT:CPU": 2},
    }
    return {
        "author_target": False, "variant": "cpu",
        "census": {"verified": True, "fresh": True, "observed": True,
                   "freshness_key": A, "envelope_hash": B,
                   "shapes": ["prefill", "decode"], "nodes_total": 1001,
                   "expected_ops_present": True, "device_seen": True},
        "footprint": {"verified": True, "sha256": A, "nonempty_diff": True,
                      "hunks": {"dispatch": "body"}, "knobs": {},
                      "opaque_reasons": [], "change_class": "dispatch",
                      "variants_affected": []},
        "t1": {"verified": True, "anchor_profile_sha256": A,
               "candidate_profile_sha256": B, "envelope_hash": B,
               "shapes": {name: copy.deepcopy(shape) for name in ("prefill", "decode")}},
    }


class P1dStaticControls(unittest.TestCase):
    def test_comment_only_t0_control_for_every_workload(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                record = proof()
                record["footprint"]["hunks"] = {"comment": "comment"}
                record.pop("t1")  # T0 must need no execution profile.
                record["t0"] = {
                    "verified": True, "anchor_objects": {"loaded-backend": A},
                    "candidate_objects": {"loaded-backend": A},
                    "anchor_recipe": A, "candidate_recipe": A,
                    "anchor_env": B, "candidate_env": B,
                }
                result = classify(record)
                self.assertEqual((result["classification"], result["tier"]), ("INERT", "T0"))
                self.assertEqual(result["witnesses"]["anchor_objects"], {"loaded-backend": A})
                # Comment syntax alone is not proof of byte identity.
                record["t0"]["candidate_objects"]["loaded-backend"] = B
                self.assertEqual(classify(record)["classification"], "UNKNOWN")

    def test_q8_dispatch_execution_control_matrix(self):
        # These are declared synthetic coverage outcomes, not measured type sets.
        for workload, hit, expected in (
            ("W1", True, "TOUCHED"), ("W2", False, "INERT"),
            ("W3", True, "TOUCHED"), ("W4", False, "INERT"),
            ("W6", False, "INERT"),
            ("W5 census with Q8 dispatch hit", True, "TOUCHED"),
            ("W5 census without Q8 dispatch hit", False, "INERT"),
        ):
            with self.subTest(workload=workload):
                record = proof()
                record["t1"]["shapes"]["decode"]["hunks"]["dispatch"]["executed"] = hit
                result = classify(record)
                self.assertEqual((result["classification"], result["tier"]), (expected, "T1"))
                self.assertEqual(result["touched_detail"].get("executed_hunks", []),
                                 ["dispatch"] if hit else [])
                self.assertEqual(result["witnesses"]["shape_envelope_hash"], B)

    def test_unchanged_unset_knob_control_and_positive_contrasts(self):
        for workload in WORKLOADS:
            with self.subTest(workload=workload):
                record = proof()
                record["footprint"]["knobs"] = {"GGML_CONTROL": {"before": "0", "after": "0"}}
                for shape in record["t1"]["shapes"].values():
                    # Unset environment resolves to the same default in both arms.
                    shape["knobs"] = {"GGML_CONTROL": {"executed": True,
                                          "anchor_value": "0", "candidate_value": "0"}}
                self.assertEqual(classify(record)["classification"], "INERT")
                changed_value = copy.deepcopy(record)
                changed_value["t1"]["shapes"]["decode"]["knobs"]["GGML_CONTROL"]["candidate_value"] = "1"
                changed_default = copy.deepcopy(record)
                changed_default["footprint"]["knobs"]["GGML_CONTROL"]["after"] = "1"
                for changed in (changed_value, changed_default):
                    result = classify(changed)
                    self.assertEqual(result["classification"], "TOUCHED")
                    self.assertEqual(result["touched_detail"]["knob_reads"], ["GGML_CONTROL"])

    def test_negative_dispatch_control_requires_complete_execution_envelope(self):
        for mutation in ("missing_shape", "missing_hunk", "unbound_profile"):
            with self.subTest(mutation=mutation):
                record = proof()
                if mutation == "missing_shape":
                    del record["t1"]["shapes"]["prefill"]
                elif mutation == "missing_hunk":
                    record["t1"]["shapes"]["prefill"]["hunks"] = {}
                else:
                    record["t1"]["envelope_hash"] = A
                result = classify(record)
                self.assertEqual((result["classification"], result["decision_class"]),
                                 ("UNKNOWN", "TOUCHED"))


if __name__ == "__main__":
    unittest.main()
