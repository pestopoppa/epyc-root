"""Check the GPU-pool capture boundary against the real AutoKernel planning reader."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIDYA = ROOT / "scripts/vidya"
SCRATCH_ROOT = Path("/mnt/raid0/llm/tmp")
CONSUMER_RELPATH = Path("scripts/kernel_rnd/autokernel/loop/belief_context.py")
SOURCE = "gpu-pool-native"
MODEL = "Qwen3.6-35B-A3B-Q4_K_M.gguf"
CONTEXT = {"current_regime": {"model": {"path": MODEL}, "quant": "Q4_K_M", "backend": "gpu"}}


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ingest(capture, ledger):
    done = subprocess.run(
        [sys.executable, "-BI", str(VIDYA / "cli.py"), "--ledger", str(ledger), "--json",
         "ingest", SOURCE, "--path", str(capture), "--as-of", datetime.now(timezone.utc).isoformat(),
         "--only-new"], cwd=ROOT, check=True, capture_output=True, text=True, timeout=20,
    )
    return json.loads(done.stdout)


def consumer_for(research):
    sys.path.insert(0, str(research))
    try:
        from scripts.kernel_rnd.autokernel.loop import belief_context
    finally:
        sys.path.remove(str(research))
    require(Path(belief_context.__file__).resolve() == (research / CONSUMER_RELPATH).resolve(),
            "AutoKernel consumer came from another checkout")
    return belief_context


def prepare(belief_context, ledger, out, *, pinned_snapshot=False):
    index = out / "index.yaml"
    index.write_text("[]\n")
    alarm = out / "alarm.yaml"
    alarm.write_text(f"backend: file\nfile:\n  path: {json.dumps(str(out / 'alarms.jsonl'))}\n")
    config = belief_context.BeliefConfig(root=ROOT, ledger=ledger, index=index,
                                         known_good=out / "autokernel-known-good.json", alarm_config=alarm,
                                         alarm_state=out / "alarm-state.json")

    def run_reader(argv, **kwargs):
        # The host controls carry a hashed source snapshot without git metadata.
        extra = ["--allow-stale-reader"] if argv[2] == "prepare" else []
        return subprocess.run([argv[0], "-BI", *argv[1:], *extra], **kwargs)

    runner = run_reader if pinned_snapshot else None
    return {
        config.consumer: belief_context.prepare(CONTEXT, config, runner=runner),
        "autopilot.planner": belief_context.prepare(
            CONTEXT, replace(config, consumer="autopilot.planner",
                             known_good=out / "other-known-good.json"), runner=runner),
    }


def check_capture(capture, research, out, *, pinned_snapshot=False):
    """Verify strict intake and preserve the candidate facts in an isolated result receipt."""
    capture = capture.resolve(strict=True)
    capture_sha = sha(capture)
    ledger = out / "ledger.jsonl"
    require(not ledger.exists(), "scope control requires a fresh scratch ledger")
    report = ingest(capture, ledger)
    count = report["rows_projected"]
    require(count > 0 and report["frames_emitted"] == 3 * count and report["units_projected"] == 1
            and not (report["refused"] or report["declined"] or report["missing"]),
            f"strict native intake did not project a complete sealed capture: {report}")
    before_retry = ledger.read_bytes()
    retry = ingest(capture, ledger)
    require(retry["frames_emitted"] == 0 and retry["frames_skipped"] == 3 * count
            and ledger.read_bytes() == before_retry, "retry altered the isolated ledger")
    record = json.loads(capture.read_text())
    request = record["capture"]
    runs = record["native"]["runs"]
    require(sha(capture) == capture_sha and len(runs) == count, "sealed input changed or count drifted")
    frames = [json.loads(line)["frame"] for line in ledger.read_text().splitlines()]
    kinds = {}
    for frame in frames:
        kinds.setdefault(frame["frame_type"].split("/")[-2], []).append(frame["assertion"])
    sources = {entry["source_id"]: entry for entry in kinds["source_observed"]}
    claims = {entry["claim_id"]: entry for entry in kinds["claim_proposed"]}
    supports = {entry["claim_id"]: entry for entry in kinds["evidence_supports_claim"]}
    require(len(frames) == 3 * count and len(sources) == len(claims) == len(supports) == count,
            "scratch ledger triplet counts differ from intake")
    claims_summary = []
    for i, run in enumerate(runs):
        claim_id = f"clm_gpu-pool:{record['sha256']}:{i}"
        claim, support = claims[claim_id], supports[claim_id]
        source = sources[claim["source_id"]]
        require(source["source_kind"] == SOURCE and source["title"] == "native_supported_pass_count"
                and source["applicability"] == {"op": run["op"], "run_id": request["row_id"],
                                                "scope_basis": "native"},
                "GPU-pool observation was assigned extra applicability")
        partition = f"{run['passed']} native supported passes, {run['unsupported']} unsupported and {len(run['failed'])} failures"
        require(partition in claim["display_text"] and support["grade"] == {"Q": "Judged", "T": "T0"}
                and support["protocol_id"] == "" and support["source_id"] == claim["source_id"],
                "candidate-local result or existing shared grade drifted")
        claims_summary.append({"claim_id": claim_id, "op": run["op"], "observed": run["observed"],
                               "passed": run["passed"], "unsupported": run["unsupported"],
                               "failed": len(run["failed"]), "seed": run["seed"], "rc": run["rc"]})

    belief_context = consumer_for(research)
    readers = {}
    for consumer, ready in prepare(belief_context, ledger, out, pinned_snapshot=pinned_snapshot).items():
        state, evidence = ready.ledger_state, ready.evidence
        require(state["frame_count"] == len(frames) and state["ledger_path"] == str(ledger)
                and state["fresh"] is True and state["head_hash"], "reader checked another ledger")
        require(evidence["reasons"] == ["no_applicable_claims"] and evidence["empty_targets"] == [MODEL]
                and not (evidence["claims"] or evidence["claim_ids"] or evidence["not_evidence_claim_ids"]
                         or evidence["nonempty_target"] or evidence["tried_index"] or ready.section
                         or belief_context.reliable_claim_ids(evidence)), f"GPU-pool scope leaked to {consumer}")
        attempted = list(claims)
        reliance = belief_context.reliance(attempted, evidence["claim_ids"], evidence["not_evidence_claim_ids"])
        require(not reliance["accepted"] and reliance["rejected"] == [
            {"claim_id": cid, "reason": "not_presented"} for cid in attempted],
            f"GPU-pool reliance was not blocked for {consumer}")
        readers[consumer] = {"ledger_head": state["head_hash"], "model_target": MODEL,
                             "visible_claims": [], "reliance": reliance,
                             "checkout_checked": ready.answer["reader_checkout_check"]}
    return {
        "schema": "epyc.vidya.gpu_pool_scope_exclusion.v1", "status": "passed",
        "scope": "candidate-local native observations excluded from ordinary model planning context",
        "synthetic_control": record["native"].get("synthetic_control") is True,
        "official_native_acceptance": False, "positive_planning_context": False,
        "capture_path": str(capture), "capture_sha256": capture_sha, "row_id": request["row_id"],
        "candidate_identity": request["identity"], "native_grant": record["native"]["grant"],
        "claims": claims_summary, "ingest": report, "retry": retry, "readers": readers,
        "sources_sha256": {
            "adapter": sha(VIDYA / "adapters/gpu_pool_native.py"),
            "reader": sha(VIDYA / "loop_beliefs.py"),
            "consumer": sha(research / CONSUMER_RELPATH),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=Path, help="official sealed native belief.json")
    parser.add_argument("--research", required=True, type=Path)
    parser.add_argument("--scratch", required=True, type=Path)
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if SCRATCH_ROOT not in scratch.parents:
        parser.error(f"--scratch must be a subdirectory of {SCRATCH_ROOT}")
    scratch.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="gpu-pool-exclusion-", dir=scratch))
    receipt = check_capture(args.capture, args.research.resolve(), out)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
