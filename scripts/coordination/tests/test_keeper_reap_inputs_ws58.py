"""Operator 2026-11-03 (session review 3.1): the keeper's reap-after-filing never deletes a file the job did not write.

2026-11-02 the reaper deleted a packet's inputs/ and helper/*.json and the job died 9 s after its grant. Rule now: a file
whose mtime is before the group's first recorded job start (grants/<id>.ended `started=`; the manifest's published_at only
when no start is recorded) is INPUT, kept in place whatever the keep globs say; keep globs + result_path only add
protection; with neither time recorded nothing is deleted.

The reaper heredoc runs end to end against a temp tree: its path constants are rewritten to the temp dir and guarded_rm.sh
is replaced by a recorder that deletes nothing, so the test sees exactly what the live pass would hand to guarded_rm."""
import datetime as dt
import json
import os
import re
import subprocess
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
KEEPER = os.path.join(os.path.dirname(HERE), "rowflow", "ws58-calendar-keeper-v13.sh")
DAY = 86400


def heredoc():
    s = open(KEEPER).read()
    return s.split("<<'PY'", 1)[1].split("\n", 1)[1].split("\nPY\n")[0]


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ReapInputs(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        td = self.td = self._td.name
        self.tmp = os.path.join(td, "a", "b") + "/"          # depth: valid_root wants <tmp>/<job> at path index 5
        self.flags = os.path.join(td, "flags") + "/"
        self.root = os.path.join(self.tmp, "job")
        for d in ("grants", "ready", "filing-done", "state/reap"):
            os.makedirs(self.flags + d)
        open(self.flags + "FILLERS.md", "w").write("# none\n")
        self.hdir = os.path.join(td, "handoffs")
        os.makedirs(self.hdir)
        open(os.path.join(self.hdir, "x.md"), "w").write("nothing cites the job dir\n")
        self.calls = os.path.join(td, "guarded_rm.calls")
        self.fake_rm = os.path.join(td, "fake_guarded_rm.sh")
        open(self.fake_rm, "w").write('#!/bin/bash\nprintf "%s\\n" "$@" >> ' + self.calls + '\necho "recorded $# paths"\n')
        self.now = int(time.time())

    def tearDown(self):
        self._td.cleanup()

    def put(self, rel, age_d, body="x"):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(body)
        return p, self.now - age_d * DAY

    def packet(self, keep, published_d=2.5, started_d=2.0, rid="job-r1"):
        files = [self.put("launch.sh", 3), self.put("inputs/data.bin", 3), self.put("helper/cfg.json", 2.2),
                 self.put("out/RESULT.json", 1.8, "{}"), self.put("out/big.tmp", 1.8), self.put("work/x.tmp", 1.8),
                 self.put("mixed/old.txt", 3), self.put("mixed/new.tmp", 1.8)]
        for p, t in files:
            os.utime(p, (t, t))
        for dp, dn, fn in os.walk(self.root):             # dirs last: creating files bumped their mtimes
            os.utime(dp, (self.now - 1.8 * DAY,) * 2)
        man = {"id": rid, "scratch_root": self.root, "keep": keep, "result_path": os.path.join(self.root, "out/RESULT.json")}
        if published_d is not None:
            man["published_at"] = iso(self.now - published_d * DAY)
        json.dump(man, open(self.flags + "ready/%s.json" % rid, "w"))
        ended = "rc=0 time=%s reason=complete\n" % iso(self.now - 1.5 * DAY)
        if started_d is not None:
            ended += "job_id=%s\nstarted=%s\n" % (rid, iso(self.now - started_d * DAY))
        for p, body in ((self.flags + "grants/%s.ended" % rid, ended), (self.flags + "filing-done/%s.FILED" % rid, "filed\n")):
            open(p, "w").write(body)
            os.utime(p, (self.now - 1.5 * DAY,) * 2)

    def run_reaper(self):
        src = heredoc()
        subs = [(r"^F = '[^']+'; G = F \+ 'grants/'; R = F \+ 'ready/'; TMP = '[^']+'$",
                 "F = %r; G = F + 'grants/'; R = F + 'ready/'; TMP = %r" % (self.flags, self.tmp)),
                (r"^VAULT = '[^']+'; TRASH = '[^']+'$",
                 "VAULT = %r; TRASH = %r" % (os.path.join(self.td, "vault") + "/", os.path.join(self.td, "trash-absent"))),
                (r"^    HDIR = .*$", "    HDIR = %r" % self.hdir),
                (r"'/[^'\s]*/guarded_rm\.sh'", repr(self.fake_rm))]
        for pat, rep in subs:
            src, n = re.subn(pat, lambda _m, r=rep: r, src, flags=re.M)
            self.assertEqual(n, 1, pat)
        env = dict(os.environ, REAP_MODE="live", REAP_LEGACY="0", REAP_DAYS="1", REAP_MAX_GIB="50", REAP_MAX_DIRS="200",
                   REAP_IDLE="0", REAP_IDLE_DAYS="1", REAP_STATE=self.flags + "state/reap/", REAP_REPORT="0")
        r = subprocess.run(["python3", "-I", "-"], input=src, capture_output=True, text=True, env=env, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        handed = sorted(os.path.relpath(x, self.root) for x in open(self.calls).read().split()) if os.path.exists(self.calls) else []
        return r.stdout, handed

    def test_inputs_before_first_job_start_are_never_handed_to_guarded_rm(self):
        self.packet(keep=[])                               # empty keep = inputs + result (no lint narrowing any more)
        out, handed = self.run_reaper()
        self.assertEqual(handed, ["mixed/new.tmp", "out/big.tmp", "work"], out)   # only what the job wrote
        self.assertIn("inputs kept=", out)
        self.assertIn("first job start", out)

    def test_keep_globs_only_add_protection(self):
        self.packet(keep=["out/*.tmp"])
        out, handed = self.run_reaper()
        self.assertEqual(handed, ["mixed/new.tmp", "work"], out)

    def test_publish_time_is_the_cutoff_only_when_no_start_is_recorded(self):
        self.packet(keep=[], published_d=2.5, started_d=None)
        out, handed = self.run_reaper()
        # helper/cfg.json (2.2 d) postdates the publish (2.5 d): with no recorded job start it counts as job-written, so the
        # whole helper/ dir (no input left in it) goes
        self.assertEqual(handed, ["helper", "mixed/new.tmp", "out/big.tmp", "work"], out)
        self.assertIn("publish time", out)

    def test_no_recorded_start_or_publish_time_falls_back_to_manifest_mtime(self):
        # v13 lifecycle patch (operator 2026-11-07): the manifest's mtime is a conservative cutoff, so a row that recorded
        # neither started= nor published_at no longer sits INPUT-ONLY forever; files older than the manifest stay inputs.
        self.packet(keep=[], published_d=None, started_d=None)
        out, handed = self.run_reaper()
        self.assertEqual(handed, [], out)              # every fixture file predates the just-written manifest
        self.assertIn("manifest mtime", out)
        self.assertIn("inputs kept=", out)

if __name__ == "__main__":
    unittest.main()
