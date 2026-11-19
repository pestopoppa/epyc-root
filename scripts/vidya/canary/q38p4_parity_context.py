"""Replay a retained native Q38P-4 comparison in an isolated planning context."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

VIDYA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VIDYA))

from ingest_sources import ingest  # noqa: E402
from ledger import Ledger  # noqa: E402
from loop_beliefs import prepare, validate_ready  # noqa: E402
from producers import q38p4_parity as parity  # noqa: E402

CONSUMER = "autokernel.planner"
METRIC = "q38p4_greedy_divergence"


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def run(seal_path, output):
    seal_path = seal_path.resolve(strict=True)
    original = seal_path.read_bytes()
    seal, plan = parity.replay(seal_path)
    result = seal["result"]
    parity.require(plan["mode"] == "native" and result["status"] == "divergence",
                   "a completed native divergence is required")
    claim_id = f"clm_{parity.SOURCE_KIND}:{seal['content_sha256']}"
    target = {
        "scope": "candidate", "op": parity.OP, "run_id": plan["run_id"],
        "build_sha": plan["arms"]["llama"]["build_sha"],
        "candidate_sha256": parity.digest(parity.canonical(plan)),
    }
    captured = datetime.fromtimestamp(seal["completed_ns"] // 10**9 + 1, timezone.utc)
    as_of = captured.isoformat()
    output = output.resolve()
    output.mkdir()
    index = output / "index.yaml"
    index.write_text("[]\n")
    alarm_config = output / "alarm-config.json"
    write_json(alarm_config, {"backend": "file", "file": {"path": str(output / "alarms.jsonl")}})
    ledger = Ledger(output / "ledger.jsonl")
    with ledger.write_lock():
        report = ingest(ledger, parity.SOURCE_KIND, [seal_path], as_of=as_of, only_new=True)
    parity.require(report["units_matched"] == report["rows_projected"] == 1
                   and report["frames_emitted"] == 3
                   and not (report["refused"] or report["declined"] or report["missing"]),
                   f"strict native ingest failed: {report}")
    parity.require(not ledger.verify(), "native ledger verification failed")
    ledger_bytes = ledger.path.read_bytes()
    records = ledger.read_all()
    source, claim, support = (record.frame["assertion"] for record in records)
    scope = {key: value for key, value in target.items() if key != "scope"} | {"scope_basis": "native"}
    parity.require(source["source_kind"] == parity.SOURCE_KIND and source["applicability"] == scope
                   and source["locator"] == str(seal_path) and claim["claim_id"] == claim_id
                   and support["claim_id"] == claim_id and support["protocol_id"] == ""
                   and support["grade"] == {"Q": "Judged", "T": "Located"}
                   and support["observation"] == {"outcome_native": result["status"]}
                   and (support["metric"], support["value"], support["reps"]) == (METRIC, 1, 1),
                   "projected observation differs from the retained native result")

    other_artifact = deepcopy(plan)
    other_artifact["arms"]["vllm"]["runtime_sha256"] = "0" * 64
    run_prefix, revision = target["run_id"].rsplit("-r", 1)
    wrong_run = f"{run_prefix}-r{int(revision) + 1}"
    conversion = parity.load((seal_path.parent / "conversion.receipt.json").read_bytes())
    gguf = conversion["gguf"]
    same_model = {"model_file": Path(gguf["path"]).name, "model_sha256": gguf["sha256"], "backend": "gpu"}
    selectors = {
        "exact-candidate": (CONSUMER, target),
        "wrong-artifact": (CONSUMER, target | {"candidate_sha256": parity.digest(parity.canonical(other_artifact))}),
        "wrong-run": (CONSUMER, target | {"run_id": wrong_run}),
        "same-model": (CONSUMER, same_model),
        "production-lineup": ("autopilot.planner", {"scope": "lineup", "stack_regime": "production"}),
    }
    reads = {}
    for name, (consumer, selector) in selectors.items():
        answer = validate_ready(prepare(
            consumer, selector, ledger=ledger.path, index_path=index, as_of=as_of,
            known_good=output / f"{name}.known-good.json", read_log=output / "reads.jsonl",
            alarm_config=alarm_config, alarm_state=output / "alarm-state.json",
            check_reader_checkout=True,
        ))
        write_json(output / f"{name}.json", answer)
        state, evidence = answer["ledger_state"], answer["evidence"]
        parity.require(not answer.get("read_log_error") and state["ledger_path"] == str(ledger.path)
                       and state["frame_count"] == evidence["frontier"] == 3
                       and state["head_hash"] == records[-1].frame_hash,
                       f"{name}: reader did not report the verified scratch ledger")
        if name == "exact-candidate":
            parity.require(evidence["status"] == "presented" and evidence["nonempty_target"]
                           and evidence["claim_ids"] == [claim_id] and len(evidence["claims"]) == 1,
                           "exact candidate did not get the native diagnostic")
            row, = evidence["claims"]
            expected = {"claim_id": claim_id, "source_kind": parity.SOURCE_KIND, "grade": "Judged/Located",
                        "tier": "target", "locator": str(seal_path), "value": 1, "unit": "comparisons", "reps": 1,
                        "run": target["run_id"], "build_sha": target["build_sha"], "op": target["op"],
                        "candidate_sha256": target["candidate_sha256"]}
            parity.require(all(row.get(key) == value for key, value in expected.items())
                           and claim_id in evidence["section"] and f"{METRIC}: 1 comparisons (n=1)" in evidence["section"],
                           "exact planning context lost the native diagnostic or its scope")
        else:
            parity.require(evidence["reasons"] == ["no_applicable_claims"]
                           and not (evidence["claim_ids"] or evidence["claims"] or evidence["section"])
                           and not any(evidence["tiers"].values()), f"{name}: diagnostic escaped candidate scope")
        reads[name] = {"consumer": consumer, "selector": selector, "claim_ids": evidence["claim_ids"],
                       "reasons": evidence["reasons"], "section_sha256": evidence["section_sha256"]}
    parity.require(ledger.path.read_bytes() == ledger_bytes and parity.replay(seal_path) == (seal, plan)
                   and seal_path.read_bytes() == original, "canary changed the ledger or original capture")
    return {
        "schema": "epyc.q38p4.native_planning_context.v1", "status": "passed", "as_of": as_of,
        "claim_id": claim_id, "grade": support["grade"], "native_status": result["status"],
        "tokens_equal": result["tokens_equal"], "stop_equal": result["stop_equal"],
        "seal_sha256": parity.digest(original), "content_sha256": seal["content_sha256"],
        "ledger_sha256": parity.digest(ledger_bytes), "ledger_head": records[-1].frame_hash,
        "ingest": report, "reads": reads, "reader_checkout": answer["reader_checkout"],
        "reader_sha256": {name: parity.digest((VIDYA / name).read_bytes()) for name in (
            "loop_beliefs.py", "claim_tuple.py", "ingest_sources.py", "adapters/q38p4_parity.py",
            "producers/q38p4_parity.py", "canary/q38p4_parity_context.py",
        )},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seal", type=Path)
    parser.add_argument("output", type=Path, help="new directory for the isolated ledger and reader answers")
    args = parser.parse_args()
    receipt = run(args.seal, args.output)
    path = args.output / "receipt.json"
    write_json(path, receipt)
    print(path)


if __name__ == "__main__":
    main()
