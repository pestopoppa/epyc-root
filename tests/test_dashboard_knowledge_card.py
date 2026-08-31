"""The accumulated-knowledge card: the loop's memory store as a FOURTH producer.

WHY THIS FILE EXISTS (operator, 2026-08-31)
-------------------------------------------
"I still don't see a card tracking autokernel's generated actionable knowledge
and hypotheses tested/confirmed/falsified." The loop's memory store
(`experiments.db`, sqlite) is that record; `dashboard/loop_status.py` reads it
READ-ONLY and folds it into `/api/loop`'s `knowledge` block, with its own
four-valued envelope from the db's mtime.

TWO STANDING RULES, BOTH EXECUTED HERE RATHER THAN REASONED ABOUT:

  * a MISSING count is not a ZERO — an absent or unreadable store renders the
    standard absent/malformed wording and NO numbers;
  * a measured null is a null AGAINST THE ANCHOR OF ITS DAY, never "falsified
    forever" — the split's wording says so.

WHERE THE FIXTURE COMES FROM, AND WHY IT MATTERS
------------------------------------------------
The fixture db is built from the REAL store's own schema (`sqlite_master.sql`,
read from the host db) and populated with ROWS COPIED from the real store —
never hand-invented columns. A fixture written from the reader's expectations
proves only that the reader is self-consistent; the fixture-invented-the-
spelling defect is the most-repeated one in this repo's history (the GPU panel
stayed dark through 41 passing tests exactly that way). Where the real store is
absent these tests SKIP rather than invent it. Every expected count below is
RECOMPUTED from the copied rows, not typed.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
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

#: The real memory store on this host — the READ-ONLY source of the fixture's
#: schema and rows. Never written, never invented.
REAL_DB = Path("/mnt/raid0/llm/autokernel/loop-memory/experiments.db")

#: How many rows per status to copy into the fixture. Small on purpose: the
#: expectations are recomputed from whatever was actually copied.
ROWS_PER_STATUS = 3


def _real_connection() -> sqlite3.Connection:
    if not REAL_DB.is_file():
        raise unittest.SkipTest(
            f"{REAL_DB} is not on this host; refusing to hand-invent the "
            "producer's schema — that defect class is the reason this fixture "
            "is built from the real store")
    return sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)


def real_schema_sql() -> list[str]:
    con = _real_connection()
    try:
        return [row[0] for row in con.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")]
    finally:
        con.close()


def copy_rows() -> tuple[list[str], list[tuple]]:
    """(column names, rows) copied verbatim from the real store — a spread of
    every status the producer has ever written, newest first."""
    con = _real_connection()
    try:
        columns = [r[1] for r in con.execute("PRAGMA table_info(experiments)")]
        statuses = [r[0] for r in con.execute(
            "SELECT DISTINCT status FROM experiments")]
        rows: list[tuple] = []
        for status in statuses:
            rows.extend(con.execute(
                "SELECT * FROM experiments WHERE status = ? "
                "ORDER BY recorded_at DESC LIMIT ?",
                (status, ROWS_PER_STATUS)).fetchall())
        return columns, rows
    finally:
        con.close()


def build_fixture(path: Path, rows: list[tuple] | None = None) -> list[tuple]:
    """A fixture db carrying the REAL schema and (by default) copied real rows."""
    columns, copied = copy_rows()
    if rows is None:
        rows = copied
    con = sqlite3.connect(path)
    try:
        for sql in real_schema_sql():
            con.execute(sql)
        con.executemany(
            f"INSERT INTO experiments VALUES ({', '.join('?' * len(columns))})",
            rows)
        con.commit()
    finally:
        con.close()
    return rows


class _Store(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="knowledge-card-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        prior = os.environ.get(loop_status.STORE_ROOT_ENV)
        os.environ[loop_status.STORE_ROOT_ENV] = str(self.root)
        self.addCleanup(self._restore, loop_status.STORE_ROOT_ENV, prior)

    @staticmethod
    def _restore(name: str, prior: str | None) -> None:
        if prior is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = prior

    @property
    def db(self) -> Path:
        return self.root / loop_status.KNOWLEDGE_DB_FILENAME

    def snap(self) -> dict:
        return loop_status.knowledge_snapshot(self.root)

    def write_status(self, **over) -> dict:
        """A loop status body in the store root — the VERBATIM recording of the
        real producer (the ledger joins against its hotspots and epoch),
        re-dated fresh, with per-test overrides on top."""
        from datetime import datetime, timezone
        body = json.loads(SAMPLE.read_text(encoding="utf-8"))
        body["generated_at"] = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z")
        body.update(over)
        (self.root / loop_status.STATUS_FILENAME).write_text(
            json.dumps(body), encoding="utf-8")
        return body

    @staticmethod
    def columns_of(db: Path) -> list:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            return [r[1] for r in con.execute("PRAGMA table_info(experiments)")]
        finally:
            con.close()

    @staticmethod
    def find_mechanism(ledger: dict, mechanism_id: str) -> dict | None:
        """Locate one mechanism entry wherever the ledger put it."""
        for group in ledger.get("agenda") or []:
            for entry in group["mechanisms"]:
                if entry["mechanism_id"] == mechanism_id:
                    return entry
        for key in ("confirmed", "null", "refused"):
            for entry in (ledger.get("unmapped") or {}).get(key, {}).get(
                    "entries", []):
                if entry["mechanism_id"] == mechanism_id:
                    return entry
        return None


class Fixture(_Store):
    def test_the_fixture_carries_the_real_stores_schema(self):
        """NON-VACUITY: the fixture's schema is byte-identical to the real
        store's, so a reader that agrees with the fixture agrees with the
        producer — the opposite of the invented-spelling defect."""
        build_fixture(self.db)
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        try:
            got = sorted(r[0] for r in con.execute(
                "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"))
        finally:
            con.close()
        self.assertEqual(got, sorted(real_schema_sql()))

    def test_the_fixture_actually_holds_rows_of_more_than_one_status(self):
        rows = build_fixture(self.db)
        self.assertGreater(len(rows), 3)
        # The status column's POSITION is read from the schema, not assumed.
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        try:
            columns = [r[1] for r in con.execute("PRAGMA table_info(experiments)")]
        finally:
            con.close()
        statuses = {row[columns.index("status")] for row in rows}
        self.assertGreater(len(statuses), 2, statuses)


class Reader(_Store):
    def _expected(self, rows: list[tuple]) -> dict:
        """Every expectation recomputed from the copied rows themselves."""
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        try:
            columns = [r[1] for r in con.execute("PRAGMA table_info(experiments)")]
        finally:
            con.close()
        s, m = columns.index("status"), columns.index("mechanism_id")
        statuses = Counter(row[s] for row in rows)
        mechanisms = Counter(row[m] for row in rows if row[m])
        return {"attempts": len(rows), "statuses": dict(statuses),
                "distinct": len(mechanisms),
                "revisited": sum(1 for n in mechanisms.values() if n >= 2)}

    def test_the_folds_match_the_rows_copied_from_the_real_store(self):
        rows = build_fixture(self.db)
        want = self._expected(rows)
        got = self.snap()
        self.assertIsNone(got["reader_error"])
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_FRESH)
        self.assertEqual(got["attempts"], want["attempts"])
        self.assertEqual(got["dispositions"], want["statuses"])
        self.assertEqual(got["mechanisms"],
                         {"distinct": want["distinct"],
                          "revisited": want["revisited"]})

    def test_the_groups_enumerate_every_status_and_sum_to_the_attempts(self):
        """Nothing hidden: the four primary dispositions plus a no-verdict
        bucket that NAMES its members must account for every row."""
        rows = build_fixture(self.db)
        want = self._expected(rows)
        groups = self.snap()["groups"]
        primary = sum(groups[k] for k in
                      loop_status.KNOWLEDGE_PRIMARY_DISPOSITIONS)
        self.assertEqual(primary + groups["no_verdict"]["total"],
                         want["attempts"])
        for status, count in want["statuses"].items():
            if status in loop_status.KNOWLEDGE_PRIMARY_DISPOSITIONS:
                self.assertEqual(groups[status], count, status)
            else:
                self.assertEqual(groups["no_verdict"]["by_status"][status],
                                 count, status)

    def test_recent_kept_names_the_newest_keeps_with_their_effects(self):
        rows = build_fixture(self.db)
        got = self.snap()["recent_kept"]
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        try:
            want = con.execute(
                "SELECT mechanism_id, effect_fraction, recorded_at "
                "FROM experiments WHERE status='kept' "
                "ORDER BY recorded_at DESC LIMIT ?",
                (loop_status.KNOWLEDGE_RECENT_KEPT,)).fetchall()
        finally:
            con.close()
        self.assertEqual(
            [(g["mechanism_id"], g["effect_fraction"], g["recorded_at"])
             for g in got], want)

    def test_absent_is_none_on_every_count_never_zero(self):
        """THE rule. `0 attempts` over a missing store claims the program has
        tried nothing — a fabricated measurement."""
        got = self.snap()
        self.assertFalse(got["artifact_present"])
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_ABSENT)
        for field in ("attempts", "mechanisms", "dispositions", "groups",
                      "recent_kept", "recorded_window"):
            self.assertIsNone(got[field], f"{field} rendered as a value "
                              "over a store that does not exist")
        self.assertIn("not a zero", got["absence_means"])

    def test_the_reader_cannot_conjure_the_store_into_existence(self):
        """`mode=ro` and the exists() guard: a bare sqlite3.connect() CREATES
        an empty db at the path — a reader that leaves one behind turns every
        later absent reading into malformed."""
        self.snap()
        self.assertFalse(self.db.exists(),
                         "reading an absent store created a file")

    def test_a_garbage_file_is_malformed_never_absent_and_never_zeros(self):
        self.db.write_bytes(b"this is not a sqlite database at all")
        got = self.snap()
        self.assertTrue(got["artifact_present"])
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_MALFORMED)
        self.assertIn("could not be read", got["reader_error"])
        self.assertIsNone(got["attempts"])
        self.assertIsNone(got["groups"])

    def test_a_db_without_the_experiments_table_is_malformed(self):
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE something_else (x)")
        con.commit()
        con.close()
        got = self.snap()
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_MALFORMED)
        self.assertIsNone(got["attempts"])

    def test_stale_is_dated_knowledge_not_an_accusation_and_keeps_its_counts(self):
        rows = build_fixture(self.db)
        old = 3 * loop_status.KNOWLEDGE_STALE_AFTER_S
        os.utime(self.db, (self.db.stat().st_mtime - old,
                           self.db.stat().st_mtime - old))
        got = self.snap()
        self.assertEqual(got["freshness"]["state"], loop_status.STATE_STALE)
        self.assertIn("complete as of the store's last write",
                      got["freshness"]["detail"])
        # A stale ACCUMULATION is still the accumulated record.
        self.assertEqual(got["attempts"], len(rows))

    def test_the_four_states_use_the_pages_shared_vocabulary(self):
        seen = {}
        seen["absent"] = self.snap()["freshness"]["state"]
        self.db.write_bytes(b"garbage")
        seen["malformed"] = self.snap()["freshness"]["state"]
        self.db.unlink()
        build_fixture(self.db)
        seen["fresh"] = self.snap()["freshness"]["state"]
        past = self.db.stat().st_mtime - 2 * loop_status.KNOWLEDGE_STALE_AFTER_S
        os.utime(self.db, (past, past))
        seen["stale"] = self.snap()["freshness"]["state"]
        self.assertEqual(seen, {"absent": "absent", "malformed": "malformed",
                                "fresh": "fresh", "stale": "stale"})
        for state in seen.values():
            self.assertIn(state, loop_status.STATES)

    def test_the_block_reaches_api_loop_through_the_injectable_root(self):
        rows = build_fixture(self.db)
        payload = S.loop_payload()
        self.assertIn("knowledge", payload)
        self.assertEqual(payload["knowledge"]["attempts"], len(rows))
        self.assertEqual(payload["knowledge"]["evidence"], str(self.db))

    def test_the_real_store_reads_clean_end_to_end(self):
        """THE integration test, read-only against the host store."""
        if not REAL_DB.is_file():
            self.skipTest(f"{REAL_DB} is not on this host")
        got = loop_status.knowledge_snapshot(REAL_DB.parent)
        self.assertIsNone(got["reader_error"], got["reader_error"])
        self.assertIn(got["freshness"]["state"],
                      (loop_status.STATE_FRESH, loop_status.STATE_STALE))
        self.assertGreater(got["attempts"], 0)
        groups = got["groups"]
        self.assertEqual(sum(groups[k] for k in
                             loop_status.KNOWLEDGE_PRIMARY_DISPOSITIONS)
                         + groups["no_verdict"]["total"], got["attempts"])


# --------------------------------------------------------------------------- #
# The hypothesis ledger — the hotspot walk (operator refinement, 2026-08-31:
# "this doesn't tell me how the planner is thinking about tackling these
# profiling bottlenecks" — the profile is the agenda and the card walks it)
# --------------------------------------------------------------------------- #
#: The live status file — the source of REAL profiled signatures for the
#: match-rule tests. The matching rule was tuned against these exact strings;
#: a test that invents its own signatures proves only self-consistency.
REAL_STATUS = Path("/mnt/raid0/llm/autokernel/loop-memory/loop-status.json")


class Ledger(_Store):

    def _distinct_mechanisms(self, rows: list) -> set:
        cols = self.columns_of(self.db)
        m = cols.index("mechanism_id")
        return {row[m] for row in rows if row[m]}

    def test_every_mechanism_lands_exactly_once_walk_or_remainder(self):
        """CONSERVATION, the non-vacuity property of the whole join: every
        mechanism in the store appears exactly once — under a hotspot, in the
        remainder, or in the counted no-verdict rest. A join that drops or
        double-lists a mechanism fabricates or erases an experiment."""
        rows = build_fixture(self.db)
        self.write_status()
        led = self.snap()["ledger"]
        listed = [e["mechanism_id"] for g in led["agenda"]
                  for e in g["mechanisms"]]
        un = led["unmapped"]
        for key in ("confirmed", "null", "refused"):
            listed += [e["mechanism_id"] for e in un[key]["entries"]]
        self.assertEqual(len(listed), len(set(listed)),
                         "a mechanism is listed more than once")
        self.assertEqual(
            len(set(listed)) + un["no_verdict_mechanisms"],
            len(self._distinct_mechanisms(rows)))
        cols = self.columns_of(self.db)
        m = cols.index("mechanism_id")
        self.assertEqual(un["unattributed_rows"],
                         sum(1 for row in rows if not row[m]))

    def test_the_mapping_is_true_of_the_rows_not_just_self_consistent(self):
        """Every mechanism the ledger placed under a hotspot must ACTUALLY
        target it, checked with a test-local normalizer against the copied
        rows — never by re-running the module's own matcher."""
        rows = build_fixture(self.db)
        self.write_status()
        cols = self.columns_of(self.db)
        m, t = cols.index("mechanism_id"), cols.index("target_symbol")
        symbols = {}
        for row in rows:
            if row[m]:
                symbols.setdefault(row[m], set()).add(row[t] or "")

        def base(name):  # independent spelling of the normalization
            name = re.sub(r"^void\s+", "", str(name or ""))
            name = re.split(r"[<(]", name)[0].strip()
            return name.split("::")[-1]

        led = self.snap()["ledger"]
        checked = 0
        for group in led["agenda"]:
            for entry in group["mechanisms"]:
                bases = {base(s) for s in symbols.get(entry["mechanism_id"],
                                                      set()) if s}
                self.assertTrue(
                    any(b and (b in group["kernel"] or group["kernel"] in b)
                        for b in bases),
                    f"{entry['mechanism_id']} (targets {bases}) filed under "
                    f"{group['kernel']}")
                checked += 1
        if not any(g["mechanisms"] for g in led["agenda"]):
            self.skipTest("no copied row targets a sample hotspot — nothing "
                          "to check on this store")
        self.assertGreater(checked, 0)

    def test_the_match_rule_holds_on_the_live_profiles_own_signatures(self):
        """The rule, exercised against REAL signatures from the live status
        file (skips where absent): the dispatcher and wrapper symbols the
        planner actually writes must join the mul_mat_vec_q variants, exact
        names must join exactly, and inlined work that shares no name must
        honestly FAIL to join."""
        if not REAL_STATUS.is_file():
            self.skipTest(f"{REAL_STATUS} is not on this host")
        body = json.loads(REAL_STATUS.read_text(encoding="utf-8"))
        sigs = [h.get("signature") for h in body.get("hotspots") or []]
        if not sigs:
            self.skipTest("the live status carries no hotspot table right now")
        bases = {loop_status._kernel_base(s) for s in sigs}
        if "mul_mat_vec_q" in bases:
            for symbol in ("mul_mat_vec_q_switch_ncols_dst",
                           "ggml_cuda_mul_mat_vec_q"):
                self.assertTrue(loop_status._bases_match(
                    loop_status._kernel_base(symbol), "mul_mat_vec_q"), symbol)
            self.assertFalse(loop_status._bases_match(
                loop_status._kernel_base("vec_dot_q4_K_q8_1_impl_vmmq"),
                "mul_mat_vec_q"))
        for exact in ("quantize_q8_1_1d", "rms_norm_f32", "rope_neox"):
            if exact in bases:
                self.assertTrue(loop_status._bases_match(
                    loop_status._kernel_base(exact), exact))
        # Template noise really is stripped from a real templated signature.
        templated = next((s for s in sigs if "<" in s), None)
        if templated:
            self.assertNotIn("<", loop_status._kernel_base(templated))

    def test_an_untried_hotspot_is_flagged_with_its_share(self):
        """THE BLIND SPOT: a hotspot no row ever targeted must say so, share
        intact — that line is the actionable insight this card exists for."""
        rows = build_fixture(self.db)
        signature = ("void a_kernel_no_row_targets<float, 2>(float const*, "
                     "float*, int)")
        self.write_status(hotspots=[{
            "signature": signature, "share_of_device_time": 0.164,
            "calls": 7, "total_duration_ns": 1}])
        cols = self.columns_of(self.db)
        t = cols.index("target_symbol")
        self.assertTrue(all("a_kernel_no_row_targets" not in str(r[t] or "")
                            for r in rows))
        led = self.snap()["ledger"]
        self.assertEqual(len(led["agenda"]), 1)
        entry = led["agenda"][0]
        self.assertTrue(entry["untried"])
        self.assertEqual(entry["kernel"], "a_kernel_no_row_targets")
        self.assertEqual(entry["share_of_device_time"], 0.164)
        self.assertEqual(entry["mechanisms"], [])

    def test_variants_of_one_kernel_fold_into_one_agenda_entry(self):
        """The sample records two mul_mat_vec_q template variants; a planner
        sees one kernel. Shares add, variants stay enumerated inside."""
        build_fixture(self.db)
        body = self.write_status()
        raw = body["hotspots"]
        led = self.snap()["ledger"]
        entry = next(g for g in led["agenda"]
                     if g["kernel"] == "mul_mat_vec_q")
        self.assertEqual(len(entry["variants"]), len(raw))
        self.assertAlmostEqual(
            entry["share_of_device_time"],
            sum(h["share_of_device_time"] for h in raw))
        self.assertEqual(entry["calls"], sum(h["calls"] for h in raw))

    def test_cross_epoch_is_computed_against_the_live_epoch(self):
        """A kept effect from another epoch is marked; the same row read under
        its OWN epoch is not. Executed both ways so the marker cannot be a
        constant."""
        rows = build_fixture(self.db)
        cols = self.columns_of(self.db)
        s, m, e = (cols.index("status"), cols.index("mechanism_id"),
                   cols.index("epoch_sha256"))
        kept = next((r for r in rows if r[s] == "kept" and r[m] and r[e]),
                    None)
        if kept is None:
            self.skipTest("the copied rows carry no kept row to re-epoch")
        self.write_status(epoch_sha256=kept[e])
        entry = self.find_mechanism(self.snap()["ledger"], kept[m])
        self.assertIsNotNone(entry)
        self.assertIsNotNone(entry["best_effect"])
        self.assertFalse(entry["best_effect"]["cross_epoch"])
        self.write_status(epoch_sha256="e" * 64)
        entry = self.find_mechanism(self.snap()["ledger"], kept[m])
        self.assertTrue(entry["best_effect"]["cross_epoch"])
        self.assertTrue(entry["cross_epoch"])

    def test_no_status_body_walks_no_agenda_and_drops_nothing(self):
        """An unreadable loop status must not sink the ledger OR invent an
        agenda: no hotspots, the stated reason, and full conservation into
        the remainder."""
        rows = build_fixture(self.db)
        led = self.snap()["ledger"]
        self.assertFalse(led["hotspots_reported"])
        self.assertEqual(led["agenda"], [])
        self.assertIn("no agenda to walk", led["hotspots_unavailable_reason"])
        un = led["unmapped"]
        listed = sum(un[k]["total"] for k in ("confirmed", "null", "refused"))
        self.assertEqual(listed + un["no_verdict_mechanisms"],
                         len(self._distinct_mechanisms(rows)))

    def test_agenda_groups_lead_with_kept_then_null_then_refused(self):
        """The walk leads with what worked. Executed on the folded order, not
        the styling."""
        rows = build_fixture(self.db)
        self.write_status()
        led = self.snap()["ledger"]

        def rank(entry):
            if entry["kept"]:
                return 0
            if entry["measured_null"]:
                return 1
            if entry["refused_at_formation"]:
                return 2
            return 3

        for group in led["agenda"]:
            ranks = [rank(e) for e in group["mechanisms"]]
            self.assertEqual(ranks, sorted(ranks), group["kernel"])

    def test_the_inbox_is_joined_and_never_created(self):
        """Reading an absent inbox must not conjure it (the sibling rule to
        the sqlite mode=ro guard); a seed naming a walked kernel is queued on
        that kernel's agenda entry."""
        build_fixture(self.db)
        self.write_status()
        led = self.snap()["ledger"]
        self.assertFalse(led["inbox"]["present"])
        self.assertFalse((self.root / "inbox").exists(),
                         "reading an absent inbox created it")
        inbox = self.root / "inbox"
        inbox.mkdir()
        (inbox / "07-mmvq-idea.md").write_text(
            "# Split mul_mat_vec_q accumulators <b>across</b> waves\n\nbody",
            encoding="utf-8")
        (inbox / "08-unrelated.md").write_text(
            "# Something about the sampler\n", encoding="utf-8")
        led = self.snap()["ledger"]
        self.assertTrue(led["inbox"]["present"])
        by_file = {s["file"]: s for s in led["inbox"]["seeds"]}
        self.assertEqual(by_file["07-mmvq-idea.md"]["matched_kernels"],
                         ["mul_mat_vec_q"])
        self.assertEqual(by_file["08-unrelated.md"]["matched_kernels"], [])
        group = next(g for g in led["agenda"]
                     if g["kernel"] == "mul_mat_vec_q")
        self.assertIn({"file": "07-mmvq-idea.md",
                       "title": "Split mul_mat_vec_q accumulators <b>across</b> waves"},
                      group["queued_seeds"])

    def test_in_flight_mechanisms_ride_on_their_hotspots_entry(self):
        """The planner's live posture: a mechanism in the status file's recent
        list that maps to a walked kernel is named on that kernel."""
        rows = build_fixture(self.db)
        cols = self.columns_of(self.db)
        m, t = cols.index("mechanism_id"), cols.index("target_symbol")
        target = next((r for r in rows if r[m]
                       and "mul_mat_vec_q" in str(r[t] or "")), None)
        if target is None:
            self.skipTest("no copied row targets mul_mat_vec_q on this store")
        self.write_status(recent=[{"mechanism_id": target[m],
                                   "status": "measured_null",
                                   "effect_fraction": None, "reason": "x"}])
        led = self.snap()["ledger"]
        group = next(g for g in led["agenda"]
                     if g["kernel"] == "mul_mat_vec_q")
        self.assertIn(target[m], group["tried_this_run"])
        self.assertIn(target[m], led["active_this_run"])

    def test_a_locked_read_is_retried_once_then_honest(self):
        """The store is written continuously by a LIVE run; a mid-read lock is
        scheduling. One retry, then the malformed verdict — never a crash and
        never a page of zeros."""
        rows = build_fixture(self.db)
        real_once = loop_status._read_knowledge_once
        calls = {"n": 0}

        def flaky(path):
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            return real_once(path)

        loop_status._read_knowledge_once = flaky
        try:
            got = loop_status.read_knowledge(self.root)
        finally:
            loop_status._read_knowledge_once = real_once
        self.assertEqual(calls["n"], 2)
        self.assertIsNone(got["reader_error"])
        self.assertEqual(got["body"]["attempts"], len(rows))

        calls["n"] = 0

        def always_locked(path):
            calls["n"] += 1
            raise sqlite3.OperationalError("database is locked")

        loop_status._read_knowledge_once = always_locked
        try:
            got = loop_status.read_knowledge(self.root)
        finally:
            loop_status._read_knowledge_once = real_once
        self.assertEqual(calls["n"], 2, "retried more than once")
        self.assertIn("locked", got["reader_error"])
        self.assertIsNone(got["body"])

    def test_absent_store_serves_no_ledger(self):
        """A ledger of zero levers over a missing store would claim the
        planner has thought about nothing."""
        self.write_status()
        self.assertIsNone(self.snap()["ledger"])

    def test_group_summaries_recompute_from_their_own_entries(self):
        """The 'N mechanisms tried; best +x%' line is a fold; each of its
        numbers is recomputed here so a transposed or hardcoded one fails."""
        build_fixture(self.db)
        self.write_status()
        led = self.snap()["ledger"]
        checked_best = 0
        for group in led["agenda"]:
            s = group["summary"]
            mechs = group["mechanisms"]
            self.assertEqual(s["mechanisms_tried"], len(mechs))
            self.assertEqual(s["attempts"], sum(m["attempts"] for m in mechs))
            self.assertEqual(s["kept_mechanisms"],
                             len([m for m in mechs if m["kept"]]))
            best = [m["best_effect"]["fraction"] for m in mechs
                    if m["kept"] and m["best_effect"]]
            if best:
                self.assertEqual(s["best_effect_fraction"], max(best))
                checked_best += 1
            else:
                self.assertIsNone(s["best_effect_fraction"])
        if not any(g["mechanisms"] for g in led["agenda"]):
            self.skipTest("no copied row targets a sample hotspot")
        self.assertGreaterEqual(checked_best, 0)

    def test_best_effect_is_the_maximum_of_the_mechanisms_kept_rows(self):
        """Forced two kept rows on ONE mechanism with different effects, so a
        min-for-max flip cannot hide behind single-row mechanisms."""
        columns, rows = copy_rows()
        idx = {name: i for i, name in enumerate(columns)}
        kept = next((r for r in rows if r[idx["status"]] == "kept"
                     and r[idx["mechanism_id"]]
                     and r[idx["effect_fraction"]] is not None), None)
        if kept is None:
            self.skipTest("the copied rows carry no kept row")
        weaker = list(kept)
        weaker[idx["attempt_id"]] = "a" * 64
        weaker[idx["effect_fraction"]] = kept[idx["effect_fraction"]] / 2.0
        weaker[idx["recorded_at"]] = "2099-01-03T00:00:00Z"
        build_fixture(self.db, rows=rows + [tuple(weaker)])
        self.write_status()
        entry = self.find_mechanism(self.snap()["ledger"],
                                    kept[idx["mechanism_id"]])
        self.assertIsNotNone(entry)
        self.assertEqual(entry["kept"], 2)
        self.assertEqual(entry["best_effect"]["fraction"],
                         kept[idx["effect_fraction"]])


