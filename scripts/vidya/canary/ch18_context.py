"""Replay CH18's filed observation through the real AutoKernel planner without inference."""
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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
VIDYA = ROOT / "scripts/vidya"
FILING = Path("data/vidya/ch18-trial-20261117/merge_trial.json")
SOURCE = "ch18-merge-trial"
BASE = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
UPSTREAM = "4e201388c319fc9f747fbe6a666793e2dc2a6d8e"
SCRATCH_ROOT = Path("/mnt/raid0/llm/tmp")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if SCRATCH_ROOT not in scratch.parents:
        parser.error(f"--scratch must be a subdirectory of {SCRATCH_ROOT}")
    scratch.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="ch18-context-", dir=scratch))
    research = args.research.resolve()
    sys.path[:0] = [str(research), str(research / "scripts/kernel_rnd")]

    from scripts.kernel_rnd.autokernel.loop import actors, belief_context

    ledger = out / "ledger.jsonl"
    index = out / "index.yaml"
    index.write_text("[]\n")
    alarm = out / "alarm.yaml"
    alarm.write_text(f"backend: file\nfile:\n  path: {out / 'alarms.jsonl'}\n")
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ingested = subprocess.run(
        [sys.executable, str(VIDYA / "cli.py"), "--ledger", str(ledger), "--json", "ingest",
         SOURCE, "--path", str(FILING), "--as-of", as_of, "--only-new"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    report = json.loads(ingested.stdout)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (1, 3, [])
    frame_records = [json.loads(line) for line in ledger.read_text().splitlines()]
    (support,) = [row["frame"]["assertion"] for row in frame_records
                  if row["frame"]["frame_type"].endswith("evidence_supports_claim/v1")]
    assert support["protocol_id"] == ""
    config = belief_context.BeliefConfig(root=ROOT, ledger=ledger, index=index,
                                         known_good=out / "known-good.json", alarm_config=alarm,
                                         alarm_state=out / "alarm-state.json")
    context = {"current_regime": {"model": {"path": "Qwen3.6-35B-A3B-Q4_K_M.gguf"},
                                   "quant": "Q4_K_M", "backend": "cpu"}}
    captured = {}

    def stop_before_agent(self, prompt, backend, env, context, *, belief):
        belief_context.require_ready(belief)
        captured.update(prompt=prompt, belief=belief)
        declared = belief.evidence["not_evidence_claim_ids"]
        return actors.Abstain(reason="CH18 context canary at planner call boundary"), declared

    planner = actors.AgentPlanner(workspace=out / "lane", belief=config)
    with patch.object(actors.AgentPlanner, "_proposal_from_agent", stop_before_agent):
        planner.propose(context)
    ready = captured["belief"]
    evidence = ready.evidence
    (claim,) = evidence["claims"]
    claim_id = claim["claim_id"]
    assert (claim["source_kind"], claim["grade"], claim["tier"], claim["value"], claim["unit"]) == (
        SOURCE, "Judged/Located", "harness", 98, "paths")
    assert claim["not_evidence"] and not claim["model_file"] and not evidence["nonempty_target"]
    assert not belief_context.reliable_claim_ids(evidence) and not evidence["tried_index"]
    assert ready.section in captured["prompt"]
    for expected in (BASE, UPSTREAM, "98 conflicted paths", "worktree_removed=True",
                     "merge_aborted=True", "conflict inventory only", "promotion"):
        assert expected in ready.section, expected

    receipt_log = out / actors.ACTOR_REPLY_DIR / belief_context.RECEIPT_LOG
    (actor_receipt,) = [json.loads(line) for line in receipt_log.read_text().splitlines()]
    refusal = actor_receipt["reliance"]
    assert refusal["accepted"] == [] and refusal["rejected"] == [
        {"claim_id": claim_id, "reason": "host_tier"}]
    other = belief_context.prepare(context, replace(config, consumer="autopilot.planner",
                                                     known_good=out / "other-known-good.json"))
    assert not other.evidence["claims"] and not other.section

    excerpt = out / "planner-context.txt"
    excerpt.write_text(ready.section + "\n")
    paths = ["scripts/vidya/loop_beliefs.py", "scripts/vidya/adapters/ch18_merge_trial.py"]
    consumer_dir = Path("scripts/kernel_rnd/autokernel/loop")
    consumers = [consumer_dir / name for name in ("actors.py", "belief_context.py")]
    state = ready.ledger_state
    receipt = {
        "schema": "epyc.vidya.ch18_merge_trial_planning_canary.v1", "status": "passed",
        "as_of": evidence["as_of"], "original_native_record": str(FILING),
        "original_native_record_sha256": sha(ROOT / FILING),
        "commit_pair": {"production_base": BASE, "upstream_tip": UPSTREAM},
        "consumer": config.consumer,
        "entry_point": "AgentPlanner.propose -> belief_context.prepare -> loop_beliefs.py prepare",
        "stop_boundary": "AgentPlanner._proposal_from_agent intercepted before any backend call",
        "ingest": {"rows": 1, "frames": 3, "refused": 0},
        "ledger": {"head_hash": state["head_hash"], "frame_count": state["frame_count"],
                   "intake_index_sha256": state["freshness"]["index_sha256"],
                   "verified_ready": True, "scratch": True},
        "reader_checkout": ready.answer.get("reader_checkout"),
        "root_sources_sha256": {path: sha(ROOT / path) for path in paths},
        "research_sources_sha256": {str(path): sha(research / path) for path in consumers},
        "claim": claim, "protocol_id": support["protocol_id"],
        "actor_receipt_id": actor_receipt["receipt_id"], "reliance_control": refusal,
        "other_consumer_control": {"consumer": "autopilot.planner", "claims": other.evidence["claims"]},
        "rendered_excerpt": excerpt.name, "rendered_excerpt_sha256": sha(excerpt),
        "scope": "Scratch ledger and empty explicit intake index. Diagnostic conflict inventory for "
                 "the original pinned pair. No canonical write, trial rerun, inference or promotion.",
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
