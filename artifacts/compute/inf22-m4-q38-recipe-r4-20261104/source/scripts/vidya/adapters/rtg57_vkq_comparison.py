"""Prospective RTG57 timing: validate native records with the sealed packet projector."""
import hashlib, importlib.util, json
from pathlib import Path
from claim_tuple import ClaimTuple, ProjectionError, register
ADAPTER_ID = "vidya.adapters.rtg57_vkq_comparison/v1"
AUTHORITY = "measurement"
ROOT = Path(__file__).resolve().parents[3] / "artifacts/operator/rtg57-f32-prep"
MODEL = "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    try:
        path = Path(path).resolve(); record = json.loads(path.read_text())
        identity = json.loads((path.parent / "identity.json").read_text())
        threads = identity["threads"]
        if threads not in (48, 96): raise ValueError("unreviewed topology")
        pkt = ROOT / f"t{threads}"
        if record["producer_script_sha256"] != sha(pkt / "driver.py") or record["source_manifest_sha256"] != sha(pkt / "SOURCES.sha256") or record["predeclared_rule_sha256"] != sha(pkt / "PROTOCOL.md"):
            raise ValueError("unsealed producer or rule")
        if not any(Path(k).name == MODEL for k in identity.get("sha256", {})):
            raise ValueError("architect model identity missing")
        spec = importlib.util.spec_from_file_location(f"rtg57_t{threads}_projector", pkt / "projector.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return threads, mod.project(path)
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise ProjectionError(f"RTG57 timing receipt refused: {exc}") from exc

def native_rows(path):
    path = str(Path(path).resolve()); threads, rows = read(path)
    return tuple({"path":path, "threads":threads, "row":row} for row in rows)
@register("rtg57-vkq-comparison")
def project(native):
    threads, rows = read(native["path"]); row = native["row"]
    if threads != native["threads"] or row not in rows: raise ProjectionError("receipt changed since read")
    return ClaimTuple(measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"],
      date=row["date"], category="CANDIDATE", claim=row["claim"], metric_direction=row["direction"],
      protocol_id="", reps=3, reps_basis="scored:3 paired process launches", unit="fraction",
      attestation_locator=native["path"], attestation_sha256=row["attestation_sha256"],
      attestation_present=True, attestation_verified=True, source_kind="rtg57-vkq-comparison",
      applicability={"scope_basis":"native", "model_file":MODEL, "quant":"UD-IQ4_XS", "backend":"cpu",
                     "knobs":{"GGML_FA_VKQ_F32":"1", "threads":threads}},
      observation={"outcome_native":"indicative timing; no correctness or adoption", "n_pairs":3},
      extra={"threads":threads,"topology":"experimental topology-shape"})
