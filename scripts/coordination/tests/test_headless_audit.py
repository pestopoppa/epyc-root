#!/usr/bin/env python3
"""Tests for headless_audit.py — the P2-7 auditor.

WHAT THESE PIN, AND WHY EACH ONE EARNS ITS PLACE.

The auditor's entire value is that it does NOT grade the worker's account of its
own work (R12; the F-01/F-02 instrument-error class). Every property below is a
property of that independence, and every one of them is invisible in the happy
path — an auditor that quietly reads the report instead of the diff produces
identical output on a run where the report happens to be true.

  1. THE MUTATION PROBE IS NOT VACUOUS. `MutationProbeAntiVacuityTests` runs the
     probe against a repo whose diff does NOT contain the change the task text
     named, and requires it to FAIL. It also runs the change-then-revert case,
     where the file is named in `git log --name-only` for the range but the net
     diff is empty — a log-based probe passes there; this one must not. And the
     revert half is exercised directly: a change whose post-image is not present
     in the tree fails `--reverse --check`.
  2. THE PACKET IS POINTERS ONLY. A packet carrying a claim-shaped key, or any
     key the auditor does not recognise, is refused as blocked-evidence rather
     than read. `PacketContractTests`.
  3. THE REPORT CANNOT RESCUE A BAD DIFF. `IndependenceTests` gives the worker a
     glowing, schema-valid report and a diff that does not do what was asked; the
     verdict must be needs-rework, and the model must not even be consulted.
  4. FAILURE IS NEVER "ACCEPT". Unresolvable range, missing report, model error,
     unparseable model output, off-enum verdict — all blocked-evidence.
     `FailClosedTests`.
  5. SINGLE WRITER. The verdict lands in the auditor's own outbox and nowhere
     else, checked against `required_writer`. `BusWriteTests`.

NO LIVE MODEL IS REQUIRED OR PERMITTED. Every test injects a stub client; a test
that could reach a real model would pass or fail on the weather. All git work
happens in temp repos created per-test — nothing here touches the live tree or
the live bus.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import headless_audit as ha  # noqa: E402
from scripts.coordination.session_bus import BusError  # noqa: E402

LIVE_BUS = REPO_ROOT / "coordination" / "session-bus"


# --------------------------------------------------------------- fixtures


def git(repo: Path, *args: str, stdin: str | None = None) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], input=stdin,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr or proc.stdout}")
    return proc.stdout


def make_repo(root: Path) -> Path:
    """A temp repo with one initial commit. Never the live tree."""
    root.mkdir(parents=True, exist_ok=True)
    git(root.parent, "init", "-q", "-b", "main", str(root))
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "test")
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "src" / "widget.py").write_text("def widget():\n    return None\n", encoding="utf-8")
    (root / "docs" / "notes.md").write_text("# notes\n", encoding="utf-8")
    git(root, "add", "--", "src/widget.py", "docs/notes.md")
    git(root, "commit", "-q", "-m", "initial")
    return root


def write_brief(path: Path, task_id: str, task_text: str) -> Path:
    path.write_text(json.dumps({
        "schema_version": "worker_brief.v1",
        "rows": [{"task_id": task_id, "task_text": task_text}],
    }), encoding="utf-8")
    return path


def write_report(path: Path, task_id: str, *, outcome: str = "pass",
                 commits: list[str] | None = None, artifacts: list[str] | None = None,
                 summary: str = "did the thing perfectly") -> Path:
    path.write_text(json.dumps({
        "schema_version": "worker_report.v1",
        "subagents_spawned": 3,
        "tokens_used": 1000,
        "denials": [],
        "rows": [{"task_id": task_id, "outcome": outcome,
                  "commits": commits or [], "artifacts": artifacts or [],
                  "summary": summary}],
    }), encoding="utf-8")
    return path


class StubClient:
    """A model that says whatever the test tells it to, and counts its calls."""

    def __init__(self, response: str):
        self.response = response
        self.calls: list[str] = []

    def __call__(self, prompt: str, *, timeout_s: float = 0.0) -> str:
        self.calls.append(prompt)
        return self.response


class ExplodingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, prompt: str, *, timeout_s: float = 0.0) -> str:
        self.calls.append(prompt)
        raise RuntimeError("model server refused the connection")


class AuditTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="headless-audit-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = make_repo(self.tmp / "repo")
        self.run_dir = self.tmp / "run"
        self.run_dir.mkdir()

    def packet(self, **over) -> dict:
        base = {
            "task_ids": ["T-1"],
            "batch_id": "batch-1",
            "worktree": str(self.repo),
            "lane": "lane0",
            "harness": "stub",
            "run_dir": str(self.run_dir),
        }
        base.update(over)
        return {k: v for k, v in base.items() if v is not None}

    def commit_change(self, rel: str, text: str, message: str) -> str:
        (self.repo / rel).write_text(text, encoding="utf-8")
        git(self.repo, "add", "--", rel)
        git(self.repo, "commit", "-q", "-m", message)
        return git(self.repo, "rev-parse", "HEAD").strip()


# ------------------------------------------------- 1. anti-vacuity of the probe


class MutationProbeAntiVacuityTests(AuditTestCase):
    """The probe must FAIL when the diff does not contain the expected change.

    A probe that passes on everything is not a probe. These three cases are the
    ways the naive versions of it pass for the wrong reason.
    """

    def _audit_offline(self, task_text: str, base: str, head: str,
                       report_kw: dict | None = None) -> dict:
        brief = write_brief(self.run_dir / "brief.json", "T-1", task_text)
        report = write_report(self.run_dir / "report.json", "T-1", **(report_kw or {}))
        return ha.audit(ha.parse_packet(self.packet(
            brief_path=str(brief), report_path=str(report),
            commit_range=f"{base}..{head}")), offline=True)

    def test_probe_passes_when_the_named_file_really_changed(self) -> None:
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("src/widget.py",
                                  "def widget():\n    return 42\n", "fix widget")
        result = self._audit_offline("Fix the null return in src/widget.py", base, head)
        probe = result["mutation_probe"]
        self.assertEqual(probe["target"], "src/widget.py")
        self.assertTrue(probe["passed"], probe)
        self.assertEqual([c["check"] for c in probe["checks"]],
                         ["present", "nonempty-net-patch", "revertible"])
        # Clean mechanical half + offline ⇒ blocked, never accept.
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)
        self.assertIsNone(result["mechanical_floor"])

    def test_probe_FAILS_when_the_diff_touches_a_different_file(self) -> None:
        """THE ANTI-VACUITY CASE. Task names src/widget.py; the worker changed docs."""
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("docs/notes.md", "# notes\nchanged\n", "touch docs")
        result = self._audit_offline("Fix the null return in src/widget.py", base, head)
        probe = result["mutation_probe"]
        self.assertEqual(probe["target"], "src/widget.py")
        self.assertFalse(probe["passed"], probe)
        present = probe["checks"][0]
        self.assertEqual(present["check"], "present")
        self.assertFalse(present["passed"])
        self.assertIn("does NOT touch src/widget.py", present["detail"])
        self.assertEqual(result["mechanical_floor"], ha.NEEDS_REWORK)
        self.assertEqual(result["verdict"], ha.NEEDS_REWORK)
        self.assertIn("mutation probe FAILED", result["rationale"])

    def test_probe_FAILS_on_change_then_revert_where_a_log_probe_would_pass(self) -> None:
        """The file is named by the range's commits; its NET effect is nothing."""
        base = git(self.repo, "rev-parse", "HEAD").strip()
        self.commit_change("src/widget.py", "def widget():\n    return 42\n", "change it")
        head = self.commit_change("src/widget.py",
                                  "def widget():\n    return None\n", "put it back")

        # A log-based probe WOULD pass here: the file is right there in the log.
        log_names = git(self.repo, "log", "--name-only", "--format=", f"{base}..{head}")
        self.assertIn("src/widget.py", log_names,
                      "fixture is wrong: the naive log probe must be able to pass here, "
                      "otherwise this test proves nothing about the net-diff choice")

        result = self._audit_offline("Fix the null return in src/widget.py", base, head)
        probe = result["mutation_probe"]
        self.assertFalse(probe["passed"], probe)
        self.assertEqual(result["verdict"], ha.NEEDS_REWORK)

    def test_revert_check_FAILS_when_the_change_is_not_present_in_the_tree(self) -> None:
        """'Would it fail if reverted' is checked against the TREE, not the diff."""
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("src/widget.py",
                                  "def widget():\n    return 42\n", "fix widget")
        # The commit says the file returns 42; the tree says otherwise. The
        # reverse-apply of that patch can no longer check clean.
        (self.repo / "src" / "widget.py").write_text(
            "totally unrelated content\n", encoding="utf-8")
        result = self._audit_offline("Fix the null return in src/widget.py", base, head)
        probe = result["mutation_probe"]
        checks = {c["check"]: c for c in probe["checks"]}
        self.assertTrue(checks["present"]["passed"])
        self.assertTrue(checks["nonempty-net-patch"]["passed"])
        self.assertFalse(checks["revertible"]["passed"], probe)
        self.assertFalse(probe["passed"])
        self.assertEqual(result["verdict"], ha.NEEDS_REWORK)

    def test_probe_is_undetermined_and_blocks_when_no_path_is_named(self) -> None:
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("src/widget.py", "x = 1\n", "whatever")
        result = self._audit_offline("Make the thing better somehow", base, head)
        self.assertTrue(result["mutation_probe"]["undetermined"])
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)
        self.assertEqual(result["mechanical_floor"], ha.BLOCKED_EVIDENCE)

    def test_probe_target_comes_from_the_task_text_not_the_diff(self) -> None:
        """If the target were chosen from the diff, the probe would be a tautology."""
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("docs/notes.md", "# notes\nx\n", "docs only")
        rows = [{"task_id": "T-1", "task_text": "Update src/widget.py to return 42"}]
        facts = ha.git_facts(self.repo, f"{base}..{head}")
        target = ha.choose_probe_target(rows, facts)
        self.assertEqual(target["target"], "src/widget.py")
        self.assertEqual(target["derived_from"], "task_text")
        self.assertNotIn(target["target"], facts["changed_paths"])


