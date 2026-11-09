"""ws58 2026-11-02 (operator: four disk fixes): keeper v12 reaper at 24 h, `.ended`+`.FILED` terminal, --reap-now mode,
git dirs reapable only when provably landed (git_reapable), and the disk janitor wiring. Static + extracted-function tests:
nothing here runs the reaper against the live tree."""
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CO = os.path.dirname(HERE)
KEEPER = os.path.join(CO, "rowflow", "ws58-calendar-keeper-v13.sh")
JANITOR = os.path.join(CO, "churn", "disk_janitor.sh")
CHURN_UP = os.path.join(CO, "churn", "churn_up.sh")


def heredoc():
    s = open(KEEPER).read()
    return s.split("<<'PY'", 1)[1].split("\n", 1)[1].split("\nPY\n")[0]


def git_reapable():
    src = heredoc()
    body = re.search(r"^def git_reapable\(p\):\n(?:(?:    .*|)\n)+", src, re.M).group(0)
    ns = {}
    exec("import os, subprocess\ndef _raise(e): raise e\n" + body, ns)
    return ns["git_reapable"]


def g(cwd, *a):
    return subprocess.run(["git", "-C", cwd, "-c", "user.email=t@t", "-c", "user.name=t", *a],
                          capture_output=True, text=True, check=True).stdout


