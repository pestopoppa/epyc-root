"""pipeline-mgmt 2026-11-11: IDLE-WHY names EVERY ready row that could use an idle region, each with its own blocker
(busy region + holder + end, drain-late, port, RAM), at most IDLE_WHY_MAX_ROWS rows then '+N more', one line per region;
placement (plan()'s assignments and pending) is unchanged by the diagnostics."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0


def cand(rid, options, rank=50, shape="quarter", est=H, gib=8, bench=False, ports=None):
    c = {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 1, "gib": gib, "bench": bench,
         "options": [frozenset(o) for o in options], "shape": shape, "since": NOW, "window_s": est + 900,
         "estimate_s": est}
    if ports:
        c["ports"] = ports
    return c


def scenario():
    gq3 = set(rf.GPU_Q3_TOKENS)
    end = NOW + 2 * H
    busy = rf.expand({"q0", "q1", "q2", "q3"})
    free = {rf.GPU} | {f"t{k}" for k in range(184, 192)}
    rows = [cand("ak-quiet", [{rf.GPU, "q0", "q1", "q2", "q3"}], rank=2, shape="quiet-host", est=1500),
            cand("g-busy", [gq3], rank=40, shape="gpu-q3", est=1700, bench=True),
            cand("g-port", [{rf.GPU}], rank=41, shape="gpu", ports=[8099]),
            cand("g-ram", [{rf.GPU}], rank=42, shape="gpu", gib=10 ** 6),
            dict(cand("g-late", [{rf.GPU}], rank=44, shape="gpu", est=10 * H), min_window_s=5 * H)]
    kw = dict(now=NOW, grant_ends=[end], held_ports=[8099], region_ends={t: end for t in busy},
              region_holders={"q0": "x0", "q1": "x1", "q2": "x2", "q3": "afc-mild"})
    return free, rows, kw, end


class IdleWhyAllRows(unittest.TestCase):
    def test_every_row_has_its_own_reason(self):
        free, rows, kw, end = scenario()
        _, idle, _ = rf.plan(free, rows, 500, **kw)
        why = idle[rf.GPU]
        self.assertEqual(why.count("\n"), 0)
        self.assertIn("ak-quiet", why)
        self.assertIn("gpu-q3 row g-busy", why)
        self.assertIn("held by afc-mild", why)
        self.assertIn(rf.dt.datetime.fromtimestamp(end, rf.dt.timezone.utc).strftime("until %H:%MZ"), why)
        self.assertIn("g-port (rank 41) port 8099 held", why)
        self.assertIn("g-ram (rank 42) RAM:", why)
        self.assertIn("g-late (rank 44) drain-late: would end after T", why)

    def test_cap_and_more(self):
        free, rows, kw, _ = scenario()
        rows += [dict(cand(f"g-x{k}", [{rf.GPU}], rank=60 + k, shape="gpu", est=10 * H), min_window_s=5 * H) for k in range(10)]
        _, idle, _ = rf.plan(free, rows, 500, **kw)
        why = idle[rf.GPU]
        self.assertEqual(why.count("; also "), rf.IDLE_WHY_MAX_ROWS - 1)
        self.assertTrue(why.endswith(f"; +{len(rows) - rf.IDLE_WHY_MAX_ROWS} more"), why)

    def test_smoke_waits_appended_in_line(self):
        line = rf.idle_why_line("grant a blocked", ["b x", "c WAIT-FOR-SMOKE: queued GPU smoke rank 3 runs first"])
        self.assertIn("; also c WAIT-FOR-SMOKE", line)


class PlanUnchanged(unittest.TestCase):
    """The placement contract: assignments, pending and drain state equal what the pre-change single-row IDLE-WHY plan
    produced (frozen expectations), across a drain, a backfill and a plain fixpoint snapshot."""

    def snap(self, free, rows, ram, **kw):
        out, _, pending = rf.plan(set(free), [dict(r) for r in rows], ram, **kw)
        return ([(c["id"], sorted(o)) for c, o in out], [c["id"] for c in pending],
                plan_drain_id(), dict(rf.plan.hard_end))

    def test_drain_snapshot(self):
        free, rows, kw, _ = scenario()
        got = self.snap(free, rows, 500, **kw)
        self.assertEqual(got, ([], ["ak-quiet", "g-port", "g-ram", "g-busy", "g-late"], "ak-quiet", {}))

    def test_fixpoint_snapshot(self):
        rows = [cand("a", [{"q0"}, {"q1"}, {"q2"}, {"q3"}], rank=5), cand("b", [{"q1"}], rank=6),
                cand("c", [{rf.GPU}], rank=7, shape="gpu"), cand("d", [{"q2"}], rank=8, gib=10 ** 6)]
        got = self.snap({"q0", "q1", "q2", rf.GPU}, rows, 500, now=NOW)
        self.assertEqual(got, ([("a", ["q0"]), ("b", ["q1"]), ("c", [rf.GPU])], ["d"], None, {}))


def plan_drain_id():
    return rf.plan.last_drain[0]["id"] if rf.plan.last_drain else None


if __name__ == "__main__":
    unittest.main()