# ------------------------------------------------------- 2. packet contract


class PacketContractTests(AuditTestCase):
    def test_claim_shaped_key_is_refused(self) -> None:
        for key in ("summary", "outcome", "rows", "commits"):
            with self.subTest(key=key):
                with self.assertRaises(ha.AuditError) as ctx:
                    ha.parse_packet(self.packet(**{key: "the worker says it went great"}))
                self.assertIn("claim-shaped", str(ctx.exception))

    def test_unknown_key_is_refused(self) -> None:
        with self.assertRaises(ha.AuditError) as ctx:
            ha.parse_packet(self.packet(vibes="excellent"))
        self.assertIn("unrecognised key", str(ctx.exception))

    def test_packet_without_worktree_is_refused(self) -> None:
        with self.assertRaises(ha.AuditError):
            ha.parse_packet({"task_ids": ["T-1"], "commit_range": "a..b"})

    def test_accepted_keys_match_the_runners_pointer_whitelist(self) -> None:
        """A drift alarm, not an import: the runner may only SHRINK this set.

        If worker_runner grows a pointer key, this fails and a human decides
        whether it is a pointer or a claim. That decision is the auditor's, which
        is why the list is not imported.
        """
        runner = (REPO_ROOT / "scripts" / "coordination" / "worker_runner.py")
        if not runner.exists():             # pragma: no cover - runner is P2-1
            self.skipTest("worker_runner.py not present")
        text = runner.read_text(encoding="utf-8")
        marker = "AUDIT_POINTER_KEYS = ("
        if marker not in text:              # pragma: no cover
            self.skipTest("worker_runner.py has no AUDIT_POINTER_KEYS block")
        block = text.split(marker, 1)[1].split(")", 1)[0]
        runner_keys = {t.strip().strip('",\'') for t in block.split(",") if t.strip()}
        runner_keys = {k for k in runner_keys if k}
        unknown = sorted(runner_keys - ha.ACCEPTED_PACKET_KEYS)
        self.assertFalse(unknown, (
            f"worker_runner.py now emits pointer key(s) {unknown} that headless_audit.py "
            f"does not accept. Decide deliberately whether each is a POINTER (add it to "
            f"ACCEPTED_PACKET_KEYS) or a CLAIM (add it to CLAIM_SHAPED_KEYS)."))


