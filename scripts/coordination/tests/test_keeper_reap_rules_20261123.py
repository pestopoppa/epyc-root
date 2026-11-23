"""Reaper rule fixes (pipeline-mgmt, operator 2026-11-23): future-mtime clamp, classified handoff pins, FILED / CANCELLED / stale-row
release, declared-inputs-only rule, partial vault, pressure window floor. Pure helpers are extracted from the keeper heredoc between
its REAP-RULES markers; the group pass runs end to end through the same temp-tree harness as test_keeper_reap_inputs_ws58 (guarded_rm
is a recorder). Nothing here touches the live tree."""
import glob
import json
import os
import re
import time
import types
import unittest

import test_keeper_reap_inputs_ws58 as inp

HERE = os.path.dirname(os.path.abspath(__file__))
KEEPER = inp.KEEPER
DAY = 86400
SYSDIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "system")


def helpers():
    src = open(KEEPER).read().split("<<'PY'", 1)[1]
    block = src.split("# <<REAP-RULES-BEGIN>>", 1)[1].split("# <<REAP-RULES-END>>", 1)[0]
    block = block.split("\n", 1)[1]
    ns = {"os": os, "re": re, "glob": glob, "time": time}
    exec(block, ns)
    return types.SimpleNamespace(**ns)


H = helpers()


def st(m, c):
    return types.SimpleNamespace(st_mtime=m, st_ctime=c)


class Etime(unittest.TestCase):
    def test_future_mtime_ages_by_ctime(self):
        now = 1_800_000_000.0
        far = now + 3 * 365 * DAY                              # a 2030 fixture stamp
        before = H.FUTURE["n"]
        self.assertEqual(H.etime(st(far, now - 5 * DAY), now), now - 5 * DAY)
        self.assertEqual(H.FUTURE["n"], before + 1)

    def test_normal_and_slightly_ahead_mtimes_are_untouched(self):
        now = 1_800_000_000.0
        self.assertEqual(H.etime(st(now - DAY, now), now), now - DAY)
        self.assertEqual(H.etime(st(now + 1800, now), now), now + 1800)   # within the 1 h slop

    def test_ctime_also_in_the_future_keeps_the_dir(self):
        now = 1_800_000_000.0
        far = now + 3 * 365 * DAY
        self.assertEqual(H.etime(st(far, far), now), now)     # fail closed: looks like activity right now


