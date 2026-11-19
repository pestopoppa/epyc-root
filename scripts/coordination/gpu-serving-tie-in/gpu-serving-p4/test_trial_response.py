"""Synthetic response classification; no operation or controller is invoked."""
import unittest

from trial_response import classify_response


class TrialResponseTests(unittest.TestCase):
    def test_all_http_statuses(self):
        evidence = {"request_id": "synthetic"}
        for status in range(100, 600):
            with self.subTest(status=status):
                result = classify_response(status=status, evidence=evidence)
                self.assertEqual(result.succeeded, 200 <= status <= 299)
                self.assertEqual(result.status, status)
                self.assertIs(result.evidence, evidence)

    def test_missing_and_malformed_statuses_refuse(self):
        for status in (None, True, False, 99, 600, "200", 200.0, [], {}):
            with self.subTest(status=status):
                result = classify_response(status=status)
                self.assertFalse(result.succeeded)
                self.assertEqual(result.reason, "missing_or_malformed_status")
                self.assertIs(result.status, status)

    def test_error_overrides_success_and_is_preserved(self):
        error = TimeoutError("synthetic timeout")
        evidence = {"partial": True}
        result = classify_response(status=200, evidence=evidence, error=error)
        self.assertFalse(result.succeeded)
        self.assertEqual(result.reason, "operation_error")
        self.assertIs(result.error, error)
        self.assertIs(result.evidence, evidence)
        self.assertEqual(result.status, 200)

    def test_previous_success_does_not_authorize_current_failure(self):
        self.assertTrue(classify_response(status=200).succeeded)
        self.assertFalse(classify_response(status=503).succeeded)


if __name__ == "__main__":
    unittest.main()