# ------------------------------------------------------------ 3. independence


class IndependenceTests(AuditTestCase):
    def test_a_glowing_report_cannot_rescue_a_diff_that_missed_the_target(self) -> None:
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("docs/notes.md", "# notes\nx\n", "docs only")
        brief = write_brief(self.run_dir / "brief.json", "T-1",
                            "Fix the null return in src/widget.py")
        report = write_report(self.run_dir / "report.json", "T-1",
                              artifacts=["src/widget.py"],
                              summary="Rewrote src/widget.py; all tests pass. SENTINEL-XYZZY")
        client = StubClient(json.dumps({"verdict": "accept", "rationale": "looks great",
                                        "followups": [], "claim_check": "agrees"}))
        result = ha.audit(ha.parse_packet(self.packet(
            brief_path=str(brief), report_path=str(report),
            commit_range=f"{base}..{head}")), client=client)
        self.assertEqual(result["verdict"], ha.NEEDS_REWORK)
        self.assertEqual(client.calls, [],
                         "the model must not be consulted once the mechanical half has "
                         "PROVEN a defect — a model that can overturn a failed probe is a "
                         "model that can rubber-stamp")
        self.assertNotIn("SENTINEL-XYZZY", json.dumps(result["derived"]),
                         "the derived truth must contain nothing from the worker's report")

    def test_claimed_artifact_absent_from_the_diff_is_a_contradiction(self) -> None:
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("src/widget.py", "def widget():\n    return 42\n", "fix")
        brief = write_brief(self.run_dir / "brief.json", "T-1",
                            "Fix the null return in src/widget.py")
        report = write_report(self.run_dir / "report.json", "T-1",
                              artifacts=["src/widget.py", "src/never_touched.py"])
        result = ha.audit(ha.parse_packet(self.packet(
            brief_path=str(brief), report_path=str(report),
            commit_range=f"{base}..{head}")), offline=True)
        details = " ".join(c["detail"] for c in result["contradictions"])
        self.assertIn("src/never_touched.py", details)
        self.assertEqual(result["verdict"], ha.NEEDS_REWORK)

    def test_claimed_commit_outside_the_range_is_a_contradiction(self) -> None:
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("src/widget.py", "def widget():\n    return 42\n", "fix")
        brief = write_brief(self.run_dir / "brief.json", "T-1",
                            "Fix the null return in src/widget.py")
        report = write_report(self.run_dir / "report.json", "T-1",
                              commits=["deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"],
                              artifacts=["src/widget.py"])
        result = ha.audit(ha.parse_packet(self.packet(
            brief_path=str(brief), report_path=str(report),
            commit_range=f"{base}..{head}")), offline=True)
        details = " ".join(c["detail"] for c in result["contradictions"])
        self.assertIn("deadbeef", details)
        self.assertEqual(result["verdict"], ha.NEEDS_REWORK)

    def test_pass_claimed_over_an_empty_diff_is_a_contradiction(self) -> None:
        head = git(self.repo, "rev-parse", "HEAD").strip()
        brief = write_brief(self.run_dir / "brief.json", "T-1",
                            "Fix the null return in src/widget.py")
        report = write_report(self.run_dir / "report.json", "T-1", outcome="pass")
        result = ha.audit(ha.parse_packet(self.packet(
            brief_path=str(brief), report_path=str(report),
            commit_range=f"{head}..{head}")), offline=True)
        self.assertEqual(result["verdict"], ha.NEEDS_REWORK)
        self.assertTrue(any("EMPTY" in c["detail"] for c in result["contradictions"]),
                        result["contradictions"])


