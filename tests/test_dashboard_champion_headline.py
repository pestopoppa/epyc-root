"""The champion headline: ONE number, ONE named anchor, allowed to be absent.

WHY THIS FILE EXISTS (operator, 2026-08-30)
-------------------------------------------
`/loop` carried ``+48.9%`` in the largest type on the page, sourced from the
operator-gated manual-research bundle, directly beside a loop whose own champion
was worth roughly a tenth of that. Different producers, different anchors,
different questions -- rendered side by side with nothing saying so. The operator
read the page and reasonably asked why the champion said +48.9% when they had
been told +9%.

The ruling: the champion headline is the champion tree's collective performance
gain over the FROZEN PRODUCTION KERNEL and nothing else competes for that slot;
capabilities the tree enables may be listed beside it.

AND IT MUST RENDER HONESTLY AS UNMEASURED. There is no direct champion-vs-v9 A/B
for the current champion ``5ad3e36d``. The last one was several commits ago; run
17 added 30 commits (audited as a block at +3.942% against *what that run started
from*) and run 18 added one. Those are MARGINALS against an anchor that advances
on every keep, and composing them would manufacture a measurement no run ever
took -- the derived-marginal error this program already made once.

THE ANCHOR IS RESOLVED, NEVER REMEMBERED (operator ruling, 2026-08-31)
----------------------------------------------------------------------
"Once we promote a new frozen version in the future, the comparison should be
against the newly promoted version, NOT stale v9." So the reader resolves the
frozen production kernel LIVE from the canonical frozen tree, and these tests
drive it with a TEMP git repository posing as that tree -- resolvable, promoted
past the bundle's baseline, off-contract, detached, or missing -- so no unit
test here depends on the real host tree. Exactly ONE integration test touches
the real ``/mnt/raid0/llm/llama.cpp``, read-only, and skips with a stated
reason where it is absent. A bundle honestly anchored on a since-promoted
production renders as SUPERSEDED-BASELINE (dated, both commits named, number
kept), NOT as malformed and NOT as fresh; it composes orthogonally with the
existing champion supersession.

WHERE THE FIXTURES COME FROM, AND WHY IT MATTERS
------------------------------------------------
A fixture written from the READER's expectations proves only that the reader is
self-consistent. That is exactly how the GPU panel stayed dark through 41 passing
tests: ``body()`` invented ``held_s``, the reader looked for ``held_s``, and both
disagreed with the producer's ``claim_held_s``.

So every value here is lifted from a record that exists on disk:

  * the loop body is ``tests/fixtures/autokernel_loop_status_sample.json`` -- a
    verbatim recording of the running loop's own store root;
  * the operator-gated bundle is the REAL emitted file, read from the host, and
    these tests SKIP rather than invent one if it is not there;
  * the champion bundle is the REAL emitted
    ``loop-memory/champion-vs-production.json`` (a producer writes it since
    2026-08-30), re-dated and re-anchored per test -- its baseline commit MUST
    be parametrized, because the whole point of the live resolver is that the
    correct anchor is whatever the (temp) frozen tree's HEAD is, not a sha
    this file remembers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from dashboard import loop_status  # noqa: E402
from dashboard import server as S  # noqa: E402

PAGE = REPO / "dashboard/static/loop.html"
HARNESS = Path(__file__).resolve().parent / "js" / "render_harness.js"
SAMPLE = REPO / "tests/fixtures/autokernel_loop_status_sample.json"

#: The real emitted operator-gated bundle, on this host. Read, never invented:
#: it is the producer of the number that caused the confusion, and a hand-written
#: stand-in would let this file and the page agree with each other while both
#: disagreed with the emitter.
REAL_BUNDLE = Path("/mnt/raid0/llm/autokernel/surface/operator_gate_bundle.json")
#: The REAL champion-vs-production bundle: a producer writes this carrier since
#: 2026-08-30, so its key names are recorded from disk rather than stated here.
REAL_CHAMPION = Path(
    "/mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json")
#: The real frozen production tree, used by exactly ONE read-only integration
#: test. Every other test drives a temp repository posing as it.
REAL_FROZEN_TREE = Path("/mnt/raid0/llm/llama.cpp")

#: The label every temp frozen tree starts on. A test value, not a remembered
#: production fact: the reader must DERIVE whatever branch the tree is on.
V9_BRANCH = "production-consolidated-v9"


def make_production_repo(path: Path, branch: str = V9_BRANCH) -> str:
    """A temp git repo posing as the frozen production tree. Returns HEAD."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", branch, str(path)],
                   check=True, capture_output=True)
    return advance_production_repo(path)


def advance_production_repo(path: Path, rename_to: str | None = None) -> str:
    """One more commit on the posing tree -- a promotion when renamed. HEAD."""
    subprocess.run(["git", "-C", str(path), "-c", "user.name=t",
                    "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
                    "-m", "promote"], check=True, capture_output=True)
    if rename_to is not None:
        subprocess.run(["git", "-C", str(path), "branch", "-m", rename_to],
                       check=True, capture_output=True)
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                          check=True, capture_output=True,
                          text=True).stdout.strip()


def _stamp(seconds_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
            ).isoformat().replace("+00:00", "Z")


def recorded_loop(*, age_s: float = 45.0, state: str = "running") -> dict:
    body = json.loads(SAMPLE.read_text(encoding="utf-8"))
    body["generated_at"] = _stamp(age_s)
    body["state"] = state
    return body


def real_bundle() -> dict:
    if not REAL_BUNDLE.is_file():
        raise unittest.SkipTest(
            f"{REAL_BUNDLE} is not on this host; refusing to invent the emitted "
            "bundle whose mislabelling is the subject of this file")
    return json.loads(REAL_BUNDLE.read_text(encoding="utf-8"))


def real_champion() -> dict:
    if not REAL_CHAMPION.is_file():
        raise unittest.SkipTest(
            f"{REAL_CHAMPION} is not on this host; refusing to hand-author the "
            "producer's key names")
    return json.loads(REAL_CHAMPION.read_text(encoding="utf-8"))


def champion_bundle(*, baseline_commit: str,
                    age_s: float = 3600.0, champion_commit: str | None = None,
                    baseline_label: str = V9_BRANCH,
                    capabilities: object = "unset") -> dict:
    """The REAL emitted champion bundle, re-dated and re-anchored per test.

    Every key comes from the file the producer actually writes (see the module
    docstring). ``baseline_commit`` is REQUIRED with no default on purpose: the
    correct anchor is whatever the posing frozen tree's HEAD is, and a default
    here would be exactly the remembered sha this revision removes.
    ``capabilities`` defaults to REMOVED so the unknown-path tests exercise a
    producer that never published the field; the real file's list is a real
    record, not this file's.
    """
    body = real_champion()
    body["generated_at"] = _stamp(age_s)
    body["stale_after_s"] = int(loop_status.CHAMPION_DEFAULT_STALE_AFTER_S)
    body["baseline"] = {"commit": baseline_commit, "label": baseline_label}
    body["champion"] = {"commit": (champion_commit if champion_commit is not None
                                   else recorded_loop()["champion_head"])}
    if capabilities == "unset":
        body.pop("capabilities", None)
    else:
        body["capabilities"] = capabilities
    return body