class Mentions(unittest.TestCase):
    ROOT = "/mnt/raid0/llm/tmp/job"
    PAT = re.compile(re.escape(ROOT) + r"(?![A-Za-z0-9_-])")

    def cls(self, text):
        return H.mention_class(text, self.PAT)

    def test_open_box_pins_ticked_box_and_prose_do_not(self):
        self.assertEqual(self.cls("- [ ] run on %s again\n" % self.ROOT), "pin")
        self.assertEqual(self.cls("- [x] result at %s\n" % self.ROOT), "cite")
        self.assertEqual(self.cls("The result is under %s.\n" % self.ROOT), "cite")
        self.assertIsNone(self.cls("nothing here\n"))

    def test_continuation_lines_inherit_their_box(self):
        self.assertEqual(self.cls("- [ ] box\n  evidence in %s\n" % self.ROOT), "pin")
        self.assertEqual(self.cls("- [x] box\n  evidence in %s\n" % self.ROOT), "cite")
        self.assertEqual(self.cls("- [ ] box\n\nplain paragraph %s\n" % self.ROOT), "cite")   # dedented: not the box's

    def test_waiting_wording_pins_and_lean_keep_is_hard(self):
        for w in ("on hold", "waiting for reboot", "awaiting the operator", "keep until Friday", "retained"):
            self.assertEqual(self.cls("- [x] %s: %s\n" % (w, self.ROOT)), "pin", w)
        self.assertEqual(self.cls("%s is KEEP: 4 good quants remain\n" % self.ROOT), "hard")
        self.assertEqual(self.cls("LEAN retention for %s\n" % self.ROOT), "hard")
        self.assertEqual(self.cls("keep: %s\n" % self.ROOT), "hard")

    def test_subpath_only_mention_is_not_a_root_mention_for_cited_pattern(self):
        pat = re.compile(re.escape(self.ROOT) + r"(/[^\s`|;,\)\]'\"<>]*)?")
        self.assertIsNone(H.mention_class("- [ ] see %s/out/RESULT.json\n" % self.ROOT, pat))
        self.assertEqual(H.mention_class("- [ ] see %s and %s/x\n" % (self.ROOT, self.ROOT), pat), "pin")

    def test_waiting_wording_within_two_lines_pins(self):
        near = "Run 23 started.\nanchor %s\nwe keep it until the champion lands\n" % self.ROOT
        self.assertEqual(self.cls(near), "pin")
        far = "we keep it\n\n\n\nx\nx\nanchor %s\nx\nx\nx\nx\n" % self.ROOT
        self.assertEqual(self.cls(far), "cite")

    def test_error_is_hard(self):
        self.assertEqual(H.mention_class("x", None), "hard")

    def test_filed_receipt_releases_pin_but_not_hard(self):
        self.assertTrue(H.handoff_blocks("pin", False))
        self.assertFalse(H.handoff_blocks("pin", True))
        self.assertTrue(H.handoff_blocks("hard", True))
        self.assertFalse(H.handoff_blocks("cite", False))
        self.assertFalse(H.handoff_blocks(None, False))

    def test_completed_and_progress_never_pin_regression(self):
        """Rule 3: the reaper reads only handoffs/active (+FILLERS); never widen HDIR to completed/archived/progress."""
        s = open(KEEPER).read()
        heredoc = s.split("<<'PY'", 1)[1]
        self.assertRegex(heredoc, r"HDIR = '/workspace/handoffs/active'")
        self.assertRegex(heredoc, r"HOFF = \{p: sread\(p\) for p in glob\.glob\(HDIR \+ '/\*\.md'\)\}")
        for bad in ("handoffs/completed", "handoffs/archived", "handoffs/blocked", "progress/"):
            self.assertNotIn(bad, heredoc)


