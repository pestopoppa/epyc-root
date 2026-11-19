"""Replay the original R23-1 EOF seal at the real planner's pre-backend boundary."""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
SEAL = Path(__file__).resolve().parents[1] / "full/NATIVE.json"
VIDYA = ROOT / "scripts/vidya"
SOURCE = "r231-eof-capture"
SCRATCH_ROOT = Path("/mnt/raid0/llm/tmp")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if SCRATCH_ROOT not in scratch.parents:
        parser.error(f"--scratch must be under {SCRATCH_ROOT}")
    scratch.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="eof-context-", dir=scratch))
    research = args.research.resolve()
    sys.path[:0] = [str(research), str(research / "scripts/kernel_rnd")]

    from scripts.kernel_rnd.autokernel.loop import actors, belief_context

    seal_sha = sha(SEAL)
    ledger = out / "ledger.jsonl"
    index = out / "index.yaml"
    index.write_text("[]\n")
    alarm_config = out / "alarm.yaml"
    alarm_config.write_text(f"backend: file\nfile:\n  path: {json.dumps(str(out / 'alarms.jsonl'))}\n")
    as_of = datetime.now(timezone.utc).isoformat()
    command = [sys.executable, "-B", str(VIDYA / "cli.py"), "--ledger", str(ledger),
               "--json", "ingest", SOURCE, "--path", str(SEAL.relative_to(ROOT)),
               "--as-of", as_of, "--only-new"]
    ingested = json.loads(subprocess.check_output(command, cwd=ROOT, text=True))
    assert (ingested["rows_projected"], ingested["frames_emitted"]) == (1, 3), ingested
    assert not (ingested["refused"] or ingested["declined"] or ingested["missing"]), ingested
    ledger_sha = sha(ledger)
    retry = json.loads(subprocess.check_output(command, cwd=ROOT, text=True))
    assert (retry["frames_emitted"], retry["frames_skipped"]) == (0, 3), retry
    assert sha(ledger) == ledger_sha
    frames = [json.loads(line)["frame"] for line in ledger.read_text().splitlines()]
    (support,) = [frame["assertion"] for frame in frames
                  if frame["frame_type"].endswith("/evidence_supports_claim/v1")]
    assert support["protocol_id"] == ""
    claim_id = support["claim_id"]

    sync_marker = ledger.with_suffix(".jsonl.sync.json")
    assert not sync_marker.exists()
    config = belief_context.BeliefConfig(
        root=ROOT, ledger=ledger, index=index, known_good=out / "known-good.json",
        alarm_config=alarm_config, alarm_state=out / "alarm-state.json",
    )
    context = {"current_regime": {"model": {"path": "Qwen3.6-35B-A3B-Q4_K_M.gguf"},
                                  "quant": "Q4_K_M", "backend": "cpu"}}
    captured = {}

    def capture_prompt(self, prompt, backend, env, context, *, belief):
        captured.update(prompt=prompt, belief=belief_context.require_ready(belief))
        return actors.Abstain(reason="R23-1 EOF canary intercepted before the backend"), [claim_id]

    planner = actors.AgentPlanner(workspace=out / "workspace", belief=config)
    with (patch.object(actors.AgentPlanner, "_proposal_from_agent", capture_prompt),
          patch.object(actors, "_run_agent", side_effect=AssertionError("entered planner backend"))):
        assert isinstance(planner.propose(context), actors.Abstain)
    ready = captured["belief"]
    state, evidence = ready.ledger_state, ready.evidence
    assert state["fresh"] is True and state["frame_count"] == 3
    assert state["ledger_path"] == str(ledger) and ready.answer["reader_checkout"]["current"] is True
    assert state["freshness"]["was_fresh"] is False
    assert state["freshness"]["sync_action"] == "ingested"
    assert state["freshness"]["frames_emitted"] == 0 and state["freshness"]["index_sha256"] == sha(index)
    marker = json.loads(sync_marker.read_text())
    assert marker["index_entries"] == 0 and sha(index) in marker["seen_sha256"]
    (claim,) = evidence["claims"]
    assert (claim["claim_id"], claim["source_kind"], claim["grade"], claim["tier"],
            claim["value"], claim["unit"]) == (claim_id, SOURCE, "Judged/Located", "harness", 9, "cases")
    assert claim["not_evidence"] and not claim["model_file"] and not evidence["nonempty_target"]
    assert evidence["not_evidence_claim_ids"] == [claim_id] and evidence["claim_ids"] == []
    assert not belief_context.reliable_claim_ids(evidence) and not evidence["tried_index"]
    assert ready.section in captured["prompt"] and claim_id in ready.section
    for phrase in ("Loop-infrastructure facts (harness tier)", "nine model-free behavior cases",
                   "loopback model-selection EOF", "simple/PTY EOF, blank, slash and text",
                   "Scope is CLI/console behavior only."):
        assert phrase in ready.section, phrase

    receipt_log = out / actors.ACTOR_REPLY_DIR / belief_context.RECEIPT_LOG
    (actor_receipt,) = [json.loads(line) for line in receipt_log.read_text().splitlines()]
    assert actor_receipt["reliance"] == {
        "declared": [claim_id], "accepted": [],
        "rejected": [{"claim_id": claim_id, "reason": "host_tier"}],
    }
    other = belief_context.prepare(
        context, replace(config, consumer="autopilot.planner", known_good=out / "other-known-good.json"),
    )
    assert other.ledger_state["head_hash"] == state["head_hash"]
    assert other.ledger_state["freshness"]["was_fresh"] is True
    assert not other.evidence["claims"] and not other.section
    assert sha(SEAL) == seal_sha and sha(ledger) == ledger_sha

    excerpt = out / "planner-context.txt"
    excerpt.write_text(ready.section + "\n")
    prompt_file = out / "planner-prompt.txt"
    prompt_file.write_text(captured["prompt"])
    assert sha(prompt_file) == actor_receipt["call"]["prompt_sha256"]
    consumer_src = Path("scripts/kernel_rnd/autokernel/loop")
    write_json(out / "receipt.json", {
        "schema": "epyc.vidya.r231_eof_planning_canary.v1", "status": "passed",
        "entry_point": "AgentPlanner.propose -> belief_context.prepare -> loop_beliefs.py prepare",
        "stop_boundary": "AgentPlanner._proposal_from_agent intercepted before backend",
        "as_of": evidence["as_of"], "consumer": config.consumer,
        "seal": str(SEAL.relative_to(ROOT)), "seal_sha256": seal_sha,
        "ingest": ingested, "retry": retry, "ledger_state": state, "ledger_sha256": ledger_sha,
        "sync_marker": marker, "reader_checkout": ready.answer["reader_checkout"],
        "claim": claim, "protocol_id": support["protocol_id"],
        "tiers_shown": evidence["tiers_shown"], "nonempty_target": evidence["nonempty_target"],
        "decision_eligible_claim_ids": belief_context.reliable_claim_ids(evidence),
        "other_consumer": {"name": other.answer["consumer"], "claims": other.evidence["claims"],
                           "head_hash": other.ledger_state["head_hash"]},
        "actor_receipt": actor_receipt, "excerpt_sha256": sha(excerpt),
        "root_sources_sha256": {str(path.relative_to(ROOT)): sha(path) for path in (
            Path(__file__).resolve(), VIDYA / "loop_beliefs.py", VIDYA / "sync.py",
            VIDYA / "claim_tuple.py", VIDYA / "ingest_sources.py",
            VIDYA / "adapters/r231_eof_capture.py",
        )},
        "research_sources_sha256": {str(consumer_src / name): sha(research / consumer_src / name)
                                    for name in ("actors.py", "belief_context.py")},
        "research_checkout": subprocess.check_output(
            ["git", "-C", str(research), "rev-parse", "HEAD"], text=True,
        ).strip(),
    })
    print(out)


if __name__ == "__main__":
    main()