# ------------------------------------------------------------- 4. fail closed


class FailClosedTests(AuditTestCase):
    _seq = 0

    def _clean_case(self) -> dict:
        # Unique content per call: a subTest loop calling this twice must not
        # produce an empty second commit (git refuses it), which would make the
        # loop's later cases fail for a fixture reason instead of the real one.
        type(self)._seq += 1
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change(
            "src/widget.py", f"def widget():\n    return {42 + self._seq}\n", "fix")
        brief = write_brief(self.run_dir / "brief.json", "T-1",
                            "Fix the null return in src/widget.py")
        report = write_report(self.run_dir / "report.json", "T-1",
                              artifacts=["src/widget.py"], commits=[head])
        return self.packet(brief_path=str(brief), report_path=str(report),
                           commit_range=f"{base}..{head}")

    def test_unresolvable_range_blocks_and_does_not_read_as_an_empty_diff(self) -> None:
        packet = self._clean_case()
        packet["commit_range"] = "cafebabecafebabecafebabecafebabecafebabe..HEAD"
        result = ha.audit(ha.parse_packet(packet), offline=True)
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)
        self.assertTrue(any("does not resolve" in r for r in result["blocked_reasons"]))

    def test_missing_commit_range_blocks(self) -> None:
        packet = self._clean_case()
        packet.pop("commit_range")
        result = ha.audit(ha.parse_packet(packet), offline=True)
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)

    def test_missing_report_blocks(self) -> None:
        packet = self._clean_case()
        Path(packet["report_path"]).unlink()
        result = ha.audit(ha.parse_packet(packet), offline=True)
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)
        self.assertTrue(any("never wrote one" in r for r in result["blocked_reasons"]))

    def test_offline_with_a_clean_mechanical_half_blocks_rather_than_guesses(self) -> None:
        result = ha.audit(ha.parse_packet(self._clean_case()), offline=True)
        self.assertIsNone(result["mechanical_floor"])
        self.assertTrue(result["mutation_probe"]["passed"])
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)
        self.assertIn("Refusing to guess", result["rationale"])

    def test_model_error_blocks(self) -> None:
        client = ExplodingClient()
        result = ha.audit(ha.parse_packet(self._clean_case()), client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)

    def test_unparseable_model_output_blocks(self) -> None:
        result = ha.audit(ha.parse_packet(self._clean_case()),
                          client=StubClient("sure, looks fine to me!"))
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)

    def test_off_enum_verdict_blocks(self) -> None:
        for bogus in ("approved", "LGTM", "accept!", "", None, 7):
            with self.subTest(bogus=bogus):
                result = ha.audit(ha.parse_packet(self._clean_case()),
                                  client=StubClient(json.dumps({"verdict": bogus})))
                self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)

    def test_accept_with_followups_and_no_followups_blocks(self) -> None:
        result = ha.audit(ha.parse_packet(self._clean_case()),
                          client=StubClient(json.dumps(
                              {"verdict": "accept-with-followups", "followups": []})))
        self.assertEqual(result["verdict"], ha.BLOCKED_EVIDENCE)

    def test_model_may_accept_a_clean_case(self) -> None:
        client = StubClient("Here is my answer:\n" + json.dumps(
            {"verdict": "accept", "rationale": "the diff returns 42 as asked",
             "followups": [], "claim_check": "report matches the diff"}))
        result = ha.audit(ha.parse_packet(self._clean_case()), client=client)
        self.assertEqual(result["verdict"], ha.ACCEPT)
        self.assertEqual(len(client.calls), 1)
        bundle = json.loads(client.calls[0].split("EVIDENCE:\n", 1)[1])
        self.assertIn("worker_claims_UNVERIFIED", bundle)
        self.assertIn("derived_truth", bundle)

    def test_model_may_lower_but_the_floor_is_never_raised(self) -> None:
        result = ha.audit(ha.parse_packet(self._clean_case()),
                          client=StubClient(json.dumps(
                              {"verdict": "needs-rework", "rationale": "wrong approach"})))
        self.assertEqual(result["verdict"], ha.NEEDS_REWORK)

    def test_severity_order_is_the_one_the_floor_relies_on(self) -> None:
        self.assertLess(ha._SEVERITY[ha.BLOCKED_EVIDENCE], ha._SEVERITY[ha.NEEDS_REWORK])
        self.assertLess(ha._SEVERITY[ha.NEEDS_REWORK], ha._SEVERITY[ha.ACCEPT_FOLLOWUPS])
        self.assertLess(ha._SEVERITY[ha.ACCEPT_FOLLOWUPS], ha._SEVERITY[ha.ACCEPT])


