"""Check exact GPU-pool candidate reads and exclusion from ordinary model planning."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
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
CANDIDATE_TARGET_LIMIT = 16  # loop_beliefs.TIER_CAPS["target"]


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity_digest(identity):
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


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


def prepare_candidate(belief_context, ledger, out, selector, *, pinned_snapshot):
    argv = [sys.executable, "-BI", str(VIDYA / "loop_beliefs.py"), "prepare",
            "--consumer", "gpu-pool.candidate", "--target-json", json.dumps(selector),
            "--ledger", str(ledger), "--index", str(out / "index.yaml"),
            "--known-good", str(out / "candidate-known-good.json"),
            "--alarm-config", str(out / "alarm.yaml"), "--alarm-state", str(out / "alarm-state.json")]
    if pinned_snapshot:
        argv.append("--allow-stale-reader")
    done = subprocess.run(argv, cwd=ROOT, check=True, capture_output=True, text=True, timeout=20)
    return belief_context.validate_ready(json.loads(done.stdout))


def checked_reader_checkout(answer, *, pinned_snapshot):
    checked = answer.get("reader_checkout_check")
    require(checked is (not pinned_snapshot), "reader checkout check did not run as requested")
    if checked:
        checkout = answer.get("reader_checkout")
        require(isinstance(checkout, dict) and checkout.get("current") is True,
                "native planning requires a current reader checkout")
    return checked


def check_candidate_reads(belief_context, ledger, out, request, claims, reader_head, *, pinned_snapshot):
    identity = request["identity"]
    base = {"scope": "candidate", "build_sha": identity["source"]["commit"],
            "candidate_sha256": identity_digest(identity), "run_id": request["row_id"]}
    selectors = {op: ({**base, "op": op}, [c for c in claims if c["op"] == op], None)
                 for op in dict.fromkeys(c["op"] for c in claims)}
    first = next(iter(selectors.values()))[0]
    foreign_artifact = deepcopy(identity)
    foreign_artifact["artifacts"][0]["sha256"] = "0" * 64 if identity["artifacts"][0]["sha256"] != "0" * 64 else "1" * 64
    foreign_shim = deepcopy(identity)
    foreign_shim["shim"]["later_recreated_source_matches_receipt"] = not identity["shim"]["later_recreated_source_matches_receipt"]
    wrong_source = "0" * 40 if base["build_sha"] != "0" * 40 else "1" * 40
    prefix, version = base["run_id"].rsplit("-v", 1)
    for name, mutation in {
            "wrong_source": {"build_sha": wrong_source},
            "wrong_artifact": {"candidate_sha256": identity_digest(foreign_artifact)},
            "wrong_shim": {"candidate_sha256": identity_digest(foreign_shim)},
            "wrong_operator": {"op": "NOT_A_GPU_POOL_OPERATOR"},
            "wrong_run": {"run_id": f"{prefix}-v{int(version) + 1}"},
    }.items():
        selectors[name] = ({**first, **mutation}, [], "no_applicable_claims")
    selectors["missing_operator"] = ({k: v for k, v in first.items() if k != "op"}, [], "inapplicable_target")

    attempts = [c["claim_id"] for c in claims]
    reads = {}
    for name, (selector, expected, exclusion) in selectors.items():
        ready = prepare_candidate(belief_context, ledger, out, selector, pinned_snapshot=pinned_snapshot)
        state, evidence = ready["ledger_state"], ready["evidence"]
        require(state["fresh"] is True and state["head_hash"] == reader_head and state["ledger_path"] == str(ledger),
                "candidate reader did not check the current scratch ledger")
        checkout_checked = checked_reader_checkout(ready, pinned_snapshot=pinned_snapshot)
        by_id = {c["claim_id"]: c for c in expected}
        presented = evidence["claim_ids"]
        ids = set(presented)
        reason = exclusion
        if len(by_id) > CANDIDATE_TARGET_LIMIT and evidence["reasons"] == ["bounded"]:
            require(0 < len(ids) <= CANDIDATE_TARGET_LIMIT and ids <= by_id.keys()
                    and evidence["tiers"]["target"] == len(by_id), f"incorrect bounded candidate routing for {name}")
            reason = "bounded"
        else:
            require(ids == by_id.keys(), f"incorrect candidate routing for {name}")
        require(len(presented) == len(ids)
                and set(belief_context.reliable_claim_ids(evidence)) == ids
                and {c["claim_id"] for c in evidence["claims"]} == ids
                and len(evidence["claims"]) == len(ids)
                and all(c["source_kind"] == SOURCE and c["run"] == selector["run_id"]
                        and all(c[key] == selector[key] for key in ("build_sha", "candidate_sha256", "op"))
                        for c in evidence["claims"])
                and not (evidence["not_evidence_claim_ids"] or evidence["tried_index"]
                         or any(evidence["flagged"].values())), f"incorrect candidate routing for {name}")
        section = evidence["section"]
        require(evidence["nonempty_target"] == bool(ids) and bool(section) == bool(ids)
                and evidence["reasons"] == ([reason] if reason else []),
                f"incorrect candidate decision for {name}")
        if ids:
            require(ready["targets"] == [selector] and all(
                selector[key] in section for key in ("build_sha", "candidate_sha256", "op", "run_id"))
                and "quant unstated" not in section and "own weights" not in section
                and all(by_id[cid]["partition"] in section for cid in ids), f"candidate text drifted for {name}")
        reliance = belief_context.reliance(attempts, presented, evidence["not_evidence_claim_ids"])
        require(reliance["accepted"] == [cid for cid in attempts if cid in ids]
                and reliance["rejected"] == [{"claim_id": cid, "reason": "not_presented"}
                                             for cid in attempts if cid not in ids],
                f"incorrect candidate reliance for {name}")
        reads[name] = {"selector": selector, "claims": evidence["claims"], "reliance": reliance,
                       "reason": reason, "section_sha256": evidence["section_sha256"],
                       "checkout_checked": checkout_checked}
    return reads


def validate_native_result(capture, capture_sha, record, result_path):
    """Bind the completed producer receipt to the original sealed invocation."""
    native = record["native"]
    request = record["capture"]
    runs = native["runs"]
    grant = native.get("grant")
    # Each prepared GPU producer seals the scheduler grant's original path and parsed record.
    require("synthetic_control" not in native and isinstance(grant, dict) and grant.get("smoke") is False
            and grant.get("path") == str(SCRATCH_ROOT / "compute-flags/grants" / (request["row_id"] + ".grant"))
            and isinstance(grant.get("record"), dict)
            and native.get("owned_pid_reaped") is True, "native planning requires an official capture")
    ops = request["selected_ops"]
    require(ops and len(ops) == len(set(ops)), "native planning requires unique selected operators")
    if "seeds" in native:
        seeds = native["seeds"]
    else:
        # Older receipts describe a single block and may omit its top-level seed.
        seeds = [native.get("seed", runs[0]["seed"])] if runs else []
    require(isinstance(seeds, list) and seeds and all(type(seed) is int for seed in seeds)
            and len(seeds) == len(set(seeds)), "native planning requires a unique seed manifest")
    require([(run["seed"], run["op"]) for run in runs] == [(seed, op) for seed in seeds for op in ops]
            and all(type(run["seed"]) is int and run["rc"] == 0 and run.get("status") == "native_exit_recorded"
                    and run.get("generated_expected") == run["observed"] > 0 for run in runs)
            and not any(run["failed"] for run in runs), "native planning requires complete terminal invocations")
    raw_result = result_path.read_bytes()
    result = json.loads(raw_result)
    expected = {"row_id": request["row_id"], "capture": str(capture), "sha256": capture_sha,
                "projected": len(runs), "refused": 0, "failed": 0,
                **{key: sum(run[key] for run in runs) for key in ("observed", "passed", "unsupported")}}
    require(isinstance(result, dict) and all(type(result.get(key)) is type(value) and result[key] == value
                                              for key, value in expected.items()),
            "producer result disagrees with the sealed capture")
    samples = result.get("resident_samples")
    require(type(samples) is int and samples >= 2 * len(runs), "producer result lacks qualified residency")
    return {"path": str(result_path), "sha256": hashlib.sha256(raw_result).hexdigest()}


def check_capture(capture, research, out, *, pinned_snapshot=False, native_result=None):
    """Verify strict intake and preserve the candidate facts in an isolated result receipt."""
    require(native_result is None or not pinned_snapshot, "native planning requires checkout checks")
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
    native_binding = (validate_native_result(capture, capture_sha, record, native_result.resolve(strict=True))
                      if native_result is not None else None)
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
                                                "build_sha": request["identity"]["source"]["commit"],
                                                "candidate_sha256": identity_digest(request["identity"]),
                                                "scope_basis": "native"},
                "GPU-pool observation was assigned extra applicability")
        partition = f"{run['passed']} native supported passes, {run['unsupported']} unsupported and {len(run['failed'])} failures"
        require(partition in claim["display_text"] and support["grade"] == {"Q": "Judged", "T": "Located"}
                and source["locator"] == f"{run['log']}#sha256={run['log_sha256']}"
                and support["protocol_id"] == "" and support["reps"] is None
                and support["source_id"] == claim["source_id"],
                "candidate-local result or existing shared grade drifted")
        claims_summary.append({"claim_id": claim_id, "op": run["op"], "observed": run["observed"],
                               "passed": run["passed"], "unsupported": run["unsupported"],
                               "failed": len(run["failed"]), "seed": run["seed"], "rc": run["rc"],
                               "partition": partition})

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
                             "checkout_checked": checked_reader_checkout(ready.answer, pinned_snapshot=pinned_snapshot)}
    candidate_reads = check_candidate_reads(belief_context, ledger, out, request, claims_summary,
                                            readers[belief_context.CONSUMER]["ledger_head"],
                                            pinned_snapshot=pinned_snapshot)
    require(sha(capture) == capture_sha, "sealed input changed during planning replay")
    if native_binding is not None:
        require(sha(Path(native_binding["path"])) == native_binding["sha256"],
                "producer result changed during planning replay")
    return {
        "schema": "epyc.vidya.gpu_pool_candidate_scope.v1", "status": "passed",
        "scope": "candidate-local observations in the shared planning reader",
        "synthetic_control": record["native"].get("synthetic_control") is True,
        "official_native_acceptance": False, "positive_planning_context": True,
        "production_consumer_adoption": False, "native_planning_context": native_binding is not None,
        "native_producer_result": native_binding,
        "capture_path": str(capture), "capture_sha256": capture_sha, "row_id": request["row_id"],
        "candidate_identity": request["identity"], "native_grant": record["native"]["grant"],
        "claims": claims_summary, "ingest": report, "retry": retry, "readers": readers,
        "candidate_reads": candidate_reads,
        "sources_sha256": {
            "adapter": sha(VIDYA / "adapters/gpu_pool_native.py"),
            "reader": sha(VIDYA / "loop_beliefs.py"),
            "carrier": sha(VIDYA / "claim_tuple.py"),
            "read_counter": sha(VIDYA / "read_counter.py"),
            "canary": sha(Path(__file__)),
            "consumer": sha(research / CONSUMER_RELPATH),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=Path, help="official sealed native belief.json")
    parser.add_argument("--native-result", type=Path, help="matching producer RESULT.json after its complete check passes")
    parser.add_argument("--research", required=True, type=Path)
    parser.add_argument("--scratch", required=True, type=Path)
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if SCRATCH_ROOT not in scratch.parents:
        parser.error(f"--scratch must be a subdirectory of {SCRATCH_ROOT}")
    scratch.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="gpu-pool-exclusion-", dir=scratch))
    receipt = check_capture(args.capture, args.research.resolve(), out, native_result=args.native_result)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
