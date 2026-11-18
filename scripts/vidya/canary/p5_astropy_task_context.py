"""Ingest the original Astropy packet and replay the exact task planning context."""

import json
from pathlib import Path
import shutil
import sys

VIDYA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VIDYA))

from adapters import p5_astropy_scorer as adapter
from ingest_sources import ingest
from ledger import Ledger
from loop_beliefs import prepare

AS_OF = "2026-11-18T20:00:00Z"
CONSUMER = "p5.scorer_controls"
TASK = "VB-P5-SCORER-CONTROLS-WIRE"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, document):
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")


def run(packet: Path, output: Path, *, checkpoint=lambda: None):
    """Use a new ledger and retain every canary answer for independent review."""
    output.mkdir()
    checkpoint()
    result = packet / "official/RESULT.json"
    ledger = Ledger(output / "ledger.jsonl")
    with ledger.write_lock():
        receipt = ingest(ledger, adapter.SOURCE_KIND, [result], as_of=AS_OF, only_new=True)
    write_json(output / "ingest.json", receipt)
    require(receipt["rows_projected"] == 30 and receipt["frames_emitted"] == 90
            and not (receipt["refused"] or receipt["declined"] or receipt["missing"]),
            "original ingest did not project 30 statuses")
    require(not ledger.verify(), "scratch ledger chain does not verify")
    original = ledger.path.read_bytes()
    records = ledger.read_all()
    assertions = [record.frame["assertion"] for record in records]
    sources = [frame for frame in assertions if frame.get("source_kind") == adapter.SOURCE_KIND]
    supports = {frame["claim_id"]: frame for frame in assertions if "grade" in frame}
    require(len(sources) == len(supports) == 30 and all("applicability" not in row for row in sources)
            and all(frame["grade"] == {"Q": "Judged", "T": "Located"} and frame["protocol_id"] == ""
                    for frame in supports.values()), "observations do not preserve ledger grade or scope")

    index = output / "index.yaml"
    index.write_text("[]\n")
    config = output / "alarm-config.json"
    write_json(config, {"backend": "file", "file": {"path": str(output / "alarm.jsonl")}})
    target = {"scope": "task", "task_id": TASK}
    cases = {
        "exact-task": (CONSUMER, target),
        "wrong-task": (CONSUMER, {**target, "task_id": "VB-P5-UNRELATED-CONTROL"}),
        "wrong-consumer": ("unrelated.planner", target),
        "model-target": (CONSUMER, {"model_file": "Qwen3.8-27B-Q8_0.gguf", "backend": "gpu"}),
    }
    counts = {}
    for name, (consumer, selector) in cases.items():
        checkpoint()
        answer = prepare(
            consumer, selector, ledger=ledger.path, index_path=index, as_of=AS_OF,
            known_good=output / f"{name}.known-good.json", read_log=output / "reads.jsonl",
            alarm_config=config, alarm_state=output / "alarm-state.json",
            check_reader_checkout=False,
        )
        write_json(output / f"{name}.json", answer)
        require(answer["status"] == "ready" and not answer.get("read_log_error"),
                f"{name}: context reader refused")
        state, evidence = answer["ledger_state"], answer["evidence"]
        require(state["fresh"] and state["frame_count"] == evidence["frontier"] == 90
                and state["head_hash"] == records[-1].frame_hash, f"{name}: wrong scratch ledger head")
        displayed = evidence["claims"]
        if name == "exact-task":
            shown = {claim["claim_id"] for claim in displayed}
            bounded = {item["claim_id"] for item in evidence["omitted"] if item["reason"] == "bounded"}
            require(evidence["status"] == "presented" and evidence["nonempty_target"] and displayed
                    and len(shown) == len(displayed) and shown == set(evidence["claim_ids"])
                    and not shown & bounded and shown | bounded == set(supports)
                    and evidence["tiers"]["target"] == 30, "exact task did not recognize all named statuses")
            require(all(claim["grade"] == "Judged/Located" and claim["task_id"] == TASK
                        and claim["source_kind"] == adapter.SOURCE_KIND and claim["model_file"] == ""
                        and claim["claim_id"] in evidence["section"] for claim in displayed),
                    "rendered evidence scope or grade changed")
            require({claim["locator"].split("#", 1)[1].split(":", 1)[0] for claim in displayed}
                    == {"negative", "gold"} and {claim["value"] for claim in displayed} == {0.0, 1.0},
                    "bounded context did not show both arms and both statuses")
        else:
            require(not any(evidence["tiers"].values())
                    and not (displayed or evidence["claim_ids"] or evidence["section"]),
                    f"{name}: Astropy evidence escaped exact task scope")
        counts[name] = {"shown": len(displayed), "eligible": evidence["tiers"]["target"],
                        "section_sha256": evidence["section_sha256"]}

    checkpoint()
    # Alter one actor-independent copy so original native bytes remain unchanged.
    changed = output / "tamper-packet"
    shutil.copytree(packet, changed, ignore=shutil.ignore_patterns("review", "logs", "__pycache__"))
    gold = next((changed / "official").glob("attempt-*/gold-report.json"))
    gold.write_bytes(gold.read_bytes() + b" ")
    tamper_ledger = Ledger(output / "tamper.ledger.jsonl")
    with tamper_ledger.write_lock():
        rejected = ingest(tamper_ledger, adapter.SOURCE_KIND, [changed / "official/RESULT.json"],
                          as_of=AS_OF, only_new=True)
    write_json(output / "tamper-ingest.json", rejected)
    require(len(rejected["refused"]) == 1
            and rejected["refused"][0]["reason"] == f"{adapter.SOURCE_KIND}: arm artifact changed"
            and rejected["rows_projected"] == rejected["frames_emitted"] == 0,
            "altered raw report was admitted")
    checkpoint()
    require(ledger.path.read_bytes() == original, "planning reader altered the scratch ledger")
    return {
        "status": "PASS", "instance_id": adapter.INSTANCE, "consumer": CONSUMER, "task_id": TASK,
        "terminal_sha256": adapter.TERMINAL, "rows": 30, "frames": 90, "refusals": 0,
        "ledger_head": records[-1].frame_hash, "reader_checkout_check": False,
        "cases": counts, "tamper_refusals": 1, "tamper_frames": 0,
    }