# --------------------------------------------------------------- 5. bus write


class BusWriteTests(AuditTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.bus = self.tmp / "bus"
        self.bus.mkdir()
        for name in ("config.yaml", "session_bus.schema.json"):
            shutil.copy2(LIVE_BUS / name, self.bus / name)
        for area in ("inbox", "outbox", "heartbeats", "cursors"):
            (self.bus / area).mkdir()
        (self.bus / "queue.jsonl").write_text("", encoding="utf-8")

    def _result(self, verdict: str) -> dict:
        return {"verdict": verdict, "batch_id": "batch-1", "task_ids": ["T-1"],
                "mechanical_floor": None, "rationale": "because",
                "mutation_probe": {"target": "src/widget.py", "passed": True},
                "contradictions": [], "blocked_reasons": [],
                "commit_range": "a..b", "worktree": str(self.repo), "followups": []}

    def test_verdict_lands_only_in_the_auditors_own_outbox(self) -> None:
        ha.emit_verdict(self.bus, "auditor", self._result(ha.ACCEPT))
        written = sorted(p.name for p in (self.bus / "outbox").glob("*"))
        self.assertEqual(written, ["auditor.jsonl"])
        self.assertEqual((self.bus / "queue.jsonl").read_text(), "",
                         "the auditor must never write queue.jsonl — it PROPOSES, the "
                         "daemon transcribes")
        row = json.loads((self.bus / "outbox" / "auditor.jsonl").read_text().strip())
        self.assertEqual(row["kind"], "finding")
        self.assertEqual(row["from"], "auditor")
        self.assertEqual(row["payload"]["audit_verdict"], ha.ACCEPT)
        self.assertTrue(row["payload"]["derived_independently"])
        self.assertNotIn("action_required", row)

    def test_actionable_verdicts_carry_one_assignee_and_route(self) -> None:
        for verdict in (ha.NEEDS_REWORK, ha.BLOCKED_EVIDENCE):
            with self.subTest(verdict=verdict):
                ha.emit_verdict(self.bus, "auditor", self._result(verdict))
        rows = [json.loads(ln) for ln in
                (self.bus / "outbox" / "auditor.jsonl").read_text().splitlines() if ln.strip()]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertTrue(row["action_required"])
            self.assertEqual(row["assignee"], "coordinator-agent")
            self.assertEqual(row["needs_routing_to"], ["coordinator-agent"])

    def test_a_non_roster_writer_is_refused(self) -> None:
        with self.assertRaises(BusError):
            ha.emit_verdict(self.bus, "not-a-roster-id", self._result(ha.ACCEPT))

    def test_required_writer_agrees_with_the_path_this_module_writes(self) -> None:
        from scripts.coordination.session_bus import required_writer
        self.assertEqual(required_writer(self.bus, self.bus / "outbox" / "auditor.jsonl"),
                         "auditor")


# ------------------------------------------------------------------- 6. CLI


class CliTests(AuditTestCase):
    def test_exit_codes_and_json_output(self) -> None:
        base = git(self.repo, "rev-parse", "HEAD").strip()
        head = self.commit_change("docs/notes.md", "# notes\nx\n", "docs only")
        brief = write_brief(self.run_dir / "brief.json", "T-1",
                            "Fix the null return in src/widget.py")
        report = write_report(self.run_dir / "report.json", "T-1")
        packet_path = self.tmp / "packet.json"
        packet_path.write_text(json.dumps(self.packet(
            brief_path=str(brief), report_path=str(report),
            commit_range=f"{base}..{head}")), encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "coordination" / "headless_audit.py"),
             "audit", "--packet", str(packet_path), "--offline"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, ha.EX_NEEDS_REWORK, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], ha.NEEDS_REWORK)

    def test_a_refused_packet_exits_blocked(self) -> None:
        packet_path = self.tmp / "bad.json"
        packet_path.write_text(json.dumps({"worktree": str(self.repo),
                                           "summary": "it went great"}), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "coordination" / "headless_audit.py"),
             "audit", "--packet", str(packet_path), "--offline"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, ha.EX_BLOCKED, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], ha.BLOCKED_EVIDENCE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
