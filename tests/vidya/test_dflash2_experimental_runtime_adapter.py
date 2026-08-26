import hashlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(ROOT / "scripts" / "vidya" / "adapters"))

import claim_tuple as ct  # noqa: E402
import dflash2_experimental_runtime as A  # noqa: E402


FAKE = textwrap.dedent(r'''
class DFlash2BeliefRefusal(ValueError):
    pass

def native_rows(source):
    if isinstance(source, dict) and source.get("schema") == "epyc.df2.matched_np1_campaign.v1":
        return []
    if not isinstance(source, dict) or source.get("schema") != "epyc.df2.experimental_runtime_campaign.v1":
        raise DFlash2BeliefRefusal("unsupported source")
    return source["native_rows"]

def project(native):
    if set(native) != {"source", "source_locator", "measurement"}:
        raise DFlash2BeliefRefusal("native shape")
    source = native["source"]
    measurement = native["measurement"]
    if native not in native_rows(source):
        raise DFlash2BeliefRefusal("row was not producer-authored")
    return dict(measurement)
''').lstrip()


def measurement(**updates):
    extra = {
        "authority": A.AUTHORITY,
        "experimental_runtime": True,
        "source_mutation_strategy": False,
        "kernel_champion_authority": False,
        "promotion_authority": False,
        "production_authority": False,
        "campaign_id": "df2-5-qwen38-concurrency-20260820",
        "campaign_locator": "/artifact/campaign-summary.json",
        "binary_sha256": "a" * 64,
        "target_model_sha256": "b" * 64,
        "draft_model_sha256": "c" * 64,
        "claim": {"claim_id": "akd-1", "device_id": "mi210_0",
                  "released_at": "2026-08-20T16:00:00+00:00"},
        "kfd_resident_samples": 4,
        "positive_vram_samples": 4,
        "manifest_sha256": "d" * 64,
    }
    row = {
        "measurement_id": "df2_deadbeef_decode",
        "metric": "decode_tokens_per_s", "value": 123.5,
        "date": "2026-08-20", "category": "CANDIDATE",
        "claim": "DFlash2 experimental-runtime dflash2_np8 throughput",
        "metric_direction": "higher_better",
        "protocol_id": "DF2-5-QWEN38-NP-GRID-v1",
        "reps": 12, "reps_basis": "scored:completed_requests",
        "unit": "tokens_per_second", "attestation_path": "",
        "attestation_locator": "/artifact/campaign-manifest.json",
        "attestation_sha256": "d" * 64, "attestation_present": True,
        "source_kind": "dflash2-experimental-runtime-measurement", "extra": extra,
    }
    row.update(updates)
    return row


class DFlash2ExperimentalRuntimeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.producer = Path(self.tmp.name) / "dflash2_beliefs.py"
        self.producer.write_text(FAKE, encoding="utf-8")
        self.hash_patch = mock.patch.object(A, "PRODUCER_SHA256", hashlib.sha256(
            self.producer.read_bytes()).hexdigest())
        self.path_patch = mock.patch.object(A, "DEFAULT_PRODUCER_PATH", self.producer)
        self.hash_patch.start(); self.path_patch.start()
        self.addCleanup(self.hash_patch.stop); self.addCleanup(self.path_patch.stop)

    def native(self, row=None):
        row = row or measurement()
        source = {"schema": A.SOURCE_SCHEMA}
        native = {"source": source, "source_locator": "/artifact/campaign-summary.json",
                  "measurement": row}
        source["native_rows"] = [native]
        return native

    def test_projection_is_registered_and_delegates_only_grading(self):
        native = self.native()
        rows = A.native_rows(native["source"])
        self.assertEqual(rows, (native,))
        projected = A.project(rows[0])
        self.assertIsInstance(projected, ct.ClaimTuple)
        self.assertEqual(projected.metric_direction, "higher_better")
        self.assertEqual(ct.grade(projected), ("Witnessed", "Attested", []))
        self.assertIs(ct.registered()[A.PROJECTION_NAME], A.project)

    def test_pre_hook_df2_4_emits_zero_rows(self):
        old = {"schema": A.PRE_HOOK_SCHEMA, "headline": {"decode_tok_s": 70.0}}
        self.assertEqual(A.native_rows(old), ())

    def test_producer_byte_drift_and_nonregular_identity_refuse(self):
        self.producer.write_text(FAKE + "# mutation\n", encoding="utf-8")
        with self.assertRaisesRegex(Exception, "producer bytes drifted"):
            A.native_rows({"schema": A.PRE_HOOK_SCHEMA})
        target = Path(self.tmp.name) / "target.py"
        target.write_text(FAKE, encoding="utf-8")
        self.producer.unlink(); self.producer.symlink_to(target)
        with self.assertRaisesRegex(Exception, "regular single-link"):
            A.native_rows({"schema": A.PRE_HOOK_SCHEMA})

    def test_forged_row_and_authority_or_direction_drift_refuse(self):
        native = self.native()
        forged = dict(native); forged["measurement"] = measurement(value=999.0)
        with self.assertRaisesRegex(Exception, "producer-authored"):
            A.project(forged)
        for key, value in (("promotion_authority", True), ("kernel_champion_authority", True)):
            row = measurement(); row["extra"] = dict(row["extra"]); row["extra"][key] = value
            with self.assertRaisesRegex(Exception, "authority boundary"):
                A.project(self.native(row))
        with self.assertRaisesRegex(Exception, "metric direction"):
            A.project(self.native(measurement(metric_direction="lower_better")))


if __name__ == "__main__":
    unittest.main()
