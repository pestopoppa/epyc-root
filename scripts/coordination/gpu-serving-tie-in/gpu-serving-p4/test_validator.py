"""Synthetic policy-only controls; no GPU, artifact or production authority."""
import copy
import unittest

from validator import validate

FINGERPRINT = "a" * 64


def fixture():
    candidate = {"tenant_id": "synthetic", "np_slots": 4}
    snapshot = {"fingerprint": FINGERPRINT,
                "tenants": {"synthetic": {"available": True, "path": "/synthetic/model.gguf",
                                          "bytes": 100, "sha256": "b" * 64, "modes": ["mtp_off"],
                                          "co_residency": "allowed"}},
                "frontiers": [{"tenant_id": "synthetic", "mode": "mtp_off", "budget_profile": "solo_resident",
                               "context_tokens": 8192, "np_ceiling": 8},
                              {"tenant_id": "synthetic", "mode": "mtp_off", "budget_profile": "solo_resident",
                               "context_tokens": 16384, "np_ceiling": 4}]}
    return candidate, snapshot


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.c, self.s = fixture()
        self.args = dict(enabled=True, expected_fingerprint=FINGERPRINT,
                         allowed_tenants=frozenset({"synthetic"}), mode="mtp_off",
                         budget_profile="solo_resident", context_tokens=5000)

    def check(self, c=None, s=None, **kwargs):
        return validate(self.c if c is None else c, self.s if s is None else s,
                        **(self.args | kwargs))

    def test_gate_allowlist_and_identity(self):
        self.assertEqual(self.check(enabled=False).reason, "disabled")
        self.assertEqual(self.check(allowed_tenants=frozenset()).reason, "tenant_not_allowed")
        self.assertEqual(self.check(expected_fingerprint="c" * 64).reason, "snapshot_identity")
        self.assertFalse(validate(self.c, self.s, enabled=True, expected_fingerprint=FINGERPRINT,
                                  mode="mtp_off", budget_profile="solo_resident", context_tokens=5000).accepted)

    def test_exact_candidate_and_serving_shape(self):
        for candidate in ({"tenant_id": "synthetic", "np_slots": True},
                          {"tenant_id": "synthetic", "np_slots": 0},
                          {"tenant_id": "synthetic", "np_slots": 4, "mode": "mtp_off"},
                          {"tenant_id": "synthetic", "np_ceiling": 4}):
            self.assertEqual(self.check(c=candidate).reason, "candidate_schema")
        self.assertEqual(self.check(context_tokens=True).reason, "serving_shape")
        self.assertEqual(self.check(mode="unknown").reason, "mode_unavailable")
        self.assertEqual(self.check(budget_profile="unknown").reason, "frontier_missing")

    def test_context_bucket_and_ceiling(self):
        self.assertEqual(self.check(c={"tenant_id": "synthetic", "np_slots": 8}).ceiling, 8)
        self.assertEqual(self.check(c={"tenant_id": "synthetic", "np_slots": 9}).reason, "ceiling_exceeded")
        self.assertEqual(self.check(c={"tenant_id": "synthetic", "np_slots": 5}, context_tokens=8193).reason,
                         "ceiling_exceeded")
        self.assertEqual(self.check(context_tokens=16385).reason, "frontier_missing")

    def test_forbidden_co_residency_requires_solo(self):
        self.s["tenants"]["synthetic"]["co_residency"] = "forbidden"
        self.assertTrue(self.check().accepted)
        for profile in ("phase2_resident_set", "other"):
            self.assertEqual(self.check(budget_profile=profile).reason, "co_residency_forbidden")
        self.s["tenants"]["synthetic"]["co_residency"] = "unknown"
        self.assertEqual(self.check().reason, "tenant_identity")

    def test_refuses_unavailable_identity_null_and_duplicate(self):
        self.s["tenants"]["synthetic"]["available"] = False
        self.assertEqual(self.check().reason, "tenant_unavailable")
        _, self.s = fixture()
        self.s["tenants"]["synthetic"]["sha256"] = "unknown"
        self.assertEqual(self.check().reason, "tenant_identity")
        _, self.s = fixture()
        self.s["frontiers"][0]["np_ceiling"] = None
        self.assertEqual(self.check().reason, "frontier_unknown")
        self.s["frontiers"].append(copy.deepcopy(self.s["frontiers"][0]))
        self.assertEqual(self.check().reason, "frontier_duplicate")


if __name__ == "__main__":
    unittest.main()
