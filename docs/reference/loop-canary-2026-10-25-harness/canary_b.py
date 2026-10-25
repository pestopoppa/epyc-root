#!/usr/bin/env python3
"""Canary B: assemble ONE AutoPilot planner turn's context in-process, read-only, no model call.

Mirrors scripts/autopilot/autopilot.py _run_loop_inner startup (~8624-8811) and the planner-turn
assembly (~9138-9591) at orchestrator HEAD 84f6f6f1, stopping BEFORE phase "planner_invoke"
(no plan_with_providers / provider.invoke). Side effects are fenced by canary_guard (audit hook).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
BASE = Path("/mnt/raid0/llm/tmp/ws58-canary-20261025")
COPIES = BASE / "B-copies"
COPIES.mkdir(parents=True, exist_ok=True)
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
CANON_LEDGER = Path("/mnt/raid0/llm/state/vidya/ledger.jsonl")
SCR_STATE = BASE / "state" / "B-autopilot"
TELEMETRY = Path("/mnt/raid0/llm/tmp/seeding_batch_telemetry.jsonl")


def sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


def tree_snapshot(root: Path) -> dict[str, list]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            st = p.stat()
            out[str(p.relative_to(root))] = [st.st_size, st.st_mtime_ns]
    return out


# ---------------------------------------------------------------- pre-run fingerprints + copies
summary: dict = {"schema": "ws58.canary_b.v1", "started": time.time(), "notes": [],
                 "not_run": [], "sections": {}}
summary["pre"] = {
    "canonical_ledger_sha256": sha(CANON_LEDGER),
    "scratch_ledger_sha256": sha(SCR_STATE / "ledger.jsonl"),
    "scratch_state_tree": tree_snapshot(SCR_STATE),
    "telemetry_sha256": sha(TELEMETRY),
    "canonical_known_good": sorted(os.listdir("/mnt/raid0/llm/state/vidya/loop-known-good")),
}
# StrategyStore copy (sqlite + FAISS mirror) -- StrategyStore.__init__ opens rw + CREATE TABLE.
src_ss = ORCH / "orchestration" / "repl_memory" / "strategies"
dst_ss = COPIES / "strategies"
if dst_ss.exists():
    shutil.rmtree(dst_ss)
shutil.copytree(src_ss, dst_ss)
summary["pre"]["strategy_db_src_sha256"] = sha(src_ss / "strategies.db")
for name in ("autopilot_short_term_memory.md", "autopilot_state.json"):
    shutil.copy2(ORCH / "orchestration" / name, COPIES / name)
(COPIES / "blocked_events.jsonl").write_text("")
for stale in ("alarm_state.B.json",):
    pass

# ---------------------------------------------------------------- guard + launcher env
sys.path.insert(0, str(HARNESS))
import canary_guard  # noqa: E402

canary_guard.install()
os.chdir(COPIES)

AUTHORITY_ENV = {  # scripts/autopilot/start_authority_daemon.py:40-57 (verbatim values)
    "AUTOPILOT_SEQ_VERDICT": "0", "AUTOPILOT_SEQ_P0_2_BRIDGE": "1",
    "AUTOPILOT_W6_AUDIT_BLOCK": "1", "AUTOPILOT_W6_AUDIT_N": "10",
    "AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS": "1", "AUTOPILOT_W6_AUDIT_SHADOW_ONLY": "1",
    "AUTOPILOT_PLANNER_TIMEOUT": "600", "AUTOPILOT_PLANNER_SPEND_BREAKER": "0",
    "AUTOPILOT_PLANNER_HINTS": "1", "AUTOPILOT_TOOL_SENTINELS": "1",
    "AUTOPILOT_STEPPING_STONES": "1", "AUTOPILOT_PLANNER_ROSTER_POLICY_ACTIVE": "1",
    "AUTOPILOT_MULTITIER_PROMOTION": "1", "AUTOPILOT_AP55_PROMOTION_GATE": "shadow",
    "AUTOPILOT_AP55_SEED_RERUN": "0", "AUTOPILOT_AP3_ROLE_RESTART_ENABLE": "scoped",
}
os.environ.update(AUTHORITY_ENV)
summary["env"] = {"EPYC_ROOT_REPO": os.environ.get("EPYC_ROOT_REPO"), **AUTHORITY_ENV}

sys.path.insert(0, str(ORCH / "scripts" / "autopilot"))
sys.path.insert(0, str(ORCH))
t0 = time.time()
import autopilot as ap  # noqa: E402
import loop_beliefs_bridge as lb  # noqa: E402
summary["import_s"] = round(time.time() - t0, 2)
summary["blocked_after_import"] = list(canary_guard.BLOCKED)

# state from a COPY; save_state neutralised (the daemon would persist startup migrations)
ap.STATE_PATH = COPIES / "autopilot_state.json"
_saves = []
ap.save_state = lambda state, *a, **k: _saves.append(time.time())


def guarded(name, fn, default=None):
    before = len(canary_guard.BLOCKED)
    try:
        val = fn()
        err = None
    except Exception as exc:  # noqa: BLE001
        val, err = default, f"{type(exc).__name__}: {exc}"
        summary.setdefault("errors", {})[name] = err + " | " + traceback.format_exc()[-800:]
    new = canary_guard.BLOCKED[before:]
    if new:
        summary.setdefault("blocked_by_section", {})[name] = new
    return val


# ---------------------------------------------------------------- startup objects (8624-8811)
state = ap.load_state()
summary["state"] = {"paused": state.get("paused"), "trial_counter": state.get("trial_counter"),
                    "in_flight_trial": state.get("in_flight_trial"),
                    "session_id": state.get("session_id")}
guarded("migrate_eval_quality_era", lambda: ap._migrate_eval_quality_era(state))
eval_quality_era, quality_exclude_before_ts = ap._quality_epoch_params_from_state(state)
journal = guarded("journal", lambda: ap.ExperimentJournal())
ap._sync_segment_snapshot_scope(journal, state)
_deinfl_ts, _deinfl_factor, _exclude_ts = ap._archive_epoch_params_from_state(state)
archive_payload = guarded("archive_payload", lambda: ap._journal_archive_payload_for_authority(
    journal, deinflate_before_ts=_deinfl_ts, deinflate_factor=_deinfl_factor,
    exclude_before_ts=_exclude_ts, objective_policy=ap._live_objective_policy_from_state(state)))
archive, rebase_completed = ap._startup_archive_from_current_era_payload(state, archive_payload)
guarded("promotion_guard_scope", lambda: ap._install_promotion_guard_scope(journal, state))
summary["not_run"].append("EvalLeakageMonitor.install()/preflight (autopilot.py:8673) -- may "
                          "append journal events; not a prompt input")
gate = guarded("safety_gate", lambda: ap.SafetyGate(
    consecutive_failures=state.get("consecutive_failures", 0),
    quality_history=state.get("quality_history", []),
    quality_history_by_tier=state.get("quality_history_by_tier", {}),
    quality_history_provenance_by_tier=state.get("quality_history_provenance_by_tier"),
    baseline_state=ap._baseline_state_for_startup_gate(state, journal),
    eval_quality_era=eval_quality_era,
    autopilot_speed_era=ap._numeric_swarm_epoch_label_from_state(state),
    quality_exclude_before_ts=quality_exclude_before_ts))
meta = ap.MetaOptimizer()
seeder = ap.Seeder(url=ap.ORCHESTRATOR_URL, dry_run=False)
lab = ap.StructuralLab(orchestrator_url=ap.ORCHESTRATOR_URL)
memory = ap.ShortTermMemory(path=COPIES / "autopilot_short_term_memory.md")
guarded("stm_startup_refresh", lambda: memory.refresh_from_journal(journal))
last_criticism_text = "(first trial — no prior criticism)"

from orchestration.repl_memory import strategy_store as _ss_mod  # noqa: E402
from orchestration.repl_memory.embedder import hash_fallback_embedding  # noqa: E402


class HashOnlyEmbedder:
    """NO inference: the TaskEmbedder's own hash fallback (what the daemon degrades to when the
    BGE embedding server :8090-8095 and llama-embedding are unavailable). Semantically void."""

    def __init__(self, dim):
        self.dim = dim

    def embed_text(self, text, side=None):
        return hash_fallback_embedding(str(text), embedding_dim=self.dim)

    def close(self):
        pass


strategy_store = guarded("strategy_store", lambda: ap.StrategyStore(
    path=dst_ss, embedder=HashOnlyEmbedder(_ss_mod.LEGACY_EMBEDDING_DIM)))
summary["notes"].append(
    "StrategyStore opened on a COPY (B-copies/strategies) with a hash-fallback embedder; the daemon "
    "would embed the 4 _PLANNER_STRATEGY_HINT_QUERIES via BGE (llama-server :8090 or "
    "llama-embedding) = inference, forbidden here, so semantic retrieval ranks are NOT reproduced.")
guarded("install_convention_bindings",
        lambda: ap._install_planner_convention_bindings(strategy_store, journal))
blacklist = ap.load_blacklist()
if "species_budget" in state:
    meta.budget = ap.SpeciesBudget(**state["species_budget"])
seeder.restore_state(state.get("seeder_state") or {"td_errors": state.get("td_errors", [])})
trial_counter = state.get("trial_counter", 0)
plot_paths: list[str] = []
summary["not_run"].append(
    "_reject_in_flight_manifest_drift/_recover_from_in_flight_trial/"
    "_sync_startup_archive_from_journal_authority (autopilot.py:8797-8806) -- startup recovery "
    "may WRITE the journal/state (state.in_flight_trial is None here, so recovery would be a no-op); skipped")
memory_count = guarded("memory_count", lambda: seeder.get_memory_count(), 0)
converged = seeder.is_converged
summary["not_run"].append(
    "pre-planner forced-action gates (_maybe_force_multitier_due_action / _maybe_force_seq_due_action"
    " / _maybe_force_frontier_rerun_action, autopilot.py:9083-9136) -- assumed to return None so "
    "the controller path is reached")

# ---------------------------------------------------------------- 2a. belief context (9138-9195)
root_repo = lb.resolve_root_repo()  # daemon: launcher passes no --belief-root-repo
summary["belief"] = {"resolved_root_repo": str(root_repo)}
belief_settings = lb.BeliefSettings(
    root_repo=root_repo,
    ledger=SCR_STATE / "ledger.jsonl",
    known_good=SCR_STATE / "loop-known-good" / "autopilot.planner.json",
    alarm_state=BASE / "alarm" / "alarm_state.B.json",
    alarm_config=BASE / "alarm" / "alarm_config.yaml",
    index=BASE / "index" / "intake_index.origin-main-6f2011142.yaml",
    degraded_log=COPIES / "loop_beliefs_degraded.jsonl",
    review_flags=COPIES / "loop_beliefs_review_flags.jsonl",
)
summary["belief"]["settings"] = belief_settings.describe()
targets = guarded("derive_targets", lambda: lb.derive_targets(
    hypotheses_loader=ap._load_operator_hypotheses,
    stack_regime_loader=lambda: (ap._infra_fingerprint_for_trial() or {}).get("digest")), [])
summary["belief"]["targets"] = targets
_bt = time.time()
outcome = guarded("belief_prepare", lambda: lb.prepare(belief_settings, targets=targets))
summary["belief"]["prepare_s"] = round(time.time() - _bt, 2)
belief_ready = None
if outcome is not None:
    summary["belief"]["status"] = outcome.status
    summary["belief"]["reason"] = outcome.reason
    summary["belief"]["detail"] = outcome.detail[:600]
    ans = outcome.answer or {}
    summary["belief"]["answer_head"] = {k: ans.get(k) for k in (
        "status", "reason", "ledger_path", "known_good_path", "ledger_state", "ledger_state_digest",
        "flag_counts", "known_good_error", "alarm", "banner", "targets")}
    ev = ans.get("evidence") or {}
    summary["belief"]["evidence_keys"] = sorted(ev.keys())
    summary["belief"]["evidence"] = {k: ev.get(k) for k in (
        "tiers", "tiers_shown", "nonempty_target", "claim_ids", "host_claim_ids",
        "not_evidence_claim_ids", "refuted_claim_ids", "contested_claim_ids",
        "withdrawn_claim_ids", "reasons", "per_target", "target_errors", "section_bytes",
        "omitted_count", "tried_index_count")}
    summary["belief"]["claims"] = [
        {k: r.get(k) for k in ("claim_id", "tier", "target", "target_label", "label",
                               "knob_family", "knob_families", "grade", "verdict")}
        for r in (ev.get("claims") or []) if isinstance(r, dict)]
    (COPIES / "belief_answer.json").write_text(json.dumps(ans, indent=1, default=str))
    belief_ready = outcome.ready
summary["not_run"].append("lb.recovery_recheck (autopilot.py:9152) -- review bookkeeping, "
                          "not a prompt input")
if belief_ready is None:
    summary["notes"].append("BELIEF REFUSED: the daemon would enter degraded mode and NOT build a "
                            "planner prompt this turn; the prompt below is assembled anyway with "
                            "an explicit refusal marker for the belief block")

# ---------------------------------------------------------------- prompt build (9196-9591)
sec: dict[str, str] = {}
sec["constitution"] = ap._read_guidance_file(ap.CONSTITUTION_PATH, "constitution.md")
sec["system_card"] = guarded("system_card", lambda: ap._render_system_card(state), "(blocked)")
sec["blacklist_text"] = ap._format_blacklist_for_prompt(blacklist)
sec["slot_memory"] = ("  (CANARY: _query_slot_memory() NOT called -- it queries live model-server "
                      "slot ports over HTTP, forbidden in this canary)")
summary["not_run"].append("_query_slot_memory() (autopilot.py:9217 -> :8229) -- HTTP to model "
                          "server slot ports")
model_sigs = guarded("model_signatures", lambda: ap.load_model_signatures(), None)
sec["model_signatures"] = (ap.format_model_signatures(model_sigs) if model_sigs is not None
                           else "(model signatures unavailable)")

# Adaptive-batch telemetry (9246-9289) -- seeding_telemetry reads TELEMETRY
_tel = {}
try:
    sys.path.insert(0, str(ap._REPO_ROOT / "scripts/benchmark"))
    import seeding_telemetry as _st
    _bs = _st.batch_summary()
    _tel = {"path": str(_st._batch_history_path()), "n_recent": _bs["n_recent"],
            "median_s_per_q": _bs["median_s_per_q"], "recent": _bs["recent"],
            "rows_loaded": len(_st._recent_batches)}
    _rate = _bs.get("median_s_per_q")
    if _rate is None:
        sec["batch_telemetry"] = ("(no batch history yet — first seed_batch will use the requested"
                                  " n; subsequent batches will auto-adapt)")
    else:
        _budget_s = float(os.environ.get("SEEDING_BATCH_BUDGET_S", "900"))
        _max_n_now, _max_reason = _st.adaptive_batch_size(100)
        sec["batch_telemetry"] = (
            f"recent median: {_rate:.0f}s/question over {_bs['n_recent']} batches\n"
            f"current budget: {_budget_s:.0f}s (SEEDING_BATCH_BUDGET_S)\n"
            f"realistic max n_questions right now: ~{_max_n_now} (scaler reason: {_max_reason})\n"
            "recent batches: " + json.dumps(_bs.get("recent", []), separators=(",", ":")) + "\n"
            "IMPORTANT: request seed_batch sizes that fit the budget. Asking for 10 questions when "
            "the realistic max is 3 just gets silently scaled down — better to ask for 3 directly "
            "so you keep clean attribution.")
except Exception as _exc:  # noqa: BLE001
    sec["batch_telemetry"] = f"(telemetry unavailable: {_exc})"
summary["telemetry"] = _tel

# trustworthiness (9299-9385)
def _trust():
    trust = journal.trustworthiness_score()
    lines = [f"total trials: {trust['total']}", f"trustworthy:  {trust['trustworthy']}",
             f"corrupted:    {trust['corrupted']}", f"ratio:        {trust['ratio']:.1%}"]
    if trust["corrupted_by"]:
        lines.append("corrupted-by breakdown: " + ", ".join(
            f"{s}:{n}" for s, n in trust["corrupted_by"].items()))
    if trust["low_signal"]:
        lines.append("WARNING: trustworthy < 5 — hypothesis-chain reasoning has low signal. ...")
    try:
        _repro = sum(1 for e in journal.recent(10)
                     if getattr(e, "deficiency_category", "") == "reproduction_confirmed")
    except Exception:
        _repro = 0
    if _repro:
        lines.append(f"reproduction_confirmed (convergence, last 10): {_repro} — ...")
    lines.append("ATTRIBUTION GUARD: corrupted-by tags are classifications (...)")
    try:
        from host_health import HostHealthState
        _hh = HostHealthState.snapshot()
        _throttled, _trig = _hh.is_throttled()
        _mw = _hh.memory_residency_warnings()
        lines.append("host-health: " + ("THROTTLED — " + "; ".join(_trig) if _throttled else
                     "nominal (no CPU-throttle / page-cache / load signal → a host-noise "
                     "narrative is UNSUPPORTED)"))
        if _mw:
            lines.append("memory-residency: ADVISORY — " + "; ".join(_mw))
    except Exception as e:  # noqa: BLE001
        lines.append(f"host-health: not collected this turn ({type(e).__name__})")
    return "\n".join(lines)


sec["journal_trustworthiness"] = guarded("trust", _trust, "(trustworthiness unavailable)")


def _hyps():
    hyps = journal.recent_hypotheses(n=3, exclude_bug_corrupted=True)
    if not hyps:
        return "(no recent trustworthy hypotheses)"
    out = []
    for e in hyps:
        outcome_s = f"q={e.quality:.3f} sp={e.speed:.1f} → {e.pareto_status}"
        out.append(f"#{e.trial_id} ({e.species}/{e.action_type}):\n"
                   f"  Hypothesis: {(e.hypothesis or '(none)')[:240]}\n  Outcome:    {outcome_s}"
                   + (f"\n  Self-criticism: {ap.scrub_legacy_scale_text(e.self_criticism)[:200]}"
                      if e.self_criticism else ""))
    return "\n\n".join(out)


sec["hypotheses_under_test"] = guarded("hypotheses", _hyps, "(hypothesis chain unavailable)")
sec["insights_structured"] = guarded("insights", lambda: journal.insights_structured_text(
    n=ap.PLANNER_STRUCTURED_INSIGHTS_LIMIT, exclude_bug_corrupted=True), "(unavailable)")
pg = guarded("geometry", lambda: archive.geometry_text(tier=ap.DEFAULT_FRONTIER_TIER),
             "(geometry unavailable)")
st_txt = guarded("stepping", lambda: archive.stepping_stones_text(
    tier=ap.DEFAULT_FRONTIER_TIER, limit=8), "")
if st_txt:
    pg = f"{pg}\n\n{st_txt}"
pu_txt = guarded("parent_util", lambda: archive.parent_utility_text(
    tier=ap.DEFAULT_FRONTIER_TIER, limit=8), "")
if pu_txt:
    pg = f"{pg}\n\n{pu_txt}"
sec["pareto_geometry"] = pg
sec["planner_evidence"] = guarded("planner_evidence", lambda: ap.format_planner_evidence_section(
    (asdict(e) for e in journal.entries_with_supersessions()),
    exclude_before_ts=quality_exclude_before_ts), "(planner evidence unavailable)")
w8 = ap._w8_replay_pressure_active(sec["planner_evidence"])
guarded("refresh_convention_bindings", lambda: ap._refresh_planner_convention_bindings(
    strategy_store, journal, reason=f"planner_turn:{trial_counter}"))
_known = ["seed_batch", "numeric_trial", "prompt_mutation", "gepa_optimize", "code_mutation",
          "structural_experiment", "consult_gate_probe", "structural_prune", "slot_compact",
          "train_routing_models", "distill_skillbank", "reset_memories", "deep_eval", "rollback",
          "distill_knowledge"]
try:
    aa_text, viable_tail, selectable = ap._build_action_availability(
        journal=journal, known_actions=_known, memory_count=memory_count, converged=converged,
        slot_memory_text=sec["slot_memory"], blacklist=blacklist,
        suppressed_numeric_surfaces=ap._PLANNER_SUPPRESSED_NUMERIC_SURFACES,
        w8_replay_pressure_text=sec["planner_evidence"])
    expl_block, stag = ap._build_exploration_block(journal=journal, archive=archive,
                                                   known_actions=viable_tail)
except Exception as _exc:  # noqa: BLE001
    summary.setdefault("errors", {})["action_availability"] = repr(_exc)
    aa_text, selectable, stag = "(action availability unavailable)", _known, "unknown"
    expl_block = f"(exploration-block assembly failed: {_exc})"
sec["action_availability"] = aa_text
sec["exploration_block"] = expl_block
sec["stagnation_signal"] = stag
sec["planner_strategy_hints"] = guarded("strategy_hints", lambda: ap._build_planner_strategy_hints(
    strategy_store, journal), "(blocked)")
sec["higher_tier_pressure"] = guarded("higher_tier", lambda: ap._build_higher_tier_planner_pressure(
    archive, gate, w8_candidate_generation_active=w8), "")
sec["eval_coverage_pressure"] = guarded("eval_cov", lambda: ap._build_eval_coverage_pressure(
    journal, w8_candidate_generation_active=w8), "")
sec["outcome_progress_pressure"] = guarded("outcome_progress",
                                           lambda: ap._build_outcome_progress_pressure(), "")
kvq = guarded("vidya_kvq", lambda: ap._build_vidya_kvq_context(), {"text": "(blocked)"})
sec["vidya_kvq_evidence_block"] = kvq["text"]
sec["pareto_summary"] = archive.summary_text(tier=ap.DEFAULT_FRONTIER_TIER)
sec["journal_summary"] = journal.summary_text(ap.PLANNER_JOURNAL_SUMMARY_LIMIT)
sec["seeder_status"] = json.dumps(seeder.convergence_status(), indent=2)
sec["species_effectiveness"] = json.dumps(journal.species_effectiveness(), indent=2)
sec["available_action_schemas"] = ap._format_available_action_schemas(selectable)
sec["model_gate_advisory"] = guarded("model_gate", lambda: ap._build_model_gate_advisory(), "")
sec["repo_readiness_advisory"] = guarded("repo_ready", lambda: ap._build_repo_readiness_advisory(), "")
sec["budget"] = json.dumps(meta.budget.as_dict(), indent=2)
sec["suite_quality_trends"] = ap._format_suite_trends(journal.suite_quality_trend(10))
sec["short_term_memory"] = guarded("stm", lambda: memory.refresh_from_journal(journal), "")
sec["prior_planner_decisions"] = guarded("prior_decisions",
                                         lambda: ap._build_prior_planner_decision_digest(), "")
sec["operator_outbox_feedback"] = guarded("outbox", lambda: ap._build_operator_outbox_feedback(), "")
sec["operator_hypotheses_block"] = guarded("op_hyps",
                                           lambda: ap._build_operator_hypotheses_block(blacklist), "")
sec["vidya_settled_ground_block"] = guarded("settled",
                                            lambda: ap._build_vidya_settled_ground_block(), "")
sec["vidya_loop_beliefs_block"] = (
    lb.render_prompt_block(belief_ready) if belief_ready is not None else
    f"  (CANARY: belief context REFUSED: {getattr(outcome, 'reason', '?')} -- the daemon would not "
    "build this prompt)")
sec["feature_flags_block"] = guarded("feature_flags", lambda: ap._build_feature_flags_block(
    lab, denylisted_flags=ap._PLANNER_DENYLISTED_FEATURE_FLAGS), "")
sec["last_invalid_feedback"] = (ap._build_last_invalid_feedback(state)
                                + ap._build_rejected_config_feedback(journal))
prompt = ap.CONTROLLER_PROMPT_TEMPLATE.format(
    constitution=sec["constitution"], system_card=sec["system_card"],
    pareto_summary=sec["pareto_summary"], pareto_geometry=sec["pareto_geometry"],
    planner_evidence=sec["planner_evidence"],
    journal_trustworthiness=sec["journal_trustworthiness"],
    hypotheses_under_test=sec["hypotheses_under_test"], journal_summary=sec["journal_summary"],
    seeder_status=sec["seeder_status"], batch_telemetry=sec["batch_telemetry"],
    species_effectiveness=sec["species_effectiveness"], health_status="OK",
    memory_count=memory_count, converged=converged, slot_memory=sec["slot_memory"],
    action_availability=sec["action_availability"],
    available_action_schemas=sec["available_action_schemas"],
    model_gate_advisory=sec["model_gate_advisory"],
    higher_tier_pressure=sec["higher_tier_pressure"],
    eval_coverage_pressure=sec["eval_coverage_pressure"],
    outcome_progress_pressure=sec["outcome_progress_pressure"],
    planner_strategy_hints=sec["planner_strategy_hints"],
    repo_readiness_advisory=sec["repo_readiness_advisory"], budget=sec["budget"],
    suite_quality_trends=sec["suite_quality_trends"],
    insights_structured=sec["insights_structured"], stagnation_signal=sec["stagnation_signal"],
    exploration_block=sec["exploration_block"], short_term_memory=sec["short_term_memory"],
    prior_planner_decisions=sec["prior_planner_decisions"], last_criticism=last_criticism_text,
    model_signatures=sec["model_signatures"], blacklist_text=sec["blacklist_text"],
    operator_outbox_feedback=sec["operator_outbox_feedback"],
    operator_hypotheses_block=sec["operator_hypotheses_block"],
    vidya_settled_ground_block=sec["vidya_settled_ground_block"],
    vidya_kvq_evidence_block=sec["vidya_kvq_evidence_block"],
    vidya_loop_beliefs_block=sec["vidya_loop_beliefs_block"],
    feature_flags_block=sec["feature_flags_block"],
    last_invalid_feedback=sec["last_invalid_feedback"],
    plot_paths="\n".join(f"  - {p}" for p in plot_paths) or "  (none yet)",
) + ap.peaf.peaf_prompt_addendum()
(BASE / "B-context.txt").write_text(prompt)
summary["prompt_chars"] = len(prompt)
summary["sections"] = {k: {"chars": len(v), "head": v[:300]} for k, v in sec.items()}
(COPIES / "sections.json").write_text(json.dumps(sec, indent=1, default=str))

# ---------------------------------------------------------------- inventory for the report
from journal_shards import journal_shards  # noqa: E402

entries = journal.all_entries()
shards = [str(p) for p in journal_shards(journal.journal_dir)]
per_shard = {}
for p in shards:
    with open(p, "rb") as fh:
        per_shard[p] = sum(1 for line in fh if line.strip())
summary["journal"] = {
    "dir": str(journal.journal_dir), "shards": shards, "shard_line_counts": per_shard,
    "entries_loaded": len(entries),
    "newest_timestamp": max((e.timestamp for e in entries), default=None),
    "newest_trial_id": max((e.trial_id for e in entries), default=None),
    "oldest_timestamp": min((e.timestamp for e in entries), default=None),
    "torn_lines_skipped": journal.torn_lines_skipped,
    "ledger_events": sum(len(v) for v in getattr(journal, "_ledger_events_by_batch", {}).values()),
}
try:
    summary["pareto"] = {
        "source": ("verified journal segment snapshot" if archive_payload and
                   archive_payload.get("snapshot") else "journal reconstruction"),
        "payload_keys": sorted((archive_payload or {}).keys())[:30],
        "tiers": {str(t): archive.frontier_size(t) for t in archive.tiers()},
        "default_tier": ap.DEFAULT_FRONTIER_TIER,
        "objective_policy": ap._live_objective_policy_from_state(state),
        "exclude_before_ts": _exclude_ts,
    }
except Exception as exc:  # noqa: BLE001
    summary["pareto"] = {"error": repr(exc)}
try:
    conn = strategy_store._conn
    rows = conn.execute("SELECT entry_type, COUNT(*) FROM strategies GROUP BY entry_type").fetchall()
    ex = conn.execute("SELECT id, species, entry_type, description FROM strategies "
                      "ORDER BY created_at DESC LIMIT 5").fetchall()
    conv = conn.execute("SELECT COUNT(*) FROM strategy_conventions").fetchone()[0]
    conv_ex = conn.execute("SELECT * FROM strategy_conventions LIMIT 3").fetchall()
    summary["strategy_store"] = {
        "db_path_used": str(dst_ss / "strategies.db"), "db_source": str(src_ss / "strategies.db"),
        "count": strategy_store.count(), "by_entry_type": {r[0]: r[1] for r in rows},
        "conventions_table_rows": conv,
        "examples": [dict(r) for r in ex],
        "convention_examples": [dict(r) for r in conv_ex],
        "search_index_health": strategy_store.search_index_health(),
        "denylisted_flags": sorted(ap._PLANNER_DENYLISTED_FEATURE_FLAGS),
        "suppressed_numeric_surfaces": sorted(ap._PLANNER_SUPPRESSED_NUMERIC_SURFACES),
        "hint_lines_in_prompt": [ln for ln in sec["planner_strategy_hints"].splitlines()],
    }
except Exception as exc:  # noqa: BLE001
    summary["strategy_store"] = {"error": repr(exc)}
try:
    hyps = ap._load_operator_hypotheses()
    import operator_hypotheses as _oh
    summary["operator_hypotheses"] = {
        "source": str(_oh.DEFAULT_HYPOTHESES_PATH), "resolutions": str(_oh.DEFAULT_RESOLUTIONS_PATH),
        "count": len(hyps), "open": sum(1 for h in hyps if getattr(h, "is_open", False)),
        "ids": [getattr(h, "id", "?") for h in hyps],
        "with_proposed_action": [getattr(h, "id", "?") for h in hyps
                                 if getattr(h, "proposed_action", None)],
    }
except Exception as exc:  # noqa: BLE001
    summary["operator_hypotheses"] = {"error": repr(exc)}

# ---------------------------------------------------------------- post-run side-effect audit
summary["post"] = {
    "canonical_ledger_sha256": sha(CANON_LEDGER),
    "scratch_ledger_sha256": sha(SCR_STATE / "ledger.jsonl"),
    "scratch_state_tree": tree_snapshot(SCR_STATE),
    "telemetry_sha256": sha(TELEMETRY),
    "strategy_db_src_sha256": sha(src_ss / "strategies.db"),
    "canonical_known_good": sorted(os.listdir("/mnt/raid0/llm/state/vidya/loop-known-good")),
}
summary["blocked_events"] = list(canary_guard.BLOCKED)
summary["allowed_writes"] = sorted(canary_guard.ALLOWED_WRITES)
summary["subprocesses"] = canary_guard.SUBPROCESSES
summary["save_state_calls_suppressed"] = len(_saves)
summary["finished"] = time.time()
(BASE / "B-summary.json").write_text(json.dumps(summary, indent=1, default=str))
print("prompt_chars", len(prompt), "belief", summary["belief"].get("status"),
      summary["belief"].get("reason"), "blocked", len(canary_guard.BLOCKED))
