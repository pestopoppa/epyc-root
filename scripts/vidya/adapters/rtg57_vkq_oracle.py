"""Read the original RTG57 model-free oracle with its predeclared strict projector."""
import importlib.util
from pathlib import Path
from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.rtg57_vkq_oracle/v1"
AUTHORITY = "measurement"
_ROOT = Path(__file__).resolve().parents[3]
_PROJECTOR = _ROOT / "artifacts/operator/rtg57-f32-prep/oracle/projector.py"

def _read(path):
    try:
        spec = importlib.util.spec_from_file_location("rtg57_original_projector", _PROJECTOR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.project(str(path))
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise ProjectionError(f"RTG57 oracle receipt refused: {exc}") from exc

def native_rows(path):
    path = str(Path(path).resolve())
    return ({"path": path, "projection": _read(path)},)

@register("rtg57-vkq-oracle")
def project(native):
    row = _read(native["path"])
    if row != native["projection"]:
        raise ProjectionError("RTG57 receipt changed since read")
    return ClaimTuple(measurement_id=row["measurement_id"], metric=row["metric"],
        value=row["value"], date=__import__("json").loads(Path(native["path"]).read_text())["completed_utc"],
        category="CANDIDATE", claim=row["claim"], metric_direction="lower_better",
        protocol_id="", reps=1, reps_basis="scored:1 model-free shape", unit="nmse",
        attestation_locator=native["path"], attestation_sha256=row["attestation_sha256"],
        attestation_present=True, attestation_verified=True, source_kind="rtg57-vkq-oracle",
        applicability={"scope_basis":"native", "backend":"cpu",
                       "knobs":{"GGML_FA_VKQ_F32":"1", "op":"FLASH_ATTN_EXT", "oracle":"fp64"}},
        observation={"outcome_native":"single model-free numerical shape; producer hashes unknown"},
        extra={"producer_script_hashes":"not recorded in original receipt"})
