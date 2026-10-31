import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent
CANDIDATE = HERE / "ws58-ready-depth-candidate.sh"
GIB = 1024**3
FLOOR = 150 * GIB


class CandidateEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="loop25-")
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "ready").mkdir()
        (self.root / "grants").mkdir()
        (self.root / "codex-channels").mkdir()
        shutil.copy2(HERE / "validate_fillers.py", self.root / "validate_fillers.py")
        self.log = self.root / "ready-depth.log"
        self.owner_md = self.root / "owner-reply.md"
        self.owner_json = self.root / "owner-reply.json"
        self.owner_json.write_text('{"updates": []}\n', encoding="utf-8")
        self.channel = self.root / "codex-channels" / "codex3.md"
        self.channel.write_text("# fixture\n", encoding="utf-8")
        self.now = dt.datetime(2026, 10, 31, 18, 0, 0, tzinfo=dt.timezone.utc)
        self.identity = {"target": str(self.root.resolve()), "device": self.root.stat().st_dev}
        self._write_fillers([
            ("alpha", "ARMED", "est_output_GiB=4"),
            ("beta", "ARMED", "est_output_GiB=3"),
        ])
        (self.root / "ready" / "alpha.json").write_text(
            json.dumps({"id": "alpha", "regions": "q1", "est_output_GiB": 4}),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _write_fillers(self, rows):
        columns = [
            "filler-id", "owner", "launcher + pid", "resources", "min useful window",
            "max private ram", "stop file", "status", "class", "duration", "min window",
            "ds41-class y/n", "ready y/n", "prior", "decision", "min_effect", "substrate", "notes",
        ]
        lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
        for row_id, status, notes in rows:
            cells = ["-"] * len(columns)
            cells[0] = row_id
            cells[1] = "fixture"
            cells[7] = status
            cells[17] = notes
            lines.append("| " + " | ".join(cells) + " |")
        (self.root / "FILLERS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _history(self, old_free, current_free, *, stale=False, rebound=False):
        start = self.now - dt.timedelta(hours=8)
        if stale:
            start = self.now - dt.timedelta(hours=9)
            end = self.now - dt.timedelta(hours=1)
        else:
            end = self.now - dt.timedelta(minutes=10)
        span = (end - start).total_seconds()
        lines = []
        for i in range(int(span // 600) + 1):
            stamp = start + dt.timedelta(seconds=i * 600)
            ratio = (stamp - start).total_seconds() / span
            if rebound:
                midpoint = start + dt.timedelta(hours=4)
                if stamp <= midpoint:
                    segment = (stamp - start).total_seconds() / (4 * 3600)
                    free = int(old_free + (340 * GIB - old_free) * segment)
                else:
                    segment = (stamp - midpoint).total_seconds() / (span - 4 * 3600)
                    free = int(340 * GIB + (current_free - 340 * GIB) * segment)
            else:
                free = int(old_free + (current_free - old_free) * ratio)
            sample = {"at": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"), "free_bytes": free, **self.identity}
            lines.append("disk_sample " + json.dumps(sample, sort_keys=True))
        self.log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _run(self, free):
        env = os.environ.copy()
        env.update({
            "COMPUTE_FLAGS_ROOT": str(self.root),
            "READY_DEPTH_LOG": str(self.log),
            "READY_DEPTH_OWNER_REPLY": str(self.owner_md),
            "READY_DEPTH_OWNER_JSON": str(self.owner_json),
            "READY_DEPTH_CHANNEL_GLOB": str(self.root / "codex-channels" / "*.md"),
            "READY_DEPTH_TEST_MODE": "1",
            "READY_DEPTH_TEST_FREE_BYTES": str(free),
            "READY_DEPTH_TEST_NOW": self.now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "DISK_FORECAST_PATH": str(self.root),
            "READY_DEPTH_ONCE": "1",
        })
        result = subprocess.run(["bash", str(CANDIDATE)], env=env, text=True, capture_output=True, check=True)
        result.log_text = self.log.read_text(encoding="utf-8")
        return result

    def test_deduplicates_ready_and_armed_rows_and_projects_below_floor(self):
        current = 200 * GIB
        self._history(300 * GIB, current)
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("reserved=7.0GiB", line)  # alpha is present in both sources, counted once.
        match = re.search(r"projected=([0-9.]+)GiB", line)
        self.assertIsNotNone(match)
        self.assertAlmostEqual(float(match.group(1)), 93.0, delta=0.3)
        self.assertIn("status=ALARM", line)
        self.assertIn("status=ALARM", self.channel.read_text(encoding="utf-8"))
        self.assertIn("READY-DEPTH LOW", self.owner_md.read_text(encoding="utf-8"))
        self.assertIn("status=ALARM", self.owner_md.read_text(encoding="utf-8"))
        owner_updates = json.loads(self.owner_json.read_text(encoding="utf-8"))["updates"]
        self.assertEqual(len(owner_updates), 1)
        self.assertIn("status=ALARM", owner_updates[0]["text"])

    def test_cutoff_uses_exact_150_gib_floor(self):
        current = 220 * GIB
        # Eight-hour measured growth is exactly 20 GiB.
        self._history(240 * GIB, current)
        self._write_fillers([("alpha", "ARMED", "est_output_GiB=4"),
                             ("beta", "ARMED", "est_output_GiB=45")])
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("projected=151.0GiB", line)
        self.assertIn("status=OK", line)

        # Exactly 150 GiB is alarmed; both clock and free-space input are fixed seams.
        self._write_fillers([("alpha", "ARMED", "est_output_GiB=4"),
                             ("beta", "ARMED", "est_output_GiB=46")])
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("projected=150.0GiB", line)
        self.assertIn("status=ALARM", line)

        self._write_fillers([("alpha", "ARMED", "est_output_GiB=4"),
                             ("beta", "ARMED", "est_output_GiB=47")])
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("projected=149.0GiB", line)
        self.assertIn("status=ALARM", line)

    def test_missing_reservation_stale_history_and_cleanup_do_not_go_green(self):
        current = 240 * GIB
        self._write_fillers([("alpha", "ARMED", "est_output_GiB=4"), ("unknown", "ARMED", "")])
        self._history(250 * GIB, current)
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("unknown", line)
        self.assertNotIn("alpha", line)  # READY's estimate resolves its duplicate ARMED row.

        self._write_fillers([("alpha", "ARMED", "est_output_GiB=4")])
        self._history(250 * GIB, current, stale=True)
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("stale", line)

        self._history(230 * GIB, current, rebound=True)
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("increase", line)

    def test_identity_timezone_duplicate_and_parser_failures_stay_unknown(self):
        current = 240 * GIB
        self._history(250 * GIB, current)
        with self.log.open("a", encoding="utf-8") as stream:
            stream.write('disk_sample {"at":"broken"\n')
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("JSONDecodeError", line)

        self._history(250 * GIB, current)
        lines = self.log.read_text(encoding="utf-8").splitlines()
        item = json.loads(lines[-1][len("disk_sample "):])

        changed = dict(item, target="/other/mount")
        self.log.write_text("\n".join(lines[:-1] + ["disk_sample " + json.dumps(changed)]) + "\n", encoding="utf-8")
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("identity", line)

        self._history(250 * GIB, current)
        lines = self.log.read_text(encoding="utf-8").splitlines()
        item = json.loads(lines[-1][len("disk_sample "):])
        changed = dict(item, device=item["device"] + 1)
        self.log.write_text("\n".join(lines[:-1] + ["disk_sample " + json.dumps(changed)]) + "\n", encoding="utf-8")
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("identity", line)

        self._history(250 * GIB, current)
        lines = self.log.read_text(encoding="utf-8").splitlines()
        item = json.loads(lines[-1][len("disk_sample "):])
        ambiguous = dict(item, at="2026-10-31T17:59:50")
        self.log.write_text("\n".join(lines + ["disk_sample " + json.dumps(ambiguous)]) + "\n", encoding="utf-8")
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("UTC", line)

        self._history(250 * GIB, current)
        lines = self.log.read_text(encoding="utf-8").splitlines()
        item = json.loads(lines[-1][len("disk_sample "):])
        conflict = dict(item, free_bytes=item["free_bytes"] + 1)
        self.log.write_text("\n".join(lines + ["disk_sample " + json.dumps(conflict)]) + "\n", encoding="utf-8")
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("duplicate", line)

        self._history(250 * GIB, current)
        self._write_fillers([("alpha", "ARMED", "est_output_GiB=4")])
        bad = ["| filler-id | owner |", "|---|---|", "| broken | row |"]
        (self.root / "FILLERS.md").write_text("\n".join(bad) + "\n", encoding="utf-8")
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("FILLERS", line)

    def test_malformed_row_manifest_mismatch_bool_and_complete_row(self):
        current = 240 * GIB
        self._history(250 * GIB, current)

        # A known complete ARMED row does not reserve space or poison coverage.
        (self.root / "grants" / "beta.complete").write_text("done\n", encoding="utf-8")
        self._write_fillers([("alpha", "ARMED", "est_output_GiB=4"), ("beta", "ARMED", "")])
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=OK", line)
        self.assertIn("reserved=4.0GiB", line)

        # A non-18-cell row means the ARMED reservation scan is incomplete.
        self._history(250 * GIB, current)
        text = (self.root / "FILLERS.md").read_text(encoding="utf-8")
        (self.root / "FILLERS.md").write_text(text + "| broken | short |\n", encoding="utf-8")
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("FILLERS-line", line)

        # A conflicting source estimate is unknown rather than double-counted.
        self._history(250 * GIB, current)
        self._write_fillers([("alpha", "ARMED", "est_output_GiB=5")])
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("alpha", line)

        # Manifest ID mismatch and boolean output estimates are rejected explicitly.
        self._history(250 * GIB, current)
        (self.root / "ready" / "alpha.json").write_text(
            json.dumps({"id": "other", "regions": "q1", "est_output_GiB": 4}), encoding="utf-8")
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("other", line)

        self._history(250 * GIB, current)
        (self.root / "ready" / "alpha.json").write_text(
            json.dumps({"id": "alpha", "regions": "q1", "est_output_GiB": True}), encoding="utf-8")
        result = self._run(current)
        line = next(line for line in reversed(result.log_text.splitlines()) if "disk forecast" in line)
        self.assertIn("status=UNKNOWN", line)
        self.assertIn("alpha", line)


if __name__ == "__main__":
    unittest.main()
