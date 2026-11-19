"""Replay a verified EXP01 filing and read-only campaign history at planner entry."""
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
    parser.add_argument("--filing", type=Path, default=FILING)
    args = parser.parse_args()
    out = args.scratch.resolve()
    if Path("/mnt/raid0/llm/tmp") not in out.parents or out.exists():
        parser.error("--scratch must be a fresh subdirectory of /mnt/raid0/llm/tmp")
    out.mkdir(parents=True)
    filing = args.filing.resolve(strict=True)
    sys.path.insert(0, str(ROOT / "scripts/vidya"))
    from adapters import exp01_proxy_capture
    from claim_tuple import grade

    measurements = [exp01_proxy_capture.project(row)
                    for row in exp01_proxy_capture.native_rows(filing)]
    assert measurements and all(grade(row)[:2] == ("Judged", "Located") for row in measurements)
    modes = {row.extra["mode"] for row in measurements}
    assert len(modes) == 1
    control = modes == {"capture-control"}
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
         "ingest", "exp01-proxy-capture", "--path", str(filing),
         "--as-of", as_of, "--only-new"], cwd=ROOT, check=True, text=True, capture_output=True,
    )
    report = json.loads(result.stdout)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (
        len(measurements), 3 * len(measurements), [])
    config = belief_context.BeliefConfig(
        root=args.reader.resolve(), ledger=ledger, index=index, alarm_config=alarm,
        known_good=out / "known-good.json", alarm_state=out / "alarm-state.json",
    )

    captured = {}

    def before_backend(self, prompt, backend, env, context, *, belief):
        belief_context.require_ready(belief)
        captured.update(prompt=prompt, belief=belief)
        return actors.Abstain(reason="EXP01 offline planner canary"), list(belief.evidence["claim_ids"])

    excerpts, claims, reliance_checks = [], [], []
    models = sorted({row.applicability["model_file"] for row in measurements})
    for model in models:
        expected = {"clm_" + row.measurement_id: row.reps for row in measurements
                    if row.applicability["model_file"] == model}
        context = {"current_regime": {"model": {"path": model}, "backend": "cpu"},
                   "prior_experiments": prior}
        planner = actors.AgentPlanner(workspace=out / "lane", belief=config)
        with patch.object(actors.AgentPlanner, "_proposal_from_agent", before_backend):
            planner.propose(context)
        ready, prompt = captured["belief"], captured["prompt"]
        assert ready.answer["reader_checkout"]["current"] is True
        actual = ready.evidence["claims"]
        assert {claim["claim_id"]: claim["reps"] for claim in actual} == expected
        assert all(claim["grade"] == "Judged/Located" and claim["claim_id"] in prompt
                   for claim in actual)
        assert ready.section in prompt
        receipt_log = out / actors.ACTOR_REPLY_DIR / belief_context.RECEIPT_LOG
        actor_receipt = json.loads(receipt_log.read_text().splitlines()[-1])
        expected_reliance = belief_context.reliance(
            list(ready.evidence["claim_ids"]),
            belief_context.reliable_claim_ids(ready.evidence),
            belief_context.host_claim_ids(ready.evidence))
        assert actor_receipt["reliance"] == expected_reliance
        reliance_checks.append(expected_reliance)
        tried = f"- `{mechanism}` → {prior[0]['status']}"
        assert "## Already tried" in prompt and tried in prompt
        excerpts.append(tried + "\n" + ready.section.rstrip())
        claims.extend(sorted(expected))
    negative_targets = [(name, "gpu") for name in models] + [("unrelated-model.gguf", "cpu")]
    for model_name, backend in negative_targets:
        negative = {"current_regime": {"model": {"path": model_name}, "backend": backend}}
        assert not belief_context.prepare(negative, config).evidence["claims"]
    excerpt = out / "planner-context.txt"
    excerpt.write_text("\n\n".join(excerpts) + "\n")
    receipt = dict(
        schema="epyc.vidya.exp01_planning_canary.v3", status="passed", as_of=as_of,
        entry="AgentPlanner.propose -> belief_context.prepare -> loop_beliefs.py prepare",
        stop="AgentPlanner._proposal_from_agent intercepted before backend execution",
        reader_checkout=ready.answer["reader_checkout"], rows=len(measurements),
        frames=3 * len(measurements), refused=0,
        filing=str(filing), mode=next(iter(modes)),
        original_results_sha256=sha(filing / "results.jsonl"),
        control_only=control, original_official_r3_pre_hook=True, claims=claims,
        proposal_reliance=reliance_checks,
        campaign_store=str(args.campaign_store), history_recalled=len(prior),
        history_rendered=dict(mechanism=mechanism, status=prior[0]["status"], stale=True),
        campaign_history_snapshot_sha256=hashlib.sha256(
            json.dumps(prior, sort_keys=True).encode()).hexdigest(),
        negative_targets=[dict(model=model, backend=backend) for model, backend in negative_targets],
        rendered_excerpt_sha256=sha(excerpt), scratch_ledger=True,
        official_native_acceptance="pending" if control else "verified-original-filing",
    )
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(out)


if __name__ == "__main__":
    main()