class _Store(unittest.TestCase):
    """Temp store root, temp gate path, and a TEMP GIT REPO posing as the
    frozen production tree — so no test below depends on the real host tree,
    and a "promotion" is three lines of git rather than a thought experiment."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="champ-headline-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        prior = os.environ.get(loop_status.STORE_ROOT_ENV)
        os.environ[loop_status.STORE_ROOT_ENV] = str(self.root)
        self.addCleanup(self._restore_env, loop_status.STORE_ROOT_ENV, prior)
        self.prod_tree = self.root / "frozen-tree"
        self.prod_sha = make_production_repo(self.prod_tree)
        prior_tree = os.environ.get(loop_status.FROZEN_TREE_ENV)
        os.environ[loop_status.FROZEN_TREE_ENV] = str(self.prod_tree)
        self.addCleanup(self._restore_env, loop_status.FROZEN_TREE_ENV,
                        prior_tree)
        # The champion-tip resolver points at a NONEXISTENT path by default, so
        # tests exercise the last-run fallback unless they build a champion
        # repo deliberately — no test may lean on the real host's champ tree.
        prior_champ = os.environ.get(loop_status.CHAMPION_TREE_ENV)
        os.environ[loop_status.CHAMPION_TREE_ENV] = str(self.root / "no-champ-tree")
        self.addCleanup(self._restore_env, loop_status.CHAMPION_TREE_ENV,
                        prior_champ)
        self.prior_gate = S.OPERATOR_GATE_BUNDLE_JSON
        self.addCleanup(setattr, S, "OPERATOR_GATE_BUNDLE_JSON", self.prior_gate)
        with S._watchdog_lock:
            S._watchdog_state.clear()

    @staticmethod
    def _restore_env(name: str, prior: str | None) -> None:
        if prior is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = prior

    def bundle(self, **kw) -> dict:
        """A champion bundle anchored, by default, on the POSING tree's HEAD."""
        kw.setdefault("baseline_commit", self.prod_sha)
        return champion_bundle(**kw)

    def promote(self, branch: str = "production-consolidated-v10") -> str:
        """Advance the posing tree past every anchored bundle — a promotion."""
        return advance_production_repo(self.prod_tree, rename_to=branch)

    def use_tree(self, path: Path) -> None:
        os.environ[loop_status.FROZEN_TREE_ENV] = str(path)

    def write_loop(self, body: object) -> None:
        target = self.root / loop_status.STATUS_FILENAME
        target.write_text(body if isinstance(body, str) else json.dumps(body),
                          encoding="utf-8")

    def write_champion(self, body: object) -> None:
        target = self.root / loop_status.CHAMPION_FILENAME
        target.write_text(body if isinstance(body, str) else json.dumps(body),
                          encoding="utf-8")

    def use_real_bundle(self) -> None:
        """Copy the REAL emitted bundle in, so its mtime is inside its envelope."""
        source = real_bundle()
        target = self.root / "operator_gate_bundle.json"
        target.write_text(json.dumps(source), encoding="utf-8")
        S.OPERATOR_GATE_BUNDLE_JSON = target

    def use_bundle_with_commit(self, commit: str) -> None:
        """The REAL emitted bundle, re-pointed at ``commit`` — for driving the
        scope line's computed relationship against a posing champion tree."""
        source = real_bundle()
        source["champion"] = dict(source.get("champion") or {}, commit=commit)
        target = self.root / "operator_gate_bundle.json"
        target.write_text(json.dumps(source), encoding="utf-8")
        S.OPERATOR_GATE_BUNDLE_JSON = target

    def lineage_repo(self) -> tuple[Path, str, str, str]:
        """A posing champion tree with a real lineage: ``parent`` is an
        ancestor of ``tip`` (the branch HEAD), and ``divergent`` is a commit on
        a side branch that is NOT in the tip's history. Returns
        ``(path, parent, tip, divergent)`` and points the resolver at it."""
        path = self.root / "champ-lineage"
        parent = make_production_repo(path, branch="ak/champion/llama-cpp-test")
        subprocess.run(["git", "-C", str(path), "checkout", "-q", "-b", "side"],
                       check=True, capture_output=True)
        # A DISTINCT message: two empty commits with the same parent, tree,
        # message and second-resolution timestamps hash to the SAME sha, and
        # "divergent" would silently equal "tip".
        subprocess.run(["git", "-C", str(path), "-c", "user.name=t",
                        "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
                        "-m", "divergent side work"],
                       check=True, capture_output=True)
        divergent = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"], check=True,
            capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "-C", str(path), "checkout", "-q",
                        "ak/champion/llama-cpp-test"],
                       check=True, capture_output=True)
        tip = advance_production_repo(path)
        self.assertNotEqual(divergent, tip)
        os.environ[loop_status.CHAMPION_TREE_ENV] = str(path)
        return path, parent, tip, divergent

    def block(self) -> dict:
        return S.loop_payload()["champion_vs_production"]


