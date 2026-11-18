"""Replay the retained KPF-17 observation through the shared task planning reader."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

VIDYA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VIDYA))

from ingest_sources import ingest  # noqa: E402
from ledger import Ledger  # noqa: E402
from loop_beliefs import prepare  # noqa: E402

TASK_ID = "VB-KPF17-MAP-REVALIDATION-WIRE"
CONSUMER = "kvfork.planner"
CLAIM_ID = "clm_kpf17-map-c539c3ecbf4ab11b1bf388ecb6c481486aa61128af86e1cbc00568596c715ce6"
MECHANISM_ID = "kpf17_map_revalidation_fixture_refused"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def run(package: Path, output: Path, *, check_reader_checkout: bool = True,
        checkpoint=lambda: None) -> dict:
    """Stop at context assembly and retain each answer in an isolated output directory."""
    package = package.resolve(strict=True)
    output = output.resolve()
    output.mkdir()
    checkpoint()
    result = json.loads((package / "RESULT.json").read_text())
    require(result.get("row_id") == "vb-kpf17-map-revalidation-20261118"
            and result.get("status") == "PASS" and result.get("result_kind") == "full",
            "original official fixture result required")
    sidecar = package / "attempts" / result["nonce"] / "belief_measurements.jsonl"
    as_of = (package / "review/as-of.txt").read_text().strip()
    ledger = Ledger(output / "ledger.jsonl")
    with ledger.write_lock():
        report = ingest(ledger, "kv-prefix-fork", [sidecar], as_of=as_of, only_new=True)
    write_json(output / "ingest.json", report)
    require(report["rows_projected"] == 1 and report["frames_emitted"] == 3
            and not (report["refused"] or report["declined"] or report["missing"]),
            "strict KPF-17 projection failed")
    require(not ledger.verify(), "KPF-17 scratch ledger failed verification")
    original = ledger.path.read_bytes()
    records = ledger.read_all()
    source, claim, support = (record.frame["assertion"] for record in records)
    require("applicability" not in source and claim["claim_id"] == CLAIM_ID
            and support["grade"] == {"Q": "Judged", "T": "Located"}
            and support["protocol_id"] == "", "projected claim differs from the native observation")
    index = output / "index.yaml"
    index.write_text("[]\n")
    config = output / "alarm-config.json"
    write_json(config, {"backend": "file", "file": {"path": str(output / "alarms.jsonl")}})
    target = {"scope": "task", "task_id": TASK_ID}
    cases = {
        "exact-task": (CONSUMER, target),
        "wrong-task": (CONSUMER, {**target, "task_id": "VB-KPF17-UNRELATED-CONTROL"}),
        "wrong-consumer": ("unrelated.planner", target),
        "cpu-model": ("autokernel.planner", {"model_file": "Qwen3.6-35B-A3B-MTP-Q8_0.gguf", "backend": "cpu"}),
        "gpu-model": ("autokernel.planner", {"model_file": "Qwen3.8-27B-Q8_0.gguf", "backend": "gpu"}),
        "lineup": ("autopilot.planner", {"scope": "lineup", "stack_regime": "production"}),
    }
    counts = {}
    for name, (consumer, selector) in cases.items():
        checkpoint()
        answer = prepare(
            consumer, selector, ledger=ledger.path, index_path=index, as_of=as_of,
            known_good=output / f"{name}.known-good.json", read_log=output / "reads.jsonl",
            alarm_config=config, alarm_state=output / "alarm-state.json",
            check_reader_checkout=check_reader_checkout,
        )
        write_json(output / f"{name}.json", answer)
        require(answer["status"] == "ready" and not answer.get("read_log_error"),
                f"{name}: reader did not become ready")
        state, evidence = answer["ledger_state"], answer["evidence"]
        require(state["fresh"] and state["frame_count"] == evidence["frontier"] == 3
                and state["head_hash"] == records[-1].frame_hash,
                f"{name}: reader did not use the verified scratch head")
        if name == "exact-task":
            require(evidence["status"] == "presented" and evidence["nonempty_target"]
                    and evidence["claim_ids"] == [CLAIM_ID] and len(evidence["claims"]) == 1,
                    "exact task did not get the native claim")
            row, = evidence["claims"]
            require(row["grade"] == "Judged/Located" and row["task_id"] == TASK_ID
                    and row["locator"] == source["locator"] and row["model_file"] == ""
                    and f"task {TASK_ID}" in evidence["section"] and CLAIM_ID in evidence["section"]
                    and claim["display_text"] in evidence["section"], "native claim text or scope changed")
            history, = evidence["tried_index"]
            require(history["claim_id"] == CLAIM_ID and history["mechanism_id"] == MECHANISM_ID
                    and history["in_section"]
                    and f"Tried for task {TASK_ID}: {MECHANISM_ID}" in evidence["section"],
                    "exact task tried history was not rendered")
        else:
            require(evidence["reasons"] == ["no_applicable_claims"]
                    and not any(evidence["tiers"].values())
                    and not (evidence["claims"] or evidence["claim_ids"] or evidence["tried_index"]
                             or evidence["section"]), f"{name}: native claim escaped task scope")
        counts[name] = {"claims": len(evidence["claims"]), "tried": len(evidence["tried_index"]),
                        "section_sha256": evidence["section_sha256"]}
    checkpoint()
    require(ledger.path.read_bytes() == original, "planning reader changed the native ledger")
    return {"schema": "epyc.kpf17.task_planning_context.v1", "status": "PASS", "claim_id": CLAIM_ID,
            "task_id": TASK_ID, "consumer": CONSUMER, "frame_count": len(records),
            "head_hash": records[-1].frame_hash, "reader_checkout_check": check_reader_checkout,
            "cases": counts, "runtime_cpus": sorted(os.sched_getaffinity(0))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = run(args.package, args.output)
    write_json(args.output / "RESULT.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
