"""operator 2026-11-10 ("Prefer q0-q2 for CPU rows" + "Yes, fix the message"): a CPU whole-quarter option on q3 is
chosen last, and IDLE-WHY no longer lets a drain row's reason mask the next row's real blocker. Origin: the MI210 sat
idle 15:05Z-19:39Z while afc-v3-q38_flash-tools-mild held q3 (c88-c95) and IDLE-WHY named only the quiet-host drain."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0


def cand(rid, options, rank=50, shape="quarter", est=H, gib=8, bench=False):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 1, "gib": gib, "bench": bench,
            "options": [frozenset(o) for o in options], "shape": shape, "since": NOW, "window_s": est + 900,
            "estimate_s": est}


QOPTS = [{"q0"}, {"q1"}, {"q2"}, {"q3"}]


class Q3Last(unittest.TestCase):
    def test_quarter_row_takes_q0_despite_demand(self):
        rows = [cand("cpu-q", QOPTS), cand("q0-wanter", [{"q0"}], rank=200, gib=10 ** 6)]
        out, _, _ = rf.plan({"q0", "q3"}, rows, 500, now=NOW)
        self.assertEqual([(c["id"], set(o)) for c, o in out], [("cpu-q", {"q0"})])

    def test_q3_when_only_fitting_quarter(self):
        out, _, _ = rf.plan({"q3"}, [cand("cpu-q", QOPTS)], 500, now=NOW)
        self.assertEqual([set(o) for _, o in out], [{"q3"}])

    def test_explicit_q3_untouched(self):
        out, _, _ = rf.plan({"q0", "q3"}, [cand("q3-only", [{"q3"}])], 500, now=NOW)
        self.assertEqual([set(o) for _, o in out], [{"q3"}])


class IdleWhyNamesBlockedRow(unittest.TestCase):
    def test_drain_reason_also_names_gpu_row_blocker(self):
        gq3 = set(rf.GPU_Q3_TOKENS)
        drain = cand("ak-quiet", [{rf.GPU, "q0", "q1", "q2", "q3"}], rank=2, shape="quiet-host", est=1500)
        gpu = cand("ak-mmq", [gq3], rank=43, shape="gpu-q3", est=1700, bench=True)
        end = NOW + 2 * H
        busy = rf.expand({"q0", "q1", "q2", "q3"})
        free = {rf.GPU} | {f"t{k}" for k in range(184, 192)}
        _, idle, _ = rf.plan(free, [drain, gpu], 500, now=NOW, grant_ends=[end],
                             region_ends={t: end for t in busy},
                             region_holders={"q0": "x0", "q1": "x1", "q2": "x2", "q3": "afc-mild"})
        why = idle[rf.GPU]
        self.assertIn("ak-quiet", why)
        self.assertIn("gpu-q3 row ak-mmq", why)
        self.assertIn("c88-c95" if "c88-c95" in why else "c88", why)
        self.assertIn("held by afc-mild", why)
        self.assertIn(rf.dt.datetime.fromtimestamp(end, rf.dt.timezone.utc).strftime("until %H:%MZ"), why)


if __name__ == "__main__":
    unittest.main()
