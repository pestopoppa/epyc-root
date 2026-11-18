"""Replay the filed EXP01 control and read-only campaign history at planner entry."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
FILING = ROOT / "data/vidya/run-filings/2026-11-04/vidya-exp01-proxy-wire-20261104"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reader", "research", "campaign-store", "scratch"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    out = args.scratch.resolve()
    if Path("/mnt/raid0/llm/tmp") not in out.parents or out.exists():
        parser.error("--scratch must be a fresh subdirectory of /mnt/raid0/llm/tmp")
    out.mkdir(parents=True)
    sys.path[:0] = [str(args.research), str(args.research / "scripts/kernel_rnd")]
    from scripts.kernel_rnd.autokernel.controller.experiments import ExperimentStore
    from scripts.kernel_rnd.autokernel.loop import actors, belief_context

    with ExperimentStore(args.campaign_store, read_only=True) as store:
        prior = store.recall(epoch="", limit=12)
    assert prior and all(row["stale_epoch"] for row in prior)
    mechanism = prior[0]["mechanism_id"]
    assert mechanism
    index, alarm, ledger = (out / name for name in ("index.yaml", "alarm.yaml", "ledger.jsonl"))
    index.write_text("[]\n")
    alarm.write_text("schema_version: alarm_channel.config.v1\nenabled: false\n")
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/vidya/cli.py"), "--ledger", str(ledger), "--json",
         "ingest", "exp01-proxy-capture", "--path", str(FILING.relative_to(ROOT)),
         "--as-of", as_of, "--only-new"], cwd=ROOT, check=True, text=True, capture_output=True,
    )
    report = json.loads(result.stdout)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (4, 12, [])
    config = belief_context.BeliefConfig(
        root=args.reader.resolve(), ledger=ledger, index=index, alarm_config=alarm,
        known_good=out / "known-good.json", alarm_state=out / "alarm-state.json",
    )

    captured = {}

    def before_backend(self, prompt, backend, env, context, *, belief):
        belief_context.require_ready(belief)
        captured.update(prompt=prompt, belief=belief)
        return actors.Abstain(reason="EXP01 offline planner canary"), []

    packet = json.loads((FILING / "NATIVE.json").read_bytes())
    excerpts, claims = [], []
    for measurement in packet["belief_measurements"]:
        model = measurement["applicability"]["model_file"]
        context = {"current_regime": {"model": {"path": model}, "backend": "cpu"},
                   "prior_experiments": prior}
        planner = actors.AgentPlanner(workspace=out / "lane", belief=config)
        with patch.object(actors.AgentPlanner, "_proposal_from_agent", before_backend):
            planner.propose(context)
        ready, prompt = captured["belief"], captured["prompt"]
        assert ready.answer["reader_checkout"]["current"] is True
        (claim,) = ready.evidence["claims"]
        assert (claim["claim_id"], claim["grade"], claim["reps"]) == (
            "clm_" + measurement["measurement_id"], "Judged/Located", 1)
        assert claim["claim_id"] in prompt and ready.section in prompt
        tried = f"- `{mechanism}` → {prior[0]['status']}"
        assert "## Already tried" in prompt and tried in prompt
        excerpts.append(tried + "\n" + ready.section.rstrip())
        claims.append(claim["claim_id"])
    for model_name, backend in ((model, "gpu"), ("unrelated-model.gguf", "cpu")):
        negative = {"current_regime": {"model": {"path": model_name}, "backend": backend}}
        assert not belief_context.prepare(negative, config).evidence["claims"]
    excerpt = out / "planner-context.txt"
    excerpt.write_text("\n\n".join(excerpts) + "\n")
    receipt = dict(
        schema="epyc.vidya.exp01_control_planning_canary.v2", status="passed", as_of=as_of,
        entry="AgentPlanner.propose -> belief_context.prepare -> loop_beliefs.py prepare",
        stop="AgentPlanner._proposal_from_agent intercepted before backend execution",
        reader_checkout=ready.answer["reader_checkout"], rows=4, frames=12, refused=0,
        control_native_archive_sha256=sha(FILING / "native-control.tar.gz"),
        control_only=True, original_official_r3_pre_hook=True, claims=claims,
        campaign_store=str(args.campaign_store), history_recalled=len(prior),
        history_rendered=dict(mechanism=mechanism, status=prior[0]["status"], stale=True),
        campaign_history_snapshot_sha256=hashlib.sha256(
            json.dumps(prior, sort_keys=True).encode()).hexdigest(),
        negative_targets=["GPU same model", "CPU unrelated model"],
        rendered_excerpt_sha256=sha(excerpt), scratch_ledger=True,
        official_native_acceptance="pending",
    )
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(out)


if __name__ == "__main__":
    main()
