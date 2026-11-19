#!/usr/bin/env python3
"""Tests for automatic filing (operator 2026-11-07 "Approve all"): commit receipts, supersede-on-rerun, janitor auto-link,
rowflow alerts --ack, SUPERSEDED/WITHDRAWN verdicts + named answers, filing-due alerts, shared-scratch reclaim guard,
idempotency/atomicity. Temp dirs and a temp git origin only; never touches live compute-flags.
Run: python3 -W ignore -m unittest scripts.coordination.tests.test_churn_filing
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

_COORD = Path(__file__).resolve().parents[1]
for p in (str(_COORD), str(_COORD / "churn"), str(_COORD / "rowflow")):
    if p not in sys.path:
        sys.path.insert(0, p)

import file_result as fr  # noqa: E402
import filing  # noqa: E402
import reclaim_row  # noqa: E402
import scratch_guard  # noqa: E402
import notify  # noqa: E402
import rowflow  # noqa: E402
import auto_file  # noqa: E402

ENV = dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def sh(cwd, *a):
    return subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True, env=dict(os.environ, **ENV)).stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.flags = os.path.join(self.root, "flags")
        for d in ("ready/armed", "ready/.withdrawn", "grants", "filing-done"):
            os.makedirs(os.path.join(self.flags, d))
        self._env = patch.dict(os.environ, {"RECLAIM_TMP_ROOT": os.path.dirname(self.root)})
        self._env.start()
        scratch_guard.TMP_ROOT = os.path.dirname(self.root)
        self.reclaims = []
        self._rc = patch.object(reclaim_row, "main", lambda argv: self.reclaims.append(list(argv)) or 0)
        self._rc.start()

    def tearDown(self):
        self._rc.stop(); self._env.stop(); self.tmp.cleanup()

    def row(self, rid, *, ended=True, rc=0, where="ready", published="2026-11-06T00:00:00Z", **extra):
        m = {"schema": "epyc.row.v3", "id": rid, "owner": "main-x", "published_at": published, "scratch_root": os.path.join(self.root, "s-" + rid),
             "decision_rule": "prose rule", "result_path": os.path.join(self.root, "s-" + rid, "RESULT.json"), "result_format": "json",
             "handoff_task": "handoffs/active/h.md:BOX-1"}
        m.update(extra)
        d = os.path.join(self.flags, "ready", where) if where != "ready" else os.path.join(self.flags, "ready")
        Path(d, rid + ".json").write_text(json.dumps(m))
        if ended:
            Path(self.flags, "grants", rid + ".ended").write_text(f"rc={rc} reason=complete\n")
        return m

    def filed(self, rid):
        return os.path.exists(os.path.join(self.flags, "filing-done", rid + ".FILED"))

    def read_filed(self, rid):
        return Path(self.flags, "filing-done", rid + ".FILED").read_text()

    def verdict(self, rid):
        return json.loads(Path(self.flags, "filing-done", rid + ".verdict.json").read_text())


class Git(Base):
    def setUp(self):
        super().setUp()
        self.origin = os.path.join(self.root, "origin.git")
        self.repo = os.path.join(self.root, "repo")
        sh(self.root, "git", "init", "-q", "--bare", "-b", "main", self.origin)
        sh(self.root, "git", "clone", "-q", self.origin, self.repo)
        sh(self.repo, "git", "checkout", "-q", "-B", "main")
        os.makedirs(os.path.join(self.repo, "handoffs/active"))
        self.h = os.path.join(self.repo, "handoffs/active/h.md")
        Path(self.h).write_text("# H\n\n- [ ] **BOX-1** lineage-a work\n- [ ] **BOX-2** other\n")
        sh(self.repo, "git", "add", "-A"); sh(self.repo, "git", "commit", "-qm", "init"); sh(self.repo, "git", "push", "-q", "origin", "main")

    def commit(self, text, *, push=True, msg="verdict"):
        Path(self.h).write_text(text)
        sh(self.repo, "git", "commit", "-qam", msg)
        sha = sh(self.repo, "git", "rev-parse", "HEAD")
        if push:
            sh(self.repo, "git", "push", "-q", "origin", "main")
        return sha


class TestReceipt(Git):
    def test_receipt_files_quotes_box_line_and_reclaims(self):
        self.row("lineage-a-r1")
        sha = self.commit("# H\n\n- [x] **BOX-1** lineage-a work: lineage-a-r1 KEEP +3.1%\n- [ ] **BOX-2** other\n")
        code, msg = filing.file_receipt(self.flags, "lineage-a-r1", f"{sha}:handoffs/active/h.md#BOX-1", repo=self.repo, verdict="pass", answer="SURFACE_E2E_OK")
        self.assertEqual(code, 0, msg)
        self.assertTrue(self.filed("lineage-a-r1"))
        self.assertIn("lineage-a-r1 KEEP +3.1%", self.read_filed("lineage-a-r1"))
        v = self.verdict("lineage-a-r1")
        self.assertEqual(v["answer"], "SURFACE_E2E_OK")
        self.assertEqual(v["receipt"]["commit"], sha)
        self.assertEqual(self.reclaims, [["lineage-a-r1", "--flags", self.flags, "--apply", "--pre-filed"]])

    def test_lineage_mention_is_enough(self):
        self.row("lineage-a-r2")
        sha = self.commit("# H\n\n- [x] **BOX-1** lineage-a-r1 done\n- [ ] **BOX-2** other\n")
        self.assertEqual(filing.file_receipt(self.flags, "lineage-a-r2", f"{sha}:h.md#BOX-1", repo=self.repo)[0], 0)

    def test_negative_wrong_commit_unpushed(self):
        self.row("lineage-a-r1")
        sha = self.commit("# H\n\n- [x] **BOX-1** lineage-a-r1 done\n- [ ] **BOX-2** other\n", push=False)
        code, msg = filing.file_receipt(self.flags, "lineage-a-r1", f"{sha}:h.md#BOX-1", repo=self.repo)
        self.assertEqual(code, 2); self.assertIn("not on origin/main", msg); self.assertFalse(self.filed("lineage-a-r1"))
        self.assertEqual(self.reclaims, [])

    def test_negative_unknown_commit_and_malformed(self):
        self.row("lineage-a-r1")
        self.assertEqual(filing.file_receipt(self.flags, "lineage-a-r1", "deadbeefdead:h.md#BOX-1", repo=self.repo)[0], 2)
        self.assertEqual(filing.file_receipt(self.flags, "lineage-a-r1", "nonsense", repo=self.repo)[0], 2)

    def test_negative_commit_does_not_touch_box(self):
        self.row("lineage-a-r1")
        sha = self.commit("# H\n\n- [ ] **BOX-1** lineage-a work\n- [x] **BOX-2** other lineage-a-r1 done\n")
        code, msg = filing.file_receipt(self.flags, "lineage-a-r1", f"{sha}:h.md#BOX-1", repo=self.repo)
        self.assertEqual(code, 2); self.assertIn("does not touch box BOX-1", msg)

    def test_negative_different_lineage(self):
        self.row("lineage-b-r1", handoff_task="handoffs/active/h.md:BOX-1")
        sha = self.commit("# H\n\n- [x] **BOX-1** lineage-a-r1 done\n- [ ] **BOX-2** other\n")
        code, msg = filing.file_receipt(self.flags, "lineage-b-r1", f"{sha}:h.md#BOX-1", repo=self.repo)
        self.assertEqual(code, 2); self.assertIn("mentions neither", msg); self.assertFalse(self.filed("lineage-b-r1"))

    def test_negative_prefix_ids_do_not_match(self):
        self.row("lineage-a-r1")
        sha = self.commit("# H\n\n- [x] **BOX-1** lineage-a-r10 done\n- [ ] **BOX-2** other\n")
        self.assertEqual(filing.file_receipt(self.flags, "lineage-a-r1", f"{sha}:h.md#BOX-1", repo=self.repo)[0], 0)  # lineage mention
        self.row("zzz-r1", handoff_task="handoffs/active/h.md:BOX-1")
        self.assertEqual(filing.file_receipt(self.flags, "zzz-r1", f"{sha}:h.md#BOX-1", repo=self.repo)[0], 2)

    def test_already_filed_is_noop_and_not_overwritten(self):
        self.row("lineage-a-r1")
        Path(self.flags, "filing-done", "lineage-a-r1.FILED").write_text("FILED original\n")
        sha = self.commit("# H\n\n- [x] **BOX-1** lineage-a-r1 done\n- [ ] **BOX-2** other\n")
        self.assertEqual(filing.file_receipt(self.flags, "lineage-a-r1", f"{sha}:h.md#BOX-1", repo=self.repo)[0], 1)
        self.assertEqual(self.read_filed("lineage-a-r1"), "FILED original\n")
        self.assertEqual(self.reclaims, [])

    def test_cli_receipt_exit_codes(self):
        self.row("lineage-a-r1")
        sha = self.commit("# H\n\n- [x] **BOX-1** lineage-a-r1 done\n- [ ] **BOX-2** other\n")
        base = ["lineage-a-r1", "--flags", self.flags, "--repo", self.repo, "--no-reclaim"]
        with redirect_stderr(io.StringIO()):
            self.assertEqual(fr.main(base + ["--receipt", "deadbeefdead:h.md#BOX-1"]), 8)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(fr.main(base + ["--receipt", f"{sha}:h.md#BOX-1", "--verdict", "pass"]), 0)
            self.assertEqual(fr.main(base + ["--receipt", f"{sha}:h.md#BOX-1"]), 0)  # NOOP


class TestScope(Git):
    """CHURN-CONT-SCOPE: a receipt commit's changed paths must stay inside the row's declared (or default) scope."""

    def commit_files(self, files, *, links=None, gitlink=False):
        for rel, txt in files.items():
            p = Path(self.repo, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt)
        for rel, target in (links or {}).items():
            p = Path(self.repo, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, p)
        Path(self.h).write_text("# H\n\n- [x] **BOX-1** lineage-a-r1 done\n- [ ] **BOX-2** other\n")
        sh(self.repo, "git", "add", "-A")
        if gitlink:
            sh(self.repo, "git", "update-index", "--add", "--cacheinfo", "160000," + "a" * 40 + ",sub/mod")
        sh(self.repo, "git", "commit", "-qm", "verdict")
        sh(self.repo, "git", "push", "-q", "origin", "main")
        return sh(self.repo, "git", "rev-parse", "HEAD")

    def receipt(self, sha, rid="lineage-a-r1"):
        return filing.file_receipt(self.flags, rid, f"{sha}:h.md#BOX-1", repo=self.repo, verdict="pass")

    def test_default_scope_handoff_only_passes(self):
        self.row("lineage-a-r1")
        self.assertEqual(self.receipt(self.commit_files({}))[0], 0)

    def test_default_scope_includes_row_output_dir_inside_repo(self):
        self.row("lineage-a-r1", scratch_root=os.path.join(self.repo, "out"))
        self.assertEqual(self.receipt(self.commit_files({"out/res.json": "{}"}))[0], 0)

    def test_default_scope_refuses_other_path(self):
        self.row("lineage-a-r1", scratch_root=os.path.join(self.repo, "out"))
        code, msg = self.receipt(self.commit_files({"scripts/evil.py": "x"}))
        self.assertEqual(code, 2)
        self.assertIn("scripts/evil.py", msg)
        self.assertIn("outside scope", msg)
        self.assertFalse(self.filed("lineage-a-r1"))

    def test_declared_scope_inside_passes(self):
        self.row("lineage-a-r1", scope=["docs/x/**", "notes/*.md"])
        self.assertEqual(self.receipt(self.commit_files({"docs/x/a/b.md": "1", "notes/n.md": "2"}))[0], 0)

    def test_declared_scope_outside_refused(self):
        self.row("lineage-a-r1", scope=["docs/x/**"])
        code, msg = self.receipt(self.commit_files({"docs/y.md": "3"}))
        self.assertEqual(code, 2)
        self.assertIn("docs/y.md", msg)

    def test_symlink_escape_refused(self):
        self.row("lineage-a-r1", scope=["docs/**"])
        code, msg = self.receipt(self.commit_files({}, links={"docs/link": "../scripts/secret"}))
        self.assertEqual(code, 2)
        self.assertIn("escapes scope", msg)

    def test_symlink_inside_scope_passes(self):
        self.row("lineage-a-r1", scope=["docs/**"])
        self.assertEqual(self.receipt(self.commit_files({"docs/real.md": "r"}, links={"docs/ok": "real.md"}))[0], 0)

    def test_gitlink_refused(self):
        self.row("lineage-a-r1", scope=["sub/**"])
        code, msg = self.receipt(self.commit_files({}, gitlink=True))
        self.assertEqual(code, 2)
        self.assertIn("gitlink", msg)

    def test_traversal_never_matches_scope(self):
        self.assertFalse(filing._in_scope("../docs/a", ["docs/**"]))
        self.assertTrue(filing._in_scope("docs/a/b", ["docs/**"]))

    def test_cli_scope_refusal_exit_8(self):
        self.row("lineage-a-r1", scope=["docs/**"])
        sha = self.commit_files({"scripts/evil.py": "x"})
        with redirect_stderr(io.StringIO()) as out:
            code = fr.main(["lineage-a-r1", "--flags", self.flags, "--repo", self.repo, "--no-reclaim", "--receipt", f"{sha}:h.md#BOX-1"])
        self.assertEqual(code, 8)
        self.assertIn("REFUSED", out.getvalue())
        self.assertIn("scope", out.getvalue())


class TestAtomic(Base):
    def test_concurrent_writers_exactly_one_wins(self):
        self.row("r-1")
        wins = []
        def go(i):
            wins.append(filing.write_filed(self.flags, "r-1", f"FILED r-1 by {i}", {"who": i}))
        ts = [threading.Thread(target=go, args=(i,)) for i in range(12)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(sum(wins), 1)
        self.assertEqual(self.verdict("r-1")["who"], int(self.read_filed("r-1").split("by ")[1]))
        left = [f for f in os.listdir(os.path.join(self.flags, "filing-done")) if f.startswith(".") or f.endswith((".tmp", ".claim"))]
        self.assertEqual(left, [])

    def test_already_filed_noop(self):
        self.assertTrue(filing.write_filed(self.flags, "r-1", "FILED a", {"a": 1}))
        self.assertFalse(filing.write_filed(self.flags, "r-1", "FILED b", {"a": 2}))
        self.assertEqual(self.read_filed("r-1"), "FILED a\n")


class TestSupersede(Base):
    def test_publish_supersedes_earlier_unfiled_and_reclaims(self):
        self.row("lin-r1", published="2026-11-06T01:00:00Z"); self.row("lin-r2", published="2026-11-06T02:00:00Z")
        self.row("lin-r3", ended=False, published="2026-11-06T03:00:00Z")
        self.row("other-r1")                              # different lineage: untouched
        self.row("done-r1"); self.row("done-r2", ended=False)
        Path(self.flags, "filing-done", "done-r1.FILED").write_text("FILED real\n")
        rep = filing.supersede_lineage(self.flags, "lin-r3")
        self.assertEqual(sorted(rep["superseded"]), ["lin-r1", "lin-r2"])
        self.assertIn("SUPERSEDED-BY lin-r3", self.read_filed("lin-r1"))
        self.assertEqual(self.verdict("lin-r2")["superseded_by"], "lin-r3")
        self.assertFalse(self.filed("other-r1")); self.assertFalse(self.filed("lin-r3"))
        self.assertEqual(self.read_filed("done-r1"), "FILED real\n")
        self.assertEqual(sorted(r[0] for r in self.reclaims), ["lin-r1", "lin-r2"])
        again = filing.supersede_lineage(self.flags, "lin-r3")
        self.assertEqual(again["superseded"], [])           # idempotent

    def test_complete_predecessor_kept_unless_named(self):
        self.row("c-r1", published="2026-11-06T01:00:00Z"); self.row("c-r2", ended=False, published="2026-11-06T02:00:00Z")
        Path(self.flags, "grants", "c-r1.complete").write_text("done\n")
        rep = filing.supersede_lineage(self.flags, "c-r2")
        self.assertEqual(rep["superseded"], []); self.assertEqual(rep["skipped"], ["c-r1"]); self.assertFalse(self.filed("c-r1"))
        self.row("c-r3", ended=False, published="2026-11-06T03:00:00Z", supersedes=["c-r1"])
        self.assertEqual(filing.supersede_lineage(self.flags, "c-r3")["superseded"], ["c-r1"])

    def test_withdrawn_filed_withdrawn(self):
        self.row("w-r1", where=".withdrawn", rc=75)
        rep = filing.supersede_lineage(self.flags, "w-r2")
        self.assertEqual(rep["withdrawn"], ["w-r1"])
        self.assertIn("WITHDRAWN", self.read_filed("w-r1"))

    def test_supersedes_field_with_free_text_and_parallel_arms(self):
        self.row("arm-r3-pca", published="2026-11-06T01:00:00Z"); self.row("arm-r3-dense", published="2026-11-06T01:00:00Z")
        self.row("arm-r4-pca", ended=False, supersedes="arm-r3-pca (widened to 2 quarters)")
        rep = filing.supersede_lineage(self.flags, None, log=lambda *_: None)
        self.assertEqual(rep["superseded"], ["arm-r3-pca"]); self.assertFalse(self.filed("arm-r3-dense"))  # parallel arm untouched

    def test_explicit_pairs_and_withdrawn_successor_never_supersedes(self):
        self.row("e-r1"); self.row("e-r2", where=".withdrawn", rc=75, published="2026-11-06T09:00:00Z")
        self.row("big-r7"); self.row("big-r8", ended=False)
        rep = filing.supersede_lineage(self.flags, None, explicit=[("big-r*", "big-r8")], log=lambda *_: None)
        self.assertIn("big-r7", rep["superseded"]); self.assertNotIn("e-r1", rep["superseded"])
        self.assertTrue(self.filed("e-r2"))   # the withdrawn attempt itself is filed WITHDRAWN

    def test_pinned_lineage_filed_without_reclaim(self):
        self.row("lsa-quality-r7"); self.row("lsa-quality-r8", ended=False)
        out = io.StringIO()
        with redirect_stdout(out):
            filing.supersede_lineage(self.flags, "lsa-quality-r8", no_reclaim_globs=["lsa-quality-*"], log=print)
        self.assertTrue(self.filed("lsa-quality-r7")); self.assertEqual(self.reclaims, [])
        self.assertIn("RECLAIM-SKIPPED-SHARED lsa-quality-r7", out.getvalue())

    def test_backfill_older_attempts_only(self):
        for i in (1, 2, 3):
            self.row(f"bf-r{i}", published=f"2026-11-06T0{i}:00:00Z")
        self.row("solo-r1")
        dry = filing.supersede_lineage(self.flags, None, dry_run=True, log=lambda *_: None)
        self.assertEqual(sorted(dry["superseded"]), ["bf-r1", "bf-r2"]); self.assertFalse(self.filed("bf-r1"))
        rep = filing.supersede_lineage(self.flags, None, log=lambda *_: None)
        self.assertEqual(sorted(rep["superseded"]), ["bf-r1", "bf-r2"])
        self.assertFalse(self.filed("bf-r3")); self.assertFalse(self.filed("solo-r1"))
        self.assertIn("SUPERSEDED-BY bf-r3", self.read_filed("bf-r1"))

    def test_publish_hook_never_raises(self):
        import publish_row
        with patch.object(filing, "supersede_lineage", side_effect=RuntimeError("boom")):
            with redirect_stdout(io.StringIO()):
                self.assertIsNone(publish_row.supersede_prior_attempts(self.flags, "x-r2"))


class TestTerminalVerdicts(Base):
    def test_cli_superseded_withdrawn_and_answer(self):
        self.row("t-r1"); self.row("t-r2")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(fr.main(["t-r1", "--flags", self.flags, "--verdict", "SUPERSEDED", "--superseded-by", "t-r2", "--answer", "SURFACE_E2E_OK"]), 0)
            vj = os.path.join(self.root, "v.json"); Path(vj).write_text(json.dumps({"verdict": "WITHDRAWN", "rationale": "never ran", "answer": "N/A"}))
            self.assertEqual(fr.main(["t-r2", "--flags", self.flags, "--verdict-json", vj]), 0)
            self.assertEqual(fr.main(["t-r2", "--flags", self.flags, "--verdict", "SUPERSEDED"]), 0)  # NOOP
        self.assertEqual(self.verdict("t-r1")["answer"], "SURFACE_E2E_OK")
        self.assertEqual(self.verdict("t-r2")["row_verdict"], "WITHDRAWN")
        self.assertIn("SUPERSEDED-BY t-r2", self.read_filed("t-r1"))

    def test_machine_verdict_stores_answer_and_is_atomic(self):
        self.row("m-r1", decision_rule="x >= 1")
        Path(self.root, "s-m-r1").mkdir(); Path(self.root, "s-m-r1", "RESULT.json").write_text('{"x": 2}')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(fr.main(["m-r1", "--flags", self.flags, "--answer", "SURFACE_E2E_OK", "--no-reclaim"]), 0)
            self.assertEqual(fr.main(["m-r1", "--flags", self.flags, "--no-reclaim"]), 0)
        self.assertIn("answer=SURFACE_E2E_OK", self.read_filed("m-r1"))


class TestAutolink(Git):
    def test_exactly_one_commit_files_ambiguous_listed(self):
        for r in ("lin-a-r1", "lin-b-r1", "lin-c-r1", "lin-d-r1"):
            self.row(r)
        os.utime(os.path.join(self.flags, "grants", "lin-a-r1.ended"), (1, 1))   # ended long ago: commits below are later
        for r in ("lin-a-r1", "lin-b-r1", "lin-c-r1", "lin-d-r1"):
            os.utime(os.path.join(self.flags, "grants", r + ".ended"), (1_700_000_000, 1_700_000_000))
        self.commit("# H\n\n- [x] **BOX-1** lin-a-r1 KEEP\n- [ ] **BOX-2** other\n")
        self.commit("# H\n\n- [x] **BOX-1** lin-a-r1 KEEP\n- [x] **BOX-2** lin-b-r1 X, lin-c-r1 Y\n")
        self.commit("# H\n\n- [x] **BOX-1** lin-a-r1 KEEP\n- [x] **BOX-2** lin-b-r1 X, lin-c-r1 Y (amended)\n")
        out = io.StringIO()
        rep = filing.autolink(self.flags, self.repo, apply=True, reclaim=False, log=lambda *_: None)
        # lin-a-r1 appears in the commit that ticked it once (later commits keep the line unchanged: no + line there? they do not)
        self.assertEqual(rep["filed"], ["lin-a-r1"] if self.filed("lin-a-r1") else rep["filed"])
        self.assertTrue(self.filed("lin-a-r1"))
        self.assertIn("lin-b-r1", rep["ambiguous"]); self.assertIn("lin-c-r1", rep["ambiguous"])
        self.assertFalse(self.filed("lin-b-r1")); self.assertFalse(self.filed("lin-c-r1"))
        self.assertFalse(self.filed("lin-d-r1")); self.assertEqual(rep["none"], 1)
        self.assertIn("auto_link", self.read_filed("lin-a-r1"))

    def test_unpushed_and_pre_end_commits_never_link(self):
        self.row("lin-e-r1"); self.row("lin-f-r1")
        os.utime(os.path.join(self.flags, "grants", "lin-e-r1.ended"), (1_700_000_000, 1_700_000_000))
        self.commit("# H\n\n- [x] **BOX-1** lin-e-r1 KEEP\n- [ ] **BOX-2** o\n", push=False)    # local only
        rep = filing.autolink(self.flags, self.repo, apply=True, reclaim=False, fetch=False, log=lambda *_: None)
        self.assertEqual(rep["filed"], []); self.assertFalse(self.filed("lin-e-r1"))
        # a pushed commit that PREDATES the row's end is not its verdict
        sh(self.repo, "git", "push", "-q", "origin", "main")
        os.utime(os.path.join(self.flags, "grants", "lin-e-r1.ended"), (4_000_000_000, 4_000_000_000))
        rep = filing.autolink(self.flags, self.repo, apply=True, reclaim=False, fetch=False, log=lambda *_: None)
        self.assertFalse(self.filed("lin-e-r1"))

    def test_already_filed_row_is_skipped_and_dry_run_writes_nothing(self):
        self.row("lin-g-r1"); self.row("lin-h-r1")
        for r in ("lin-g-r1", "lin-h-r1"):
            os.utime(os.path.join(self.flags, "grants", r + ".ended"), (1_700_000_000, 1_700_000_000))
        Path(self.flags, "filing-done", "lin-g-r1.FILED").write_text("FILED keep me\n")
        self.commit("# H\n\n- [x] **BOX-1** lin-g-r1 KEEP\n- [x] **BOX-2** lin-h-r1 KEEP\n")
        rep = filing.autolink(self.flags, self.repo, apply=False, log=lambda *_: None)
        self.assertEqual(rep["filed"], ["lin-h-r1"]); self.assertFalse(self.filed("lin-h-r1"))
        self.assertEqual(self.read_filed("lin-g-r1"), "FILED keep me\n")


class TestAlerts(Base):
    def alert(self, rid, key="k1"):
        rec = {"schema": "rowflow.inbox.v1", "key": key, "ts": "2026-11-07T00:00:00Z", "kind": "row-ended", "severity": "warning",
               "row_id": rid, "owner": "main-x", "summary": "s"}
        notify._append_line(notify.inbox_path(self.flags), rec)

    def test_ack_refused_for_unfiled_ended_row_until_forced(self):
        self.row("a-r1"); self.alert("a-r1")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(rowflow.main(["--flags", self.flags, "alerts", "--ack", "k1"]), 3)
        self.assertIn("not filing", out.getvalue()); self.assertNotIn("k1", notify.acked_keys(self.flags))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(rowflow.main(["--flags", self.flags, "alerts", "--ack", "k1", "--force-ack"]), 0)
        self.assertIn("k1", notify.acked_keys(self.flags))

    def test_ack_ok_when_filed_or_not_ended(self):
        self.row("b-r1"); self.alert("b-r1", "k2"); self.row("c-r1", ended=False); self.alert("c-r1", "k3")
        Path(self.flags, "filing-done", "b-r1.FILED").write_text("FILED\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(rowflow.main(["--flags", self.flags, "alerts", "--ack", "k2"]), 0)
            self.assertEqual(rowflow.main(["--flags", self.flags, "alerts", "--ack", "k3"]), 0)

    def test_ack_with_file_commit_goes_through_receipt_path(self):
        self.row("d-r1"); self.alert("d-r1", "k4")
        calls = []
        class R:
            returncode = 1; stdout = "REFUSED d-r1: commit not found"; stderr = ""
        def fake_run(cmd, **kw):
            calls.append(cmd); return R()
        with patch("subprocess.run", fake_run), redirect_stdout(io.StringIO()) as o:
            rc = rowflow.main(["--flags", self.flags, "alerts", "--ack", "k4", "--file", "pass", "--commit", "deadbeef1"])
        self.assertEqual(rc, 2); self.assertIn("--receipt", calls[0]); self.assertIn("deadbeef1:handoffs/active/h.md#BOX-1", calls[0])
        self.assertNotIn("k4", notify.acked_keys(self.flags))        # a refused receipt never acks

    def test_filing_due_one_alert_per_row_owner_in_inbox(self):
        self.row("e-r1")
        for _ in range(3):
            notify.filing_due(self.flags, "e-r1", "main-inf22", "rc=0 reason=complete")
        inbox = [r for r in notify.read_inbox(self.flags) if r["kind"] == "filing-due"]
        self.assertEqual(len(inbox), 1); self.assertEqual(inbox[0]["owner"], "main-inf22")
        self.assertEqual(len(notify.alerts_for(self.flags, slug="main-inf22")), 1)   # reaches the owner's dispatcher block
        notify.filing_due(self.flags, "e-r2", "main-inf22")
        self.assertEqual(len([r for r in notify.read_inbox(self.flags) if r["kind"] == "filing-due"]), 2)

    def test_auto_file_alerts_prose_rows_once_and_skips_filed(self):
        self.row("f-r1"); self.row("f-r2")
        Path(self.flags, "filing-done", "f-r2.FILED").write_text("FILED\n")
        due = [{"id": "f-r1"}, {"id": "f-r2"}]
        Path(self.flags, "filing-due.jsonl").write_text("".join(json.dumps(d) + "\n" for d in due))
        t = os.path.getmtime(os.path.join(self.flags, "grants", "f-r1.ended")) + 3600
        for _ in range(2):
            rep = auto_file.run_pass(self.flags, os.path.join(self.root, "bus"), now=t, min_age_s=1200)
        ids = [r["row_id"] for r in notify.read_inbox(self.flags) if r["kind"] == "filing-due"]
        self.assertEqual(ids, ["f-r1"])


class TestReclaimGuard(Base):
    def setUp(self):
        super().setUp()
        self._rc.stop()   # exercise the real reclaim_row (dry-run: nothing is deleted)

    def tearDown(self):
        self._rc.start(); super().tearDown()

    def shared_case(self, live_extra):
        d = os.path.join(self.root, "shared"); os.makedirs(d); Path(d, "big.bin").write_text("x")
        self.row("old-r1", scratch_root=d, raw=["*.bin"], result_path=os.path.join(d, "RESULT.json"))
        self.row("old-r2", ended=False, scratch_root=os.path.join(self.root, "elsewhere"), **live_extra(d))
        return d

    def run_reclaim(self, rid):
        out = io.StringIO()
        with redirect_stdout(out):
            code = reclaim_row.main([rid, "--flags", self.flags, "--pre-filed"])
        return code, out.getvalue()

    def test_negative_control_unshared_row_would_reap(self):
        d = os.path.join(self.root, "alone"); os.makedirs(d); Path(d, "big.bin").write_text("x")
        os.utime(os.path.join(d, "big.bin"), (4_000_000_000, 4_000_000_000))   # written by the job (after the start cutoff)
        self.row("solo-r1", scratch_root=d, raw=["*.bin"], result_path=os.path.join(d, "RESULT.json"))
        code, out = self.run_reclaim("solo-r1")
        self.assertEqual(code, 0); self.assertIn("verdict=REAP", out); self.assertNotIn("RECLAIM-SKIPPED-SHARED", out)

    def test_live_workdir_in_old_scratch_blocks_reclaim(self):   # old code compared scratch_root only and would reap here
        self.shared_case(lambda d: {"workdir": os.path.join(d, "sub")})
        code, out = self.run_reclaim("old-r1")
        self.assertIn("RECLAIM-SKIPPED-SHARED", out); self.assertNotIn("verdict=REAP", out)
        self.assertEqual(json.loads(Path(self.flags, "filing-done", "old-r1.reclaim.json").read_text())["state"], "SHARED")

    def test_live_result_path_and_workdir_arg_and_parent_child(self):
        d = self.shared_case(lambda d: {"result_path": os.path.join(d, "out", "r.json")})
        self.assertIn("RECLAIM-SKIPPED-SHARED", self.run_reclaim("old-r1")[1])
        Path(self.flags, "ready", "old-r2.json").unlink()
        self.row("old-r3", ended=False, scratch_root=os.path.join(self.root, "x"), launcher={"path": "/l.sh", "args": f"--workdir {d}/w --foo"})
        self.assertIn("RECLAIM-SKIPPED-SHARED", self.run_reclaim("old-r1")[1])
        Path(self.flags, "ready", "old-r3.json").unlink()
        self.row("old-r4", ended=False, scratch_root=self.root + "/shared/deeper")           # child of the old row's dir
        self.assertIn("RECLAIM-SKIPPED-SHARED", self.run_reclaim("old-r1")[1])
        Path(self.flags, "ready", "old-r4.json").unlink()
        self.row("old-r5", ended=False, scratch_root=self.root)                              # parent of it
        self.assertIn("RECLAIM-SKIPPED-SHARED", self.run_reclaim("old-r1")[1])

    def test_terminal_live_row_does_not_block_and_symlink_resolves(self):
        d = self.shared_case(lambda d: {"workdir": d})
        Path(self.flags, "grants", "old-r2.ended").write_text("rc=0\n")                      # now terminal: no longer live
        code, out = self.run_reclaim("old-r1")
        self.assertNotIn("RECLAIM-SKIPPED-SHARED", out)
        Path(self.flags, "grants", "old-r2.ended").unlink()
        link = os.path.join(self.root, "alias"); os.symlink(d, link)
        Path(self.flags, "ready", "old-r2.json").write_text(json.dumps({"id": "old-r2", "scratch_root": link}))
        self.assertIn("RECLAIM-SKIPPED-SHARED", self.run_reclaim("old-r1")[1])               # realpath, not string, comparison

    def test_pinned_glob_blocks_even_with_no_manifest_overlap(self):
        d = os.path.join(self.root, "c7"); os.makedirs(d); Path(d, "big.bin").write_text("x")
        self.row("c7-local-code28k-r1", scratch_root=d, raw=["*.bin"], result_path=os.path.join(d, "RESULT.json"))
        Path(self.flags, "filing-no-reclaim.globs").write_text("# pinned\nc7-local-*\n")
        code, out = self.run_reclaim("c7-local-code28k-r1")
        self.assertIn("RECLAIM-SKIPPED-SHARED", out); self.assertNotIn("verdict=REAP", out)


class TestScratchGuard(Base):
    def test_overlaps(self):
        a = os.path.join(self.root, "a"); os.makedirs(os.path.join(a, "b"))
        self.assertTrue(scratch_guard.overlaps(a, os.path.join(a, "b"))); self.assertTrue(scratch_guard.overlaps(os.path.join(a, "b"), a))
        self.assertFalse(scratch_guard.overlaps(a, a + "2"))

    def test_broad_result_dir_is_ignored(self):
        m = {"result_path": os.path.join(os.path.dirname(self.root), "loose.json")}
        self.assertEqual(scratch_guard.manifest_paths(m), [])


if __name__ == "__main__":
    unittest.main()
