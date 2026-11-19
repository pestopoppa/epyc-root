"""Project a sealed native Q38P-4 comparison into the existing diagnostic carrier."""

from datetime import datetime, timezone
from pathlib import Path

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames
from producers.q38p4_parity import OP, SEAL_NAME, SOURCE_KIND, canonical, digest, replay

ADAPTER_ID = "vidya.adapters.q38p4_parity/v1"
AUTHORITY = "measurement"


def units(path):
    path = Path(path)
    return [path] if path.is_file() else sorted(path.rglob(SEAL_NAME))


def candidate_scope(plan):
    return {
        "build_sha": plan["arms"]["llama"]["build_sha"],
        "candidate_sha256": digest(canonical(plan)),
        "op": OP, "run_id": plan["run_id"], "scope_basis": "native",
    }


def _read(path):
    try:
        return replay(path)
    except (OSError, KeyError, ValueError, TypeError, OverflowError, IndexError, RecursionError) as exc:
        raise ProjectionError(f"{SOURCE_KIND} {path}: {exc}") from exc


def _eligible(seal, plan):
    return plan["mode"] == "native" and seal["result"]["status"] in {"match", "divergence"}


def _tuple(path, seal, plan):
    result = seal["result"]
    state = "matched" if result["status"] == "match" else "diverged"
    left, right = (result["arms"][engine] for engine in ("llama", "vllm"))
    text = (
        f"Q38P-4 greedy MI210 replay {state} for one {len(plan['prompt_token_ids'])}-token "
        f"input for the two observed runtimes. Digest-pinned receipts declare the model conversion "
        f"and tokenizer identities. Native output lengths "
        f"were {len(left['tokens'])} and {len(right['tokens'])}, with stops "
        f"{left['native_stop']} and {right['native_stop']}. Scope is this input and capture pair."
    )
    return ClaimTuple(
        measurement_id=f"{SOURCE_KIND}:{seal['content_sha256']}",
        date=datetime.fromtimestamp(seal["completed_ns"] // 10**9, timezone.utc).date().isoformat(),
        metric="q38p4_greedy_divergence", value=int(state == "diverged"), unit="comparisons",
        metric_direction="lower_better", category="CANDIDATE", claim=text,
        protocol_id="", reps=1, reps_basis="one finite paired MI210 diagnostic",
        attestation_path=str(path), attestation_sha256=seal["content_sha256"],
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability=candidate_scope(plan), observation={"outcome_native": result["status"]},
        extra={"adapter": ADAPTER_ID, "result": result, "artifacts": seal["artifacts"]},
    )


@register(SOURCE_KIND)
def project(path):
    path = Path(path)
    seal, plan = _read(path)
    if not _eligible(seal, plan):
        raise ProjectionError(f"{SOURCE_KIND} {path}: complete native comparison required")
    return _tuple(path, seal, plan)


def frames_for_path(path, *, as_of):
    path = Path(path)
    seal, plan = _read(path)
    if not _eligible(seal, plan):
        return []
    return to_frames(_tuple(path, seal, plan), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)
