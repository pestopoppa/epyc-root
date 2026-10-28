"""Prospective HPR existing-family extension. Stdlib-only synthetic actual-writer round trips.

Run only under a canonical grant with CPython 3.12 and EPYC_HPR_RESEARCH_WT pinned to c4c2a3638.
No model/server/network call: the actual writer's HTTP and template digest are mocked by its fixture.
"""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from adapters import np_ctx_kvu as N
from adapters import _kvu_hpr_prefix as H
from claim_tuple import ProjectionError


class HprWriterReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("EPYC_HPR_RESEARCH_WT")
        if configured is None:
            raise unittest.SkipTest(
                "set EPYC_HPR_RESEARCH_WT to the pinned research checkout; expected producer helper "
                "at artifacts/np_context_kvu_cpu_study_20261020/driver/test_kvu_ckpt_arms.py"
            )
        research = Path(configured)
        driver = research / "artifacts/np_context_kvu_cpu_study_20261020/driver"
        missing = [name for name in ("kvu_ckpt_arms.py", "test_kvu_ckpt_arms.py") if not (driver / name).is_file()]
        if missing:
            raise RuntimeError(
                f"EPYC_HPR_RESEARCH_WT={research} lacks required producer file(s) in {driver}: {', '.join(missing)}"
            )
        sys.path.insert(0, str(driver))
        import kvu_ckpt_arms
        from test_kvu_ckpt_arms import native_fixture
        cls.K, cls.native_fixture = kvu_ckpt_arms, staticmethod(native_fixture)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.path = self.directory / "requests.jsonl"
        binary = self.directory / "llama-server"
        binary.write_text("synthetic non-executable binary identity only")
        K = self.K
        self.arm = K.ARM_DENSE
        cell = K.Cell("q36_35b", "dense", "ckpt", "8k", 0, 1.0, 1.0, "synthetic")
        launch = K.Launch("synthetic_hpr", "q36_35b", "dense", "select", 40960, [cell], (), 1.0, str(binary))
        self.la = K._la(launch, self.arm, 40960)
        self.server = types.SimpleNamespace(argv=K.arm_argv("q36_35b", self.arm, 40960, 18971, 24, str(binary)))
        self.args = types.SimpleNamespace(cpu_list="72-95", threads=24)
        self.facts = dict(kv_unified="false", n_ctx_slot="40960", n_slots="1", n_ctx_train_warn=None)
        self.cell_key = cell.key

    def emit(self, probe, prompt, generated, retained, prior_ids=(), prior_probe="launch_seed", incomplete=False):
        K = self.K
        rec = self.native_fixture(prompt, generated, retained)
        if incomplete:
            rec["ids"] = generated[:-1]
        capture = K.native_prefix_capture(prompt, rec)
        fields = dict(cell_key=self.cell_key, probe=probe, wave=0, status=200, error=None,
                      prompt_n=len(prompt), cache_n=0, predicted_n=len(generated), ttft_s=0.1,
                      raw_request_record_schema=K.HPR_PREFIX_CAPTURE_SCHEMA, prefix_capture=capture,
                      sim_inputs=dict(lcp_prev=K.common_prefix(prior_ids, prompt)))
        if not incomplete:
            sim = K.ServerSim(self.arm, cached=len(prior_ids))
            _, _, fields["prior_prefix_state"] = K.hpr_sim_step(sim, capture, [], list(prior_ids), prior_probe)
        return K.emit_request_row(fields, self.args, self.la, self.server, self.facts, [0.0, 0.0, 0.0], 0)

    def write(self, rows):
        self.path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def test_contract_copy_matches_actual_writer_and_native_provenance_survives_projection(self):
        self.assertEqual(H.CONTRACT, self.K.HPR_NATIVE_CONTRACT)
        self.assertEqual(H.sha(H.CONTRACT), self.K.HPR_NATIVE_CONTRACT_SHA256)
        first = self.emit("cold", [1, 2, 3], [8, 9], 4)
        second = self.emit("extend", [1, 2, 3, 8, 10], [12, 13], 6, [1, 2, 3, 8], "cold")
        self.write([first, second])
        tuples = [N.project(native) for native in N.native_rows(self.path)]
        self.assertEqual(len(tuples), 6)
        self.assertEqual({t.metric for t in tuples}, {"request_ok", "ttft_s", "prompt_n_tokens"})
        for t in tuples:
            p = t.extra["hpr_prefix_provenance"]
            self.assertEqual(p["native_contract_status"], "UNVERIFIED")
            self.assertIn("no simulator pass", p["scope"])
        self.assertEqual(tuples[0].extra["hpr_prefix_provenance"]["prior_prefix_verification"],
                         "producer_attested_launch_seed_raw_ids_absent")
        self.assertEqual(tuples[3].extra["hpr_prefix_provenance"]["prior_prefix_verification"],
                         "previous_native_record_rederived")

    def test_incomplete_actual_writer_capture_retains_refusal_without_correctness_metric(self):
        row = self.emit("incomplete", [1, 2, 3], [8, 9], 4, incomplete=True)
        self.write([row])
        tuples = [N.project(native) for native in N.native_rows(self.path)]
        self.assertEqual({t.metric for t in tuples}, {"request_ok", "ttft_s", "prompt_n_tokens"})
        for t in tuples:
            p = t.extra["hpr_prefix_provenance"]
            self.assertEqual(p["state"], "incomplete")
            self.assertTrue(p["refusal_problems"])
            self.assertIn("request_ok is HTTP status", p["scope"])

    def test_resealed_raw_or_completeness_tampering_is_refused(self):
        original = self.emit("cold", [1, 2, 3], [8, 9], 4)
        for field, value in (("generated_token_ids", [8, 100]), ("state", "incomplete"), ("retained_generated_tokens", 0)):
            row = copy.deepcopy(original)
            row["prefix_capture"][field] = value
            row["row_sha256"] = N.row_hash(row)
            self.write([row])
            with self.subTest(field=field), self.assertRaises(ProjectionError):
                N.native_rows(self.path)

    def test_resealed_prior_state_cannot_use_current_observed_cache_to_mask_disagreement(self):
        first = self.emit("cold", [1, 2, 3], [8, 9], 4)
        second = self.emit("extend", [1, 2, 3, 8, 10], [12, 13], 6, [1, 2, 3, 8], "cold")
        second["prior_prefix_state"]["retained_slot_tokens"] = second["cache_n"]
        second["row_sha256"] = N.row_hash(second)
        self.write([first, second])
        with self.assertRaisesRegex(ProjectionError, "prior captured state"):
            N.native_rows(self.path)

    def test_legacy_writer_rows_preserve_existing_metric_set(self):
        row = self.emit("legacy", [1, 2, 3], [8, 9], 4)
        for name in ("prefix_capture", "raw_request_record_schema", "prior_prefix_state"):
            row.pop(name)
        row["row_sha256"] = N.row_hash(row)
        self.write([row])
        tuples = [N.project(native) for native in N.native_rows(self.path)]
        self.assertEqual(len(tuples), 3)
        self.assertTrue(all("hpr_prefix_provenance" not in t.extra for t in tuples))


if __name__ == "__main__":
    unittest.main()