class KeeperStatic(unittest.TestCase):
    def test_defaults_and_modes(self):
        s = open(KEEPER).read()
        self.assertIn("REAP_IDLE_DAYS=${REAP_IDLE_DAYS:-1}", s)
        self.assertIn("E.get('REAP_IDLE_DAYS', '1')", s)
        self.assertIn('if not os.path.isfile(c): c = G + rid + ".ended"', s)
        self.assertIn("--reap-now) REAPONLY=reap; REAP_LEGACY=1;;", s)
        self.assertIn('if [ -n "$REAPONLY" ]; then reap_filed; echo "reap-now pass done"; exit 0; fi', s)
        compile(heredoc(), "keeper-heredoc", "exec")
        for f in (KEEPER, JANITOR, CHURN_UP):
            self.assertEqual(subprocess.run(["bash", "-n", f]).returncode, 0, f)

    def test_tick_only_allocates_reaping_is_the_janitors(self):
        # operator 2026-11-03 (session review 3.1): a ~100 s reap pass inside the tick blocked granting
        s = open(KEEPER).read()
        tick = re.search(r"^tick\(\) \{ (.*) \}$", s, re.M).group(1)
        self.assertEqual(tick, 'if [ -n "$REAPONLY" ]; then reap_filed; return 0; fi; allocate_tick;')
        loop = s.split('while [ "$(date -u +%s)" -lt "$STOP_AT" ]; do', 1)[1].split("\ndone\n", 1)[0]
        self.assertNotIn("reap_filed", loop)
        self.assertNotIn("REAP_EVERY_S", s)
        self.assertIn('bash "$KEEPER" --reap-now', open(JANITOR).read())

    def test_janitor_cadence_and_churn_up_stop_leaves_it(self):
        j = open(JANITOR).read()
        self.assertIn("JANITOR_REAP_EVERY_S:-1800", j)
        self.assertIn("JANITOR_SWEEP_EVERY_S:-3600", j)
        self.assertIn("--reap-now", j)
        self.assertIn("/mnt/raid0/llm/.trash /mnt/raid0/llm/.trash-reap", j)
        self.assertIn("disk-janitor.log", j)
        self.assertNotRegex(j, r"\brm\s+-")  # the janitor itself deletes nothing
        c = open(CHURN_UP).read()
        stop = c.split("do_stop() {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("janitor", stop)
        self.assertIn("--janitor=start|--janitor=stop|--janitor=status|--janitor=dry-run", c)

    def test_janitor_dry_run_touches_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            trash = os.path.join(td, "trash")
            os.makedirs(os.path.join(trash, "20200101-000000-old"))
            keeper = os.path.join(td, "keeper.sh")
            open(keeper, "w").write('echo "REAP-WOULD x: $1"\n')
            env = dict(os.environ, JANITOR_FLAGS=td, JANITOR_KEEPER=keeper, JANITOR_TRASHES=trash + " " + os.path.join(td, "absent"),
                       JANITOR_SWEEP=os.path.join(CO, "..", "safety", "trash-sweep.sh"), JANITOR_DISK=td)
            r = subprocess.run(["bash", JANITOR, "--dry-run"], capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("REAP REAP-WOULD x: --reap-dry-run", r.stdout)
            self.assertIn("entries=1", r.stdout)
            self.assertIn("SWEEP-SKIP", r.stdout)
            self.assertTrue(os.path.isdir(os.path.join(trash, "20200101-000000-old")))
            self.assertFalse(os.path.exists(os.path.join(td, "disk-janitor.log")))


class GitReapable(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.bare = os.path.join(self.td, "origin.git")
        seed = os.path.join(self.td, "seed")
        subprocess.run(["git", "init", "-q", "-b", "main", seed], check=True)
        open(os.path.join(seed, "a.txt"), "w").write("a\n")
        g(seed, "add", "a.txt")
        g(seed, "commit", "-q", "-m", "s")
        subprocess.run(["git", "init", "-q", "-b", "main", "--bare", self.bare], check=True)
        g(seed, "remote", "add", "origin", self.bare)
        g(seed, "push", "-q", "origin", "main")
        g(seed, "fetch", "-q", "origin")
        self.seed = seed
        self.f = git_reapable()

    def test_clean_landed_clone_and_worktree_are_reapable(self):
        scratch = os.path.join(self.td, "scratch")
        os.makedirs(scratch)
        g(self.td, "clone", "-q", self.bare, os.path.join(scratch, "clone"))
        g(self.seed, "worktree", "add", "-q", "--detach", os.path.join(scratch, "wt"), "origin/main")
        ok, why = self.f(scratch)
        self.assertTrue(ok, why)

    def test_unlanded_dirty_or_unregistered_is_kept(self):
        wt = os.path.join(self.td, "s1", "wt")
        g(self.seed, "worktree", "add", "-q", "--detach", wt, "origin/main")
        open(os.path.join(wt, "a.txt"), "a").write("x\n")
        self.assertFalse(self.f(os.path.dirname(wt))[0])           # dirty
        g(wt, "commit", "-q", "-am", "local")
        ok, why = self.f(os.path.dirname(wt))
        self.assertFalse(ok)
        self.assertIn("not in origin/main", why)                   # unlanded commit
        cp = os.path.join(self.td, "s2", "copy")
        os.makedirs(cp)
        open(os.path.join(cp, ".git"), "w").write("gitdir: %s/.git/worktrees/nope\n" % self.seed)
        self.assertFalse(self.f(os.path.dirname(cp))[0])           # copied .git file, not registered
        wt2 = os.path.join(self.td, "s3", "wt")
        g(self.seed, "worktree", "add", "-q", "--detach", wt2, "origin/main")
        g(self.seed, "worktree", "lock", wt2)
        self.assertIn("locked", self.f(os.path.dirname(wt2))[1])  # locked worktree
        empty = os.path.join(self.td, "s4")
        os.makedirs(empty)
        self.assertFalse(self.f(empty)[0])                         # no .git at all: not this rule's business


class JanitorQuietHostSkip(unittest.TestCase):
    """The scheduled reap stays off a live quiet-host grant unless disk is under the floor."""

    def run_reap(self, grant, floor, arg=""):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "grants"))
            os.makedirs(os.path.join(td, "ws58-keeper-state"))
            if grant:
                with open(os.path.join(td, "grants", "r1.grant"), "w") as f:
                    f.write(grant + "\n")
            keeper = os.path.join(td, "keeper.sh")
            with open(keeper, "w") as f:
                f.write("echo KEEPER-RAN\n")
            j = open(JANITOR).read()
            funcs = "".join(re.search(r"^%s\(\) \{.*?^\}\n" % n, j, re.S | re.M).group(0) for n in ("quiet_host_grant", "reap"))
            sh = ('set -euo pipefail; MODE=loop; F=%s; KEEPER=%s; STAMP=%s/none; DISK=%s; REAP_EVERY_S=1800; LOG=/dev/stdout; '
                  'REAP_DISK_FLOOR_GIB=%d; log() { echo "$*"; }\n%s\nreap %s\n' % (td, keeper, td, td, floor, funcs, arg))
            r = subprocess.run(["bash", "-c", sh], capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout

    QUIET = "regions=0-95 start=2026-01-01T00:00Z end=2099-01-01T00:00Z holds=gpu-quiet,q0,q1,q2,q3 id=r1"

    def test_skips_during_quiet_host(self):
        out = self.run_reap(self.QUIET, 0)
        self.assertIn("REAP-SKIP quiet-host grant r1", out)
        self.assertNotIn("KEEPER-RAN", out)

    def test_disk_floor_overrides(self):
        out = self.run_reap(self.QUIET, 10 ** 9)
        self.assertIn("REAP-OVERRIDE", out)
        self.assertIn("KEEPER-RAN", out)

    def test_force_still_reaps(self):
        self.assertIn("KEEPER-RAN", self.run_reap(self.QUIET, 0, "force"))

    def test_quarter_grant_does_not_skip(self):
        g = self.QUIET.replace("gpu-quiet,q0,q1,q2,q3", "q0,q1")
        self.assertIn("KEEPER-RAN", self.run_reap(g, 0))

    def test_expired_grant_does_not_skip(self):
        g = self.QUIET.replace("2099", "2020")
        self.assertIn("KEEPER-RAN", self.run_reap(g, 0))


if __name__ == "__main__":
    unittest.main()
