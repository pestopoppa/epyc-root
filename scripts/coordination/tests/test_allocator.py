#!/usr/bin/env python3
"""Tests of the single-snapshot allocator in scripts/coordination/rowflow/rowflow.py: a seeded property/simulation sweep
over plan() (pure) plus one regression per 2026-11-01 incident (DF2 arm-time pin, whole-host dry run on one quarter,
GPU parser flag, fetch-only row holding a quarter, grant healing, quarters_of). Stdlib only; every file write happens
under a temp dir; no live compute-flags file is touched and no process is started."""
import json
import os
import random
import shutil
import tempfile
import textwrap
import time
import unittest

import sys
_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RF = os.path.join(_COORD, "rowflow")
sys.path.insert(0, _RF)
import rowflow as rf  # noqa: E402

Q = set(rf.QUARTERS)
ALL = set(rf.REGIONS)


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    if mode:
        os.chmod(path, mode)


def cand(cid, kind="grant", lane="cpu", rank=100, lane_count=0, gib=0, bench=False, options=()):
    return {"id": cid, "kind": kind, "lane": lane, "rank": rank, "lane_count": lane_count, "gib": gib, "bench": bench,
            "options": [frozenset(o) for o in options]}


def random_state(rng):
    free = {r for r in rf.REGIONS if rng.random() < 0.6}
    cands = []
    for i in range(rng.randint(0, 12)):
        lane = rng.choice(["cpu", "gpu"])
        opts = set()
        for _ in range(rng.randint(1, 4)):
            o = {r for r in rf.REGIONS if rng.random() < 0.4}
            if lane == "gpu":
                o.add(rf.GPU)
            if not o:
                o.add(rng.choice(rf.REGIONS))
            opts.add(frozenset(o))
        cands.append(cand(f"c{i}", kind=rng.choice(["grant", "dryrun"]), lane=lane, rank=rng.randint(0, 200),
                          lane_count=rng.randint(0, 4), gib=rng.randint(0, 200), bench=rng.random() < 0.3, options=sorted(opts, key=sorted)))
    return free, cands, rng.randint(60, 1100), rng.random() < 0.5


def fits(c, free, ram, gpu_open):
    """A candidate is placeable iff some option is within `free`, survives the bench/q3 rule and the RAM margin holds."""
    if ram - float(c["gib"]) < rf.RAM_MARGIN_GIB:
        return False
    for o in c["options"]:
        if not o or not o <= free:
            continue
        if c["bench"] and gpu_open and "q3" in o:
            continue
        return True
    return False


