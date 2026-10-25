#!/usr/bin/env python3
"""Canary A: assemble ONE AutoKernel planner context for the live Q38FN campaign, read-only.

NO model call. This re-runs the head of `AgentPlanner.propose` (actors.py:3742-3758):
`belief_context.prepare` (the real consumer half, which runs ROOT loop_beliefs.py prepare as
a child process) -> `render_context(context, belief_section=...)` -> `_HYPOTHESIS_TASK.format`,
and STOPS there (the next line in propose is `_seated`/`_proposal_from_agent`, the backend call).

`build_context` is a closure inside run.py main() that is only reachable after profiling and
anchor builds (inference), so the context dict is assembled here from the same module-level
readers build_context calls (run.prior_experiments' body with a read-only store,
run.accumulator_keeps, resume.pending_hypotheses, archive.SharedHistory.recall,
controller.inbox.read_inbox). Sections that need a live profile/launch (target, cpu_profile,
node_profile, kernel_hotspots, long_context, serving_observations, runtime_*) are omitted and
listed in the summary.

All belief writes go to a scratch COPY of the ledger state (ledger, sync marker, loop-memo,
known-good, read log) and a scratch alarm state/config with delivery disabled.
Usage: canary_a.py <label> <root-or-DEFAULT>
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

BASE = Path("/mnt/raid0/llm/tmp/ws58-canary-20261025")
CAMPAIGN = Path("/mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003")
STORE = CAMPAIGN / "store-b0ba1d427"
MODEL = ("/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/"
         "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf")
SHARED_HISTORY_ROOT = Path("/mnt/raid0/llm/autokernel/loop-memory")
# The 10-22 run's epochs (experiments rows 332-337 / epoch_aliases): champion dd3d9721c unchanged.
EPOCH = "c5d9ecd695a39f8e7526551b6f13f30ea1a04b06986de12640da8aa6606944e1"
MEASUREMENT_EPOCH = "829b98d18946db132b73299b3cd5621f6e9e50383d7d17c5ab878855e4586884"
KNOWN = {
    "akm-cpu-fa-query-major-row-schedule": "row 337 measured_null -1.103% (replicate of it3 +4.73%, DISCARD)",
    "akm-cpu-fa-visible-kv-lookahead": "row 335 keep_candidate +1.33% needs-confirm",
    "akm-cpu-fa-verify-gqa-pair-stream": "rows 332-334 gate_refused/patch_rejected/patch_rounds_exhausted",
}


def git_head(path: Path) -> str:
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    label, root_arg = sys.argv[1], sys.argv[2]
    out_dir = BASE / f"A-{label}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = Path(os.environ["CANARY_STATE"]) if os.environ.get("CANARY_STATE") else BASE / "state" / ("A1-default" if label == "default" else "A2-views")
    ledger = state / "ledger.jsonl"
    ledger_sha_before = sha(ledger)

    from scripts.kernel_rnd.autokernel.loop import actors, belief_context, dispatch_guard, loop
    from scripts.kernel_rnd.autokernel.loop import run as run_mod, archive, resume as resume_mod
    from scripts.kernel_rnd.autokernel.controller import experiments, inbox

    # ROOT: "DEFAULT" = exactly what run.py does with no --belief-root-repo
    # (belief_context.resolve_root_repo(None): env EPYC_ROOT_REPO, else /workspace if it has the
    # reader, else the hub view).
    explicit = None if root_arg == "DEFAULT" else Path(root_arg)
    root = belief_context.resolve_root_repo(explicit)

    # ---- context, from the readers build_context calls (run.py:3864-3887) ----
    with experiments.ExperimentStore(STORE, read_only=True, bounded=False) as store:
        rows = store.recall(epoch=EPOCH, ranking_authorized=True, include_claims=True,
                            measurement_epoch=MEASUREMENT_EPOCH)
    # run.prior_experiments returns the ranked rows as-is when --rank-prior-experiments (default on).
    prior = rows
    # current_regime exactly as run.py:3839-3843 builds it for a CPU serving target:
    # census = workload_contract.verify_workload(args.model) (run.py:3341, GGUF header read only),
    # recipe = build_recipe.NATIVE_CPU_RECIPE (run.py:3346), args.surface = "serving:" + recipe name
    # (run.py:3597; the 10-22 receipts show "serving:q38fn-802bf9ac6-cpu-t48-mtp-d4").
    from scripts.kernel_rnd.autokernel.controller import workload_contract, build_recipe
    try:
        census_quant = workload_contract.verify_workload(Path(MODEL)).dominant_quant
    except Exception as exc:  # noqa: BLE001
        census_quant = f"<census error {type(exc).__name__}: {exc}>"
        census_quant = workload_contract.read_census(Path(MODEL)).dominant_quant
    regime = {"model": {"path": MODEL}, "quant": census_quant, "backend": "cpu",
              "recipe": {"build_recipe": build_recipe.NATIVE_CPU_RECIPE.to_dict()},
              "measurement_surface": "serving:q38fn-802bf9ac6-cpu-t48-mtp-d4"}
    keeps = run_mod.accumulator_keeps(STORE)
    pending = resume_mod.pending_hypotheses(STORE, epoch=EPOCH, anchor_commit=None,
                                            measurement_epoch=MEASUREMENT_EPOCH)
    shared = archive.SharedHistory([SHARED_HISTORY_ROOT], current_store=STORE).recall(scope={
        "model": MODEL, "quant": regime["quant"], "backend": "cpu",
        "measurement_surface": regime["measurement_surface"]})
    inbox_dir = STORE / "inbox"
    inbox_texts = inbox.read_inbox(inbox_dir)
    context = {
        "program": loop.PROGRAM.read_text(encoding="utf-8"),
        "prior_experiments": prior,
        **({"accumulator_keeps": keeps} if keeps else {}),
        **({"pending_accepted_hypotheses": list(pending)} if pending else {}),
        "current_regime": regime,
        "shared_prior_experiments": shared,
        "inbox": inbox_texts,
    }

    # ---- belief: the real consumer half, every write routed to scratch ----
    config = belief_context.BeliefConfig(
        root=root, ledger=ledger, known_good=state / "loop-known-good" / "autokernel.planner.json",
        alarm_state=BASE / "alarm" / f"alarm_state.A-{label}.json",
        alarm_config=BASE / "alarm" / "alarm_config.yaml",
        index=Path(os.environ.get("CANARY_INDEX") or BASE / "index" / "intake_index.origin-main-6f2011142.yaml"),
        source_roots=(STORE,))
    belief_status, refusal, ready = "ready", None, None
    try:
        ready = belief_context.prepare(context, config)
    except belief_context.BeliefContextRefused as exc:
        belief_status, refusal = "refused", {"reason": exc.reason, "detail": exc.detail}
    section = ready.section if ready else ""

    # ---- prompt, exactly as propose() builds it for a codex CPU planner; STOP before backend ----
    context_text = actors.render_context(context, belief_section=section)
    prompt = actors._HYPOTHESIS_TASK.format(
        context=context_text, platform="the CPUs in the selected original serving launch",
        target_path="one source path on the selected CPU serving route",
        profile_rule=("use the original CPU launch/model and inspect its source route; "
                      "if the CPU profile is unavailable, state that limit and do not invent "
                      "timing evidence"))
    if section and section not in prompt:
        prompt += "\n\n" + section
    (out_dir / "prompt.txt").write_text(prompt)
    (out_dir / "belief_section.txt").write_text(section)

    # ---- do-not-repeat formation guard (run.py:6960 -> dispatch_guard.characterised_reason) ----
    guard = {}
    for mech, row in {r.get("mechanism_id"): r for r in prior if r.get("mechanism_id")}.items():
        if mech not in KNOWN:
            continue
        hyp = SimpleNamespace(mechanism_id=mech, target_surface=row.get("target_surface"),
                              target_symbol=row.get("target_symbol"))
        guard[mech] = dispatch_guard.characterised_reason(
            hyp, {**context, "epoch_sha256": EPOCH, "measurement_epoch_sha256": MEASUREMENT_EPOCH})
    # Also the same mechanism under a fresh id (what a planner re-proposal looks like).
    hyp = SimpleNamespace(mechanism_id="akm-cpu-fa-gqa-query-major-rows",
                          target_surface="ggml/src/ggml-cpu/ops.cpp",
                          target_symbol="ggml_compute_forward_flash_attn_ext_f16_one_chunk")
    guard["<renamed query-major>"] = dispatch_guard.characterised_reason(
        hyp, {**context, "epoch_sha256": EPOCH, "measurement_epoch_sha256": MEASUREMENT_EPOCH})
    # Control: the same guard with current_regime = row 337's recorded research_scope, to separate
    # "regime never matches" from "fewer than 3 comparable answers".
    rs337 = next((r.get("research_scope") for r in prior
                  if r.get("mechanism_id") == "akm-cpu-fa-query-major-row-schedule"
                  and isinstance(r.get("research_scope"), dict)), None)
    guard_control = {}
    if rs337:
        for mech in KNOWN:
            row = next((r for r in prior if r.get("mechanism_id") == mech), None)
            if row is None:
                continue
            hyp = SimpleNamespace(mechanism_id=mech, target_surface=row.get("target_surface"),
                                  target_symbol=row.get("target_symbol"))
            guard_control[mech] = dispatch_guard.characterised_reason(
                hyp, {**context, "current_regime": rs337, "epoch_sha256": EPOCH,
                      "measurement_epoch_sha256": MEASUREMENT_EPOCH})
    project = {"regime_quant": regime["quant"],
               "row337_scope_present": bool(rs337),
               "row337_quant": (rs337 or {}).get("quant"),
               "row337_surface": (rs337 or {}).get("measurement_surface")}
    answers_by_mech = {}
    for r in prior:
        if r.get("status") in dispatch_guard.ANSWER_STATUSES and r.get("mechanism_id"):
            answers_by_mech.setdefault(r["mechanism_id"], []).append(r.get("status"))

    ev = ready.evidence if ready else {}
    claims = ev.get("claims") or []
    tiers = ev.get("tiers") or ev.get("tier_counts")
    known_hits = {}
    for mech, why in KNOWN.items():
        known_hits[mech] = {
            "expected": why,
            "in_prompt": mech in prompt,
            "in_belief_section": mech in section,
            "in_already_tried_window": mech in context_text.split("## Already tried", 1)[-1][:20000]
            if "## Already tried" in context_text else False,
            "prior_rows": [(r.get("status"), r.get("effect_fraction"), r.get("same_epoch"))
                           for r in prior if r.get("mechanism_id") == mech],
        }
    summary = {
        "label": label, "root_arg": root_arg, "root_used": str(root),
        "root_head": git_head(root), "EPYC_ROOT_REPO": os.environ.get("EPYC_ROOT_REPO"),
        "reader": str(config.reader()), "reader_sha256": sha(config.reader()),
        "belief_status": belief_status, "refusal": refusal,
        "ledger_state": ready.ledger_state if ready else None,
        "ledger_copy_sha_before": ledger_sha_before, "ledger_copy_sha_after": sha(ledger),
        "evidence_keys": sorted(ev),
        "tiers": tiers, "tiers_shown": ev.get("tiers_shown"),
        "claim_ids_presented": ev.get("claim_ids"),
        "usable_claim_ids": belief_context.reliable_claim_ids(ev) if ev else [],
        "host_claim_ids": belief_context.host_claim_ids(ev) if ev else [],
        "claims_tier_counts": {t: sum(1 for c in claims if c.get("tier") == t)
                               for t in {c.get("tier") for c in claims}},
        "tried_index_count": len(ev.get("tried_index") or []) if isinstance(ev.get("tried_index"), list)
        else ev.get("tried_index_count"),
        "section_bytes": len(section.encode()),
        "prior_rows": len(prior),
        "prior_same_epoch": sum(1 for r in prior if r.get("same_epoch")),
        "prior_status_counts": {s: sum(1 for r in prior if r.get("status") == s)
                                for s in sorted({str(r.get("status")) for r in prior})},
        "accumulator_keeps": keeps, "pending_accepted": len(pending),
        "shared_history": {"rows": len(shared.get("rows") or []), "errors": shared.get("errors"),
                           "queried_roots": shared.get("queried_roots")},
        "inbox_dir": str(inbox_dir), "inbox_count": len(inbox_texts),
        "inbox_names": sorted(p.name for p in inbox_dir.glob("*.md")),
        "regime": {k: (v if k != "recipe" else bool(v.get("build_recipe"))) for k, v in regime.items()},
        "known_hits": known_hits, "formation_guard": guard, "formation_guard_control_row337_scope": guard_control, "regime_projection": project,
        "comparable_answers_by_mechanism": {m: answers_by_mech.get(m) for m in KNOWN},
        "prompt_chars": len(prompt),
        "omitted_sections": ["target", "kernel_hotspots", "cpu_profile", "node_profile",
                             "long_context", "serving_observations", "runtime_*",
                             "operator_unblock_artifacts (none in ak_run.sh)",
                             "CPU program prefix (static text)"],
        "receipt_written": False,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True, default=str))
    print(json.dumps({k: summary[k] for k in (
        "root_used", "root_head", "belief_status", "refusal", "tiers", "tiers_shown",
        "usable_claim_ids", "section_bytes", "prior_rows", "prior_same_epoch", "inbox_count",
        "formation_guard", "formation_guard_control_row337_scope", "regime_projection", "comparable_answers_by_mechanism", "ledger_copy_sha_before",
        "ledger_copy_sha_after")}, indent=1, default=str))
    for m, h in known_hits.items():
        print(m, {k: v for k, v in h.items() if k != "expected"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