# --------------------------------------------------------------------------- #
# The rendered card
# --------------------------------------------------------------------------- #
@unittest.skipIf(shutil.which("node") is None, "node is not installed")
class Rendering(_Store):
    """Every state EXECUTED on the real page JS — absent, malformed, stale,
    fresh — plus the anchoring rule for the effects it names."""

    def setUp(self) -> None:
        super().setUp()
        # A readable loop body so the rest of the page renders around the card.
        body = json.loads(SAMPLE.read_text(encoding="utf-8"))
        from datetime import datetime, timezone
        body["generated_at"] = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z")
        (self.root / loop_status.STATUS_FILENAME).write_text(
            json.dumps(body), encoding="utf-8")

    def _render(self) -> dict:
        blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                            PAGE.read_text(encoding="utf-8"), re.S)
        self.assertTrue(blocks)
        tmp = Path(tempfile.mkdtemp(prefix="knowledge-render-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "page.js").write_text("\n".join(blocks), encoding="utf-8")
        (tmp / "payload.json").write_text(json.dumps(S.loop_payload()),
                                          encoding="utf-8")
        proc = subprocess.run(
            ["node", str(HARNESS), str(tmp / "page.js"),
             str(tmp / "payload.json")],
            capture_output=True, text=True, timeout=60)
        self.assertTrue(proc.stdout.strip(), proc.stderr[:400])
        out = json.loads(proc.stdout)
        self.assertEqual(out["threw"], [])
        self.assertIn("know", out["by_id"])
        return out

    @staticmethod
    def _text(html: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()

    def test_a_real_shaped_store_renders_the_header_line_and_the_walk(self):
        rows = build_fixture(self.db)
        out = self._render()
        html = out["by_id"]["know"]
        card = self._text(html)
        # The compact header line: counts are attendance, one line, all there.
        self.assertIn("attempts ever", card)
        self.assertIn(str(len(rows)), card)
        self.assertIn("mechanisms explored", card)
        self.assertIn("revisited", card)
        self.assertIn("measured_null", card)
        self.assertIn("anchor of their day", card)
        self.assertIn("not falsified forever", card)
        self.assertIn("refused_at_formation", card)
        self.assertIn("before costing any device time", card)
        self.assertIn("no scientific verdict", card)
        # The hotspot walk: the sample's profile is mul_mat_vec_q variants,
        # rendered as ONE agenda entry with its share beside its baseline.
        self.assertIn("mul_mat_vec_q", card)
        self.assertIn("of device time in the champion profile", card)
        # The remainder exists and is a <details> (collapsed ≠ removed).
        self.assertIn("Beyond the current profile", card)
        self.assertRegex(html, r'<details class="kn-rem"(?![^>]*open)')
        self.assertTrue(out["class_by_id"]["know-badge"].endswith("fresh"),
                        out["class_by_id"]["know-badge"])

    def test_every_copied_mechanism_renders_somewhere_on_the_card(self):
        """Conservation at RENDER level: agenda, remainder or nested details —
        collapsed is fine, absent is not."""
        rows = build_fixture(self.db)
        cols = self.columns_of(self.db)
        m = cols.index("mechanism_id")
        html = self._render()["by_id"]["know"]
        for mech in {row[m] for row in rows if row[m]}:
            entry = self.find_mechanism(
                loop_status.knowledge_snapshot(self.root)["ledger"], mech)
            if entry is None:
                continue  # counted no-verdict rest — counted, not listed
            self.assertIn(mech, html, f"{mech} fell off the rendered card")

    def test_every_effect_on_the_card_is_anchored(self):
        rows = build_fixture(self.db)
        out = self._render()
        card = self._text(out["by_id"]["know"])
        # Every percentage on the card sits beside its baseline; an unlabelled
        # percentage is the page's founding defect. The ledger's anchors are
        # "the anchor of its/their day" (marginals) and the profile share's
        # "of device time in the champion profile".
        found = 0
        for match in re.finditer(r"[-+]?\d+(?:\.\d+)?%", card):
            found += 1
            window = card[max(0, match.start() - 160):match.end() + 160]
            self.assertTrue(
                "anchor of its day" in window or "anchor of their day" in window
                or "of device time in the champion profile" in window,
                f"unanchored figure {match.group()!r} in …{window}…")
        self.assertGreater(found, 0, "the sweep found no percentages at all")

    def test_untrusted_statements_render_escaped_everywhere(self):
        """Statements and refusal reasons are LLM output. Metacharacters in
        the fixture prove the escaping — in the row text AND in the title
        attribute that carries the full statement."""
        columns, rows = copy_rows()
        template = list(rows[0])
        idx = {name: i for i, name in enumerate(columns)}
        payload = ('<script>alert(1)</script> beats the "anchor" '
                   "& friends' <img src=x onerror=steal()>")
        hostile = template[:]
        hostile[idx["attempt_id"]] = "f" * 64
        hostile[idx["mechanism_id"]] = "akm-xss-probe"
        hostile[idx["target_symbol"]] = "mul_mat_vec_q_switch_ncols_dst"
        hostile[idx["status"]] = "kept"
        hostile[idx["effect_fraction"]] = 0.0123
        hostile[idx["statement"]] = payload
        hostile[idx["refusal_reason"]] = None
        hostile[idx["recorded_at"]] = "2099-01-01T00:00:00Z"
        hostile2 = template[:]
        hostile2[idx["attempt_id"]] = "e" * 64
        hostile2[idx["mechanism_id"]] = "akm-xss-refused"
        hostile2[idx["target_symbol"]] = "mul_mat_vec_q_switch_ncols_dst"
        hostile2[idx["status"]] = "refused_at_formation"
        hostile2[idx["effect_fraction"]] = None
        hostile2[idx["statement"]] = 'x" onmouseover="alert(2)'
        hostile2[idx["refusal_reason"]] = "<b>critic</b> says \"no\" & <i>why</i>"
        hostile2[idx["recorded_at"]] = "2099-01-02T00:00:00Z"
        build_fixture(self.db, rows=rows + [tuple(hostile), tuple(hostile2)])
        html = self._render()["by_id"]["know"]
        self.assertIn("akm-xss-probe", html)
        self.assertIn("akm-xss-refused", html)
        self.assertNotIn("<script>alert(1)", html)
        self.assertNotIn("<img src=x", html)
        self.assertNotIn('x" onmouseover=', html,
                         "an attribute-breaking quote survived into markup")
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("x&quot; onmouseover=&quot;alert(2)", html)
        self.assertNotIn("<b>critic</b>", html)
        self.assertIn("&lt;b&gt;critic&lt;/b&gt;", html)

    def test_a_cross_epoch_keep_renders_the_not_comparable_caveat(self):
        """A kept magnitude from an earlier epoch must carry its caveat on the
        page, and the SAME store under the keep's own epoch must not."""
        rows = build_fixture(self.db)
        cols = self.columns_of(self.db)
        s, e, f = (cols.index("status"), cols.index("epoch_sha256"),
                   cols.index("effect_fraction"))
        kept = next((r for r in rows if r[s] == "kept" and r[e]
                     and r[f] is not None), None)
        if kept is None:
            self.skipTest("the copied rows carry no dated keep")
        status = json.loads(
            (self.root / loop_status.STATUS_FILENAME).read_text())
        status["epoch_sha256"] = "d" * 64
        (self.root / loop_status.STATUS_FILENAME).write_text(
            json.dumps(status))
        html = self._render()["by_id"]["know"]
        card = self._text(html)
        self.assertIn("earlier epoch — not comparable to current numbers",
                      card)
        # ...and ON THE ROW ITSELF, not only in a group summary that happens
        # to repeat the phrase (the summary's copy is how the first version of
        # this test passed over a silenced row caveat — a key too wide).
        mech = kept[cols.index("mechanism_id")]
        row_divs = [d for d in re.findall(r'<div class="ag-mech">.*?</div>',
                                          html, re.S) if mech and mech in d]
        self.assertTrue(row_divs, f"no rendered ledger row for {mech}")
        self.assertTrue(
            any("earlier epoch — not comparable to current numbers" in d
                for d in row_divs),
            "the kept row's own caveat is missing (only a summary carries it)")
        status["epoch_sha256"] = kept[e]
        (self.root / loop_status.STATUS_FILENAME).write_text(
            json.dumps(status))
        card2 = self._text(self._render()["by_id"]["know"])
        self.assertNotEqual(card, card2,
                            "re-epoching the status changed nothing rendered")

    def test_the_header_counts_are_the_folds_not_a_transposition(self):
        """The header line's numbers are pinned against the recomputed folds,
        with kept forced != measured_null so a transposition cannot alias."""
        columns, rows = copy_rows()
        idx = {name: i for i, name in enumerate(columns)}
        null_row = next((r for r in rows
                         if r[idx["status"]] == "measured_null"), None)
        if null_row is None:
            self.skipTest("the copied rows carry no measured_null row")
        extra = list(null_row)
        extra[idx["attempt_id"]] = "b" * 64
        build_fixture(self.db, rows=rows + [tuple(extra)])
        snap = loop_status.knowledge_snapshot(self.root)
        g = snap["groups"]
        self.assertNotEqual(g["kept"], g["measured_null"],
                            "the forced inequality did not take")
        card = self._text(self._render()["by_id"]["know"])
        self.assertIn(f"kept {g['kept']}", card)
        self.assertIn(f"measured_null {g['measured_null']}", card)
        self.assertIn(f"refused_at_formation {g['refused_at_formation']}", card)
        self.assertIn(f"{snap['mechanisms']['distinct']} mechanisms explored",
                      card)

    def test_the_walk_summary_prints_tried_and_attempts_in_order(self):
        """`3 mechanisms tried (5 attempts)` — with attempts forced greater
        than mechanisms, so the two numbers cannot be swapped silently."""
        columns, rows = copy_rows()
        idx = {name: i for i, name in enumerate(columns)}
        target = next((r for r in rows if r[idx["mechanism_id"]]
                       and "mul_mat_vec_q" in str(r[idx["target_symbol"]] or "")),
                      None)
        if target is None:
            self.skipTest("no copied row targets mul_mat_vec_q on this store")
        extra = list(target)
        extra[idx["attempt_id"]] = "c" * 64
        build_fixture(self.db, rows=rows + [tuple(extra)])
        led = loop_status.knowledge_snapshot(self.root)["ledger"]
        group = next(g for g in led["agenda"]
                     if g["kernel"] == "mul_mat_vec_q")
        s = group["summary"]
        self.assertGreater(s["attempts"], s["mechanisms_tried"])
        card = self._text(self._render()["by_id"]["know"])
        plural = "" if s["mechanisms_tried"] == 1 else "s"
        self.assertIn(f"{s['mechanisms_tried']} mechanism{plural} tried "
                      f"against this hotspot ({s['attempts']} attempts)", card)

    def test_an_untried_hotspot_renders_loud(self):
        build_fixture(self.db)
        status = json.loads(
            (self.root / loop_status.STATUS_FILENAME).read_text())
        status["hotspots"] = [{"signature":
                               "void a_kernel_no_row_targets<float>(float*)",
                               "share_of_device_time": 0.164, "calls": 7,
                               "total_duration_ns": 1}]
        (self.root / loop_status.STATUS_FILENAME).write_text(
            json.dumps(status))
        card = self._text(self._render()["by_id"]["know"])
        self.assertIn("no hypothesis has ever targeted this kernel", card)
        self.assertIn("16.4% of device time in the champion profile "
                      "unexplored", card)

    def test_absent_renders_the_standard_wording_and_no_zeros(self):
        out = self._render()
        card = self._text(out["by_id"]["know"])
        self.assertIn("ABSENT", card)
        self.assertIn("never recorded an attempt", card)
        self.assertIn("missing count is not a zero", card)
        self.assertNotIn("attempts ever", card)
        self.assertNotRegex(card, r"\b0\b(?! bytes)",
                            "a zero rendered over a missing store")
        self.assertTrue(out["class_by_id"]["know-badge"].endswith("absent"))

    def test_malformed_renders_the_fault_and_no_zeros(self):
        self.db.write_bytes(b"not a database")
        out = self._render()
        card = self._text(out["by_id"]["know"])
        self.assertIn("MALFORMED", card)
        self.assertIn("could not be read", card)
        self.assertNotIn("attempts ever", card)
        self.assertTrue(out["class_by_id"]["know-badge"].endswith("malformed"))

    def test_stale_renders_dated_with_the_counts_still_shown(self):
        rows = build_fixture(self.db)
        past = self.db.stat().st_mtime - 2 * loop_status.KNOWLEDGE_STALE_AFTER_S
        os.utime(self.db, (past, past))
        out = self._render()
        card = self._text(out["by_id"]["know"])
        self.assertIn("DATED", card)
        # The apostrophe is HTML-escaped in the rendered card, so the key
        # stops before it rather than quietly failing on the entity.
        self.assertIn("complete as of the store", card)
        self.assertIn(str(len(rows)), card)
        self.assertTrue(out["class_by_id"]["know-badge"].endswith("stale"))
        self.assertTrue(
            out["text_by_id"]["know-badgetxt"].startswith("STALE"),
            out["text_by_id"]["know-badgetxt"])

    def test_the_four_renderings_are_distinct(self):
        seen = {}
        seen["absent"] = self._render()["by_id"]["know"]
        self.db.write_bytes(b"garbage")
        seen["malformed"] = self._render()["by_id"]["know"]
        self.db.unlink()
        build_fixture(self.db)
        seen["fresh"] = self._render()["by_id"]["know"]
        past = self.db.stat().st_mtime - 2 * loop_status.KNOWLEDGE_STALE_AFTER_S
        os.utime(self.db, (past, past))
        seen["stale"] = self._render()["by_id"]["know"]
        self.assertEqual(len(set(seen.values())), 4,
                         "two knowledge states rendered identically")


class Wiring(unittest.TestCase):
    def test_the_page_declares_the_card_and_reads_it(self):
        html = PAGE.read_text(encoding="utf-8")
        script = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html,
                                      re.S))
        for element in ("sec-knowledge", "know", "know-badge", "know-badgetxt"):
            self.assertIn(f'id="{element}"', html, element)
        for element in ("know", "know-badge", "know-badgetxt"):
            self.assertIn(f'"{element}"', script,
                          f"{element} is declared but never read")

    def test_the_readme_names_the_fourth_producer(self):
        text = (REPO / "dashboard/README.md").read_text(encoding="utf-8")
        self.assertIn("experiments.db", text)
        self.assertIn("fourth producer", text.lower())


if __name__ == "__main__":
    unittest.main()
