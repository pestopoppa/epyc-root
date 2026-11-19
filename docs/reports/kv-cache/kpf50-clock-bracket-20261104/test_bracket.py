import hashlib
import json
import unittest

from bracket import verify


def fixture(phase, pid, base, tick):
    rows = [dict(host_before_ns=base+i*4, hsa_ticks=tick+i, host_after_ns=base+i*4+i+1) for i in range(3)]
    raw = json.dumps(dict(schema="epyc.kpf50.hsa-clock.v1", pid=pid, frequency_hz=1_000_000, samples=rows)).encode()
    selected = rows[0]
    witness = dict(schema="kpf50.clock-sample.v1", window="full-a", run_id="run1", phase=phase,
                   hsa_tick=selected["hsa_ticks"], hsa_hz=1_000_000,
                   mono_before_ns=selected["host_before_ns"], mono_after_ns=selected["host_after_ns"],
                   native_sha256=hashlib.sha256(raw).hexdigest(), producer_sha256="a"*64,
                   pid=pid, birth_ticks=pid*10, process_start_bound_ns=base,
                   process_end_bound_ns=base+20)
    return witness, raw


class BracketTests(unittest.TestCase):
    def setUp(self):
        self.before, self.br = fixture("clock_before", 10, 100, 1000)
        self.after, self.ar = fixture("clock_after", 11, 200, 2000)

    def test_step_inside_same_host_clock_domain(self):
        result = verify(self.before, self.after, self.br, self.ar, window="full-a", run_id="run1",
                        step_begin_ns=120, step_end_ns=180)
        self.assertTrue(result["verified"])
        self.assertEqual(result["step_interval_monotonic_ns"], [120, 180])

    def test_rejects_wrong_lineage_and_phase(self):
        bad = dict(self.after, run_id="other")
        with self.assertRaises(ValueError):
            verify(self.before, bad, self.br, self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=180)

    def test_rejects_tampering_and_unbracketed_step(self):
        with self.assertRaises(ValueError):
            verify(self.before, self.after, self.br+b" ", self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=180)
        with self.assertRaises(ValueError):
            verify(self.before, self.after, self.br, self.ar, window="full-a", run_id="run1", step_begin_ns=99, step_end_ns=180)
        with self.assertRaises(ValueError):
            verify(self.before, self.after, self.br, self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=205)

    def test_rejects_bad_native_identity_and_inverted_interval(self):
        wrong = dict(self.before, phase="clock_after")
        with self.assertRaises(ValueError):
            verify(wrong, self.after, self.br, self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=180)
        with self.assertRaises(ValueError):
            verify(self.before, self.after, self.br, self.ar, window="full-a", run_id="run1", step_begin_ns=180, step_end_ns=120)

    def test_rejects_bad_identity_types_lifetime_and_non_narrowest_selection(self):
        bad_pid = dict(self.before, pid=True)
        with self.assertRaises(ValueError):
            verify(bad_pid, self.after, self.br, self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=180)
        bad_hz = dict(self.before, hsa_hz=True)
        with self.assertRaises(ValueError):
            verify(bad_hz, self.after, self.br, self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=180)
        outside = json.loads(self.br)
        outside["samples"][0]["host_before_ns"] = 99
        raw = json.dumps(outside).encode()
        witness = dict(self.before, native_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            verify(witness, self.after, raw, self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=180)
        wrong_selection = dict(self.before, hsa_tick=self.before["hsa_tick"]+1,
                               mono_before_ns=self.before["mono_before_ns"]+4,
                               mono_after_ns=self.before["mono_after_ns"]+6)
        with self.assertRaises(ValueError):
            verify(wrong_selection, self.after, self.br, self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=180)

    def test_rejects_any_native_sample_overlapping_step(self):
        native = json.loads(self.br)
        native["samples"][2]["host_before_ns"] = 119
        native["samples"][2]["host_after_ns"] = 121
        raw = json.dumps(native).encode()
        witness = dict(self.before, native_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            verify(witness, self.after, raw, self.ar, window="full-a", run_id="run1", step_begin_ns=120, step_end_ns=180)


if __name__ == "__main__":
    unittest.main()
