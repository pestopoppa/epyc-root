"""Replay original NPD1 native requests through the real planner without inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
FILING = Path("data/vidya/mi210-npd1-native-20261118")
SOURCE = "mi210-paired-raw"
METRIC = "native_request_tpot_ms"
SCRATCH_ROOT = Path("/mnt/raid0/llm/tmp")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reader", "research", "scratch"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--candidate-reader", type=Path,
                        help="Validate a candidate while keeping the current reader as an omission control")
    args = parser.parse_args()
    out = args.scratch.resolve()
    if SCRATCH_ROOT not in out.parents or out.exists():
        parser.error(f"--scratch must be a fresh subdirectory of {SCRATCH_ROOT}")
    out.mkdir(parents=True)
    sys.path.insert(0, str(ROOT))
    from scripts.vidya.producers import mi210_paired_capture as raw

    research = args.research.resolve(strict=True)
    sys.path[:0] = [str(research), str(research / "scripts/kernel_rnd")]
    from scripts.kernel_rnd.autokernel.loop import actors, belief_context

    filing = ROOT / FILING
    manifest = json.loads((filing / "SHA256.json").read_text())
    assert all(sha(filing / file) == digest for file, digest in manifest.items())
    # The raw reader binds declaration identity to the directory basename.
    filed_intent = json.loads((filing / "capture/declaration.json").read_text())
    run_id = filed_intent["run_id"]
    assert re.fullmatch(r"belief-[0-9a-f]{32}", run_id)
    staged = shutil.copytree(filing / "capture", out / run_id)
    assert all(sha(staged / Path(file).name) == digest for file, digest in manifest.items()
               if Path(file).parent == Path("capture"))
    run = raw.read(staged)
    intent = run["intent"]
    declaration = intent["declaration"]
    assert (run["state"], declaration["source"], declaration["mode"]) == (
        "complete", "NPD1-STEP3", "measurement")
    assert len(declaration["model"]) == len(run["attempts"]) == 4
    assert run_id == intent["run_id"]
    native_rows = {}
    for attempt in run["attempts"]:
        native = attempt["native"]
        assert attempt["run_id"] == run_id and native["state"] == "complete"
        request, = native["requests"]
        timing = request["timings"]
        locator = FILING / "capture" / f"attempt-{attempt['index']:02d}.json"
        native_rows[locator.name] = {
            "original_locator": str(locator),
            "original_run_id": attempt["run_id"], "native_pair": native["pair"],
            "native_arm": native["arm"], "predicted_ms": timing["predicted_ms"],
            "predicted_n": timing["predicted_n"],
            "native_tpot_ms": timing["predicted_ms"] / timing["predicted_n"],
        }

    index, alarm, ledger = (out / name for name in ("index.yaml", "alarm.yaml", "ledger.jsonl"))
    index.write_text("[]\n")
    alarm.write_text("backend: file\nfile:\n  path: " + str(out / "alarms.jsonl") + "\n")
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ingested = subprocess.run(
        [sys.executable, str(ROOT / "scripts/vidya/cli.py"), "--ledger", str(ledger), "--json",
         "ingest", SOURCE, "--path", str(staged), "--as-of", as_of, "--only-new"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    report = json.loads(ingested.stdout)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (4, 12, [])
    frames = [json.loads(line)["frame"] for line in ledger.read_text().splitlines()]
    sources = {frame["assertion"]["source_id"]: frame["assertion"] for frame in frames
               if frame["frame_type"].endswith("source_observed/v1")}
    support = {frame["assertion"]["claim_id"]: frame["assertion"] for frame in frames
               if frame["frame_type"].endswith("evidence_supports_claim/v1")}
    assert len(sources) == len(support) == 4
    assert all("applicability" not in source for source in sources.values())
    for assertion in support.values():
        source = sources[assertion["source_id"]]
        assert source["source_kind"] == SOURCE
        assert (assertion["metric"], assertion["unit"], assertion["metric_direction"],
                assertion["reps"], assertion["protocol_id"], assertion["grade"]) == (
            METRIC, "ms/token", "lower_better", 1, "", {"Q": "Judged", "T": "Located"})
        assert math.isclose(float(assertion["value"]),
                            native_rows[Path(source["locator"]).name]["native_tpot_ms"], rel_tol=1e-11)

    config = belief_context.BeliefConfig(
        root=args.reader.resolve(strict=True), ledger=ledger, index=index, alarm_config=alarm,
        known_good=out / "known-good.json", alarm_state=out / "alarm-state.json",
    )
    original = {"current_regime": {"model": {"path": declaration["model"][0]["path"]},
                                   "quant": "IQ4_XS", "backend": "cpu"}}
    unrelated = {"current_regime": {"model": {"path": "Qwen3.6-35B-A3B-Q4_K_M.gguf"},
                                    "quant": "Q4_K_M", "backend": "gpu"}}
    reader_baseline = None
    if args.candidate_reader is not None:
        baseline = belief_context.prepare(original, config)
        assert baseline.answer["reader_checkout"]["current"] is True
        assert baseline.evidence["reasons"] == ["no_applicable_claims"] and not baseline.section
        reader_baseline = {"reader_checkout": baseline.answer["reader_checkout"],
                           "reasons": baseline.evidence["reasons"], "claims": []}
        config = replace(config, root=args.candidate_reader.resolve(strict=True),
                         known_good=out / "candidate-known-good.json")

    captured = {}

    def before_backend(self, prompt, backend, env, context, *, belief):
        belief_context.require_ready(belief)
        captured.update(prompt=prompt, belief=belief)
        return actors.Abstain(reason="NPD1 offline planner canary"), list(support)

    planner = actors.AgentPlanner(workspace=out / "lane", belief=config)
    with patch.object(actors.AgentPlanner, "_proposal_from_agent", before_backend):
        planner.propose(original)
    ready = captured["belief"]
    evidence = ready.evidence
    shown_ids = set(evidence["not_evidence_claim_ids"])
    assert ready.answer["reader_checkout"]["current"] is True
    assert ready.section in captured["prompt"] and len(shown_ids) == 3
    assert ready.section.count("lower TPOT is better") == 3
    assert ready.section.count("One native request from the captured launch; no protocol or paired effect.") == 3
    assert (evidence["tiers"]["harness"], evidence["tiers_shown"]["harness"]) == (4, 3)
    assert not evidence["nonempty_target"] and not evidence["tried_index"]
    assert not belief_context.reliable_claim_ids(evidence)

    claims = evidence["claims"]
    assert len(claims) == 3 and {claim["claim_id"] for claim in claims} == shown_ids
    omitted, = evidence["omitted"]
    omitted_id, = set(support) - shown_ids
    assert (omitted["claim_id"], omitted["reason"]) == (omitted_id, "bounded")
    rows = []
    for claim in claims:
        assertion = support[claim["claim_id"]]
        source = sources[assertion["source_id"]]
        assert claim["locator"] == source["locator"] and claim["claim_id"] in ready.section
        assert (claim["tier"], claim["grade"], claim["unit"], claim["reps"],
                claim["not_evidence"], claim["model_file"]) == (
            "harness", "Judged/Located", "ms/token", 1, True, "")
        assert all(claim[key] is None for key in ("effect_rel", "anchor_value", "n_pairs"))
        assert not claim["outcome"] and not claim["mechanism_id"]
        native = native_rows[Path(claim["locator"]).name]
        assert math.isclose(claim["value"], native["native_tpot_ms"], rel_tol=1e-11)
        rows.append({**claim, **native, "metric": assertion["metric"],
                     "metric_direction": assertion["metric_direction"],
                     "protocol_id": assertion["protocol_id"]})

    receipt_log = out / actors.ACTOR_REPLY_DIR / belief_context.RECEIPT_LOG
    actor_receipt, = [json.loads(line) for line in receipt_log.read_text().splitlines()]
    reliance = actor_receipt["reliance"]
    assert reliance["declared"] == list(support) and reliance["accepted"] == []
    assert reliance["rejected"] == [
        {"claim_id": claim_id, "reason": "host_tier" if claim_id in shown_ids else "not_presented"}
        for claim_id in support]

    same_consumer = belief_context.prepare(unrelated, config)
    assert set(same_consumer.evidence["not_evidence_claim_ids"]) == shown_ids
    assert not same_consumer.evidence["nonempty_target"]
    assert not belief_context.reliable_claim_ids(same_consumer.evidence)
    for context in (original, unrelated):
        other = belief_context.prepare(
            context, replace(config, consumer="autopilot.planner",
                             known_good=out / "other-known-good.json"))
        assert other.evidence["reasons"] == ["no_applicable_claims"]
        assert not other.evidence["claims"] and not other.section

    assert all(sha(filing / file) == digest for file, digest in manifest.items())
    bounded = support[omitted_id]
    bounded_source = sources[bounded["source_id"]]
    rows.append({**native_rows[Path(bounded_source["locator"]).name],
                 "claim_id": omitted_id, "metric": bounded["metric"],
                 "metric_direction": bounded["metric_direction"], "unit": bounded["unit"],
                 "reps": bounded["reps"], "protocol_id": bounded["protocol_id"],
                 "grade": "Judged/Located", "omission_reason": omitted["reason"]})
    excerpt = out / "planner-context.txt"
    excerpt.write_text(ready.section + "\n")
    state = ready.ledger_state
    receipt = {
        "schema": "epyc.vidya.mi210_npd1_planning_canary.v1",
        "status": "candidate-passed" if args.candidate_reader else "passed",
        "as_of": evidence["as_of"], "original_filing": str(FILING), "original_run_id": run_id,
        "original_files_sha256": manifest, "original_terminal_row_sha256": run["terminal"]["row_sha256"],
        "original_weight_file_count": len(declaration["model"]), "native_model_applicability": {},
        "consumer": config.consumer, "reader_checkout": ready.answer["reader_checkout"],
        "reader_sha256": sha(config.reader()), "unmodified_reader_control": reader_baseline,
        "ingest": {"rows": 4, "frames": 12, "refused": 0},
        "ledger": {"head_hash": state["head_hash"], "frame_count": state["frame_count"],
                   "intake_index_sha256": state["freshness"]["index_sha256"], "scratch": True},
        "entry_point": "AgentPlanner.propose -> belief_context.prepare -> loop_beliefs.py prepare",
        "stop_boundary": "AgentPlanner._proposal_from_agent intercepted before backend execution",
        "actor_receipt_id": actor_receipt["receipt_id"], "reliance": reliance,
        "claims": rows, "shown": 3, "bounded": 1, "rendered_excerpt_sha256": sha(excerpt),
        "control_unrelated_consumer": {"consumer": "autopilot.planner", "claims": []},
        "control_unrelated_model": {"target": same_consumer.target,
                                    "background_claim_ids": sorted(shown_ids), "reliable_claim_ids": []},
        "scope": "Four original per-request native TPOT observations as consumer background only. "
                 "No modeled placement effect, paired inference or promotion. No inference rerun or "
                 "canonical ledger write.",
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(out)


if __name__ == "__main__":
    main()
