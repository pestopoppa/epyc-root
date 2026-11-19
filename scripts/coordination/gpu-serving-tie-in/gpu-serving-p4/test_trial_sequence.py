"""Synthetic sequencing only; callbacks have no external effects."""
import unittest

from trial_sequence import run_trial


class TrialSequenceTests(unittest.TestCase):
    def test_success_requires_all_steps(self):
        calls = []
        def operation(name, status):
            def run():
                calls.append(name)
                return {"status": status, "evidence": name}
            return run
        result = run_trial(("apply", "evaluate"), {
            "apply": operation("apply", 200), "evaluate": operation("evaluate", 204)
        }, enabled=True)
        self.assertTrue(result.succeeded)
        self.assertEqual(calls, ["apply", "evaluate"])
        self.assertEqual(result.responses[1][1].evidence, "evaluate")

    def test_failure_is_sticky_and_later_callback_is_not_called(self):
        for status in (500, 599, None, "200"):
            with self.subTest(status=status):
                calls = []
                def operation(name, value):
                    def run():
                        calls.append(name)
                        return {"status": value, "evidence": name}
                    return run
                result = run_trial(("first", "second", "third"), {
                    "first": operation("first", 200),
                    "second": operation("second", status),
                    "third": operation("third", 200),
                }, enabled=True)
                self.assertFalse(result.succeeded)
                self.assertEqual(calls, ["first", "second"])
                self.assertEqual(result.responses[-1][1].status, status)
                self.assertEqual(result.responses[-1][1].evidence, "second")

    def test_exception_stops_and_is_retained(self):
        error = TimeoutError("synthetic")
        calls = []
        def fail():
            raise error
        result = run_trial(("fail", "later"), {
            "fail": fail, "later": lambda: calls.append("later")
        }, enabled=True)
        self.assertFalse(result.succeeded)
        self.assertIs(result.responses[0][1].error, error)
        self.assertEqual(calls, [])

    def test_disabled_and_invalid_steps_invoke_nothing(self):
        calls = []
        operation = lambda: calls.append("called")
        self.assertEqual(run_trial(("one",), {"one": operation}).reason, "disabled")
        for steps, ops in (((), {}), (("one", "two"), {"one": operation}),
                           (("one", "one"), {"one": operation}),
                           (("one",), {"one": operation, "extra": operation})):
            self.assertFalse(run_trial(steps, ops, enabled=True).succeeded)
        self.assertEqual(calls, [])

    def test_malformed_operation_result_refuses(self):
        for value in (None, {}, {"status": 200, "extra": True}):
            with self.subTest(value=value):
                result = run_trial(("one",), {"one": lambda: value}, enabled=True)
                self.assertFalse(result.succeeded)
                self.assertIs(result.responses[0][1].evidence, value)


if __name__ == "__main__":
    unittest.main()