# --------------------------------------------------------------------------- #
# The reader
# --------------------------------------------------------------------------- #
class Contract(_Store):

    def test_the_contract_this_file_pins_is_the_one_the_reader_reads(self):
        """NON-VACUITY / anti-drift.

        Every fixture below is built against key names stated in this file
        because no producer writes this carrier yet. If the reader renamed a
        field, every test here would keep passing against its own spelling --
        the self-consistent-fixture failure, one level up. So the reader's own
        accepted body is round-tripped and the derived block must carry the
        values through.
        """
        self.write_loop(recorded_loop())
        body = self.bundle()
        self.write_champion(body)
        got = self.block()
        self.assertTrue(got["measured"])
        self.assertEqual(got["effect_fraction"], body["effect_fraction"])
        self.assertEqual(got["surface"], body["surface"])
        self.assertEqual(got["pairs"], body["pairs"])
        self.assertEqual(got["metric"], body["metric"])
        self.assertEqual(got["champion"]["measured_commit"],
                         body["champion"]["commit"])

    def test_the_anchor_is_the_frozen_production_kernel_and_is_stated_always(self):
        """Named on EVERY reading -- measured, absent, refused. A percentage
        with no named anchor is the defect that produced this whole revision.
        The expected commit is the POSING TREE's HEAD, read back with git by
        this test — never a constant, in the reader or in here."""
        self.write_loop(recorded_loop())
        for label, setup in (("absent", lambda: None),
                             ("malformed", lambda: self.write_champion("{half")),
                             ("measured",
                              lambda: self.write_champion(self.bundle()))):
            with self.subTest(label):
                if label != "absent":
                    (self.root / loop_status.CHAMPION_FILENAME).unlink(
                        missing_ok=True)
                setup()
                got = self.block()
                self.assertEqual(got["baseline"]["commit"], self.prod_sha)
                self.assertEqual(got["baseline"]["label"], V9_BRANCH)
                # And the RESOLVED production is served beside it, from git.
                self.assertTrue(got["production"]["resolved"])
                self.assertEqual(got["production"]["commit"], self.prod_sha)
                self.assertEqual(got["production"]["label"], V9_BRANCH)

    def test_a_bundle_anchored_on_a_SUPERSEDED_production_is_dated_not_refused(self):
        """THE promotion case (operator ruling, 2026-08-31). The bundle is
        honest about what it measured; production has moved past it. It is NOT
        malformed and NOT fresh — it is SUPERSEDED-BASELINE, number kept, both
        commits named."""
        self.write_loop(recorded_loop())
        old = self.prod_sha
        new = self.promote("production-consolidated-v10")
        self.assertNotEqual(old, new)
        self.write_champion(self.bundle(baseline_commit=old))
        got = self.block()
        self.assertTrue(got["measured"], "an honest bundle lost its number")
        self.assertIsNone(got["reader_error"], "the bundle was refused")
        self.assertIsNotNone(got["effect_fraction"])
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_FRESH,
                         "file freshness is a separate axis and the file is new")
        self.assertEqual(got["baseline_check"], "superseded")
        sup = got["baseline_supersession"]
        self.assertIsNotNone(sup)
        self.assertEqual(sup["measured_against"], old)
        self.assertEqual(sup["current_production"], new)
        self.assertEqual(sup["current_label"], "production-consolidated-v10")
        self.assertIn("superseded by a promotion", sup["detail"])
        # The displayed anchor stays the bundle's own — relabelling it with
        # today's production would claim a comparison nobody ran.
        self.assertEqual(got["baseline"]["commit"], old)

    def test_a_freshly_promoted_baseline_is_current_not_refused(self):
        """The OTHER direction the hardcoded sha got wrong: the first correct
        post-promotion bundle must read as the current standing."""
        self.write_loop(recorded_loop())
        new = self.promote("production-consolidated-v10")
        self.write_champion(self.bundle(
            baseline_commit=new, baseline_label="production-consolidated-v10"))
        got = self.block()
        self.assertTrue(got["measured"])
        self.assertIsNone(got["reader_error"])
        self.assertEqual(got["baseline_check"], "current")
        self.assertIsNone(got["baseline_supersession"])
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_FRESH)
        self.assertEqual(got["production"]["label"],
                         "production-consolidated-v10")

    def test_a_bundle_naming_no_identifiable_anchor_is_REFUSED(self):
        """MALFORMED is now exactly this: an anchor that cannot be identified.
        Unidentifiable is the emitter's fault; merely superseded is not."""
        self.write_loop(recorded_loop())
        cases = {
            "short sha": self.bundle(baseline_commit=self.prod_sha[:12]),
            "empty": self.bundle(baseline_commit=""),
        }
        no_commit = self.bundle()
        del no_commit["baseline"]["commit"]
        cases["no commit key"] = no_commit
        no_baseline = self.bundle()
        del no_baseline["baseline"]
        cases["no baseline at all"] = no_baseline
        for label, body in cases.items():
            with self.subTest(label):
                self.write_champion(body)
                got = self.block()
                self.assertFalse(got["measured"])
                self.assertEqual(got["freshness"]["state"],
                                 loop_status.STATE_MALFORMED)
                self.assertIn("baseline", got["reader_error"])
                self.assertIsNone(got["effect_fraction"])

    def test_absent_is_not_a_measured_zero(self):
        self.write_loop(recorded_loop())
        got = self.block()
        self.assertFalse(got["measured"])
        self.assertIsNone(got["effect_fraction"])
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_ABSENT)
        self.assertIn("not been taken", got["absence_means"])
        self.assertIn("direct A/B", got["would_populate"])
        # The sentence names the RESOLVED current production, from the
        # posing tree — a remembered sha here would go stale on promotion.
        self.assertIn(self.prod_sha[:12], got["would_populate"])
        self.assertIn(V9_BRANCH, got["would_populate"])

    def test_absent_is_not_malformed_is_not_stale_is_not_fresh(self):
        """Four states, four verdicts, in the SAME vocabulary the loop badge and
        the operator-gate badge use. Three producers spelling `stale` three ways
        is a page nobody can read at a glance."""
        self.write_loop(recorded_loop())
        seen = {}
        seen["absent"] = self.block()
        self.write_champion("")
        seen["malformed"] = self.block()
        self.write_champion(self.bundle(
            age_s=60 * 86400))
        seen["stale"] = self.block()
        self.write_champion(self.bundle())
        seen["fresh"] = self.block()
        states = {k: v["freshness"]["state"] for k, v in seen.items()}
        self.assertEqual(states, {"absent": "absent", "malformed": "malformed",
                                  "stale": "stale", "fresh": "fresh"})
        self.assertEqual(len({v["freshness"]["detail"] for v in seen.values()}), 4)
        for state in states.values():
            self.assertIn(state, loop_status.STATES)
        # A stale bundle still CARRIES its number -- the measurement happened.
        self.assertTrue(seen["stale"]["measured"])

    def test_an_empty_file_is_malformed_not_absent(self):
        self.write_loop(recorded_loop())
        self.write_champion("")
        got = self.block()
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_MALFORMED)
        self.assertIn("empty", got["reader_error"])

    def test_a_future_stamp_cannot_buy_permanent_freshness(self):
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle(age_s=-86400))
        got = self.block()
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_MALFORMED)
        self.assertIn("FUTURE", got["freshness"]["detail"])

    def test_a_measurement_for_a_superseded_champion_says_so(self):
        """The normal case, not an edge one: a cumulative A/B is expensive and
        the champion advances on every keep."""
        self.write_loop(recorded_loop())
        older = real_bundle()["champion"]["commit"]
        self.write_champion(self.bundle(champion_commit=older))
        got = self.block()
        self.assertTrue(got["measured"])
        self.assertIsNotNone(got["supersession"])
        self.assertEqual(got["supersession"]["measured_for"], older)
        self.assertEqual(got["supersession"]["current_champion"],
                         recorded_loop()["champion_head"])
        self.assertIn("cannot be added", got["supersession"]["detail"])
        # ORTHOGONALITY: a superseded CHAMPION is not a superseded BASELINE.
        self.assertIsNone(got["baseline_supersession"])
        self.assertEqual(got["baseline_check"], "current")

    def _champion_repo(self, at_commit_of: str | None = None) -> tuple[Path, str]:
        """A temp git repo posing as the champion tree, attached to an
        ak/champion/* branch. Returns (path, HEAD)."""
        path = self.root / "champ-tree"
        head = make_production_repo(path, branch="ak/champion/llama-cpp-test")
        os.environ[loop_status.CHAMPION_TREE_ENV] = str(path)
        return path, head

    def test_the_branch_tip_outranks_a_dead_runs_status_file(self):
        """INC geometry, 2026-08-31: run 20's dying status named the
        pre-reconciliation head while the merge moved the branch; the panel
        called a fresh measurement of the REAL champion superseded. The tip is
        the champion (the single-champion invariant); the status file is one
        run's view and outlives the run."""
        path, tip = self._champion_repo()
        stale = dict(recorded_loop());  stale["champion_head"] = "4" * 40
        self.write_loop(stale)
        self.write_champion(self.bundle(champion_commit=tip))
        got = self.block()
        self.assertIsNone(got["supersession"],
                          "measured == branch tip must never read superseded, "
                          "whatever a dead run's status file says")
        self.assertEqual(got["champion"]["branch_tip"], tip)

    def test_a_tip_past_the_measurement_supersedes_with_its_source_named(self):
        path, _ = self._champion_repo()
        older = real_bundle()["champion"]["commit"]
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle(champion_commit=older))
        got = self.block()
        self.assertIsNotNone(got["supersession"])
        self.assertEqual(got["supersession"]["current_champion_source"],
                         "the champion branch tip")

    def test_an_unresolvable_tree_falls_back_to_the_last_runs_view(self):
        self.write_loop(recorded_loop())
        older = real_bundle()["champion"]["commit"]
        self.write_champion(self.bundle(champion_commit=older))
        got = self.block()
        self.assertIsNotNone(got["supersession"])
        self.assertEqual(got["supersession"]["current_champion_source"],
                         "the last loop run's status")
        self.assertIn("last loop run", got["supersession"]["detail"])

    def test_the_same_commit_raises_no_supersession(self):
        """Compliant-path control: the flag must not fire on every reading."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle())
        got = self.block()
        self.assertIsNone(got["supersession"])
        self.assertIsNone(got["baseline_supersession"])

    def test_the_marginals_are_declared_uncomposable_on_every_reading(self):
        self.write_loop(recorded_loop())
        for label in ("absent", "measured"):
            with self.subTest(label):
                if label == "measured":
                    self.write_champion(self.bundle())
                note = self.block()["not_composable"]
                self.assertIn("must never be summed", note)
                self.assertIn("advances on every keep", note)


class Capabilities(_Store):

    def test_unknown_is_stated_with_a_reason_and_a_remedy(self):
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle())
        caps = self.block()["capabilities"]
        self.assertFalse(caps["known"])
        self.assertEqual(caps["items"], [])
        self.assertIn("no producer attributes a capability list",
                      caps["unknown_reason"])
        self.assertIn("capabilities", caps["would_populate"])

    def test_a_published_list_is_carried_verbatim_with_its_evidence(self):
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle(capabilities=[
            {"name": "FlashAttention2 on gfx90a", "evidence": "gate fa2_supported"},
            "iqk IQ4_XS coverage",
        ]))
        caps = self.block()["capabilities"]
        self.assertTrue(caps["known"])
        self.assertEqual([i["name"] for i in caps["items"]],
                         ["FlashAttention2 on gfx90a", "iqk IQ4_XS coverage"])
        self.assertEqual(caps["items"][0]["evidence"], "gate fa2_supported")
        self.assertIsNone(caps["items"][1]["evidence"])
        self.assertIsNone(caps["unknown_reason"])

    def test_a_DECLARED_EMPTY_list_is_not_unknown(self):
        """Two different facts. 'The producer looked and found none' is a
        statement; 'nobody has been asked' is the absence of one."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle(capabilities=[]))
        caps = self.block()["capabilities"]
        self.assertTrue(caps["known"])
        self.assertEqual(caps["items"], [])
        self.assertIsNone(caps["unknown_reason"])

    def test_the_shipped_page_names_no_capability_of_its_own(self):
        """The list must be DERIVED, never typed. If a capability name ever
        appears in the markup, it is a memory wearing a measurement's clothes --
        and there is no FlashAttention2 record anywhere under the campaign for
        it to have come from."""
        html = PAGE.read_text(encoding="utf-8")
        # Comments explain the rule and may name the example the operator gave;
        # strip them so this greps the CODE, not its own rationale.
        code = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
        code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
        code = "\n".join(re.sub(r"//.*$", "", line) for line in code.splitlines())
        for banned in ("FlashAttention", "FlashAttention2", "GGML_IQK",
                       "IQ4_XS", "rocwmma"):
            self.assertNotIn(banned, code,
                             f"{banned!r} is typed into the shipped page")


