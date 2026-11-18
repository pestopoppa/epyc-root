"""Project prospective sealed V9-8 lifecycle comparisons through the shared carrier."""

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import ModuleType

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames

SOURCE_KIND = "kernel-promotion-lifecycle"
ADAPTER_ID = "vidya.adapters.kernel_promotion_lifecycle/v1"
AUTHORITY = "measurement"
VALIDATOR = Path(__file__).resolve().parents[3] / "scripts/benchmark/kernel_promotion_evidence.py"


def units(path):
    path = Path(path)
    if path.is_file():
        return [path.parent] if path.name == "MANIFEST.json" else [path]
    if (path / "resident/capture.json").is_file() or (path / "MANIFEST.json").is_file():
        return [path]
    return sorted({p.parent for p in path.glob("*/MANIFEST.json")})


def _validate(path):
    try:
        source = VALIDATOR.read_bytes()
        validator = ModuleType("_vidya_kernel_promotion_evidence")
        validator.__file__ = str(VALIDATOR)
        exec(compile(source, str(VALIDATOR), "exec"), validator.__dict__)
        manifest = path / "MANIFEST.json"
        manifest_sha = validator.digest(manifest)
        report = validator.verify(path)
        validator.require(validator.digest(manifest) == manifest_sha, "evidence manifest changed during replay")
        validator.require("observation" in report, "capture predates prospective lifecycle observation wiring")
        validator.require(report["observation"]["source"]["validator_sha256"] == sha256(source).hexdigest(),
                          "validator bytes changed during replay")
        return report, manifest_sha
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError, RecursionError) as exc:
        raise ProjectionError(f"{SOURCE_KIND} {path}: {exc}") from exc


def _eligible(report):
    # Fresh fallback retains diagnostic evidence without admitting the failed resident comparison.
    return (report["resident_complete"] and bool(report["comparisons"])
            and all(item[key] in {"exact", "different"} for item in report["comparisons"]
                    for key in ("content", "token_ids")))


def _tuple(path, report, manifest_sha):
    observation = report["observation"]
    comparisons = report["comparisons"]
    mismatches = sum("different" in (item["content"], item["token_ids"]) for item in comparisons)
    intent = "resident and fresh" if report["fresh_complete"] else "resident"
    schedule_sha = observation["schedule_sha256"]
    production = observation["arm_images"]["production"]["binary_sha256"]
    candidate = observation["arm_images"]["candidate"]["binary_sha256"]
    claim = (
        f"V9-8 {intent} lifecycle diagnostics found {mismatches} exact-parity mismatches "
        f"in {len(comparisons)} comparisons under schedule {schedule_sha}. "
        f"The seal binds the model files and runtime images (production {production}, candidate {candidate}). "
        "This claim concerns output parity for the captured requests."
    )
    closed = datetime.fromisoformat(observation["closed_utc"]).astimezone(UTC)
    return ClaimTuple(
        measurement_id=f"{SOURCE_KIND}:{manifest_sha}",
        metric="kernel_promotion_lifecycle_mismatches", value=mismatches, date=closed.date().isoformat(),
        category="CANDIDATE", claim=claim, metric_direction="lower_better", unit="comparisons",
        protocol_id="", reps=1, reps_basis="one sealed lifecycle comparison",
        attestation_path=str(path / "MANIFEST.json"), attestation_sha256=manifest_sha,
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={"consumer": "autokernel.planner"},
        observation={"outcome_native": report["verdict"]},
        extra={"adapter": ADAPTER_ID, "comparisons": len(comparisons), **observation},
    )


@register(SOURCE_KIND)
def project(path):
    path = Path(path)
    report, manifest_sha = _validate(path)
    if not _eligible(report):
        raise ProjectionError(f"{SOURCE_KIND} {path}: lifecycle has no complete resident comparison")
    return _tuple(path, report, manifest_sha)


def frames_for_path(path, *, as_of):
    path = Path(path)
    report, manifest_sha = _validate(path)
    if not _eligible(report):
        return []
    return to_frames(_tuple(path, report, manifest_sha), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)
