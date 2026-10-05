"""Project original prospective fixture receipts through the shared verifier carrier."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from scripts.ci.native_conformance import read_receipt
from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.ci_conformance/v1"


def native_rows(path):
    try:
        record, digest = read_receipt(path)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProjectionError(f"CI fixture receipt refused: {exc}") from exc
    if record["fixture_execution_conformant"] is None:
        return ()
    return ({"record": record, "receipt_path": str(Path(path).resolve()),
             "receipt_sha256": digest},)


@register("ci-fixture-conformance", source_class="verifier",
          decided_proposition_field="decided_proposition")
def project_ci_conformance(native):
    try:
        rows = native_rows(native["receipt_path"])
        if len(rows) != 1 or rows[0] != native:
            raise ProjectionError("native receipt changed since reopening")
        record = native["record"]
        return ClaimTuple(measurement_id="ci-fixture:" + record["receipt_sha256"],
            metric=record["metric"], value=record["fixture_execution_conformant"],
            date=record["ended_utc"], category=record["category"],
            metric_direction=record["metric_direction"], protocol_id="",
            claim=record["decided_proposition"], decided_proposition=record["decided_proposition"],
            source_class="verifier", source_kind=ADAPTER_ID, binding_kind="identity",
            attestation_locator=native["receipt_path"],
            extra={"receipt_sha256": native["receipt_sha256"], "runner": record["runner"],
                   "repositories": record["repositories"], "argv": record["argv"],
                   "readset": record["readset"], "counts": record["summary"]["counts"],
                   "exclusions": record["exclusions"]})
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectionError(f"CI fixture projection refused: {exc}") from exc