# --------------------------------------------------------------------------- #
# The production anchor is RESOLVED from the frozen tree, never remembered
# --------------------------------------------------------------------------- #
class ProductionResolution(_Store):
    """Operator ruling, 2026-08-31: after a promotion the comparison must be
    against the newly promoted kernel, never a stale remembered one. Every
    state here is EXECUTED against a temp git repo posing as the frozen tree."""

    def test_the_label_is_derived_from_the_branch_not_a_constant(self):
        """A tree on -v10 must render -v10 with no edit anywhere: the label is
        the branch name, read live."""
        tree = self.root / "v10-tree"
        sha = make_production_repo(tree, branch="production-consolidated-v10")
        got = loop_status.resolve_production(tree)
        self.assertTrue(got["resolved"], got["error"])
        self.assertEqual(got["commit"], sha)
        self.assertEqual(got["branch"], "production-consolidated-v10")
        self.assertEqual(got["label"], "production-consolidated-v10")

    def test_a_missing_tree_is_an_explicit_state_with_no_fallback_sha(self):
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle())
        self.use_tree(self.root / "no-such-tree")
        got = self.block()
        prod = got["production"]
        self.assertFalse(prod["resolved"])
        self.assertIn("not a git repository", prod["error"])
        self.assertIn("no-such-tree", prod["error"])
        # NO silent fallback: nothing resolves, nothing is remembered.
        self.assertIsNone(prod["commit"])
        self.assertIsNone(prod["label"])
        self.assertEqual(got["baseline_check"], "unverifiable")
        self.assertIsNone(got["baseline_supersession"])
        # The bundle itself is honest and keeps its number...
        self.assertTrue(got["measured"])
        self.assertIn("could not resolve", got["production_unresolved_means"])

    def test_an_off_contract_branch_does_not_resolve(self):
        """`verify_llama_cpp.sh` enforces production-consolidated-*; a tree on
        any other branch is not provably the production kernel."""
        tree = self.root / "off-contract"
        make_production_repo(tree, branch="feature/not-production")
        got = loop_status.resolve_production(tree)
        self.assertFalse(got["resolved"])
        self.assertIn("feature/not-production", got["error"])
        self.assertIn("production-consolidated-", got["error"])
        self.assertIsNone(got["label"])
        # The commit IS reported — it resolved — but earns no trust flag.
        self.assertIsNotNone(got["commit"])

    def test_a_detached_head_does_not_resolve(self):
        tree = self.root / "detached"
        make_production_repo(tree)
        subprocess.run(["git", "-C", str(tree), "checkout", "-q", "--detach"],
                       check=True, capture_output=True)
        got = loop_status.resolve_production(tree)
        self.assertFalse(got["resolved"])
        self.assertIn("DETACHED", got["error"])

    def test_a_resolution_failure_does_not_take_down_the_payload(self):
        """Requirement 2: its own state, never a crash — the loop block, the
        tiles, the notice must all still be served."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle())
        self.use_tree(self.root / "gone")
        payload = S.loop_payload()
        self.assertIsNotNone(payload["loop"])
        self.assertIsNotNone(payload["derived"])
        self.assertEqual(payload["freshness_state"], "fresh")
        self.assertFalse(
            payload["champion_vs_production"]["production"]["resolved"])

    def test_both_supersessions_compose_and_stay_distinct(self):
        """Requirement 4: champion-superseded and baseline-superseded are
        orthogonal — a bundle can be both, and each block names its own facts."""
        self.write_loop(recorded_loop())
        old = self.prod_sha
        older_champ = real_bundle()["champion"]["commit"]
        new = self.promote("production-consolidated-v10")
        self.write_champion(self.bundle(
            baseline_commit=old, champion_commit=older_champ))
        got = self.block()
        self.assertTrue(got["measured"])
        self.assertIsNotNone(got["supersession"])
        self.assertIsNotNone(got["baseline_supersession"])
        self.assertEqual(got["supersession"]["measured_for"], older_champ)
        self.assertEqual(got["baseline_supersession"]["measured_against"], old)
        self.assertEqual(got["baseline_supersession"]["current_production"], new)
        self.assertNotEqual(got["supersession"]["detail"],
                            got["baseline_supersession"]["detail"])

    def test_the_resolver_is_injectable_and_the_injection_is_used(self):
        """The verification bar: tests must never NEED the real host tree. A
        pre-resolved block passed in wins over the (broken) environment."""
        self.write_loop(recorded_loop())
        forged_sha = "f" * 40
        self.write_champion(self.bundle(
            baseline_commit=forged_sha,
            baseline_label="production-consolidated-v99"))
        self.use_tree(self.root / "gone")  # resolving would fail loudly
        got = loop_status.champion_snapshot(production={
            "resolved": True, "commit": forged_sha,
            "branch": "production-consolidated-v99",
            "label": "production-consolidated-v99",
            "tree": "injected", "error": None})
        self.assertTrue(got["production"]["resolved"])
        self.assertEqual(got["baseline_check"], "current")
        self.assertIsNone(got["baseline_supersession"])

    def test_no_production_sha_is_remembered_anywhere_in_the_surface(self):
        """The defect itself, as a guard: the v9 sha (or ANY 40-hex literal)
        hardcoded in the reader or the page is a comparison that goes stale at
        the next promotion. Comments included on purpose — a sha in a comment
        becomes the next copy-paste."""
        for path in (REPO / "dashboard/loop_status.py", PAGE):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("0db32c06", text, f"v9 sha remembered in {path}")
            self.assertNotRegex(text, r"\b[0-9a-f]{40}\b",
                                f"a 40-hex literal is remembered in {path}")

    def test_the_real_frozen_tree_resolves_on_contract(self):
        """THE one integration test, read-only (rev-parse and branch query
        only). It asserts the SHAPE of the contract, never a specific sha or
        version — that is the point of the revision."""
        if not (REAL_FROZEN_TREE / ".git").exists():
            self.skipTest(
                f"{REAL_FROZEN_TREE} is not on this host — the live resolver "
                "contract cannot be exercised against the real frozen tree")
        got = loop_status.resolve_production(REAL_FROZEN_TREE)
        self.assertTrue(got["resolved"], got["error"])
        self.assertRegex(got["commit"], r"^[0-9a-f]{40}$")
        self.assertTrue(
            got["branch"].startswith(loop_status.PRODUCTION_BRANCH_PREFIX),
            got["branch"])
        self.assertEqual(got["label"], got["branch"])


# --------------------------------------------------------------------------- #
# The run's lifecycle, which is NOT its freshness
# --------------------------------------------------------------------------- #
class Lifecycle(_Store):

    def test_a_stopped_run_is_FINISHED_not_STALE(self):
        """Run 18 was stopped with a STOP sentinel. The loop drains the current
        iteration and exits through the normal `complete` path, so half an hour
        later a freshness-keyed banner would accuse a producer that did exactly
        what it was told."""
        self.write_loop(recorded_loop(age_s=10800, state="complete"))
        payload = S.loop_payload()
        self.assertEqual(payload["freshness_state"], loop_status.STATE_STALE)
        self.assertEqual(payload["notice"]["kind"], loop_status.NOTICE_FINISHED)
        self.assertEqual(payload["notice"]["run_state"], "complete")
        self.assertIn("STOP sentinel", payload["notice"]["detail"])

    def test_a_declared_failure_is_FAILED_while_perfectly_fresh(self):
        """Freshness alone draws NO banner here: the run published on its way
        out, so the reading is current and the run is dead."""
        self.write_loop(recorded_loop(age_s=20, state="failed"))
        payload = S.loop_payload()
        self.assertEqual(payload["freshness_state"], loop_status.STATE_FRESH)
        self.assertEqual(payload["notice"]["kind"], loop_status.NOTICE_FAILED)

    def test_an_unexplained_silence_is_STALE(self):
        """The compliant-path control for the two above: a run that declared no
        end and went quiet is still stale, and must not be excused as finished."""
        self.write_loop(recorded_loop(age_s=10800, state="running"))
        payload = S.loop_payload()
        self.assertEqual(payload["notice"]["kind"], loop_status.NOTICE_STALE)

    def test_a_live_run_raises_no_notice_at_all(self):
        self.write_loop(recorded_loop(age_s=20, state="running"))
        self.assertEqual(S.loop_payload()["notice"]["kind"],
                         loop_status.NOTICE_NONE)

    def test_absent_and_malformed_outrank_any_declared_state(self):
        """With no trustworthy body there is no declared state to believe."""
        self.assertEqual(S.loop_payload()["notice"]["kind"],
                         loop_status.NOTICE_ABSENT)
        self.write_loop('{"schema": "epyc.autokernel.loop_status.v1", "state": "com')
        self.assertEqual(S.loop_payload()["notice"]["kind"],
                         loop_status.NOTICE_MALFORMED)

    def test_every_run_state_maps_to_a_notice_and_they_are_distinct(self):
        seen = {}
        for state in loop_status.RUN_STATES:
            self.write_loop(recorded_loop(age_s=20, state=state))
            seen[state] = S.loop_payload()["notice"]["kind"]
        self.assertEqual(seen["complete"], loop_status.NOTICE_FINISHED)
        self.assertEqual(seen["failed"], loop_status.NOTICE_FAILED)
        self.assertEqual(seen["running"], loop_status.NOTICE_NONE)
        self.assertEqual(seen["starting"], loop_status.NOTICE_NONE)
        for kind in seen.values():
            self.assertIn(kind, loop_status.NOTICES)


# --------------------------------------------------------------------------- #
# The gate card's scope line: the relationship is COMPUTED, never worded
# --------------------------------------------------------------------------- #
class GateScopeRelationship(_Store):
    """Operator note, 2026-08-31. The scope line asserted "a different tree" as
    prose written at commit time; a reconciliation merge then made the measured
    commit a PARENT of the current champion and the line rendered the opposite
    of the truth. The relationship is now a git-ancestry fact
    (`loop_status.champion_relationship`, `merge-base --is-ancestor` against
    the champion tree) computed per reading — four verdicts, each executed
    here against a posing lineage repo, none reasoned about."""

    def test_the_four_relationship_verdicts_are_computed_from_ancestry(self):
        _, parent, tip, divergent = self.lineage_repo()
        cases = {
            "tip": (tip, loop_status.REL_TIP),
            "ancestor": (parent, loop_status.REL_ANCESTOR),
            "divergent": (divergent, loop_status.REL_DIVERGENT),
        }
        for label, (commit, want) in cases.items():
            with self.subTest(label):
                got = loop_status.champion_relationship(commit)
                self.assertEqual(got["relation"], want, got)
                self.assertEqual(got["current_champion"], tip)
        self.assertIn("IN the current champion",
                      loop_status.champion_relationship(parent)["detail"])
        self.assertIn("different line of work",
                      loop_status.champion_relationship(divergent)["detail"])

    def test_an_unresolvable_tree_is_unresolvable_never_divergent(self):
        """"We cannot say" is not "it is different" — folding the two is how
        the original constant got written in the first place."""
        os.environ[loop_status.CHAMPION_TREE_ENV] = str(self.root / "gone")
        got = loop_status.champion_relationship("f" * 40)
        self.assertEqual(got["relation"], loop_status.REL_UNRESOLVABLE)
        self.assertIn("cannot be resolved", got["detail"])

    def test_a_commit_the_tree_never_saw_is_unresolvable_never_divergent(self):
        self.lineage_repo()
        got = loop_status.champion_relationship("f" * 40)
        self.assertEqual(got["relation"], loop_status.REL_UNRESOLVABLE)
        self.assertIn("cannot be established", got["detail"])

    def test_a_missing_measured_commit_is_unresolvable_with_the_reason(self):
        self.lineage_repo()
        for bad in (None, "", "270b48ed"):
            with self.subTest(repr(bad)):
                got = loop_status.champion_relationship(bad)
                self.assertEqual(got["relation"], loop_status.REL_UNRESOLVABLE)
                self.assertIn("no full 40-hex", got["detail"])

    def test_the_gate_reader_carries_the_computed_verdict(self):
        """The wiring: `_read_operator_gate_bundle` serves the verdict beside
        the commit, so the page repeats a computation instead of asserting."""
        _, parent, tip, _ = self.lineage_repo()
        self.use_bundle_with_commit(parent)
        got = S._read_operator_gate_bundle()
        rel = got["champion_relationship"]
        self.assertEqual(rel["relation"], loop_status.REL_ANCESTOR)
        self.assertEqual(rel["current_champion"], tip)
        self.assertEqual(rel["measured"], parent)


# --------------------------------------------------------------------------- #
# The rendered page
# --------------------------------------------------------------------------- #
@unittest.skipIf(shutil.which("node") is None, "node is not installed")
class Rendering(_Store):
    """Executes the real page JS. Stubs are not a browser: this proves the
    render path emits the content, not that the page looks right."""

    def _page_js(self) -> str:
        blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                            PAGE.read_text(encoding="utf-8"), re.S)
        self.assertTrue(blocks, "no inline script blocks found in loop.html")
        return "\n".join(blocks)

    def _render(self, page_js: str | None = None) -> dict:
        tmp = Path(tempfile.mkdtemp(prefix="champ-render-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "page.js").write_text(
            page_js if page_js is not None else self._page_js(), encoding="utf-8")
        (tmp / "payload.json").write_text(json.dumps(S.loop_payload()),
                                          encoding="utf-8")
        proc = subprocess.run(
            ["node", str(HARNESS), str(tmp / "page.js"), str(tmp / "payload.json")],
            capture_output=True, text=True, timeout=60)
        self.assertTrue(proc.stdout.strip(),
                        f"harness produced no output; stderr={proc.stderr[:400]}")
        out = json.loads(proc.stdout)
        self.assertEqual(out["threw"], [])
        # Keyed to the ELEMENT, never to the whole page: a whole-page substring
        # key is how "100%" once matched "+3.100%".
        self.assertIn("champ", out["by_id"])
        return out

    @staticmethod
    def _text(html: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()

    def test_the_harness_CATCHES_an_injected_fault(self):
        """Mutation, as a test. APPENDED, not prepended: declarations hoist."""
        self.write_loop(recorded_loop())
        broken = self._page_js() + "\nfunction renderChampion(d){ throw new Error('injected'); }\n"
        tmp = Path(tempfile.mkdtemp(prefix="champ-render-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "page.js").write_text(broken, encoding="utf-8")
        (tmp / "payload.json").write_text(json.dumps(S.loop_payload()),
                                          encoding="utf-8")
        proc = subprocess.run(
            ["node", str(HARNESS), str(tmp / "page.js"), str(tmp / "payload.json")],
            capture_output=True, text=True, timeout=60)
        out = json.loads(proc.stdout)
        self.assertTrue(out["threw"], "the harness did not notice an injected fault")
        self.assertTrue(any("injected" in t for t in out["threw"]))

    def test_an_unmeasured_headline_renders_words_never_a_number(self):
        self.write_loop(recorded_loop())
        card = self._text(self._render()["by_id"]["champ"])
        self.assertIn("NOT YET MEASURED", card)
        self.assertIn("not yet measured", card)
        self.assertIn("What would produce this number", card)
        # No percentage anywhere in the card. A 0.0% here would be a fabricated
        # measurement, and any other figure would be an invented one.
        self.assertNotRegex(card, r"[-+]?\d+\.\d+%")

    def test_the_headline_number_never_renders_without_its_anchor(self):
        """One element, both facts. There is no code path that emits the figure
        without the 'vs'."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle())
        card = self._text(self._render()["by_id"]["champ"])
        pct = f"+{self.bundle()['effect_fraction'] * 100:.1f}%"
        self.assertIn(pct, card)
        self.assertIn("vs the frozen production kernel", card)
        self.assertIn(V9_BRANCH, card)
        self.assertIn(self.prod_sha[:12], card)
        # ...and, matching the live-resolved production, it is tagged current.
        self.assertIn("current production — resolved live", card)
        # And the figure sits in front of its anchor, not somewhere else on the
        # page: the two are within one short span of each other.
        self.assertLess(card.index("vs the frozen") - card.index(pct), 40)

    def test_a_long_dead_measurement_is_dated_in_days_not_hours(self):
        """One age vocabulary across all three producers. This panel's envelope
        is weeks, so without a days branch a two-month-old measurement rendered
        `1416.0h ago` — a figure an operator has to do arithmetic on to discover
        is unusable."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle(age_s=59 * 86400))
        out = self._render()
        badge = out["text_by_id"]["champ-badgetxt"]
        self.assertTrue(badge.startswith("STALE"), badge)
        self.assertTrue(badge.endswith("d ago"), badge)
        self.assertIn("59.0d", badge)

    def test_a_superseded_measurement_is_marked_in_the_card(self):
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle(
            champion_commit=real_bundle()["champion"]["commit"]))
        out = self._render()
        card = self._text(out["by_id"]["champ"])
        self.assertIn("SUPERSEDED CHAMPION", card)
        self.assertIn(real_bundle()["champion"]["commit"][:12], card)
        self.assertIn(recorded_loop()["champion_head"][:12], card)
        # The badge names WHICH side is superseded — "SUPERSEDED" alone sends
        # an investigator to the wrong arm of the A/B.
        badge = out["text_by_id"]["champ-badgetxt"]
        self.assertTrue(badge.startswith("SUPERSEDED CHAMPION"), badge)
        self.assertNotIn("BASELINE", badge)

    def test_a_promotion_renders_SUPERSEDED_BASELINE_dated_with_both_commits(self):
        """Requirement 3, executed. The number was measured against a since-
        promoted production: still shown, visibly dated, both kernels named —
        and the supersession outranks the file's freshness in the badge (the
        lesson this panel already learned once for the champion side)."""
        self.write_loop(recorded_loop())
        old = self.prod_sha
        new = self.promote("production-consolidated-v10")
        self.write_champion(self.bundle(baseline_commit=old))
        out = self._render()
        badge = out["text_by_id"]["champ-badgetxt"]
        self.assertTrue(badge.startswith("SUPERSEDED BASELINE"), badge)
        self.assertNotIn("CHAMPION", badge)
        self.assertNotIn("fresh", badge)
        html = out["by_id"]["champ"]
        card = self._text(html)
        self.assertIn("SUPERSEDED BASELINE", card)
        self.assertIn(old[:12], card)
        self.assertIn(new[:12], card)
        self.assertIn("production-consolidated-v10", card)
        self.assertIn("superseded by a promotion", card)
        # The old number still shows — the measurement happened — but DATED
        # (amber), never in the fresh-gain colour.
        pct = f"+{self.bundle()['effect_fraction'] * 100:.1f}%"
        self.assertIn(pct, card)
        self.assertIn("ch-num dated", html)
        self.assertNotIn("ch-num pos", html)
        # And it is NOT tagged as the current production comparison.
        self.assertNotIn("current production — resolved live", card)

    def test_both_supersessions_render_distinguishably(self):
        """Requirement 4, executed on the page: both badges/states visible and
        tellable apart in one card."""
        self.write_loop(recorded_loop())
        old = self.prod_sha
        older_champ = real_bundle()["champion"]["commit"]
        new = self.promote("production-consolidated-v10")
        self.write_champion(self.bundle(
            baseline_commit=old, champion_commit=older_champ))
        out = self._render()
        badge = out["text_by_id"]["champ-badgetxt"]
        self.assertTrue(badge.startswith("SUPERSEDED BASELINE+CHAMPION"), badge)
        card = self._text(out["by_id"]["champ"])
        self.assertIn("SUPERSEDED BASELINE", card)
        self.assertIn("SUPERSEDED CHAMPION", card)
        self.assertIn(old[:12], card)
        self.assertIn(new[:12], card)
        self.assertIn(older_champ[:12], card)
        self.assertIn(recorded_loop()["champion_head"][:12], card)

    def test_an_unresolvable_production_renders_its_own_state_not_a_fallback(self):
        """Requirement 2, executed. No remembered sha, no crash: the champ card
        carries the explicit failure with its reason, and every other panel on
        the page still renders."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle())
        self.use_tree(self.root / "gone-tree")
        out = self._render()
        self.assertEqual(out["text_by_id"]["champ-badgetxt"],
                         "PRODUCTION UNRESOLVED")
        html = out["by_id"]["champ"]
        card = self._text(html)
        self.assertIn("CANNOT RESOLVE THE FROZEN PRODUCTION KERNEL", card)
        self.assertIn("not a git repository", card)
        self.assertIn("gone-tree", card)
        # No sha is invented for the missing anchor, and the number that IS
        # shown is dated, not painted as a verified-current gain.
        self.assertNotIn("0db32c06", card)
        self.assertIn("ch-num dated", html)
        # The rest of the page survives the failure.
        for pid in ("tiles", "recent", "gpu"):
            self.assertTrue(self._text(out["by_id"].get(pid, "")).strip(),
                            f"panel #{pid} went dark on a resolver failure")

    def test_the_champion_card_and_the_gate_card_cannot_be_confused(self):
        """THE defect, in one assertion. Both cards carry a large percentage;
        each must name its own anchor, its own producer and its own question."""
        self.write_loop(recorded_loop())
        self.use_real_bundle()
        self.write_champion(self.bundle())
        out = self._render()
        champ = self._text(out["by_id"]["champ"])
        gate = self._text(out["by_id"]["opgate"])
        self.assertIn("This is not the champion headline", gate)
        self.assertIn("different anchor", gate)
        # The gate card names ITS anchor beside ITS number.
        #
        # NOT keyed on the bare commit prefix: this bundle's champion BRANCH is
        # `ak/champion/llama-cpp-0db32c06e3e5`, so `0db32c06e3e5 in gate` is
        # satisfied by the branch name and stayed green through a mutation that
        # dropped the anchor entirely. The key has to be the claim, not a
        # substring that happens to co-occur with it.
        self.assertIn("+48.9%", gate)
        anchor = real_bundle()["production_anchor"]["commit"][:12]
        self.assertIn(f"the frozen production kernel {anchor}", gate)
        self.assertNotIn("an anchor this bundle does not name", gate)
        # ...and says which commit it measured. Its relationship to the current
        # champion is COMPUTED per render from git ancestry, never worded as a
        # constant: this line once asserted "a different tree" as prose and
        # kept rendering it after a reconciliation merge made the measured
        # commit a PARENT of the champion. In this fixture the champion tree is
        # deliberately unresolvable, so the honest verdict is "cannot say" —
        # the four computed verdicts are executed in GateScopeRelationship.
        self.assertIn(real_bundle()["champion"]["commit"][:12], gate)
        self.assertIn("cannot be established", gate)
        self.assertNotIn("a different tree", gate)
        # The champion card does not carry the gate bundle's figure at all.
        self.assertNotIn("+48.9%", champ)
        self.assertNotIn("48.9", champ)

    def test_the_gate_cards_measured_points_carry_BOTH_arms(self):
        """A `delta_pct` with no baseline beside it is the headline defect one
        level down. These are the rows the +48.9% is drawn from."""
        self.write_loop(recorded_loop())
        self.use_real_bundle()
        gate = self._text(self._render()["by_id"]["opgate"])
        points = [g for g in real_bundle()["gates"]
                  if g["gate"] == "dflash2_vs_production_serving_path"][0]["points"]
        for point in points:
            with self.subTest(in_flight=point["in_flight"]):
                self.assertIn(f"{point['champion_tps']:.3f}", gate)
                self.assertIn(f"{point['production_ceiling_tps']:.3f}", gate)
        self.assertIn("production ceiling", gate)
        self.assertIn("frozen anchor", gate)

    def test_a_stopped_run_renders_FINISHED_and_a_lost_one_renders_STALE(self):
        """Executed, not reasoned about: three renderings, three banners."""
        seen = {}
        self.write_loop(recorded_loop(age_s=10800, state="complete"))
        seen["finished"] = self._render()["by_id"]["banner"]
        self.write_loop(recorded_loop(age_s=10800, state="running"))
        seen["stale"] = self._render()["by_id"]["banner"]
        self.write_loop(recorded_loop(age_s=20, state="failed"))
        seen["failed"] = self._render()["by_id"]["banner"]
        self.write_loop(recorded_loop(age_s=20, state="running"))
        seen["live"] = self._render()["by_id"]["banner"]

        self.assertIn("FINISHED", self._text(seen["finished"]))
        self.assertIn("STOP sentinel", self._text(seen["finished"]))
        self.assertNotIn("STALE", self._text(seen["finished"]))
        self.assertIn("STALE", self._text(seen["stale"]))
        self.assertIn("FAILED", self._text(seen["failed"]))
        self.assertEqual(self._text(seen["live"]), "")
        self.assertEqual(len(set(seen.values())), 4,
                         "two run outcomes produced the same banner")

    #: Phrases that NAME a baseline. A percentage is acceptable only if one of
    #: these sits within `_ANCHOR_WINDOW` characters of it.
    _ANCHORING = ("of the ANCHOR", "of claim-held seconds", "of held",
                  "vs the frozen production kernel", "vs anchor at the time",
                  "Share of device time in the champion profile",
                  "vs that baseline", "the frozen production kernel",
                  "production's ceiling", "of the anchor", "production ceiling",
                  "frozen anchor", "marginal", "must not be summed",
                  # The producer's own reason text names the bar it was measured
                  # against ("did not clear the 1.188% noise floor"), and that IS
                  # a named baseline — it is not the page's to relabel.
                  "noise floor")
    _ANCHOR_WINDOW = 160

    @classmethod
    def _unanchored(cls, html: str, pid: str) -> list:
        """Every percentage in ``html`` with no baseline named near it.

        TABLES ARE READ BY COLUMN, so a cell's label is its ``<th>``, however
        many characters of kernel signature sit between them. A flat character
        window over the panel's text models a paragraph, not a table, and would
        report the hotspot Share column as unlabelled while a reader sees its
        header perfectly well.

        TILES ARE READ ONE AT A TIME, so each is scored ALONE. Scored together,
        the noise-floor tile's "of the ANCHOR's mean" sat within 160 characters
        of the GPU tile's percentage and exempted it — a mutation that stripped
        the GPU tile's denominator survived on its neighbour's label. Panels are
        exactly the wrong grain: the whole point is that each figure carries its
        own anchor.
        """
        offenders = []
        rest = html or ""
        for table in re.findall(r"<table.*?</table>", rest, re.S):
            rest = rest.replace(table, " ")
            head = cls._text("".join(re.findall(r"<thead.*?</thead>", table, re.S)))
            for row in re.findall(r"<tr.*?</tr>", table, re.S):
                text = cls._text(row)
                if not re.search(r"[-+]?\d+(?:\.\d+)?%", text):
                    continue
                if not any(p in head or p in text for p in cls._ANCHORING):
                    offenders.append(f"#{pid} table row with no labelled "
                                     f"baseline in its header or itself: {text[:200]}")
        segments = rest.split('<div class="tile">')
        for segment in segments:
            text = cls._text(segment)
            for match in re.finditer(r"[-+]?\d+(?:\.\d+)?%", text):
                lo = max(0, match.start() - cls._ANCHOR_WINDOW)
                window = text[lo:match.end() + cls._ANCHOR_WINDOW]
                if not any(phrase in window for phrase in cls._ANCHORING):
                    offenders.append(f"#{pid} {match.group()!r} in …{window}…")
        return offenders

    def test_every_percentage_on_the_page_states_what_it_is_a_percentage_of(self):
        """THE SWEEP the operator asked for. Every figure on the page must name
        its baseline; an unlabelled percentage is the defect that produced this
        revision, and it does not stop being one in a small tile.

        PER FIGURE, NOT PER PANEL. The first version of this test asked whether
        an anchoring phrase appeared ANYWHERE in the panel, and three separate
        mutations survived it: one labelled figure elsewhere in the same panel
        exempted every unlabelled one beside it. That is the same key-too-wide
        fault this whole page revision exists to correct, committed by its own
        test.
        """
        self.write_loop(recorded_loop())
        self.use_real_bundle()
        self.write_champion(self.bundle())
        out = self._render()
        offenders = []
        for pid in ("champ", "tiles", "recent", "gpu", "hot", "opgate", "know"):
            offenders += self._unanchored(out["by_id"].get(pid, ""), pid)
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_the_percentage_sweep_can_actually_find_something(self):
        """NON-VACUITY CONTROL. The sweep above passes trivially if it finds no
        percentages, or if every window is wide enough to catch some phrase by
        accident. So: prove it counts real figures, and prove it rejects one
        with nothing near it."""
        self.write_loop(recorded_loop())
        self.use_real_bundle()
        self.write_champion(self.bundle())
        out = self._render()
        found = sum(len(re.findall(r"[-+]?\d+(?:\.\d+)?%",
                                   self._text(out["by_id"].get(pid, ""))))
                    for pid in ("champ", "tiles", "recent", "gpu", "hot", "opgate"))
        self.assertGreater(found, 10, "the sweep found almost no percentages")
        # ...and it REJECTS an unanchored figure, in both of its two modes.
        self.assertTrue(self._unanchored(
            "<div>the champion got +12.5% and that is all we will say</div>", "x"))
        self.assertTrue(self._unanchored(
            "<table><thead><tr><th>Thing</th><th>Effect</th></tr></thead>"
            "<tbody><tr><td>a</td><td>+12.5%</td></tr></tbody></table>", "x"))
        # ...and ACCEPTS a labelled one, so it is not simply always-red.
        self.assertFalse(self._unanchored(
            "<table><thead><tr><th>Thing</th><th>Δ vs that baseline</th></tr>"
            "</thead><tbody><tr><td>a</td><td>+12.5%</td></tr></tbody></table>",
            "x"))

    def test_the_iteration_table_labels_its_effects_as_marginals(self):
        """The column header is the label a reader actually sees beside the
        number; a caption at the top of the panel is not within reach of a row
        thirty lines down."""
        self.write_loop(recorded_loop())
        recent = self._text(self._render()["by_id"]["recent"])
        self.assertIn("Effect vs anchor at the time", recent)
        self.assertIn("must not be summed", recent)

    def test_an_unreachable_hub_clears_all_three_producers(self):
        """A last successful champion render left on screen under a dead hub is
        an arbitrarily old reading presented as the current one."""
        self.write_loop(recorded_loop())
        # Driven through the harness's OWN entry-point argument rather than by
        # appending a bare call: an appended call runs at eval time, and the
        # harness then invokes `render` afterwards and paints the cleared card
        # straight back over it. That is not a hypothetical — it is what this
        # test did on its first run, and it passed nothing while looking green
        # in the other direction.
        js = self._page_js() + (
            "\nfunction __probeFetchFailure(){ renderFetchFailure('boom'); }\n")
        tmp = Path(tempfile.mkdtemp(prefix="champ-render-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "page.js").write_text(js, encoding="utf-8")
        (tmp / "payload.json").write_text(json.dumps(S.loop_payload()),
                                          encoding="utf-8")
        proc = subprocess.run(
            ["node", str(HARNESS), str(tmp / "page.js"), str(tmp / "payload.json"),
             "__probeFetchFailure"],
            capture_output=True, text=True, timeout=60)
        out = json.loads(proc.stdout)
        self.assertEqual(out["ran"], 1, f"the probe never ran: {out}")
        self.assertEqual(out["class_by_id"].get("champ-badge"), "badge malformed")
        self.assertEqual(out["text_by_id"].get("champ-badgetxt"), "UNKNOWN")
        self.assertIn("hub could not be reached", self._text(out["by_id"]["champ"]))

    def test_the_not_composable_lecture_is_off_the_card_but_still_served(self):
        """Operator note (a), 2026-08-31: the "cannot be added up" paragraph no
        longer renders on the headline card. The FIELD stays on the wire
        (pinned by `test_the_marginals_are_declared_uncomposable_on_every_
        reading`) and the recent-iterations table keeps its own
        must-not-be-summed caption — the rule lives where the marginals live."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle())
        out = self._render()
        card = self._text(out["by_id"]["champ"])
        self.assertNotIn("cannot be added up", card)
        self.assertNotIn("must never be summed", card)
        # The wire still carries the rationale, and the table still warns.
        self.assertIn("must never be summed", self.block()["not_composable"])
        self.assertIn("must not be summed", self._text(out["by_id"]["recent"]))

    def test_the_capabilities_live_in_a_collapsed_accordion(self):
        """Operator note (b), 2026-08-31: a `<details>` titled "Champion
        Capabilities", COLLAPSED by default (no `open` attribute), the entries
        unchanged inside it, and the evidence/run-record footer lines inside
        it too — and nowhere else on the card."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle(capabilities=[
            {"name": "FlashAttention2 on gfx90a", "evidence": "gate fa2_supported"},
            "iqk IQ4_XS coverage",
        ]))
        html = self._render()["by_id"]["champ"]
        m = re.search(r'<details class="ch-acc"([^>]*)>(.*?)</details>', html,
                      re.S)
        self.assertIsNotNone(m, "no capabilities accordion rendered")
        self.assertNotIn("open", m.group(1),
                         "the accordion must render collapsed by default")
        inner = m.group(2)
        self.assertIn("<summary>Champion Capabilities", inner)
        for entry in ("FlashAttention2 on gfx90a", "gate fa2_supported",
                      "iqk IQ4_XS coverage"):
            self.assertIn(entry, inner, "an entry fell out of the accordion")
        self.assertIn("evidence:", inner,
                      "the evidence footer did not move into the accordion")
        outside = html.replace(m.group(0), " ")
        self.assertNotIn("FlashAttention2 on gfx90a", outside,
                         "a capability entry also renders outside the accordion")
        self.assertNotIn("evidence:", outside,
                         "an evidence footer also renders outside the accordion")

    def test_the_unknown_capability_state_is_visible_on_the_collapsed_summary(self):
        """Collapsing must not hide "nobody has said" behind a heading that
        implies a list exists: UNKNOWN rides on the summary line itself."""
        self.write_loop(recorded_loop())
        self.write_champion(self.bundle())
        html = self._render()["by_id"]["champ"]
        m = re.search(r'<summary>(.*?)</summary>', html, re.S)
        self.assertIsNotNone(m)
        self.assertIn("UNKNOWN", m.group(1))

    def test_the_scope_lines_relationship_is_computed_not_worded(self):
        """Operator note (c), executed: four verdicts, four renderings, driven
        by git ancestry against a posing champion tree — never by prose."""
        self.write_loop(recorded_loop())
        path, parent, tip, divergent = self.lineage_repo()
        seen = {}
        for label, commit in (("tip", tip), ("ancestor", parent),
                              ("divergent", divergent)):
            self.use_bundle_with_commit(commit)
            seen[label] = self._text(self._render()["by_id"]["opgate"])
        os.environ[loop_status.CHAMPION_TREE_ENV] = str(self.root / "gone-champ")
        self.use_bundle_with_commit(parent)
        seen["unresolvable"] = self._text(self._render()["by_id"]["opgate"])

        self.assertIn("IS the current champion tip", seen["tip"])
        self.assertIn(tip[:12], seen["tip"])

        self.assertIn("its work is IN the current champion", seen["ancestor"])
        self.assertIn(tip[:12], seen["ancestor"])
        self.assertIn("same lineage", seen["ancestor"])
        self.assertNotIn("divergent tree", seen["ancestor"])

        self.assertIn("not in its history", seen["divergent"])
        self.assertIn("genuinely divergent tree", seen["divergent"])
        self.assertNotIn("IN the current champion", seen["divergent"])

        self.assertIn("cannot be established", seen["unresolvable"])
        self.assertNotIn("divergent tree", seen["unresolvable"])
        self.assertNotIn("IN the current champion", seen["unresolvable"])
        self.assertEqual(len(set(seen.values())), 4,
                         "two relationship states rendered identically")


class Wiring(unittest.TestCase):

    def test_the_registry_row_advertises_the_headline(self):
        rows = {e["id"]: e for e in json.loads(
            (REPO / "dashboard/registry.json").read_text(encoding="utf-8")
        )["dashboards"]}
        blurb = rows["autokernel-loop"]["blurb"]
        self.assertIn("champion headline", blurb)
        self.assertIn("frozen production kernel", blurb)

    def test_the_page_declares_the_headline_section_and_reads_it(self):
        html = PAGE.read_text(encoding="utf-8")
        for element in ("sec-champion", "champ", "champ-badge", "champ-badgetxt"):
            self.assertIn(f'id="{element}"', html, element)

    def test_the_headline_is_the_first_section_on_the_page(self):
        """Position is part of the ruling: nothing competes for this slot."""
        html = PAGE.read_text(encoding="utf-8")
        body = html[html.index("<main>"):]
        first = re.search(r'<section id="([a-z-]+)"', body)
        self.assertEqual(first.group(1), "sec-champion")
        self.assertLess(body.index('id="sec-champion"'),
                        body.index('id="sec-opgate"'),
                        "the operator-gated card outranks the champion headline")


if __name__ == "__main__":
    unittest.main()