class ReadyRowsAndFillers(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.F = self._td.name + "/"
        for d in ("filing-done", "closed-stale", "grants"):
            os.makedirs(self.F + d)
        self.now = time.time()

    def tearDown(self):
        self._td.cleanup()

    def touch(self, rel, age_h=0):
        p = self.F + rel
        open(p, "w").write("x")
        os.utime(p, (self.now - age_h * 3600,) * 2)

    def test_filed_ready_row_does_not_pin(self):
        self.assertTrue(H.ready_row_pins("r1", self.F, self.now))
        self.touch("filing-done/r1.FILED")
        self.assertFalse(H.ready_row_pins("r1", self.F, self.now))

    def test_closed_stale_marker_releases_only_after_48h_and_not_if_objected(self):
        self.touch("closed-stale/r2.CLOSED-STALE", 10)
        self.assertTrue(H.ready_row_pins("r2", self.F, self.now))
        self.touch("closed-stale/r3.CLOSED-STALE", 49)
        self.assertFalse(H.ready_row_pins("r3", self.F, self.now))
        self.touch("closed-stale/r3.KEEP")
        self.assertTrue(H.ready_row_pins("r3", self.F, self.now))

    def test_stale_candidate(self):
        man = self.F + "r4.json"
        open(man, "w").write("{}")
        G = self.F + "grants/"
        os.utime(man, (self.now - 15 * DAY,) * 2)
        self.assertTrue(H.stale_candidate("r4", man, self.F, G, self.now, 14))
        os.utime(man, (self.now - 13 * DAY,) * 2)
        self.assertFalse(H.stale_candidate("r4", man, self.F, G, self.now, 14))
        os.utime(man, (self.now - 15 * DAY,) * 2)
        self.touch("grants/r4.ended")                         # any grant record at all => not stale
        self.assertFalse(H.stale_candidate("r4", man, self.F, G, self.now, 14))

    def test_filler_statuses_that_release(self):
        for stt in ("COMPLETE", "DONE", "RETIRED", "CANCELLED", "SKIPPED", "WITHDRAWN"):
            self.assertTrue(H.FILL_DONE.match(stt), stt)
        for stt in ("RUNNING", "QUEUED", "PARKED", "READY", ""):
            self.assertFalse(H.FILL_DONE.match(stt), stt)

    def test_vault_subset_takes_evidence_then_smallest_up_to_cap(self):
        evid = re.compile("VERDICT")
        sized = [("/a/big.bin", 90), ("/a/VERDICT.json", 50), ("/a/s1.txt", 5), ("/a/s2.txt", 6)]
        chosen, left = H.vault_subset(sized, 70, evid)
        self.assertEqual(chosen, ["/a/VERDICT.json", "/a/s1.txt", "/a/s2.txt"])
        self.assertEqual(left, ["/a/big.bin"])
        self.assertEqual(H.vault_subset([("/a/x", 10)], 5, evid), ([], ["/a/x"]))

    def test_owner_name_is_sanitised(self):
        self.assertEqual(H.safe_owner("pipeline-mgmt"), "pipeline-mgmt")
        self.assertNotIn("/", H.safe_owner("../../etc/x y"))
        self.assertEqual(H.safe_owner(None), "unknown")
        self.assertEqual(H.safe_owner(".hidden"), "unknown")


class _Base(inp.ReapInputs):
    sysdir = SYSDIR


for _n in [n for n in dir(inp.ReapInputs) if n.startswith("test_")]:
    setattr(_Base, _n, None)                                   # run the harness, not the old-rule tests again


class GroupPass(_Base):
    def run_reaper(self):
        for f in glob.glob(self.flags + "state/reap/logged.json"):
            os.remove(f)                                       # REAP lines are logged once per (dir, verdict): reset between passes
        return super().run_reaper()

    def declare(self, inputs=("inputs",), rid="job-r1"):
        self.packet(keep=[], rid=rid)
        p = self.flags + "ready/%s.json" % rid
        m = json.load(open(p))
        m["scratch_inputs"] = [{"path": x} for x in inputs]
        json.dump(m, open(p, "w"))

    def test_only_manifest_declared_inputs_survive(self):
        self.declare()
        out, handed = self.run_reaper()
        # pre-start files that are NOT declared (launch.sh, helper/, mixed/) are now reclaimable; inputs/ and the result stay
        # (release_inputs, unchanged, frees a declared input it cannot re-derive through guarded_rm as soon as the row is released)
        self.assertEqual(handed, ["helper", "inputs", "launch.sh", "mixed", "out/big.tmp", "work"], out)
        self.assertIn("5 entries", out)
        self.assertIn("manifest-declared only", out)

    def test_old_mtime_rule_still_applies_when_declared_rule_is_unavailable(self):
        self.declare()
        self.sysdir = "/nonexistent"
        out, handed = self.run_reaper()
        self.assertEqual(handed, ["mixed/new.tmp", "out/big.tmp", "work"], out)

    def cite(self, line):
        open(os.path.join(self.hdir, "x.md"), "w").write(line % self.root + "\n")

    def test_filed_row_releases_open_box_pin_but_not_lean(self):
        self.declare()
        self.cite("- [ ] rerun in %s")
        out, handed = self.run_reaper()
        self.assertIn("5 entries", out)                        # FILED receipt exists: the open box no longer pins
        os.remove(self.calls)
        self.cite("LEAN retention: %s is kept")
        out, handed = self.run_reaper()
        self.assertEqual(handed, [], out)
        self.assertIn("handoff-live", out)

    def test_ready_row_pin_released_by_filing_and_cancelled_filler_row(self):
        self.declare()
        other = {"id": "other-r2", "launcher": {"path": os.path.join(self.root, "launch.sh")}}
        json.dump(other, open(self.flags + "ready/other-r2.json", "w"))
        out, handed = self.run_reaper()
        self.assertEqual(handed, [], out)                      # unfiled ready row names the root: pinned
        self.assertIn("ready-manifest:other-r2", out)
        open(self.flags + "filing-done/other-r2.FILED", "w").write("filed\n")
        out, handed = self.run_reaper()
        self.assertTrue(handed, out)                           # filed: no longer pins
        os.remove(self.calls)
        row = ["", "fill-9"] + [""] * 6 + ["CANCELLED"] + [""] * 10 + [" names %s " % self.root, ""]
        open(self.flags + "FILLERS.md", "w").write("|".join(row) + "\n")
        out, handed = self.run_reaper()
        self.assertTrue(handed, out)                           # CANCELLED row does not pin
        os.remove(self.calls)
        row[8] = "RUNNING"
        open(self.flags + "FILLERS.md", "w").write("|".join(row) + "\n")
        out, handed = self.run_reaper()
        self.assertEqual(handed, [], out)
        self.assertIn("FILLERS-live:fill-9", out)

    def test_matured_closed_stale_marker_drops_the_row_so_its_dir_is_released(self):
        self.declare(rid="job-r1")
        os.remove(self.flags + "filing-done/job-r1.FILED")     # never filed: the group would WAIT forever
        out, handed = self.run_reaper()
        self.assertIn("WAIT", out)
        if os.path.exists(self.calls):
            os.remove(self.calls)
        os.makedirs(self.flags + "closed-stale")
        mk = self.flags + "closed-stale/job-r1.CLOSED-STALE"
        open(mk, "w").write("{}")
        os.utime(mk, (self.now - 49 * 3600,) * 2)
        out, handed = self.run_reaper()
        self.assertNotIn("WAIT job-r1", out)
        self.assertEqual(handed, [], out)                      # dropped from groups; the idle pass (disabled here) owns the dir now

    def test_rule8_writes_marker_and_owner_log_only(self):
        self.declare(rid="stale-r9")
        m = self.flags + "ready/stale-r9.json"
        d = json.load(open(m))
        d["owner"] = "pipeline-mgmt"
        json.dump(d, open(m, "w"))
        for f in glob.glob(self.flags + "grants/stale-r9.*") + glob.glob(self.flags + "filing-done/stale-r9.*"):
            os.remove(f)
        os.utime(m, (self.now - 15 * DAY,) * 2)
        out, handed = self.run_reaper()
        self.assertIn("CLOSED-STALE stale-r9", out)
        self.assertTrue(os.path.exists(self.flags + "closed-stale/stale-r9.CLOSED-STALE"))
        self.assertIn("stale-r9", open(self.flags + "closed-stale/pipeline-mgmt.owner.log").read())
        self.assertTrue(os.path.exists(m))                     # the row itself is untouched
        self.assertEqual(handed, [])                           # released only 48 h later


class Static(unittest.TestCase):
    def test_pressure_floor_caps_and_sort(self):
        s = open(KEEPER).read()
        self.assertIn("REAP_MAX_GIB=${REAP_MAX_GIB_PRESSURE:-200}; REAP_MAX_DIRS=${REAP_MAX_DIRS_PRESSURE:-1000}", s)
        self.assertIn("REAP_PRESSURE=$REAP_PRESSURE REAP_IDLE=$REAP_IDLE", s)
        self.assertIn("IDLE_DAYS = max(IDLE_DAYS, float(E.get('REAP_IDLE_FLOOR_DAYS', '1')))", s)
        self.assertIn("return (-(size / 2**30) * max(0.0, (now - newest) / 86400), name)", s)


if __name__ == "__main__":
    unittest.main()
