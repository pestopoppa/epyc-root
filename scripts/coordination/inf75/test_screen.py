import unittest

from screen import classify

H = "a" * 64
J = "b" * 64


def sample():
    shape = {"anchor_lines": 20, "candidate_lines": 20,
             "hunks": {"h1": {"executed": False}, "h2": {"executed": True,
                       "anchor_branches": [3, 4], "candidate_branches": [3, 4]}},
             "knobs": {"GGML_SCALE_SPLIT": {"executed": False}},
             "anchor_hip_matmul_routes": {}, "candidate_hip_matmul_routes": {},
             "anchor_op_backend": {"MUL_MAT:CPU": 3},
             "candidate_op_backend": {"MUL_MAT:CPU": 3}}
    return {"author_target": False, "variant": "cpu", "census": {"verified": True,
            "fresh": True, "observed": True, "freshness_key": H, "envelope_hash": J,
            "shapes": ["decode"], "nodes_total": 1001, "expected_ops_present": True,
            "device_seen": True},
            "footprint": {"verified": True, "sha256": H, "nonempty_diff": True,
            "hunks": {"h1": "body", "h2": "predicate"}, "knobs": {
                "GGML_SCALE_SPLIT": {"before": "0", "after": "1"}},
            "opaque_reasons": [], "change_class": "shared_machinery", "variants_affected": []},
            "t1": {"verified": True, "anchor_profile_sha256": H,
                   "candidate_profile_sha256": J, "envelope_hash": J, "shapes": {"decode": shape}}}


class ScreenTests(unittest.TestCase):
    def test_unexecuted_default_flip_is_inert_with_witness(self):
        result = classify(sample())
        self.assertEqual((result["classification"], result["tier"]), ("INERT", "T1"))
        self.assertEqual(result["witnesses"]["shape_envelope_hash"], J)

    def test_executed_flip_is_touched_even_if_effective_values_equal(self):
        r = sample()
        r["t1"]["shapes"]["decode"]["knobs"]["GGML_SCALE_SPLIT"] = {
            "executed": True, "anchor_value": "1", "candidate_value": "1"}
        result = classify(r)
        self.assertEqual(result["classification"], "TOUCHED")
        self.assertEqual(result["touched_detail"]["knob_reads"], ["GGML_SCALE_SPLIT"])

    def test_unchanged_knob_effective_value_is_inert(self):
        r = sample()
        r["footprint"]["knobs"]["GGML_SCALE_SPLIT"]["after"] = "0"
        r["t1"]["shapes"]["decode"]["knobs"]["GGML_SCALE_SPLIT"] = {
            "executed": True, "anchor_value": "0", "candidate_value": "0"}
        self.assertEqual(classify(r)["classification"], "INERT")

    def test_t0_requires_nonempty_matching_object_inventory_and_recipe(self):
        r = sample()
        r["t0"] = {"verified": True, "anchor_objects": {"lib": H}, "candidate_objects": {"lib": H},
                   "anchor_recipe": H, "candidate_recipe": H, "anchor_env": J, "candidate_env": J}
        self.assertEqual(classify(r)["tier"], "T0")
        r["t0"]["candidate_objects"]["other"] = J
        self.assertEqual(classify(r)["tier"], "T1")

    def test_bad_census_or_incomplete_coverage_fails_closed(self):
        for mutate in (
            lambda r: r["census"].update(nodes_total=1000),
            lambda r: r["census"].update(fresh=False),
            lambda r: r["t1"].update(shapes={}),
            lambda r: r["t1"]["shapes"]["decode"].update(candidate_lines=0),
            lambda r: r["t1"]["shapes"]["decode"]["hunks"].pop("h1"),
            lambda r: r["t1"].update(candidate_profile_sha256=""),
        ):
            r = sample()
            mutate(r)
            with self.subTest(record=r):
                result = classify(r)
                self.assertEqual((result["classification"], result["decision_class"]), ("UNKNOWN", "TOUCHED"))

    def test_changed_branch_body_and_route_are_touched(self):
        for mutate, field in (
            (lambda s: s["hunks"]["h1"].update(executed=True), "executed_hunks"),
            (lambda s: s["hunks"]["h2"].update(candidate_branches=[0, 7]), "changed_branches"),
            (lambda s: s["candidate_op_backend"].update({"MUL_MAT:CPU": 4}), "changed_routes"),
        ):
            r = sample()
            mutate(r["t1"]["shapes"]["decode"])
            result = classify(r)
            self.assertEqual(result["classification"], "TOUCHED")
            self.assertTrue(result["touched_detail"][field])

    def test_missing_coverage_default_flip_is_conservatively_touched(self):
        r = sample()
        del r["t1"]
        result = classify(r)
        self.assertEqual(result["classification"], "TOUCHED")
        self.assertEqual(result["touched_detail"]["potential_knob_reads"], ["GGML_SCALE_SPLIT"])
        self.assertNotIn("knob_reads", result["touched_detail"])

    def test_nonempty_diff_missing_hunks_never_passes(self):
        r = sample()
        r["footprint"]["hunks"] = {}
        self.assertEqual(classify(r)["classification"], "UNKNOWN")

    def test_author_is_always_touched(self):
        self.assertEqual(classify({"author_target": True})["classification"], "TOUCHED")
        r = sample()
        r["author_target"] = True
        self.assertEqual(classify(r)["classification"], "TOUCHED")


if __name__ == "__main__":
    unittest.main()
