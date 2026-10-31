import datetime
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts/vidya"))
from ledger import Ledger  # noqa: E402
from fold import fold  # noqa: E402
from adapters import calendar_overrun as a  # noqa: E402

FIXTURE = tempfile.TemporaryDirectory()
N = str(pathlib.Path(FIXTURE.name) / "fd-div-1b-c5-asan-t1-repair.ended")
pathlib.Path(N).write_text(
    "rc=0 time=2026-10-28T02:24:41Z reason=complete\njob_id=fd-div-1b-c5-asan-t1-repair\nowner=workspace-58 calendar / INF-67\nstep=job-run\nestimated_wall_s=1800\nstarted=2026-10-28T02:22:28Z\nregions=78-95\n"
)
H = hashlib.sha256(pathlib.Path(N).read_bytes()).hexdigest()
F = a.frames_for_path(N, as_of="2026-10-28T00:00:00Z") + a.frames_for_path(
    N, as_of="2026-10-28T02:46:48Z"
)
OLD = [x["frame_id"] for x in F[:3]]
KEEP = [x["frame_id"] for x in F[3:]]


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Repair(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.t.name) / "ledger"
        ledger = Ledger(self.path)
        for f in F:
            ledger.append(f)
        self.base = self.path.read_bytes()
        self.sha = hashlib.sha256(self.base).hexdigest()
        self.ts = stamp()
        self.kw = dict(
            native_sha256=H, old_ids=OLD, retained_ids=KEEP, created_at=self.ts
        )
        self.batch = a.prepare_duplicate_repair(N, F, **self.kw)

    def tearDown(self):
        self.t.cleanup()

    def apply(self):
        return a.apply_duplicate_repair(
            N,
            self.path,
            base_bytes=self.base,
            base_sha256=self.sha,
            reviewed_frames=self.batch,
            **self.kw,
        )

    def test_success_and_idempotent(self):
        self.assertEqual(self.apply()["appended_or_present"], 3)
        self.assertEqual(self.apply()["appended_or_present"], 3)
        allf = [r.frame for r in Ledger(self.path).read_all()]
        b = fold(allf, as_of=self.ts).beliefs[F[1]["assertion"]["claim_id"]].as_dict()
        self.assertEqual(b["pro"], {"Q": "Judged", "T": "Located"})
        self.assertEqual(b["pro_witnesses"], [F[5]["assertion"]["evidence_id"]])
        self.assertEqual(set(b["retracted_support"]), set(OLD))
        self.assertFalse(Ledger(self.path).verify())

    def test_reject_hash_and_different_frame(self):
        with self.assertRaises(a.ProjectionError):
            a.prepare_duplicate_repair(N, F, **dict(self.kw, native_sha256="0" * 64))
        modified = json.loads(json.dumps(F))
        modified[3]["assertion"]["title"] = "corrupt"
        with self.assertRaises(a.ProjectionError):
            a.prepare_duplicate_repair(N, modified, **self.kw)

    def test_missing_reordered_and_preexisting(self):
        for frames in (F[:-1], F[3:] + F[:3], F + self.batch):
            with self.assertRaises(a.ProjectionError):
                a.prepare_duplicate_repair(N, frames, **self.kw)

    def test_foreign_or_torn_frontier(self):
        with open(self.path, "ab") as out:
            out.write(b"garbage")
        with self.assertRaises(a.ProjectionError):
            self.apply()

    def test_review_and_base_mismatch(self):
        self.batch[0]["assertion"]["reason"] = "forged"
        with self.assertRaises(a.ProjectionError):
            self.apply()

    def test_partial_retry(self):
        from ledger_write_lease import OwnedWriteLease, LeasedLedger

        with OwnedWriteLease(self.path) as lease:
            lease.append(LeasedLedger(lease), self.batch[0])
        self.assertEqual(self.apply()["appended_or_present"], 3)

    def test_actor_or_scope_mismatch(self):
        for field in ("actor", "authority_scope"):
            x = json.loads(json.dumps(F))
            x[0]["pubinfo"][field] = "evil"
            with self.assertRaises(a.ProjectionError):
                a.prepare_duplicate_repair(N, x, **self.kw)

    def test_interrupted_after_first_append_retries(self):
        from ledger_write_lease import OwnedWriteLease

        original = OwnedWriteLease.append
        calls = []

        def interrupted(lease, ledger, frame):
            if calls:
                raise RuntimeError("simulated lease break")
            calls.append(1)
            return original(lease, ledger, frame)

        with patch.object(OwnedWriteLease, "append", interrupted):
            with self.assertRaises(RuntimeError):
                self.apply()
        self.assertEqual(len(Ledger(self.path).read_all()), 7)
        self.assertEqual(self.apply()["appended_or_present"], 3)

    def test_bad_base_digest_rejected(self):
        self.sha = "0" * 64
        with self.assertRaises(a.ProjectionError):
            self.apply()
        self.assertEqual(self.path.read_bytes(), self.base)

    def test_stale_time_fails_before_append(self):
        old = "2026-10-30T00:00:00Z"
        self.kw["created_at"] = old
        self.batch = a.prepare_duplicate_repair(N, F, **self.kw)
        with self.assertRaises(a.ProjectionError):
            self.apply()
        self.assertEqual(self.path.read_bytes(), self.base)


if __name__ == "__main__":
    unittest.main(verbosity=2)
