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

    def test_a_real_shaped_store_renders_the_folds(self):
        rows = build_fixture(self.db)
        out = self._render()
        card = self._text(out["by_id"]["know"])
        self.assertIn("Attempts ever", card)
        self.assertIn(str(len(rows)), card)
        self.assertIn("Mechanisms explored", card)
        self.assertIn("Mechanisms revisited", card)
        self.assertIn("measured_null", card)
        self.assertIn("anchor of their day", card)
        self.assertIn("not falsified forever", card)
        self.assertIn("refused_at_formation", card)
        self.assertIn("before costing any device time", card)
        self.assertIn("no scientific verdict", card)
        self.assertTrue(out["class_by_id"]["know-badge"].endswith("fresh"),
                        out["class_by_id"]["know-badge"])

    def test_the_recent_keeps_are_named_with_anchored_effects(self):
        rows = build_fixture(self.db)
        out = self._render()
        html = out["by_id"]["know"]
        card = self._text(html)
        if "Most recent keeps" not in card:
            self.skipTest("the copied rows carry no keeps — nothing to name")
        # Every percentage in the card sits beside its marginal label; an
        # unlabelled percentage is the page's founding defect.
        for match in re.finditer(r"[-+]\d+(?:\.\d+)?%", card):
            window = card[max(0, match.start() - 160):match.end() + 160]
            self.assertIn("marginal", window,
                          f"unanchored effect {match.group()!r} on the card")

    def test_absent_renders_the_standard_wording_and_no_zeros(self):
        out = self._render()
        card = self._text(out["by_id"]["know"])
        self.assertIn("ABSENT", card)
        self.assertIn("never recorded an attempt", card)
        self.assertIn("missing count is not a zero", card)
        self.assertNotIn("Attempts ever", card)
        self.assertNotRegex(card, r"\b0\b(?! bytes)",
                            "a zero rendered over a missing store")
        self.assertTrue(out["class_by_id"]["know-badge"].endswith("absent"))

    def test_malformed_renders_the_fault_and_no_zeros(self):
        self.db.write_bytes(b"not a database")
        out = self._render()
        card = self._text(out["by_id"]["know"])
        self.assertIn("MALFORMED", card)
        self.assertIn("could not be read", card)
        self.assertNotIn("Attempts ever", card)
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
