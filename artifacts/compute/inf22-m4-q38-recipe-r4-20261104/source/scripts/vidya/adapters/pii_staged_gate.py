"""Project private original PII sub-gate findings; never export indexed bodies."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from scripts.hooks.pii_staged_capture import read_receipt
from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.pii_staged_gate/v1"
AUTHORITY = "pii_subgate_observation_no_privacy_or_promotion_authority"


def native_rows(path):
    try:
        record, digest = read_receipt(path)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        # No private exception snippets, indexed filenames or body fragments.
        raise ProjectionError("private PII sub-gate custody refused") from None
    if record["pii_staged_policy_check_passed"] is None:
        return ()
    return ({"record": record, "receipt_path": str(Path(path).resolve()),
             "receipt_sha256": digest},)


@register("pii-staged-gate", source_class="verifier",
          decided_proposition_field="decided_proposition")
def project(native):
    try:
        if native_rows(native["receipt_path"]) != (native,):
            raise ProjectionError("private original gate custody changed")
        record = native["record"]
        return ClaimTuple(measurement_id="pii-subgate:" + record["receipt_sha256"],
            metric=record["metric"], value=record["pii_staged_policy_check_passed"],
            date=record["ended_utc"], category=record["category"],
            metric_direction=record["metric_direction"], protocol_id="",
            claim=record["decided_proposition"], decided_proposition=record["decided_proposition"],
            source_class="verifier", source_kind=ADAPTER_ID, binding_kind="identity",
            attestation_locator=native["receipt_path"],
            extra={"receipt_sha256": native["receipt_sha256"],
                   "index_sha256": record["original_index_sha256"],
                   "policy_sha256": record["policy_digest"], "counts": record["counts"],
                   "exit_code": record["exit_code"], "scope": record["scope"],
                   "promotion_authority": False})
    except (KeyError, TypeError, ValueError):
        raise ProjectionError("private PII sub-gate projection refused") from None
