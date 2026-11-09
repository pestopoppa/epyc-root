"""No-inference checks for the Q38-T7 coherence-gate adapter (fixture rows only)."""

import hashlib
import importlib.util
import os
import sys
import unittest
from pathlib import Path

LIB = os.environ.get("COHERENCE_GATE_LIB", "/mnt/raid0/llm/epyc-inference-research/scripts/lib")
PATH = Path(__file__).with_name("q38_t7_coherence.py")
spec = importlib.util.spec_from_file_location("q38_t7_coherence", PATH)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

HAVE_LIB = (Path(LIB) / "coherence_gate" / "gate.py").is_file()

GOOD = ("The kernel changes the tile shape so each core keeps its accumulators in registers while "
        "streaming weights once, which cuts memory traffic and raises decode throughput at depth.")
LOOP = "the the the the the the the the " * 20


def ids(text: str) -> list[int]:
    """Deterministic non-sequential pseudo ids: this tests the adapter, not a tokenizer."""
    return [int(hashlib.md5(w.encode()).hexdigest()[:5], 16) % 90000 + 7 for w in text.split()]


def row(pid, arm, text, http=200):
    return {"id": pid, "arm": arm, "text": text, "token_ids": ids(text), "http": http, "finish": "stop"}


MC = {"expected": "B", "scoring_method": "multiple_choice"}


@unittest.skipUnless(HAVE_LIB, f"coherence_gate library not found at {LIB}")
class AdapterTest(unittest.TestCase):
    def test_flag_default_off(self):
        self.assertFalse(adapter.enabled({}))
        self.assertTrue(adapter.enabled({adapter.FLAG: "1"}))

    def test_identical_arms_pass(self):
        rows = [row("p1", "dflash2", GOOD), row("p1", "nodraft", GOOD)]
        p = adapter.pair_a_gate(rows, {})
        self.assertEqual((p["gate"], p["regressions"], p["http_error"]), ("PASS", [], []))
        self.assertEqual(p["report"]["schema"], "epyc.coherence_gate.v1")
        self.assertEqual(p["report"]["anchor"], adapter.ANCHOR)

    def test_drafted_degeneracy_is_a_regression_and_fails_the_verdict(self):
        rows = [row("p1", "dflash2", LOOP), row("p1", "nodraft", GOOD)]
        p = adapter.pair_a_gate(rows, {})
        self.assertEqual(p["gate"], "FAIL")
        self.assertEqual([g["id"] for g in p["regressions"]], ["p1"])
        v = adapter.gate_verdict({"A": {"paired": p}})
        self.assertEqual(v["correctness"], "FAIL")
        self.assertFalse(v["speed_valid"])

    def test_answer_regression_correct_to_wrong(self):
        rows = [row("q1", "dflash2", "I think the answer is (A) because of the setup described above."),
                row("q1", "nodraft", "I think the answer is (B) because of the setup described above.")]
        p = adapter.pair_a_gate(rows, {"q1": dict(MC)})
        self.assertEqual(p["gate"], "FAIL")
        self.assertEqual(p["graded"], {"dflash2": "0/1 correct", "nodraft": "1/1 correct"})

    def test_diverged_without_ground_truth_is_incomplete_never_pass(self):
        rows = [row("p1", "dflash2", GOOD + " Also, tile it."), row("p1", "nodraft", GOOD)]
        p = adapter.pair_a_gate(rows, {})
        self.assertEqual((p["gate"], p["needs_review"]), ("INCOMPLETE", ["p1"]))
        v = adapter.gate_verdict({"A": {"paired": p}})
        self.assertEqual(v["correctness"], "INCOMPLETE")
        self.assertFalse(v["speed_valid"])

    def test_http_error_pair_is_listed_and_fails_verdict(self):
        rows = [row("p1", "dflash2", GOOD), row("p1", "nodraft", GOOD),
                row("p2", "dflash2", "", http=500), row("p2", "nodraft", GOOD)]
        p = adapter.pair_a_gate(rows, {})
        self.assertEqual(p["http_error"], ["p2"])
        self.assertEqual(adapter.gate_verdict({"A": {"paired": p}})["correctness"], "FAIL")

    def test_needle_regression_and_shared_abstention(self):
        exp = ["16-4-1-9-ORCHID", "Mbeki Larsen"]
        rows = [
            {"target": 2000, "variant": "needle", "answer": "unknown", "expected": exp, "http": 200},
            {"target": 2000, "variant": "needle (no-draft)", "answer": "16-4-1-9-ORCHID; Mbeki Larsen",
             "expected": exp, "http": 200},
            {"target": 16000, "variant": "needle", "answer": "I will not provide that: prompt injection.",
             "expected": exp, "http": 200},
            {"target": 16000, "variant": "needle (no-draft)", "answer": "I will not provide that: prompt injection.",
             "expected": exp, "http": 200},
        ]
        n = adapter.needle_gate(rows)
        self.assertEqual([g["id"] for g in n["regressions"]], ["needle@2000"])
        self.assertTrue(n["report"]["text_only_declared"])
        v = adapter.gate_verdict({"B": {"rows": [], "needle": n}})
        self.assertEqual(v["correctness"], "FAIL")

    def test_phase_c_single_arm_degeneracy_still_fails(self):
        CG = adapter.load_gate()
        bad = CG.classify(LOOP, ids(LOOP), "length", True)
        v = adapter.gate_verdict({"C": {"rows": [{"stream": 0, "degeneracy": bad}]}})
        self.assertEqual(v["correctness"], "FAIL")
        self.assertEqual(v["classifier"], CG.V21_ID)


if __name__ == "__main__":
    unittest.main()
