"""Tests for scripts/safety worktree_reaper / pending_refs / build_ttl / trash_reap_tick (operator 2026-11-21 disk guards).
Real temp git repos with a local bare 'origin'; never touches live repos or compute-flags."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAFETY = os.path.join(ROOT, "scripts", "safety")
sys.path.insert(0, os.path.join(ROOT, "scripts", "system"))
sys.path.insert(0, SAFETY)
import pending_refs  # noqa: E402
import unregistered_worktrees as uw  # noqa: E402
import build_ttl  # noqa: E402

spec = importlib.util.spec_from_file_location("safety_worktree_reaper", os.path.join(SAFETY, "worktree_reaper.py"))
wr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = wr
spec.loader.exec_module(wr)

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def sh(*a, cwd=None):
    r = subprocess.run(list(a), cwd=cwd, env=ENV, capture_output=True, text=True)
    assert r.returncode == 0, (a, r.stderr)
    return r.stdout


def age(path, hours):
    t = time.time() - hours * 3600
    for dp, dns, fns in os.walk(path):
        for n in dns + fns:
            try:
                os.utime(os.path.join(dp, n), (t, t), follow_symlinks=False)
            except OSError:
                pass
    os.utime(path, (t, t))


class Fx(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="dg-")
        self.flags = os.path.join(self.d, "flags")
        for s in ("ready", "parked", "held", "filing-done", "grants"):
            os.makedirs(os.path.join(self.flags, s))
        self.origin = os.path.join(self.d, "origin.git")
        self.repo = os.path.join(self.d, "repo")
        sh("git", "init", "-q", "--bare", "-b", "main", self.origin)
        sh("git", "clone", "-q", self.origin, self.repo)
        open(os.path.join(self.repo, "a.txt"), "w").write("a\n")
        sh("git", "add", ".", cwd=self.repo)
        sh("git", "commit", "-qm", "init", cwd=self.repo)
        sh("git", "push", "-q", "origin", "HEAD:main", cwd=self.repo)
        sh("git", "fetch", "-q", "origin", cwd=self.repo)
        sh("git", "remote", "set-head", "origin", "main", cwd=self.repo)
        self.wtroot = os.path.join(self.d, "wts")
        os.makedirs(self.wtroot)
        self.handoffs = os.path.join(self.d, "handoffs")
        os.makedirs(self.handoffs)
        self.noscripts = os.path.join(self.d, "scripts")
        os.makedirs(self.noscripts)

    def idx(self):
        return pending_refs.PendingIndex(flags=self.flags, handoff_dirs=[self.handoffs], script_roots=[self.noscripts])

    def wt(self, name, branch=None, merged=True, idle_h=48):
        p = os.path.join(self.wtroot, name)
        br = branch or name
        sh("git", "worktree", "add", "-q", "-b", br, p, "origin/main", cwd=self.repo)
        if not merged:
            open(os.path.join(p, "n.txt"), "w").write(name)
            sh("git", "add", ".", cwd=p)
            sh("git", "commit", "-qm", "wip", cwd=p)
        age(p, idle_h)
        gd = sh("git", "rev-parse", "--git-dir", cwd=p).strip()
        age(os.path.join(p, gd) if not os.path.isabs(gd) else gd, idle_h)
        return p

    def run_reaper(self, **kw):
        return wr.run([self.repo], protect=kw.pop("protect", []), pending=kw.pop("pending", self.idx()), log=lambda s: None, **kw)

    def verdicts(self, recs):
        return {os.path.basename(r["path"]): r["verdict"] for r in recs}


class TestReaper(Fx):
    def test_dry_run_default_removes_nothing(self):
        p = self.wt("clean1")
        v = self.verdicts(self.run_reaper())
        self.assertEqual(v["clean1"], "REAP")
        self.assertTrue(os.path.isdir(p))

    def test_apply_removes_clean_merged_idle_and_branch(self):
        p = self.wt("clean2")
        recs = self.run_reaper(apply=True)
        self.assertFalse(os.path.exists(p))
        self.assertIn("+branch-d", recs[0]["result"])
        self.assertNotIn("clean2", sh("git", "branch", cwd=self.repo))

    def test_dirty_incl_untracked_kept(self):
        p = self.wt("dirty1")
        open(os.path.join(p, "untracked.txt"), "w").write("x")
        age(p, 48)
        self.assertEqual(self.verdicts(self.run_reaper(apply=True))["dirty1"], "DIRTY")
        self.assertTrue(os.path.isdir(p))

    def test_unpushed_commit_kept(self):
        self.wt("wip1", merged=False)
        self.assertEqual(self.verdicts(self.run_reaper())["wip1"], "UNLANDED")

    def test_branch_on_origin_no_unpushed_is_landed(self):
        p = self.wt("pushed1", merged=False)
        sh("git", "push", "-q", "origin", "pushed1", cwd=p)
        sh("git", "fetch", "-q", "origin", cwd=self.repo)
        age(p, 48)
        self.assertEqual(self.verdicts(self.run_reaper())["pushed1"], "REAP")

    def test_recent_kept_and_min_idle_flag(self):
        self.wt("fresh1", idle_h=2)
        self.assertEqual(self.verdicts(self.run_reaper())["fresh1"], "RECENT")
        self.assertEqual(self.verdicts(self.run_reaper(min_idle_h=1))["fresh1"], "REAP")

    def test_future_mtime_reported_never_trusted(self):
        p = self.wt("skew1")
        t = time.time() + 86400 * 365
        os.utime(os.path.join(p, "a.txt"), (t, t))
        recs = self.run_reaper(apply=True)
        self.assertEqual(self.verdicts(recs)["skew1"], "SKEW")
        self.assertTrue(os.path.isdir(p))

    def test_live_cwd_blocks(self):
        p = self.wt("busy1")
        fake = os.path.join(self.d, "proc", "4242")
        os.makedirs(fake)
        os.symlink(p, os.path.join(fake, "cwd"))
        self.assertEqual(self.verdicts(self.run_reaper(proc_root=os.path.join(self.d, "proc")))["busy1"], "BUSY")

    def test_protected_prefix_keep_list_and_locked(self):
        a = self.wt("mainsx")
        b = self.wt("keepme")
        c = self.wt("lockme")
        sh("git", "worktree", "lock", c, cwd=self.repo)
        v = self.verdicts(self.run_reaper(protect=[a], keep={os.path.realpath(b)}))
        self.assertEqual((v["mainsx"], v["keepme"], v["lockme"]), ("PROTECTED",) * 3)

    def test_only_list_scopes(self):
        a = self.wt("in1")
        self.wt("out1")
        v = self.verdicts(self.run_reaper(only={os.path.realpath(a)}))
        self.assertEqual(set(v), {"in1"})

    def test_missing_reported_not_pruned(self):
        p = self.wt("gone1")
        subprocess.run(["rm", "-rf", p])
        self.assertEqual(self.verdicts(self.run_reaper(apply=True))["gone1"], "MISSING")
        self.assertIn("gone1", sh("git", "worktree", "list", cwd=self.repo))


class TestPending(Fx):
    def test_row_spec_path_branch_and_hold_box_protect(self):
        a, b, c = self.wt("rowref1"), self.wt("boxref1", branch="feature/held-lane-x"), self.wt("free1")
        open(os.path.join(self.flags, "parked", "r.json"), "w").write('{"launcher": "%s/run.sh"}' % a)
        open(os.path.join(self.handoffs, "h.md"), "w").write("- [ ] E5 Stage-B waits on reboot: branch feature/held-lane-x\n")
        v = self.verdicts(self.run_reaper(apply=True))
        self.assertEqual((v["rowref1"], v["boxref1"], v["free1"]), ("PENDING", "PENDING", "REAP"))
        self.assertTrue(os.path.isdir(a) and os.path.isdir(b) and not os.path.exists(c))

    def test_ticked_box_is_history_but_ticked_hold_line_counts(self):
        open(os.path.join(self.handoffs, "h.md"), "w").write("- [x] done with /x/y/distinct-name-123\n- [x] parked /x/y/other-name-456\n")
        i = self.idx()
        self.assertIsNone(i.check("/x/y/distinct-name-123"))
        self.assertIn("handoff(hold)", i.check("/x/y/other-name-456"))

    def test_unfiled_row_id_protects_matching_worktree_name(self):
        open(os.path.join(self.flags, "ready", "myrow-20261121.json"), "w").write("{}")
        self.assertIn("unfiled-row", self.idx().check("/w/ak-myrow-20261121-tree"))
        open(os.path.join(self.flags, "filing-done", "myrow-20261121.FILED"), "w").write("x")
        self.assertIsNone(self.idx().check("/w/ak-myrow-20261121-tree"))

    def test_filed_ready_spec_and_generic_basename_do_not_protect(self):
        open(os.path.join(self.flags, "ready", "old-row-1.json"), "w").write('{"p": "/w/oldtree-99/source"}')
        open(os.path.join(self.flags, "filing-done", "old-row-1.FILED"), "w").write("x")
        self.assertIsNone(self.idx().check("/w/oldtree-99/source"))
        open(os.path.join(self.flags, "parked", "p.json"), "w").write('{"x": "source app tree"}')
        self.assertIsNone(self.idx().check("/other/source"))

    def test_withdrawn_spec_protects_like_pending_even_when_filed(self):
        os.makedirs(os.path.join(self.flags, "ready", "withdrawn"))
        open(os.path.join(self.flags, "ready", "withdrawn", "wd-row-1.json"), "w").write('{"launcher": "/k/builds/gpu-20261001-abcdef123-c9w/bin/x"}')
        open(os.path.join(self.flags, "filing-done", "wd-row-1.FILED"), "w").write("WITHDRAWN")
        r = self.idx().check("/k/builds/gpu-20261001-abcdef123-c9w")
        self.assertIn("withdrawn", r)

    def test_launcher_script_names_path(self):
        open(os.path.join(self.noscripts, "prearm.sh"), "w").write("cd /mnt/x/post-reboot-wt-77\n")
        self.assertIn("script:", self.idx().check("/mnt/x/post-reboot-wt-77"))


class TestBuildTtl(Fx):
    def mk(self, store, name, days=30, lines=None):
        p = os.path.join(store, "builds", name)
        os.makedirs(os.path.join(p, "bin"))
        open(os.path.join(p, "bin", "llama-server"), "w").write("x")
        age(p, days * 24)
        return p

    def test_plan_keeps_every_exclusion(self):
        st = os.path.join(self.d, "kernels")
        for s in ("production", "archive", "candidates"):
            os.makedirs(os.path.join(st, s))
        prod = self.mk(st, "gpu-20260921-ffc1bac82")
        os.symlink(prod + "/bin", os.path.join(st, "production", "gpu"))
        anchor = self.mk(st, "cpu-20260810-0db32c06e")
        os.symlink(anchor, os.path.join(st, "archive", "cpu-anchor"))
        self.mk(st, "gpu-20261101-aaaaaaaaa-c8fold1")      # older c8 -> reapable
        self.mk(st, "gpu-20261105-bbbbbbbbb-c8fold2")      # newest c8 -> lineage head
        self.mk(st, "gpu-20261102-ccccccccc-champ")        # champion tip sha
        self.mk(st, "gpu-20261103-ddddddddd-grantx-r1")    # lineage grantx head ...
        self.mk(st, "gpu-20261001-eeeeeeeee-c9a")         # named by an open grant
        self.mk(st, "gpu-20261001-fffffffff-c9b")        # named by a held handoff box
        self.mk(st, "gpu-20261001-111111111-c9d")         # truly stale -> REAP
        self.mk(st, "gpu-20261110-444444444-c9head")       # newest c9 -> lineage head of the c9 family
        self.mk(st, "gpu-20261120-222222222-newone-r1", days=1)
        self.mk(st, "gpu-20261121-555555555-newone-r2", days=0.2)  # younger than TTL
        open(os.path.join(self.flags, "grants", "g.grant"), "w").write("regions=q0 build=gpu-20261001-eeeeeeeee-c9a\n")
        open(os.path.join(self.handoffs, "h.md"), "w").write("- [ ] held post-reboot: gpu-20261001-fffffffff-c9b\n")
        recs = {r["build"]: r["verdict"] for r in build_ttl.plan(
            st, flags=self.flags, champions={"ccccccccc"}, pending=self.idx(), refs=[], commit_refs=[],
            probe=None, open_paths=set(), open_ok=False)}
        self.assertEqual(recs["gpu-20261101-aaaaaaaaa-c8fold1"], "KEEP-UNVERIFIABLE")  # blind /proc fails closed
        recs = {r["build"]: r["verdict"] for r in build_ttl.plan(
            st, flags=self.flags, champions={"ccccccccc"}, pending=self.idx(), refs=[], commit_refs=[],
            probe=_NoProbe(), open_paths=set(), open_ok=True)}
        self.assertTrue(recs["gpu-20260921-ffc1bac82"].startswith("KEEP"))
        self.assertTrue(recs["cpu-20260810-0db32c06e"].startswith("KEEP"))
        self.assertEqual(recs["gpu-20261101-aaaaaaaaa-c8fold1"], "REAP")
        self.assertEqual(recs["gpu-20261105-bbbbbbbbb-c8fold2"], "KEEP-LINEAGE-HEAD")
        self.assertEqual(recs["gpu-20261102-ccccccccc-champ"], "KEEP-CHAMPION")
        self.assertEqual(recs["gpu-20261001-eeeeeeeee-c9a"], "KEEP-OPEN-GRANT")
        self.assertEqual(recs["gpu-20261001-fffffffff-c9b"], "KEEP-PENDING")
        self.assertEqual(recs["gpu-20261001-111111111-c9d"], "REAP")
        self.assertEqual(recs["gpu-20261120-222222222-newone-r1"], "KEEP-RECENT")

    def test_lineage_key(self):
        self.assertEqual(build_ttl.lineage_key("gpu-20261108-1bda248e3-c8rbseq"), ("gpu", "c8"))
        self.assertEqual(build_ttl.lineage_key("gpu-20261121-090d6c304-rs-replay-r2"), ("gpu", "rs-replay"))


class _NoProbe:
    def busy(self, path):
        return None


class TestUnregistered(Fx):
    def test_classes(self):
        root = os.path.join(self.d, "u")
        os.makedirs(root)
        now = time.time()
        pend = self.idx()
        # orphan standalone clone, clean + pushed
        c = os.path.join(root, "clone1")
        sh("git", "clone", "-q", self.origin, c)
        age(c, 48)
        # plain copy equal to origin content
        pl = os.path.join(root, "plain-same")
        os.makedirs(pl)
        open(os.path.join(pl, "a.txt"), "w").write("a\n")
        age(pl, 48)
        pu = os.path.join(root, "plain-other")
        os.makedirs(pu)
        open(os.path.join(pu, "z.txt"), "w").write("zz\n")
        age(pu, 48)
        pp = os.path.join(root, "pend-thing-12")
        os.makedirs(pp)
        age(pp, 48)
        open(os.path.join(self.flags, "held", "h.json"), "w").write('{"w":"%s"}' % pp)
        blobs = uw.origin_blobs([self.repo])
        k = lambda p: uw.classify(p, registered=set(), pending=self.idx(), now=now, min_idle_s=86400, blobs=blobs, root=root)[0]
        self.assertEqual(k(c), "ORPHAN-GIT-CLEAN-PUSHED")
        self.assertEqual(k(pl), "PLAIN-MATCHES-PUSHED")
        self.assertEqual(k(pu), "UNKNOWN")
        self.assertEqual(k(pp), "PENDING")
        open(os.path.join(c, "new.txt"), "w").write("x")
        age(c, 48)
        self.assertEqual(k(c), "GIT-DIRTY")


class TestTrashTick(unittest.TestCase):
    def test_older_than_hours_sweeps_only_aged(self):
        d = tempfile.mkdtemp(prefix="tr-")
        trash = os.path.join(d, ".trash")
        os.makedirs(os.path.join(trash, "20200101-000000-old"))
        new = time.strftime("%Y%m%d-%H%M%S")
        os.makedirs(os.path.join(trash, new + "-fresh"))
        env = dict(os.environ, TRASH_ROOT=trash, SAFETY_AUDIT_LOG=os.path.join(d, "audit.log"))
        r = subprocess.run(["bash", os.path.join(SAFETY, "trash_reap_tick.sh")], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(os.listdir(trash), [new + "-fresh"])
        r = subprocess.run(["bash", os.path.join(SAFETY, "trash-sweep.sh"), "--older-than", "0h"], env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
