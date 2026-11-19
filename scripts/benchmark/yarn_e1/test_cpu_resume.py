"""Offline regression controls for the vanished turn-42 CY2 slot."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import cpu_resume as guard


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "CY2/state.json"
        self.state.parent.mkdir()
        self.slot = self.root / "slots/CY2.bin"
        self.slot.parent.mkdir()
        self.receipt = self.root / "checkpoint.json"
        self.identity = dict(model_sha256="a"*64, build_sha256="b"*64, argv_sha256="c"*64)
        self.old = dict(arm="CY2", turn=42, saved_turn=42, depth=367636,
                        short_done=["prior-short"], probes_done=[320000],
                        cold_done=False, restore_selftest=True)
        self.state.write_text(json.dumps(self.old))
        self.records = self.root / "CY2/calls.jsonl"
        self.records.write_text('{"kind":"needle","grade":"correct"}\n')
        self.runner = SimpleNamespace(RESULTS=self.root, SLOTS=self.slot.parent)
        self.args = SimpleNamespace(arm="CY2", force_preflight=False, selftest_external=False)

    def seal_fixture(self):
        self.slot.write_bytes(b"test-slot-bytes")
        self.receipt.write_text(json.dumps(dict(schema="yarn-cpu-checkpoint-v1",
            identity=self.identity,
            state_sha256=hashlib.sha256(self.state.read_bytes()).hexdigest(),
            slot_sha256=hashlib.sha256(self.slot.read_bytes()).hexdigest())))

    def prepare(self):
        return guard.prepare_resume(self.state, self.slot, self.receipt, self.identity)

    def test_historical_missing_slot_refills_before_legacy_reads_state(self):
        before = self.state.read_bytes()
        records = self.records.read_bytes()
        def legacy_run(args):
            st = json.loads(self.state.read_bytes())
            self.assertEqual(st["saved_turn"], 0)
            self.assertEqual(st["turn"], 0)
            self.assertEqual(st["depth"], 0)
            self.assertEqual(st["probes_done"], [])
            self.assertNotIn("restore_selftest", st)
            self.assertIsNot(args, self.args)
            return 75
        self.runner.run = Mock(side_effect=legacy_run)
        self.assertEqual(guard.run_guarded(self.runner, self.args, self.identity, self.receipt), 75)
        decision = json.loads(self.state.with_name("resume-decision.json").read_bytes())
        self.assertEqual(decision["action"], "re-prefill")
        self.assertEqual(Path(decision["archive"]).read_bytes(), before)
        self.assertEqual(self.records.read_bytes(), records)

    def test_verified_checkpoint_resumes_byte_identical_state_and_slot(self):
        self.seal_fixture()
        before = self.state.read_bytes(), self.slot.read_bytes()
        self.assertEqual(self.prepare()["action"], "resume")
        self.assertEqual((self.state.read_bytes(), self.slot.read_bytes()), before)

    def test_each_identity_dimension_invalidates_checkpoint(self):
        for key in self.identity:
            with self.subTest(key=key):
                self.state.write_text(json.dumps(self.old))
                self.seal_fixture()
                value = dict(self.identity, **{key: "d"*64})
                decision = guard.prepare_resume(self.state, self.slot, self.receipt, value)
                self.assertEqual(decision["action"], "re-prefill")
                self.assertEqual(json.loads(self.state.read_bytes()), guard.fresh_state("CY2"))
                self.assertEqual(self.slot.read_bytes(), b"test-slot-bytes")

    def test_corrupt_or_deleted_slot_never_restores(self):
        for mode in ("corrupt", "missing", "empty"):
            with self.subTest(mode=mode):
                self.state.write_text(json.dumps(self.old))
                self.seal_fixture()
                if mode == "missing":
                    self.slot.unlink()
                else:
                    self.slot.write_bytes(b"changed" if mode == "corrupt" else b"")
                self.assertEqual(self.prepare()["action"], "re-prefill")

    def test_progress_after_save_cannot_claim_saved_depth(self):
        self.old["turn"] = 43
        self.state.write_text(json.dumps(self.old))
        self.seal_fixture()
        self.assertEqual(self.prepare()["action"], "re-prefill")

    def test_malformed_state_is_preserved(self):
        self.state.write_bytes(b"unfinished {")
        decision = self.prepare()
        self.assertEqual(Path(decision["archive"]).read_bytes(), b"unfinished {")
        self.assertEqual(json.loads(self.state.read_bytes())["saved_turn"], 0)

    def test_modified_state_invalidates_existing_receipt(self):
        self.seal_fixture()
        self.old["probes_done"].append(510000)
        self.state.write_text(json.dumps(self.old))
        self.assertEqual(self.prepare()["action"], "re-prefill")

    def test_refuses_force_preflight_and_external_server_before_mutation(self):
        self.runner.run = Mock()
        original = self.state.read_bytes()
        for key in ("force_preflight", "selftest_external"):
            args = SimpleNamespace(**vars(self.args))
            setattr(args, key, True)
            with self.assertRaises(ValueError):
                guard.run_guarded(self.runner, args, self.identity, self.receipt)
        self.runner.run.assert_not_called()
        self.assertEqual(self.state.read_bytes(), original)

    def test_invalid_identity_leaves_existing_state_untouched(self):
        original = self.state.read_bytes()
        for identity in ({}, dict(self.identity, argv_sha256="mtime-is-not-proof")):
            with self.assertRaises(ValueError):
                guard.prepare_resume(self.state, self.slot, self.receipt, identity)
        self.assertEqual(self.state.read_bytes(), original)

    def test_new_run_has_no_resume_claim(self):
        self.state.unlink()
        self.assertEqual(self.prepare(), dict(action="fresh", reason="no prior state", archive=None))


if __name__ == "__main__":
    unittest.main()