class PlanProperties(unittest.TestCase):
    N = 2000

    def test_plan_invariants_over_random_states(self):
        rng = random.Random(20261101)
        placed_total = 0
        for n in range(self.N):
            free, cands, ram_gib, gpu_open = random_state(rng)
            snapshot = json.dumps([sorted(free), [{**c, "options": [sorted(o) for o in c["options"]]} for c in cands], ram_gib, gpu_open])
            assigned, idle, pending = rf.plan(set(free), [dict(c) for c in cands], ram_gib, gpu_open)
            # (i) no double booking
            used = set()
            for c, o in assigned:
                self.assertTrue(o <= free, f"state {n}: {c['id']} got {sorted(o)} outside free {sorted(free)}\n{snapshot}")
                self.assertFalse(used & o, f"state {n}: region handed twice: {sorted(used & o)}\n{snapshot}")
                self.assertIn(o, c["options"], f"state {n}: {c['id']} assigned an option it never offered\n{snapshot}")
                used |= o
            remaining = free - used
            # (iii) cumulative RAM budget
            ram = float(ram_gib)
            for c, o in assigned:
                ram -= float(c["gib"])
                self.assertGreaterEqual(ram, rf.RAM_MARGIN_GIB, f"state {n}: RAM margin broken at {c['id']}\n{snapshot}")
            # (ii) no idle region while a fitting row is ready
            ids_assigned = {c["id"] for c, _ in assigned}
            self.assertEqual(ids_assigned | {c["id"] for c in pending}, {c["id"] for c in cands}, f"state {n}: a candidate vanished\n{snapshot}")
            for c in pending:
                self.assertFalse(fits(c, remaining, ram, gpu_open),
                                 f"state {n}: {c['id']} fits remaining free {sorted(remaining)} (ram {ram}) but was left pending\n{snapshot}")
            # (v) idle dict
            self.assertEqual(set(idle), remaining, f"state {n}: idle keys != remaining free\n{snapshot}")
            for r, why in idle.items():
                self.assertIsInstance(why, str)
                self.assertTrue(why.strip(), f"state {n}: empty idle reason for {r}\n{snapshot}")
            placed_total += len(assigned)
        self.assertGreater(placed_total, self.N // 2, "the sweep never exercised placement; the generator is degenerate")

    def test_plan_is_pure(self):
        rng = random.Random(7)
        for _ in range(50):
            free, cands, ram, gpu_open = random_state(rng)
            before = json.dumps([sorted(free), [{**c, "options": [sorted(o) for o in c["options"]]} for c in cands]])
            a1 = rf.plan(free, cands, ram, gpu_open)
            a2 = rf.plan(free, cands, ram, gpu_open)
            after = json.dumps([sorted(free), [{**c, "options": [sorted(o) for o in c["options"]]} for c in cands]])
            self.assertEqual(before, after, "plan() mutated its inputs")
            self.assertEqual([(c["id"], sorted(o)) for c, o in a1[0]], [(c["id"], sorted(o)) for c, o in a2[0]], "plan() is not deterministic")

    def test_starved_lane_first_then_rank_then_grant(self):
        # (iv) starved lane: lower lane_count wins the single free region
        a = cand("a", lane="cpu", lane_count=3, rank=1, options=[{"q1"}])
        b = cand("b", lane="gpu", lane_count=0, rank=200, options=[{"q1"}])
        assigned, idle, pending = rf.plan({"q1"}, [a, b], 1000)
        self.assertEqual([c["id"] for c, _ in assigned], ["b"])
        self.assertEqual([c["id"] for c in pending], ["a"])
        self.assertEqual(idle, {})
        # equal lane_count: lower rank wins
        a = cand("a", lane_count=1, rank=50, options=[{"q1"}])
        b = cand("b", lane_count=1, rank=10, options=[{"q1"}])
        assigned, _, _ = rf.plan({"q1"}, [a, b], 1000)
        self.assertEqual([c["id"] for c, _ in assigned], ["b"])
        # equal rank: grant beats dryrun regardless of list order
        a = cand("a", kind="dryrun", lane_count=1, rank=10, options=[{"q1"}])
        b = cand("b", kind="grant", lane_count=1, rank=10, options=[{"q1"}])
        for order in ([a, b], [b, a]):
            assigned, _, _ = rf.plan({"q1"}, order, 1000)
            self.assertEqual([c["id"] for c, _ in assigned], ["b"], order)
        # RAM: a row that would eat the margin stays pending with a RAM reason
        big = cand("big", gib=500, options=[{"q1"}])
        assigned, idle, pending = rf.plan({"q1"}, [big], 500)
        self.assertEqual(assigned, [])
        self.assertIn("RAM", idle["q1"])
        # bench + GPU grant open: q3 is withheld, with the reason
        bench = cand("t", bench=True, options=[{"q3"}])
        assigned, idle, _ = rf.plan({"q3"}, [bench], 1000, gpu_grant_open=True)
        self.assertEqual(assigned, [])
        self.assertIn("q3", idle["q3"])
        assigned, _, _ = rf.plan({"q3"}, [bench], 1000, gpu_grant_open=False)
        self.assertEqual(len(assigned), 1)


class Incident20261101(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="allocator-test-")
        self.flags = os.path.join(self.root, "compute-flags")
        os.makedirs(os.path.join(self.flags, "grants"))
        os.makedirs(os.path.join(self.flags, "dryrun"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def gpu_launcher(self, name, flags_line):
        d = os.path.join(self.root, name)
        write(os.path.join(d, "launch.sh"), textwrap.dedent(f"""\
            #!/bin/bash
            set -euo pipefail
            D={d}
            ENGINE={os.path.join(_RF, "filler_run15.sh")}
            exec bash "$ENGINE" --id x {flags_line} --min-window 600 --stop "$D/STOP" \\
              --complete-cmd true --workdir "$D" --cmd true
            """), 0o755)
        return os.path.join(d, "launch.sh")

    def test_df2_arm_time_pin_two_rows_distinct_quarters(self):
        """DF2 arm-time pin: an any-cpu-quarter grant and an any-quarter dry run on free={q0,q2} land on DISTINCT quarters."""
        any_q = [{q} for q in rf.QUARTERS]
        g = cand("df2-grant", kind="grant", rank=100, lane_count=2, options=any_q)
        dr = cand("df2-dryrun", kind="dryrun", rank=10, lane_count=2, options=any_q)
        assigned, idle, pending = rf.plan({"q0", "q2"}, [g, dr], 1000)
        self.assertEqual(sorted(c["id"] for c, _ in assigned), ["df2-dryrun", "df2-grant"])
        got = [o for _, o in assigned]
        self.assertEqual(len(got[0]), 1); self.assertEqual(len(got[1]), 1)
        self.assertNotEqual(got[0], got[1], "the same quarter was handed to both rows")
        self.assertEqual(got[0] | got[1], {"q0", "q2"})
        self.assertEqual(idle, {})
        self.assertEqual(pending, [])

    def test_whole_host_dry_run_on_one_quarter(self):
        d = {"regions": "0-95", "launcher": {"path": os.path.join(self.root, "does-not-exist.sh")}}
        opts, bench = rf.row_shape(d)
        self.assertEqual(opts, [frozenset(Q)])
        self.assertFalse(bench)
        dopts, one_q = rf.dryrun_shape(d, opts)
        self.assertTrue(one_q)
        self.assertEqual(sorted(sorted(o) for o in dopts), [["q0"], ["q1"], ["q2"], ["q3"]])
        d2 = dict(d, dryrun_whole_host=True)
        self.assertEqual(rf.dryrun_shape(d2, opts), (opts, False))
        self.assertEqual(rf.grant_regions(d, frozenset({"q2"}), True), "48-71")
        self.assertEqual(rf.grant_regions(d, frozenset(Q), False), "0-95")
        self.assertEqual(rf.grant_regions({"regions": "any-cpu-quarter"}, frozenset({"q1"}), False), "24-47")
        # GPU exclusive row claiming the whole host: dry-run shape is GPU + q3 only
        lp = self.gpu_launcher("gpu-excl", "--class gpu --gpu-quiet exclusive --claim-cpus 0-95")
        gd = {"regions": "mi210_0,184-191", "launcher": {"path": lp}}
        opts, bench = rf.row_shape(gd)
        self.assertEqual(opts, [frozenset({rf.GPU} | Q)])
        self.assertTrue(bench)
        dopts, one_q = rf.dryrun_shape(gd, opts)
        self.assertEqual(dopts, [frozenset({rf.GPU, "q3"})])
        self.assertTrue(one_q)
        self.assertEqual(rf.grant_regions(gd, dopts[0], one_q), "mi210_0,184-191")

    def test_gpu_parser_flag_qual_interpreter(self):
        lp = self.gpu_launcher("gpu-qi", "--class gpu --qual-interpreter python3 --requires-tool /usr/bin/python3")
        o = rf.parse_launcher(lp)
        self.assertEqual(o["class"], "gpu")
        self.assertEqual(o["id"], "x")
        lp2 = self.gpu_launcher("gpu-nofold", "--class gpu --no-fold-siblings --qual-interpreter python3")
        o2 = rf.parse_launcher(lp2)
        self.assertTrue(o2["nofold"])
        opts, _ = rf.row_shape({"regions": "mi210_0,184-191", "launcher": {"path": lp2}})
        self.assertEqual(opts, [frozenset({rf.GPU})], "q3 must stay usable for correctness rows")

    def test_fetch_only_row_held_a_quarter_underused(self):
        cpus = list(range(48, 72)) + list(range(144, 168))
        log, seen = [], set()
        s0 = {c: (0, 0) for c in cpus}
        self.assertEqual(rf.underused(self.flags, {"q2": "fetch-row"}, log.append, seen, sample=s0, now=1000), [])
        s1 = {c: (1000, 100000) for c in cpus}
        out = rf.underused(self.flags, {"q2": "fetch-row"}, log.append, seen, sample=s1, now=1700)
        self.assertEqual(len(out), 1)
        r, rid, pct = out[0]
        self.assertEqual((r, rid), ("q2", "fetch-row"))
        self.assertAlmostEqual(pct, 1.0, places=6)
        self.assertTrue(any("UNDERUSED q2 fetch-row" in l for l in log), log)
        self.assertIn("underused:q2:fetch-row", seen)
        fp = os.path.join(self.flags, "dryrun", "fetch-row", "UNDERUSED.json")
        self.assertTrue(os.path.exists(fp))
        rec = json.load(open(fp))
        self.assertIn("fix_task", rec)
        self.assertEqual(rec["region"], "q2")
        # a new holder on the same quarter restarts the history: 50 % busy, but no 10-minute span yet -> nothing
        s2 = {c: (50000, 200000) for c in cpus}
        self.assertEqual(rf.underused(self.flags, {"q2": "fetch-row-2"}, log.append, seen, sample=s2, now=1800), [])
        self.assertFalse(os.path.exists(os.path.join(self.flags, "dryrun", "fetch-row-2", "UNDERUSED.json")))
        # writes stayed inside the allowed paths
        written = set()
        for base, _, files in os.walk(self.flags):
            for f in files:
                written.add(os.path.relpath(os.path.join(base, f), self.flags))
        self.assertEqual(written, {"ws58-keeper-state/allocator/usage.json", "dryrun/fetch-row/UNDERUSED.json"})

    def test_heal_grants(self):
        G = os.path.join(self.flags, "grants")
        log, seen = [], set()
        # x: dead poller, no .ended -> stale
        write(os.path.join(G, "x.grant"), "regions=0-23 start=2026-11-01T00:00Z end=2026-11-01T02:00Z holds=q0\n")
        rf.atomic_json(os.path.join(self.flags, "dryrun", "x", "ARMED.json"), {"pid": 999999999})
        kept = rf.heal_grants(self.flags, rf.open_grants(self.flags), {}, log.append, seen)
        self.assertEqual(kept, [])
        self.assertFalse(os.path.exists(os.path.join(G, "x.grant")))
        stale = [p for p in os.listdir(G) if p.startswith("stale-")]
        self.assertEqual(len(stale), 1)
        self.assertTrue(os.path.exists(os.path.join(G, stale[0], "x.grant")))
        self.assertTrue(any("HEAL stale-grant x" in l for l in log), log)
        self.assertIn("stale-grant:x", seen)
        # y: alive, not started, region held by another job -> conflict, grant withdrawn
        write(os.path.join(G, "y.grant"), "regions=24-47 start=2026-11-01T00:00Z end=2026-11-01T02:00Z holds=q1\n")
        rf.atomic_json(os.path.join(self.flags, "dryrun", "y", "ARMED.json"), {"pid": os.getpid()})
        kept = rf.heal_grants(self.flags, rf.open_grants(self.flags), {"q1": ("HELD", "filler-other")}, log.append, seen)
        self.assertEqual(kept, [])
        self.assertFalse(os.path.exists(os.path.join(G, "y.grant")))
        self.assertTrue(any("HEAL conflict y" in l for l in log), log)
        # z: alive, STARTed on a quarter another job holds -> kept, logged CONFLICT, not killed
        write(os.path.join(G, "z.grant"), "regions=48-71 start=2026-11-01T00:00Z end=2026-11-01T02:00Z holds=q2\n")
        rf.atomic_json(os.path.join(self.flags, "dryrun", "z", "ARMED.json"), {"pid": os.getpid()})
        time.sleep(0.05)
        write(os.path.join(self.flags, "dryrun", "z", "poller.out"), "launcher up pid=1\nSTART regions=48-71\n")
        grants = rf.open_grants(self.flags)
        self.assertEqual([g["id"] for g in grants], ["z"])
        self.assertTrue(grants[0]["started"])
        self.assertEqual(grants[0]["holds"], {"q2"})
        kept = rf.heal_grants(self.flags, grants, {"q2": ("HELD", "filler-other")}, log.append, seen)
        self.assertEqual([g["id"] for g in kept], ["z"])
        self.assertTrue(os.path.exists(os.path.join(G, "z.grant")))
        self.assertTrue(any(l.startswith("CONFLICT z") for l in log), log)
        self.assertFalse(any("HEAL conflict z" in l for l in log))
        # a grant onto a region held by its OWN filler tag is not a conflict
        log2 = []
        kept = rf.heal_grants(self.flags, rf.open_grants(self.flags), {"q2": ("HELD", "filler-z")}, log2.append, set())
        self.assertEqual([g["id"] for g in kept], ["z"])
        self.assertEqual(log2, [])

    def test_open_grants_derives_holds_for_old_grants(self):
        G = os.path.join(self.flags, "grants")
        write(os.path.join(G, "old.grant"), "regions=mi210_0,184-191 start=2026-11-01T00:00Z end=2026-11-01T02:00Z\n")
        g = rf.open_grants(self.flags)[0]
        self.assertEqual(g["holds"], {rf.GPU})
        self.assertIsNone(g["pid"])
        self.assertFalse(g["dryrun"])

    def test_quarters_of(self):
        self.assertEqual(rf.quarters_of("184-191"), set())
        self.assertEqual(rf.quarters_of("184-191", fold=True), {"q3"})
        self.assertEqual(rf.quarters_of("0-95"), Q)
        self.assertEqual(rf.quarters_of("q1,q2"), {"q1", "q2"})
        self.assertEqual(rf.quarters_of("mi210_0"), set())
        self.assertEqual(rf.quarters_of("mi210_0,184-191"), set())
        self.assertEqual(rf.quarters_of("48-71"), {"q2"})
        self.assertEqual(rf.quarters_of("0-47,96-143"), {"q0", "q1"})
        self.assertEqual(rf.quarters_of(""), set())
        self.assertEqual(rf.cpu_list("q2"), "48-71")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class AdmitImport(unittest.TestCase):
    def test_admit_imports_the_parser_under_isolated_python(self):
        """22:33Z 2026-11-01: `python3 -I` does not add the script dir to sys.path; admit() must still reach grant_ok_launcher."""
        import subprocess, tempfile, textwrap
        rf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow", "rowflow.py")
        code = textwrap.dedent(f"""
            import importlib.util, sys
            spec = importlib.util.spec_from_file_location("rowflow_iso", {rf_path!r}); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            ok, line = m.admit({tempfile.gettempdir()!r}, "no-such-row", {{}}, 1, "0-23", 600)
            print("OK" if (ok is False and line.startswith("refuse")) else "BAD " + repr((ok, line)))
        """)
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.stdout.strip(), "OK", r.stdout + r.stderr)
