"""Deterministic demonstrations of the EV-15b T=1 identity; no model calls."""
import math
import unittest


def normalize(values):
    peak = max(values)
    weights = [math.exp(value - peak) for value in values]
    total = sum(weights)
    return [value / total for value in weights]


class ReadoutSpecTest(unittest.TestCase):
    def test_full_vocabulary_denominator_cancels_at_temperature_one(self):
        logits = [-1.1, 0.3, 1.2, -0.4, 0.1, 0.9, -1.4, 2.0, 0.5, 3.5, -2.0]
        log_denom = math.log(sum(math.exp(x) for x in logits))
        full_logprobs = [x - log_denom for x in logits]
        from_logprobs = normalize(full_logprobs[:9])
        from_logits = normalize(logits[:9])
        for left, right in zip(from_logprobs, from_logits, strict=True):
            self.assertAlmostEqual(left, right, places=14)
        self.assertAlmostEqual(sum(from_logprobs), 1.0)
        self.assertLess(sum(math.exp(x) for x in full_logprobs[:9]), 1.0)

    def test_temperature_change_is_not_the_same_distribution(self):
        scores = [-1.1, 0.3, 1.2, -0.4, 0.1, 0.9, -1.4, 2.0, 0.5]
        one = normalize(scores)
        half = normalize([x / 0.5 for x in scores])
        self.assertGreater(max(abs(a - b) for a, b in zip(one, half, strict=True)), 0.1)


if __name__ == '__main__':
    unittest.main()
