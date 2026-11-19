"""Project a write-side qwen4exp CPU loader seal through the shared claim carrier."""

from pathlib import Path

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames
from adapters.quality_pack_comparison import _validator
from producers.qwen4exp_cpu_loader_contract import SEAL_NAME, SOURCE_KIND, TERMINAL, replay, selector

ADAPTER_ID = "vidya.adapters.qwen4exp_cpu_loader/v1"
AUTHORITY = "measurement"


def units(path):
    path = Path(path)
    return [path] if path.is_file() else sorted(path.rglob(SEAL_NAME))


def _validate(path):
    try:
        tool, validator_sha = _validator()
        return replay(path, tool, validator_sha)
    except (OSError, KeyError, ValueError, TypeError, IndexError, OverflowError, RecursionError) as exc:
        raise ProjectionError(f"{SOURCE_KIND} {path}: {exc}") from exc


def _tuple(path, record, plan, state, evidence):
    refusals = [arm for arm, check in state["checks"].items()
                if not check["semantic_matches"] or check["finish"] != check["expected_finish"]]
    response = ", ".join(sorted(refusals)) if refusals else "none"
    claim = (
        f"Qwen4exp CPU loader diagnostic recorded both named norm loads per arm and two owned requests. "
        f"Responses refused by the pinned semantic/finish checks: {response}. "
        "GGUF headers and pinned loader sources give v10 [10240] and C13 [2560, 4]. Scope is this CPU capture."
    )
    scope = selector(plan, state["validator_source_sha256"])
    return ClaimTuple(
        measurement_id=f"{SOURCE_KIND}:{record['content_sha256']}",
        metric="qwen4exp_cpu_loader_response_refusals", value=len(refusals), date=record["completed_at"][:10],
        category="CANDIDATE", claim=claim, metric_direction="lower_better", unit="responses",
        protocol_id="", reps=1, reps_basis="one finite paired native CPU diagnostic",
        attestation_path=str(path), attestation_sha256=record["content_sha256"],
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={key: value for key, value in scope.items() if key != "scope"} | {"scope_basis": "native"},
        observation={"outcome_native": state["status"]},
        extra={"adapter": ADAPTER_ID, "response_checks": state["checks"], "raw_equality": state["comparison"],
               "load_witnesses": evidence, "model_shards": plan["model_shards"], "runtimes": plan["arms"],
               "request_plan_sha256": state["request_plan_sha256"], "grant_sha256": state["grant_sha256"]},
    )


@register(SOURCE_KIND)
def project(path):
    path = Path(path)
    record, plan, state, evidence = _validate(path)
    if state["status"] not in TERMINAL:
        raise ProjectionError(f"{SOURCE_KIND} {path}: incomplete CPU diagnostic")
    return _tuple(path, record, plan, state, evidence)


def frames_for_path(path, *, as_of):
    path = Path(path)
    record, plan, state, evidence = _validate(path)
    if state["status"] not in TERMINAL:
        return []
    return to_frames(_tuple(path, record, plan, state, evidence), as_of=as_of,
                     adapter_id=ADAPTER_ID, authority=AUTHORITY)
