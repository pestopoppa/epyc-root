import copy
import unittest

from episode_capture import capture_episode, digest


def example(**changes):
    args = dict(run_id="r1", episode_id="e1", question_id="q1", request={"prompt": "p"},
                response={"content": "FINAL: 1"}, selected_index=3, parse_status="ok",
                candidate_pool_sha256="a" * 64, order=[7, 3])
    args.update(changes)
    return capture_episode(**args)


class CaptureTests(unittest.TestCase):
    def test_categorical_preserved_without_fabricated_vector(self):
        row = example()
        self.assertEqual(row["response"]["content"], "FINAL: 1")
        self.assertEqual(row["selected_source_index"], 3)
        self.assertIsNone(row["distribution"]["probabilities"])
        self.assertIsNone(row["distribution"]["retained_mass"])
        self.assertFalse(row["sc43_vector_compliant"])
        self.assertEqual(row["locator"], {"run_id": "r1", "episode_id": "e1"})

    def test_structural_vector_preserved_but_not_attested(self):
        native = {"probabilities": [0.1, 0.2], "score_tokens": ["A", "B"], "K": 2,
                  "retained_mass": 0.3, "readout_method": "native", "aggregation_timing": "pre-order-aggregation",
                  "native_provenance": "verified", "status": "verified"}
        row = example(native_distribution=native)
        self.assertEqual(row["distribution"]["probabilities"], [0.1, 0.2])
        self.assertEqual(row["distribution"]["status"], "structurally_complete")
        self.assertEqual(row["distribution"]["native_provenance"], "unverified")
        self.assertFalse(row["sc43_vector_compliant"])

    def test_partial_or_invalid_vector_fails_closed(self):
        vectors = [
            {"probabilities": [0.1], "score_tokens": ["A", "B"], "K": 2},
            {"probabilities": [0.8, 0.8], "score_tokens": ["A", "B"], "K": 2, "retained_mass": 1.6},
            {"probabilities": [0.2, 0.2], "score_tokens": ["A", "A"], "K": 2, "retained_mass": 0.4},
        ]
        for v in vectors:
            with self.subTest(v=v):
                row = example(native_distribution=v)
                self.assertEqual(row["distribution"]["status"], "incomplete")
                self.assertFalse(row["sc43_vector_compliant"])

    def test_unknown_selection_stays_unknown(self):
        row = example(selected_index=None, parse_status="invalid")
        self.assertIsNone(row["selected_source_index"])
        with self.assertRaises(ValueError):
            example(selected_index=3, parse_status="invalid")

    def test_digest_detects_response_change(self):
        row = example()
        record_hash = row.pop("record_sha256")
        self.assertEqual(record_hash, digest(row))
        changed = copy.deepcopy(row)
        changed["response"]["content"] = "FINAL: 0"
        self.assertNotEqual(record_hash, digest(changed))


if __name__ == "__main__":
    unittest.main()
