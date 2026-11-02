"""Synthetic policy-only controls; no GPU, artifact or production authority."""
import copy
import unittest

from validator import validate

FINGERPRINT = "a" * 64


def fixture():
    candidate = {"tenant_id": "synthetic", "mode": "mtp_off", "budget_profile": "solo",
                 "context_tokens": 5000, "np_ceiling": 4}
    snapshot = {"fingerprint": FINGERPRINT,
                "tenants": {"synthetic": {"available": True, "path": "/synthetic/model.gguf",
                                          "bytes": 100, "sha256": "b" * 64, "modes": ["mtp_off"]}},
                "frontiers": [{"tenant_id": "synthetic", "mode": "mtp_off", "budget_profile": "solo",
                               "context_tokens": 8192, "np_ceiling": 8},
                              {"tenant_id": "synthetic", "mode": "mtp_off", "budget_profile": "solo",
                               "context_tokens": 16384, "np_ceiling": 4}]}
    return candidate, snapshot


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.c, self.s = fixture()

    def check(self, c=None, s=None, **kwargs):
        return validate(self.c if c is None else c, self.s if s is None else s,
                        enabled=True, expected_fingerprint=kwargs.get("expected", FINGERPRINT))

    def test_default_off_and_identity(self):
        self.assertFalse(validate(self.c, self.s, expected_fingerprint=FINGERPRINT).accepted)
        self.assertFalse(self.check(expected="c" * 64).accepted)
        self.assertFalse(validate(self.c, None, enabled=True, expected_fingerprint=FINGERPRINT).accepted)

    def test_context_bucket_and_ceiling(self):
        self.assertEqual(self.check().ceiling, 8)
        self.c.update(context_tokens=8193, np_ceiling=5)
        self.assertEqual(self.check().reason, "ceiling_exceeded")
        self.c["context_tokens"] = 16385
        self.assertEqual(self.check().reason, "frontier_missing")

    def test_rejects_bool_unknown_extra_and_unavailable(self):
        for key, value in (("context_tokens", True), ("np_ceiling", False), ("tenant_id", "missing"),
                           ("budget_profile", "other"), ("mode", "mtp_on"), ("extra", 1)):
            candidate = copy.deepcopy(self.c)
            candidate[key] = value
            self.assertFalse(self.check(c=candidate).accepted, key)
        self.s["tenants"]["synthetic"]["available"] = False
        self.assertEqual(self.check().reason, "tenant_unavailable")

    def test_refuses_missing_identity_null_and_duplicate_frontier(self):
        self.s["tenants"]["synthetic"]["sha256"] = "unknown"
        self.assertEqual(self.check().reason, "tenant_identity")
        _, self.s = fixture()
        self.s["frontiers"][0]["np_ceiling"] = None
        self.assertEqual(self.check().reason, "frontier_unknown")
        self.s["frontiers"].append(copy.deepcopy(self.s["frontiers"][0]))
        self.assertEqual(self.check().reason, "frontier_duplicate")


if __name__ == "__main__":
    unittest.main()
